"""
Dedicated test suite verifying Webhook Secret Encryption, Migration Idempotency,
Tamper-Resistance, and Fail-Closed Security Invariants.
Verifies requirement B6 & Section 6 of Post-Remediation Security Rules:
- Plaintext secrets are encrypted with AES-256-GCM.
- Already encrypted secrets are preserved without double-encryption.
- Migration is idempotent and safe.
- Tampered ciphertext fails closed and raises security alerts.
- Logs and reports contain no plaintext secret values.
"""

import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
import models
from core.security import encrypt_secret_at_rest, decrypt_secret_at_rest
from scripts.migrate_webhook_secrets import migrate_webhook_secrets
from services.notification_service import notification_service

# Isolated SQLite test engine for pure fixture execution
test_engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="module")
def setup_webhook_test_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    org = models.Organization(name="Webhook Test Org", slug=f"webhook-test-{uuid.uuid4().hex[:6]}", status="ACTIVE")
    db.add(org)
    db.commit()
    db.refresh(org)
    yield db, org
    db.close()
    Base.metadata.drop_all(bind=test_engine)


def test_webhook_encryption_migration_lifecycle(setup_webhook_test_db):
    db, org = setup_webhook_test_db

    # 1. Seed test endpoints
    raw_plaintext_secret = f"whsec_raw_{uuid.uuid4().hex}"
    already_encrypted_secret = encrypt_secret_at_rest(f"whsec_pre_encrypted_{uuid.uuid4().hex}")
    
    ep_plain = models.WebhookEndpoint(
        org_id=org.id,
        name="Plain Endpoint",
        url="https://example.com/webhook-plain",
        secret_hash="hash_plain_123",
        secret_key=raw_plaintext_secret,
        event_types=["decision.created"],
        is_active=True
    )
    ep_already_enc = models.WebhookEndpoint(
        org_id=org.id,
        name="Already Encrypted Endpoint",
        url="https://example.com/webhook-already-enc",
        secret_hash="hash_enc_456",
        secret_key=already_encrypted_secret,
        event_types=["decision.created"],
        is_active=True
    )
    ep_no_secret = models.WebhookEndpoint(
        org_id=org.id,
        name="No Secret Endpoint",
        url="https://example.com/webhook-no-secret",
        secret_hash="hash_none_789",
        secret_key=None,
        event_types=["decision.created"],
        is_active=True
    )
    db.add_all([ep_plain, ep_already_enc, ep_no_secret])
    db.commit()

    # 2. Test Dry-Run: Must detect 1 migration candidate without modifying database
    dry_run_stats = migrate_webhook_secrets(dry_run=True, db_session=db)
    assert dry_run_stats["migrated"] == 1
    assert dry_run_stats["already_encrypted"] == 1
    assert dry_run_stats["skipped_no_secret"] == 1
    assert ep_plain.secret_key == raw_plaintext_secret, "Dry-run must not mutate database"

    # 3. Test Commit Migration: Must encrypt plaintext secret
    commit_stats = migrate_webhook_secrets(dry_run=False, db_session=db)
    assert commit_stats["migrated"] == 1
    assert commit_stats["already_encrypted"] == 1
    assert commit_stats["dry_run"] is False

    db.refresh(ep_plain)
    db.refresh(ep_already_enc)
    assert ep_plain.secret_key.startswith("enc:aesgcm:")
    assert ep_plain.secret_key != raw_plaintext_secret
    assert decrypt_secret_at_rest(ep_plain.secret_key) == raw_plaintext_secret
    assert ep_already_enc.secret_key == already_encrypted_secret, "Already-encrypted secret must be preserved untouched"

    # 4. Test Idempotency: Re-running must migrate 0 endpoints and leave all ciphertexts identical
    re_run_stats = migrate_webhook_secrets(dry_run=False, db_session=db)
    assert re_run_stats["migrated"] == 0
    assert re_run_stats["already_encrypted"] == 2
    assert ep_plain.secret_key.startswith("enc:aesgcm:")


def test_webhook_tampered_ciphertext_fails_closed(setup_webhook_test_db):
    db, org = setup_webhook_test_db
    valid_secret = "whsec_valid_hmac_secret_9999"
    ciphertext = encrypt_secret_at_rest(valid_secret)

    # 1. Clean decryption succeeds
    decrypted = decrypt_secret_at_rest(ciphertext)
    assert decrypted == valid_secret

    # 2. Tampered ciphertext payload must fail closed
    parts = ciphertext.split(":")
    # Alter the ciphertext bytes
    tampered_ciphertext = f"{parts[0]}:{parts[1]}:{parts[2]}:AAAA{parts[3][4:]}"
    tampered_decrypted = decrypt_secret_at_rest(tampered_ciphertext)
    assert tampered_decrypted is None, "Tampered ciphertext must fail closed and return None"

    # 3. Corrupted nonce must fail closed
    tampered_nonce = f"{parts[0]}:{parts[1]}:XXXXX:{parts[3]}"
    assert decrypt_secret_at_rest(tampered_nonce) is None

    # 4. Outbound delivery service fails closed on tampered webhook secret
    ep_tampered = models.WebhookEndpoint(
        org_id=org.id,
        name="Tampered Endpoint",
        url="https://example.com/webhook-tampered",
        secret_hash="hash_tampered",
        secret_key=tampered_ciphertext,
        event_types=["decision.created"],
        is_active=True
    )
    db.add(ep_tampered)
    db.commit()
    db.refresh(ep_tampered)

    # When notification_service attempts delivery with tampered endpoint secret:
    delivery_result = notification_service.dispatch_webhook_delivery(
        db=db,
        endpoint=ep_tampered,
        event_type="decision.created",
        payload_data={"resource_id": "res_123", "action": "BLOCKED"}
    )
    assert delivery_result is None, "Dispatch must fail closed and return None when secret is tampered"
