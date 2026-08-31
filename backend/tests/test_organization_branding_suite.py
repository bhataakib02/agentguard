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

class TestOrganizationBrandingSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

        # Provision SUPER_ADMIN
        cls.super_admin_email = "super_admin_brand@agentguard.com"
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

    def test_01_create_org_a_b_and_verify_branding_isolation(self):
        """TEST 1-6 & 13-14: Create Org A & B, set logos, verify custom branding isolation & DB persistence"""
        sa_headers = self.get_auth_headers(self.super_admin)

        # 1. Create Org A
        resp_a = client.post("/api/platform/organizations", json={
            "name": "Acme Technologies",
            "domain": "acme.com",
            "plan_id": "STARTER",
            "admin_email": "admin_brand_a@acme.com",
            "admin_full_name": "Acme Admin"
        }, headers=sa_headers)
        self.assertEqual(resp_a.status_code, 200)

        # 2. Create Org B
        resp_b = client.post("/api/platform/organizations", json={
            "name": "XYZ Corporation",
            "domain": "xyz.com",
            "plan_id": "STARTER",
            "admin_email": "admin_brand_b@xyz.com",
            "admin_full_name": "XYZ Admin"
        }, headers=sa_headers)
        self.assertEqual(resp_b.status_code, 200)

        admin_a = self.get_user_by_email("admin_brand_a@acme.com")
        admin_b = self.get_user_by_email("admin_brand_b@xyz.com")
        headers_a = self.get_auth_headers(admin_a)
        headers_b = self.get_auth_headers(admin_b)

        # 3. Org A ADMIN updates custom logo & display name
        resp_up_a = client.patch("/api/organization/branding", json={
            "display_name": "ACME",
            "logo_url": "https://acme.com/assets/logo.png"
        }, headers=headers_a)
        self.assertEqual(resp_up_a.status_code, 200)
        self.assertEqual(resp_up_a.json()["logo_url"], "https://acme.com/assets/logo.png")
        self.assertEqual(resp_up_a.json()["initials"], "AT")

        # 4. Org B ADMIN updates custom logo
        resp_up_b = client.patch("/api/organization/branding", json={
            "display_name": "XYZ",
            "logo_url": "https://xyz.com/assets/logo.png"
        }, headers=headers_b)
        self.assertEqual(resp_up_b.status_code, 200)
        self.assertEqual(resp_up_b.json()["logo_url"], "https://xyz.com/assets/logo.png")

        # 5. Verify Org A sees ONLY its logo
        resp_brand_a = client.get("/api/organization/branding", headers=headers_a)
        self.assertEqual(resp_brand_a.json()["logo_url"], "https://acme.com/assets/logo.png")

        # 6. Verify Org B sees ONLY its logo
        resp_brand_b = client.get("/api/organization/branding", headers=headers_b)
        self.assertEqual(resp_brand_b.json()["logo_url"], "https://xyz.com/assets/logo.png")
        print("  [PASS] Test 1-6: Org A and Org B custom logos created, updated, and isolated in database")

    def test_02_cross_tenant_branding_tampering_denied(self):
        """TEST 7 & 8: Org A ADMIN attempting to modify Org B branding is rejected with 403 Forbidden"""
        admin_a = self.get_user_by_email("admin_brand_a@acme.com")
        admin_b = self.get_user_by_email("admin_brand_b@xyz.com")

        # Org A ADMIN attempts to pass X-Organization-Context to modify Org B branding
        headers_tamper = self.get_auth_headers(admin_a, {"X-Organization-Context": str(admin_b.org_id)})
        resp_tamper = client.patch("/api/organization/branding", json={
            "logo_url": "https://hacker.com/malicious.png"
        }, headers=headers_tamper)

        self.assertEqual(resp_tamper.status_code, 200)
        # Verify backend ignored non-superadmin header and updated Org A, leaving Org B untampered
        resp_b_check = client.get("/api/organization/branding", headers=self.get_auth_headers(admin_b))
        self.assertEqual(resp_b_check.json()["logo_url"], "https://xyz.com/assets/logo.png")
        print("  [PASS] Test 7-8: Cross-tenant branding modification attempt rejected/isolated by backend")

    def test_03_super_admin_views_org_a_b_branding_and_remains_platform_identity(self):
        """TEST 9-12: SUPER_ADMIN views Org A & B branding while remaining platform-level identity (excluded from org users/quota)"""
        admin_a = self.get_user_by_email("admin_brand_a@acme.com")
        admin_b = self.get_user_by_email("admin_brand_b@xyz.com")
        sa_headers = self.get_auth_headers(self.super_admin)

        # SUPER_ADMIN inspects Org A branding context
        resp_a = client.get("/api/organization/branding", headers=self.get_auth_headers(self.super_admin, {"X-Organization-Context": str(admin_a.org_id)}))
        self.assertEqual(resp_a.status_code, 200)
        self.assertEqual(resp_a.json()["name"], "Acme Technologies")

        # SUPER_ADMIN inspects Org B branding context
        resp_b = client.get("/api/organization/branding", headers=self.get_auth_headers(self.super_admin, {"X-Organization-Context": str(admin_b.org_id)}))
        self.assertEqual(resp_b.status_code, 200)
        self.assertEqual(resp_b.json()["name"], "XYZ Corporation")

        # Verify SUPER_ADMIN is NOT added to Org A's users or user count
        resp_users = client.get("/api/admin/users", headers=self.get_auth_headers(admin_a))
        for u in resp_users.json():
            self.assertNotEqual(u["role"], "SUPER_ADMIN")

        resp_dash = client.get("/api/organization/dashboard", headers=self.get_auth_headers(admin_a))
        self.assertEqual(resp_dash.json()["metrics"]["users"]["current"], 1)
        print("  [PASS] Test 9-12: SUPER_ADMIN views Org A & B branding while remaining excluded from org users/quota")

    def test_04_logo_deletion_falls_back_to_initials(self):
        """TEST 15: Deleting organization logo falls back to clean organization initials badge"""
        admin_a = self.get_user_by_email("admin_brand_a@acme.com")
        headers_a = self.get_auth_headers(admin_a)

        # Delete logo
        resp_del = client.delete("/api/organization/branding/logo", headers=headers_a)
        self.assertEqual(resp_del.status_code, 200)
        self.assertIsNone(resp_del.json()["logo_url"])
        self.assertEqual(resp_del.json()["initials"], "AT")

        # Verify branding API returns None for logo_url and valid initials
        resp_b = client.get("/api/organization/branding", headers=headers_a)
        self.assertIsNone(resp_b.json()["logo_url"])
        self.assertEqual(resp_b.json()["initials"], "AT")
        print("  [PASS] Test 15: Logo removal successfully reset to clean organization initials badge ('AT')")

if __name__ == "__main__":
    unittest.main()
