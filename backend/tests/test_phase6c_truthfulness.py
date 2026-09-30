"""
Phase 6C: Hard-Coded, Mocked & Simulated Functionality Remediation Test Suite
Validates truthfulness across Digital Twin, Red Team Lab, Cost Optimization,
Impact Analysis, System Health, Billing, Email, Slack/Teams, and Integration Hub.
Tests tenant isolation, audit logging, zero secret exposure, and no fake data.
Minimum 25 test cases.
"""

import os
import sys
import unittest
import uuid
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from starlette.testclient import TestClient
from main import app
from database import SessionLocal
from core import security
import models

client = TestClient(app)


class TestPhase6cTruthfulness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        try:
            # 1. Organization A
            cls.org_a = cls.db.query(models.Organization).filter(models.Organization.slug == "phase6c-org-a").first()
            if not cls.org_a:
                cls.org_a = models.Organization(
                    name="Phase 6C Org A",
                    slug="phase6c-org-a",
                    domain="phase6c-a.com",
                    status="ACTIVE"
                )
                cls.db.add(cls.org_a)
                cls.db.commit()
                cls.db.refresh(cls.org_a)
            cls.org_a_id = str(cls.org_a.id)

            # 2. Organization B
            cls.org_b = cls.db.query(models.Organization).filter(models.Organization.slug == "phase6c-org-b").first()
            if not cls.org_b:
                cls.org_b = models.Organization(
                    name="Phase 6C Org B",
                    slug="phase6c-org-b",
                    domain="phase6c-b.com",
                    status="ACTIVE"
                )
                cls.db.add(cls.org_b)
                cls.db.commit()
                cls.db.refresh(cls.org_b)
            cls.org_b_id = str(cls.org_b.id)

            # 3. Platform Admin Org
            cls.platform_org = cls.db.query(models.Organization).filter(models.Organization.slug == "platform-admin-org").first()
            if not cls.platform_org:
                cls.platform_org = models.Organization(
                    name="Platform Admin Org",
                    slug="platform-admin-org",
                    domain="agentguard.com",
                    status="ACTIVE"
                )
                cls.db.add(cls.platform_org)
                cls.db.commit()
                cls.db.refresh(cls.platform_org)
            cls.platform_org_id = str(cls.platform_org.id)

            # Helper for Users
            def get_or_create_user(org_id, email, full_name, role):
                u = cls.db.query(models.User).filter(models.User.email == email).first()
                if not u:
                    u = models.User(
                        org_id=org_id,
                        email=email,
                        full_name=full_name,
                        role=role,
                        password_hash=security.get_password_hash("Blackbird@12."),
                        status="ACTIVE"
                    )
                    cls.db.add(u)
                    cls.db.commit()
                    cls.db.refresh(u)
                return u

            cls.user_a = get_or_create_user(cls.org_a_id, "admin-6c-a@agentguard.com", "Admin 6C A", "ADMIN")
            cls.user_a_id = str(cls.user_a.id)

            cls.user_b = get_or_create_user(cls.org_b_id, "admin-6c-b@agentguard.com", "Admin 6C B", "ADMIN")
            cls.user_b_id = str(cls.user_b.id)

            cls.super_admin = get_or_create_user(cls.platform_org_id, "super-6c@agentguard.com", "Super Admin 6C", "SUPER_ADMIN")
            cls.super_admin_id = str(cls.super_admin.id)

            # Agents for Org A and Org B
            cls.agent_a = cls.db.query(models.Agent).filter(models.Agent.agent_code == "AG-6C-A01").first()
            if not cls.agent_a:
                cls.agent_a = models.Agent(
                    org_id=cls.org_a_id,
                    owner_id=cls.user_a_id,
                    agent_code="AG-6C-A01",
                    name="Billing Assistant 6C",
                    purpose="Autonomous finance agent",
                    autonomy_level="MEDIUM",
                    department="Finance",
                    status="NORMAL",
                    risk_score=15
                )
                cls.db.add(cls.agent_a)
                cls.db.commit()
                cls.db.refresh(cls.agent_a)
            cls.agent_a_id = str(cls.agent_a.id)

            cls.agent_b = cls.db.query(models.Agent).filter(models.Agent.agent_code == "AG-6C-B01").first()
            if not cls.agent_b:
                cls.agent_b = models.Agent(
                    org_id=cls.org_b_id,
                    owner_id=cls.user_b_id,
                    agent_code="AG-6C-B01",
                    name="Operations Agent 6C",
                    purpose="Operations agent Org B",
                    autonomy_level="HIGH",
                    department="Operations",
                    status="NORMAL",
                    risk_score=20
                )
                cls.db.add(cls.agent_b)
                cls.db.commit()
                cls.db.refresh(cls.agent_b)
            cls.agent_b_id = str(cls.agent_b.id)

            # Tokens
            cls.token_a = security.create_access_token(
                user_id=cls.user_a_id,
                email=cls.user_a.email,
                role="ADMIN"
            )
            cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}

            cls.token_b = security.create_access_token(
                user_id=cls.user_b_id,
                email=cls.user_b.email,
                role="ADMIN"
            )
            cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

            cls.token_super = security.create_access_token(
                user_id=cls.super_admin_id,
                email=cls.super_admin.email,
                role="SUPER_ADMIN"
            )
            cls.headers_super = {"Authorization": f"Bearer {cls.token_super}"}

        finally:
            cls.db.close()

    # ==================== 1. DIGITAL TWIN TESTS ====================

    def test_01_digital_twin_classification_simulated(self):
        """Digital Twin run must explicitly return classification == 'SIMULATED' and a clear disclaimer."""
        res = client.post(
            "/api/digital-twin/run",
            json={"agent_id": self.agent_a_id, "scenario_type": "TRAFFIC_SPIKE"},
            headers=self.headers_a
        )
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(data.get("classification"), "SIMULATED")
        self.assertTrue(data.get("is_simulated"))
        self.assertFalse(data.get("is_prediction"))
        self.assertIn("SIMULATED SCENARIO ANALYSIS", data.get("disclaimer", ""))
        self.assertIn("inputs_real", data)
        self.assertIn("transformations_simulated", data)

    def test_02_digital_twin_real_inputs_telemetry(self):
        """Digital Twin must include real baseline observations in inputs_real."""
        res = client.post(
            "/api/digital-twin/run",
            json={"agent_id": self.agent_a_id, "scenario_type": "API_FAILURE"},
            headers=self.headers_a
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        inputs_real = data.get("inputs_real", {})
        self.assertIn("historical_executions_observed", inputs_real)
        self.assertIn("baseline_avg_latency_ms", inputs_real)
        self.assertIn("active_policies_count", inputs_real)

    def test_03_digital_twin_tenant_isolation(self):
        """Tenant Org A cannot run a digital twin simulation on Org B's agent."""
        res = client.post(
            "/api/digital-twin/run",
            json={"agent_id": self.agent_b_id, "scenario_type": "TRAFFIC_SPIKE"},
            headers=self.headers_a
        )
        self.assertEqual(res.status_code, 404)

    def test_04_digital_twin_audit_logging(self):
        """Digital Twin execution must produce an immutable audit log."""
        client.post(
            "/api/digital-twin/run",
            json={"agent_id": self.agent_a_id, "scenario_type": "MALICIOUS_INPUT"},
            headers=self.headers_a
        )
        db = SessionLocal()
        try:
            log = db.query(models.AuditLog).filter(
                models.AuditLog.org_id == self.org_a_id,
                models.AuditLog.event_type == "DIGITAL_TWIN_SIMULATION_EXECUTED"
            ).first()
            self.assertIsNotNone(log)
            self.assertEqual(log.result, "SUCCESS")
        finally:
            db.close()

    def test_05_digital_twin_super_admin_access(self):
        """Super Admin can simulate agents across any tenant."""
        res = client.post(
            "/api/digital-twin/run",
            json={"agent_id": self.agent_b_id, "scenario_type": "TRAFFIC_SPIKE"},
            headers=self.headers_super
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json().get("agent_id"), self.agent_b_id)

    # ==================== 2. RED TEAM LAB TESTS ====================

    def test_06_red_team_distinguishes_real_vs_simulated(self):
        """Red Team execution must return test_category distinguishing REAL vs SIMULATED."""
        res = client.post(
            "/api/red-team/run",
            json={"agent_id": self.agent_a_id, "attack_type": "AUTHORIZATION_BOUNDARY"},
            headers=self.headers_a
        )
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(data.get("test_category"), "REAL INTERNAL GOVERNANCE TEST")
        self.assertIn("expected_outcome", data)
        self.assertIn("actual_outcome", data)

    def test_07_red_team_policy_engine_real_evaluation(self):
        """Red Team must execute real PolicyEngine and report the enforcing policy."""
        res = client.post(
            "/api/red-team/run",
            json={"agent_id": self.agent_a_id, "attack_type": "AUTHORIZATION_BOUNDARY"},
            headers=self.headers_a
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("policy_applied", data)
        self.assertIn(data.get("actual_outcome"), ["REFUSE", "REVIEW", "ALLOW"])

    def test_08_red_team_financial_cap_excess(self):
        """Red Team FINANCIAL_CAP_EXCESS scenario must be blocked by Hard Financial Cap Policy."""
        res = client.post(
            "/api/red-team/run",
            json={"agent_id": self.agent_a_id, "attack_type": "FINANCIAL_CAP_EXCESS"},
            headers=self.headers_a
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("actual_outcome"), "REFUSE")
        self.assertEqual(data.get("test", {}).get("defense_result"), "PASSED")
        self.assertEqual(data.get("test", {}).get("security_score"), 98)

    def test_09_red_team_unsafe_deletion(self):
        """Red Team UNSAFE_DELETION scenario must be blocked by production safety policy."""
        res = client.post(
            "/api/red-team/run",
            json={"agent_id": self.agent_a_id, "attack_type": "UNSAFE_DELETION"},
            headers=self.headers_a
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("actual_outcome"), "REFUSE")
        self.assertEqual(data.get("test", {}).get("defense_result"), "PASSED")

    def test_10_red_team_prompt_injection_simulated_category(self):
        """PROMPT_INJECTION attack vector must be classified as SIMULATED ATTACK SCENARIO."""
        res = client.post(
            "/api/red-team/run",
            json={"agent_id": self.agent_a_id, "attack_type": "PROMPT_INJECTION"},
            headers=self.headers_a
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("test_category"), "SIMULATED ATTACK SCENARIO")

    def test_11_red_team_tenant_isolation(self):
        """Tenant Org A cannot run red team tests on Org B's agent."""
        res = client.post(
            "/api/red-team/run",
            json={"agent_id": self.agent_b_id, "attack_type": "AUTHORIZATION_BOUNDARY"},
            headers=self.headers_a
        )
        self.assertEqual(res.status_code, 404)

    def test_12_red_team_audit_logging(self):
        """Red Team execution must create an audit log entry."""
        client.post(
            "/api/red-team/run",
            json={"agent_id": self.agent_a_id, "attack_type": "TOOL_ABUSE"},
            headers=self.headers_a
        )
        db = SessionLocal()
        try:
            log = db.query(models.AuditLog).filter(
                models.AuditLog.org_id == self.org_a_id,
                models.AuditLog.event_type == "RED_TEAM_TEST_EXECUTED"
            ).order_by(models.AuditLog.timestamp.desc()).first()
            self.assertIsNotNone(log)
            self.assertIn("TOOL_ABUSE", log.action)
        finally:
            db.close()

    # ==================== 3. COST OPTIMIZATION TESTS ====================

    def test_13_optimization_insufficient_data_handling(self):
        """When fewer than 5 executions exist, recommendations endpoint must return INSUFFICIENT DATA."""
        res = client.get(
            "/api/optimization/recommendations?range=7d",
            headers=self.headers_b
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        if data.get("sample_count", 0) < 5:
            self.assertEqual(data.get("status"), "INSUFFICIENT DATA")
            self.assertEqual(data.get("data_sufficiency"), "INSUFFICIENT")
            self.assertEqual(data.get("recommendations"), [])
            self.assertIn("requires at least 5 real execution samples", data.get("message", ""))

    def test_14_optimization_no_invented_savings_on_insufficient_data(self):
        """Optimization must never return fabricated dollar savings numbers when data is scarce."""
        res = client.get(
            "/api/optimization/recommendations?range=24h",
            headers=self.headers_b
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        if data.get("sample_count", 0) < 5:
            self.assertEqual(len(data.get("recommendations", [])), 0)

    def test_15_optimization_compute_truthful_metrics(self):
        """Compute usage endpoint must return real observed metrics, not fake GPU clusters or kWh."""
        res = client.get("/api/optimization/compute", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "REAL_OBSERVED")
        self.assertIn("observed_executions", data)
        self.assertIn("total_tokens_consumed", data)
        self.assertNotIn("active_gpu_clusters", data)
        self.assertNotIn("energy_consumption", data)

    def test_16_optimization_tenant_isolation(self):
        """Non-SUPER_ADMIN cannot query optimization data for another tenant."""
        res = client.get(
            f"/api/optimization/recommendations?org_id={self.org_b_id}",
            headers=self.headers_a
        )
        self.assertEqual(res.status_code, 403)

    # ==================== 4. IMPACT ANALYSIS TESTS ====================

    def test_17_impact_metrics_real_aggregation(self):
        """Impact metrics must be derived from database records and not return static fake strings."""
        res = client.get("/api/impact/metrics", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "REAL_AGGREGATION")
        self.assertIn("total_decisions_evaluated", data)
        self.assertIn("prevented_financial_risk_amount", data)
        self.assertIsInstance(data.get("prevented_financial_risk_amount"), (int, float))

    def test_18_impact_metrics_calculates_refusal_prevented_amount(self):
        """When a decision with amount is refused, it reflects in prevented_financial_risk_amount."""
        db = SessionLocal()
        try:
            # Seed a real refused decision
            dec = models.Decision(
                agent_id=self.agent_a_id,
                user_id=self.user_a_id,
                intent_summary="Unauthorized high-value transaction test",
                action_requested="wire_transfer",
                resource_target="vault",
                amount=25000.0,
                decision="REFUSE",
                risk_score=90,
                policy_name="Financial Safety Policy",
                explanation="Transaction blocked by hard financial safety policy ceiling",
                execution_status="BLOCKED",
                timestamp=datetime.datetime.utcnow()
            )
            db.add(dec)
            db.commit()
        finally:
            db.close()

        res = client.get("/api/impact/metrics", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data.get("prevented_financial_risk_amount", 0), 25000.0)

    def test_19_impact_tenant_isolation(self):
        """Tenant Org A only sees its own decision impact, not Org B's."""
        res = client.get(f"/api/impact/metrics?org_id={self.org_b_id}", headers=self.headers_a)
        self.assertEqual(res.status_code, 403)

    # ==================== 5. SYSTEM HEALTH TESTS ====================

    def test_20_system_health_real_database_ping(self):
        """System health performs a real database ping and returns measured latency in ms."""
        res = client.get("/api/system/health", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn(data.get("status"), ["HEALTHY", "DEGRADED", "UNAVAILABLE"])
        subsystems = data.get("subsystems", {})
        self.assertIn("database", subsystems)
        db_sys = subsystems["database"]
        self.assertIn(db_sys.get("status"), ["HEALTHY", "DEGRADED", "UNAVAILABLE"])
        if db_sys.get("status") == "HEALTHY":
            self.assertIsInstance(db_sys.get("latency_ms"), int)
            self.assertGreaterEqual(db_sys.get("latency_ms"), 1)

    def test_21_system_health_real_uptime(self):
        """System health returns true process uptime in seconds (not static 86400)."""
        res = client.get("/api/system/health", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        uptime = data.get("uptime_seconds")
        self.assertIsInstance(uptime, int)
        self.assertGreater(uptime, 0)

    def test_22_system_health_notification_not_configured(self):
        """When SMTP credentials are not in environment, notification_subsystem reports NOT_CONFIGURED."""
        if not (os.getenv("SMTP_HOST") or os.getenv("SENDGRID_API_KEY")):
            res = client.get("/api/system/health", headers=self.headers_a)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            notif = data.get("subsystems", {}).get("notification_subsystem", {})
            self.assertEqual(notif.get("status"), "NOT_CONFIGURED")

    # ==================== 6. BILLING, EMAIL & INTEGRATION TESTS ====================

    def test_23_billing_unconfigured_external_gateway(self):
        """Integrations endpoint must report Stripe as NOT_CONFIGURED if STRIPE_SECRET_KEY is absent."""
        if not (os.getenv("STRIPE_SECRET_KEY") or os.getenv("STRIPE_API_KEY")):
            res = client.get("/api/integrations", headers=self.headers_a)
            self.assertEqual(res.status_code, 200)
            integrations = res.json()
            stripe_item = next((i for i in integrations if i["id"] == "stripe"), None)
            self.assertIsNotNone(stripe_item)
            self.assertEqual(stripe_item["status"], "NOT_CONFIGURED")
            self.assertNotEqual(stripe_item["status"], "CONNECTED")

    def test_24_email_invitation_truthful_delivery_status(self):
        """Invite user endpoint must report EMAIL_PROVIDER_NOT_CONFIGURED if SMTP is unconfigured."""
        if not (os.getenv("SMTP_HOST") or os.getenv("SENDGRID_API_KEY")):
            test_email = f"invite-{uuid.uuid4().hex[:8]}@phase6c-a.com"
            res = client.post(
                "/api/organization/invite-user",
                json={
                    "email": test_email,
                    "full_name": "Truthful Invite User",
                    "role": "DEVELOPER",
                    "department": "Engineering"
                },
                headers=self.headers_a
            )
            self.assertEqual(res.status_code, 200, res.text)
            data = res.json()
            self.assertEqual(data.get("email_delivery_status"), "EMAIL_PROVIDER_NOT_CONFIGURED")
            self.assertIn("SMTP provider is not configured", data.get("email_delivery_note", ""))

    def test_25_slack_teams_truthful_state(self):
        """Slack and Teams must report NOT_CONFIGURED when webhook URLs are missing from environment."""
        if not (os.getenv("SLACK_WEBHOOK_URL") or os.getenv("SLACK_BOT_TOKEN")):
            res = client.get("/api/integrations", headers=self.headers_a)
            self.assertEqual(res.status_code, 200)
            integrations = res.json()
            slack_item = next((i for i in integrations if i["id"] == "slack"), None)
            self.assertIsNotNone(slack_item)
            self.assertEqual(slack_item["status"], "NOT_CONFIGURED")
            self.assertNotEqual(slack_item["status"], "CONNECTED")

    def test_26_zero_secret_leakage_in_integrations(self):
        """No integration card may leak raw secret keys or tokens."""
        res = client.get("/api/integrations", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        body = res.text
        for secret_prefix in ["sk-", "Bearer ", "AKIA", "rzp_live_", "whsec_"]:
            self.assertNotIn(secret_prefix, body)


if __name__ == "__main__":
    unittest.main()
