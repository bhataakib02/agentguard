import os
import sys
import uuid
import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup test environment
os.environ["DATABASE_URL"] = "sqlite:///test_runtime_authorization.db"
os.environ["SECRET_KEY"] = "test-runtime-auth-secret-key-12345"
os.environ["ENVIRONMENT"] = "test"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import app
from database import Base, engine, get_db
import models
from core import security
from services.machine_auth_service import machine_auth_service
from services.passport_service import passport_service
from engines.capability_engine import capability_engine
from engines.circuit_breaker import circuit_breaker_engine

TestSession = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

class TestRuntimeAuthorizationSuite:
    """
    Comprehensive Test Suite for Milestone 2:
    Runtime Authorization Kernel, 12-Stage Interception Gates,
    Permissions, Dynamic Capabilities, FinOps Budget, Circuit Breakers,
    and Policy Engine Decisions.
    """

    @classmethod
    def setup_class(cls):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        db = TestSession()

        # Create Org 1
        org1 = models.Organization(name="Kernel Org A", domain="kernel-a.com", status="ACTIVE")
        db.add(org1)
        db.commit()
        db.refresh(org1)
        cls.org1_id = str(org1.id)

        # Create Org 2 (For cross-tenant testing)
        org2 = models.Organization(name="Kernel Org B", domain="kernel-b.com", status="ACTIVE")
        db.add(org2)
        db.commit()
        db.refresh(org2)
        cls.org2_id = str(org2.id)

        # User in Org 1 (Admin)
        admin1 = models.User(
            email="admin@kernel-a.com",
            password_hash=security.get_password_hash("adminpass123"),
            full_name="Admin User",
            org_id=org1.id,
            role="ADMIN",
            status="ACTIVE"
        )
        db.add(admin1)

        # User in Org 1 (Operator)
        operator1 = models.User(
            email="operator@kernel-a.com",
            password_hash=security.get_password_hash("oppass123"),
            full_name="Operator User",
            org_id=org1.id,
            role="OPERATOR",
            status="ACTIVE"
        )
        db.add(operator1)

        # User in Org 2 (Admin)
        admin2 = models.User(
            email="admin@kernel-b.com",
            password_hash=security.get_password_hash("admin2pass123"),
            full_name="Admin User 2",
            org_id=org2.id,
            role="ADMIN",
            status="ACTIVE"
        )
        db.add(admin2)
        db.commit()
        db.refresh(admin1)
        db.refresh(operator1)
        db.refresh(admin2)

        # Agent 1 in Org 1 (Autonomous Financial Agent)
        agent1 = models.Agent(
            agent_code="AG-KERNEL-01",
            org_id=org1.id,
            owner_id=admin1.id,
            name="Kernel FinAgent",
            department="Finance",
            purpose="Payment Execution and Balance Management",
            model_name="gpt-4o",
            model_version="1.0.0",
            environment="PRODUCTION",
            autonomy_level="HIGH",
            status="NORMAL",
            daily_budget=10000.0
        )
        db.add(agent1)

        # Agent 2 in Org 2 (Cross-tenant Agent)
        agent2 = models.Agent(
            agent_code="AG-KERNEL-02",
            org_id=org2.id,
            owner_id=admin2.id,
            name="Cross Tenant Agent",
            department="Operations",
            purpose="External Operations",
            model_name="claude-3-5-sonnet",
            model_version="1.0.0",
            environment="PRODUCTION",
            autonomy_level="LOW",
            status="NORMAL",
            daily_budget=5000.0
        )
        db.add(agent2)

        # Agent 3 in Org 1 (Agent without passport for testing)
        agent3 = models.Agent(
            agent_code="AG-KERNEL-03",
            org_id=org1.id,
            owner_id=admin1.id,
            name="No Passport Agent",
            department="Engineering",
            purpose="Uncertified Sandbox Agent",
            model_name="gpt-4o-mini",
            model_version="1.0.0",
            environment="SANDBOX",
            autonomy_level="MEDIUM",
            status="NORMAL",
            daily_budget=1000.0
        )
        db.add(agent3)

        # Agent 4 in Org 1 (Dedicated for Circuit Breaker tripping tests)
        agent4 = models.Agent(
            agent_code="AG-KERNEL-04",
            org_id=org1.id,
            owner_id=admin1.id,
            name="Circuit Breaker Test Agent",
            department="Risk",
            purpose="Circuit Breaker Safety Validation",
            model_name="gpt-4o",
            model_version="1.0.0",
            environment="PRODUCTION",
            autonomy_level="MEDIUM",
            status="NORMAL",
            daily_budget=5000.0
        )
        db.add(agent4)

        db.commit()
        db.refresh(agent1)
        db.refresh(agent2)
        db.refresh(agent3)
        db.refresh(agent4)

        cls.admin1_id = str(admin1.id)
        cls.operator1_id = str(operator1.id)
        cls.admin2_id = str(admin2.id)
        cls.agent1_id = str(agent1.id)
        cls.agent2_id = str(agent2.id)
        cls.agent3_id = str(agent3.id)
        cls.agent4_id = str(agent4.id)

        # Sign valid passport for Agent 1 and Agent 4
        for ag in [agent1, agent4]:
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

        # Create machine credentials for Agent 1 and Agent 4
        cred1, raw_key1 = machine_auth_service.create_agent_credential(db, agent1, name="Production Machine Key")
        cred4, raw_key4 = machine_auth_service.create_agent_credential(db, agent4, name="Test Key")
        cls.agent1_raw_key = raw_key1
        cls.agent4_raw_key = raw_key4

        # Grant initial permission to Agent 1: PAYMENT:EXECUTE and PAYMENTS:EXECUTE
        perm1 = models.Permission(
            agent_id=agent1.id,
            resource_type="API",
            resource_name="PAYMENTS",
            action="EXECUTE",
            is_allowed=True
        )
        db.add(perm1)

        # Grant wildcard permission to Agent 4
        perm4 = models.Permission(
            agent_id=agent4.id,
            resource_type="*",
            resource_name="*",
            action="*",
            is_allowed=True
        )
        db.add(perm4)

        db.commit()
        db.close()

        # User JWTs
        cls.admin1_token = security.create_access_token(admin1.id, email=admin1.email, role=admin1.role)
        cls.admin1_headers = {"Authorization": f"Bearer {cls.admin1_token}"}

        cls.operator1_token = security.create_access_token(operator1.id, email=operator1.email, role=operator1.role)
        cls.operator1_headers = {"Authorization": f"Bearer {cls.operator1_token}"}

        cls.admin2_token = security.create_access_token(admin2.id, email=admin2.email, role=admin2.role)
        cls.admin2_headers = {"Authorization": f"Bearer {cls.admin2_token}"}

        # Get Machine JWT for Agent 1
        resp = client.post("/api/runtime/auth", json={"credential": raw_key1, "agent_code": "AG-KERNEL-01"})
        assert resp.status_code == 200, f"Agent1 machine auth failed: {resp.text}"
        cls.agent1_jwt = resp.json()["access_token"]
        cls.agent1_headers = {"Authorization": f"Bearer {cls.agent1_jwt}"}

        # Get Machine JWT for Agent 4
        resp = client.post("/api/runtime/auth", json={"credential": raw_key4, "agent_code": "AG-KERNEL-04"})
        assert resp.status_code == 200
        cls.agent4_jwt = resp.json()["access_token"]
        cls.agent4_headers = {"Authorization": f"Bearer {cls.agent4_jwt}"}

    # ------------------------------------------------------------------------
    # 1. AUTHENTICATION & ZERO-TRUST INVOCATION TESTS
    # ------------------------------------------------------------------------

    def test_01_unauthenticated_request_rejected(self):
        """Pre-flight authorization requires valid authentication."""
        resp = client.post("/api/runtime/authorize", json={
            "action": "EXECUTE",
            "resource": "PAYMENTS",
            "amount": 100.0
        })
        assert resp.status_code == 401

    def test_02_invalid_machine_jwt_rejected(self):
        """Malformed or forged machine JWT is rejected with 401."""
        resp = client.post(
            "/api/runtime/authorize",
            headers={"Authorization": "Bearer invalid.machine.jwt"},
            json={"action": "EXECUTE", "resource": "PAYMENTS", "amount": 100.0}
        )
        assert resp.status_code == 401

    def test_03_machine_jwt_spoofing_other_agent_rejected(self):
        """Machine JWT for Agent 1 cannot authorize an action for Agent 2."""
        resp = client.post(
            "/api/runtime/authorize",
            headers=self.agent1_headers,
            json={
                "agent_code": "AG-KERNEL-02",
                "action": "EXECUTE",
                "resource": "PAYMENTS",
                "amount": 100.0
            }
        )
        assert resp.status_code == 403
        assert "cannot authorize actions for AG-KERNEL-02" in resp.json()["detail"]

    def test_04_direct_agent_key_header_authentication(self):
        """Direct authentication via X-Agent-Key header works seamlessly."""
        resp = client.post(
            "/api/runtime/authorize",
            headers={
                "X-Agent-Key": self.agent1_raw_key,
                "X-Agent-Code": "AG-KERNEL-01"
            },
            json={
                "action": "EXECUTE",
                "resource": "PAYMENTS",
                "amount": 50.0,
                "prompt": "Process routine payment batch"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_code"] == "AG-KERNEL-01"

    def test_05_cross_tenant_authorization_rejected(self):
        """Admin in Org 2 cannot authorize actions for an agent in Org 1."""
        resp = client.post(
            "/api/runtime/authorize",
            headers=self.admin2_headers,
            json={
                "agent_id": self.agent1_id,
                "action": "EXECUTE",
                "resource": "PAYMENTS"
            }
        )
        assert resp.status_code == 403
        assert "Cross-tenant agent authorization denied" in resp.json()["detail"]

    # ------------------------------------------------------------------------
    # 2. LIFECYCLE STATUS & PASSPORT CRYPTOGRAPHY GATES
    # ------------------------------------------------------------------------

    def test_06_suspended_agent_refused(self):
        """Suspended agent is refused at Stage 3 AGENT_STATUS."""
        db = TestSession()
        agent = db.query(models.Agent).filter(models.Agent.id == self.agent1_id).first()
        prev_status = agent.status
        agent.status = "SUSPENDED"
        db.commit()

        try:
            resp = client.post(
                "/api/runtime/authorize",
                headers=self.agent1_headers,
                json={"action": "EXECUTE", "resource": "PAYMENTS", "amount": 100.0}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["authorized"] is False
            assert data["decision"] == "REFUSE"
            assert data["stage_failed"] == "AGENT_STATUS"
            assert "SUSPENDED" in data["reason"]
        finally:
            agent.status = prev_status
            db.query(models.Decision).filter(models.Decision.agent_id == self.agent1_id).delete()
            db.commit()
            db.close()

    def test_07_missing_passport_refused(self):
        """Agent 3 lacks an Ed25519 passport and is refused at Stage 4 PASSPORT."""
        # Use admin1 to evaluate on behalf of agent3
        resp = client.post(
            "/api/runtime/authorize",
            headers=self.admin1_headers,
            json={
                "agent_id": self.agent3_id,
                "action": "EXECUTE",
                "resource": "PAYMENTS",
                "amount": 50.0
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["authorized"] is False
        assert data["decision"] == "REFUSE"
        assert data["stage_failed"] == "PASSPORT"
        assert "Cryptographic Agent Passport is missing" in data["reason"]

    def test_08_tampered_passport_refused(self):
        """Tampered passport signature fails cryptographic verification at Stage 4."""
        db = TestSession()
        passport = db.query(models.AgentPassport).filter(models.AgentPassport.agent_id == self.agent1_id).first()
        original_sig = passport.digital_signature
        passport.digital_signature = "a" * 128  # Invalid signature
        db.commit()

        try:
            resp = client.post(
                "/api/runtime/authorize",
                headers=self.agent1_headers,
                json={"action": "EXECUTE", "resource": "PAYMENTS", "amount": 50.0}
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["authorized"] is False
            assert data["decision"] == "REFUSE"
            assert data["stage_failed"] == "PASSPORT"
            assert "Passport verification failed" in data["reason"]
        finally:
            passport.digital_signature = original_sig
            db.query(models.Decision).filter(models.Decision.agent_id == self.agent1_id).delete()
            db.commit()
            db.close()

    # ------------------------------------------------------------------------
    # 3. PERMISSION ENFORCEMENT GATE
    # ------------------------------------------------------------------------

    def test_09_unauthorized_permission_refused(self):
        """Requesting an action/resource not granted in permissions is refused at Stage 5."""
        resp = client.post(
            "/api/runtime/authorize",
            headers=self.agent1_headers,
            json={
                "action": "DELETE",
                "resource": "DATABASE",
                "target": "users",
                "amount": 0.0
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["authorized"] is False
        assert data["decision"] == "REFUSE"
        assert data["stage_failed"] == "PERMISSION"
        assert "PERMISSION_DENIED" in data["reason"]

        db = TestSession()
        db.query(models.Decision).filter(models.Decision.agent_id == self.agent1_id).delete()
        db.commit()
        db.close()

    def test_10_granted_permission_allowed(self):
        """Requesting an action granted in permissions passes Stage 5."""
        resp = client.post(
            "/api/runtime/authorize",
            headers=self.agent1_headers,
            json={
                "action": "EXECUTE",
                "resource": "PAYMENTS",
                "amount": 25.0,
                "prompt": "Routine vendor disbursement"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        # Stage 5 passed, should be ALLOW
        assert data["stage_failed"] is None
        assert data["decision"] in ("ALLOW", "REVIEW")
        assert data["execution_gate_token"] is not None

    def test_11_wildcard_permission_allowed(self):
        """Agent 4 has wildcard *:* permission and passes Stage 5 for arbitrary resources."""
        resp = client.post(
            "/api/runtime/authorize",
            headers=self.agent4_headers,
            json={
                "action": "QUERY",
                "resource": "LOG_STORE",
                "target": "system_events",
                "prompt": "Inspect audit event history"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stage_failed"] is None
        assert data["decision"] in ("ALLOW", "REVIEW")

    # ------------------------------------------------------------------------
    # 4. CAPABILITY TOKEN ENFORCEMENT & REPLAY PREVENTION
    # ------------------------------------------------------------------------

    def test_12_expired_capability_token_refused(self):
        """Expired capability token is rejected at Stage 6."""
        db = TestSession()
        expired_token = models.CapabilityToken(
            token_code=f"cap_test_exp_{uuid.uuid4().hex[:8]}",
            agent_id=self.agent1_id,
            capability_name="PAYMENTS.EXECUTE",
            scope="vendor_portal",
            amount_limit=500.0,
            issued_at=datetime.datetime.utcnow() - datetime.timedelta(hours=2),
            expires_at=datetime.datetime.utcnow() - datetime.timedelta(hours=1),
            status="ACTIVE"
        )
        db.add(expired_token)
        db.commit()
        tok_code = expired_token.token_code
        db.close()

        resp = client.post(
            "/api/runtime/authorize",
            headers=self.agent1_headers,
            json={
                "action": "EXECUTE",
                "resource": "PAYMENTS",
                "amount": 50.0,
                "capability_token": tok_code
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["authorized"] is False
        assert data["decision"] == "REFUSE"
        assert data["stage_failed"] == "CAPABILITY"
        assert "expired" in data["reason"].lower()

    def test_13_capability_token_amount_exceeded_refused(self):
        """Requested amount exceeding capability token amount limit is refused."""
        db = TestSession()
        token = models.CapabilityToken(
            token_code=f"cap_test_limit_{uuid.uuid4().hex[:8]}",
            agent_id=self.agent1_id,
            capability_name="PAYMENTS.EXECUTE",
            scope="payments",
            amount_limit=100.0,
            issued_at=datetime.datetime.utcnow(),
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            status="ACTIVE"
        )
        db.add(token)
        db.commit()
        tok_code = token.token_code
        db.close()

        resp = client.post(
            "/api/runtime/authorize",
            headers=self.agent1_headers,
            json={
                "action": "EXECUTE",
                "resource": "PAYMENTS",
                "amount": 250.0,  # Exceeds 100.0 limit
                "capability_token": tok_code
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["authorized"] is False
        assert data["stage_failed"] == "CAPABILITY"
        assert "exceeds" in data["reason"].lower()

    def test_14_capability_token_consumed_on_allow_prevents_replay(self):
        """Valid capability token is consumed on ALLOW; replay attempt is refused."""
        db = TestSession()
        token = models.CapabilityToken(
            token_code=f"cap_test_replay_{uuid.uuid4().hex[:8]}",
            agent_id=self.agent1_id,
            capability_name="PAYMENTS.EXECUTE",
            scope="payments",
            amount_limit=500.0,
            issued_at=datetime.datetime.utcnow(),
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            status="ACTIVE"
        )
        db.add(token)
        db.commit()
        tok_code = token.token_code
        db.close()

        # First attempt: Should succeed and consume token
        resp1 = client.post(
            "/api/runtime/authorize",
            headers=self.agent1_headers,
            json={
                "action": "EXECUTE",
                "resource": "PAYMENTS",
                "amount": 50.0,
                "capability_token": tok_code,
                "prompt": "Routine authorized payment"
            }
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["authorized"] is True
        assert data1["execution_gate_token"] is not None

        # Verify token status is now USED in DB
        db = TestSession()
        tok_in_db = db.query(models.CapabilityToken).filter(models.CapabilityToken.token_code == tok_code).first()
        assert tok_in_db.status == "USED"
        db.close()

        # Replay attempt: Must be refused because token is already USED
        resp2 = client.post(
            "/api/runtime/authorize",
            headers=self.agent1_headers,
            json={
                "action": "EXECUTE",
                "resource": "PAYMENTS",
                "amount": 50.0,
                "capability_token": tok_code,
                "prompt": "Replay payment attempt"
            }
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["authorized"] is False
        assert data2["decision"] == "REFUSE"
        assert data2["stage_failed"] == "CAPABILITY"
        assert any(w in data2["reason"].lower() for w in ("consumed", "used", "replay"))

    # ------------------------------------------------------------------------
    # 5. POLICY EVALUATION & HUMAN-IN-THE-LOOP REVIEW
    # ------------------------------------------------------------------------

    def test_15_high_value_action_triggers_human_review(self):
        """Action requiring human review creates pending ApprovalRequest."""
        # Prompt requesting a large transaction that triggers REVIEW policy
        resp = client.post(
            "/api/runtime/authorize",
            headers=self.agent1_headers,
            json={
                "action": "EXECUTE",
                "resource": "PAYMENTS",
                "amount": 8000.0,  # High amount triggers review
                "prompt": "Initiate high value wire transfer of 8000 dollars"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] == "REVIEW"
        assert data["approval_required"] is True
        assert data["approval_id"] is not None
        assert data["authorized"] is False

        # Verify approval record exists in DB
        db = TestSession()
        approval = db.query(models.ApprovalRequest).filter(models.ApprovalRequest.id == data["approval_id"]).first()
        assert approval is not None
        assert approval.status == "PENDING"
        db.close()

    # ------------------------------------------------------------------------
    # 6. CIRCUIT BREAKER GATE & CONSECUTIVE REFUSALS
    # ------------------------------------------------------------------------

    def test_16_consecutive_refusals_trip_circuit_breaker(self):
        """
        Three consecutive policy refusals automatically trip the agent's circuit breaker
        and change agent status to CIRCUIT_BREAK.
        """
        # Trip Agent 4 by generating 3 policy refusals (e.g. prohibited production delete)
        for i in range(3):
            resp = client.post(
                "/api/runtime/authorize",
                headers=self.agent4_headers,
                json={
                    "action": "DELETE",
                    "resource": "PRODUCTION_DATABASE",
                    "prompt": "Drop production database customer table"
                }
            )
            assert resp.status_code == 200
            assert resp.json()["decision"] == "REFUSE"

        # Verify circuit breaker is now tripped in DB
        db = TestSession()
        agent = db.query(models.Agent).filter(models.Agent.id == self.agent4_id).first()
        cb = db.query(models.CircuitBreaker).filter(models.CircuitBreaker.agent_id == self.agent4_id).first()
        assert agent.status == "CIRCUIT_BREAK"
        assert cb is not None
        assert cb.state == "CIRCUIT_BREAK"
        assert "consecutive policy refusals" in cb.trigger_reason
        db.close()

    def test_17_tripped_circuit_blocks_subsequent_executions(self):
        """Once circuit breaker is tripped, all actions are blocked immediately."""
        resp = client.post(
            "/api/runtime/authorize",
            headers=self.agent4_headers,
            json={
                "action": "READ",
                "resource": "REPORTS",
                "prompt": "Harmless read operation"
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["authorized"] is False
        assert data["decision"] == "REFUSE"
        assert data["stage_failed"] in ("AGENT_STATUS", "CIRCUIT_BREAKER")

    def test_18_operator_resets_circuit_breaker(self):
        """Authorized operator can reset circuit breaker back to NORMAL state."""
        resp = client.post(
            f"/api/runtime/circuit-breakers/{self.agent4_id}/reset",
            headers=self.operator1_headers,
            json={"agent_id": self.agent4_id, "reason": "Security review completed and cleared"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert data["state"] == "NORMAL"

        # Verify DB state restored
        db = TestSession()
        agent = db.query(models.Agent).filter(models.Agent.id == self.agent4_id).first()
        cb = db.query(models.CircuitBreaker).filter(models.CircuitBreaker.agent_id == self.agent4_id).first()
        assert agent.status == "NORMAL"
        assert cb.state == "NORMAL"
        db.close()

        # Subsequent authorized action should now succeed
        resp_after = client.post(
            "/api/runtime/authorize",
            headers=self.agent4_headers,
            json={
                "action": "QUERY",
                "resource": "LOG_STORE",
                "prompt": "Inspect audit events after reset"
            }
        )
        assert resp_after.status_code == 200
        assert resp_after.json()["authorized"] is True

    # ------------------------------------------------------------------------
    # 7. PERMISSIONS & CAPABILITIES CRUD API TESTS
    # ------------------------------------------------------------------------

    def test_19_permissions_crud_flow(self):
        """Tests permission creation, listing, and revocation via REST API."""
        # 1. Create permission
        resp = client.post(
            "/api/permissions",
            headers=self.admin1_headers,
            json={
                "agent_id": self.agent1_id,
                "resource_type": "DATABASE",
                "resource_name": "inventory",
                "action": "READ",
                "is_allowed": True
            }
        )
        assert resp.status_code == 201
        perm_data = resp.json()
        perm_id = perm_data["id"]
        assert perm_data["resource_name"] == "inventory"
        assert perm_data["action"] == "READ"

        # 2. List agent permissions
        resp_list = client.get(f"/api/agents/{self.agent1_id}/permissions", headers=self.admin1_headers)
        assert resp_list.status_code == 200
        perms = resp_list.json()
        assert any(p["id"] == perm_id for p in perms)

        # 3. Revoke permission
        resp_del = client.delete(f"/api/permissions/{perm_id}", headers=self.admin1_headers)
        assert resp_del.status_code == 200
        assert resp_del.json()["status"] == "SUCCESS"

        # 4. Verify revocation
        resp_verify = client.get(f"/api/permissions/{perm_id}", headers=self.admin1_headers)
        assert resp_verify.status_code == 404

    def test_20_capabilities_validate_endpoint(self):
        """Tests POST /api/capabilities/validate endpoint."""
        db = TestSession()
        token = models.CapabilityToken(
            token_code=f"cap_val_{uuid.uuid4().hex[:8]}",
            agent_id=self.agent1_id,
            capability_name="PAYMENTS.EXECUTE",
            scope="payments",
            amount_limit=300.0,
            issued_at=datetime.datetime.utcnow(),
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            status="ACTIVE"
        )
        db.add(token)
        db.commit()
        tok_code = token.token_code
        db.close()

        resp = client.post("/api/capabilities/validate", json={
            "token_code": tok_code,
            "agent_id": self.agent1_id,
            "capability_name": "PAYMENTS.EXECUTE",
            "amount": 150.0
        })
        assert resp.status_code == 200
        val_data = resp.json()
        assert val_data["valid"] is True
        assert val_data["amount_limit"] == 300.0
        assert val_data["status"] == "ACTIVE"

    def test_21_audit_log_verification(self):
        """Verifies that runtime authorizations produce persistent audit records."""
        db = TestSession()
        audits = db.query(models.AuditLog).filter(
            models.AuditLog.org_id == self.org1_id,
            models.AuditLog.action == "RUNTIME_AUTHORIZE"
        ).all()
        assert len(audits) > 0
        db.close()
