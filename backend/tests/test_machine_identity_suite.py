import os
import sys
import uuid
import datetime
import hashlib
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup test environment
os.environ["DATABASE_URL"] = "sqlite:///test_machine_identity.db"
os.environ["SECRET_KEY"] = "test-machine-identity-secret-key-12345"
os.environ["ENVIRONMENT"] = "test"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import app
from database import Base, engine, get_db
import models
from core import security
from services.machine_auth_service import machine_auth_service
from services.passport_service import passport_service

TestSession = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

class TestMachineIdentitySuite:
    """
    Comprehensive Test Suite for Milestone 1:
    Machine Agent Identity, Credentials, Ed25519 Cryptographic Passport,
    Machine Authentication, and Zero-Trust Tenant Scoping.
    """

    @classmethod
    def setup_class(cls):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        db = TestSession()
        # Create Organization 1 (Acme Corp)
        org1 = models.Organization(name="Acme Corp", domain="acme.com", status="ACTIVE")
        db.add(org1)
        db.commit()
        db.refresh(org1)
        cls.org1_id = str(org1.id)

        # Create Organization 2 (Cyberdyne)
        org2 = models.Organization(name="Cyberdyne", domain="cyberdyne.com", status="ACTIVE")
        db.add(org2)
        db.commit()
        db.refresh(org2)
        cls.org2_id = str(org2.id)

        # Create Admin User in Org 1
        admin1 = models.User(
            org_id=org1.id,
            email="admin@acme.com",
            full_name="Acme Admin",
            role="ADMIN",
            status="ACTIVE"
        )
        # Create Viewer User in Org 1
        viewer1 = models.User(
            org_id=org1.id,
            email="viewer@acme.com",
            full_name="Acme Viewer",
            role="VIEWER",
            status="ACTIVE"
        )
        # Create Admin User in Org 2
        admin2 = models.User(
            org_id=org2.id,
            email="admin@cyberdyne.com",
            full_name="Cyberdyne Admin",
            role="ADMIN",
            status="ACTIVE"
        )
        db.add_all([admin1, viewer1, admin2])
        db.commit()
        db.refresh(admin1)
        db.refresh(viewer1)
        db.refresh(admin2)

        cls.admin1_id = str(admin1.id)
        cls.viewer1_id = str(viewer1.id)
        cls.admin2_id = str(admin2.id)

        cls.token_admin1 = security.create_access_token(admin1.id)
        cls.token_viewer1 = security.create_access_token(viewer1.id)
        cls.token_admin2 = security.create_access_token(admin2.id)

        # Create Agent in Org 1
        agent1 = models.Agent(
            agent_code="AG-901",
            org_id=org1.id,
            owner_id=admin1.id,
            name="Acme Financial Agent",
            department="Finance",
            purpose="Automated invoice reconciliation",
            model_name="gpt-4o",
            model_version="1.0.0",
            environment="PRODUCTION",
            autonomy_level="MEDIUM",
            status="NORMAL",
            risk_score=10,
            trust_score=95,
            daily_budget=5000.0
        )
        # Create Agent in Org 2
        agent2 = models.Agent(
            agent_code="AG-902",
            org_id=org2.id,
            owner_id=admin2.id,
            name="Cyberdyne Defense Agent",
            department="Security",
            purpose="Perimeter security",
            model_name="claude-3-5-sonnet",
            model_version="1.0.0",
            environment="PRODUCTION",
            autonomy_level="HIGH",
            status="NORMAL",
            risk_score=15,
            trust_score=90,
            daily_budget=10000.0
        )
        db.add_all([agent1, agent2])
        db.commit()
        db.refresh(agent1)
        db.refresh(agent2)

        cls.agent1_id = str(agent1.id)
        cls.agent1_code = str(agent1.agent_code)
        cls.agent2_id = str(agent2.id)
        cls.agent2_code = str(agent2.agent_code)

        # Issue cryptographically signed passports
        for ag in [agent1, agent2]:
            p = models.AgentPassport(
                agent_id=ag.id,
                passport_number=f"AG-PASSPORT-{ag.agent_code}",
                digital_signature="pending",
                issued_at=datetime.datetime.utcnow(),
                expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=365),
                verification_status="VERIFIED"
            )
            passport_service.sign_passport(ag, p)
            db.add(p)
        db.commit()
        db.close()

    # ------------------------------------------------------------------------
    # 1.1 CREDENTIAL ISSUANCE & HASHING TESTS
    # ------------------------------------------------------------------------

    def test_agent_credential_generation(self):
        """Verify credential generation produces ag_agent_ prefix and valid structure."""
        resp = client.post(
            f"/api/agents/{self.agent1_id}/credentials",
            headers={"Authorization": f"Bearer {self.token_admin1}"},
            json={"name": "Production Service Key", "credential_type": "API_KEY"}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "plaintext_token" in data
        assert data["plaintext_token"].startswith("ag_agent_")
        assert len(data["plaintext_token"]) > 30
        assert data["credential"]["agent_id"] == self.agent1_id
        assert data["credential"]["status"] == "ACTIVE"
        assert data["credential"]["name"] == "Production Service Key"
        assert data["credential"]["key_prefix"].startswith("ag_agent_")

    def test_credential_hashing(self):
        """Verify the database stores only SHA-256 hash and NEVER the plaintext."""
        resp = client.post(
            f"/api/agents/{self.agent1_id}/credentials",
            headers={"Authorization": f"Bearer {self.token_admin1}"},
            json={"name": "Security Audit Key"}
        )
        assert resp.status_code == 200
        data = resp.json()
        token = data["plaintext_token"]
        cred_id = data["credential"]["id"]

        db = TestSession()
        cred_in_db = db.query(models.AgentCredential).filter(models.AgentCredential.id == cred_id).first()
        assert cred_in_db is not None
        # Must be 64-char hex SHA-256
        assert len(cred_in_db.key_hash) == 64
        # Hash matches SHA-256 of plaintext
        expected_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        assert cred_in_db.key_hash == expected_hash
        # Plaintext is NOT stored in any field
        assert token not in cred_in_db.key_hash
        db.close()

    def test_plaintext_credential_returned_once(self):
        """Verify listing credentials returns metadata only, never the plaintext token or hash."""
        resp = client.get(
            f"/api/agents/{self.agent1_id}/credentials",
            headers={"Authorization": f"Bearer {self.token_admin1}"}
        )
        assert resp.status_code == 200
        creds = resp.json()
        assert len(creds) >= 2
        for c in creds:
            assert "plaintext_token" not in c
            assert "key_hash" not in c
            assert "key_prefix" in c
            assert c["status"] == "ACTIVE"

    def test_unauthorized_role_cannot_issue_credential(self):
        """Verify a VIEWER role cannot issue credentials (HTTP 403)."""
        resp = client.post(
            f"/api/agents/{self.agent1_id}/credentials",
            headers={"Authorization": f"Bearer {self.token_viewer1}"},
            json={"name": "Unauthorized Key"}
        )
        assert resp.status_code == 403

    def test_cross_tenant_credential_issue_rejected(self):
        """Verify Org 2 Admin cannot issue credentials for Org 1 Agent (HTTP 403)."""
        resp = client.post(
            f"/api/agents/{self.agent1_id}/credentials",
            headers={"Authorization": f"Bearer {self.token_admin2}"},
            json={"name": "Cross Tenant Key"}
        )
        assert resp.status_code == 403

    def test_credential_rotation(self):
        """Verify credential rotation atomically revokes the old key and issues a new active key."""
        # 1. Create initial key
        init_resp = client.post(
            f"/api/agents/{self.agent1_id}/credentials",
            headers={"Authorization": f"Bearer {self.token_admin1}"},
            json={"name": "Key To Rotate"}
        )
        old_id = init_resp.json()["credential"]["id"]
        old_token = init_resp.json()["plaintext_token"]

        # 2. Rotate it
        rot_resp = client.post(
            f"/api/agents/{self.agent1_id}/credentials/{old_id}/rotate",
            headers={"Authorization": f"Bearer {self.token_admin1}"},
            json={"name": "Rotated Replacement Key"}
        )
        assert rot_resp.status_code == 200
        rot_data = rot_resp.json()
        new_id = rot_data["credential"]["id"]
        new_token = rot_data["plaintext_token"]

        assert new_id != old_id
        assert new_token != old_token

        # Verify old credential is now REVOKED in DB
        db = TestSession()
        old_cred = db.query(models.AgentCredential).filter(models.AgentCredential.id == old_id).first()
        assert old_cred.status == "REVOKED"
        assert old_cred.revoked_at is not None

        new_cred = db.query(models.AgentCredential).filter(models.AgentCredential.id == new_id).first()
        assert new_cred.status == "ACTIVE"
        db.close()

    def test_credential_revocation(self):
        """Verify credential revocation endpoint sets status to REVOKED."""
        create_resp = client.post(
            f"/api/agents/{self.agent1_id}/credentials",
            headers={"Authorization": f"Bearer {self.token_admin1}"},
            json={"name": "Key To Revoke"}
        )
        cred_id = create_resp.json()["credential"]["id"]

        del_resp = client.delete(
            f"/api/agents/{self.agent1_id}/credentials/{cred_id}",
            headers={"Authorization": f"Bearer {self.token_admin1}"}
        )
        assert del_resp.status_code == 200

        db = TestSession()
        cred = db.query(models.AgentCredential).filter(models.AgentCredential.id == cred_id).first()
        assert cred.status == "REVOKED"
        assert cred.revoked_at is not None
        db.close()

    def test_expired_credential(self):
        """Verify authentication with an expired credential is rejected."""
        create_resp = client.post(
            f"/api/agents/{self.agent1_id}/credentials",
            headers={"Authorization": f"Bearer {self.token_admin1}"},
            json={"name": "Expiring Key"}
        )
        token = create_resp.json()["plaintext_token"]
        cred_id = create_resp.json()["credential"]["id"]

        # Manually backdate expiration in DB
        db = TestSession()
        cred = db.query(models.AgentCredential).filter(models.AgentCredential.id == cred_id).first()
        cred.expires_at = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        db.commit()
        db.close()

        auth_resp = client.post(
            "/api/runtime/auth",
            json={"credential": token, "agent_code": self.agent1_code}
        )
        assert auth_resp.status_code == 401
        assert "expired" in auth_resp.json()["detail"].lower()

    # ------------------------------------------------------------------------
    # 1.2 MACHINE AUTHENTICATION & JWT CLAIMS TESTS
    # ------------------------------------------------------------------------

    def test_machine_auth_success(self):
        """Verify valid machine credential authenticates and returns short-lived Machine JWT."""
        create_resp = client.post(
            f"/api/agents/{self.agent1_id}/credentials",
            headers={"Authorization": f"Bearer {self.token_admin1}"},
            json={"name": "Worker Key"}
        )
        token = create_resp.json()["plaintext_token"]

        auth_resp = client.post(
            "/api/runtime/auth",
            json={"credential": token, "agent_code": self.agent1_code}
        )
        assert auth_resp.status_code == 200
        auth_data = auth_resp.json()
        assert "access_token" in auth_data
        assert auth_data["token_type"] == "bearer"
        assert auth_data["agent_code"] == self.agent1_code
        assert auth_data["org_id"] == self.org1_id
        assert auth_data["expires_in"] == 3600

    def test_machine_auth_invalid_credential(self):
        """Verify fake/invalid credential is rejected with HTTP 401."""
        resp = client.post(
            "/api/runtime/auth",
            json={"credential": "ag_agent_invalid_forged_key_00000000", "agent_code": self.agent1_code}
        )
        assert resp.status_code == 401

    def test_machine_auth_revoked_agent(self):
        """Verify suspended agent cannot authenticate with machine credentials."""
        # Create key while un-suspended
        create_resp = client.post(
            f"/api/agents/{self.agent2_id}/credentials",
            headers={"Authorization": f"Bearer {self.token_admin2}"},
            json={"name": "Agent 2 Key"}
        )
        token2 = create_resp.json()["plaintext_token"]

        # Suspend agent 2
        db = TestSession()
        agent2 = db.query(models.Agent).filter(models.Agent.id == self.agent2_id).first()
        agent2.status = "SUSPENDED"
        db.commit()
        db.close()

        resp = client.post(
            "/api/runtime/auth",
            json={"credential": token2, "agent_code": self.agent2_code}
        )
        assert resp.status_code == 401
        assert "suspended" in resp.json()["detail"].lower()

        # Restore agent 2
        db = TestSession()
        agent2 = db.query(models.Agent).filter(models.Agent.id == self.agent2_id).first()
        agent2.status = "NORMAL"
        db.commit()
        db.close()

    def test_machine_jwt_claims(self):
        """Verify Machine JWT contains standard claims (sub, agent_code, org_id, token_type=machine)."""
        create_resp = client.post(
            f"/api/agents/{self.agent1_id}/credentials",
            headers={"Authorization": f"Bearer {self.token_admin1}"},
            json={"name": "Claims Key"}
        )
        token = create_resp.json()["plaintext_token"]

        auth_resp = client.post(
            "/api/runtime/auth",
            json={"credential": token}
        )
        machine_jwt = auth_resp.json()["access_token"]

        # Call /api/runtime/me
        me_resp = client.get(
            "/api/runtime/me",
            headers={"Authorization": f"Bearer {machine_jwt}"}
        )
        print("ME_RESP_DEBUG:", me_resp.status_code, me_resp.text)
        assert me_resp.status_code == 200, f"Failed: {me_resp.status_code} {me_resp.text}"
        me_data = me_resp.json()
        assert me_data["authenticated"] is True
        assert me_data["identity_type"] == "MACHINE_AGENT"
        assert me_data["agent_code"] == self.agent1_code
        assert me_data["org_id"] == self.org1_id
        assert me_data["passport"]["is_cryptographically_valid"] is True
        assert me_data["passport"]["algorithm"] == "Ed25519"

    def test_direct_agent_key_header_auth(self):
        """Verify an agent can authenticate directly using X-Agent-Code and X-Agent-Key headers."""
        create_resp = client.post(
            f"/api/agents/{self.agent1_id}/credentials",
            headers={"Authorization": f"Bearer {self.token_admin1}"},
            json={"name": "Direct Header Key"}
        )
        token = create_resp.json()["plaintext_token"]

        me_resp = client.get(
            "/api/runtime/me",
            headers={
                "X-Agent-Code": self.agent1_code,
                "X-Agent-Key": token
            }
        )
        assert me_resp.status_code == 200
        data = me_resp.json()
        assert data["agent_code"] == self.agent1_code
        assert data["auth_method"] == "AGENT_KEY"

    def test_runtime_heartbeat(self):
        """Verify agent can send liveness heartbeats."""
        create_resp = client.post(
            f"/api/agents/{self.agent1_id}/credentials",
            headers={"Authorization": f"Bearer {self.token_admin1}"},
            json={"name": "Heartbeat Key"}
        )
        token = create_resp.json()["plaintext_token"]
        auth_resp = client.post("/api/runtime/auth", json={"credential": token})
        jwt_token = auth_resp.json()["access_token"]

        hb_resp = client.post(
            "/api/runtime/heartbeat",
            headers={"Authorization": f"Bearer {jwt_token}"},
            json={"metadata": {"memory_mb": 256}}
        )
        assert hb_resp.status_code == 200
        assert hb_resp.json()["status"] == "HEALTHY"
        assert hb_resp.json()["session_active"] is True

    # ------------------------------------------------------------------------
    # 1.4 & 1.5 PASSPORT SIGNING & VERIFICATION TESTS
    # ------------------------------------------------------------------------

    def test_passport_signing(self):
        """Verify passport is signed with Ed25519 digital signature."""
        resp = client.get(
            f"/api/agents/{self.agent1_id}/passport",
            headers={"Authorization": f"Bearer {self.token_admin1}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        passport = data["passport"]
        assert passport["digital_signature"].startswith("ed25519:")
        assert passport["verification_status"] == "VERIFIED"

    def test_passport_verification(self):
        """Verify GET /api/agents/{id}/passport/verify confirms cryptographic validity."""
        resp = client.get(
            f"/api/agents/{self.agent1_id}/passport/verify",
            headers={"Authorization": f"Bearer {self.token_admin1}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["status"] == "VERIFIED"
        assert data["algorithm"] == "Ed25519"

    def test_tampered_passport(self):
        """Verify that altering passport signature or canonical agent data fails verification."""
        db = TestSession()
        passport = db.query(models.AgentPassport).filter(models.AgentPassport.agent_id == self.agent1_id).first()
        original_sig = passport.digital_signature

        # Tamper with the signature
        passport.digital_signature = "ed25519:dGFtcGVyZWRzaWduYXR1cmVmb3JhdWRpdDEyMzQ1Njc4OQ=="
        db.commit()

        resp = client.get(
            f"/api/agents/{self.agent1_id}/passport/verify",
            headers={"Authorization": f"Bearer {self.token_admin1}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert data["status"] == "TAMPERED"

        # Restore original signature
        passport.digital_signature = original_sig
        db.commit()
        db.close()

    def test_expired_passport(self):
        """Verify that an expired passport is flagged as EXPIRED upon verification."""
        db = TestSession()
        passport = db.query(models.AgentPassport).filter(models.AgentPassport.agent_id == self.agent1_id).first()
        original_exp = passport.expires_at

        passport.expires_at = datetime.datetime.utcnow() - datetime.timedelta(days=2)
        db.commit()

        resp = client.get(
            f"/api/agents/{self.agent1_id}/passport/verify",
            headers={"Authorization": f"Bearer {self.token_admin1}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert data["status"] == "EXPIRED"

        # Restore original expiration
        passport.expires_at = original_exp
        passport.verification_status = "VERIFIED"
        db.commit()
        db.close()

    def test_cross_tenant_machine_auth(self):
        """Verify machine tokens from Org 1 cannot be used to impersonate Org 2 agents."""
        create_resp = client.post(
            f"/api/agents/{self.agent1_id}/credentials",
            headers={"Authorization": f"Bearer {self.token_admin1}"},
            json={"name": "Org 1 Key"}
        )
        token1 = create_resp.json()["plaintext_token"]
        auth_resp = client.post("/api/runtime/auth", json={"credential": token1})
        jwt_token1 = auth_resp.json()["access_token"]

        # Attempt to use credential 1 with Org 2 agent code
        cross_auth = client.post(
            "/api/runtime/auth",
            json={"credential": token1, "agent_code": self.agent2_code}
        )
        assert cross_auth.status_code == 401
        assert "does not match" in cross_auth.json()["detail"].lower()
