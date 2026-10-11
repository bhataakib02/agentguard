import os
import sys
import uuid
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///test_byok.db"
os.environ["SECRET_KEY"] = "test-byok-secret-key-123456789012"
os.environ["ENVIRONMENT"] = "test"

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from main import app
from database import Base, engine, get_db
import models
from core import security
from services.byok_service import byok_service

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
test_client = TestClient(app)


class TestBYOKTenantSuite:
    @classmethod
    def setup_class(cls):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        cls.db = TestingSessionLocal()

        # Tenant A
        cls.org_a = models.Organization(
            id=str(uuid.uuid4()),
            name="Tenant Alpha Corp",
            slug=f"tenant-alpha-{uuid.uuid4().hex[:6]}",
            status="ACTIVE"
        )
        # Tenant B
        cls.org_b = models.Organization(
            id=str(uuid.uuid4()),
            name="Tenant Beta Corp",
            slug=f"tenant-beta-{uuid.uuid4().hex[:6]}",
            status="ACTIVE"
        )
        cls.db.add(cls.org_a)
        cls.db.add(cls.org_b)
        cls.db.commit()

        # Admin User in Tenant A
        cls.admin_a = models.User(
            id=str(uuid.uuid4()),
            org_id=cls.org_a.id,
            email=f"admin-{uuid.uuid4().hex[:4]}@alpha.com",
            full_name="Alpha Admin",
            role="ADMIN",
            status="ACTIVE",
            password_hash=security.get_password_hash("AlphaPass123!")
        )
        # Viewer User in Tenant A (non-admin)
        cls.viewer_a = models.User(
            id=str(uuid.uuid4()),
            org_id=cls.org_a.id,
            email=f"viewer-{uuid.uuid4().hex[:4]}@alpha.com",
            full_name="Alpha Viewer",
            role="VIEWER",
            status="ACTIVE",
            password_hash=security.get_password_hash("ViewerPass123!")
        )
        # Admin User in Tenant B
        cls.admin_b = models.User(
            id=str(uuid.uuid4()),
            org_id=cls.org_b.id,
            email=f"admin-{uuid.uuid4().hex[:4]}@beta.com",
            full_name="Beta Admin",
            role="ADMIN",
            status="ACTIVE",
            password_hash=security.get_password_hash("BetaPass123!")
        )
        cls.db.add(cls.admin_a)
        cls.db.add(cls.viewer_a)
        cls.db.add(cls.admin_b)
        cls.db.commit()

        cls.token_admin_a = security.create_access_token(
            user_id=cls.admin_a.id, email=cls.admin_a.email, role="ADMIN"
        )
        cls.token_viewer_a = security.create_access_token(
            user_id=cls.viewer_a.id, email=cls.viewer_a.email, role="VIEWER"
        )
        cls.token_admin_b = security.create_access_token(
            user_id=cls.admin_b.id, email=cls.admin_b.email, role="ADMIN"
        )

    @classmethod
    def teardown_class(cls):
        cls.db.close()

    def test_01_byok_encryption_and_decryption(self):
        org_a = self.org_a
        plaintext = "super-sensitive-llm-prompt-with-api-keys"

        # Configure BYOK for Org A
        byok_service.configure_tenant_byok(
            db=self.db,
            org=org_a,
            provider="AWS_KMS",
            key_arn="arn:aws:kms:us-east-1:123456789012:key/alpha-kms-key-1",
            key_alias="alias/alpha-kms"
        )

        ciphertext = byok_service.encrypt_payload(self.db, str(org_a.id), plaintext)
        assert ciphertext.startswith("v1.")
        assert plaintext not in ciphertext

        decrypted = byok_service.decrypt_payload(self.db, str(org_a.id), ciphertext)
        assert decrypted == plaintext

    def test_02_byok_cross_tenant_cryptographic_isolation(self):
        org_a = self.org_a
        org_b = self.org_b
        secret_a = "confidential-financial-trade-plan"

        byok_service.configure_tenant_byok(
            db=self.db,
            org=org_a,
            provider="LOCAL_AES",
            key_alias="alias/alpha-local",
            config_params={"raw_key_material": "tenant-a-secret-seed-987654321"}
        )
        byok_service.configure_tenant_byok(
            db=self.db,
            org=org_b,
            provider="LOCAL_AES",
            key_alias="alias/beta-local",
            config_params={"raw_key_material": "tenant-b-secret-seed-123456789"}
        )

        # Encrypt under Tenant A
        ciphertext_a = byok_service.encrypt_payload(self.db, str(org_a.id), secret_a)

        # Tenant B attempts to decrypt Tenant A's ciphertext
        with pytest.raises(ValueError, match="Decryption failed"):
            byok_service.decrypt_payload(self.db, str(org_b.id), ciphertext_a)

    def test_03_byok_rotation_and_tamper_resistance(self):
        org_a = self.org_a
        secret_text = "agent-memory-checkpoint"

        byok_service.configure_tenant_byok(
            db=self.db,
            org=org_a,
            provider="GCP_KMS",
            key_arn="projects/agentguard/locations/global/keyRings/ring/cryptoKeys/key1"
        )

        c1 = byok_service.encrypt_payload(self.db, str(org_a.id), secret_text)
        assert byok_service.decrypt_payload(self.db, str(org_a.id), c1) == secret_text

        # Rotate key material
        byok_service.rotate_tenant_byok(db=self.db, org=org_a)
        assert org_a.kms_config_json.get("key_version") == 2
        assert "rotated_at" in org_a.kms_config_json

        # New encryption uses new derived key
        c2 = byok_service.encrypt_payload(self.db, str(org_a.id), secret_text)
        assert c2 != c1

        # Tampered ciphertext payload
        tampered_c = c2[:-4] + "AAAA"
        with pytest.raises(ValueError):
            byok_service.decrypt_payload(self.db, str(org_a.id), tampered_c)

    def test_04_byok_roundtrip_probe(self):
        org_a = self.org_a
        byok_service.configure_tenant_byok(
            db=self.db,
            org=org_a,
            provider="VAULT",
            key_arn="transit/keys/alpha-guard"
        )

        probe_result = byok_service.test_roundtrip(self.db, org_a)
        assert probe_result["success"] is True
        assert probe_result["status"] == "OPERATIONAL"
        assert probe_result["probe_verified"] is True
        assert probe_result["provider"] == "VAULT"

    def test_05_byok_rest_api_lifecycle(self):
        headers_admin = {"Authorization": f"Bearer {self.token_admin_a}"}
        headers_viewer = {"Authorization": f"Bearer {self.token_viewer_a}"}

        # 1. GET default BYOK status
        res = test_client.get("/api/organization/byok", headers=headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert "provider" in data
        assert "is_custom_key" in data

        # 2. Non-admin cannot configure BYOK
        res = test_client.post(
            "/api/organization/byok",
            headers=headers_viewer,
            json={"provider": "AWS_KMS", "key_arn": "arn:aws:kms:us-east-1:111:key/test"}
        )
        assert res.status_code == 403

        # 3. Admin configures BYOK
        res = test_client.post(
            "/api/organization/byok",
            headers=headers_admin,
            json={
                "provider": "AWS_KMS",
                "key_arn": "arn:aws:kms:us-east-1:111:key/test",
                "key_alias": "alias/alpha-kms-prod"
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["provider"] == "AWS_KMS"
        assert data["status"] == "ACTIVE"
        assert data["is_custom_key"] is True

        # 4. Probe test endpoint
        res = test_client.post("/api/organization/byok/test", headers=headers_admin)
        assert res.status_code == 200
        test_data = res.json()
        assert test_data["success"] is True
        assert test_data["status"] == "OPERATIONAL"
        assert test_data["probe_verified"] is True

        # 5. Rotate key
        res = test_client.post("/api/organization/byok/rotate", headers=headers_admin, json={})
        assert res.status_code == 200
        rotate_data = res.json()
        assert rotate_data["status"] == "ACTIVE"

        # 6. Disable BYOK
        res = test_client.post("/api/organization/byok/disable", headers=headers_admin)
        assert res.status_code == 200
        disable_data = res.json()
        assert disable_data["provider"] == "SYSTEM_MANAGED"
        assert disable_data["is_custom_key"] is False

        # 7. Verify Audit Logs created
        audits = self.db.query(models.AuditLog).filter(
            models.AuditLog.org_id == self.org_a.id,
            models.AuditLog.resource == "byok"
        ).all()
        event_types = [a.event_type for a in audits]
        assert "BYOK_KEY_CONFIGURED" in event_types
        assert "BYOK_KEY_TESTED" in event_types
        assert "BYOK_KEY_ROTATED" in event_types
        assert "BYOK_KEY_DISABLED" in event_types
