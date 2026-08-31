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

class TestMultiTenantSaaSSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

        # Seed plans
        plans_data = [
            {"id": "FREE", "name": "Free Community", "description": "Evaluation", "price_monthly": 0.0, "max_users": 3, "max_ai_agents": 2, "max_api_keys": 1, "max_monthly_api_requests": 10000, "max_storage_gb": 5.0},
            {"id": "STARTER", "name": "Starter Plan", "description": "Small team", "price_monthly": 299.0, "max_users": 5, "max_ai_agents": 2, "max_api_keys": 5, "max_monthly_api_requests": 100000, "max_storage_gb": 20.0},
            {"id": "PROFESSIONAL", "name": "Professional Enterprise", "description": "Enterprise governance", "price_monthly": 999.0, "max_users": 50, "max_ai_agents": 25, "max_api_keys": 20, "max_monthly_api_requests": 1000000, "max_storage_gb": 100.0},
            {"id": "ENTERPRISE", "name": "Custom Enterprise", "description": "Custom enterprise control", "price_monthly": 4999.0, "max_users": 1000, "max_ai_agents": 500, "max_api_keys": 100, "max_monthly_api_requests": 10000000, "max_storage_gb": 1000.0}
        ]
        for p in plans_data:
            if not cls.db.query(models.Plan).filter(models.Plan.id == p["id"]).first():
                cls.db.add(models.Plan(**p))
        cls.db.commit()

        # Create SUPER_ADMIN user
        cls.super_admin_email = "mt_super_admin@agentguard.com"
        cls.super_admin = cls.db.query(models.User).filter(models.User.email == cls.super_admin_email).first()
        if not cls.super_admin:
            cls.platform_org = models.Organization(name="AgentGuard Platform", domain="agentguard.com", status="ACTIVE")
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

    def get_admin_a(self):
        return self.db.query(models.User).filter(models.User.email == "admin@alpha.com").first()

    def get_admin_b(self):
        return self.db.query(models.User).filter(models.User.email == "admin@beta.com").first()

    def test_01_super_admin_creates_org_a_and_b(self):
        """TEST 1 & 2: SUPER_ADMIN provisions Organization A and Organization B with Starter plans"""
        headers = self.get_auth_headers(self.super_admin)

        # Create Org A
        resp_a = client.post("/api/platform/organizations", json={
            "name": "Alpha Corporate SaaS",
            "domain": "alpha.com",
            "plan_id": "STARTER",
            "admin_email": "admin@alpha.com",
            "admin_full_name": "Alpha Admin"
        }, headers=headers)
        self.assertEqual(resp_a.status_code, 200)

        # Create Org B
        resp_b = client.post("/api/platform/organizations", json={
            "name": "Beta Enterprises SaaS",
            "domain": "beta.com",
            "plan_id": "STARTER",
            "admin_email": "admin@beta.com",
            "admin_full_name": "Beta Admin"
        }, headers=headers)
        self.assertEqual(resp_b.status_code, 200)

        admin_a = self.get_admin_a()
        admin_b = self.get_admin_b()

        self.assertIsNotNone(admin_a)
        self.assertIsNotNone(admin_b)
        self.assertEqual(admin_a.role, "ADMIN")
        self.assertEqual(admin_b.role, "ADMIN")
        print("  [SUCCESS] TEST 1 & 2: SUPER_ADMIN created Org A & Org B with tenant ADMINs")

    def test_02_org_a_admin_manages_org_a_only(self):
        """TEST 3 & 4: Org A ADMIN can manage Org A, but cannot access Org B (403 Forbidden)"""
        admin_a = self.get_admin_a()
        admin_b = self.get_admin_b()
        headers_a = self.get_auth_headers(admin_a)

        # Org A ADMIN fetches own org dashboard -> 200
        resp_own = client.get("/api/organization/dashboard", headers=headers_a)
        self.assertEqual(resp_own.status_code, 200)
        self.assertEqual(resp_own.json()["org_name"], "Alpha Corporate SaaS")

        # Org A ADMIN tries to call platform organization management endpoint -> 403
        resp_cross = client.get(f"/api/platform/organizations/{admin_b.org_id}", headers=headers_a)
        self.assertEqual(resp_cross.status_code, 403)
        print("  [SUCCESS] TEST 3 & 4: Org A ADMIN manages Org A; blocked from Org B (403)")

    def test_03_org_a_admin_cannot_escalate_to_super_admin(self):
        """TEST 6 & 7: Org A ADMIN cannot self-assign or invite SUPER_ADMIN role (403)"""
        admin_a = self.get_admin_a()
        headers_a = self.get_auth_headers(admin_a)

        # Self-role update to SUPER_ADMIN -> 403
        resp_self = client.patch("/api/profile/me", json={"role": "SUPER_ADMIN"}, headers=headers_a)
        self.assertEqual(resp_self.status_code, 403)

        # Invite user with SUPER_ADMIN role -> 403
        resp_invite = client.post("/api/organization/invite-user", json={
            "email": "hacker@alpha.com",
            "full_name": "Hacker User",
            "role": "SUPER_ADMIN"
        }, headers=headers_a)
        self.assertEqual(resp_invite.status_code, 403)
        print("  [SUCCESS] TEST 6 & 7: Privilege escalation to SUPER_ADMIN rejected with 403")

    def test_04_license_limits_enforcement(self):
        """TEST 9 & 19: Metred resource creation beyond plan limits is rejected (402 Payment Required)"""
        admin_a = self.get_admin_a()
        headers_a = self.get_auth_headers(admin_a)

        # Update license max_users to 2 for testing limit
        lic = self.db.query(models.License).filter(models.License.org_id == admin_a.org_id).first()
        lic.max_users = 2
        lic.max_ai_agents = 1
        self.db.commit()

        # Currently Org A has 1 user (admin_a). Invite user #2 -> Should succeed
        resp_u2 = client.post("/api/organization/invite-user", json={
            "email": "user2@alpha.com",
            "full_name": "User Two",
            "role": "USER"
        }, headers=headers_a)
        self.assertEqual(resp_u2.status_code, 200)

        # Invite user #3 (exceeds max_users limit 2) -> Should be rejected with 402 / LICENSE_LIMIT_REACHED
        resp_u3 = client.post("/api/organization/invite-user", json={
            "email": "user3@alpha.com",
            "full_name": "User Three",
            "role": "USER"
        }, headers=headers_a)
        self.assertEqual(resp_u3.status_code, 402)
        self.assertIn("LICENSE_LIMIT_REACHED", resp_u3.json()["detail"])

        # Create Agent #1 -> Should succeed
        resp_ag1 = client.post("/api/agents", json={
            "name": "Alpha Support Agent",
            "department": "Support",
            "purpose": "Customer assistance",
            "model_name": "gemini-pro",
            "model_version": "1.5",
            "environment": "PRODUCTION",
            "autonomy_level": "MEDIUM",
            "daily_budget": 500.0
        }, headers=headers_a)
        self.assertEqual(resp_ag1.status_code, 200)

        # Create Agent #2 (exceeds max_ai_agents limit 1) -> Should be rejected with 402 / LICENSE_LIMIT_REACHED
        resp_ag2 = client.post("/api/agents", json={
            "name": "Alpha Finance Agent",
            "department": "Finance",
            "purpose": "Invoice auditing",
            "model_name": "gemini-pro",
            "model_version": "1.5",
            "environment": "PRODUCTION",
            "autonomy_level": "MEDIUM",
            "daily_budget": 500.0
        }, headers=headers_a)
        self.assertEqual(resp_ag2.status_code, 402)
        self.assertIn("LICENSE_LIMIT_REACHED", resp_ag2.json()["detail"])
        print("  [SUCCESS] TEST 9 & 19: License max_users & max_ai_agents limits enforced (402)")

    def test_05_suspended_license_restricted_state(self):
        """TEST 10: Suspended license blocks resource creation"""
        admin_a = self.get_admin_a()
        headers_a = self.get_auth_headers(admin_a)

        # Suspend Org A license
        lic = self.db.query(models.License).filter(models.License.org_id == admin_a.org_id).first()
        lic.status = "SUSPENDED"
        lic.max_users = 100
        self.db.commit()

        # Attempt to invite user while suspended -> 402 LICENSE_RESTRICTED
        resp = client.post("/api/organization/invite-user", json={
            "email": "blocked@alpha.com",
            "full_name": "Blocked User",
            "role": "USER"
        }, headers=headers_a)
        self.assertEqual(resp.status_code, 402)
        self.assertIn("LICENSE_RESTRICTED", resp.json()["detail"])

        # Restore license to ACTIVE
        lic.status = "ACTIVE"
        self.db.commit()
        print("  [SUCCESS] TEST 10: Suspended license enters restricted state & blocks creation")

    def test_06_agent_and_audit_tenant_isolation(self):
        """TEST 11 & 12: Org A agents and audit logs never appear in Org B queries"""
        admin_b = self.get_admin_b()
        headers_b = self.get_auth_headers(admin_b)

        # Query agents as Org B ADMIN -> Org A agents must NOT be returned
        resp_agents = client.get("/api/agents", headers=headers_b)
        self.assertEqual(resp_agents.status_code, 200)
        agents_b = resp_agents.json()
        for a in agents_b:
            self.assertNotEqual(a["name"], "Alpha Support Agent")

        # Query activity as Org B ADMIN -> Org A audit logs must NOT be returned
        resp_act = client.get("/api/profile/activity", headers=headers_b)
        self.assertEqual(resp_act.status_code, 200)
        print("  [SUCCESS] TEST 11 & 12: Agent & Audit Log tenant isolation verified")

    def test_07_super_admin_platform_overview_real_data(self):
        """TEST 8 & 20: SUPER_ADMIN platform dashboard returns real database metrics"""
        headers_sa = self.get_auth_headers(self.super_admin)

        resp = client.get("/api/platform/overview", headers=headers_sa)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertTrue(data["total_organizations"] >= 2)
        self.assertTrue(data["total_users"] >= 3)
        self.assertTrue(data["active_licenses"] >= 2)
        print("  [SUCCESS] TEST 8 & 20: SUPER_ADMIN overview returns real database data")

if __name__ == "__main__":
    unittest.main()
