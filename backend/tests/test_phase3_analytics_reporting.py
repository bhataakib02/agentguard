import unittest
import uuid
import sys
import os
import datetime
import hmac
import hashlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from starlette.testclient import TestClient
from main import app
from database import SessionLocal
from core import security
from services.notification_service import (
    compute_webhook_signature,
    validate_webhook_url,
    dispatch_webhook_delivery,
    notify_governance_event,
)
import models

client = TestClient(app)


class TestPhase3AnalyticsReporting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

        # 1. Platform Organization & SUPER_ADMIN
        cls.platform_org = cls.db.query(models.Organization).filter(
            models.Organization.name == "Phase 3 Platform Org"
        ).first()
        if not cls.platform_org:
            cls.platform_org = models.Organization(
                name="Phase 3 Platform Org",
                domain="p3platform.agentguard",
                status="ACTIVE"
            )
            cls.db.add(cls.platform_org)
            cls.db.commit()
            cls.db.refresh(cls.platform_org)

        cls.sa_email = f"sa_p3_{uuid.uuid4().hex[:6]}@agentguard.com"
        cls.super_admin = models.User(
            org_id=cls.platform_org.id,
            email=cls.sa_email,
            full_name="Phase 3 Super Admin",
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
            name=f"Phase 3 Org Alpha {uuid.uuid4().hex[:4]}",
            domain="alpha.p3",
            status="ACTIVE"
        )
        cls.db.add(cls.org_a)
        cls.db.commit()
        cls.db.refresh(cls.org_a)

        cls.user_a_email = f"user_a_{uuid.uuid4().hex[:6]}@alpha.p3"
        cls.user_a = models.User(
            org_id=cls.org_a.id,
            email=cls.user_a_email,
            full_name="User Alpha P3",
            role="ADMIN",
            status="ACTIVE"
        )
        cls.db.add(cls.user_a)
        cls.db.commit()
        cls.db.refresh(cls.user_a)
        cls.user_a_token = security.create_access_token(
            cls.user_a.id, email=cls.user_a.email, role=cls.user_a.role
        )

        cls.agent_a = models.Agent(
            agent_code=f"AG-P3-A-{uuid.uuid4().hex[:4].upper()}",
            org_id=cls.org_a.id,
            owner_id=cls.user_a.id,
            name="Alpha Payment Bot P3",
            department="Finance",
            purpose="Process financial decisions",
            environment="PRODUCTION",
            autonomy_level="MEDIUM",
            status="ACTIVE",
            risk_score=20,
            daily_budget=50000.0
        )
        cls.db.add(cls.agent_a)
        cls.db.commit()
        cls.db.refresh(cls.agent_a)

        # 3. Organization Beta & User Beta & Agent Beta
        cls.org_b = models.Organization(
            name=f"Phase 3 Org Beta {uuid.uuid4().hex[:4]}",
            domain="beta.p3",
            status="ACTIVE"
        )
        cls.db.add(cls.org_b)
        cls.db.commit()
        cls.db.refresh(cls.org_b)

        cls.user_b_email = f"user_b_{uuid.uuid4().hex[:6]}@beta.p3"
        cls.user_b = models.User(
            org_id=cls.org_b.id,
            email=cls.user_b_email,
            full_name="User Beta P3",
            role="ADMIN",
            status="ACTIVE"
        )
        cls.db.add(cls.user_b)
        cls.db.commit()
        cls.db.refresh(cls.user_b)
        cls.user_b_token = security.create_access_token(
            cls.user_b.id, email=cls.user_b.email, role=cls.user_b.role
        )

        cls.agent_b = models.Agent(
            agent_code=f"AG-P3-B-{uuid.uuid4().hex[:4].upper()}",
            org_id=cls.org_b.id,
            owner_id=cls.user_b.id,
            name="Beta Data Agent P3",
            department="Data",
            purpose="Process data export tasks",
            environment="PRODUCTION",
            autonomy_level="HIGH",
            status="ACTIVE",
            risk_score=25,
            daily_budget=30000.0
        )
        cls.db.add(cls.agent_b)
        cls.db.commit()
        cls.db.refresh(cls.agent_b)

        # Seed specific known decisions for Org A
        now = datetime.datetime.utcnow()
        cls.dec_a1 = models.Decision(
            agent_id=cls.agent_a.id,
            intent_summary="Standard vendor payment",
            action_requested="execute_payment",
            resource_target="payment_api",
            decision="ALLOW",
            policy_name="Standard Limits",
            explanation="Approved within standard vendor payment limits",
            risk_score=20.0,
            amount=150.0,
            timestamp=now - datetime.timedelta(hours=2)
        )
        cls.dec_a2 = models.Decision(
            agent_id=cls.agent_a.id,
            intent_summary="International wire transfer",
            action_requested="wire_transfer",
            resource_target="swift_network",
            decision="REFUSE",
            policy_name="Anti Fraud",
            explanation="Refused due to abnormal wire amount and high risk score",
            risk_score=80.0,
            amount=5000.0,
            timestamp=now - datetime.timedelta(hours=1)
        )
        cls.dec_b1 = models.Decision(
            agent_id=cls.agent_b.id,
            intent_summary="Customer data export",
            action_requested="data_export",
            resource_target="customer_db",
            decision="ALLOW",
            policy_name="Data Access",
            explanation="Permitted under normal data analytics access scope",
            risk_score=10.0,
            amount=0.0,
            timestamp=now - datetime.timedelta(hours=3)
        )
        cls.db.add_all([cls.dec_a1, cls.dec_a2, cls.dec_b1])
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        # Clean up test decisions and dependent approval requests
        cls.db.query(models.ApprovalRequest).filter(
            models.ApprovalRequest.agent_id.in_([cls.agent_a.id, cls.agent_b.id])
        ).delete(synchronize_session=False)
        cls.db.query(models.Decision).filter(
            models.Decision.agent_id.in_([cls.agent_a.id, cls.agent_b.id])
        ).delete(synchronize_session=False)
        cls.db.query(models.WebhookDelivery).delete(synchronize_session=False)
        cls.db.query(models.WebhookEndpoint).filter(
            models.WebhookEndpoint.org_id.in_([cls.org_a.id, cls.org_b.id])
        ).delete(synchronize_session=False)
        cls.db.commit()
        cls.db.close()

    # ==========================================
    # TEST 1: Tenant analytics only returns tenant data
    # ==========================================
    def test_01_tenant_analytics_only_returns_tenant_data(self):
        resp = client.get(
            "/api/v1/analytics/overview",
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # Org A has 2 decisions: 1 ALLOW, 1 REFUSE
        self.assertEqual(data["total_decisions"], 2)
        self.assertEqual(data["allowed"], 1)
        self.assertEqual(data["refused"], 1)

    # ==========================================
    # TEST 2: Cross-tenant analytics request rejected
    # ==========================================
    def test_02_cross_tenant_analytics_request_rejected(self):
        # Org A user attempts to request Org B's context
        resp = client.get(
            "/api/v1/analytics/overview",
            headers={
                "Authorization": f"Bearer {self.user_a_token}",
                "X-Organization-Context": str(self.org_b.id)
            }
        )
        self.assertEqual(resp.status_code, 403, "Cross-tenant context attempt must be rejected with 403")

    # ==========================================
    # TEST 3: SUPER_ADMIN platform analytics works
    # ==========================================
    def test_03_super_admin_platform_analytics_works(self):
        resp = client.get(
            "/api/v1/platform/overview",
            headers={"Authorization": f"Bearer {self.sa_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("total_organizations", data)
        self.assertIn("total_users", data)
        self.assertIn("total_ai_agents", data)
        self.assertGreaterEqual(data["total_organizations"], 2)

    # ==========================================
    # TEST 4: Decision counts match database records
    # ==========================================
    def test_04_decision_counts_match_db_records(self):
        db_count = self.db.query(models.Decision).join(models.Agent).filter(
            models.Agent.org_id == self.org_a.id
        ).count()
        resp = client.get(
            "/api/v1/analytics/overview",
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_decisions"], db_count)

    # ==========================================
    # TEST 5: Risk averages match database records
    # ==========================================
    def test_05_risk_averages_match_db_records(self):
        # Org A decisions have risk 20.0 and 80.0 -> average is 50.0
        resp = client.get(
            "/api/v1/analytics/overview",
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["avg_risk_score"], 50.0)
        self.assertEqual(data["max_risk_score"], 80.0)

    # ==========================================
    # TEST 6: Time-series aggregation uses actual timestamps
    # ==========================================
    def test_06_time_series_aggregation_uses_actual_timestamps(self):
        resp = client.get(
            "/api/v1/analytics/time-series?range=24h",
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["range"], "24h")
        self.assertIsInstance(data["data"], list)
        total_time_series_decisions = sum(d["decisions"] for d in data["data"])
        self.assertEqual(total_time_series_decisions, 2)

    # ==========================================
    # TEST 7: Policy statistics reflect actual policy decisions
    # ==========================================
    def test_07_policy_statistics_reflect_actual_policy_decisions(self):
        resp = client.get(
            "/api/v1/analytics/by-policy",
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        policy_names = [p["policy_name"] for p in data]
        self.assertIn("Standard Limits", policy_names)
        self.assertIn("Anti Fraud", policy_names)

    # ==========================================
    # TEST 8: Report generation contains real database metrics
    # ==========================================
    def test_08_report_generation_contains_real_db_metrics(self):
        resp = client.post(
            "/api/v1/reports/generate",
            json={"report_type": "EXECUTIVE", "file_format": "PDF"},
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertIn("report_id", data)
        self.assertGreater(data["file_size_bytes"], 0)

        # Verify ReportHistory recorded in DB
        rep_hist = self.db.query(models.ReportHistory).filter(
            models.ReportHistory.id == data["report_id"]
        ).first()
        self.assertIsNotNone(rep_hist)
        self.assertEqual(str(rep_hist.org_id), str(self.org_a.id))

    # ==========================================
    # TEST 9: Cross-tenant report download rejected
    # ==========================================
    def test_09_cross_tenant_report_download_rejected(self):
        # Generate report for Org A
        gen_resp = client.post(
            "/api/v1/reports/generate",
            json={"report_type": "GOVERNANCE", "file_format": "CSV"},
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(gen_resp.status_code, 200)
        report_id = gen_resp.json()["report_id"]

        # Org B user attempts to download Org A's report
        down_resp = client.get(
            f"/api/v1/reports/download/{report_id}",
            headers={"Authorization": f"Bearer {self.user_b_token}"}
        )
        self.assertEqual(down_resp.status_code, 403, "Cross-tenant report download must be rejected with 403")

    # ==========================================
    # TEST 10: Webhook secret never appears in API response
    # ==========================================
    def test_10_webhook_secret_never_appears_in_api_response(self):
        # Create webhook
        create_resp = client.post(
            "/api/v1/webhooks",
            json={
                "name": "SIEM Webhook",
                "url": "https://siem.enterprise.corp/events",
                "event_types": ["decision.refused", "security.incident_created"]
            },
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(create_resp.status_code, 201)
        webhook_id = create_resp.json()["id"]

        # GET /webhooks - secret should NOT appear, only preview
        list_resp = client.get(
            "/api/v1/webhooks",
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(list_resp.status_code, 200)
        wh = [w for w in list_resp.json() if w["id"] == webhook_id][0]
        self.assertNotIn("secret_key", wh)
        self.assertTrue(wh["secret_preview"].startswith("whsec_****"))

        # GET /webhooks/{id} - secret should NOT appear
        detail_resp = client.get(
            f"/api/v1/webhooks/{webhook_id}",
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(detail_resp.status_code, 200)
        self.assertNotIn("secret_key", detail_resp.json())

    # ==========================================
    # TEST 11: Webhook signature generated correctly
    # ==========================================
    def test_11_webhook_signature_generated_correctly(self):
        secret = "whsec_supersecretkey12345678"
        payload = '{"event":"decision.created","status":"ALLOW"}'
        timestamp = "1727600000"
        sig = compute_webhook_signature(secret, payload, timestamp)
        self.assertTrue(sig.startswith("sha256="))

        # Verify manual HMAC computation matches
        signed_payload = f"{timestamp}.{payload}".encode("utf-8")
        expected_hash = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
        self.assertEqual(sig, f"sha256={expected_hash}")

    # ==========================================
    # TEST 12: Webhook delivery failure is recorded
    # ==========================================
    def test_12_webhook_delivery_failure_is_recorded(self):
        # Create webhook with non-existent public URL
        wh = models.WebhookEndpoint(
            org_id=self.org_a.id,
            name="Failing Endpoint",
            url="https://nonexistent-domain-agentguard-fail.invalid/events",
            secret_key="whsec_testkey",
            secret_hash="hash",
            secret_preview="whsec_****tkey",
            is_active=True
        )
        self.db.add(wh)
        self.db.commit()
        self.db.refresh(wh)

        success = dispatch_webhook_delivery(
            db=self.db,
            webhook=wh,
            event_type="test.event",
            payload={"msg": "ping"},
            max_retries=2
        )
        self.assertFalse(success)

        # Verify delivery record exists and is marked FAILED
        delivery = self.db.query(models.WebhookDelivery).filter(
            models.WebhookDelivery.webhook_id == wh.id
        ).order_by(models.WebhookDelivery.created_at.desc()).first()
        self.assertIsNotNone(delivery)
        self.assertEqual(delivery.status, "FAILED")
        self.assertGreater(delivery.attempt_count, 0)
        self.assertIsNotNone(delivery.error_message)

    # ==========================================
    # TEST 13: Webhook retry is bounded
    # ==========================================
    def test_13_webhook_retry_is_bounded(self):
        wh = self.db.query(models.WebhookEndpoint).filter(
            models.WebhookEndpoint.name == "Failing Endpoint"
        ).first()
        self.assertIsNotNone(wh)
        # Attempt count should not exceed max_retries
        delivery = self.db.query(models.WebhookDelivery).filter(
            models.WebhookDelivery.webhook_id == wh.id
        ).order_by(models.WebhookDelivery.created_at.desc()).first()
        self.assertLessEqual(delivery.attempt_count, 3)

    # ==========================================
    # TEST 14: Disabled webhook is not delivered
    # ==========================================
    def test_14_disabled_webhook_is_not_delivered(self):
        wh_disabled = models.WebhookEndpoint(
            org_id=self.org_a.id,
            name="Disabled Webhook",
            url="https://example.com/webhook",
            secret_key="whsec_testkey",
            secret_hash="hash",
            secret_preview="whsec_****tkey",
            is_active=False
        )
        self.db.add(wh_disabled)
        self.db.commit()
        self.db.refresh(wh_disabled)

        success = dispatch_webhook_delivery(
            db=self.db,
            webhook=wh_disabled,
            event_type="decision.created",
            payload={"test": 1}
        )
        self.assertFalse(success)
        # No delivery should be logged for inactive webhook
        count = self.db.query(models.WebhookDelivery).filter(
            models.WebhookDelivery.webhook_id == wh_disabled.id
        ).count()
        self.assertEqual(count, 0)

    # ==========================================
    # TEST 15: Approval escalation creates notification event
    # ==========================================
    def test_15_approval_escalation_creates_notification_event(self):
        # Create an overdue approval request
        app_req = models.ApprovalRequest(
            decision_id=self.dec_a2.id,
            agent_id=self.agent_a.id,
            amount=5000.0,
            reason="High risk threshold exceeded",
            status="PENDING",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=26)
        )
        self.db.add(app_req)
        self.db.commit()

        resp = client.post(
            "/api/v1/approvals/escalate",
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(data["overdue_escalated"], 1)

        # Check in-app notification was created
        notif = self.db.query(models.Notification).filter(
            models.Notification.title.contains("Approval Overdue")
        ).order_by(models.Notification.created_at.desc()).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.severity, "WARNING")

    # ==========================================
    # TEST 16: No fake analytics constants remain in production analytics services
    # ==========================================
    def test_16_no_fake_analytics_constants_in_production(self):
        # Inspect router files directly to verify no fake constants remain
        routers_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "routers"))
        files_to_check = ["analytics.py", "risk.py", "platform.py"]
        fake_tokens = ["1,420,890", "1.42M", "24.5 GB", "or 18", "99.94%"]

        for fname in files_to_check:
            fpath = os.path.join(routers_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            for token in fake_tokens:
                self.assertNotIn(
                    token,
                    content,
                    f"Forbidden fake constant '{token}' found in {fname}"
                )

    # ==========================================
    # TEST 17: Integration status does not claim CONNECTED without verification
    # ==========================================
    def test_17_integration_status_does_not_claim_connected_without_verification(self):
        resp = client.get(
            "/api/v1/integrations",
            headers={"Authorization": f"Bearer {self.user_a_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        integrations = resp.json()
        self.assertIsInstance(integrations, list)

        # Check that OpenAI, Anthropic, Gemini are NOT falsely labeled CONNECTED if env vars missing
        for item in integrations:
            if item.get("category") == "LLM Providers":
                self.assertNotEqual(
                    item.get("status"),
                    "CONNECTED",
                    f"LLM Provider {item.get('name')} must not claim CONNECTED without verified live key"
                )

    # ==========================================
    # TEST 18: Phase 1 authentication regression
    # ==========================================
    def test_18_phase1_authentication_regression(self):
        # Unauthenticated calls must return 401
        endpoints = [
            "/api/v1/analytics/overview",
            "/api/v1/reports/history",
            "/api/v1/webhooks",
            "/api/v1/approvals"
        ]
        for ep in endpoints:
            resp = client.get(ep)
            self.assertEqual(resp.status_code, 401, f"{ep} must require authentication (401)")

    # ==========================================
    # TEST 19: Phase 2 policy enforcement regression
    # ==========================================
    def test_19_phase2_policy_enforcement_regression(self):
        from engines.policy_evaluator import evaluate_condition
        # Evaluate policy engine condition evaluation function
        context = {"amount": 7500.0, "risk_score": 85, "action": "fund_transfer"}
        cond = "amount > 5000"
        self.assertTrue(evaluate_condition(cond, context))

        cond_risk = "risk_score >= 80"
        self.assertTrue(evaluate_condition(cond_risk, context))


if __name__ == "__main__":
    unittest.main()
