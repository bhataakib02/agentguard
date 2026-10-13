"""
Comprehensive test suite for Passport Key Rotation and Adversarial Signature Verification.
Verifies requirement B2:
- Active public key verifies fresh passports.
- Historical public keys remain trusted and verify historical passports signed by them.
- Unknown or missing key IDs are safely rejected.
- Untrusted passports cannot inject public keys.
- Invalid signatures and modified payloads fail closed.
"""

import uuid
import datetime
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from services.passport_service import PassportSigningService
import models

class DummyAgent:
    def __init__(self, agent_id=None, agent_code="AGT-TEST-001", org_id=None):
        self.id = agent_id or uuid.uuid4()
        self.agent_code = agent_code
        self.org_id = org_id or uuid.uuid4()
        self.owner_id = uuid.uuid4()
        self.autonomy_level = "HIGH"
        self.department = "SECURITY"
        self.environment = "PRODUCTION"
        self.model_name = "claude-3-opus"
        self.model_version = "20240229"
        self.purpose = "Security analysis agent"
        self.status = "ACTIVE"

class DummyPassport:
    def __init__(self, agent_id=None):
        self.id = uuid.uuid4()
        self.agent_id = agent_id or uuid.uuid4()
        self.passport_number = f"PASS-{uuid.uuid4().hex[:8].upper()}"
        self.passport_version = "1.0"
        self.key_id = None
        self.algorithm = "Ed25519"
        self.digital_signature = None
        self.verification_status = "PENDING"
        self.issued_at = datetime.datetime.utcnow()
        self.expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=365)
        self.claims = {}
        self.capabilities = ["read:secrets", "write:audit"]


def test_passport_active_key_verification():
    service = PassportSigningService()
    agent = DummyAgent()
    passport = DummyPassport(agent_id=agent.id)

    # Sign with active key
    sig = service.sign_passport(agent, passport, capabilities=["read:secrets", "write:audit"])
    assert sig.startswith("ed25519:")
    assert passport.key_id == service.key_id

    # Verify
    result = service.verify_passport(passport, agent)
    assert result["valid"] is True
    assert result["status"] == "VERIFIED"
    assert result["key_id"] == service.key_id


def test_passport_key_rotation_historical_verification():
    service = PassportSigningService()
    agent_v1 = DummyAgent(agent_code="AGT-V1")
    passport_v1 = DummyPassport(agent_id=agent_v1.id)

    initial_key_id = service.key_id
    # Sign v1 passport with initial active key
    service.sign_passport(agent_v1, passport_v1)
    assert passport_v1.key_id == initial_key_id

    # Rotate to a new active key
    new_key_id = f"plat_v2_{uuid.uuid4().hex[:6]}"
    new_priv_key = ed25519.Ed25519PrivateKey.generate()
    service.rotate_active_key(new_key_id, new_priv_key)

    assert service.key_id == new_key_id
    assert initial_key_id in service._trusted_keys
    assert new_key_id in service._trusted_keys

    # Sign v2 passport with new active key
    agent_v2 = DummyAgent(agent_code="AGT-V2")
    passport_v2 = DummyPassport(agent_id=agent_v2.id)
    service.sign_passport(agent_v2, passport_v2)
    assert passport_v2.key_id == new_key_id

    # Both historical (v1) and fresh (v2) passports must verify successfully
    res_v1 = service.verify_passport(passport_v1, agent_v1)
    assert res_v1["valid"] is True
    assert res_v1["status"] == "VERIFIED"
    assert res_v1["key_id"] == initial_key_id

    res_v2 = service.verify_passport(passport_v2, agent_v2)
    assert res_v2["valid"] is True
    assert res_v2["status"] == "VERIFIED"
    assert res_v2["key_id"] == new_key_id


def test_passport_unknown_or_missing_key_id_rejected():
    service = PassportSigningService()
    agent = DummyAgent()
    passport = DummyPassport(agent_id=agent.id)
    service.sign_passport(agent, passport)

    # 1. Missing key_id
    passport.key_id = None
    res_missing = service.verify_passport(passport, agent)
    assert res_missing["valid"] is False
    assert res_missing["status"] == "UNKNOWN_KEY_ID"

    # 2. Unknown key_id
    passport.key_id = "untrusted_attacker_key_999"
    res_unknown = service.verify_passport(passport, agent)
    assert res_unknown["valid"] is False
    assert res_unknown["status"] == "UNKNOWN_KEY_ID"


def test_passport_tampered_payload_rejected():
    service = PassportSigningService()
    agent = DummyAgent()
    passport = DummyPassport(agent_id=agent.id)
    service.sign_passport(agent, passport)

    # Verify clean pass first
    assert service.verify_passport(passport, agent)["valid"] is True

    # Tamper with agent autonomy level
    agent.autonomy_level = "CRITICAL_ELEVATED"
    res_tampered = service.verify_passport(passport, agent)
    assert res_tampered["valid"] is False
    assert res_tampered["status"] == "TAMPERED"

    # Restore autonomy, tamper with department
    agent.autonomy_level = "HIGH"
    agent.department = "FINANCE_UNAUTHORIZED"
    res_tampered_dept = service.verify_passport(passport, agent)
    assert res_tampered_dept["valid"] is False
    assert res_tampered_dept["status"] == "TAMPERED"


def test_passport_invalid_signature_format_or_corrupt_bytes():
    service = PassportSigningService()
    agent = DummyAgent()
    passport = DummyPassport(agent_id=agent.id)
    service.sign_passport(agent, passport)

    # Corrupt digital signature format
    passport.digital_signature = "rsa:badformat"
    assert service.verify_passport(passport, agent)["status"] == "UNVERIFIED"

    # Corrupt signature bytes
    passport.digital_signature = "ed25519:AAAA"
    assert service.verify_passport(passport, agent)["status"] == "TAMPERED"


def test_passport_untrusted_cannot_inject_key():
    service = PassportSigningService()
    agent = DummyAgent()
    passport = DummyPassport(agent_id=agent.id)
    
    # Generate untrusted external keypair
    attacker_priv = ed25519.Ed25519PrivateKey.generate()
    attacker_pub = attacker_priv.public_key()
    attacker_key_id = "attacker_evil_key"

    # Attacker tries to attach their own key ID to the passport
    passport.key_id = attacker_key_id
    canonical_bytes = service.canonicalize_passport_data(agent, passport)
    attacker_sig = attacker_priv.sign(canonical_bytes)
    import base64
    passport.digital_signature = f"ed25519:{base64.b64encode(attacker_sig).decode('utf-8')}"

    # Platform service does not trust attacker's key ID -> must reject
    res = service.verify_passport(passport, agent)
    assert res["valid"] is False
    assert res["status"] == "UNKNOWN_KEY_ID"
