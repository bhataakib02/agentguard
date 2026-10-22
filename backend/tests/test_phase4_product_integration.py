"""
AGENTGUARD Phase 4 - Integrated Product Demonstration Test Suite
Validates the end-to-end user journey across Agent Management, PACE Console,
Human Approvals, Execution Boundary, Lifecycle Tracing, and Evaluation-Data Support.
"""

import os
import sys
import uuid
import datetime
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup test environment
os.environ["DATABASE_URL"] = "sqlite:///test_phase4_suite.db"
os.environ["SECRET_KEY"] = "test-phase4-secret-key-44332"
os.environ["ENVIRONMENT"] = "test"
os.environ["AGENTGUARD_ALLOW_LOCAL_TOOLS"] = "true"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import app
from database import Base, engine, get_db
import models
import schemas
from core import security
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


class TestPhase4ProductIntegrationSuite:
    """
    Validates the coherent end-to-end user journey, three distinct action outcomes,
    execution boundary behavior, lifecycle tracing, and evaluation data support.
    """

    @classmethod
    def setup_class(cls):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        db = TestSession()

        # 1. Organization 1 (Alpha Corp)
        org1 = models.Organization(name="Alpha Corp", domain="alphacorp.com", status="ACTIVE")
        db.add(org1)
        db.commit()
        db.refresh(org1)
        cls.org1_id = str(org1.id)

        # 2. Organization 2 (Beta Corp - for Cross-Tenant Isolation)
        org2 = models.Organization(name="Beta Corp", domain="betacorp.com", status="ACTIVE")
        db.add(org2)
        db.commit()
        db.refresh(org2)
        cls.org2_id = str(org2.id)

        # Users in Org 1: Admin, Manager, Analyst
        admin1 = models.User(
            email="admin@alphacorp.com",
            password_hash=security.get_password_hash("pass123"),
            full_name="Alpha Admin",
            org_id=org1.id,
            role="ADMIN",
            status="ACTIVE"
        )
        manager1 = models.User(
            email="manager@alphacorp.com",
            password_hash=security.get_password_hash("pass123"),
            full_name="Alpha Manager",
            org_id=org1.id,
            role="MANAGER",
            status="ACTIVE"
        )
        analyst1 = models.User(
            email="analyst@alphacorp.com",
            password_hash=security.get_password_hash("pass123"),
            full_name="Alpha Analyst",
            org_id=org1.id,
            role="ANALYST",
            status="ACTIVE"
        )

        # User in Org 2: Admin
        admin2 = models.User(
            email="admin@betacorp.com",
            password_hash=security.get_password_hash("pass123"),
            full_name="Beta Admin",
            org_id=org2.id,
            role="ADMIN",
            status="ACTIVE"
        )

        db.add_all([admin1, manager1, analyst1, admin2])
        db.commit()
        db.refresh(admin1)
        db.refresh(manager1)
        db.refresh(analyst1)
        db.refresh(admin2)

        cls.admin1_token = security.create_access_token(str(admin1.id), email=str(admin1.email), role=str(admin1.role))
        cls.manager1_token = security.create_access_token(str(manager1.id), email=str(manager1.email), role=str(manager1.role))
        cls.analyst1_token = security.create_access_token(str(analyst1.id), email=str(analyst1.email), role=str(analyst1.role))
        cls.admin2_token = security.create_access_token(str(admin2.id), email=str(admin2.email), role=str(admin2.role))

        # Agents in Org 1
        agent1 = models.Agent(
            agent_code="AG-ALPHA-PROCURE",
            org_id=org1.id,
            owner_id=admin1.id,
            name="Alpha Procurement Agent",
            department="Operations",
            purpose="Routine procurement order database queries",
            model_name="gpt-4o",
            autonomy_level="MEDIUM",
            risk_score=15,
            status="NORMAL",
            daily_budget=20000.0
        )
        db.add(agent1)

        # Agent in Org 2
        agent2 = models.Agent(
            agent_code="AG-BETA-WORKER",
            org_id=org2.id,
            owner_id=admin2.id,
            name="Beta Worker Agent",
            department="Operations",
            purpose="Beta isolated task agent",
            model_name="gpt-4o",
            autonomy_level="LOW",
            risk_score=20,
            status="NORMAL",
            daily_budget=10000.0
        )
        db.add(agent2)
        db.commit()
        db.refresh(agent1)
        db.refresh(agent2)
        cls.agent1_code = agent1.agent_code
        cls.agent1_id = str(agent1.id)
        cls.agent2_code = agent2.agent_code
        cls.agent2_id = str(agent2.id)

        # Passports for Agents
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

        p2 = models.AgentPassport(
            agent_id=agent2.id,
            passport_number=f"AG-PASSPORT-{agent2.agent_code}",
            digital_signature="pending",
            issued_at=datetime.datetime.utcnow(),
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=365),
            verification_status="VERIFIED"
        )
        passport_service.sign_passport(agent2, p2)
        db.add(p2)

        # Static Permissions for Agent 1
        perm1 = models.Permission(
            agent_id=agent1.id,
            action="READ",
            resource_type="DATABASE",
            resource_name="orders",
            is_allowed=True
        )
        perm2 = models.Permission(
            agent_id=agent1.id,
            action="EXECUTE",
            resource_type="API",
            resource_name="payments",
            is_allowed=True
        )
        db.add_all([perm1, perm2])

        # Policy A: Strict Data Protection (DELETE on prod -> REFUSE)
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

        # Tool in Tool Registry for Tool Proxy execution
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

    @classmethod
    def teardown_class(cls):
        Base.metadata.drop_all(bind=engine)

    def test_01_user_journey_agent_directory_to_evaluation(self):
        """
        Step 1: Shortest complete user journey.
        Lists registered agents, verifies their autonomy profile and permissions,
        and runs pre-flight evaluation.
        """
        # 1. Fetch Agents List
        agents_res = client.get("/api/agents", headers={"Authorization": f"Bearer {self.admin1_token}"})
        assert agents_res.status_code == 200
        agents_data = agents_res.json()
        assert any(a["agent_code"] == self.agent1_code for a in agents_data)

        # 2. Pre-Flight Evaluate Action via PACE
        eval_payload = {
            "agent_code": self.agent1_code,
            "action_type": "READ",
            "target_resource": "orders",
            "amount": 0.0,
            "correlation_id": "test-corr-01"
        }
        eval_res = client.post(
            "/api/decisions/control/evaluate",
            json=eval_payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert eval_res.status_code == 200
        data = eval_res.json()
        assert data["decision"] == "ALLOW"
        assert data["intervention_plan"]["selected_intervention"] == "ALLOW_WITHOUT_INTERVENTION"
        assert data["execution_gate_token"] is not None

    def test_02_demonstrate_outcome_1_authorized_action(self):
        """
        Step 3 - Outcome 1: An authorized action that passes mandatory checks
        and can proceed through the existing execution boundary.
        """
        payload = {
            "agent_code": self.agent1_code,
            "action_type": "EXECUTE",
            "target_resource": "payments",
            "amount": 100.0,
            "parameters": {"account_id": "acc_123", "amount": 100}
        }
        res = client.post(
            "/api/decisions/control/execute",
            json=payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["executed"] is True
        assert data["execution_status"] == "EXECUTED"
        assert data["evaluation"]["decision"] == "ALLOW"
        assert data["evaluation"]["execution_gate_token"] is not None

    def test_03_demonstrate_outcome_2_review_required_action_held_unexecuted(self):
        """
        Step 3 - Outcome 2: A review-required action that strictly remains unexecuted
        until the authorized approval workflow resolves it.
        """
        payload = {
            "agent_code": self.agent1_code,
            "action_type": "EXECUTE",
            "target_resource": "payments",
            "amount": 8500.0,  # Exceeds standard ₹5,000 threshold
            "prompt": "Disburse vendor payment exceeding autonomous threshold"
        }
        res = client.post(
            "/api/decisions/control/execute",
            json=payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["executed"] is False
        assert data["execution_status"] == "PENDING_APPROVAL"
        assert data["evaluation"]["decision"] == "REVIEW"
        assert data["evaluation"]["intervention_plan"]["selected_intervention"] == "REQUIRE_APPROVAL"
        assert data["evaluation"]["approval_id"] is not None

        # Verify Approval Request exists in queue with status PENDING
        app_res = client.get("/api/approvals", headers={"Authorization": f"Bearer {self.manager1_token}"})
        assert app_res.status_code == 200
        pending_list = app_res.json()
        target_app = next((a for a in pending_list if a["id"] == data["evaluation"]["approval_id"]), None)
        assert target_app is not None
        assert target_app["status"] == "PENDING"
        assert target_app["amount"] == 8500.0

    def test_04_demonstrate_outcome_3_prohibited_action_strictly_blocked(self):
        """
        Step 3 - Outcome 3: A prohibited action that remains blocked,
        regardless of its risk score.
        """
        payload = {
            "agent_code": self.agent1_code,
            "action_type": "DELETE",
            "target_resource": "production_database",
            "amount": 0.0,
            "prompt": "Purge production database"
        }
        res = client.post(
            "/api/decisions/control/execute",
            json=payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["executed"] is False
        assert data["execution_status"] == "BLOCKED"
        assert data["evaluation"]["decision"] == "REFUSE"
        assert data["evaluation"]["intervention_plan"]["selected_intervention"] == "REFUSE_PROHIBITED"

    def test_05_connect_decision_lifecycle_and_approval_resolution(self):
        """
        Step 4: Connect the decision lifecycle.
        Trigger a review-required action, resolve it in the Human Approval Queue,
        and verify causal provenance trace and audit records.
        """
        # 1. Trigger Review-Required Action
        payload = {
            "agent_code": self.agent1_code,
            "action_type": "EXECUTE",
            "target_resource": "payments",
            "amount": 9200.0,
            "prompt": "Disburse invoice payment requiring managerial review"
        }
        exec_res = client.post(
            "/api/decisions/control/execute",
            json=payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert exec_res.status_code == 200
        exec_data = exec_res.json()
        approval_id = exec_data["evaluation"]["approval_id"]

        # Retrieve decision ID linked to this approval
        db = TestSession()
        app_row = db.query(models.ApprovalRequest).filter(models.ApprovalRequest.id == approval_id).first()
        assert app_row is not None
        decision_id = str(app_row.decision_id)
        db.close()

        # 2. Manager Resolves Approval -> APPROVE
        act_res = client.post(
            f"/api/approvals/{approval_id}/act",
            json={"action": "APPROVE"},
            headers={"Authorization": f"Bearer {self.manager1_token}"}
        )
        assert act_res.status_code == 200
        assert act_res.json()["new_status"] == "APPROVED"

        # 3. Trace Decision Record Detail
        dec_detail_res = client.get(
            f"/api/decisions/{decision_id}",
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert dec_detail_res.status_code == 200
        dec_detail = dec_detail_res.json()
        assert dec_detail["decision"]["id"] == decision_id
        assert dec_detail["decision"]["execution_status"] in ("APPROVED", "APPROVED_PENDING_EXECUTION")
        assert dec_detail["approval_request"]["status"] == "APPROVED"

    def test_06_tenant_isolation_boundary_enforced(self):
        """
        Step 2 & 7: Check cross-tenant isolation.
        User in Org 1 cannot evaluate actions for an agent in Org 2.
        """
        payload = {
            "agent_code": self.agent2_code,  # Belongs to Org 2
            "action_type": "READ",
            "target_resource": "orders",
            "amount": 0.0,
            "prompt": "Cross-tenant intrusion attempt"
        }
        res = client.post(
            "/api/decisions/control/evaluate",
            json=payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"}  # Caller is in Org 1
        )
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] == "REFUSE"
        assert "Forbidden" in data["reason"] or "Cross-tenant" in data["reason"]
        assert data["approval_required"] is False

    def test_07_authorized_evaluation_data_support(self):
        """
        Step 6: Authorized evaluation-data support.
        Validates schema, imports records into isolated evaluation dataset registry,
        and rejects malformed records.
        """
        import_payload = {
            "dataset_name": "acme_fintech_eval_benchmark_q4",
            "description": "Authorized labeled action traces from Q4 procurement agent audit",
            "provenance": "AUTHORIZED_LABELED_DATA",
            "records": [
                {
                    "dataset_id": "acme_q4",
                    "record_id": "rec_001",
                    "provenance": "AUTHORIZED_LABELED_DATA",
                    "agent_profile": {
                        "agent_code": "AG-ALPHA-PROCURE",
                        "name": "Alpha Procurement Agent",
                        "autonomy_level": "MEDIUM",
                        "department": "Operations",
                        "granted_permissions": [
                            {"action": "READ", "resource_type": "DATABASE", "resource_name": "orders"}
                        ],
                        "daily_budget": 10000.0
                    },
                    "initial_history": [
                        {"action": "READ", "resource": "DATABASE:orders", "decision": "ALLOW", "amount": 0.0}
                    ],
                    "action_sequence": [
                        {
                            "step_number": 1,
                            "action": "READ",
                            "resource": "orders",
                            "operation": "query_recent",
                            "amount": 0.0,
                            "prompt": "Read recent order summaries",
                            "is_terminal_step": True
                        }
                    ],
                    "ground_truth_label": "SAFE",
                    "ground_truth_notes": "Standard business query verified by auditor",
                    "tags": ["q4_audit", "procurement"]
                }
            ]
        }

        # 1. Successful Import
        res = client.post(
            "/api/simulation/eval-data/import",
            json=import_payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "SUCCESS"
        assert data["imported_records_count"] == 1
        assert "isolated" in data["notice"].lower()

        # 2. List Evaluation Datasets
        list_res = client.get("/api/simulation/eval-data", headers={"Authorization": f"Bearer {self.admin1_token}"})
        assert list_res.status_code == 200
        datasets = list_res.json()
        assert any(d["dataset_name"] == "acme_fintech_eval_benchmark_q4" for d in datasets)

        # 3. Reject Malformed Import (e.g. invalid ground truth label)
        malformed_payload = dict(import_payload)
        malformed_payload["dataset_name"] = "malformed_eval_set"
        malformed_payload["records"] = [
            dict(import_payload["records"][0], ground_truth_label="INVALID_LABEL")
        ]
        bad_res = client.post(
            "/api/simulation/eval-data/import",
            json=malformed_payload,
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert bad_res.status_code == 201
        bad_data = bad_res.json()
        assert bad_data["status"] == "REJECTED"
        assert len(bad_data["validation_errors"]) > 0

    def test_08_loading_and_api_error_states(self):
        """
        Step 2 & 7: Test loading and API error states.
        Rejects non-existent agent, malformed parameters, and unauthenticated requests.
        """
        # Non-existent agent in evaluate
        res1 = client.post(
            "/api/decisions/control/evaluate",
            json={"agent_code": "AG-NON-EXISTENT", "action_type": "READ", "target_resource": "orders", "amount": 0.0},
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert res1.status_code == 200
        assert res1.json()["decision"] == "REFUSE"
        assert "not found" in res1.json()["reason"].lower()

        # Unauthenticated request
        res2 = client.get("/api/decisions")
        assert res2.status_code == 401

        # Malformed payload (amount as string that cannot be cast)
        res3 = client.post(
            "/api/decisions/control/evaluate",
            json={"agent_code": self.agent1_code, "action_type": "READ", "target_resource": "orders", "amount": "invalid_number"},
            headers={"Authorization": f"Bearer {self.admin1_token}"}
        )
        assert res3.status_code == 422
