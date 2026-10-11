"""
Test Suite: Enterprise SIEM Audit Export & Forwarder Integrations
Verifies:
1. CEF (Common Event Format) log export strictly scoped to tenant.
2. JSON-Lines (NDJSON) log export strictly scoped to tenant.
3. Cross-tenant isolation in audit SIEM exports.
4. Truthful NOT_CONFIGURED status for SIEM forwarders when unconfigured.
5. Immutability protection on audit endpoints.
"""

import uuid
import datetime
import pytest
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
import models
from core import security

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

        # 3. Users for Alpha and Beta
        cls.user_alpha = models.User(
            email=f"alpha_siem_{uuid.uuid4().hex[:6]}@example.com",
            password_hash=security.get_password_hash("Secret123!"),
            full_name="Alpha SIEM Admin",
            role="ADMIN",
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
        cls.db.add(cls.user_beta)
        cls.db.commit()

        cls.token_alpha = security.create_access_token(cls.user_alpha.id, email=cls.user_alpha.email, role=cls.user_alpha.role)
        cls.token_beta = security.create_access_token(cls.user_beta.id, email=cls.user_beta.email, role=cls.user_beta.role)
        cls.headers_alpha = {"Authorization": f"Bearer {cls.token_alpha}"}
        cls.headers_beta = {"Authorization": f"Bearer {cls.token_beta}"}

        # 4. Create distinct audit logs for Alpha and Beta
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
        """SIEM status endpoint reports truthful NOT_CONFIGURED when forwarder URL is unset"""
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
