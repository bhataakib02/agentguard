import unittest
import uuid
import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from starlette.testclient import TestClient
from main import app
from database import SessionLocal
from core import security
import models

client = TestClient(app)

class TestEnterpriseReportCenterSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

        # Provision SUPER_ADMIN
        cls.super_admin_email = "super_admin_rpt@agentguard.com"
        cls.super_admin = cls.db.query(models.User).filter(models.User.email == cls.super_admin_email).first()
        if not cls.super_admin:
            cls.platform_org = models.Organization(name="Platform Admin Control", domain="agentguard.com", status="ACTIVE")
            cls.db.add(cls.platform_org)
            cls.db.commit()
            cls.db.refresh(cls.platform_org)

            cls.super_admin = models.User(
                org_id=cls.platform_org.id,
                email=cls.super_admin_email,
                full_name="Platform Super Admin",
                role="SUPER_ADMIN",
                status="ACTIVE"
            )
            cls.db.add(cls.super_admin)
            cls.db.commit()
            cls.db.refresh(cls.super_admin)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def get_auth_headers(self, user_obj, extra_headers=None):
        token = security.create_access_token(user_obj.id)
        h = {"Authorization": f"Bearer {token}"}
        if extra_headers:
            h.update(extra_headers)
        return h

    def get_user_by_email(self, email):
        return self.db.query(models.User).filter(models.User.email == email).first()

    def test_01_provision_tenant_orgs_and_generate_pdf_excel_csv(self):
        """TEST 1-4 & 10-14 & 17-21: Provision Org A & B, generate PDF, Excel, and CSV reports from real DB data"""
        sa_headers = self.get_auth_headers(self.super_admin)

        # 1. Provision Org A
        resp_a = client.post("/api/platform/organizations", json={
            "name": "Acme Technologies",
            "domain": "acme.com",
            "plan_id": "STARTER",
            "admin_email": "admin_rpt_a@acme.com",
            "admin_full_name": "Acme Admin"
        }, headers=sa_headers)
        self.assertEqual(resp_a.status_code, 200)

        # 2. Provision Org B
        resp_b = client.post("/api/platform/organizations", json={
            "name": "XYZ Corporation",
            "domain": "xyz.com",
            "plan_id": "STARTER",
            "admin_email": "admin_rpt_b@xyz.com",
            "admin_full_name": "XYZ Admin"
        }, headers=sa_headers)
        self.assertEqual(resp_b.status_code, 200)

        admin_a = self.get_user_by_email("admin_rpt_a@acme.com")
        admin_b = self.get_user_by_email("admin_rpt_b@xyz.com")
        headers_a = self.get_auth_headers(admin_a)
        headers_b = self.get_auth_headers(admin_b)

        # 3. Generate Executive Summary PDF Report for Org A
        resp_pdf = client.post("/api/reports/generate", json={
            "report_type": "EXECUTIVE",
            "file_format": "PDF"
        }, headers=headers_a)
        self.assertEqual(resp_pdf.status_code, 200)
        self.assertEqual(resp_pdf.json()["file_format"], "PDF")
        self.assertTrue(resp_pdf.json()["file_size_bytes"] > 0)
        report_a_id = resp_pdf.json()["report_id"]

        # 4. Generate IAM Excel Report for Org A
        resp_excel = client.post("/api/reports/generate", json={
            "report_type": "IAM",
            "file_format": "EXCEL"
        }, headers=headers_a)
        self.assertEqual(resp_excel.status_code, 200)
        self.assertEqual(resp_excel.json()["file_format"], "EXCEL")

        # 5. Generate Audit CSV Report for Org A
        resp_csv = client.post("/api/reports/generate", json={
            "report_type": "AUDIT",
            "file_format": "CSV"
        }, headers=headers_a)
        self.assertEqual(resp_csv.status_code, 200)
        self.assertEqual(resp_csv.json()["file_format"], "CSV")

        # 6. Verify Org A history contains 3 records
        resp_hist = client.get("/api/reports/history", headers=headers_a)
        self.assertEqual(resp_hist.status_code, 200)
        self.assertEqual(len(resp_hist.json()), 3)

        # 7. Verify Org B history is completely isolated (0 records)
        resp_hist_b = client.get("/api/reports/history", headers=headers_b)
        self.assertEqual(resp_hist_b.status_code, 200)
        self.assertEqual(len(resp_hist_b.json()), 0)
        print("  [PASS] Test 1-4: PDF, Excel, and CSV reports generated from real DB and isolated per tenant")

    def test_02_report_download_security_and_cross_tenant_isolation(self):
        """TEST 18 & 21-22: Authorized report download works; cross-tenant download attempt rejected with 403"""
        admin_a = self.get_user_by_email("admin_rpt_a@acme.com")
        admin_b = self.get_user_by_email("admin_rpt_b@xyz.com")
        headers_a = self.get_auth_headers(admin_a)
        headers_b = self.get_auth_headers(admin_b)

        # Fetch Org A report ID
        resp_hist = client.get("/api/reports/history", headers=headers_a)
        report_a_id = resp_hist.json()[0]["id"]

        # Authorized download by Org A ADMIN -> 200 OK
        resp_dl_a = client.get(f"/api/reports/download/{report_a_id}", headers=headers_a)
        self.assertEqual(resp_dl_a.status_code, 200)

        # Unauthorized download attempt by Org B ADMIN targeting Org A report -> 403 Forbidden
        resp_dl_b = client.get(f"/api/reports/download/{report_a_id}", headers=headers_b)
        self.assertEqual(resp_dl_b.status_code, 403)
        print("  [PASS] Test 18 & 21-22: Authorized download succeeded (200); cross-tenant download rejected (403)")

    def test_03_scheduled_report_delivery(self):
        """TEST 26: Create recurring report schedule & verify DB persistence"""
        admin_a = self.get_user_by_email("admin_rpt_a@acme.com")
        headers_a = self.get_auth_headers(admin_a)

        resp_sched = client.post("/api/reports/schedule", json={
            "report_type": "EXECUTIVE",
            "file_format": "PDF",
            "frequency": "WEEKLY",
            "recipient_emails": "execs@acme.com"
        }, headers=headers_a)
        self.assertEqual(resp_sched.status_code, 200)

        resp_list = client.get("/api/reports/scheduled", headers=headers_a)
        self.assertEqual(resp_list.status_code, 200)
        self.assertTrue(len(resp_list.json()) >= 1)
        self.assertEqual(resp_list.json()[0]["frequency"], "WEEKLY")
        print("  [PASS] Test 26: Recurring report schedule created and persisted in PostgreSQL database")

    def test_04_audit_logs_recorded_for_report_actions(self):
        """TEST 20 & 30: REPORT_GENERATED, REPORT_DOWNLOADED, REPORT_SCHEDULED audit logs exist in DB"""
        audits = self.db.query(models.AuditLog).filter(models.AuditLog.resource == "reports").all()
        self.assertTrue(len(audits) >= 3)
        events = [a.event_type for a in audits]
        self.assertIn("REPORT_GENERATED", events)
        self.assertIn("REPORT_DOWNLOADED", events)
        self.assertIn("REPORT_SCHEDULED", events)
        print("  [PASS] Test 20 & 30: REPORT_GENERATED, REPORT_DOWNLOADED, and REPORT_SCHEDULED audit logs verified")

if __name__ == "__main__":
    unittest.main()
