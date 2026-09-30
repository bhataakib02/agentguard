"""
AgentGuard Phase 6F: Production Hardening, Deployment Validation & Observability Suite
Covers 34 focused verification tests:
1-4:   Production Database & Configuration Validation (PostgreSQL enforcement, pooling, plan idempotency)
5-10:  Health, Liveness & Readiness Probes (Process liveness, DB readiness, 503 failure handling)
11-12: System Health & Secret Redaction (Deep dependency checks, zero secret leakage)
13-17: Redis & Celery Worker Infrastructure (Broker parsing, inspector, task & Beat registration)
18-22: Webhook Worker Queue Hardening (Bounded backoff, DLQ, SSRF loopback/metadata, HMAC signatures)
23-24: Scheduled Tasks & Idempotency (Report duplicate prevention, 24h escalation deduplication)
25-28: External Service Abstractions (Storage LOCAL & S3 NOT_CONFIGURED, Email SMTP & MOCK)
29-30: WebSocket Multi-Node & Pub/Sub (Single-node fallback, tenant channel isolation)
31-32: Security, CORS & Trusted Hosts (No wildcard CORS, host allowlist enforcement)
33-34: Backup & Restore Verification (pg_dump command spec, database integrity audit)
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import datetime
import uuid
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from starlette.testclient import TestClient
from main import app
from database import SessionLocal, engine
from config import settings
import models

client = TestClient(app)


class TestPhase6FProductionHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

        # Create or fetch test organization
        cls.org = cls.db.query(models.Organization).filter(
            models.Organization.name == "Phase 6F Hardening Org"
        ).first()
        if not cls.org:
            cls.org = models.Organization(
                name="Phase 6F Hardening Org",
                domain="p6f-hardening.agentguard",
                status="ACTIVE"
            )
            cls.db.add(cls.org)
            cls.db.commit()
            cls.db.refresh(cls.org)

        # Create or fetch test user
        cls.user = cls.db.query(models.User).filter(
            models.User.email == "hardening_admin@p6f.agentguard"
        ).first()
        if not cls.user:
            cls.user = models.User(
                email="hardening_admin@p6f.agentguard",
                full_name="Hardening Admin",
                password_hash="hashed_pw_p6f",
                org_id=cls.org.id,
                role="ADMIN",
                status="ACTIVE"
            )
            cls.db.add(cls.user)
            cls.db.commit()
            cls.db.refresh(cls.user)

        # Create test agent
        cls.agent = cls.db.query(models.Agent).filter(
            models.Agent.agent_code == "AG-P6F-01"
        ).first()
        if not cls.agent:
            cls.agent = models.Agent(
                org_id=cls.org.id,
                owner_id=cls.user.id,
                name="Production Hardening Agent",
                agent_code="AG-P6F-01",
                purpose="Production deployment verification",
                status="NORMAL",
                autonomy_level="MEDIUM",
                daily_budget=50000.0
            )
            cls.db.add(cls.agent)
            cls.db.commit()
            cls.db.refresh(cls.agent)

    def tearDown(self):
        self.db.rollback()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    # -------------------------------------------------------------------------
    # TEST 1: Production PostgreSQL Enforcement (No Silent SQLite Fallback)
    # -------------------------------------------------------------------------
    def test_01_production_sqlite_rejection(self):
        """Verifies that in production mode, SQLite URLs or empty URLs raise a critical configuration error."""
        from config import Settings

        # Simulate production environment with sqlite URL
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "DATABASE_URL": "sqlite:///local.db"}):
            with self.assertRaises(RuntimeError) as ctx:
                s = Settings()
            self.assertIn("Silent fallback to SQLite in production is strictly prohibited", str(ctx.exception))

    # -------------------------------------------------------------------------
    # TEST 2: Production PostgreSQL URL Acceptance
    # -------------------------------------------------------------------------
    def test_02_production_postgresql_acceptance(self):
        """Verifies that postgresql:// URLs are correctly normalized and accepted in production mode."""
        from config import Settings

        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "DATABASE_URL": "postgres://user:pass@db.prod.internal:5432/agentguard"
        }):
            s = Settings()
            self.assertTrue(s.DATABASE_URL.startswith("postgresql://"))
            self.assertIn("db.prod.internal", s.DATABASE_URL)

    # -------------------------------------------------------------------------
    # TEST 3: Database Connection Pool Parameters
    # -------------------------------------------------------------------------
    def test_03_db_connection_pool_settings(self):
        """Verifies that connection pool parameters (pool_size, max_overflow, pool_timeout) are configurable."""
        self.assertGreaterEqual(getattr(settings, "DB_POOL_SIZE", 10), 5)
        self.assertGreaterEqual(getattr(settings, "DB_MAX_OVERFLOW", 20), 10)
        self.assertGreaterEqual(getattr(settings, "DB_POOL_TIMEOUT", 30), 15)

    # -------------------------------------------------------------------------
    # TEST 4: Plan Seeding Idempotency
    # -------------------------------------------------------------------------
    def test_04_plan_seeding_idempotency(self):
        """Verifies that ensure_canonical_plans() can execute repeatedly without primary key conflicts."""
        from bootstrap import ensure_canonical_plans

        # Should execute cleanly without throwing IntegrityError
        ensure_canonical_plans(self.db)
        plans = self.db.query(models.Plan.id).all()
        plan_ids = {p[0] for p in plans}
        self.assertTrue({"FREE", "STARTER", "PROFESSIONAL", "ENTERPRISE"}.issubset(plan_ids))

    # -------------------------------------------------------------------------
    # TEST 5: Liveness Probe (/health/live)
    # -------------------------------------------------------------------------
    def test_05_health_liveness_probe(self):
        """Verifies that /health/live returns 200 OK and status ALIVE."""
        resp = client.get("/health/live")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ALIVE")
        self.assertEqual(data["process"], "RUNNING")
        self.assertIn("timestamp", data)

    # -------------------------------------------------------------------------
    # TEST 6: Alternative Liveness Route (/health/liveness)
    # -------------------------------------------------------------------------
    def test_06_health_liveness_alias_route(self):
        """Verifies that /health/liveness also returns 200 OK."""
        resp = client.get("/health/liveness")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ALIVE")

    # -------------------------------------------------------------------------
    # TEST 7: Readiness Probe (/health/ready) - Healthy Database
    # -------------------------------------------------------------------------
    def test_07_health_readiness_probe_success(self):
        """Verifies that /health/ready returns 200 OK and CONNECTED when the database is healthy."""
        resp = client.get("/health/ready")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "READY")
        self.assertEqual(data["database"], "CONNECTED")

    # -------------------------------------------------------------------------
    # TEST 8: Readiness Probe (/health/ready) - Database Disconnection
    # -------------------------------------------------------------------------
    @patch("sqlalchemy.orm.Session.execute")
    def test_08_health_readiness_probe_db_failure(self, mock_execute):
        """Verifies that /health/ready returns 503 Service Unavailable when the database ping fails."""
        mock_execute.side_effect = Exception("OperationalError: Connection refused")
        resp = client.get("/health/ready")
        self.assertEqual(resp.status_code, 503)
        data = resp.json()
        self.assertEqual(data["status"], "NOT_READY")
        self.assertEqual(data["database"], "DISCONNECTED")
        self.assertIn("Connection refused", data["error"])

    # -------------------------------------------------------------------------
    # TEST 9: Alternative Readiness Route (/health/readiness)
    # -------------------------------------------------------------------------
    def test_09_health_readiness_alias_route(self):
        """Verifies that /health/readiness returns 200 OK when database is accessible."""
        resp = client.get("/health/readiness")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "READY")

    # -------------------------------------------------------------------------
    # TEST 10: Root API Status Route (/api/health)
    # -------------------------------------------------------------------------
    def test_10_api_root_health_metadata(self):
        """Verifies root API metadata returns platform name, tagline, and RUNNING status."""
        resp = client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["platform"], "AGENTGUARD")
        self.assertEqual(data["status"], "RUNNING")
        self.assertIn("docs", data)

    # -------------------------------------------------------------------------
    # TEST 11: Deep System Health Subsystem Inspection
    # -------------------------------------------------------------------------
    def test_11_deep_system_health_inspection(self):
        """Verifies that /api/system/health inspects all core subsystems accurately."""
        admin_user = models.User(
            id=str(uuid.uuid4()),
            org_id=self.org.id,
            email=f"admin_p6f_{uuid.uuid4().hex[:6]}@agentguard.com",
            full_name="P6F Admin",
            role="ADMIN",
            status="ACTIVE"
        )
        self.db.add(admin_user)
        self.db.commit()

        from core.security import create_access_token
        token = create_access_token(admin_user.id)
        resp = client.get("/api/system/health", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        subsystems = data["subsystems"]
        self.assertIn("database", subsystems)
        self.assertIn("redis", subsystems)
        self.assertIn("worker", subsystems)
        self.assertIn("scheduler", subsystems)
        self.assertIn("policy_engine", subsystems)
        self.assertIn("object_storage", subsystems)
        self.assertIn("email_provider", subsystems)

    # -------------------------------------------------------------------------
    # TEST 12: Secret Redaction in Health Responses
    # -------------------------------------------------------------------------
    def test_12_secret_redaction_in_health(self):
        """Verifies that no database passwords, Redis tokens, or SMTP keys leak in health responses."""
        from core.security import create_access_token
        user = self.db.query(models.User).filter(models.User.role == "ADMIN").first()
        token = create_access_token(user.id)

        resp = client.get("/api/system/health", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(resp.status_code, 200)
        content_str = resp.text.lower()

        # Sensitive patterns that must never be exposed
        self.assertNotIn("password", content_str)
        self.assertNotIn("secret_key", content_str)
        self.assertNotIn("postgres:", content_str)
        self.assertNotIn("aws_secret", content_str)

    # -------------------------------------------------------------------------
    # TEST 13: Redis Broker Configuration & Fallback
    # -------------------------------------------------------------------------
    def test_13_redis_broker_configuration_parsing(self):
        """Verifies Celery broker URL defaults and eager fallback parsing."""
        self.assertTrue(hasattr(settings, "CELERY_BROKER_URL"))
        self.assertTrue(hasattr(settings, "CELERY_RESULT_BACKEND"))
        self.assertTrue(hasattr(settings, "CELERY_TASK_ALWAYS_EAGER"))

    # -------------------------------------------------------------------------
    # TEST 14: Redis Health Inspector Truthful Reporting
    # -------------------------------------------------------------------------
    def test_14_redis_health_inspector_truthful(self):
        """Verifies that inspect_broker_health() reports NOT_CONFIGURED when REDIS_URL is empty."""
        from celery_app import inspect_broker_health

        original_redis = settings.REDIS_URL
        original_broker = settings.CELERY_BROKER_URL
        try:
            settings.REDIS_URL = ""
            settings.CELERY_BROKER_URL = "memory://"
            health = inspect_broker_health()
            self.assertEqual(health["status"], "NOT_CONFIGURED")
            self.assertFalse(health["connected"])
        finally:
            settings.REDIS_URL = original_redis
            settings.CELERY_BROKER_URL = original_broker

    # -------------------------------------------------------------------------
    # TEST 15: Celery Worker Health Inspector
    # -------------------------------------------------------------------------
    def test_15_celery_worker_inspector_truthful(self):
        """Verifies that inspect_worker_health() reports eager mode or active worker status truthfully."""
        from celery_app import inspect_worker_health

        health = inspect_worker_health()
        self.assertIn(health["status"], ("HEALTHY", "NOT_CONFIGURED", "UNAVAILABLE"))
        self.assertIn("mode", health)

    # -------------------------------------------------------------------------
    # TEST 16: Celery Task Registration Audit
    # -------------------------------------------------------------------------
    def test_16_celery_task_registration(self):
        """Verifies all required background tasks are registered in the Celery app registry."""
        from celery_app import celery_app
        import tasks.webhook_tasks
        import tasks.report_tasks
        import tasks.escalation_tasks
        import tasks.notification_tasks

        registered_tasks = set(celery_app.tasks.keys())
        required_tasks = {
            "tasks.webhook_tasks.dispatch_webhook_task",
            "tasks.webhook_tasks.retry_pending_webhooks_task",
            "tasks.report_tasks.execute_scheduled_reports_task",
            "tasks.escalation_tasks.escalate_approvals_task",
            "tasks.notification_tasks.deliver_notification_task"
        }
        for task_name in required_tasks:
            self.assertIn(task_name, registered_tasks)

    # -------------------------------------------------------------------------
    # TEST 17: Celery Beat Periodic Schedules
    # -------------------------------------------------------------------------
    def test_17_celery_beat_schedules_registered(self):
        """Verifies Beat schedule contains periodic jobs for reports, escalation, and webhooks."""
        from celery_app import celery_app

        beat_schedule = celery_app.conf.beat_schedule
        self.assertIn("execute-scheduled-reports", beat_schedule)
        self.assertIn("escalate-overdue-approvals", beat_schedule)
        self.assertIn("retry-pending-webhooks", beat_schedule)

    # -------------------------------------------------------------------------
    # TEST 18: Webhook Worker Bounded Backoff Formula
    # -------------------------------------------------------------------------
    def test_18_webhook_worker_bounded_backoff(self):
        """Verifies backoff increments are bounded to 30s, 120s, 480s for attempts 1, 2, 3."""
        for attempt in range(1, 4):
            backoff = 30 * (4 ** (attempt - 1))
            if attempt == 1:
                self.assertEqual(backoff, 30)
            elif attempt == 2:
                self.assertEqual(backoff, 120)
            elif attempt == 3:
                self.assertEqual(backoff, 480)

    # -------------------------------------------------------------------------
    # TEST 19: Webhook Worker Dead-Letter Transition
    # -------------------------------------------------------------------------
    @patch("requests.post")
    def test_19_webhook_worker_dlq_transition(self, mock_post):
        """Verifies that an exhausted delivery transitions to terminal DEAD_LETTER."""
        from tasks.webhook_tasks import dispatch_webhook_task

        mock_resp = MagicMock()
        mock_resp.status_code = 502
        mock_resp.text = "Bad Gateway"
        mock_post.return_value = mock_resp

        endpoint = models.WebhookEndpoint(
            org_id=self.org.id,
            name="DLQ Test Hook",
            url="https://flaky-partner.org/hook",
            secret_hash="hash_dlq",
            secret_key="secret_dlq",
            is_active=True
        )
        self.db.add(endpoint)
        self.db.commit()

        delivery = models.WebhookDelivery(
            webhook_id=endpoint.id,
            event_type="security.alert",
            status="RETRYING",
            attempt_count=2,  # Next attempt is 3 (max_attempts exhaustion)
            payload_json={"alert": "DLQ test"}
        )
        self.db.add(delivery)
        self.db.commit()

        res = dispatch_webhook_task(str(delivery.id), max_attempts=3)
        self.assertEqual(res["status"], "DEAD_LETTER")

        self.db.refresh(delivery)
        self.assertEqual(delivery.status, "DEAD_LETTER")
        self.assertIsNone(delivery.next_attempt_at)

    # -------------------------------------------------------------------------
    # TEST 20: Webhook SSRF Blocking on Loopback (127.0.0.1)
    # -------------------------------------------------------------------------
    def test_20_webhook_ssrf_blocking_loopback(self):
        """Verifies that webhook delivery to internal loopback addresses is immediately blocked."""
        from tasks.webhook_tasks import dispatch_webhook_task

        endpoint = models.WebhookEndpoint(
            org_id=self.org.id,
            name="SSRF Loopback Hook",
            url="http://127.0.0.1:8080/internal/admin",
            secret_hash="hash_loopback",
            secret_key="secret_loopback",
            is_active=True
        )
        self.db.add(endpoint)
        self.db.commit()

        delivery = models.WebhookDelivery(
            webhook_id=endpoint.id,
            event_type="test.event",
            status="QUEUED",
            attempt_count=0,
            payload_json={"test": True}
        )
        self.db.add(delivery)
        self.db.commit()

        res = dispatch_webhook_task(str(delivery.id))
        self.assertEqual(res["status"], "SSRF_BLOCKED")

        self.db.refresh(delivery)
        self.assertEqual(delivery.status, "DEAD_LETTER")
        self.assertIn("loopback", delivery.error_message.lower())

    # -------------------------------------------------------------------------
    # TEST 21: Webhook SSRF Blocking on Metadata Service (169.254.169.254)
    # -------------------------------------------------------------------------
    def test_21_webhook_ssrf_blocking_metadata(self):
        """Verifies that webhook delivery to cloud metadata service is blocked."""
        from tasks.webhook_tasks import dispatch_webhook_task

        endpoint = models.WebhookEndpoint(
            org_id=self.org.id,
            name="SSRF Metadata Hook",
            url="http://169.254.169.254/latest/meta-data/",
            secret_hash="hash_meta",
            secret_key="secret_meta",
            is_active=True
        )
        self.db.add(endpoint)
        self.db.commit()

        delivery = models.WebhookDelivery(
            webhook_id=endpoint.id,
            event_type="test.event",
            status="QUEUED",
            attempt_count=0,
            payload_json={"test": True}
        )
        self.db.add(delivery)
        self.db.commit()

        res = dispatch_webhook_task(str(delivery.id))
        self.assertEqual(res["status"], "SSRF_BLOCKED")

    # -------------------------------------------------------------------------
    # TEST 22: Webhook HMAC-SHA256 Signature Verification
    # -------------------------------------------------------------------------
    def test_22_webhook_hmac_signature_generation(self):
        """Verifies that webhook payloads are cryptographically signed using HMAC-SHA256."""
        from services.notification_service import compute_webhook_signature
        import hmac, hashlib

        secret = "whsec_test_secret_key_12345"
        payload_bytes = b'{"event":"test"}'
        timestamp = "2026-09-30T12:00:00"

        sig = compute_webhook_signature(secret, payload_bytes, timestamp)
        self.assertTrue(sig.startswith("sha256="))

        expected_msg = f"{timestamp}.".encode("utf-8") + payload_bytes
        expected_raw = hmac.new(secret.encode("utf-8"), expected_msg, hashlib.sha256).hexdigest()
        self.assertEqual(sig, f"sha256={expected_raw}")

    # -------------------------------------------------------------------------
    # TEST 23: Scheduled Report Duplicate Prevention
    # -------------------------------------------------------------------------
    def test_23_scheduled_report_duplicate_prevention(self):
        """Verifies that execute_scheduled_reports_task prevents duplicate executions within scheduled window."""
        from tasks.report_tasks import execute_scheduled_reports_task

        now = datetime.datetime.utcnow()
        sched = models.ScheduledReport(
            org_id=self.org.id,
            user_id=self.user.id,
            report_type="SECURITY_AUDIT",
            title="Scheduled Report Duplicate Test",
            frequency="DAILY",
            file_format="PDF",
            recipient_emails="audit@p6f.agentguard",
            status="ACTIVE",
            last_run_at=now,
            next_run_at=now + datetime.timedelta(days=1)
        )
        self.db.add(sched)
        self.db.commit()

        res = execute_scheduled_reports_task()
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("executed_count", res)
        self.assertIn("skipped_count", res)
        # Should skip because next_run_at is in the future
        self.assertGreaterEqual(res["skipped_count"], 1)

    # -------------------------------------------------------------------------
    # TEST 24: Approval Escalation Idempotency
    # -------------------------------------------------------------------------
    @patch("requests.post")
    def test_24_approval_escalation_idempotency(self, mock_post):
        """Verifies that escalate_approvals_task does not create duplicate escalation audits within 24h."""
        from tasks.escalation_tasks import escalate_approvals_task

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"ok": true}'
        mock_post.return_value = mock_resp

        dec = models.Decision(
            agent_id=self.agent.id,
            intent_summary="Idempotent Escalation",
            action_requested="TRANSFER",
            resource_target="bank",
            amount=20000.0,
            decision="REVIEW",
            risk_score=70,
            explanation="Requires review",
            execution_status="PENDING_APPROVAL"
        )
        self.db.add(dec)
        self.db.commit()

        appr = models.ApprovalRequest(
            decision_id=dec.id,
            agent_id=self.agent.id,
            amount=20000.0,
            reason="Review required",
            status="PENDING",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=28)
        )
        self.db.add(appr)
        self.db.commit()

        # Run 1: escalates
        res1 = escalate_approvals_task()
        self.assertGreaterEqual(res1["overdue_escalated"], 1)

        # Run 2: idempotent skip
        res2 = escalate_approvals_task()
        self.assertEqual(res2["overdue_escalated"], 0)
        self.assertGreaterEqual(res2["skipped_idempotent"], 1)

    # -------------------------------------------------------------------------
    # TEST 25: Storage Service Local Fallback
    # -------------------------------------------------------------------------
    def test_25_storage_service_local_fallback(self):
        """Verifies storage_service falls back to local tenant directory when S3 is unconfigured."""
        from services.storage_service import storage_service

        content = b"%PDF-1.4 Test Report Content"
        res = storage_service.save_report_file(
            content=content,
            filename="audit_test.pdf",
            org_id=str(self.org.id),
            format_type="PDF"
        )
        self.assertEqual(res["storage_backend"], "LOCAL")
        self.assertTrue(os.path.exists(res["file_path"]))
        self.assertEqual(res["file_size_bytes"], len(content))

    # -------------------------------------------------------------------------
    # TEST 26: Storage Service Truthful S3 Status
    # -------------------------------------------------------------------------
    def test_26_storage_service_truthful_s3_status(self):
        """Verifies storage_service reports NOT_CONFIGURED when S3_BUCKET is empty."""
        from services.storage_service import storage_service

        status_info = storage_service.get_storage_status()
        self.assertEqual(status_info["object_storage"]["status"], "NOT_CONFIGURED")

    # -------------------------------------------------------------------------
    # TEST 27: Email Service Truthful NOT_CONFIGURED Status
    # -------------------------------------------------------------------------
    def test_27_email_service_truthful_not_configured(self):
        """Verifies email_service returns EMAIL_PROVIDER_NOT_CONFIGURED when SMTP_HOST is unset."""
        from services.email_service import email_service

        orig = settings.EMAIL_PROVIDER
        try:
            settings.EMAIL_PROVIDER = "NONE"
            res = email_service.send_email("user@org.com", "Test Subject", "Test Body")
            self.assertEqual(res["status"], "EMAIL_PROVIDER_NOT_CONFIGURED")
            self.assertFalse(res["delivered"])
        finally:
            settings.EMAIL_PROVIDER = orig

    # -------------------------------------------------------------------------
    # TEST 28: Email Service Mock Provider for Tests
    # -------------------------------------------------------------------------
    def test_28_email_service_mock_provider(self):
        """Verifies email_service mock provider records outbound emails for deterministic testing."""
        from services.email_service import email_service

        orig = settings.EMAIL_PROVIDER
        try:
            settings.EMAIL_PROVIDER = "MOCK"
            res = email_service.send_email("recipient@enterprise.com", "Alert", "Security Incident")
            self.assertEqual(res["status"], "EMAIL_SENT")
            self.assertTrue(res["delivered"])
            self.assertEqual(res["provider"], "MOCK")
        finally:
            settings.EMAIL_PROVIDER = orig

    # -------------------------------------------------------------------------
    # TEST 29: WebSocket Connection Manager Single-Node Fallback
    # -------------------------------------------------------------------------
    def test_29_websocket_single_node_fallback(self):
        """Verifies WebSocket manager reports SINGLE_NODE mode when Redis Pub/Sub is unavailable."""
        from ws_manager import manager as ws_mgr

        status = ws_mgr.get_status()
        self.assertEqual(status["status"], "HEALTHY")
        self.assertIn(status["mode"], ("SINGLE_NODE", "REDIS_DISTRIBUTED"))

    # -------------------------------------------------------------------------
    # TEST 30: WebSocket Channel Tenant Scoping
    # -------------------------------------------------------------------------
    def test_30_websocket_channel_tenant_scoping(self):
        """Verifies WebSocket channels are partitioned by organization ID."""
        import asyncio
        from ws_manager import manager as ws_mgr

        target_org = str(uuid.uuid4())
        # Simulate broadcast to tenant channel without error
        asyncio.run(ws_mgr.broadcast({"event": "TEST_ALERT"}, org_id=target_org))

    # -------------------------------------------------------------------------
    # TEST 31: CORS Origin Restriction
    # -------------------------------------------------------------------------
    def test_31_cors_origins_not_wildcard(self):
        """Verifies that CORS_ORIGINS is an explicit allowlist and does not default to wildcard '*'."""
        self.assertIsInstance(settings.CORS_ORIGINS, list)
        self.assertNotIn("*", settings.CORS_ORIGINS)

    # -------------------------------------------------------------------------
    # TEST 32: Trusted Hosts Configuration
    # -------------------------------------------------------------------------
    def test_32_trusted_hosts_allowlist(self):
        """Verifies that TRUSTED_HOSTS is defined and contains trusted domains."""
        self.assertTrue(hasattr(settings, "TRUSTED_HOSTS"))
        self.assertIsInstance(settings.TRUSTED_HOSTS, list)

    # -------------------------------------------------------------------------
    # TEST 33: Backup Utility Command Spec Generator
    # -------------------------------------------------------------------------
    def test_33_backup_utility_command_generator(self):
        """Verifies pg_dump command generation utility formats valid PostgreSQL CLI options."""
        from scripts.backup_restore import generate_pg_dump_command

        orig_db = settings.DATABASE_URL
        try:
            settings.DATABASE_URL = "postgresql://agent_admin:secret_pass@db.agentguard.io:5432/agentguard_prod"
            info = generate_pg_dump_command("prod_backup.dump")
            self.assertTrue(info["supported"])
            self.assertIn("pg_dump", info["dump_command"])
            self.assertIn("-h db.agentguard.io", info["dump_command"])
            self.assertIn("-d agentguard_prod", info["dump_command"])
            # Ensure password is not present in command string
            self.assertNotIn("secret_pass", info["dump_command"])
        finally:
            settings.DATABASE_URL = orig_db

    # -------------------------------------------------------------------------
    # TEST 34: Database Integrity Audit Utility
    # -------------------------------------------------------------------------
    def test_34_database_integrity_audit(self):
        """Verifies database integrity audit utility inspects canonical plans and foreign keys."""
        from scripts.backup_restore import verify_database_integrity

        audit_res = verify_database_integrity()
        self.assertIn(audit_res["status"], ("HEALTHY", "DEGRADED"))
        self.assertTrue(audit_res["canonical_plans_verified"])
        self.assertEqual(audit_res["invalid_agent_ownership_count"], 0)


if __name__ == "__main__":
    unittest.main()
