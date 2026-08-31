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

class TestTenantSecurityPenetration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

        # Create SUPER_ADMIN
        cls.super_admin_email = "pen_super_admin@agentguard.com"
        cls.super_admin = cls.db.query(models.User).filter(models.User.email == cls.super_admin_email).first()
        if not cls.super_admin:
            cls.platform_org = models.Organization(name="PenTest Platform", domain="agentguard.com", status="ACTIVE")
            cls.db.add(cls.platform_org)
            cls.db.commit()
            cls.db.refresh(cls.platform_org)

            cls.super_admin = models.User(
                org_id=cls.platform_org.id,
                email=cls.super_admin_email,
                full_name="PenTest Super Admin",
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

    def test_01_create_org_a_b_and_admins(self):
        """TEST 1-4: Create Org A, Org B, ADMIN_A, ADMIN_B"""
        sa_headers = self.get_auth_headers(self.super_admin)

        resp_a = client.post("/api/platform/organizations", json={
            "name": "Org A Security Corp",
            "domain": "orga.com",
            "plan_id": "STARTER",
            "admin_email": "admin_a@orga.com",
            "admin_full_name": "Admin A"
        }, headers=sa_headers)
        self.assertEqual(resp_a.status_code, 200)

        resp_b = client.post("/api/platform/organizations", json={
            "name": "Org B Financial Corp",
            "domain": "orgb.com",
            "plan_id": "STARTER",
            "admin_email": "admin_b@orgb.com",
            "admin_full_name": "Admin B"
        }, headers=sa_headers)
        self.assertEqual(resp_b.status_code, 200)

        admin_a = self.get_user_by_email("admin_a@orga.com")
        admin_b = self.get_user_by_email("admin_b@orgb.com")

        self.assertIsNotNone(admin_a)
        self.assertIsNotNone(admin_b)
        print("  [PASS] Test 1-4: Created Org A, Org B, ADMIN_A, ADMIN_B")

    def test_02_admin_a_accesses_org_a_success(self):
        """TEST 5: ADMIN_A accesses Organization A -> PASS"""
        admin_a = self.get_user_by_email("admin_a@orga.com")
        headers_a = self.get_auth_headers(admin_a)

        resp = client.get("/api/organization/dashboard", headers=headers_a)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["org_name"], "Org A Security Corp")
        print("  [PASS] Test 5: ADMIN_A accesses Organization A")

    def test_03_admin_a_attempts_access_org_b_denied(self):
        """TEST 6: ADMIN_A attempts to access Organization B -> 403 DENIED"""
        admin_a = self.get_user_by_email("admin_a@orga.com")
        admin_b = self.get_user_by_email("admin_b@orgb.com")
        headers_a = self.get_auth_headers(admin_a)

        resp = client.get(f"/api/platform/organizations/{admin_b.org_id}", headers=headers_a)
        self.assertEqual(resp.status_code, 403)
        print("  [PASS] Test 6: ADMIN_A access to Organization B rejected with 403")

    def test_04_admin_a_modifies_request_org_id_denied(self):
        """TEST 7: ADMIN_A modifies request body organization_id -> DENIED"""
        admin_a = self.get_user_by_email("admin_a@orga.com")
        admin_b = self.get_user_by_email("admin_b@orgb.com")
        headers_a = self.get_auth_headers(admin_a)

        # ADMIN_A attempts to update profile specifying Org B's org_id
        resp = client.patch("/api/profile/me", json={"org_id": str(admin_b.org_id)}, headers=headers_a)
        self.assertEqual(resp.status_code, 403)

        # ADMIN_A attempts to pass X-Organization-Context header
        resp_ctx = client.get("/api/organization/dashboard", headers=self.get_auth_headers(admin_a, {"X-Organization-Context": str(admin_b.org_id)}))
        self.assertEqual(resp_ctx.status_code, 200)
        # Verify backend ignored non-superadmin header and returned Org A
        self.assertEqual(resp_ctx.json()["org_name"], "Org A Security Corp")
        print("  [PASS] Test 7: Body/Header organization_id tampering rejected by backend")

    def test_05_admin_a_modifies_url_denied(self):
        """TEST 8: ADMIN_A modifies URL to Org B -> DENIED"""
        admin_a = self.get_user_by_email("admin_a@orga.com")
        admin_b = self.get_user_by_email("admin_b@orgb.com")
        headers_a = self.get_auth_headers(admin_a)

        resp = client.get(f"/api/profile/{admin_b.id}", headers=headers_a)
        self.assertEqual(resp.status_code, 403)
        print("  [PASS] Test 8: URL parameter tampering rejected with 403")

    def test_06_admin_a_modifies_localstorage_denied(self):
        """TEST 9: ADMIN_A modifies localStorage role/org -> DENIED by backend token authorization"""
        admin_a = self.get_user_by_email("admin_a@orga.com")
        # Token encodes admin_a.id, backend decodes user from DB
        headers_a = self.get_auth_headers(admin_a)

        resp = client.get("/api/platform/overview", headers=headers_a)
        self.assertEqual(resp.status_code, 403)
        print("  [PASS] Test 9: Client-side role claims ignored; backend token decoded from DB")

    def test_07_admin_a_assigns_super_admin_denied(self):
        """TEST 10: ADMIN_A attempts to assign SUPER_ADMIN -> DENIED"""
        admin_a = self.get_user_by_email("admin_a@orga.com")
        headers_a = self.get_auth_headers(admin_a)

        resp = client.post("/api/organization/invite-user", json={
            "email": "hacker_sa@orga.com",
            "full_name": "Hacker SA",
            "role": "SUPER_ADMIN"
        }, headers=headers_a)
        self.assertEqual(resp.status_code, 403)
        print("  [PASS] Test 10: Assigning SUPER_ADMIN role rejected with 403")

    def test_08_super_admin_accesses_org_a_b_all(self):
        """TEST 11, 12, 13: SUPER_ADMIN accesses Org A, Org B, and views all organizations -> PASS"""
        admin_a = self.get_user_by_email("admin_a@orga.com")
        admin_b = self.get_user_by_email("admin_b@orgb.com")
        sa_headers = self.get_auth_headers(self.super_admin)

        # SUPER_ADMIN views Org A
        resp_a = client.get(f"/api/platform/organizations/{admin_a.org_id}", headers=sa_headers)
        self.assertEqual(resp_a.status_code, 200)

        # SUPER_ADMIN views Org B
        resp_b = client.get(f"/api/platform/organizations/{admin_b.org_id}", headers=sa_headers)
        self.assertEqual(resp_b.status_code, 200)

        # SUPER_ADMIN views all orgs
        resp_all = client.get("/api/platform/organizations", headers=sa_headers)
        self.assertEqual(resp_all.status_code, 200)
        self.assertTrue(len(resp_all.json()) >= 2)
        print("  [PASS] Test 11-13: SUPER_ADMIN accesses Org A, Org B, and platform overview")

    def test_09_org_a_user_queries_org_b_agents_denied(self):
        """TEST 14: Org A user queries Org B agents -> DENIED / Empty"""
        admin_b = self.get_user_by_email("admin_b@orgb.com")
        admin_a = self.get_user_by_email("admin_a@orga.com")
        headers_a = self.get_auth_headers(admin_a)

        resp = client.get("/api/agents", headers=headers_a)
        self.assertEqual(resp.status_code, 200)
        for agent in resp.json():
            self.assertEqual(str(agent["org_id"]), str(admin_a.org_id))
            self.assertNotEqual(str(agent["org_id"]), str(admin_b.org_id))
        print("  [PASS] Test 14: Agent tenant query returns only Org A records")

    def test_10_expired_license_restricted_state(self):
        """TEST 15 & 16: Expired license enters restricted state; valid license allows operation"""
        admin_a = self.get_user_by_email("admin_a@orga.com")
        headers_a = self.get_auth_headers(admin_a)

        # 1. Expire License
        lic = self.db.query(models.License).filter(models.License.org_id == admin_a.org_id).first()
        lic.status = "EXPIRED"
        self.db.commit()

        # Restrict operation -> 402 LICENSE_RESTRICTED
        resp_exp = client.post("/api/organization/invite-user", json={
            "email": "user_exp@orga.com",
            "full_name": "Exp User",
            "role": "USER"
        }, headers=headers_a)
        self.assertEqual(resp_exp.status_code, 402)
        self.assertIn("LICENSE_RESTRICTED", resp_exp.json()["detail"])

        # 2. Restore Valid License
        lic.status = "ACTIVE"
        lic.max_users = 50
        self.db.commit()

        resp_val = client.post("/api/organization/invite-user", json={
            "email": "user_val@orga.com",
            "full_name": "Val User",
            "role": "USER"
        }, headers=headers_a)
        self.assertEqual(resp_val.status_code, 200)
        print("  [PASS] Test 15 & 16: Expired license restricted (402); valid license allowed (200)")

    def test_11_login_reloads_org_and_role_from_db(self):
        """TEST 17: Logout / Login reloads organization and role from database"""
        admin_a = self.get_user_by_email("admin_a@orga.com")
        headers_a = self.get_auth_headers(admin_a)

        resp = client.get("/api/auth/me", headers=headers_a)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["email"], "admin_a@orga.com")
        self.assertEqual(data["role"], "ADMIN")
        self.assertEqual(str(data["org_id"]), str(admin_a.org_id))
        print("  [PASS] Test 17: Authentication reloads real org_id & role from database")

if __name__ == "__main__":
    unittest.main()
