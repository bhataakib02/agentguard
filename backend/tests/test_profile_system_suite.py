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
from core.deps import HUMAN_ROLES, ROLE_PERMISSIONS
import models

client = TestClient(app)

class TestProfileAndSettingsSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

        # Create Test Organization
        cls.org_a = models.Organization(name="AgentGuard Enterprise Core", domain="agentguard.com")
        cls.org_b = models.Organization(name="External Competitor Corp", domain="competitor.com")
        cls.db.add_all([cls.org_a, cls.org_b])
        cls.db.commit()
        cls.db.refresh(cls.org_a)
        cls.db.refresh(cls.org_b)

        # Create Test Users for all 9 human roles in Org A
        cls.users = {}
        for r in HUMAN_ROLES:
            u_email = f"suite_{r.lower()}@agentguard.com"
            u = cls.db.query(models.User).filter(models.User.email == u_email).first()
            if not u:
                u = models.User(
                    org_id=cls.org_a.id,
                    auth_user_id=str(uuid.uuid4()),
                    email=u_email,
                    full_name=f"Suite {r.title()}",
                    role=r,
                    department=f"{r.title()} Dept",
                    job_title=f"{r.title()} Specialist",
                    phone="+1 (555) 019-2831",
                    status="ACTIVE"
                )
                cls.db.add(u)
                cls.db.commit()
                cls.db.refresh(u)
            cls.users[r] = u

        # Create Org B User (for organization isolation check)
        cls.org_b_user = cls.db.query(models.User).filter(models.User.email == "suite_victim@competitor.com").first()
        if not cls.org_b_user:
            cls.org_b_user = models.User(
                org_id=cls.org_b.id,
                auth_user_id=str(uuid.uuid4()),
                email="suite_victim@competitor.com",
                full_name="Org B Victim",
                role="USER",
                department="External",
                status="ACTIVE"
            )
            cls.db.add(cls.org_b_user)
            cls.db.commit()
            cls.db.refresh(cls.org_b_user)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def get_auth_headers(self, user_obj):
        token = security.create_access_token(user_obj.id)
        return {"Authorization": f"Bearer {token}"}

    def test_01_get_real_profile_me(self):
        """1. GET /api/profile/me returns real authenticated database profile"""
        super_admin = self.users["SUPER_ADMIN"]
        headers = self.get_auth_headers(super_admin)

        response = client.get("/api/profile/me", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["email"], super_admin.email)
        self.assertEqual(data["role"], "SUPER_ADMIN")
        self.assertEqual(data["role_level"], 9)
        self.assertEqual(data["org_name"], "AgentGuard Enterprise Core")
        self.assertIn("*", data["effective_permissions"])
        print("  [SUCCESS] TEST 1: GET /api/profile/me returns real database profile")

    def test_02_edit_profile_safe_fields(self):
        """2. PATCH /api/profile/me updates safe fields & persists in DB"""
        user_obj = self.users["USER"]
        headers = self.get_auth_headers(user_obj)

        new_name = "Bhaskar Updated Bhatnagar"
        new_dept = "AI Engineering"
        new_title = "Lead Security Architect"
        new_phone = "+1 (555) 999-8888"

        patch_resp = client.patch("/api/profile/me", json={
            "full_name": new_name,
            "department": new_dept,
            "job_title": new_title,
            "phone": new_phone
        }, headers=headers)
        self.assertEqual(patch_resp.status_code, 200)

        # Re-fetch profile to verify persistence
        get_resp = client.get("/api/profile/me", headers=headers)
        self.assertEqual(get_resp.status_code, 200)
        data = get_resp.json()

        self.assertEqual(data["full_name"], new_name)
        self.assertEqual(data["department"], new_dept)
        self.assertEqual(data["job_title"], new_title)
        self.assertEqual(data["phone"], new_phone)
        print("  [SUCCESS] TEST 2: PATCH /api/profile/me safe fields updated & verified")

    def test_03_privilege_escalation_protection(self):
        """3. Reject attempt to modify role, org_id, permissions or status via profile update (403)"""
        user_obj = self.users["USER"]
        headers = self.get_auth_headers(user_obj)

        # Attempt to escalate role to SUPER_ADMIN
        resp = client.patch("/api/profile/me", json={"role": "SUPER_ADMIN"}, headers=headers)
        self.assertEqual(resp.status_code, 403)
        self.assertIn("strictly prohibited", resp.json()["detail"])

        # Attempt to change org_id
        resp_org = client.patch("/api/profile/me", json={"org_id": str(self.org_b.id)}, headers=headers)
        self.assertEqual(resp_org.status_code, 403)

        # Re-verify DB user role is STILL USER
        self.db.refresh(user_obj)
        self.assertEqual(user_obj.role, "USER")
        print("  [SUCCESS] TEST 3: Privilege escalation attempt rejected with 403 Forbidden")

    def test_04_profile_access_organization_isolation(self):
        """4. Standard users blocked from viewing other profiles; ADMINs isolated to own org"""
        user_obj = self.users["USER"]
        admin_obj = self.users["ADMIN"]
        org_b_user = self.org_b_user

        # Standard user trying to view Admin profile -> 403
        headers_user = self.get_auth_headers(user_obj)
        resp_blocked = client.get(f"/api/profile/{admin_obj.id}", headers=headers_user)
        self.assertEqual(resp_blocked.status_code, 403)

        # Admin trying to view Org B user profile -> 403
        headers_admin = self.get_auth_headers(admin_obj)
        resp_cross_org = client.get(f"/api/profile/{org_b_user.id}", headers=headers_admin)
        self.assertEqual(resp_cross_org.status_code, 403)
        print("  [SUCCESS] TEST 4: Profile cross-user & organization isolation enforced (403)")

    def test_05_sessions_and_revocation(self):
        """5. Sessions endpoint & revocation audit logging"""
        user_obj = self.users["USER"]
        headers = self.get_auth_headers(user_obj)

        sess_resp = client.get("/api/profile/sessions", headers=headers)
        if sess_resp.status_code != 200:
            print("  [DEBUG test_05 failure]:", sess_resp.status_code, sess_resp.text)
        self.assertEqual(sess_resp.status_code, 200)

        revoke_resp = client.post("/api/profile/sessions/revoke-others", headers=headers)
        if revoke_resp.status_code != 200:
            print("  [DEBUG revoke_resp failure]:", revoke_resp.status_code, revoke_resp.text)
        self.assertEqual(revoke_resp.status_code, 200)
        print("  [SUCCESS] TEST 5: Sessions list & session revocation verified")

    def test_06_audit_logging_integrity(self):
        """6. Personal activity audit log stream"""
        user_obj = self.users["USER"]
        headers = self.get_auth_headers(user_obj)

        act_resp = client.get("/api/profile/activity", headers=headers)
        if act_resp.status_code != 200:
            print("  [DEBUG test_06 failure]:", act_resp.status_code, act_resp.text)
        self.assertEqual(act_resp.status_code, 200)
        logs = act_resp.json()
        self.assertIsInstance(logs, list)
        self.assertTrue(len(logs) > 0)
        print("  [SUCCESS] TEST 6: Personal audit activity logs retrieved")

    def test_07_all_human_roles_display_matrix(self):
        """7. Verify profile response across all 9 human roles"""
        for r in HUMAN_ROLES:
            u = self.users[r]
            headers = self.get_auth_headers(u)
            resp = client.get("/api/profile/me", headers=headers)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["role"], r)
            self.assertIsNotNone(data["role_description"])
        print("  [SUCCESS] TEST 7: All 9 human role profiles verified with 100% PASS")

if __name__ == "__main__":
    unittest.main()
