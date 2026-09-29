import unittest
import uuid
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from starlette.testclient import TestClient
from main import app
from database import SessionLocal
from core import security
from engines.policy_evaluator import evaluate_condition, validate_rule_syntax
import models

client = TestClient(app)


class TestPhase2PolicyEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

        # 1. Platform Organization & SUPER_ADMIN
        cls.platform_org = cls.db.query(models.Organization).filter(
            models.Organization.name == "Phase 2 Platform Org"
        ).first()
        if not cls.platform_org:
            cls.platform_org = models.Organization(
                name="Phase 2 Platform Org",
                domain="p2platform.agentguard",
                status="ACTIVE"
            )
            cls.db.add(cls.platform_org)
            cls.db.commit()
            cls.db.refresh(cls.platform_org)

        cls.sa_email = f"sa_p2_{uuid.uuid4().hex[:6]}@agentguard.com"
        cls.super_admin = models.User(
            org_id=cls.platform_org.id,
            email=cls.sa_email,
            full_name="Phase 2 Super Admin",
            role="SUPER_ADMIN",
            status="ACTIVE"
        )
        cls.db.add(cls.super_admin)
        cls.db.commit()
        cls.db.refresh(cls.super_admin)
        cls.sa_token = security.create_access_token(
            cls.super_admin.id, email=cls.super_admin.email, role="SUPER_ADMIN"
        )

        # 2. Organization Alpha & User Alpha & Agent Alpha
        cls.org_a = models.Organization(
            name=f"Phase 2 Org Alpha {uuid.uuid4().hex[:4]}",
            domain="alpha.p2",
            status="ACTIVE"
        )
        cls.db.add(cls.org_a)
        cls.db.commit()
        cls.db.refresh(cls.org_a)

        cls.user_a_email = f"user_a_{uuid.uuid4().hex[:6]}@alpha.p2"
        cls.user_a = models.User(
            org_id=cls.org_a.id,
            email=cls.user_a_email,
            full_name="Alpha Officer",
            role="USER",
            status="ACTIVE"
        )
        cls.db.add(cls.user_a)
        cls.db.commit()
        cls.db.refresh(cls.user_a)
        cls.user_a_token = security.create_access_token(
            cls.user_a.id, email=cls.user_a.email, role="USER"
        )

        cls.agent_a = models.Agent(
            agent_code=f"AGT-A-{uuid.uuid4().hex[:4].upper()}",
            org_id=cls.org_a.id,
            owner_id=cls.user_a.id,
            name="AlphaOpsAgent",
            department="Operations",
            purpose="Process operations tasks",
            environment="PRODUCTION",
            autonomy_level="MEDIUM",
            status="NORMAL",
            risk_score=20,
            daily_budget=50000.0
        )
        cls.db.add(cls.agent_a)
        cls.db.commit()
        cls.db.refresh(cls.agent_a)

        # 3. Organization Beta & User Beta & Agent Beta
        cls.org_b = models.Organization(
            name=f"Phase 2 Org Beta {uuid.uuid4().hex[:4]}",
            domain="beta.p2",
            status="ACTIVE"
        )
        cls.db.add(cls.org_b)
        cls.db.commit()
        cls.db.refresh(cls.org_b)

        cls.user_b_email = f"user_b_{uuid.uuid4().hex[:6]}@beta.p2"
        cls.user_b = models.User(
            org_id=cls.org_b.id,
            email=cls.user_b_email,
            full_name="Beta Specialist",
            role="USER",
            status="ACTIVE"
        )
        cls.db.add(cls.user_b)
        cls.db.commit()
        cls.db.refresh(cls.user_b)
        cls.user_b_token = security.create_access_token(
            cls.user_b.id, email=cls.user_b.email, role="USER"
        )

        cls.agent_b = models.Agent(
            agent_code=f"AGT-B-{uuid.uuid4().hex[:4].upper()}",
            org_id=cls.org_b.id,
            owner_id=cls.user_b.id,
            name="BetaFinanceAgent",
            department="Finance",
            purpose="Beta finance workflows",
            environment="PRODUCTION",
            autonomy_level="MEDIUM",
            status="NORMAL",
            risk_score=25,
            daily_budget=30000.0
        )
        cls.db.add(cls.agent_b)
        cls.db.commit()
        cls.db.refresh(cls.agent_b)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def tearDown(self):
        # Clean up policies created for test orgs between runs to guarantee isolation
        policy_ids = [p.id for p in self.db.query(models.Policy).filter(
            models.Policy.org_id.in_([self.org_a.id, self.org_b.id])
        ).all()]
        if policy_ids:
            self.db.query(models.PolicyRule).filter(models.PolicyRule.policy_id.in_(policy_ids)).delete(synchronize_session=False)
            self.db.query(models.Policy).filter(models.Policy.id.in_(policy_ids)).delete(synchronize_session=False)
            self.db.commit()

    # ==========================================
    # TEST 1: No authentication -> decision endpoint rejected
    # ==========================================
    def test_01_unauthenticated_decision_rejected(self):
        resp = client.post("/api/decisions/evaluate", json={"prompt": "Transfer 100 dollars"})
        self.assertEqual(resp.status_code, 401, "Unauthenticated request must be rejected with 401")

    # ==========================================
    # TEST 2: Organization A user -> Organization B agent/policy cannot be evaluated
    # ==========================================
    def test_02_org_a_user_cannot_evaluate_org_b_agent(self):
        resp = client.post(
            "/api/decisions/evaluate",
            json={"prompt": "Check account balance", "agent_id": str(self.agent_b.id)},
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(resp.status_code, 403, "User from Org A cannot evaluate an agent from Org B")
        self.assertIn("Forbidden", resp.json().get("detail", ""))

    # ==========================================
    # TEST 3: Organization A agent -> Organization B policy cannot be used
    # ==========================================
    def test_03_org_a_agent_does_not_use_org_b_policy(self):
        # Create an aggressive REFUSE policy exclusively in Org B
        policy_b = models.Policy(
            org_id=self.org_b.id,
            name="Org B Strict Lockdown",
            category="SECURITY",
            priority=1,
            status="ACTIVE"
        )
        self.db.add(policy_b)
        self.db.commit()
        self.db.refresh(policy_b)

        rule_b = models.PolicyRule(
            policy_id=policy_b.id,
            condition_expression="'export' in action or intent == 'DATA_EXPORT'",
            decision_output="REFUSE",
            risk_delta=40,
            description="Org B blocks all export actions"
        )
        self.db.add(rule_b)
        self.db.commit()

        # Org A user executes export on Agent A
        resp = client.post(
            "/api/decisions/evaluate",
            json={"prompt": "Export user data to csv", "agent_id": str(self.agent_a.id), "amount": 100.0},
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # Should NOT be REFUSE under Org B's policy!
        self.assertNotEqual(data["policy_name"], "Org B Strict Lockdown", "Org A evaluation must never apply Org B policies")

    # ==========================================
    # TEST 4: Active policy with matching rule -> expected policy effect occurs
    # ==========================================
    def test_04_active_policy_matching_rule_enforces_decision(self):
        # Create a custom policy in Org A: block amounts over 2000
        policy_a = models.Policy(
            org_id=self.org_a.id,
            name="Org A ₹2,000 Micro-Ceiling",
            category="FINANCE",
            priority=1,
            status="ACTIVE"
        )
        self.db.add(policy_a)
        self.db.commit()
        self.db.refresh(policy_a)

        rule_a = models.PolicyRule(
            policy_id=policy_a.id,
            condition_expression="amount > 2000",
            decision_output="REFUSE",
            risk_delta=30,
            description="Org A strictly refuses amounts over ₹2,000"
        )
        self.db.add(rule_a)
        self.db.commit()

        resp = client.post(
            "/api/decisions/evaluate",
            json={"prompt": "Process vendor invoice", "agent_id": str(self.agent_a.id), "amount": 2500.0},
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["decision"], "REFUSE", "Expected matching database rule to produce REFUSE")
        self.assertEqual(data["execution_status"], "BLOCKED")
        self.assertEqual(data["policy_name"], "Org A ₹2,000 Micro-Ceiling")

    # ==========================================
    # TEST 5: Active policy with non-matching rule -> correct default behavior occurs
    # ==========================================
    def test_05_active_policy_non_matching_rule_falls_back_safely(self):
        # Create policy in Org A: block amounts over 2000
        policy_a = models.Policy(
            org_id=self.org_a.id,
            name="Org A ₹2,000 Micro-Ceiling",
            category="FINANCE",
            priority=1,
            status="ACTIVE"
        )
        self.db.add(policy_a)
        self.db.commit()

        rule_a = models.PolicyRule(
            policy_id=policy_a.id,
            condition_expression="amount > 2000",
            decision_output="REFUSE",
            risk_delta=30,
            description="Org A strictly refuses amounts over ₹2,000"
        )
        self.db.add(rule_a)
        self.db.commit()

        # Transaction amount 500 does not match amount > 2000
        resp = client.post(
            "/api/decisions/evaluate",
            json={"prompt": "Process small vendor invoice", "agent_id": str(self.agent_a.id), "amount": 500.0},
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["decision"], "ALLOW", "Non-matching rule within safe limits should default to ALLOW")
        self.assertEqual(data["execution_status"], "EXECUTED")

    # ==========================================
    # TEST 6: Disabled/inactive policy -> does not affect evaluation
    # ==========================================
    def test_06_disabled_policy_is_ignored(self):
        # Create a DISABLED policy in Org A with REFUSE
        policy_disabled = models.Policy(
            org_id=self.org_a.id,
            name="Org A Inactive Policy",
            category="SECURITY",
            priority=1,
            status="DISABLED"
        )
        self.db.add(policy_disabled)
        self.db.commit()
        self.db.refresh(policy_disabled)

        rule_disabled = models.PolicyRule(
            policy_id=policy_disabled.id,
            condition_expression="amount > 100",
            decision_output="REFUSE",
            risk_delta=50,
            description="Inactive rule blocking everything over 100"
        )
        self.db.add(rule_disabled)
        self.db.commit()

        # Evaluate amount 500 (would match if active)
        resp = client.post(
            "/api/decisions/evaluate",
            json={"prompt": "Routine petty cash payment", "agent_id": str(self.agent_a.id), "amount": 500.0},
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertNotEqual(data["policy_name"], "Org A Inactive Policy", "Disabled policy must not be applied")

    # ==========================================
    # TEST 7: Multiple policies -> deterministic precedence (priority order)
    # ==========================================
    def test_07_multiple_policies_priority_order(self):
        # Create Policy 1 (Priority 1) and Policy 2 (Priority 2) with review output
        pol_p1 = models.Policy(
            org_id=self.org_a.id,
            name="Policy Priority 1 Primary",
            category="FINANCE",
            priority=1,
            status="ACTIVE"
        )
        pol_p2 = models.Policy(
            org_id=self.org_a.id,
            name="Policy Priority 2 Secondary",
            category="FINANCE",
            priority=2,
            status="ACTIVE"
        )
        self.db.add_all([pol_p1, pol_p2])
        self.db.commit()
        self.db.refresh(pol_p1)
        self.db.refresh(pol_p2)

        rule1 = models.PolicyRule(
            policy_id=pol_p1.id,
            condition_expression="amount == 2222",
            decision_output="REVIEW",
            risk_delta=10,
            description="Priority 1 rule match"
        )
        rule2 = models.PolicyRule(
            policy_id=pol_p2.id,
            condition_expression="amount == 2222",
            decision_output="REVIEW",
            risk_delta=10,
            description="Priority 2 rule match"
        )
        self.db.add_all([rule1, rule2])
        self.db.commit()

        resp = client.post(
            "/api/decisions/evaluate",
            json={"prompt": "Test priority matching", "agent_id": str(self.agent_a.id), "amount": 2222.0},
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["decision"], "REVIEW")
        self.assertEqual(data["policy_name"], "Policy Priority 1 Primary", "Highest priority policy (1) must precede (2)")

    # ==========================================
    # TEST 8: Multiple matching rules -> deterministic precedence (REFUSE > REVIEW > ALLOW)
    # ==========================================
    def test_08_multiple_matching_rules_severity_precedence(self):
        # Create a policy with both an ALLOW rule and a REFUSE rule matching the same amount
        pol_conflict = models.Policy(
            org_id=self.org_a.id,
            name="Conflict Test Policy",
            category="SECURITY",
            priority=1,
            status="ACTIVE"
        )
        self.db.add(pol_conflict)
        self.db.commit()
        self.db.refresh(pol_conflict)

        r_allow = models.PolicyRule(
            policy_id=pol_conflict.id,
            condition_expression="amount == 1234",
            decision_output="ALLOW",
            risk_delta=0,
            description="Allow rule"
        )
        r_refuse = models.PolicyRule(
            policy_id=pol_conflict.id,
            condition_expression="amount == 1234",
            decision_output="REFUSE",
            risk_delta=30,
            description="Refuse rule"
        )
        self.db.add_all([r_allow, r_refuse])
        self.db.commit()

        resp = client.post(
            "/api/decisions/evaluate",
            json={"prompt": "Execute matching amount transaction", "agent_id": str(self.agent_a.id), "amount": 1234.0},
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["decision"], "REFUSE", "REFUSE must always take precedence over ALLOW")
        self.assertEqual(data["execution_status"], "BLOCKED")

    # ==========================================
    # TEST 9: Policy modification -> subsequent decision reflects modification
    # ==========================================
    def test_09_policy_modification_affects_decisions(self):
        # Create policy that blocks export actions
        pol = models.Policy(
            org_id=self.org_a.id,
            name="Export Logs Guard",
            category="DATA",
            priority=1,
            status="ACTIVE"
        )
        self.db.add(pol)
        self.db.commit()
        self.db.refresh(pol)

        rule = models.PolicyRule(
            policy_id=pol.id,
            condition_expression="'export' in action or intent == 'DATA_EXPORT'",
            decision_output="REFUSE",
            risk_delta=20,
            description="Exporting logs blocked"
        )
        self.db.add(rule)
        self.db.commit()

        # Check that it blocks
        resp1 = client.post(
            "/api/decisions/evaluate",
            json={"prompt": "Export logs from database", "agent_id": str(self.agent_a.id), "amount": 10.0},
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(resp1.json()["decision"], "REFUSE")

        # Disable the policy via PATCH API
        patch_resp = client.patch(
            f"/api/policies/{pol.id}",
            json={"status": "DISABLED"},
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(patch_resp.status_code, 200)
        self.assertEqual(patch_resp.json()["status"], "DISABLED")

        # Check subsequent decision no longer refuses
        resp2 = client.post(
            "/api/decisions/evaluate",
            json={"prompt": "Export logs from database", "agent_id": str(self.agent_a.id), "amount": 10.0},
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertNotEqual(resp2.json()["decision"], "REFUSE", "Modified (disabled) policy must no longer refuse")

    # ==========================================
    # TEST 10: Policy rule modification -> subsequent decision reflects modification
    # ==========================================
    def test_10_policy_rule_modification_affects_decisions(self):
        # Create policy with rule: amount > 4000
        pol = models.Policy(
            org_id=self.org_a.id,
            name="Threshold Test Policy",
            category="FINANCE",
            priority=1,
            status="ACTIVE"
        )
        self.db.add(pol)
        self.db.commit()
        self.db.refresh(pol)

        rule = models.PolicyRule(
            policy_id=pol.id,
            condition_expression="amount > 4000",
            decision_output="REFUSE",
            risk_delta=20,
            description="Block over 4000"
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)

        # 4500 is refused
        resp1 = client.post(
            "/api/decisions/evaluate",
            json={"prompt": "Routine purchase request", "agent_id": str(self.agent_a.id), "amount": 4500.0},
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(resp1.json()["decision"], "REFUSE")

        # Modify rule to amount > 10000 via API
        patch_rule = client.patch(
            f"/api/policies/{pol.id}/rules/{rule.id}",
            json={"condition_expression": "amount > 10000"},
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(patch_rule.status_code, 200)

        # 4500 should no longer trigger this rule's REFUSE
        resp2 = client.post(
            "/api/decisions/evaluate",
            json={"prompt": "Routine purchase request", "agent_id": str(self.agent_a.id), "amount": 4500.0},
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertNotEqual(resp2.json()["decision"], "REFUSE", "Rule modified to 10000 must not block 4500")

    # ==========================================
    # TEST 11: Invalid rule definition fails safely
    # ==========================================
    def test_11_invalid_rule_fails_safely(self):
        # API rejects invalid rule syntax
        pol = models.Policy(
            org_id=self.org_a.id,
            name="Syntax Test Policy",
            category="SECURITY",
            priority=1,
            status="ACTIVE"
        )
        self.db.add(pol)
        self.db.commit()
        self.db.refresh(pol)

        # Attempt to insert an arbitrary code execution attempt
        bad_rule_resp = client.post(
            f"/api/policies/{pol.id}/rules",
            json={"condition_expression": "__import__('os').system('echo pwned')", "decision_output": "ALLOW"},
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(bad_rule_resp.status_code, 400, "Unsafe condition expression must be rejected with 400")

        # Direct evaluation of safe evaluator on invalid condition fails safely
        matched, is_valid, err = evaluate_condition("invalid >>> syntax", {"amount": 100})
        self.assertFalse(matched)
        self.assertFalse(is_valid)

    # ==========================================
    # TEST 12: SUPER_ADMIN can inspect/manage policy data
    # ==========================================
    def test_12_super_admin_can_manage_platform_policies(self):
        resp = client.get("/api/platform/governance", headers={"Authorization": f"Bearer {self.sa_token}"})
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

        # SUPER_ADMIN listing all policies via /policies
        resp_all = client.get("/api/policies", headers={"Authorization": f"Bearer {self.sa_token}"})
        self.assertEqual(resp_all.status_code, 200)

    # ==========================================
    # TEST 13: Normal tenant user cannot access another tenant's policy
    # ==========================================
    def test_13_tenant_user_cannot_access_other_tenant_policy(self):
        # Create policy in Org B
        pol_b = models.Policy(
            org_id=self.org_b.id,
            name="Private Org B Policy",
            category="SECURITY",
            priority=1,
            status="ACTIVE"
        )
        self.db.add(pol_b)
        self.db.commit()
        self.db.refresh(pol_b)

        resp_get = client.get(
            f"/api/policies/{pol_b.id}",
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(resp_get.status_code, 403, "User A cannot access Org B policy")

        resp_patch = client.patch(
            f"/api/policies/{pol_b.id}",
            json={"name": "Hacked Policy"},
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(resp_patch.status_code, 403, "User A cannot modify Org B policy")

        resp_del = client.delete(
            f"/api/policies/{pol_b.id}",
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(resp_del.status_code, 403, "User A cannot delete Org B policy")

    # ==========================================
    # TEST 14: Decision audit/provenance identifies the policy/rule used
    # ==========================================
    def test_14_decision_audit_and_provenance_record_policy_metadata(self):
        pol = models.Policy(
            org_id=self.org_a.id,
            name="Provenance Audit Target Policy",
            category="FINANCE",
            priority=1,
            status="ACTIVE"
        )
        self.db.add(pol)
        self.db.commit()
        self.db.refresh(pol)

        rule = models.PolicyRule(
            policy_id=pol.id,
            condition_expression="amount == 3333",
            decision_output="REVIEW",
            risk_delta=15,
            description="Trigger review for 3333"
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)

        resp = client.post(
            "/api/decisions/evaluate",
            json={"prompt": "Transfer 3333", "agent_id": str(self.agent_a.id), "amount": 3333.0},
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        decision_id = data["id"]

        # Inspect persisted Decision
        dec = self.db.query(models.Decision).filter(models.Decision.id == decision_id).first()
        self.assertIsNotNone(dec)
        self.assertEqual(dec.policy_name, "Provenance Audit Target Policy")

        # Inspect ProvenanceEvent
        prov = self.db.query(models.ProvenanceEvent).filter(models.ProvenanceEvent.decision_id == decision_id).first()
        self.assertIsNotNone(prov)
        self.assertIn("policy_applied", prov.causal_chain_json)
        self.assertEqual(prov.causal_chain_json["policy_applied"], "Provenance Audit Target Policy")
        self.assertEqual(prov.causal_chain_json["policy_id"], str(pol.id))
        self.assertEqual(prov.causal_chain_json["rule_id"], str(rule.id))

        # Inspect AuditLog
        audit = self.db.query(models.AuditLog).filter(
            models.AuditLog.actor_id == self.agent_a.agent_code,
            models.AuditLog.result == "REVIEW"
        ).order_by(models.AuditLog.timestamp.desc()).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.metadata_json.get("policy"), "Provenance Audit Target Policy")
        self.assertEqual(audit.metadata_json.get("policy_id"), str(pol.id))
        self.assertEqual(audit.metadata_json.get("rule_id"), str(rule.id))

    # ==========================================
    # TEST 15: No global .first() policy fallback exists
    # ==========================================
    def test_15_no_global_first_policy_fallback(self):
        # If an org has no policies, it must NOT pick another org's policy via .first()
        empty_org = models.Organization(
            name=f"Empty Policy Org {uuid.uuid4().hex[:4]}",
            domain="empty.p2",
            status="ACTIVE"
        )
        self.db.add(empty_org)
        self.db.commit()
        self.db.refresh(empty_org)

        user_empty = models.User(
            org_id=empty_org.id,
            email=f"empty_{uuid.uuid4().hex[:6]}@empty.p2",
            full_name="Empty User",
            role="USER",
            status="ACTIVE"
        )
        self.db.add(user_empty)
        self.db.commit()
        self.db.refresh(user_empty)
        token_empty = security.create_access_token(
            user_empty.id, email=user_empty.email, role="USER"
        )

        agent_empty = models.Agent(
            agent_code=f"AGT-E-{uuid.uuid4().hex[:4].upper()}",
            org_id=empty_org.id,
            owner_id=user_empty.id,
            name="EmptyAgent",
            department="Ops",
            purpose="Ops",
            environment="PRODUCTION",
            autonomy_level="MEDIUM",
            status="NORMAL",
            risk_score=15,
            daily_budget=10000.0
        )
        self.db.add(agent_empty)
        self.db.commit()
        self.db.refresh(agent_empty)

        # Evaluate on an agent in an org with zero custom policies
        resp = client.post(
            "/api/decisions/evaluate",
            json={"prompt": "Routine petty task", "agent_id": str(agent_empty.id), "amount": 100.0},
            headers={"Authorization": f"Bearer {token_empty}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # Must fall back to baseline default, NOT any custom policy from Org A or Org B
        self.assertEqual(data["policy_name"], "Standard Autonomous Access Policy")
        self.assertEqual(data["decision"], "ALLOW")


if __name__ == "__main__":
    unittest.main()
