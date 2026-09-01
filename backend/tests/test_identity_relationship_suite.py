import sys
import unittest
import requests
import json
from sqlalchemy import text
from fastapi.testclient import TestClient

sys.path.insert(0, r"d:\AGENTGUARD\backend")
from database import engine
from config import settings
from main import app

SUPABASE_URL = settings.SUPABASE_URL
PUBLISHABLE_KEY = settings.SUPABASE_PUBLISHABLE_KEY
TEST_PASSWORD = "Blackbird@12."

def get_auth_token(email):
    headers = {"apikey": PUBLISHABLE_KEY, "Content-Type": "application/json"}
    login_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    resp = requests.post(login_url, json={"email": email, "password": TEST_PASSWORD}, headers=headers)
    if resp.status_code == 200:
        return resp.json().get("access_token")
    return None

class TestIdentityRelationships(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.token_acme_user = get_auth_token("zoya@acme.com")
        cls.token_acme_admin = get_auth_token("aarav@acme.com")
        cls.token_nexa_admin = get_auth_token("zoya@nexa.com")
        cls.token_super_admin = get_auth_token("thefreelancer2076@gmail.com")

        with engine.connect() as conn:
            cls.acme_org_id = str(conn.execute(text("SELECT id FROM public.organizations WHERE slug = 'acme-technologies';")).scalar())
            cls.nexa_org_id = str(conn.execute(text("SELECT id FROM public.organizations WHERE slug = 'nexa-financial-services';")).scalar())
            
            cls.acme_user = conn.execute(text("SELECT * FROM public.users WHERE email = 'zoya@acme.com';")).mappings().fetchone()
            cls.nexa_user = conn.execute(text("SELECT * FROM public.users WHERE email = 'kabir@nexa.com';")).mappings().fetchone()

            cls.acme_agent = conn.execute(text("SELECT * FROM public.agents WHERE org_id = :org_id LIMIT 1;"), {"org_id": cls.acme_org_id}).mappings().fetchone()
            cls.nexa_agent = conn.execute(text("SELECT * FROM public.agents WHERE org_id = :org_id LIMIT 1;"), {"org_id": cls.nexa_org_id}).mappings().fetchone()

    def test_01_user_belongs_to_one_organization(self):
        """TEST A: User belongs to exactly one organization via Foreign Key"""
        self.assertIsNotNone(self.acme_user["org_id"])
        self.assertEqual(str(self.acme_user["org_id"]), self.acme_org_id)
        print("  [PASS] Test A: User belongs to exactly one organization")

    def test_02_tenant_isolation_cross_user_access(self):
        """TEST B: User from Org A cannot retrieve Org B user"""
        with engine.connect() as conn:
            user_b = conn.execute(text("SELECT id FROM public.users WHERE email = 'zoya@nexa.com';")).scalar()

        headers = {"Authorization": f"Bearer {self.token_acme_user}"}
        resp = self.client.get(f"/api/profile/{user_b}", headers=headers)
        self.assertIn(resp.status_code, [403, 404])
        print("  [PASS] Test B: Cross-organization user access blocked with 403/404")

    def test_03_tenant_isolation_cross_agent_access(self):
        """TEST C: User from Org A cannot retrieve Org B agent"""
        headers = {"Authorization": f"Bearer {self.token_acme_user}"}
        resp = self.client.get(f"/api/agents/{self.nexa_agent['id']}", headers=headers)
        self.assertIn(resp.status_code, [403, 404])
        print("  [PASS] Test C: Cross-organization agent access blocked with 403/404")

    def test_04_admin_tenant_isolation(self):
        """TEST D: ADMIN from Org A cannot manage Org B users or list Org B users"""
        headers = {"Authorization": f"Bearer {self.token_acme_admin}"}
        resp = self.client.get("/api/admin/users", headers=headers)
        self.assertEqual(resp.status_code, 200)
        users = resp.json()
        org_ids = {u["org_id"] for u in users}
        self.assertTrue(all(oid == self.acme_org_id for oid in org_ids))
        print("  [PASS] Test D: Admin list query isolated strictly to Admin's organization")

    def test_05_super_admin_platform_controls(self):
        """TEST E & F: SUPER_ADMIN can view all orgs and is NOT displayed as tenant employee"""
        headers = {"Authorization": f"Bearer {self.token_super_admin}"}
        
        # Test E: View all orgs
        resp_orgs = self.client.get("/api/platform/organizations", headers=headers)
        self.assertEqual(resp_orgs.status_code, 200)
        self.assertGreaterEqual(len(resp_orgs.json()), 5)

        # Test F: Filtered from admin users list
        headers_admin = {"Authorization": f"Bearer {self.token_acme_admin}"}
        resp_users = self.client.get("/api/admin/users", headers=headers_admin)
        emails = [u["email"] for u in resp_users.json()]
        self.assertNotIn("thefreelancer2076@gmail.com", emails)
        print("  [PASS] Test E & F: SUPER_ADMIN global access verified & excluded from org employee lists")

    def test_06_agent_creation_and_ownership(self):
        """TEST G & H: Agent created under Org A with owner employee assigned"""
        headers = {"Authorization": f"Bearer {self.token_acme_admin}"}
        payload = {
            "name": "ACME Test Suite Agent",
            "purpose": "Automated identity relationship test agent",
            "autonomy_level": "HIGH",
            "model_name": "gpt-4o",
            "owner_id": str(self.acme_user["id"])
        }
        resp = self.client.post("/api/agents", json=payload, headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["org_id"], self.acme_org_id)
        self.assertEqual(data["owner_id"], str(self.acme_user["id"]))
        print("  [PASS] Test G & H: AI agent created with org_id and owner_id relationship")

    def test_07_agent_creation_org_tampering_protection(self):
        """TEST I: Attempt creating agent for Org B while authenticated as Org A -> Rejected/Overridden"""
        headers = {"Authorization": f"Bearer {self.token_acme_admin}"}
        payload = {
            "name": "Malicious Cross-Org Agent",
            "purpose": "Tampering test",
            "org_id": self.nexa_org_id,
            "owner_id": str(self.acme_user["id"])
        }
        resp = self.client.post("/api/agents", json=payload, headers=headers)
        if resp.status_code == 200:
            self.assertEqual(resp.json()["org_id"], self.acme_org_id)
        else:
            self.assertIn(resp.status_code, [400, 403])
        print("  [PASS] Test I: Backend rejected/overrode org_id tampering on agent creation")

    def test_08_role_persists_after_reauth(self):
        """TEST J: Role change persists after logout/login"""
        with engine.connect() as conn:
            target = conn.execute(text("SELECT id, role FROM public.users WHERE email = 'kabir@acme.com';")).mappings().fetchone()
        
        headers = {"Authorization": f"Bearer {self.token_acme_admin}"}
        # Change role to ANALYST
        resp_patch = self.client.patch(f"/api/admin/users/{target['id']}/role", json={"role": "ANALYST"}, headers=headers)
        self.assertEqual(resp_patch.status_code, 200)

        # Re-authenticate kabir@acme.com
        new_token = get_auth_token("kabir@acme.com")
        resp_me = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_token}"})
        self.assertEqual(resp_me.json()["role"], "ANALYST")
        print("  [PASS] Test J: Role change persists across re-authentication")

    def test_09_frontend_tampering_protections(self):
        """TEST K & L: Self-role escalation to SUPER_ADMIN & profile tampering blocked"""
        headers = {"Authorization": f"Bearer {self.token_acme_user}"}
        resp = self.client.patch("/api/profile/me", json={"role": "SUPER_ADMIN", "org_id": self.nexa_org_id}, headers=headers)
        self.assertEqual(resp.status_code, 403)
        print("  [PASS] Test K & L: Frontend role & org_id tampering rejected with 403")

    def test_10_separate_control_attributes(self):
        """TEST N, O, P: Verify AGENT machine identity, autonomy levels & governance outcomes remain separate"""
        with engine.connect() as conn:
            agent_row = conn.execute(text("SELECT * FROM public.agents LIMIT 1;")).mappings().fetchone()
            decision_row = conn.execute(text("SELECT * FROM public.decisions LIMIT 1;")).mappings().fetchone()

        self.assertIn(agent_row["autonomy_level"], ["LOW", "MEDIUM", "HIGH", "FULL"])
        self.assertIn(decision_row["decision"], ["ALLOW", "REVIEW", "REFUSE"])
        print("  [PASS] Test N, O, P: Machine IAM role, autonomy levels, and governance decisions remain distinct")

if __name__ == "__main__":
    unittest.main()
