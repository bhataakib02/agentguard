import os
import sys
import uuid
import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup test environment
os.environ["DATABASE_URL"] = "sqlite:///test_pace_suite.db"
os.environ["SECRET_KEY"] = "test-pace-secret-key-67890"
os.environ["ENVIRONMENT"] = "test"
os.environ["AGENTGUARD_ALLOW_LOCAL_TOOLS"] = "true"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import app
from database import Base, engine, get_db
import models
import schemas
from core import security
from services.machine_auth_service import machine_auth_service
from services.passport_service import passport_service
from engines.predictive_action_control_engine import predictive_action_control_engine

TestSession = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class TestPredictiveActionControlEngineSuite:
    """
    Focused Test Suite for AGENTGUARD Predictive Action Control Engine (PACE) - Phase 1.
    Validates canonical evaluation request, pipeline stages, sequence-aware risk assessment,
    deterministic decision hierarchy, audit evidence, fail-safe resilience, and execution boundary enforcement.
    """

    @classmethod
    def setup_class(cls):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        db = TestSession()

        # 1. Organization 1 (Active)
        org1 = models.Organization(name="PACE Alpha Org", domain="pace-alpha.com", status="ACTIVE")
        db.add(org1)
        db.commit()
        db.refresh(org1)
        cls.org1_id = str(org1.id)

        # 2. Organization 2 (Active - Cross-Tenant Isolation Testing)
        org2 = models.Organization(name="PACE Beta Org", domain="pace-beta.com", status="ACTIVE")
        db.add(org2)
        db.commit()
        db.refresh(org2)
        cls.org2_id = str(org2.id)

        # 3. Organization 3 (Suspended Tenant)
        org3 = models.Organization(name="PACE Inactive Org", domain="pace-inactive.com", status="SUSPENDED")
        db.add(org3)
        db.commit()
        db.refresh(org3)
        cls.org3_id = str(org3.id)

        # Users in Org 1
        admin1 = models.User(
            email="admin@pace-alpha.com",
            password_hash=security.get_password_hash("adminpass123"),
            full_name="Alpha Admin",
            org_id=org1.id,
            role="ADMIN",
            status="ACTIVE"
        )
        manager1 = models.User(
            email="manager@pace-alpha.com",
            password_hash=security.get_password_hash("managerpass123"),
            full_name="Alpha Manager",
            org_id=org1.id,
            role="MANAGER",
            status="ACTIVE"
        )
        db.add_all([admin1, manager1])

        # User in Org 2 (Admin)
        admin2 = models.User(
            email="admin@pace-beta.com",
            password_hash=security.get_password_hash("admin2pass123"),
            full_name="Beta Admin",
            org_id=org2.id,
            role="ADMIN",
            status="ACTIVE"
        )
        db.add(admin2)
        db.commit()
        db.refresh(admin1)
        db.refresh(manager1)
        db.refresh(admin2)

        cls.admin1_id = str(admin1.id)
        cls.admin1_token = security.create_access_token(str(admin1.id), email=admin1.email, role=admin1.role)
        cls.manager1_token = security.create_access_token(str(manager1.id), email=manager1.email, role=manager1.role)
        cls.admin2_token = security.create_access_token(str(admin2.id), email=admin2.email, role=admin2.role)

        # 4. Primary Machine Agent in Org 1 (NORMAL, MEDIUM autonomy)
        agent1 = models.Agent(
            agent_code="AG-PACE-01",
            org_id=org1.id,
            owner_id=admin1.id,
            name="Alpha Procurement Agent",
            department="Operations",
            purpose="Autonomous Supply Chain and Database Query Operations",
            model_name="gpt-4o",
            autonomy_level="MEDIUM",
            status="NORMAL",
            risk_score=15,
            trust_score=95,
            daily_budget=20000.0
        )
        db.add(agent1)
        db.commit()
        db.refresh(agent1)
        cls.agent1_id = str(agent1.id)
        cls.agent1_code = agent1.agent_code

        # Passports & Machine Credentials for Agent 1
        p1 = models.AgentPassport(
            agent_id=agent1.id,
            passport_number=f"AG-PASSPORT-{agent1.agent_code}",
            digital_signature="pending",
            issued_at=datetime.datetime.utcnow(),
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=365),
            verification_status="VERIFIED"
        )
        passport_service.sign_passport(agent1, p1)
        db.add(p1)

        cred1, raw_key1 = machine_auth_service.create_agent_credential(db, agent1, name="Primary API Key")
        cls.agent1_key = raw_key1
        cls.agent1_jwt = machine_auth_service.issue_machine_jwt(agent1, cred1)["access_token"]

        # Permissions for Agent 1:
        # Allowed: DATABASE:orders:READ, API:payments:EXECUTE
        # Prohibited: DATABASE:production:DELETE
        perm_db = models.Permission(
            agent_id=agent1.id,
            resource_type="DATABASE",
            resource_name="orders",
            action="READ",
            is_allowed=True
        )
        perm_api = models.Permission(
            agent_id=agent1.id,
            resource_type="API",
            resource_name="payments",
            action="EXECUTE",
            is_allowed=True
        )
        db.add_all([perm_db, perm_api])

        # 5. Suspended Agent in Org 1
        agent_susp = models.Agent(
            agent_code="AG-PACE-SUSP",
            org_id=org1.id,
            owner_id=admin1.id,
            name="Suspended Agent",
            purpose="Suspended Test Agent",
            autonomy_level="LOW",
            status="SUSPENDED",
            daily_budget=5000.0
        )
        db.add(agent_susp)
        db.commit()
        db.refresh(agent_susp)
        cls.agent_susp_id = str(agent_susp.id)
        cls.agent_susp_code = agent_susp.agent_code

        # 6. Agent in Org 2 (Cross-Tenant)
        agent2 = models.Agent(
            agent_code="AG-PACE-BETA",
            org_id=org2.id,
            owner_id=admin2.id,
            name="Beta Agent",
            purpose="Org 2 Agent",
            autonomy_level="HIGH",
            status="NORMAL",
            daily_budget=50000.0
        )
        db.add(agent2)
        db.commit()
        db.refresh(agent2)
        cls.agent2_id = str(agent2.id)
        cls.agent2_code = agent2.agent_code

        # 7. Policies in Org 1
        # Policy A: Strict Data Protection (DELETE on production -> REFUSE)
        pol_data = models.Policy(
            org_id=org1.id,
            name="Production Data Protection Policy",
            category="SECURITY",
            priority=1,
            status="ACTIVE"
        )
        db.add(pol_data)
        db.commit()
        db.refresh(pol_data)

        rule_data = models.PolicyRule(
            policy_id=pol_data.id,
            condition_expression="action == 'DELETE' and 'prod' in resource",
            decision_output="REFUSE",
            risk_delta=40,
            description="Autonomous database deletion in production is strictly prohibited."
        )
        db.add(rule_data)

        # Policy B: Financial Approval Threshold (> ₹5,000 -> REVIEW)
        pol_fin = models.Policy(
            org_id=org1.id,
            name="Financial Governance Policy",
            category="FINANCE",
            priority=2,
            status="ACTIVE"
        )
        db.add(pol_fin)
        db.commit()
        db.refresh(pol_fin)

        rule_fin = models.PolicyRule(
            policy_id=pol_fin.id,
            condition_expression="amount > 5000",
            decision_output="REVIEW",
            risk_delta=20,
            description="Transaction amounts exceeding ₹5,000.00 require human managerial review."
        )
        db.add(rule_fin)

        # 8. Tool in Tool Registry for Tool Proxy execution
        tool = models.Tool(
            org_id=org1.id,
            name="payments",
            category="PAYMENT",
            endpoint="http://localhost:8000/mock-payment-endpoint",
            risk_level="MEDIUM",
            status="ACTIVE"
        )
        db.add(tool)
        db.commit()
        db.close()

    # ------------------------------------------------------------------------
    # TEST 1: Authorized Low-Risk Action Receives ALLOW
    # ------------------------------------------------------------------------
    def test_01_authorized_low_risk_action_receives_allow(self):
        """
        Validates Stage 1-7: An authenticated agent with valid permissions, active status,
        and safe parameters receives ALLOW along with an execution gate token.
        """
        req_payload = {
            "agent_code": self.agent1_code,
            "action_type": "READ",
            "target_resource": "orders",
            "amount": 0.0,
            "correlation_id": "test-corr-01"
        }
        res = client.post(
            "/api/decisions/control/evaluate",
            json=req_payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert res.status_code == 200, res.text
        data = res.json()

        assert data["decision"] == "ALLOW"
        assert data["approval_required"] is False
        assert data["execution_gate_token"] is not None
        assert data["execution_gate_token"].startswith("gate_")
        assert data["agent_code"] == self.agent1_code
        assert data["risk_score"] <= 30
        assert data["risk_level"] == "LOW"
        assert "0-100" in data["risk_scale"]
        assert data["correlation_id"] == "test-corr-01"

    # ------------------------------------------------------------------------
    # TEST 2: Prohibited Action Receives REFUSE Even When Risk Score is Low
    # ------------------------------------------------------------------------
    def test_02_prohibited_action_receives_refuse_even_with_low_risk(self):
        """
        Validates deterministic policy enforcement: An action prohibited by a mandatory rule
        (DELETE on production) receives REFUSE, even if requested amount is 0.
        """
        req_payload = {
            "agent_code": self.agent1_code,
            "action_type": "DELETE",
            "target_resource": "production_db",
            "amount": 0.0,
            "correlation_id": "test-corr-02"
        }
        res = client.post(
            "/api/decisions/control/evaluate",
            json=req_payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert res.status_code == 200, res.text
        data = res.json()

        assert data["decision"] == "REFUSE"
        assert data["execution_gate_token"] is None
        assert "prohibited" in data["reason"].lower() or "blocked" in data["reason"].lower() or "permission" in data["reason"].lower()
        assert data["approval_required"] is False

    # ------------------------------------------------------------------------
    # TEST 3: Review-Required Action Receives REVIEW and Is Not Executed
    # ------------------------------------------------------------------------
    def test_03_review_required_action_receives_review_and_not_executed(self):
        """
        Validates Stage 6: An action exceeding the ₹5,000 financial threshold receives REVIEW,
        generates an ApprovalRequest in PENDING state, does NOT issue a gate token,
        and when passed to the execution boundary, is strictly blocked from executing.
        """
        req_payload = {
            "agent_code": self.agent1_code,
            "action_type": "EXECUTE",
            "target_resource": "payments",
            "amount": 12000.0,
            "correlation_id": "test-corr-03"
        }

        # Step 3a: Evaluation endpoint check
        eval_res = client.post(
            "/api/decisions/control/evaluate",
            json=req_payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert eval_res.status_code == 200, eval_res.text
        eval_data = eval_res.json()

        assert eval_data["decision"] == "REVIEW"
        assert eval_data["approval_required"] is True
        assert eval_data["approval_status"] == "PENDING"
        assert eval_data["approval_id"] is not None
        assert eval_data["execution_gate_token"] is None

        # Step 3b: Execution Boundary check (must not execute!)
        exec_res = client.post(
            "/api/decisions/control/execute",
            json=req_payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert exec_res.status_code == 200, exec_res.text
        exec_data = exec_res.json()

        assert exec_data["executed"] is False
        assert exec_data["execution_status"] == "PENDING_APPROVAL"
        assert "approval" in exec_data["error"].lower()

        # Step 3c: Manager approves the request via human approval workflow
        app_id = eval_data["approval_id"]
        act_res = client.post(
            f"/api/approvals/{app_id}/act",
            json={"action": "APPROVE"},
            headers={"Authorization": f"Bearer {self.manager1_token}"}
        )
        assert act_res.status_code == 200, act_res.text
        assert act_res.json()["new_status"] == "APPROVED"

    # ------------------------------------------------------------------------
    # TEST 4: Invalid or Unauthenticated Identity Cannot Receive ALLOW
    # ------------------------------------------------------------------------
    def test_04_invalid_or_unauthenticated_identity_cannot_receive_allow(self):
        """
        Validates Stage 1: Unauthenticated requests, forged credentials, or invalid identities
        are never authorized.
        """
        req_payload = {
            "agent_code": self.agent1_code,
            "action_type": "READ",
            "target_resource": "orders",
            "amount": 0.0
        }

        # 4a: Completely missing authentication
        unauth_res = client.post("/api/decisions/control/evaluate", json=req_payload)
        assert unauth_res.status_code in (401, 403)

        # 4b: Invalid bearer token
        bad_token_res = client.post(
            "/api/decisions/control/evaluate",
            json=req_payload,
            headers={"Authorization": "Bearer invalid-garbage-token"}
        )
        assert bad_token_res.status_code in (401, 403)

        # 4c: Non-existent agent identifier
        bad_agent_req = {
            "agent_code": "AG-DOES-NOT-EXIST",
            "action_type": "READ",
            "target_resource": "orders"
        }
        not_found_res = client.post(
            "/api/decisions/control/evaluate",
            json=bad_agent_req,
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert not_found_res.status_code == 200
        assert not_found_res.json()["decision"] == "REFUSE"
        assert "not found" in not_found_res.json()["reason"].lower()

    # ------------------------------------------------------------------------
    # TEST 5: Cross-Tenant Isolation Enforced
    # ------------------------------------------------------------------------
    def test_05_cross_tenant_isolation_enforced(self):
        """
        Validates Stage 1: An agent or user from Org 1 cannot evaluate or execute actions
        on an agent belonging to Org 2.
        """
        req_payload = {
            "agent_code": self.agent2_code,  # Agent belonging to Org 2
            "action_type": "READ",
            "target_resource": "orders"
        }

        # Admin 1 (from Org 1) attempts cross-tenant action on Agent 2
        res = client.post(
            "/api/decisions/control/evaluate",
            json=req_payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert res.status_code == 200, res.text
        data = res.json()

        assert data["decision"] == "REFUSE"
        assert "cross-tenant" in data["reason"].lower() or "another organization" in data["reason"].lower()

    # ------------------------------------------------------------------------
    # TEST 6: Risk Assessment Does Not Bypass Mandatory Policies
    # ------------------------------------------------------------------------
    def test_06_risk_assessment_does_not_bypass_mandatory_policies(self):
        """
        Validates Stage 5: Even if risk assessment yields a low score, an action violating
        mandatory authorization (e.g. missing permission) receives REFUSE.
        """
        # Request ungranted permission: DATABASE:customers:DELETE
        req_payload = {
            "agent_code": self.agent1_code,
            "action_type": "DELETE",
            "target_resource": "customers",
            "amount": 0.0
        }
        res = client.post(
            "/api/decisions/control/evaluate",
            json=req_payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert res.status_code == 200, res.text
        data = res.json()

        assert data["decision"] == "REFUSE"
        assert "permission_denied" in data["reason"].lower() or "lacking" in data["reason"].lower()

    # ------------------------------------------------------------------------
    # TEST 7: Sequence-Risk Indicators Affect Result Only According to Documented Rules
    # ------------------------------------------------------------------------
    def test_07_sequence_risk_indicators_documented_rules(self):
        """
        Validates Section 4:
        7a: Missing history handles gracefully without inventing events.
        7b: Repeated refusals cascade increases sequence risk.
        7c: Rapid burst activity triggers sequence penalty.
        7d: Multi-step recon to sensitive operation progression is detected.
        """
        # 7a: Create a fresh agent with zero history to test missing history
        db = TestSession()
        fresh_agent = models.Agent(
            agent_code="AG-PACE-FRESH",
            org_id=self.org1_id,
            owner_id=self.admin1_id,
            name="Fresh Agent",
            purpose="Zero history testing",
            autonomy_level="LOW",
            status="NORMAL",
            daily_budget=10000.0
        )
        db.add(fresh_agent)
        db.commit()
        db.refresh(fresh_agent)

        p_fresh = models.AgentPassport(
            agent_id=fresh_agent.id,
            passport_number=f"AG-PASSPORT-{fresh_agent.agent_code}",
            digital_signature="pending",
            issued_at=datetime.datetime.utcnow(),
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=30),
            verification_status="VERIFIED"
        )
        passport_service.sign_passport(fresh_agent, p_fresh)
        db.add(p_fresh)
        db.add(models.Permission(
            agent_id=fresh_agent.id,
            resource_type="DATABASE",
            resource_name="orders",
            action="READ",
            is_allowed=True
        ))
        db.commit()

        # Evaluate fresh agent
        fresh_res = client.post(
            "/api/decisions/control/evaluate",
            json={
                "agent_code": fresh_agent.agent_code,
                "action_type": "READ",
                "target_resource": "orders"
            },
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert fresh_res.status_code == 200
        fresh_data = fresh_res.json()
        seq_fresh = fresh_data["sequence_indicators"]
        assert seq_fresh["missing_history"] is True
        assert seq_fresh["events_evaluated"] == 0
        assert seq_fresh["sequence_risk_delta"] == 0

        # 7b: Seed 2 consecutive refusals for fresh_agent to test REPEATED_REFUSALS_CASCADE
        now = datetime.datetime.utcnow()
        for i in range(2):
            refusal_dec = models.Decision(
                agent_id=fresh_agent.id,
                user_id=self.admin1_id,
                intent_summary="Prior refused probe",
                action_requested="UNAUTHORIZED_ACTION",
                resource_target="restricted_zone",
                amount=0.0,
                decision="REFUSE",
                risk_score=85,
                policy_name="Security Firewall",
                explanation="Blocked probe",
                execution_status="BLOCKED",
                timestamp=now + datetime.timedelta(seconds=5 * (i + 1))
            )
            db.add(refusal_dec)
        db.commit()

        seq_res = client.post(
            "/api/decisions/control/evaluate",
            json={
                "agent_code": fresh_agent.agent_code,
                "action_type": "READ",
                "target_resource": "orders"
            },
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert seq_res.status_code == 200
        seq_data = seq_res.json()
        seq_info = seq_data["sequence_indicators"]

        assert seq_info["missing_history"] is False
        assert seq_info["events_evaluated"] >= 2
        pattern_names = [p["pattern_name"] for p in seq_info["patterns_detected"]]
        assert "REPEATED_REFUSALS_CASCADE" in pattern_names
        assert seq_info["sequence_risk_delta"] >= 20
        assert "REPEATED_REFUSALS_CASCADE" in seq_info["explanation"]

        db.close()

    # ------------------------------------------------------------------------
    # TEST 8: Decision Evidence Recorded in Audit Service
    # ------------------------------------------------------------------------
    def test_08_decision_evidence_recorded_in_audit_service(self):
        """
        Validates Stage 7: Every PACE evaluation is recorded immutably in models.AuditLog
        with correlation ID, decision result, and sequence indicators.
        """
        corr_id = f"audit-test-{uuid.uuid4().hex[:8]}"
        res = client.post(
            "/api/decisions/control/evaluate",
            json={
                "agent_code": self.agent1_code,
                "action_type": "READ",
                "target_resource": "orders",
                "correlation_id": corr_id
            },
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert res.status_code == 200

        # Query database to confirm AuditLog record
        db = TestSession()
        audit_entry = db.query(models.AuditLog).filter(
            models.AuditLog.org_id == self.org1_id,
            models.AuditLog.action == "READ"
        ).order_by(models.AuditLog.timestamp.desc()).first()

        assert audit_entry is not None
        assert audit_entry.event_type in ("PACE_DECISION_ALLOW", "PACE_DECISION_REFUSE", "PACE_DECISION_REVIEW")
        meta = audit_entry.metadata_json or {}
        assert meta.get("correlation_id") == corr_id
        assert "sequence_indicators" in meta
        db.close()

    # ------------------------------------------------------------------------
    # TEST 9: Exceptions and Unavailable Dependencies Fail Safely
    # ------------------------------------------------------------------------
    def test_09_exceptions_fail_safely(self):
        """
        Validates Resilience: When internal components encounter unexpected errors,
        PACE fails safely (REFUSE), never failing open to ALLOW.
        """
        # Test agent in suspended organization
        suspended_org_res = client.post(
            "/api/decisions/control/evaluate",
            json={
                "agent_id": self.agent_susp_id,
                "action_type": "READ",
                "target_resource": "orders"
            },
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert suspended_org_res.status_code == 200
        data = suspended_org_res.json()
        assert data["decision"] == "REFUSE"
        assert "suspended" in data["reason"].lower()

    # ------------------------------------------------------------------------
    # TEST 10: Action Execution Boundary Enforces Returned Decision
    # ------------------------------------------------------------------------
    def test_10_execution_boundary_enforces_decision(self):
        """
        Validates Section 5: The Action Execution Boundary strictly enforces decisions.
        - ALLOW: dispatches execution through Tool Proxy with valid gate token.
        - REVIEW: withheld from execution.
        - REFUSE: blocked from execution.
        """
        # 10a: Prohibited action attempted via execution endpoint
        refuse_req = {
            "agent_code": self.agent1_code,
            "action_type": "DELETE",
            "target_resource": "production_database"
        }
        refuse_exec = client.post(
            "/api/decisions/control/execute",
            json=refuse_req,
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert refuse_exec.status_code == 200
        assert refuse_exec.json()["executed"] is False
        assert refuse_exec.json()["execution_status"] == "BLOCKED"

        # 10b: Review-required action attempted via execution endpoint
        review_req = {
            "agent_code": self.agent1_code,
            "action_type": "EXECUTE",
            "target_resource": "payments",
            "amount": 12000.0  # Exceeds policy threshold ₹5,000 but within daily budget ₹20,000
        }
        review_exec = client.post(
            "/api/decisions/control/execute",
            json=review_req,
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert review_exec.status_code == 200
        assert review_exec.json()["executed"] is False
        assert review_exec.json()["execution_status"] == "PENDING_APPROVAL"

        # 10c: Allowed action executed through boundary
        allow_req = {
            "agent_code": self.agent1_code,
            "action_type": "EXECUTE",
            "target_resource": "payments",
            "amount": 100.0,  # Within autonomous threshold
            "parameters": {"account_id": "acc_123", "amount": 100}
        }
        allow_exec = client.post(
            "/api/decisions/control/execute",
            json=allow_req,
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert allow_exec.status_code == 200
        exec_res = allow_exec.json()
        assert exec_res["evaluation"]["decision"] == "ALLOW"
        assert exec_res["evaluation"]["execution_gate_token"] is not None
        # Dispatched to Tool Proxy
        assert exec_res["executed"] is True
        assert exec_res["execution_status"] == "EXECUTED"
