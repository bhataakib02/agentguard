import sys
import unittest
from sqlalchemy import text
from fastapi.testclient import TestClient

sys.path.insert(0, r"d:\AGENTGUARD\backend")
from database import engine, SessionLocal
from config import settings
from main import app
from core import security
import models

class TestIdentityRelationships(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        try:
            # 1. Ensure Org A (Acme Identity Corporation)
            org_a = cls.db.query(models.Organization).filter(
                (models.Organization.slug == "acme-identity-corp") |
                (models.Organization.name == "Acme Identity Corporation")
            ).first()
            if not org_a:
                org_a = models.Organization(
                    name="Acme Identity Corporation",
                    slug="acme-identity-corp",
                    domain="acme-identity.com",
                    status="ACTIVE"
                )
                cls.db.add(org_a)
                cls.db.commit()
                cls.db.refresh(org_a)
            else:
                if org_a.slug != "acme-identity-corp":
                    org_a.slug = "acme-identity-corp"
                    cls.db.commit()
            cls.acme_org_id = str(org_a.id)

            # 2. Ensure Org B (Nexa Financial Services)
            org_b = cls.db.query(models.Organization).filter(
                (models.Organization.slug == "nexa-financial-services") |
                (models.Organization.name == "Nexa Financial Services")
            ).first()
            if not org_b:
                org_b = models.Organization(
                    name="Nexa Financial Services",
                    slug="nexa-financial-services",
                    domain="nexa.com",
                    status="ACTIVE"
                )
                cls.db.add(org_b)
                cls.db.commit()
                cls.db.refresh(org_b)
            else:
                if org_b.slug != "nexa-financial-services":
                    org_b.slug = "nexa-financial-services"
                    cls.db.commit()
            cls.nexa_org_id = str(org_b.id)

            # Helper to idempotently provision or update users
            def ensure_user(org_id, email, full_name, role):
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
                else:
                    if u.org_id != org_id or u.role != role or u.status != "ACTIVE":
                        u.org_id = org_id
                        u.role = role
                        u.status = "ACTIVE"
                        cls.db.commit()
                        cls.db.refresh(u)
                return u

            cls.user_acme = ensure_user(org_a.id, "zoya@acme.com", "Zoya Khan", "USER")
            cls.admin_acme = ensure_user(org_a.id, "aarav@acme.com", "Aarav Patel", "ADMIN")
            cls.kabir_acme = ensure_user(org_a.id, "kabir@acme.com", "Kabir Mehta", "USER")

            cls.admin_nexa = ensure_user(org_b.id, "zoya@nexa.com", "Zoya Khan", "ADMIN")
            cls.user_nexa = ensure_user(org_b.id, "kabir@nexa.com", "Kabir Mehta", "USER")

            # Ensure SUPER_ADMIN
            sa = cls.db.query(models.User).filter(models.User.email == "thefreelancer2076@gmail.com").first()
            if not sa:
                sa = cls.db.query(models.User).filter(models.User.role == "SUPER_ADMIN").first()
                if not sa:
                    sa = models.User(
                        org_id=None,
                        email="thefreelancer2076@gmail.com",
                        full_name="Platform Super Admin",
                        role="SUPER_ADMIN",
                        status="ACTIVE"
                    )
                    cls.db.add(sa)
                    cls.db.commit()
                    cls.db.refresh(sa)
                else:
                    sa.email = "thefreelancer2076@gmail.com"
                    cls.db.commit()
            else:
                if sa.role != "SUPER_ADMIN":
                    sa.role = "SUPER_ADMIN"
                    cls.db.commit()
            cls.super_admin = sa

            # Ensure Agent in Org A
            agent_a = cls.db.query(models.Agent).filter(models.Agent.org_id == org_a.id).first()
            if not agent_a:
                agent_a = models.Agent(
                    org_id=org_a.id,
                    name="ACME Core Agent",
                    agent_code="AGT-ACME-TEST-01",
                    purpose="Automated test agent for identity relationship suite",
                    autonomy_level="HIGH",
                    status="ACTIVE",
                    owner_id=cls.user_acme.id
                )
                cls.db.add(agent_a)
                cls.db.commit()
                cls.db.refresh(agent_a)
            cls.acme_agent = {"id": str(agent_a.id), "name": agent_a.name, "org_id": str(agent_a.org_id)}

            # Ensure Agent in Org B
            agent_b = cls.db.query(models.Agent).filter(models.Agent.org_id == org_b.id).first()
            if not agent_b:
                agent_b = models.Agent(
                    org_id=org_b.id,
                    name="Nexa Risk Agent",
                    agent_code="AGT-NEXA-TEST-01",
                    purpose="Automated test agent for identity relationship suite",
                    autonomy_level="MEDIUM",
                    status="ACTIVE",
                    owner_id=cls.user_nexa.id
                )
                cls.db.add(agent_b)
                cls.db.commit()
                cls.db.refresh(agent_b)
            cls.nexa_agent = {"id": str(agent_b.id), "name": agent_b.name, "org_id": str(agent_b.org_id)}

            # Ensure at least one Decision exists in the DB for test_10
            decision = cls.db.query(models.Decision).first()
            if not decision:
                decision = models.Decision(
                    org_id=org_a.id,
                    agent_id=agent_a.id,
                    decision="ALLOW",
                    action_type="DATA_QUERY",
                    risk_score=0.1
                )
                cls.db.add(decision)
                cls.db.commit()

            cls.acme_user = {"id": str(cls.user_acme.id), "org_id": str(cls.user_acme.org_id), "email": cls.user_acme.email}
            cls.nexa_user = {"id": str(cls.user_nexa.id), "org_id": str(cls.user_nexa.org_id), "email": cls.user_nexa.email}

            # Deterministic, local cryptographic JWT access tokens
            cls.token_acme_user = security.create_access_token(cls.user_acme.id, email=cls.user_acme.email, role=cls.user_acme.role)
            cls.token_acme_admin = security.create_access_token(cls.admin_acme.id, email=cls.admin_acme.email, role=cls.admin_acme.role)
            cls.token_nexa_admin = security.create_access_token(cls.admin_nexa.id, email=cls.admin_nexa.email, role=cls.admin_nexa.role)
            cls.token_super_admin = security.create_access_token(cls.super_admin.id, email=cls.super_admin.email, role=cls.super_admin.role)
        finally:
            cls.db.close()

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
        new_token = security.create_access_token(target['id'], email="kabir@acme.com")
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
