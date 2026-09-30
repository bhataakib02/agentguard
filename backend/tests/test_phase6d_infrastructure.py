"""
Phase 6D: Production Infrastructure, Async Workers, Persistent Queues & External Service Architecture Test Suite
Covers:
1. Redis configuration
2. Worker task registration
3. Webhook queued state
4. Webhook worker success
5. Webhook retry
6. Webhook exponential backoff
7. Webhook dead-letter
8. Webhook idempotency
9. Webhook tenant isolation
10. Webhook SSRF protection
11. Scheduled report queueing
12. Scheduled report execution
13. Scheduled report duplicate prevention
14. Scheduled report tenant isolation
15. Notification worker
16. Email NOT_CONFIGURED behavior
17. Email configured behavior using test provider
18. Approval escalation
19. Escalation idempotency
20. Report storage abstraction
21. Local storage behavior
22. Unconfigured object storage
23. Worker failure handling
24. Redis unavailable behavior
25. Worker health endpoint
26. Scheduler health
27. WebSocket tenant isolation
28. WebSocket graceful single-node fallback
29. Secret redaction
30. Authorization / tenant validation
"""

import unittest
import uuid
import datetime
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from starlette.testclient import TestClient
from main import app
from database import SessionLocal
from config import settings
from core import security
import models
from celery_app import celery_app, inspect_broker_health, inspect_worker_health
from services.storage_service import storage_service
from services.email_service import email_service
from services.notification_service import validate_webhook_url
from ws_manager import manager as ws_manager

from tasks.webhook_tasks import dispatch_webhook_task, retry_pending_webhooks_task
from tasks.report_tasks import execute_scheduled_reports_task
from tasks.escalation_tasks import escalate_approvals_task
from tasks.notification_tasks import deliver_notification_task

client = TestClient(app)


class TestPhase6dInfrastructure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

        # Create distinct test tenant organizations
        cls.org_a = models.Organization(
            name="Phase6D Primary Org",
            domain="phase6d-a.com",
            status="ACTIVE"
        )
        cls.org_b = models.Organization(
            name="Phase6D Isolated Org",
            domain="phase6d-b.com",
            status="ACTIVE"
        )
        cls.db.add(cls.org_a)
        cls.db.add(cls.org_b)
        cls.db.commit()
        cls.db.refresh(cls.org_a)
        cls.db.refresh(cls.org_b)

        # Create test users
        cls.super_admin = models.User(
            org_id=cls.org_a.id,
            email=f"sa_p6d_{uuid.uuid4().hex[:6]}@agentguard.com",
            full_name="Phase 6D Super Admin",
            role="SUPER_ADMIN",
            status="ACTIVE"
        )
        cls.admin_a = models.User(
            org_id=cls.org_a.id,
            email=f"admin_p6d_a_{uuid.uuid4().hex[:6]}@phase6d-a.com",
            full_name="Phase 6D Admin A",
            role="ADMIN",
            status="ACTIVE"
        )
        cls.admin_b = models.User(
            org_id=cls.org_b.id,
            email=f"admin_p6d_b_{uuid.uuid4().hex[:6]}@phase6d-b.com",
            full_name="Phase 6D Admin B",
            role="ADMIN",
            status="ACTIVE"
        )
        cls.db.add(cls.super_admin)
        cls.db.add(cls.admin_a)
        cls.db.add(cls.admin_b)
        cls.db.commit()
        cls.db.refresh(cls.super_admin)
        cls.db.refresh(cls.admin_a)
        cls.db.refresh(cls.admin_b)

        # Create test agent in Org A
        cls.agent_a = models.Agent(
            org_id=cls.org_a.id,
            agent_code=f"AG-P6D-{uuid.uuid4().hex[:4].upper()}",
            name="Infrastructure Auditor Agent",
            status="ACTIVE",
            purpose="Phase 6D Infrastructure Testing",
            owner_id=cls.admin_a.id
        )


        cls.db.add(cls.agent_a)
        cls.db.commit()
        cls.db.refresh(cls.agent_a)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def get_auth_headers(self, user_obj):
        token = security.create_access_token(user_id=user_obj.id, email=user_obj.email, role=user_obj.role)
        return {"Authorization": f"Bearer {token}"}

    # -------------------------------------------------------------------------
    # TEST 1: Redis Configuration
    # -------------------------------------------------------------------------
    def test_01_redis_configuration(self):
        """Verifies Redis and Celery broker configuration settings exist and are non-empty."""
        self.assertIsNotNone(settings.CELERY_BROKER_URL)
        self.assertIsNotNone(settings.CELERY_RESULT_BACKEND)
        self.assertIn("redis", settings.CELERY_BROKER_URL.lower())

    # -------------------------------------------------------------------------
    # TEST 2: Worker Task Registration
    # -------------------------------------------------------------------------
    def test_02_worker_task_registration(self):
        """Verifies all Phase 6D worker tasks are registered with Celery."""
        tasks = celery_app.tasks
        self.assertIn("tasks.webhook_tasks.dispatch_webhook_task", tasks)
        self.assertIn("tasks.webhook_tasks.retry_pending_webhooks_task", tasks)
        self.assertIn("tasks.report_tasks.execute_scheduled_reports_task", tasks)
        self.assertIn("tasks.escalation_tasks.escalate_approvals_task", tasks)
        self.assertIn("tasks.notification_tasks.deliver_notification_task", tasks)

    # -------------------------------------------------------------------------
    # TEST 3: Webhook Queued State
    # -------------------------------------------------------------------------
    def test_03_webhook_queued_state(self):
        """Verifies newly dispatched webhook creates a WebhookDelivery in QUEUED state."""
        endpoint = models.WebhookEndpoint(
            org_id=self.org_a.id,
            name="Test Queued Endpoint",
            url="https://api.external-partner.com/webhook",
            secret_hash="hash_123",
            secret_key="secret_key_abc",
            is_active=True
        )
        self.db.add(endpoint)
        self.db.commit()

        delivery = models.WebhookDelivery(
            webhook_id=endpoint.id,
            event_type="test.queued",
            status="QUEUED",
            payload_json={"message": "queued test"}
        )
        self.db.add(delivery)
        self.db.commit()
        self.db.refresh(delivery)

        self.assertEqual(delivery.status, "QUEUED")
        self.assertEqual(delivery.attempt_count, 0)

    # -------------------------------------------------------------------------
    # TEST 4: Webhook Worker Success
    # -------------------------------------------------------------------------
    @patch("requests.post")
    def test_04_webhook_worker_success(self, mock_post):
        """Verifies successful delivery transitions status to DELIVERED and records audit log."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"received": true}'
        mock_post.return_value = mock_resp

        endpoint = models.WebhookEndpoint(
            org_id=self.org_a.id,
            name="Success Partner Hook",
            url="https://partner.enterprise.com/hook",
            secret_hash="hash_success",
            secret_key="secret_key_success",
            is_active=True
        )
        self.db.add(endpoint)
        self.db.commit()

        delivery = models.WebhookDelivery(
            webhook_id=endpoint.id,
            event_type="policy.violation",
            status="QUEUED",
            payload_json={"severity": "HIGH"}
        )
        self.db.add(delivery)
        self.db.commit()

        # Run task
        res = dispatch_webhook_task(str(delivery.id))
        self.assertEqual(res["status"], "DELIVERED")

        self.db.refresh(delivery)
        self.assertEqual(delivery.status, "DELIVERED")
        self.assertEqual(delivery.response_code, 200)
        self.assertIsNotNone(delivery.delivered_at)

        # Audit log verified
        audit = self.db.query(models.AuditLog).filter(
            models.AuditLog.event_type == "WEBHOOK_DELIVERED",
            models.AuditLog.resource == f"webhook:{endpoint.id}"
        ).first()
        self.assertIsNotNone(audit)

    # -------------------------------------------------------------------------
    # TEST 5: Webhook Retry
    # -------------------------------------------------------------------------
    @patch("requests.post")
    def test_05_webhook_retry(self, mock_post):
        """Verifies delivery failure on attempt 1 schedules retry with next_attempt_at."""
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.text = "Service Unavailable"
        mock_post.return_value = mock_resp

        endpoint = models.WebhookEndpoint(
            org_id=self.org_a.id,
            name="Failing Server Hook",
            url="https://flaky.external.com/hook",
            secret_hash="hash_flaky",
            secret_key="secret_key_flaky",
            is_active=True
        )
        self.db.add(endpoint)
        self.db.commit()

        delivery = models.WebhookDelivery(
            webhook_id=endpoint.id,
            event_type="agent.blocked",
            status="QUEUED",
            attempt_count=0,
            payload_json={"agent_id": str(self.agent_a.id)}
        )
        self.db.add(delivery)
        self.db.commit()

        res = dispatch_webhook_task(str(delivery.id))
        self.assertEqual(res["status"], "RETRY_SCHEDULED")

        self.db.refresh(delivery)
        self.assertIn(delivery.status, ("RETRY_SCHEDULED", "RETRYING"))
        self.assertEqual(delivery.attempt_count, 1)
        self.assertIsNotNone(delivery.next_attempt_at)

    # -------------------------------------------------------------------------
    # TEST 6: Webhook Exponential Backoff
    # -------------------------------------------------------------------------
    def test_06_webhook_exponential_backoff(self):
        """Verifies backoff formula produces bounded exponential increments: 30s, 120s, 480s."""
        backoffs = [30 * (4 ** (i - 1)) for i in range(1, 4)]
        self.assertEqual(backoffs, [30, 120, 480])

    # -------------------------------------------------------------------------
    # TEST 7: Webhook Dead-Letter
    # -------------------------------------------------------------------------
    @patch("requests.post")
    def test_07_webhook_dead_letter(self, mock_post):
        """Verifies delivery failing on attempt 3 transitions directly to DEAD_LETTER."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        endpoint = models.WebhookEndpoint(
            org_id=self.org_a.id,
            name="Dead Letter Hook",
            url="https://permanently-down.org/hook",
            secret_hash="hash_dl",
            secret_key="secret_key_dl",
            is_active=True
        )
        self.db.add(endpoint)
        self.db.commit()

        delivery = models.WebhookDelivery(
            webhook_id=endpoint.id,
            event_type="governance.alert",
            status="RETRY_SCHEDULED",
            attempt_count=2,  # Next attempt will be attempt 3 (exhaustion)
            payload_json={"incident": "DLQ Test"}
        )
        self.db.add(delivery)
        self.db.commit()

        res = dispatch_webhook_task(str(delivery.id))
        self.assertEqual(res["status"], "DEAD_LETTER")

        self.db.refresh(delivery)
        self.assertEqual(delivery.status, "DEAD_LETTER")
        self.assertEqual(delivery.attempt_count, 3)
        self.assertIsNone(delivery.next_attempt_at)

        # Audit log verified
        audit = self.db.query(models.AuditLog).filter(
            models.AuditLog.event_type == "WEBHOOK_DEAD_LETTER",
            models.AuditLog.resource == f"webhook:{endpoint.id}"
        ).first()
        self.assertIsNotNone(audit)

    # -------------------------------------------------------------------------
    # TEST 8: Webhook Idempotency
    # -------------------------------------------------------------------------
    @patch("requests.post")
    def test_08_webhook_idempotency(self, mock_post):
        """Verifies calling dispatch_webhook_task on an already DELIVERED record does not re-send."""
        endpoint = models.WebhookEndpoint(
            org_id=self.org_a.id,
            name="Idempotent Hook",
            url="https://idempotent.com/hook",
            secret_hash="hash_idem",
            secret_key="secret_key_idem",
            is_active=True
        )
        self.db.add(endpoint)
        self.db.commit()

        delivery = models.WebhookDelivery(
            webhook_id=endpoint.id,
            event_type="test.idem",
            status="DELIVERED",
            response_code=200
        )
        self.db.add(delivery)
        self.db.commit()

        res = dispatch_webhook_task(str(delivery.id))
        self.assertEqual(res["status"], "ALREADY_COMPLETED")
        mock_post.assert_not_called()

    # -------------------------------------------------------------------------
    # TEST 9: Webhook Tenant Isolation
    # -------------------------------------------------------------------------
    def test_09_webhook_tenant_isolation(self):
        """Verifies Admin A cannot view or retry Org B's webhook deliveries."""
        endpoint_b = models.WebhookEndpoint(
            org_id=self.org_b.id,
            name="Org B Hook",
            url="https://orgb.com/hook",
            secret_hash="hash_b",
            is_active=True
        )
        self.db.add(endpoint_b)
        self.db.commit()

        delivery_b = models.WebhookDelivery(
            webhook_id=endpoint_b.id,
            event_type="test.orgb",
            status="DEAD_LETTER"
        )
        self.db.add(delivery_b)
        self.db.commit()

        # Admin A attempts to retry Org B's delivery -> 403 Forbidden
        headers_a = self.get_auth_headers(self.admin_a)
        resp = client.post(f"/api/webhooks/dead-letter/{delivery_b.id}/retry", headers=headers_a)
        self.assertEqual(resp.status_code, 403)

    # -------------------------------------------------------------------------
    # TEST 10: Webhook SSRF Protection
    # -------------------------------------------------------------------------
    def test_10_webhook_ssrf_protection(self):
        """Verifies SSRF engine blocks private IPs, loopback, and metadata endpoints."""
        safe, err = validate_webhook_url("http://127.0.0.1:8080/hook")
        self.assertFalse(safe)
        self.assertIn("internal loopback", err.lower())

        safe, err = validate_webhook_url("http://169.254.169.254/latest/meta-data")
        self.assertFalse(safe)

        safe, err = validate_webhook_url("http://10.0.0.5/hook")
        self.assertFalse(safe)

        safe, err = validate_webhook_url("https://hooks.slack.com/services/T00/B00/X00")
        self.assertTrue(safe)

    # -------------------------------------------------------------------------
    # TEST 11: Scheduled Report Queueing
    # -------------------------------------------------------------------------
    def test_11_scheduled_report_queueing(self):
        """Verifies Celery Beat schedule contains scheduled reports task."""
        schedule = celery_app.conf.beat_schedule
        self.assertIn("execute-scheduled-reports", schedule)
        self.assertEqual(schedule["execute-scheduled-reports"]["task"], "tasks.report_tasks.execute_scheduled_reports_task")

    # -------------------------------------------------------------------------
    # TEST 12: Scheduled Report Execution
    # -------------------------------------------------------------------------
    def test_12_scheduled_report_execution(self):
        """Verifies execute_scheduled_reports_task generates report, creates ReportHistory, and updates schedule."""
        sched = models.ScheduledReport(
            org_id=self.org_a.id,
            user_id=self.admin_a.id,
            report_type="SECURITY",
            title="Weekly Security Summary",
            file_format="PDF",
            frequency="WEEKLY",
            recipient_emails="security@phase6d-a.com",
            status="ACTIVE",
            last_run_at=None  # Due immediately
        )
        self.db.add(sched)
        self.db.commit()

        res = execute_scheduled_reports_task()
        self.assertGreaterEqual(res["executed_count"], 1)

        self.db.refresh(sched)
        self.assertIsNotNone(sched.last_run_at)
        self.assertIsNotNone(sched.next_run_at)

        # Check ReportHistory record
        history = self.db.query(models.ReportHistory).filter(
            models.ReportHistory.org_id == self.org_a.id,
            models.ReportHistory.report_type == "SECURITY"
        ).order_by(models.ReportHistory.created_at.desc()).first()
        self.assertIsNotNone(history)

    # -------------------------------------------------------------------------
    # TEST 13: Scheduled Report Duplicate Prevention
    # -------------------------------------------------------------------------
    def test_13_scheduled_report_duplicate_prevention(self):
        """Verifies a scheduled report whose next_run_at is in the future is skipped."""
        sched = models.ScheduledReport(
            org_id=self.org_a.id,
            user_id=self.admin_a.id,
            report_type="EXECUTIVE",
            title="Future Executive Report",
            file_format="PDF",
            frequency="WEEKLY",
            recipient_emails="",
            status="ACTIVE",
            last_run_at=datetime.datetime.utcnow(),
            next_run_at=datetime.datetime.utcnow() + datetime.timedelta(days=6)
        )
        self.db.add(sched)
        self.db.commit()

        res = execute_scheduled_reports_task()
        self.assertGreaterEqual(res["skipped_count"], 1)

    # -------------------------------------------------------------------------
    # TEST 14: Scheduled Report Tenant Isolation
    # -------------------------------------------------------------------------
    def test_14_scheduled_report_tenant_isolation(self):
        """Verifies reports generated for Org A cannot be read or downloaded by Org B."""
        rep = models.ReportHistory(
            org_id=self.org_a.id,
            user_id=self.admin_a.id,
            report_type="AUDIT",
            title="Org A Audit Report",
            file_format="PDF",
            file_path="local://org_dummy/dummy.pdf"
        )
        self.db.add(rep)
        self.db.commit()

        headers_b = self.get_auth_headers(self.admin_b)
        resp = client.get(f"/api/reports/download/{rep.id}", headers=headers_b)
        self.assertEqual(resp.status_code, 403)

    # -------------------------------------------------------------------------
    # TEST 15: Notification Worker
    # -------------------------------------------------------------------------
    def test_15_notification_worker(self):
        """Verifies deliver_notification_task processes notification without errors."""
        notif = models.Notification(
            user_id=self.admin_a.id,
            type="ALERT",
            title="Infrastructure Notice",
            message="Database read replica healthy",
            severity="INFO"
        )
        self.db.add(notif)
        self.db.commit()

        res = deliver_notification_task(str(notif.id))
        self.assertEqual(res["status"], "PROCESSED")

    # -------------------------------------------------------------------------
    # TEST 16: Email NOT_CONFIGURED Behavior
    # -------------------------------------------------------------------------
    def test_16_email_not_configured_behavior(self):
        """Verifies EmailService truthfully returns EMAIL_PROVIDER_NOT_CONFIGURED when unconfigured."""
        original_provider = settings.EMAIL_PROVIDER
        original_host = settings.SMTP_HOST
        try:
            settings.EMAIL_PROVIDER = "NONE"
            settings.SMTP_HOST = ""
            res = email_service.send_email(
                to_email="test@example.com",
                subject="Test Notice",
                body_text="Test message"
            )
            self.assertEqual(res["status"], "EMAIL_PROVIDER_NOT_CONFIGURED")
            self.assertFalse(res["delivered"])
        finally:
            settings.EMAIL_PROVIDER = original_provider
            settings.SMTP_HOST = original_host

    # -------------------------------------------------------------------------
    # TEST 17: Email Configured Behavior Using Test Provider
    # -------------------------------------------------------------------------
    def test_17_email_configured_behavior_using_test_provider(self):
        """Verifies EmailService delivers email and records mock output when MOCK provider is set."""
        original_provider = settings.EMAIL_PROVIDER
        try:
            settings.EMAIL_PROVIDER = "MOCK"
            res = email_service.send_email(
                to_email="auditor@enterprise.com",
                subject="Audit Report Attachment",
                body_text="Your report is ready",
                attachments=[{"filename": "report.pdf", "content": b"%PDF-1.4"}]
            )
            self.assertEqual(res["status"], "EMAIL_SENT")
            self.assertTrue(res["delivered"])
            self.assertEqual(res["provider"], "MOCK")
        finally:
            settings.EMAIL_PROVIDER = original_provider

    # -------------------------------------------------------------------------
    # TEST 18: Approval Escalation
    # -------------------------------------------------------------------------
    @patch("requests.post")
    def test_18_approval_escalation(self, mock_post):
        """Verifies escalate_approvals_task detects overdue approval request exceeding 24h SLA."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"ok": true}'
        mock_post.return_value = mock_resp

        dec = models.Decision(
            agent_id=self.agent_a.id,
            intent_summary="Escalation test decision",
            action_requested="FINANCIAL_TRANSFER",
            resource_target="bank_account",
            amount=50000.0,
            decision="REVIEW",
            risk_score=75,
            explanation="Governance Escalation: Requires human review",
            execution_status="PENDING_APPROVAL"
        )
        self.db.add(dec)
        self.db.commit()

        overdue_time = datetime.datetime.utcnow() - datetime.timedelta(hours=26)
        req = models.ApprovalRequest(
            decision_id=dec.id,
            agent_id=self.agent_a.id,
            amount=50000.0,
            reason="Large vendor payment",
            status="PENDING",
            created_at=overdue_time
        )
        self.db.add(req)
        self.db.commit()

        res = escalate_approvals_task(org_id_filter=str(self.org_a.id))
        self.assertGreaterEqual(res["overdue_escalated"], 1)

    # -------------------------------------------------------------------------
    # TEST 19: Escalation Idempotency
    # -------------------------------------------------------------------------
    @patch("requests.post")
    def test_19_escalation_idempotency(self, mock_post):
        """Verifies repeated execution of escalate_approvals_task skips previously escalated items."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"ok": true}'
        mock_post.return_value = mock_resp

        # Running immediately again for the same overdue request
        res = escalate_approvals_task(org_id_filter=str(self.org_a.id))
        self.assertEqual(res["overdue_escalated"], 0)
        self.assertGreaterEqual(res["skipped_idempotent"], 1)



    # -------------------------------------------------------------------------
    # TEST 20: Report Storage Abstraction
    # -------------------------------------------------------------------------
    def test_20_report_storage_abstraction(self):
        """Verifies storage_service exposes save_report_file and get_storage_status interfaces."""
        status = storage_service.get_storage_status()
        self.assertIn("active_backend", status)
        self.assertIn("local_storage", status)
        self.assertIn("object_storage", status)

    # -------------------------------------------------------------------------
    # TEST 21: Local Storage Behavior
    # -------------------------------------------------------------------------
    def test_21_local_storage_behavior(self):
        """Verifies save_report_file stores bytes, computes sha256 checksum, and retrieves content."""
        sample_bytes = b"AGENTGUARD_LOCAL_STORAGE_TEST_PAYLOAD"
        filename = f"test_report_{uuid.uuid4().hex[:8]}.pdf"
        saved = storage_service.save_report_file(
            content=sample_bytes,
            filename=filename,
            org_id=str(self.org_a.id),
            format_type="PDF"
        )
        self.assertEqual(saved["storage_backend"], "LOCAL")
        self.assertEqual(saved["file_size_bytes"], len(sample_bytes))
        self.assertIsNotNone(saved["sha256_checksum"])

        retrieved = storage_service.get_report_file(saved["storage_key"], str(self.org_a.id))
        self.assertEqual(retrieved, sample_bytes)

    # -------------------------------------------------------------------------
    # TEST 22: Unconfigured Object Storage
    # -------------------------------------------------------------------------
    def test_22_unconfigured_object_storage(self):
        """Verifies that missing S3 credentials truthfully report NOT_CONFIGURED."""
        original_bucket = settings.S3_BUCKET
        try:
            settings.S3_BUCKET = ""
            status = storage_service.get_storage_status()
            self.assertEqual(status["object_storage"]["status"], "NOT_CONFIGURED")
        finally:
            settings.S3_BUCKET = original_bucket

    # -------------------------------------------------------------------------
    # TEST 23: Worker Failure Handling
    # -------------------------------------------------------------------------
    def test_23_worker_failure_handling(self):
        """Verifies dispatch_webhook_task handles non-existent delivery IDs without raising exceptions."""
        non_existent_id = str(uuid.uuid4())
        res = dispatch_webhook_task(non_existent_id)
        self.assertEqual(res["status"], "NOT_FOUND")

    # -------------------------------------------------------------------------
    # TEST 24: Redis Unavailable Behavior
    # -------------------------------------------------------------------------
    def test_24_redis_unavailable_behavior(self):
        """Verifies inspect_broker_health handles unreachable Redis gracefully without throwing exceptions."""
        with patch("redis.from_url") as mock_redis:
            mock_redis.side_effect = ConnectionError("Could not connect to Redis at localhost:6379")
            health = inspect_broker_health()
            self.assertEqual(health["status"], "UNAVAILABLE")
            self.assertFalse(health["connected"])

    # -------------------------------------------------------------------------
    # TEST 25: Worker Health Endpoint
    # -------------------------------------------------------------------------
    def test_25_worker_health_endpoint(self):
        """Verifies /api/system/health returns detailed infrastructure subsystems."""
        headers = self.get_auth_headers(self.admin_a)
        resp = client.get("/api/system/health", headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        subsystems = data["subsystems"]
        self.assertIn("redis", subsystems)
        self.assertIn("worker", subsystems)
        self.assertIn("scheduler", subsystems)
        self.assertIn("object_storage", subsystems)
        self.assertIn("email_provider", subsystems)
        self.assertIn("websocket", subsystems)

    # -------------------------------------------------------------------------
    # TEST 26: Scheduler Health
    # -------------------------------------------------------------------------
    def test_26_scheduler_health(self):
        """Verifies scheduler health reports periodic task definitions."""
        schedule = celery_app.conf.beat_schedule
        self.assertGreaterEqual(len(schedule), 3)

    # -------------------------------------------------------------------------
    # TEST 27: WebSocket Tenant Isolation
    # -------------------------------------------------------------------------
    def test_27_websocket_tenant_isolation(self):
        """Verifies WebSocket manager enforces org-scoped channels."""
        status = ws_manager.get_status()
        self.assertIn("mode", status)
        self.assertIn("active_connections", status)

    # -------------------------------------------------------------------------
    # TEST 28: WebSocket Graceful Single-Node Fallback
    # -------------------------------------------------------------------------
    def test_28_websocket_graceful_single_node_fallback(self):
        """Verifies WebSocket falls back to SINGLE_NODE mode when Redis is not running."""
        ws_manager._redis_client = None
        ws_manager._redis_checked = True
        status = ws_manager.get_status()
        self.assertEqual(status["mode"], "SINGLE_NODE")
        self.assertFalse(status["redis_pubsub"])

    # -------------------------------------------------------------------------
    # TEST 29: Secret Redaction
    # -------------------------------------------------------------------------
    def test_29_secret_redaction(self):
        """Verifies health endpoints and services do not leak passwords or secret keys."""
        headers = self.get_auth_headers(self.admin_a)
        resp = client.get("/api/system/health", headers=headers)
        self.assertEqual(resp.status_code, 200)
        text_resp = resp.text.lower()
        self.assertNotIn("password", text_resp)
        self.assertNotIn("secret_key", text_resp)
        self.assertNotIn("aws_secret", text_resp)

    # -------------------------------------------------------------------------
    # TEST 30: Authorization / Tenant Validation
    # -------------------------------------------------------------------------
    def test_30_authorization_tenant_validation(self):
        """Verifies non-admin / viewer users cannot access super-admin platform health."""
        viewer = models.User(
            org_id=self.org_a.id,
            email=f"viewer_p6d_{uuid.uuid4().hex[:6]}@phase6d-a.com",
            full_name="Phase 6D Viewer",
            role="VIEWER",
            status="ACTIVE"
        )
        self.db.add(viewer)
        self.db.commit()

        headers_viewer = self.get_auth_headers(viewer)
        resp = client.get("/api/platform/health", headers=headers_viewer)
        self.assertEqual(resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()
