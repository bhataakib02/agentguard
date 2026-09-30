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

class TestPhase6bApiContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        try:
            # 1. Ensure Tenant Org A
            cls.org_a = cls.db.query(models.Organization).filter(models.Organization.slug == "phase6b-org-a").first()
            if not cls.org_a:
                cls.org_a = models.Organization(
                    name="Phase 6B Org A",
                    slug="phase6b-org-a",
                    domain="phase6b-a.com",
                    status="ACTIVE"
                )
                cls.db.add(cls.org_a)
                cls.db.commit()
                cls.db.refresh(cls.org_a)

            # 2. Ensure Tenant Org B
            cls.org_b = cls.db.query(models.Organization).filter(models.Organization.slug == "phase6b-org-b").first()
            if not cls.org_b:
                cls.org_b = models.Organization(
                    name="Phase 6B Org B",
                    slug="phase6b-org-b",
                    domain="phase6b-b.com",
                    status="ACTIVE"
                )
                cls.db.add(cls.org_b)
                cls.db.commit()
                cls.db.refresh(cls.org_b)

            # Ensure Platform Org for Super Admin
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

            # Ensure Licenses
            for org in [cls.org_a, cls.org_b]:
                lic = cls.db.query(models.License).filter(models.License.org_id == org.id).first()
                if not lic:
                    lic = models.License(
                        org_id=org.id,
                        plan_id="STARTER",
                        status="ACTIVE",
                        start_date=datetime.datetime.utcnow(),
                        expiry_date=datetime.datetime.utcnow() + datetime.timedelta(days=365)
                    )
                    cls.db.add(lic)
                    cls.db.commit()

            # Ensure Users
            def get_or_create_user(org_id, email, full_name, role):
                u = cls.db.query(models.User).filter(models.User.email == email).first()
                if not u:
                    u = models.User(
                        org_id=org_id,
                        email=email,
                        full_name=full_name,
                        role=role,
                        status="ACTIVE"
                    )
                    cls.db.add(u)
                    cls.db.commit()
                    cls.db.refresh(u)
                return u

            cls.user_a = get_or_create_user(cls.org_a.id, "user_a@phase6b.com", "User A", "USER")
            cls.admin_a = get_or_create_user(cls.org_a.id, "admin_a@phase6b.com", "Admin A", "ADMIN")
            cls.admin_b = get_or_create_user(cls.org_b.id, "admin_b@phase6b.com", "Admin B", "ADMIN")
            cls.super_admin = get_or_create_user(cls.platform_org.id, "super_admin_6b@agentguard.com", "Super Admin 6B", "SUPER_ADMIN")

            # Ensure Agent for Org A
            cls.agent_a = cls.db.query(models.Agent).filter(models.Agent.org_id == cls.org_a.id).first()
            if not cls.agent_a:
                cls.agent_a = models.Agent(
                    org_id=cls.org_a.id,
                    owner_id=cls.admin_a.id,
                    agent_code="AGT-P6B-A-01",
                    name="Phase6B Agent A",
                    department="Engineering",
                    purpose="Automated contract testing",
                    autonomy_level="MEDIUM",
                    status="NORMAL"
                )
                cls.db.add(cls.agent_a)
                cls.db.commit()
                cls.db.refresh(cls.agent_a)

            # Ensure Passport for Agent A
            cls.passport_a = cls.db.query(models.AgentPassport).filter(models.AgentPassport.agent_id == cls.agent_a.id).first()
            if not cls.passport_a:
                now = datetime.datetime.utcnow()
                cls.passport_a = models.AgentPassport(
                    agent_id=cls.agent_a.id,
                    passport_number="AG-PASS-P6B-A-001",
                    digital_signature="sha256:contract_test_sig",
                    issued_at=now,
                    expires_at=now + datetime.timedelta(days=365),
                    verification_status="VERIFIED"
                )
                cls.db.add(cls.passport_a)
                cls.db.commit()

            # Ensure Agent for Org B
            cls.agent_b = cls.db.query(models.Agent).filter(models.Agent.org_id == cls.org_b.id).first()
            if not cls.agent_b:
                cls.agent_b = models.Agent(
                    org_id=cls.org_b.id,
                    owner_id=cls.admin_b.id,
                    agent_code="AGT-P6B-B-01",
                    name="Phase6B Agent B",
                    department="Finance",
                    purpose="Automated contract testing",
                    autonomy_level="LOW",
                    status="NORMAL"
                )
                cls.db.add(cls.agent_b)
                cls.db.commit()
                cls.db.refresh(cls.agent_b)

            # Store string IDs to avoid DetachedInstanceError across sessions
            cls.org_a_id = str(cls.org_a.id)
            cls.org_b_id = str(cls.org_b.id)
            cls.user_a_id = str(cls.user_a.id)
            cls.admin_a_id = str(cls.admin_a.id)
            cls.admin_b_id = str(cls.admin_b.id)
            cls.super_admin_id = str(cls.super_admin.id)
            cls.agent_a_id = str(cls.agent_a.id)
            cls.agent_b_id = str(cls.agent_b.id)

            # Generate Cryptographic Tokens
            cls.token_admin_a = security.create_access_token(cls.admin_a.id, email=cls.admin_a.email, role=cls.admin_a.role)
            cls.token_admin_b = security.create_access_token(cls.admin_b.id, email=cls.admin_b.email, role=cls.admin_b.role)
            cls.token_user_a = security.create_access_token(cls.user_a.id, email=cls.user_a.email, role=cls.user_a.role)
            cls.token_super_admin = security.create_access_token(cls.super_admin.id, email=cls.super_admin.email, role=cls.super_admin.role)

            cls.headers_admin_a = {"Authorization": f"Bearer {cls.token_admin_a}"}
            cls.headers_admin_b = {"Authorization": f"Bearer {cls.token_admin_b}"}
            cls.headers_user_a = {"Authorization": f"Bearer {cls.token_user_a}"}
            cls.headers_super_admin = {"Authorization": f"Bearer {cls.token_super_admin}"}
        finally:
            cls.db.close()

    def test_01_direct_report_export_pdf_authorized(self):
        """Test GET /api/reports/export/pdf streams real PDF for authorized tenant"""
        resp = client.get("/api/reports/export/pdf?type=EXECUTIVE", headers=self.headers_admin_a)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("content-type"), "application/pdf")
        self.assertTrue(len(resp.content) > 100)
        self.assertTrue(resp.content.startswith(b"%PDF"))

    def test_02_direct_report_export_excel_authorized(self):
        """Test GET /api/reports/export/excel streams real Excel XLSX for authorized tenant"""
        resp = client.get("/api/reports/export/excel?type=EXECUTIVE", headers=self.headers_admin_a)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(resp.content) > 100)

    def test_03_direct_report_export_csv_authorized(self):
        """Test GET /api/reports/export/csv streams real CSV for authorized tenant"""
        resp = client.get("/api/reports/export/csv?type=EXECUTIVE", headers=self.headers_admin_a)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("AGENTGUARD CONTROL PLANE REPORT", resp.text)

    def test_04_direct_report_export_unauthenticated(self):
        """Test unauthenticated export is rejected with 401"""
        resp = client.get("/api/reports/export/pdf?type=EXECUTIVE")
        self.assertIn(resp.status_code, [401, 403])

    def test_05_direct_report_export_cannot_cross_tenant(self):
        """Test Admin A cannot export reports for Org B"""
        cross_headers = {
            "Authorization": f"Bearer {self.token_admin_a}",
            "X-Organization-Context": self.org_b_id
        }
        resp = client.get("/api/reports/export/pdf?type=EXECUTIVE", headers=cross_headers)
        self.assertEqual(resp.status_code, 403)

    def test_06_platform_organization_status_toggle_super_admin(self):
        """Test PATCH /api/platform/organizations/{org_id}/status works for SUPER_ADMIN"""
        resp = client.patch(
            f"/api/platform/organizations/{self.org_a_id}/status",
            json={"status": "SUSPENDED"},
            headers=self.headers_super_admin
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["new_status"], "SUSPENDED")

        # Restore to ACTIVE
        resp_restore = client.patch(
            f"/api/platform/organizations/{self.org_a_id}/status",
            json={"status": "ACTIVE"},
            headers=self.headers_super_admin
        )
        self.assertEqual(resp_restore.status_code, 200)
        self.assertEqual(resp_restore.json()["new_status"], "ACTIVE")

    def test_07_platform_organization_status_toggle_rejected_for_non_super_admin(self):
        """Test PATCH /api/platform/organizations/{org_id}/status rejected with 403 for tenant admin"""
        resp = client.patch(
            f"/api/platform/organizations/{self.org_a_id}/status",
            json={"status": "SUSPENDED"},
            headers=self.headers_admin_a
        )
        self.assertEqual(resp.status_code, 403)

    def test_08_platform_organization_status_invalid_org_or_status(self):
        """Test invalid org ID returns 404 and invalid status returns 400"""
        resp_404 = client.patch(
            f"/api/platform/organizations/{uuid.uuid4()}/status",
            json={"status": "ACTIVE"},
            headers=self.headers_super_admin
        )
        self.assertEqual(resp_404.status_code, 404)

        resp_400 = client.patch(
            f"/api/platform/organizations/{self.org_a_id}/status",
            json={"status": "INVALID_STATUS"},
            headers=self.headers_super_admin
        )
        self.assertEqual(resp_400.status_code, 400)

    def test_09_platform_user_status_toggle_super_admin(self):
        """Test PATCH /api/platform/users/{user_id}/status works for SUPER_ADMIN"""
        resp = client.patch(
            f"/api/platform/users/{self.user_a_id}/status",
            json={"status": "SUSPENDED"},
            headers=self.headers_super_admin
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["new_status"], "SUSPENDED")

        # Restore
        resp_restore = client.patch(
            f"/api/platform/users/{self.user_a_id}/status",
            json={"status": "ACTIVE"},
            headers=self.headers_super_admin
        )
        self.assertEqual(resp_restore.status_code, 200)
        self.assertEqual(resp_restore.json()["new_status"], "ACTIVE")

    def test_10_platform_user_status_toggle_rejected_for_non_super_admin(self):
        """Test PATCH /api/platform/users/{user_id}/status rejected with 403 for tenant admin"""
        resp = client.patch(
            f"/api/platform/users/{self.user_a_id}/status",
            json={"status": "SUSPENDED"},
            headers=self.headers_admin_a
        )
        self.assertEqual(resp.status_code, 403)

    def test_11_agent_passport_authorized_tenant(self):
        """Test GET /api/agents/{id}/passport returns valid passport for tenant agent"""
        resp = client.get(f"/api/agents/{self.agent_a_id}/passport", headers=self.headers_admin_a)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("agent", data)
        self.assertIn("passport", data)
        self.assertEqual(data["passport"]["passport_number"], "AG-PASS-P6B-A-001")

    def test_12_agent_passport_cross_tenant_rejected(self):
        """Test Admin B cannot view Agent A passport (403 Forbidden)"""
        resp = client.get(f"/api/agents/{self.agent_a_id}/passport", headers=self.headers_admin_b)
        self.assertEqual(resp.status_code, 403)

    def test_13_agent_passport_invalid_id(self):
        """Test non-existent agent ID returns 404"""
        resp = client.get(f"/api/agents/{uuid.uuid4()}/passport", headers=self.headers_admin_a)
        self.assertEqual(resp.status_code, 404)

    def test_14_platform_api_integrations_endpoint(self):
        """Test GET /api/platform/api returns metrics without secrets"""
        resp = client.get("/api/platform/api", headers=self.headers_super_admin)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("api_status", data)
        self.assertIn("total_api_keys", data)
        self.assertIn("active_webhooks", data)
        self.assertIn("webhook_delivery_rate", data)
        # Ensure no plaintext secrets are in response
        self.assertNotIn("secret", str(data).lower())
        self.assertNotIn("password", str(data).lower())

    def test_15_platform_api_integrations_rejected_for_tenant_admin(self):
        """Test GET /api/platform/api rejected with 403 for non-super-admin"""
        resp = client.get("/api/platform/api", headers=self.headers_admin_a)
        self.assertEqual(resp.status_code, 403)

if __name__ == "__main__":
    unittest.main()
