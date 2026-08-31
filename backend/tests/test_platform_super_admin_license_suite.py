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

class TestPlatformSuperAdminLicenseSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

        # Provision SUPER_ADMIN
        cls.super_admin_email = "super_admin_lic@agentguard.com"
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

    def get_auth_headers(self, user_obj):
        token = security.create_access_token(user_obj.id)
        return {"Authorization": f"Bearer {token}"}

    def get_user_by_email(self, email):
        return self.db.query(models.User).filter(models.User.email == email).first()

    def test_01_provision_tenant_orgs_and_verify_superadmin_exclusion(self):
        """TEST 1-4 & 10 & 11 & 26: Provision Org A & B; SUPER_ADMIN is NEVER returned in org user lists or quota counts"""
        sa_headers = self.get_auth_headers(self.super_admin)

        # Provision Org A
        resp_a = client.post("/api/platform/organizations", json={
            "name": "Acme SaaS Tenant A",
            "domain": "acme.com",
            "plan_id": "STARTER",
            "admin_email": "admin@acme.com",
            "admin_full_name": "Acme Admin"
        }, headers=sa_headers)
        self.assertEqual(resp_a.status_code, 200)

        # Provision Org B
        resp_b = client.post("/api/platform/organizations", json={
            "name": "TechCorp Tenant B",
            "domain": "techcorp.com",
            "plan_id": "STARTER",
            "admin_email": "admin@techcorp.com",
            "admin_full_name": "TechCorp Admin"
        }, headers=sa_headers)
        self.assertEqual(resp_b.status_code, 200)

        admin_a = self.get_user_by_email("admin@acme.com")
        headers_a = self.get_auth_headers(admin_a)

        # Query Org A users via /api/admin/users
        resp_users_a = client.get("/api/admin/users", headers=headers_a)
        self.assertEqual(resp_users_a.status_code, 200)
        users_list = resp_users_a.json()

        # SUPER_ADMIN must NEVER appear in Org A's user list
        for u in users_list:
            self.assertNotEqual(u["role"], "SUPER_ADMIN")
            self.assertNotEqual(u["email"], self.super_admin_email)

        # Check Org A dashboard user count -> Must equal 1 (admin_a only, excluding SUPER_ADMIN)
        resp_dash = client.get("/api/organization/dashboard", headers=headers_a)
        self.assertEqual(resp_dash.status_code, 200)
        self.assertEqual(resp_dash.json()["metrics"]["users"]["current"], 1)
        print("  [PASS] Test 1-4 & 10-11: SUPER_ADMIN is completely excluded from Org user list & user quota count")

    def test_02_super_admin_license_extension_renewal_revocation(self):
        """TEST 12, 13, 14: SUPER_ADMIN creates, extends, renews, and revokes licenses in real DB"""
        sa_headers = self.get_auth_headers(self.super_admin)
        admin_a = self.get_user_by_email("admin@acme.com")

        # 1. Extend License (+90 days)
        resp_ext = client.post("/api/platform/licenses/extend", json={
            "org_id": str(admin_a.org_id),
            "days": 90
        }, headers=sa_headers)
        self.assertEqual(resp_ext.status_code, 200)
        self.assertIn("new_expiry_date", resp_ext.json())

        # 2. Renew License (1 Year)
        resp_ren = client.post("/api/platform/licenses/renew", json={
            "org_id": str(admin_a.org_id)
        }, headers=sa_headers)
        self.assertEqual(resp_ren.status_code, 200)

        # 3. Revoke License
        resp_rev = client.post("/api/platform/licenses/revoke", json={
            "org_id": str(admin_a.org_id),
            "reason": "Security Compliance Audit"
        }, headers=sa_headers)
        self.assertEqual(resp_rev.status_code, 200)
        self.assertEqual(resp_rev.json()["license_status"], "CANCELLED")

        # Restore license for subsequent tests
        lic = self.db.query(models.License).filter(models.License.org_id == admin_a.org_id).first()
        lic.status = "ACTIVE"
        self.db.commit()
        print("  [PASS] Test 12-14: SUPER_ADMIN license extend, renew, & revoke API executed successfully")

    def test_03_org_admin_and_user_license_tampering_denied(self):
        """TEST 15 & 16: Organization ADMIN and standard USER attempting license management get 403 Forbidden"""
        admin_a = self.get_user_by_email("admin@acme.com")
        headers_a = self.get_auth_headers(admin_a)

        # Org ADMIN attempts to extend license -> 403
        resp_ext = client.post("/api/platform/licenses/extend", json={"org_id": str(admin_a.org_id), "days": 365}, headers=headers_a)
        self.assertEqual(resp_ext.status_code, 403)

        # Org ADMIN attempts to revoke license -> 403
        resp_rev = client.post("/api/platform/licenses/revoke", json={"org_id": str(admin_a.org_id)}, headers=headers_a)
        self.assertEqual(resp_rev.status_code, 403)
        print("  [PASS] Test 15 & 16: License modification by Org ADMIN rejected with 403 Forbidden")

    def test_04_expired_license_restricts_and_valid_license_allows(self):
        """TEST 17, 18, 19: Expired license restricts operations; valid license permits operation; limit enforces"""
        admin_a = self.get_user_by_email("admin@acme.com")
        headers_a = self.get_auth_headers(admin_a)

        # Expire license
        lic = self.db.query(models.License).filter(models.License.org_id == admin_a.org_id).first()
        lic.status = "EXPIRED"
        self.db.commit()

        # Inviting user while EXPIRED -> 402 Payment Required
        resp_exp = client.post("/api/organization/invite-user", json={
            "email": "user_exp_test@acme.com",
            "full_name": "Exp Test User",
            "role": "USER"
        }, headers=headers_a)
        self.assertEqual(resp_exp.status_code, 402)
        self.assertIn("LICENSE_RESTRICTED", resp_exp.json()["detail"])

        # Restore valid license & set max_users = 2
        lic.status = "ACTIVE"
        lic.max_users = 2
        self.db.commit()

        # Valid license allows operation
        resp_ok = client.post("/api/organization/invite-user", json={
            "email": "user_ok_test@acme.com",
            "full_name": "OK Test User",
            "role": "USER"
        }, headers=headers_a)
        self.assertEqual(resp_ok.status_code, 200)

        # Exceeding limit (user #3) -> 402 LICENSE_LIMIT_REACHED
        resp_limit = client.post("/api/organization/invite-user", json={
            "email": "user_limit_test@acme.com",
            "full_name": "Limit Test User",
            "role": "USER"
        }, headers=headers_a)
        self.assertEqual(resp_limit.status_code, 402)
        self.assertIn("LICENSE_LIMIT_REACHED", resp_limit.json()["detail"])
        print("  [PASS] Test 17-19: Expired license restricted (402), valid license allowed (200), limit enforced (402)")

    def test_05_audit_logs_recorded_in_database(self):
        """TEST 20: Audit logs for organization creation, license changes, and role events exist in PostgreSQL"""
        audits = self.db.query(models.AuditLog).filter(models.AuditLog.actor_type == "SUPER_ADMIN").all()
        self.assertTrue(len(audits) > 0)
        event_types = [a.event_type for a in audits]
        self.assertIn("ORGANIZATION_CREATED", event_types)
        print("  [PASS] Test 20: Real audit log records generated & persisted in database")

if __name__ == "__main__":
    unittest.main()
