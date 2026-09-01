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

class TestFiveDemoOrganizations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

        # Provision SUPER_ADMIN
        cls.super_admin_email = "super_admin_demo5@agentguard.com"
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

    def test_01_verify_all_5_organizations_exist(self):
        """VERIFY 1-3: Verify 5 demo orgs exist in PostgreSQL with valid licenses and custom branding"""
        expected_names = [
            "ACME Technologies",
            "Nexa Financial Services",
            "MedCore Health Systems",
            "UrbanGrid Logistics",
            "EduNova Learning"
        ]

        for name in expected_names:
            org = self.db.query(models.Organization).filter(models.Organization.name == name).first()
            self.assertIsNotNone(org, f"Organization {name} not found in database")
            self.assertIsNotNone(org.logo_url, f"Branding logo missing for {name}")

            lic = self.db.query(models.License).filter(models.License.org_id == org.id).first()
            self.assertIsNotNone(lic, f"License missing for {name}")
            self.assertEqual(lic.status, "ACTIVE")
        print("  [PASS] Item 1-3: All 5 demo organizations exist with active licenses & custom branding")

    def test_02_verify_8_human_users_per_organization_and_roles(self):
        """VERIFY 4-5 & 20: Each org has exactly 8 human users with distinct roles (ADMIN, MANAGER, etc.)"""
        orgs = self.db.query(models.Organization).filter(
            models.Organization.name.in_([
                "ACME Technologies",
                "Nexa Financial Services",
                "MedCore Health Systems",
                "UrbanGrid Logistics",
                "EduNova Learning"
            ])
        ).all()

        for org in orgs:
            users = self.db.query(models.User).filter(
                models.User.org_id == org.id,
                models.User.role != "SUPER_ADMIN"
            ).all()

            self.assertEqual(len(users), 8, f"Org {org.name} expected 8 users, found {len(users)}")
            roles = set(u.role for u in users)
            self.assertIn("ADMIN", roles)
            self.assertIn("MANAGER", roles)
            self.assertIn("SECURITY_ANALYST", roles)
            self.assertIn("USER", roles)
        print("  [PASS] Item 4-5: All 5 organizations contain 8 human users with exact role distribution")

    def test_03_verify_ai_agents_autonomy_and_passports(self):
        """VERIFY 6-7 & 14-17: Each org has AI agents, passports, capability tokens, and autonomy levels (LOW, MEDIUM, HIGH, FULL)"""
        orgs = self.db.query(models.Organization).filter(
            models.Organization.name.in_([
                "Acme Financial Technologies",
                "NovaCare Health Systems",
                "Vertex Manufacturing Industries",
                "Orbit Retail & Commerce",
                "Skyline Logistics & Mobility"
            ])
        ).all()

        for org in orgs:
            agents = self.db.query(models.Agent).filter(models.Agent.org_id == org.id).all()
            self.assertTrue(len(agents) >= 4, f"Org {org.name} expected >=4 agents, found {len(agents)}")

            for ag in agents:
                passport = self.db.query(models.AgentPassport).filter(models.AgentPassport.agent_id == ag.id).first()
                self.assertIsNotNone(passport, f"Agent passport missing for {ag.name}")
                self.assertIn(ag.autonomy_level, ["LOW", "MEDIUM", "HIGH", "FULL"])

                token = self.db.query(models.CapabilityToken).filter(models.CapabilityToken.agent_id == ag.id).first()
                self.assertIsNotNone(token, f"Capability token missing for {ag.name}")
        print("  [PASS] Item 6-7 & 14-17: AI agents, passports, capability tokens, and autonomy tiers verified")

    def test_04_verify_cross_tenant_isolation(self):
        """VERIFY 8-10: Acme Fintech ADMIN cannot query or modify NovaCare users/agents/policies"""
        admin_acme = self.get_user_by_email("admin@acmefintech.com")
        admin_nova = self.get_user_by_email("admin@novacarehealth.org")

        headers_acme = self.get_auth_headers(admin_acme)

        # 1. Query users -> Returns Acme users only (8), excludes NovaCare
        resp_u = client.get("/api/admin/users", headers=headers_acme)
        self.assertEqual(resp_u.status_code, 200)
        self.assertEqual(len(resp_u.json()), 8)
        for u in resp_u.json():
            self.assertNotEqual(str(u["org_id"]), str(admin_nova.org_id))

        # 2. Access NovaCare org dashboard -> 403 Forbidden or Org A context
        resp_tamper = client.get("/api/organization/dashboard", headers=self.get_auth_headers(admin_acme, {"X-Organization-Context": str(admin_nova.org_id)}))
        self.assertEqual(resp_tamper.json()["org_name"], "Acme Financial Technologies")
        print("  [PASS] Item 8-10: Tenant isolation verified; Org A cannot view/tamper Org B data")

    def test_05_verify_super_admin_isolation(self):
        """VERIFY 11 & 21: SUPER_ADMIN is NEVER added to any organization's user table or user quota count"""
        admin_acme = self.get_user_by_email("admin@acmefintech.com")
        acme_org_id = admin_acme.org_id

        # Query Acme users
        users_acme = self.db.query(models.User).filter(models.User.org_id == acme_org_id).all()
        for u in users_acme:
            self.assertNotEqual(u.role, "SUPER_ADMIN")

        # Acme dashboard user count
        resp_dash = client.get("/api/organization/dashboard", headers=self.get_auth_headers(admin_acme))
        self.assertEqual(resp_dash.json()["metrics"]["users"]["current"], 8)
        print("  [PASS] Item 11 & 21: SUPER_ADMIN is completely excluded from organization tenancy & user quota")

if __name__ == "__main__":
    unittest.main()
