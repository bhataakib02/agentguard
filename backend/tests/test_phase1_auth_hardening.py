import unittest
import uuid
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from starlette.testclient import TestClient
from main import app
from database import SessionLocal
from core import security
from jose import jwt
import models

client = TestClient(app)

class TestPhase1AuthHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

        # 1. Ensure a platform organization exists
        cls.platform_org = cls.db.query(models.Organization).filter(models.Organization.name == "Phase 1 Security Platform").first()
        if not cls.platform_org:
            cls.platform_org = models.Organization(name="Phase 1 Security Platform", domain="agentguard.security", status="ACTIVE")
            cls.db.add(cls.platform_org)
            cls.db.commit()
            cls.db.refresh(cls.platform_org)

        # 2. Ensure a tenant organization exists
        cls.tenant_org = cls.db.query(models.Organization).filter(models.Organization.name == "Phase 1 Tenant Org").first()
        if not cls.tenant_org:
            cls.tenant_org = models.Organization(name="Phase 1 Tenant Org", domain="tenant.security", status="ACTIVE")
            cls.db.add(cls.tenant_org)
            cls.db.commit()
            cls.db.refresh(cls.tenant_org)

        # 3. Provision a verified SUPER_ADMIN user
        cls.super_admin_email = f"sa_phase1_{uuid.uuid4().hex[:6]}@agentguard.com"
        cls.super_admin = models.User(
            org_id=cls.platform_org.id,
            email=cls.super_admin_email,
            full_name="Phase 1 Super Admin",
            role="SUPER_ADMIN",
            status="ACTIVE"
        )
        cls.db.add(cls.super_admin)

        # 4. Provision a normal tenant USER
        cls.normal_user_email = f"normal_{uuid.uuid4().hex[:6]}@tenant.com"
        cls.normal_user = models.User(
            org_id=cls.tenant_org.id,
            email=cls.normal_user_email,
            full_name="Standard Employee",
            role="USER",
            status="ACTIVE"
        )
        cls.db.add(cls.normal_user)

        # 5. Provision a tenant ADMIN user
        cls.tenant_admin_email = f"admin_{uuid.uuid4().hex[:6]}@tenant.com"
        cls.tenant_admin = models.User(
            org_id=cls.tenant_org.id,
            email=cls.tenant_admin_email,
            full_name="Tenant Admin",
            role="ADMIN",
            status="ACTIVE"
        )
        cls.db.add(cls.tenant_admin)

        # 6. Provision a SUSPENDED user
        cls.suspended_user_email = f"suspended_{uuid.uuid4().hex[:6]}@tenant.com"
        cls.suspended_user = models.User(
            org_id=cls.tenant_org.id,
            email=cls.suspended_user_email,
            full_name="Suspended Employee",
            role="USER",
            status="SUSPENDED"
        )
        cls.db.add(cls.suspended_user)

        cls.db.commit()
        cls.db.refresh(cls.super_admin)
        cls.db.refresh(cls.normal_user)
        cls.db.refresh(cls.tenant_admin)
        cls.db.refresh(cls.suspended_user)

    def setUp(self):
        self.db.rollback()

    def get_token(self, user_obj):
        return security.create_access_token(user_obj.id, email=user_obj.email, role=user_obj.role)

    # --- TEST 1: Unauthenticated access is rejected on core endpoints ---
    def test_01_unauthenticated_requests_rejected(self):
        """Unauthenticated requests to protected endpoints must return 401"""
        resp_me = client.get("/api/auth/me")
        self.assertEqual(resp_me.status_code, 401, "Unauthenticated /auth/me must return 401")

        resp_platform = client.get("/api/platform/overview")
        self.assertEqual(resp_platform.status_code, 401, "Unauthenticated /platform/overview must return 401")

        resp_empty_bearer = client.get("/api/auth/me", headers={"Authorization": "Bearer "})
        self.assertEqual(resp_empty_bearer.status_code, 401, "Empty Bearer token must return 401")

    # --- TEST 2: Forged / tampered tokens are rejected ---
    def test_02_forged_tokens_rejected(self):
        """Forged JWTs with forged secret or unverified claims must return 401"""
        fake_token = jwt.encode(
            {"sub": str(self.super_admin.id), "email": self.super_admin.email, "role": "SUPER_ADMIN"},
            "attacker-fake-secret-key",
            algorithm="HS256"
        )
        resp = client.get("/api/platform/overview", headers={"Authorization": f"Bearer {fake_token}"})
        self.assertEqual(resp.status_code, 401, "Forged JWT with fake secret key must be rejected with 401")

        garbage_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalidpayload.invalidsig"
        resp_garbage = client.get("/api/auth/me", headers={"Authorization": f"Bearer {garbage_token}"})
        self.assertEqual(resp_garbage.status_code, 401, "Malformed token must be rejected with 401")

    # --- TEST 3: Normal user cannot access SUPER_ADMIN platform endpoints ---
    def test_03_normal_user_denied_platform_access(self):
        """Authenticated normal user accessing /platform/* must be rejected with 403 Forbidden"""
        user_token = self.get_token(self.normal_user)
        headers = {"Authorization": f"Bearer {user_token}"}

        resp_me = client.get("/api/auth/me", headers=headers)
        self.assertEqual(resp_me.status_code, 200, "Normal user can access own /auth/me")
        self.assertEqual(resp_me.json()["role"], "USER")

        # Attempt to access platform endpoints
        resp_overview = client.get("/api/platform/overview", headers=headers)
        self.assertEqual(resp_overview.status_code, 403, "Normal user must receive 403 on /platform/overview")

        resp_orgs = client.get("/api/platform/organizations", headers=headers)
        self.assertEqual(resp_orgs.status_code, 403, "Normal user must receive 403 on /platform/organizations")

        resp_licenses = client.get("/api/platform/licenses", headers=headers)
        self.assertEqual(resp_licenses.status_code, 403, "Normal user must receive 403 on /platform/licenses")

        resp_plans = client.get("/api/platform/plans", headers=headers)
        self.assertEqual(resp_plans.status_code, 403, "Normal user must receive 403 on /platform/plans")

    # --- TEST 4: SUPER_ADMIN allowed on platform endpoints ---
    def test_04_super_admin_allowed_platform_access(self):
        """Authenticated SUPER_ADMIN has authoritative access to /platform/*"""
        sa_token = self.get_token(self.super_admin)
        headers = {"Authorization": f"Bearer {sa_token}"}

        resp_me = client.get("/api/auth/me", headers=headers)
        self.assertEqual(resp_me.status_code, 200)
        self.assertEqual(resp_me.json()["role"], "SUPER_ADMIN")

        resp_overview = client.get("/api/platform/overview", headers=headers)
        self.assertEqual(resp_overview.status_code, 200, "SUPER_ADMIN must receive 200 on /platform/overview")

        resp_orgs = client.get("/api/platform/organizations", headers=headers)
        self.assertEqual(resp_orgs.status_code, 200, "SUPER_ADMIN must receive 200 on /platform/organizations")

        resp_plans = client.get("/api/platform/plans", headers=headers)
        self.assertEqual(resp_plans.status_code, 200, "SUPER_ADMIN must receive 200 on /platform/plans")

    # --- TEST 5: Suspended accounts are rejected ---
    def test_05_suspended_account_rejected(self):
        """Tokens for suspended or inactive accounts must receive 403 Forbidden"""
        suspended_token = self.get_token(self.suspended_user)
        headers = {"Authorization": f"Bearer {suspended_token}"}

        resp = client.get("/api/auth/me", headers=headers)
        self.assertEqual(resp.status_code, 403, "Suspended user must receive 403 on authenticated endpoints")

    # --- TEST 6: Unauthenticated /auth/login cannot issue tokens ---
    def test_06_unauthenticated_login_sync_rejected(self):
        """Direct call to /auth/login without authentication header must be rejected with 401"""
        resp = client.post("/api/auth/login", json={
            "email": self.super_admin.email,
            "auth_user_id": str(self.super_admin.id)
        })
        self.assertEqual(resp.status_code, 401, "Unauthenticated POST /auth/login must be rejected with 401")

    # --- TEST 7: /auth/login email mismatch rejected ---
    def test_07_login_sync_email_mismatch_rejected(self):
        """Calling /auth/login with token belonging to user A but requesting user B must return 403"""
        user_token = self.get_token(self.normal_user)
        headers = {"Authorization": f"Bearer {user_token}"}

        resp = client.post("/api/auth/login", json={
            "email": self.super_admin.email,
            "auth_user_id": str(self.super_admin.id)
        }, headers=headers)
        self.assertEqual(resp.status_code, 403, "Impersonation via /auth/login must be rejected with 403")

    # --- TEST 8: Registration cannot escalate role to SUPER_ADMIN ---
    def test_08_registration_cannot_grant_super_admin(self):
        """Self-registration cannot grant SUPER_ADMIN role even if requested in payload"""
        reg_email = f"reg_{uuid.uuid4().hex[:6]}@test.com"
        resp = client.post("/api/auth/register", json={
            "org_name": "Test Org Escalation",
            "full_name": "Attacker Account",
            "email": reg_email,
            "role": "SUPER_ADMIN"
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["role"], "USER", "Self-registered user role must be forced to USER")

        db_user = self.db.query(models.User).filter(models.User.email == reg_email).first()
        self.assertEqual(db_user.role, "USER", "Database record role must strictly be USER")

    # --- TEST 9: Duplicate registration returns 409 Conflict (prevents takeover bypass) ---
    def test_09_registration_duplicate_email_rejected_409(self):
        """Attempting to register with an existing user email must return 409 Conflict instead of issuing a token"""
        resp = client.post("/api/auth/register", json={
            "org_name": "Takeover Attempt",
            "full_name": "Takeover",
            "email": self.super_admin_email
        })
        self.assertEqual(resp.status_code, 409, "Registration with existing email must return 409 Conflict")

    # --- TEST 10: Logout invalidates session server-side ---
    def test_10_logout_invalidates_session(self):
        """Calling /api/auth/logout must revoke the session, and subsequent calls with that token must return 401"""
        # Create a test session
        token = self.get_token(self.normal_user)
        session = models.Session(
            user_id=self.normal_user.id,
            token=token,
            expires_at=security.utcnow() + security.timedelta(hours=1),
            revoked=False
        )
        self.db.add(session)
        self.db.commit()

        headers = {"Authorization": f"Bearer {token}"}

        # Token is valid initially
        resp_before = client.get("/api/auth/me", headers=headers)
        self.assertEqual(resp_before.status_code, 200)

        # Call logout
        resp_logout = client.post("/api/auth/logout", headers=headers)
        self.assertEqual(resp_logout.status_code, 200)
        self.assertEqual(resp_logout.json()["status"], "SUCCESS")

        # Now token must be rejected with 401
        resp_after = client.get("/api/auth/me", headers=headers)
        self.assertEqual(resp_after.status_code, 401, "Revoked token must be rejected with 401")

    # --- TEST 11: All domain endpoints reject unauthenticated access ---
    def test_11_unauthenticated_domain_endpoints_rejected(self):
        """All domain control endpoints must return 401 for unauthenticated requests"""
        endpoints = [
            "/api/iam/users",
            "/api/iam/roles",
            "/api/iam/api-keys",
            "/api/iam/sessions",
            "/api/approvals",
            "/api/capabilities",
            "/api/decisions",
            "/api/security/incidents",
            "/api/security/overview",
            "/api/audit/logs",
            "/api/runtime/circuit-breakers",
            "/api/policies",
            "/api/red-team/tests",
            "/api/risk/agents",
            "/api/risk/trends",
            "/api/analytics/overview",
            "/api/behavior/profiles",
            "/api/trust",
            "/api/provenance/events",
            "/api/digital-twin/simulations",
            "/api/economics/budgets",
            "/api/notifications",
            "/api/permissions",
            "/api/agent-network/graph",
            "/api/developers/docs-summary",
            "/api/integrations",
            "/api/optimization/compute",
            "/api/impact/metrics",
            "/api/ai/models",
            "/api/settings",
        ]
        for ep in endpoints:
            resp = client.get(ep)
            self.assertEqual(resp.status_code, 401, f"Unauthenticated GET {ep} must return 401 Unauthorized, got {resp.status_code}")

    # --- TEST 12: CORS configuration allows trusted origins and rejects wildcards with credentials ---
    def test_12_cors_allowed_and_disallowed_origins(self):
        """CORS preflight request for allowed origin returns headers, invalid origin does not get allowed origin"""
        # Allowed origin
        resp_allowed = client.options("/api/auth/me", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })
        self.assertEqual(resp_allowed.headers.get("access-control-allow-origin"), "http://localhost:3000")
        self.assertEqual(resp_allowed.headers.get("access-control-allow-credentials"), "true")

        # Disallowed origin
        resp_disallowed = client.options("/api/auth/me", headers={
            "Origin": "https://malicious-site.com",
            "Access-Control-Request-Method": "GET"
        })
        self.assertNotEqual(
            resp_disallowed.headers.get("access-control-allow-origin"),
            "https://malicious-site.com",
            "Malicious origin must not be allowed"
        )

    # --- TEST 13: Normal user denied admin routes ---
    def test_13_normal_user_denied_admin_routes(self):
        """Normal user accessing /api/admin/users must receive 403 Forbidden"""
        user_token = self.get_token(self.normal_user)
        headers = {"Authorization": f"Bearer {user_token}"}
        resp = client.get("/api/admin/users", headers=headers)
        self.assertEqual(resp.status_code, 403, "Normal user must receive 403 on /api/admin/users")

    # --- TEST 14: Tenant admin allowed on admin routes but scoped to own organization ---
    def test_14_tenant_admin_scoped_access(self):
        """Tenant admin can access /api/admin/users but only sees their own organization's users"""
        admin_token = self.get_token(self.tenant_admin)
        headers = {"Authorization": f"Bearer {admin_token}"}
        resp = client.get("/api/admin/users", headers=headers)
        self.assertEqual(resp.status_code, 200)
        users = resp.json()
        for u in users:
            self.assertEqual(str(u["org_id"]), str(self.tenant_org.id))
            self.assertNotEqual(u["role"], "SUPER_ADMIN", "SUPER_ADMIN must never appear in tenant user list")


    # ==========================================================
    # EXACT 13 SECURITY TESTS REQUIRED BY PHASE 1 SPECIFICATION
    # ==========================================================

    def test_spec_01_unauthenticated_to_protected_endpoint(self):
        """TEST 1: Unauthenticated -> protected endpoint | EXPECTED: 401/403"""
        resp = client.get("/api/auth/me")
        self.assertIn(resp.status_code, [401, 403], f"Unauthenticated request must return 401/403, got {resp.status_code}")

    def test_spec_02_normal_user_to_super_admin_endpoint(self):
        """TEST 2: Normal USER -> SUPER_ADMIN endpoint | EXPECTED: 403"""
        user_token = self.get_token(self.normal_user)
        resp = client.get("/api/platform/overview", headers={"Authorization": f"Bearer {user_token}"})
        self.assertEqual(resp.status_code, 403, f"Normal USER accessing SUPER_ADMIN endpoint must return 403, got {resp.status_code}")

    def test_spec_03_org_admin_to_platform_endpoint(self):
        """TEST 3: Organization ADMIN -> platform endpoint | EXPECTED: 403"""
        admin_token = self.get_token(self.tenant_admin)
        resp = client.get("/api/platform/overview", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(resp.status_code, 403, f"Org ADMIN accessing platform endpoint must return 403, got {resp.status_code}")

    def test_spec_04_super_admin_to_platform_endpoint(self):
        """TEST 4: SUPER_ADMIN -> platform endpoint | EXPECTED: success (200)"""
        sa_token = self.get_token(self.super_admin)
        resp = client.get("/api/platform/overview", headers={"Authorization": f"Bearer {sa_token}"})
        self.assertEqual(resp.status_code, 200, f"SUPER_ADMIN accessing platform endpoint must succeed, got {resp.status_code}")

    def test_spec_05_org_a_user_to_org_b_resource(self):
        """TEST 5: Organization A user -> Organization B resource | EXPECTED: 403/404"""
        # Create an agent in platform_org (Org B)
        org_b_agent = self.db.query(models.Agent).filter(models.Agent.org_id == self.platform_org.id).first()
        if not org_b_agent:
            org_b_agent = models.Agent(
                org_id=self.platform_org.id,
                owner_id=self.super_admin.id,
                agent_code=f"AG-{uuid.uuid4().hex[:4]}",
                name="Org B Confidential Agent",
                department="Operations",
                purpose="Cross-org security isolation test",
                model_name="gpt-4o",
                model_version="1.0.0",
                environment="PRODUCTION",
                autonomy_level="LOW",
                status="NORMAL",
                daily_budget=1000.0
            )
            self.db.add(org_b_agent)
            self.db.commit()
            self.db.refresh(org_b_agent)

        user_a_token = self.get_token(self.normal_user)
        # Normal user in Org A attempts to access Org B's agent
        resp = client.get(f"/api/agents/{org_b_agent.id}", headers={"Authorization": f"Bearer {user_a_token}"})
        self.assertIn(resp.status_code, [403, 404], f"Cross-org resource access must return 403/404, got {resp.status_code}")

    def test_spec_06_tampered_org_id_rejected(self):
        """TEST 6: Tampered org_id | EXPECTED: rejected / ignored"""
        user_a_token = self.get_token(self.normal_user)
        # User in Org A sends X-Organization-Context for Org B
        resp = client.get("/api/organization/dashboard", headers={
            "Authorization": f"Bearer {user_a_token}",
            "X-Organization-Context": str(self.platform_org.id)
        })
        self.assertEqual(resp.status_code, 200)
        # Server must derive org from user identity, not from client header
        self.assertEqual(resp.json()["org_id"], str(self.tenant_org.id), "Server must not trust client-provided org_id")

    def test_spec_07_tampered_role_rejected(self):
        """TEST 7: Tampered role | EXPECTED: rejected"""
        # Attacker signs token with their own secret claiming SUPER_ADMIN
        tampered_token = jwt.encode(
            {"sub": str(self.normal_user.id), "email": self.normal_user.email, "role": "SUPER_ADMIN"},
            "attacker_key",
            algorithm="HS256"
        )
        resp = client.get("/api/platform/overview", headers={"Authorization": f"Bearer {tampered_token}"})
        self.assertEqual(resp.status_code, 401, "Tampered signature/role must be rejected with 401")

        # Also test profile update attempting to escalate role
        user_token = self.get_token(self.normal_user)
        resp_esc = client.patch("/api/profile/me", json={"role": "SUPER_ADMIN"}, headers={"Authorization": f"Bearer {user_token}"})
        self.assertEqual(resp_esc.status_code, 403, "Privilege escalation attempt must be rejected with 403")

    def test_spec_08_invalid_token(self):
        """TEST 8: Invalid token | EXPECTED: 401"""
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid_garbage_token_value_xyz"})
        self.assertEqual(resp.status_code, 401, "Invalid token must return 401")

    def test_spec_09_expired_token_or_session(self):
        """TEST 9: Expired token/session | EXPECTED: 401"""
        from datetime import datetime, timedelta, timezone
        expired_dt = datetime.now(timezone.utc) - timedelta(hours=2)
        expired_token = jwt.encode(
            {"sub": str(self.normal_user.id), "email": self.normal_user.email, "role": "USER", "exp": expired_dt},
            security.settings.SECRET_KEY,
            algorithm=security.settings.ALGORITHM
        )
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        self.assertEqual(resp.status_code, 401, "Expired token must return 401")

    def test_spec_10_logout_then_protected_request(self):
        """TEST 10: Logout -> protected request | EXPECTED: rejected (401)"""
        token = self.get_token(self.normal_user)
        session = models.Session(
            user_id=self.normal_user.id,
            token=token,
            expires_at=security.utcnow() + security.timedelta(hours=1),
            revoked=False
        )
        self.db.add(session)
        self.db.commit()

        # Logout
        resp_logout = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(resp_logout.status_code, 200)

        # Protected request after logout
        resp_protected = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(resp_protected.status_code, 401, "Request with revoked session must be rejected with 401")

    def test_spec_11_direct_platform_api_call_without_auth(self):
        """TEST 11: Direct /platform API call without authentication | EXPECTED: rejected (401)"""
        resp = client.get("/api/platform/overview")
        self.assertEqual(resp.status_code, 401, "Unauthenticated direct call to /platform must return 401")

    def test_spec_12_cors_preflight_from_allowed_origin(self):
        """TEST 12: CORS preflight from allowed origin | EXPECTED: successful"""
        resp = client.options("/api/auth/me", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })
        self.assertEqual(resp.headers.get("access-control-allow-origin"), "http://localhost:3000")
        self.assertEqual(resp.headers.get("access-control-allow-credentials"), "true")

    def test_spec_13_cors_request_from_unauthorized_origin(self):
        """TEST 13: CORS request from unauthorized origin | EXPECTED: rejected / not allowed"""
        resp = client.options("/api/auth/me", headers={
            "Origin": "https://unauthorized-attacker-site.com",
            "Access-Control-Request-Method": "GET"
        })
        self.assertNotEqual(
            resp.headers.get("access-control-allow-origin"),
            "https://unauthorized-attacker-site.com",
            "Unauthorized origin must not receive Access-Control-Allow-Origin"
        )


if __name__ == "__main__":
    unittest.main()

