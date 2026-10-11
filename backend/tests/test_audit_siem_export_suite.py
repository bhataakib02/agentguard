"""
Test Suite: Enterprise SIEM Audit Export & Asynchronous Forwarder Pipeline
Verifies:
1. CEF (Common Event Format) log export strictly scoped to tenant.
2. JSON-Lines (NDJSON) log export strictly scoped to tenant.
3. Cross-tenant isolation in audit SIEM exports.
4. Truthful NOT_CONFIGURED status for SIEM forwarders when unconfigured.
5. Immutability protection on audit endpoints.
6. Missing configuration rejection (API & worker).
7. Authorization failures for non-admin users.
8. SSRF protection against loopback, private IPs, and cloud metadata.
9. Secret credential masking and metadata field redaction.
10. Successful batch delivery with mocked external collector (Splunk HEC).
11. HTTP failure handling and bounded exponential retry.
12. Timeout handling and bounded retry.
13. Retries exhaustion transitioning to DEAD_LETTER with immutable audit log.
14. Concurrent worker claim lock preventing duplicate batch dispatch.
15. Cross-tenant delivery and configuration isolation.
16. Datadog and Generic HTTP adapter formatting.
17. Truthful operational status reporting with delivery history.
"""

import uuid
import datetime
import unittest.mock
import pytest
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
import models
from core import security
from services.siem_forwarder_service import (
    format_audit_log_cef,
    format_audit_log_json,
    redact_sensitive_data,
    mask_secret,
    get_adapter,
    DatadogAdapter,
    GenericHttpAdapter,
)
from tasks.siem_tasks import forward_siem_batch_task

client = TestClient(app)


class TestSiemAuditExportSuite:
    @classmethod
    def setup_class(cls):
        cls.db = SessionLocal()

        # 1. Tenant Alpha
        cls.org_alpha = models.Organization(
            name=f"SIEM Alpha Org {uuid.uuid4().hex[:6]}",
            display_name="SIEM Alpha"
        )
        cls.db.add(cls.org_alpha)

        # 2. Tenant Beta
        cls.org_beta = models.Organization(
            name=f"SIEM Beta Org {uuid.uuid4().hex[:6]}",
            display_name="SIEM Beta"
        )
        cls.db.add(cls.org_beta)
        cls.db.commit()

        # 3. Users for Alpha (Admin, Regular User) and Beta (Admin)
        cls.user_alpha = models.User(
            email=f"alpha_siem_{uuid.uuid4().hex[:6]}@example.com",
            password_hash=security.get_password_hash("Secret123!"),
            full_name="Alpha SIEM Admin",
            role="ADMIN",
            org_id=cls.org_alpha.id
        )
        cls.user_alpha_regular = models.User(
            email=f"alpha_user_{uuid.uuid4().hex[:6]}@example.com",
            password_hash=security.get_password_hash("Secret123!"),
            full_name="Alpha Regular User",
            role="USER",
            org_id=cls.org_alpha.id
        )
        cls.user_beta = models.User(
            email=f"beta_siem_{uuid.uuid4().hex[:6]}@example.com",
            password_hash=security.get_password_hash("Secret123!"),
            full_name="Beta SIEM Admin",
            role="ADMIN",
            org_id=cls.org_beta.id
        )
        cls.db.add(cls.user_alpha)
        cls.db.add(cls.user_alpha_regular)
        cls.db.add(cls.user_beta)
        cls.db.commit()

        cls.token_alpha = security.create_access_token(cls.user_alpha.id, email=cls.user_alpha.email, role=cls.user_alpha.role)
        cls.token_alpha_regular = security.create_access_token(cls.user_alpha_regular.id, email=cls.user_alpha_regular.email, role=cls.user_alpha_regular.role)
        cls.token_beta = security.create_access_token(cls.user_beta.id, email=cls.user_beta.email, role=cls.user_beta.role)

        cls.headers_alpha = {"Authorization": f"Bearer {cls.token_alpha}"}
        cls.headers_alpha_regular = {"Authorization": f"Bearer {cls.token_alpha_regular}"}
        cls.headers_beta = {"Authorization": f"Bearer {cls.token_beta}"}

        # 4. Distinct audit logs for Alpha and Beta
        cls.log_alpha = models.AuditLog(
            org_id=cls.org_alpha.id,
            event_type="AUTH_DECISION",
            actor_type="AGENT",
            actor_id="AG-ALPHA-FINANCE",
            action="EXECUTE_PAYMENT",
            resource=f"org:{cls.org_alpha.id}:account_123",
            result="SUCCESS",
            metadata_json={"amount": 450.0, "currency": "USD"},
            timestamp=datetime.datetime.utcnow()
        )
        cls.log_beta = models.AuditLog(
            org_id=cls.org_beta.id,
            event_type="SECURITY_ALERT",
            actor_type="AGENT",
            actor_id="AG-BETA-RESEARCH",
            action="EXFILTRATE_DATA",
            resource=f"org:{cls.org_beta.id}:vault_secret",
            result="BLOCKED",
            metadata_json={"severity": "CRITICAL"},
            timestamp=datetime.datetime.utcnow()
        )
        cls.db.add(cls.log_alpha)
        cls.db.add(cls.log_beta)
        cls.db.commit()

    @classmethod
    def teardown_class(cls):
        cls.db.close()

    def test_01_export_cef_tenant_alpha(self):
        """Alpha CEF export must contain Alpha events in Common Event Format and exclude Beta events"""
        resp = client.get("/api/audit/export/cef", headers=self.headers_alpha)
        assert resp.status_code == 200
        text = resp.text
        assert "CEF:0|AgentGuard|SecurityKernel|1.0|" in text
        assert "AG-ALPHA-FINANCE" in text
        assert "EXECUTE_PAYMENT" in text
        # Beta's events must NOT be present in Alpha's export
        assert "AG-BETA-RESEARCH" not in text
        assert "EXFILTRATE_DATA" not in text

    def test_02_export_jsonl_tenant_beta(self):
        """Beta JSONL export must contain Beta events in JSON-Lines format and exclude Alpha events"""
        resp = client.get("/api/audit/export/jsonl", headers=self.headers_beta)
        assert resp.status_code == 200
        text = resp.text
        assert "AG-BETA-RESEARCH" in text
        assert "EXFILTRATE_DATA" in text
        # Alpha's events must NOT be present in Beta's export
        assert "AG-ALPHA-FINANCE" not in text
        assert "EXECUTE_PAYMENT" not in text

    def test_03_siem_forwarder_truthful_status(self):
        """SIEM status endpoint reports truthful status and supported formats"""
        resp = client.get("/api/audit/siem/status", headers=self.headers_alpha)
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "supported_formats" in data
        assert "CEF" in data["supported_formats"]
        assert "JSONL" in data["supported_formats"]
        assert data["status"] in ("CONFIGURED", "NOT_CONFIGURED")

    def test_04_integrations_list_contains_siem(self):
        """Integrations hub lists SIEM log streamer with truthful status"""
        resp = client.get("/api/integrations", headers=self.headers_alpha)
        assert resp.status_code == 200
        integrations = resp.json()
        siem_item = next((i for i in integrations if i["id"] == "siem_forwarder"), None)
        assert siem_item is not None
        assert siem_item["status"] in ("CONFIGURED", "NOT_CONFIGURED")
        assert "CEF" in siem_item["name"] or "SIEM" in siem_item["name"]

    def test_05_audit_logs_immutability(self):
        """Audit logs strictly reject PUT, PATCH, and DELETE operations with 403"""
        for method in [client.delete, client.put, client.patch]:
            resp = method("/api/audit/logs/some-id", headers=self.headers_alpha)
            assert resp.status_code == 403
            assert "immutable" in resp.json()["detail"].lower()

    # ------------------------------------------------------------------------
    # EXTENDED ASYNCHRONOUS SIEM PIPELINE VERIFICATIONS
    # ------------------------------------------------------------------------

    def test_06_missing_config_truthful_rejection(self):
        """When SIEM is unconfigured, forwarding is rejected truthfully with 400 NOT_CONFIGURED"""
        # Ensure no config for org_beta
        self.db.query(models.SiemCollectorConfig).filter(models.SiemCollectorConfig.org_id == self.org_beta.id).delete()
        self.db.commit()

        resp = client.post("/api/audit/siem/forward", headers=self.headers_beta)
        assert resp.status_code == 400
        assert "NOT_CONFIGURED" in resp.json()["detail"]

    def test_07_authorization_failures_ordinary_user(self):
        """Ordinary users (USER role) cannot configure SIEM, view config, or trigger batch forward"""
        # 1. Trigger forward forbidden
        resp_fwd = client.post("/api/audit/siem/forward", headers=self.headers_alpha_regular)
        assert resp_fwd.status_code == 403
        assert "forbidden" in resp_fwd.json()["detail"].lower()

        # 2. View config forbidden
        resp_cfg = client.get("/api/audit/siem/config", headers=self.headers_alpha_regular)
        assert resp_cfg.status_code == 403
        assert "forbidden" in resp_cfg.json()["detail"].lower()

        # 3. Alter config forbidden
        resp_set = client.post(
            "/api/audit/siem/config",
            json={"collector_url": "https://siem.example.com/ingest"},
            headers=self.headers_alpha_regular
        )
        assert resp_set.status_code == 403
        assert "forbidden" in resp_set.json()["detail"].lower()

    def test_08_ssrf_rejection_policy(self):
        """SSRF destinations (loopback, link-local metadata, private IPs) are rejected at config and worker levels"""
        # Loopback rejection
        resp_loop = client.post(
            "/api/audit/siem/config",
            json={"collector_url": "http://127.0.0.1:8088/collector"},
            headers=self.headers_alpha
        )
        assert resp_loop.status_code == 400
        assert "SSRF Protection" in resp_loop.json()["detail"]

        # Cloud metadata rejection
        resp_meta = client.post(
            "/api/audit/siem/config",
            json={"collector_url": "http://169.254.169.254/latest/meta-data"},
            headers=self.headers_alpha
        )
        assert resp_meta.status_code == 400
        assert "SSRF Protection" in resp_meta.json()["detail"]

        # Worker defense: If invalid URL bypassed into DB, worker catches SSRF before dispatch
        malicious_cfg = models.SiemCollectorConfig(
            org_id=self.org_alpha.id,
            name="Malicious Hook",
            collector_url="http://127.0.0.1:9200/bypass",
            is_active=True
        )
        self.db.add(malicious_cfg)
        self.db.commit()

        bad_delivery = models.SiemDelivery(
            org_id=self.org_alpha.id,
            batch_id=f"bad_batch_{uuid.uuid4().hex[:8]}",
            provider="GENERIC_HTTP",
            status="PENDING"
        )
        self.db.add(bad_delivery)
        self.db.commit()

        res = forward_siem_batch_task(str(bad_delivery.id))
        assert res["status"] == "SSRF_BLOCKED"

        self.db.expire_all()
        refreshed = self.db.query(models.SiemDelivery).filter_by(id=bad_delivery.id).first()
        assert refreshed.status == "DEAD_LETTER"
        assert "SSRF Protection" in refreshed.error_message

        # Verify immutable SSRF audit log
        ssrf_audit = self.db.query(models.AuditLog).filter_by(event_type="SIEM_SSRF_BLOCKED").first()
        assert ssrf_audit is not None
        assert ssrf_audit.result == "BLOCKED"

        # Cleanup malicious config
        self.db.delete(malicious_cfg)
        self.db.commit()

    def test_09_secret_redaction_in_config_and_payload(self):
        """Secrets are masked in config endpoints, and sensitive audit payload keys are redacted"""
        # 1. Configure collector with secret
        raw_secret = "super_secret_splunk_token_xyz98765"
        resp_cfg = client.post(
            "/api/audit/siem/config",
            json={
                "name": "Production Splunk Cluster",
                "provider": "SPLUNK_HEC",
                "collector_url": "https://splunk.corp.net:8088/services/collector/event",
                "auth_token": raw_secret,
                "format": "JSONL",
                "batch_size": 50
            },
            headers=self.headers_alpha
        )
        assert resp_cfg.status_code == 200
        data = resp_cfg.json()
        assert raw_secret not in str(data)  # Raw secret must never be exposed
        assert data["auth_token_preview"] is not None
        assert "sup****98765" in data["auth_token_preview"] or "****" in data["auth_token_preview"]

        # 2. GET config also masks secret
        resp_get = client.get("/api/audit/siem/config", headers=self.headers_alpha)
        assert resp_get.status_code == 200
        get_data = resp_get.json()
        assert raw_secret not in str(get_data)
        assert get_data["auth_token_preview"] is not None

        # 3. Payload sensitive data redaction helper
        raw_meta = {
            "password": "PlainUserPassword123!",
            "api_key": "live_sk_secret_token",
            "nested": {"access_token": "bearer_secret_tok"},
            "normal_data": "public_action_info"
        }
        redacted = redact_sensitive_data(raw_meta)
        assert redacted["password"] == "[REDACTED]"
        assert redacted["api_key"] == "[REDACTED]"
        assert redacted["nested"]["access_token"] == "[REDACTED]"
        assert redacted["normal_data"] == "public_action_info"

    def test_10_successful_delivery_mocked_collector(self):
        """Asynchronous batch forwarding successfully delivers to mocked collector with truthful QUEUED status"""
        # 1. Trigger forward via API
        resp_fwd = client.post("/api/audit/siem/forward", headers=self.headers_alpha)
        assert resp_fwd.status_code == 202
        fwd_data = resp_fwd.json()
        # Truthful status: NEVER claims delivered immediately, reports QUEUED
        assert fwd_data["status"] == "QUEUED"
        delivery_id = fwd_data["delivery_id"]

        # 2. Mock external collector receiving dispatch
        mock_resp = unittest.mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"text":"Success","code":0}'

        with unittest.mock.patch("requests.post", return_value=mock_resp) as mock_post:
            res = forward_siem_batch_task(delivery_id)
            assert res["status"] == "DELIVERED"
            assert res["response_code"] == 200
            assert mock_post.called

            # Check that Splunk authorization header was attached
            call_kwargs = mock_post.call_args[1]
            assert "Splunk" in call_kwargs["headers"]["Authorization"]
            assert call_kwargs["timeout"] == (5.0, 10.0)

        # 3. Verify persistent delivery record
        delivery = self.db.query(models.SiemDelivery).filter_by(id=delivery_id).first()
        assert delivery.status == "DELIVERED"
        assert delivery.response_code == 200
        assert delivery.delivered_at is not None
        assert delivery.error_message is None

        # 4. Verify immutable audit log recorded
        audit_rec = self.db.query(models.AuditLog).filter_by(
            event_type="SIEM_BATCH_DELIVERED",
            org_id=self.org_alpha.id
        ).first()
        assert audit_rec is not None
        assert audit_rec.result == "DELIVERED"

    def test_11_http_failure_and_bounded_retry(self):
        """HTTP error from collector transitions delivery to RETRYING with exponential backoff and sanitized error"""
        fail_delivery = models.SiemDelivery(
            org_id=self.org_alpha.id,
            batch_id=f"fail_batch_{uuid.uuid4().hex[:8]}",
            provider="SPLUNK_HEC",
            format="JSONL",
            status="PENDING"
        )
        self.db.add(fail_delivery)
        self.db.commit()

        mock_resp = unittest.mock.MagicMock()
        mock_resp.status_code = 503
        mock_resp.text = "Service Temporarily Unavailable"

        with unittest.mock.patch("requests.post", return_value=mock_resp):
            res = forward_siem_batch_task(str(fail_delivery.id), max_attempts=3)
            assert res["status"] == "RETRY_SCHEDULED"
            assert res["attempt"] == 1
            assert res["next_attempt_seconds"] > 0

        self.db.expire_all()
        refreshed = self.db.query(models.SiemDelivery).filter_by(id=fail_delivery.id).first()
        assert refreshed.status == "RETRYING"
        assert refreshed.attempt_count == 1
        assert refreshed.response_code == 503
        assert "HTTP 503" in refreshed.error_message
        assert refreshed.next_attempt_at is not None

    def test_12_timeout_and_bounded_retry(self):
        """Network timeout transitions delivery to RETRYING with sanitized error message"""
        timeout_delivery = models.SiemDelivery(
            org_id=self.org_alpha.id,
            batch_id=f"timeout_batch_{uuid.uuid4().hex[:8]}",
            provider="SPLUNK_HEC",
            format="JSONL",
            status="PENDING"
        )
        self.db.add(timeout_delivery)
        self.db.commit()

        import requests
        with unittest.mock.patch("requests.post", side_effect=requests.exceptions.Timeout("Read timed out (10s)")):
            res = forward_siem_batch_task(str(timeout_delivery.id), max_attempts=3)
            assert res["status"] == "RETRY_SCHEDULED"

        self.db.expire_all()
        refreshed = self.db.query(models.SiemDelivery).filter_by(id=timeout_delivery.id).first()
        assert refreshed.status == "RETRYING"
        assert "Timeout" in refreshed.error_message

    def test_13_exhausted_retries_dead_letter(self):
        """Exhausting retry attempts moves batch to DEAD_LETTER and emits immutable audit event"""
        dl_delivery = models.SiemDelivery(
            org_id=self.org_alpha.id,
            batch_id=f"dl_batch_{uuid.uuid4().hex[:8]}",
            provider="SPLUNK_HEC",
            format="JSONL",
            status="RETRYING",
            attempt_count=2  # On next failure, reaches max_attempts (3)
        )
        self.db.add(dl_delivery)
        self.db.commit()

        mock_resp = unittest.mock.MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"

        with unittest.mock.patch("requests.post", return_value=mock_resp):
            res = forward_siem_batch_task(str(dl_delivery.id), max_attempts=3)
            assert res["status"] == "DEAD_LETTER"
            assert res["attempts"] == 3

        self.db.expire_all()
        refreshed = self.db.query(models.SiemDelivery).filter_by(id=dl_delivery.id).first()
        assert refreshed.status == "DEAD_LETTER"
        assert refreshed.attempt_count == 3
        assert refreshed.next_attempt_at is None

        # Verify immutable DEAD_LETTER audit log
        dl_audit = self.db.query(models.AuditLog).filter_by(
            event_type="SIEM_BATCH_DEAD_LETTER",
            org_id=self.org_alpha.id
        ).first()
        assert dl_audit is not None
        assert dl_audit.result == "DEAD_LETTER"

    def test_14_concurrent_workers_claim_prevention(self):
        """Worker claim lock prevents concurrent workers from dispatching the exact same batch"""
        locked_delivery = models.SiemDelivery(
            org_id=self.org_alpha.id,
            batch_id=f"locked_batch_{uuid.uuid4().hex[:8]}",
            provider="SPLUNK_HEC",
            format="JSONL",
            status="CLAIMED",
            lock_token=uuid.uuid4().hex,
            locked_at=datetime.datetime.utcnow(),
            attempt_count=1
        )
        self.db.add(locked_delivery)
        self.db.commit()

        with unittest.mock.patch("requests.post") as mock_post:
            res = forward_siem_batch_task(str(locked_delivery.id))
            # Second worker attempt receives ALREADY_CLAIMED and avoids duplicate dispatch
            assert res["status"] == "ALREADY_CLAIMED"
            assert not mock_post.called

    def test_15_tenant_isolation_cross_tenant_checks(self):
        """Tenant Beta cannot view or modify Tenant Alpha's SIEM deliveries or configurations"""
        # 1. Beta listing deliveries must not include Alpha's deliveries
        resp_deliveries = client.get("/api/audit/siem/deliveries", headers=self.headers_beta)
        assert resp_deliveries.status_code == 200
        beta_deliveries = resp_deliveries.json()
        for d in beta_deliveries:
            assert d["org_id"] == str(self.org_beta.id)

        # 2. Beta config must not show Alpha's config
        resp_cfg_beta = client.get("/api/audit/siem/config", headers=self.headers_beta)
        assert resp_cfg_beta.status_code == 200
        assert resp_cfg_beta.json()["configured"] is False

    def test_16_adapter_coverage_datadog_and_generic(self):
        """Verifies Datadog and Generic HTTP adapter serialization contracts"""
        # Datadog Adapter
        dd_adapter = DatadogAdapter()
        target_url, headers, body_bytes = dd_adapter.prepare_request(
            events=[self.log_alpha],
            collector_url="https://http-intake.logs.datadoghq.com/api/v2/logs",
            auth_token="dd_test_key_123",
            format_type="JSONL",
            batch_id="batch_dd_test"
        )
        assert headers["DD-API-KEY"] == "dd_test_key_123"
        assert "application/json" in headers["Content-Type"]
        payload_str = body_bytes.decode("utf-8")
        assert "agentguard-security-kernel" in payload_str
        assert "EXECUTE_PAYMENT" in payload_str

        # Generic HTTP Adapter (CEF)
        generic_adapter = GenericHttpAdapter()
        cef_url, cef_headers, cef_body = generic_adapter.prepare_request(
            events=[self.log_alpha],
            collector_url="https://collector.example.com/cef",
            auth_token="bearer_tok_456",
            format_type="CEF",
            batch_id="batch_cef_test"
        )
        assert cef_headers["Authorization"] == "Bearer bearer_tok_456"
        assert "text/plain" in cef_headers["Content-Type"]
        cef_str = cef_body.decode("utf-8")
        assert "CEF:0|AgentGuard|SecurityKernel|1.0|" in cef_str

    def test_17_truthful_delivery_status_and_deliveries_list(self):
        """SIEM status and deliveries list endpoints reflect operational state accurately"""
        resp_status = client.get("/api/audit/siem/status", headers=self.headers_alpha)
        assert resp_status.status_code == 200
        status_data = resp_status.json()
        assert status_data["status"] == "CONFIGURED"
        assert status_data["delivery_semantics"] == "AT_LEAST_ONCE"
        assert len(status_data["recent_deliveries"]) > 0

        resp_list = client.get("/api/audit/siem/deliveries", headers=self.headers_alpha)
        assert resp_list.status_code == 200
        items = resp_list.json()
        assert len(items) > 0
        assert any(item["status"] in ("DELIVERED", "RETRYING", "DEAD_LETTER") for item in items)
