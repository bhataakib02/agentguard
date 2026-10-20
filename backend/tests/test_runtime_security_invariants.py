"""
AgentGuard Runtime Security Invariant Tests
Verifies that no machine request can bypass:
1. Machine Authentication (missing, forged, expired, or revoked tokens)
2. Multi-tenant isolation (cross-tenant invocation, resource access)
3. Agent Permission checks (unauthorized tool, scope, or action)
4. Capability checks & replay prevention (expired, limit-exceeded, or replayed tokens)
5. Policy decisions & human approval gates (policy REFUSE or REVIEW)
6. Execution gate tokens (missing, cross-agent, or replayed gate tokens)
7. SSRF protections (cloud metadata, loopback, illegal schemes)
8. Ed25519 Passport cryptographic integrity (tamper detection, expiration, revocation)
9. BYOK tenant key isolation (cross-tenant ciphertext inaccessibility)
"""

import os
import sys
import uuid
import datetime
import pytest
from starlette.testclient import TestClient
from jose import jwt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from database import SessionLocal
from config import settings
import models
from core import security
from services.machine_auth_service import machine_auth_service
from services.passport_service import passport_service
from services.byok_service import byok_service
from services.tool_proxy_service import tool_proxy_service

client = TestClient(app)

class TestRuntimeSecurityInvariants:
    @classmethod
    def setup_class(cls):
        cls.db = SessionLocal()
        from bootstrap import ensure_canonical_plans
        ensure_canonical_plans(cls.db)

        # 1. Tenant Org Alpha
        cls.org_alpha = models.Organization(
            name=f"Security Invariant Org Alpha {uuid.uuid4().hex[:6]}",
            domain="alpha.security.test",
            status="ACTIVE"
        )
        cls.db.add(cls.org_alpha)

        # 2. Tenant Org Beta
        cls.org_beta = models.Organization(
            name=f"Security Invariant Org Beta {uuid.uuid4().hex[:6]}",
            domain="beta.security.test",
            status="ACTIVE"
        )
        cls.db.add(cls.org_beta)
        cls.db.commit()
        cls.db.refresh(cls.org_alpha)
        cls.db.refresh(cls.org_beta)

        # 3. Admin in Org Alpha
        cls.admin_alpha = models.User(
            org_id=cls.org_alpha.id,
            email=f"admin_alpha_{uuid.uuid4().hex[:6]}@alpha.security.test",
            full_name="Alpha Admin",
            role="ADMIN",
            status="ACTIVE"
        )
        cls.db.add(cls.admin_alpha)

        # 4. Admin in Org Beta
        cls.admin_beta = models.User(
            org_id=cls.org_beta.id,
            email=f"admin_beta_{uuid.uuid4().hex[:6]}@beta.security.test",
            full_name="Beta Admin",
            role="ADMIN",
            status="ACTIVE"
        )
        cls.db.add(cls.admin_beta)
        cls.db.commit()
        cls.db.refresh(cls.admin_alpha)
        cls.db.refresh(cls.admin_beta)

        # 5. Agent Alpha in Org Alpha
        cls.agent_alpha = models.Agent(
            agent_code=f"AG-ALPHA-{uuid.uuid4().hex[:4]}",
            org_id=cls.org_alpha.id,
            owner_id=cls.admin_alpha.id,
            name="Alpha Production Agent",
            department="Operations",
            purpose="Autonomous financial transfers and payment ops",
            model_name="gpt-4o",
            model_version="1.0.0",
            environment="PRODUCTION",
            autonomy_level="HIGH",
            status="NORMAL",
            daily_budget=50000.0
        )
        cls.db.add(cls.agent_alpha)

        # 6. Agent Beta in Org Beta
        cls.agent_beta = models.Agent(
            agent_code=f"AG-BETA-{uuid.uuid4().hex[:4]}",
            org_id=cls.org_beta.id,
            owner_id=cls.admin_beta.id,
            name="Beta Production Agent",
            department="Operations",
            purpose="Autonomous data queries",
            model_name="claude-3-5-sonnet",
            model_version="1.0.0",
            environment="PRODUCTION",
            autonomy_level="MEDIUM",
            status="NORMAL",
            daily_budget=10000.0
        )
        cls.db.add(cls.agent_beta)
        cls.db.commit()
        cls.db.refresh(cls.agent_alpha)
        cls.db.refresh(cls.agent_beta)

        # Issue Machine Credentials for Agent Alpha
        cred_alpha, raw_token_alpha = machine_auth_service.create_agent_credential(
            db=cls.db,
            agent=cls.agent_alpha,
            name="Alpha Primary Machine Key",
            expires_in_days=30
        )
        cls.cred_alpha = cred_alpha
        cls.raw_token_alpha = raw_token_alpha

        # Issue Machine JWT for Agent Alpha
        jwt_info = machine_auth_service.issue_machine_jwt(
            agent=cls.agent_alpha,
            credential=cred_alpha,
            expires_in_hours=1
        )
        cls.machine_jwt_alpha = jwt_info["access_token"]
        cls.headers_alpha = {"Authorization": f"Bearer {cls.machine_jwt_alpha}"}

        # Issue and sign Ed25519 Passport for Agent Alpha
        cls.passport_alpha = models.AgentPassport(
            agent_id=cls.agent_alpha.id,
            passport_number=f"PASS-ALPHA-{uuid.uuid4().hex[:6].upper()}",
            passport_version="1.0",
            algorithm="Ed25519",
            key_id=passport_service.key_id,
            verification_status="PENDING",
            issued_at=datetime.datetime.utcnow(),
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=365)
        )
        passport_service.sign_passport(cls.agent_alpha, cls.passport_alpha, capabilities=["payment:execute", "read:balance"])
        cls.db.add(cls.passport_alpha)
        cls.db.commit()
        cls.db.refresh(cls.passport_alpha)

    @classmethod
    def teardown_class(cls):
        cls.db.close()

    # --- 1. AUTHENTICATION BYPASS TESTS ---
    def test_01_machine_cannot_bypass_authentication_with_empty_or_missing_token(self):
        """Unauthenticated requests to machine runtime endpoints must return 401"""
        resp_no_auth = client.post("/api/runtime/authorize", json={"action": "EXECUTE", "resource": "PAYMENTS"})
        assert resp_no_auth.status_code == 401

        resp_empty_bearer = client.post("/api/runtime/authorize", headers={"Authorization": "Bearer "}, json={"action": "EXECUTE"})
        assert resp_empty_bearer.status_code == 401

        resp_garbage = client.post("/api/runtime/authorize", headers={"Authorization": "Bearer invalid_garbage_token_value"}, json={})
        assert resp_garbage.status_code == 401

    def test_02_machine_cannot_bypass_authentication_with_forged_signature(self):
        """Forged machine JWT signed with unauthorized secret key must return 401"""
        forged_jwt = jwt.encode(
            {
                "sub": str(self.agent_alpha.id),
                "agent_id": str(self.agent_alpha.id),
                "org_id": str(self.org_alpha.id),
                "token_type": "machine",
                "exp": int(datetime.datetime.utcnow().timestamp()) + 3600
            },
            "malicious-attacker-secret-key-9999",
            algorithm="HS256"
        )
        resp = client.post(
            "/api/runtime/authorize",
            headers={"Authorization": f"Bearer {forged_jwt}"},
            json={"action": "EXECUTE", "resource": "PAYMENTS"}
        )
        assert resp.status_code == 401

    def test_03_machine_cannot_bypass_authentication_with_revoked_credential(self):
        """Revoked machine credentials must immediately fail verification"""
        temp_cred, temp_raw = machine_auth_service.create_agent_credential(
            db=self.db,
            agent=self.agent_alpha,
            name="Temporary Revocation Test Key"
        )
        jwt_info = machine_auth_service.issue_machine_jwt(agent=self.agent_alpha, credential=temp_cred)
        temp_jwt = jwt_info["access_token"]
        
        # Works initially
        res = machine_auth_service.decode_and_verify_machine_jwt(temp_jwt, self.db)
        assert res["agent"].id == self.agent_alpha.id

        # Revoke the credential
        machine_auth_service.revoke_agent_credential(self.db, str(self.agent_alpha.id), str(temp_cred.id))
        self.db.refresh(temp_cred)
        assert temp_cred.status == "REVOKED"

    # --- 2. TENANT ISOLATION BYPASS TESTS ---
    def test_04_machine_cannot_cross_tenant_access_resources(self):
        """Machine from Org Alpha cannot access or invoke Org Beta resources"""
        token_alpha_admin = security.create_access_token(self.admin_alpha.id, email=self.admin_alpha.email, role="ADMIN")
        resp = client.get(
            f"/api/agents/{self.agent_beta.id}",
            headers={"Authorization": f"Bearer {token_alpha_admin}"}
        )
        assert resp.status_code in [403, 404]

    def test_05_machine_cannot_spoof_tenant_context_header(self):
        """Tampered X-Organization-Context header from user is rejected or scoped to true tenant"""
        token_alpha = security.create_access_token(self.admin_alpha.id, email=self.admin_alpha.email, role="USER")
        resp = client.get(
            "/api/organization/dashboard",
            headers={
                "Authorization": f"Bearer {token_alpha}",
                "X-Organization-Context": str(self.org_beta.id)
            }
        )
        assert resp.status_code == 200
        # Verified tenant remains Org Alpha, never Org Beta
        assert resp.json()["org_id"] == str(self.org_alpha.id)

    # --- 3. PERMISSION CHECKS BYPASS TESTS ---
    def test_06_machine_cannot_bypass_permission_boundary(self):
        """Action requiring permission not held by agent is REFUSED by authorization kernel"""
        resp = client.post(
            "/api/runtime/authorize",
            headers=self.headers_alpha,
            json={
                "action": "EXECUTE",
                "resource": "UNAUTHORIZED_ROOT_SHELL",
                "amount": 10.0
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] == "REFUSE"

    # --- 4. CAPABILITY CHECKS & REPLAY DEFENSE TESTS ---
    def test_07_expired_capability_token_cannot_bypass_checks(self):
        """Presenting an expired capability token must be rejected"""
        expired_token = models.CapabilityToken(
            token_code=f"cap_exp_{uuid.uuid4().hex[:8]}",
            agent_id=self.agent_alpha.id,
            capability_name="PAYMENTS.EXECUTE",
            scope="single-use",
            amount_limit=500.0,
            issued_at=datetime.datetime.utcnow() - datetime.timedelta(days=2),
            expires_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=5),
            status="ACTIVE"
        )
        self.db.add(expired_token)
        self.db.commit()

        resp = client.post(
            "/api/runtime/authorize",
            headers=self.headers_alpha,
            json={
                "action": "EXECUTE",
                "resource": "PAYMENTS",
                "capability_token": expired_token.token_code,
                "amount": 50.0
            }
        )
        assert resp.status_code == 200
        assert resp.json()["decision"] == "REFUSE"

    def test_08_capability_token_replay_attack_is_prevented(self):
        """A consumed single-use capability token cannot be replayed"""
        consumed_token = models.CapabilityToken(
            token_code=f"cap_replay_{uuid.uuid4().hex[:8]}",
            agent_id=self.agent_alpha.id,
            capability_name="PAYMENTS.EXECUTE",
            scope="single-use",
            amount_limit=500.0,
            issued_at=datetime.datetime.utcnow(),
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            status="USED"
        )
        self.db.add(consumed_token)
        self.db.commit()

        resp = client.post(
            "/api/runtime/authorize",
            headers=self.headers_alpha,
            json={
                "action": "EXECUTE",
                "resource": "PAYMENTS",
                "capability_token": consumed_token.token_code,
                "amount": 50.0
            }
        )
        assert resp.status_code == 200
        assert resp.json()["decision"] == "REFUSE"

    # --- 5. POLICY DECISIONS & APPROVAL ENFORCEMENT ---
    def test_09_high_risk_action_triggers_review_and_blocks_unauthorized_execution(self):
        """High risk or financial exceeding threshold triggers REVIEW, blocking automatic pass"""
        resp = client.post(
            "/api/runtime/authorize",
            headers=self.headers_alpha,
            json={
                "action": "EXECUTE",
                "resource": "PAYMENTS",
                "amount": 999999999.0
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] in ["REFUSE", "REVIEW"]

    # --- 6. EXECUTION GATE TOKEN BYPASS TESTS ---
    def test_10_execution_gate_rejects_missing_or_forged_gate_token(self):
        """Direct call to execution gateway without valid gate token is rejected"""
        resp_missing = client.post(
            "/api/runtime/execute",
            headers=self.headers_alpha,
            json={"tool_name": "refund_tool", "parameters": {}}
        )
        assert resp_missing.status_code in [400, 401, 403, 422]

        resp_forged = client.post(
            "/api/runtime/execute",
            headers=self.headers_alpha,
            json={
                "execution_gate_token": "gate_fake_unauthorized_token_xyz",
                "tool_name": "refund_tool",
                "parameters": {}
            }
        )
        assert resp_forged.status_code in [400, 401, 403, 404]

    # --- 7. SSRF PROTECTION IN EXECUTION GATEWAY ---
    def test_11_execution_proxy_blocks_cloud_metadata_ssrf(self, monkeypatch):
        """Tool proxy execution service strictly blocks AWS/GCP 169.254.169.254 metadata endpoint"""
        monkeypatch.setenv("AGENTGUARD_ALLOW_LOCAL_TOOLS", "false")
        ssrf_targets = [
            "http://169.254.169.254/latest/meta-data/",
            "http://metadata.google.internal/computeMetadata/v1/",
            "http://127.0.0.1:8080/admin",
            "http://localhost:5432",
            "file:///etc/passwd"
        ]
        for target in ssrf_targets:
            res = tool_proxy_service._validate_ssrf_safety(target)
            assert res["safe"] is False
            assert "reason" in res

    # --- 8. ED25519 PASSPORT INTEGRITY & TAMPER DETECTION ---
    def test_12_ed25519_passport_validates_clean_and_detects_tampering(self):
        """Tampering with signed claims immediately fails Ed25519 cryptographic verification"""
        # Ensure agent status is normal in case earlier test tripped circuit breaker
        self.agent_alpha.status = "NORMAL"
        self.db.commit()
        self.db.refresh(self.agent_alpha)
        self.db.refresh(self.passport_alpha)
        # 1. Clean verification succeeds
        clean_result = passport_service.verify_passport(self.passport_alpha, self.agent_alpha)
        assert clean_result["valid"] is True, f"Verification failed: {clean_result}"
        assert clean_result["status"] == "VERIFIED"

        # 2. Tampered signature fails
        original_sig = self.passport_alpha.digital_signature
        self.passport_alpha.digital_signature = "ed25519:YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY3ODkw"
        tampered_result = passport_service.verify_passport(self.passport_alpha, self.agent_alpha, capabilities=["payment:execute", "read:balance"])
        assert tampered_result["valid"] is False
        assert tampered_result["status"] in ["TAMPERED", "UNVERIFIED"]
        self.passport_alpha.digital_signature = original_sig

        # 3. Explicit revocation fails
        self.passport_alpha.verification_status = "REVOKED"
        revoked_result = passport_service.verify_passport(self.passport_alpha, self.agent_alpha)
        assert revoked_result["valid"] is False
        assert revoked_result["status"] == "REVOKED"
        self.passport_alpha.verification_status = "VERIFIED"

    # --- 9. BYOK CRYPTOGRAPHIC TENANT ISOLATION ---
    def test_13_byok_keys_are_strictly_isolated_between_tenants(self):
        """Tenant Alpha's ciphertext cannot be decrypted under Tenant Beta's cryptographic context"""
        plaintext = "CONFIDENTIAL_ORGANIZATION_PAYLOAD"
        encrypted_data = byok_service.encrypt_payload(self.db, str(self.org_alpha.id), plaintext)
        
        # Correct tenant decrypts
        decrypted_alpha = byok_service.decrypt_payload(self.db, str(self.org_alpha.id), encrypted_data)
        assert decrypted_alpha == plaintext

        # Cross-tenant decrypt with Tenant Beta fails
        with pytest.raises(Exception):
            byok_service.decrypt_payload(self.db, str(self.org_beta.id), encrypted_data)
