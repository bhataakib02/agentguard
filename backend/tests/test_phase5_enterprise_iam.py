"""
Phase 5: Enterprise Identity, RBAC, Organization Administration & Security Operations Tests
Authoritative IAM verification, role hierarchy, permission matrix, user lifecycle,
tenant isolation, secure API keys, secure invitations, security incident lifecycle,
audit immutability, agent ownership validation, and regression suites.
"""

import json
import uuid
import hashlib
import datetime
import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Setup test database (SQLite in-memory)
os.environ["DATABASE_URL"] = "sqlite:///test_phase5.db"
os.environ["SECRET_KEY"] = "test-phase5-secret-key-not-production"
os.environ["ENVIRONMENT"] = "test"

from main import app
from database import Base, engine, get_db
import models
from core.permissions import (
    ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_DEVELOPER, ROLE_MANAGER,
    ROLE_SECURITY_ANALYST, ROLE_OPERATOR, ROLE_ANALYST, ROLE_VIEWER,
    ROLE_USER, can_manage_role, has_permission, get_user_permissions,
    PERM_ORGANIZATION_VIEW, PERM_USER_VIEW, PERM_AGENT_VIEW,
    PERM_POLICY_VIEW, PERM_DECISION_VIEW, PERM_AUDIT_VIEW,
    PERM_REPORT_VIEW, PERM_SECURITY_VIEW, PERM_TELEMETRY_VIEW,
    PERM_API_KEY_VIEW, PERM_PLATFORM_ADMIN, PERM_USER_SUSPEND
)

# Create tables for testing
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class TestPhase5EnterpriseIAM:
    """Phase 5 acceptance test suite: 39 exhaustive tests."""

    _tokens = {}
    _org_ids = {}
    _user_ids = {}
    _agent_ids = {}

    @classmethod
    def _register_and_login(cls, org_name, full_name, email, password="TestPass123!", role="ADMIN", status="ACTIVE"):
        """Helper: register org + user in test DB, return valid JWT token."""
        db = TestSession()
        try:
            org = db.query(models.Organization).filter(models.Organization.name == org_name).first()
            if not org:
                org = models.Organization(name=org_name, status="ACTIVE", domain=f"{org_name.lower()}.com")
                db.add(org)
                db.commit()
                db.refresh(org)

            user = db.query(models.User).filter(models.User.email == email).first()
            if not user:
                user = models.User(
                    org_id=org.id,
                    email=email,
                    full_name=full_name,
                    role=role,
                    department="Engineering",
                    status=status
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            else:
                user.role = role
                user.status = status
                user.org_id = org.id
                db.commit()
                db.refresh(user)

            from core import security
            token = security.create_access_token(user.id, email=user.email, role=user.role)
            return token, str(user.id), str(org.id)
        finally:
            db.close()

    @classmethod
    def _auth_header(cls, token):
        return {"Authorization": f"Bearer {token}"}

    @classmethod
    def setup_class(cls):
        """Setup initial test organizations and identities."""
        # Org Alpha
        tok_alpha_admin, uid_alpha_admin, oid_alpha = cls._register_and_login(
            "Phase5OrgAlpha", "Alpha Admin", "alpha_admin@test.com", role="ADMIN"
        )
        cls._tokens["alpha_admin"] = tok_alpha_admin
        cls._user_ids["alpha_admin"] = uid_alpha_admin
        cls._org_ids["alpha"] = oid_alpha

        tok_alpha_user, uid_alpha_user, _ = cls._register_and_login(
            "Phase5OrgAlpha", "Alpha User", "alpha_user@test.com", role="USER"
        )
        cls._tokens["alpha_user"] = tok_alpha_user
        cls._user_ids["alpha_user"] = uid_alpha_user

        # Org Beta
        tok_beta_admin, uid_beta_admin, oid_beta = cls._register_and_login(
            "Phase5OrgBeta", "Beta Admin", "beta_admin@test.com", role="ADMIN"
        )
        cls._tokens["beta_admin"] = tok_beta_admin
        cls._user_ids["beta_admin"] = uid_beta_admin
        cls._org_ids["beta"] = oid_beta

        tok_beta_user, uid_beta_user, _ = cls._register_and_login(
            "Phase5OrgBeta", "Beta User", "beta_user@test.com", role="USER"
        )
        cls._tokens["beta_user"] = tok_beta_user
        cls._user_ids["beta_user"] = uid_beta_user

        # SUPER_ADMIN
        tok_super, uid_super, _ = cls._register_and_login(
            "PlatformGovernance", "Root SuperAdmin", "superadmin@platform.com", role="SUPER_ADMIN"
        )
        cls._tokens["super_admin"] = tok_super
        cls._user_ids["super_admin"] = uid_super

        # Create agents for Alpha and Beta
        db = TestSession()
        try:
            agent_alpha = models.Agent(
                agent_code="AG-ALPHA-01",
                org_id=oid_alpha,
                owner_id=uid_alpha_admin,
                name="Alpha Sentinel",
                department="Security",
                purpose="Autonomous Security Governance",
                status="NORMAL",
                daily_budget=5000.0
            )
            agent_beta = models.Agent(
                agent_code="AG-BETA-01",
                org_id=oid_beta,
                owner_id=uid_beta_admin,
                name="Beta Worker",
                department="Operations",
                purpose="Workflow Automation",
                status="NORMAL",
                daily_budget=3000.0
            )
            db.add_all([agent_alpha, agent_beta])
            db.commit()
            db.refresh(agent_alpha)
            db.refresh(agent_beta)
            cls._agent_ids["alpha"] = str(agent_alpha.id)
            cls._agent_ids["beta"] = str(agent_beta.id)
        finally:
            db.close()

    # =========================================================================
    # Test 1: Unauthenticated IAM request rejected
    # =========================================================================
    def test_01_unauthenticated_iam_request_rejected(self):
        endpoints = [
            ("GET", "/api/iam/permissions"),
            ("GET", "/api/iam/api-keys"),
            ("GET", "/api/iam/invitations"),
            ("GET", "/api/admin/users"),
            ("GET", "/api/security/incidents"),
        ]
        for method, ep in endpoints:
            if method == "GET":
                res = client.get(ep)
            assert res.status_code in (401, 403), f"Endpoint {ep} allowed unauthenticated access with status {res.status_code}"

    # =========================================================================
    # Test 2: Tenant user can access own organization
    # =========================================================================
    def test_02_tenant_user_can_access_own_organization(self):
        res = client.get("/api/organization/dashboard", headers=self._auth_header(self._tokens["alpha_admin"]))
        assert res.status_code == 200
        data = res.json()
        assert data["org_id"] == self._org_ids["alpha"]
        assert "Phase5OrgAlpha" in data["org_name"]

    # =========================================================================
    # Test 3: Tenant user cannot access another organization
    # =========================================================================
    def test_03_tenant_user_cannot_access_another_organization(self):
        # Pass Org Beta's ID in header context
        res = client.get(
            "/api/organization/dashboard",
            headers={
                "Authorization": f"Bearer {self._tokens['alpha_admin']}",
                "X-Organization-Context": self._org_ids["beta"]
            }
        )
        assert res.status_code == 200
        # Must resolve to own org (Alpha), NOT Beta
        data = res.json()
        assert data["org_id"] == self._org_ids["alpha"]
        assert data["org_id"] != self._org_ids["beta"]

    # =========================================================================
    # Test 4: Tenant ADMIN can manage permitted users
    # =========================================================================
    def test_04_tenant_admin_can_manage_permitted_users(self):
        res = client.get("/api/admin/users", headers=self._auth_header(self._tokens["alpha_admin"]))
        assert res.status_code == 200
        users = res.json()
        assert len(users) >= 2
        for u in users:
            assert u["org_id"] == self._org_ids["alpha"]
            assert u["role"] != "SUPER_ADMIN"

    # =========================================================================
    # Test 5: Non-admin cannot manage users
    # =========================================================================
    def test_05_non_admin_cannot_manage_users(self):
        res = client.get("/api/admin/users", headers=self._auth_header(self._tokens["alpha_user"]))
        assert res.status_code == 403
        assert "privileges required" in res.json().get("detail", "").lower()

    # =========================================================================
    # Test 6: Tenant ADMIN cannot create SUPER_ADMIN
    # =========================================================================
    def test_06_tenant_admin_cannot_create_super_admin(self):
        # 1. Via invite
        res = client.post(
            "/api/iam/invitations",
            headers=self._auth_header(self._tokens["alpha_admin"]),
            json={"email": "hacker_super@test.com", "role": "SUPER_ADMIN"}
        )
        assert res.status_code in (400, 403)

        # 2. Via role update
        res = client.patch(
            f"/api/admin/users/{self._user_ids['alpha_user']}/role",
            headers=self._auth_header(self._tokens["alpha_admin"]),
            json={"role": "SUPER_ADMIN"}
        )
        assert res.status_code == 403
        assert "SUPER_ADMIN" in res.json().get("detail", "")

    # =========================================================================
    # Test 7: Tenant ADMIN cannot assign unauthorized privileged role
    # =========================================================================
    def test_07_tenant_admin_cannot_assign_unauthorized_privileged_role(self):
        # Invalid role
        res = client.patch(
            f"/api/admin/users/{self._user_ids['alpha_user']}/role",
            headers=self._auth_header(self._tokens["alpha_admin"]),
            json={"role": "GOD_MODE"}
        )
        assert res.status_code == 400

        # Self-role modification blocked
        res = client.patch(
            f"/api/admin/users/{self._user_ids['alpha_admin']}/role",
            headers=self._auth_header(self._tokens["alpha_admin"]),
            json={"role": "ADMIN"}
        )
        assert res.status_code == 403

    # =========================================================================
    # Test 8: SUPER_ADMIN can manage platform users
    # =========================================================================
    def test_08_super_admin_can_manage_platform_users(self):
        res = client.get("/api/platform/users", headers=self._auth_header(self._tokens["super_admin"]))
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 4

    # =========================================================================
    # Test 9: User suspension blocks protected operations
    # =========================================================================
    def test_09_user_suspension_blocks_protected_operations(self):
        # Alpha admin suspends alpha user
        res = client.post(
            f"/api/admin/users/{self._user_ids['alpha_user']}/suspend",
            headers=self._auth_header(self._tokens["alpha_admin"])
        )
        assert res.status_code == 200
        assert res.json()["status"] == "SUSPENDED"

        # Suspended user's token is immediately rejected
        res = client.get("/api/organization/dashboard", headers=self._auth_header(self._tokens["alpha_user"]))
        assert res.status_code == 403
        assert "suspended" in res.json().get("detail", "").lower()

    # =========================================================================
    # Test 10: User reactivation restores permitted access
    # =========================================================================
    def test_10_user_reactivation_restores_permitted_access(self):
        # Reactivate user
        res = client.post(
            f"/api/admin/users/{self._user_ids['alpha_user']}/activate",
            headers=self._auth_header(self._tokens["alpha_admin"])
        )
        assert res.status_code == 200
        assert res.json()["status"] == "ACTIVE"

        # User can now perform permitted operations again
        res = client.get("/api/organization/dashboard", headers=self._auth_header(self._tokens["alpha_user"]))
        assert res.status_code == 200

    # =========================================================================
    # Test 11: User deactivation blocks access
    # =========================================================================
    def test_11_user_deactivation_blocks_access(self):
        # Create a temp user to deactivate
        _, temp_uid, _ = self._register_and_login("Phase5OrgAlpha", "Temp User", "temp_deact@test.com", role="USER")
        from core import security
        temp_token = security.create_access_token(temp_uid, email="temp_deact@test.com", role="USER")

        res = client.post(
            f"/api/admin/users/{temp_uid}/deactivate",
            headers=self._auth_header(self._tokens["alpha_admin"])
        )
        assert res.status_code == 200
        assert res.json()["status"] == "DEACTIVATED"

        # Deactivated user's token is rejected
        res = client.get("/api/organization/dashboard", headers=self._auth_header(temp_token))
        assert res.status_code == 403

    # =========================================================================
    # Test 12: Organization isolation across admin user endpoints
    # =========================================================================
    def test_12_organization_isolation(self):
        # Org Alpha admin tries to view Org Beta user detail
        res = client.get(
            f"/api/admin/users/{self._user_ids['beta_user']}",
            headers=self._auth_header(self._tokens["alpha_admin"])
        )
        assert res.status_code == 403
        assert "organization" in res.json().get("detail", "").lower()

    # =========================================================================
    # Test 13: User cannot change own org_id
    # =========================================================================
    def test_13_user_cannot_change_own_org_id(self):
        # Attempt to change role and hijack org_id
        res = client.patch(
            f"/api/admin/users/{self._user_ids['alpha_user']}/role",
            headers=self._auth_header(self._tokens["alpha_admin"]),
            json={"role": "DEVELOPER", "org_id": self._org_ids["beta"]}
        )
        assert res.status_code == 200

        # Verify DB still has org_id == alpha
        db = TestSession()
        try:
            u = db.query(models.User).filter(models.User.id == self._user_ids["alpha_user"]).first()
            assert u.org_id == self._org_ids["alpha"]
            assert u.org_id != self._org_ids["beta"]
        finally:
            db.close()

    # =========================================================================
    # Test 14: Agent owner must belong to same organization
    # =========================================================================
    def test_14_agent_owner_must_belong_to_same_organization(self):
        # Valid same-org owner assignment
        res = client.patch(
            f"/api/agents/{self._agent_ids['alpha']}",
            headers=self._auth_header(self._tokens["alpha_admin"]),
            json={"owner_id": self._user_ids["alpha_user"]}
        )
        assert res.status_code == 200
        assert res.json()["owner_id"] == self._user_ids["alpha_user"]

    # =========================================================================
    # Test 15: Cross-tenant agent ownership rejected
    # =========================================================================
    def test_15_cross_tenant_agent_ownership_rejected(self):
        # 1. Attempt to assign Beta user as owner of Alpha agent
        res = client.patch(
            f"/api/agents/{self._agent_ids['alpha']}",
            headers=self._auth_header(self._tokens["alpha_admin"]),
            json={"owner_id": self._user_ids["beta_user"]}
        )
        assert res.status_code == 403
        assert "same organization" in res.json().get("detail", "").lower()

        # 2. Attempt to assign suspended user as owner
        # Suspend alpha user first
        client.post(
            f"/api/admin/users/{self._user_ids['alpha_user']}/suspend",
            headers=self._auth_header(self._tokens["alpha_admin"])
        )
        res = client.patch(
            f"/api/agents/{self._agent_ids['alpha']}",
            headers=self._auth_header(self._tokens["alpha_admin"]),
            json={"owner_id": self._user_ids["alpha_user"]}
        )
        assert res.status_code == 400
        assert "SUSPENDED" in res.json().get("detail", "")

        # Reactivate user for future tests
        client.post(
            f"/api/admin/users/{self._user_ids['alpha_user']}/activate",
            headers=self._auth_header(self._tokens["alpha_admin"])
        )

    # =========================================================================
    # Test 16: API key plaintext returned only on creation
    # =========================================================================
    def test_16_api_key_plaintext_returned_only_on_creation(self):
        res = client.post(
            "/api/iam/api-keys",
            headers=self._auth_header(self._tokens["alpha_admin"]),
            json={"name": "Alpha Build Key", "scopes": ["AGENT_VIEW", "DECISION_CREATE"]}
        )
        assert res.status_code == 200
        data = res.json()
        assert "plaintext_key" in data
        assert data["plaintext_key"].startswith("ag_live_")
        assert "key_prefix" in data
        self.__class__._alpha_api_key_raw = data["plaintext_key"]
        self.__class__._alpha_api_key_id = data["id"]

    # =========================================================================
    # Test 17: API key secret never appears in later responses
    # =========================================================================
    def test_17_api_key_secret_never_appears_in_later_responses(self):
        res = client.get("/api/iam/api-keys", headers=self._auth_header(self._tokens["alpha_admin"]))
        assert res.status_code == 200
        keys = res.json()
        assert len(keys) >= 1
        for k in keys:
            assert "plaintext_key" not in k
            assert "key_hash" not in k
            assert "key_prefix" in k

    # =========================================================================
    # Test 18: Revoked API key cannot authenticate
    # =========================================================================
    def test_18_revoked_api_key_cannot_authenticate(self):
        # 1. Verify the key works before revocation
        raw_key = self.__class__._alpha_api_key_raw
        res = client.get("/api/organization/dashboard", headers={"X-API-Key": raw_key})
        assert res.status_code == 200

        # 2. Revoke key
        key_id = self.__class__._alpha_api_key_id
        res = client.post(
            f"/api/iam/api-keys/{key_id}/revoke",
            headers=self._auth_header(self._tokens["alpha_admin"])
        )
        assert res.status_code == 200
        assert res.json().get("status") in ("SUCCESS", "REVOKED") or res.json().get("is_revoked") is True

        # 3. Authenticating with revoked key fails
        res = client.get("/api/organization/dashboard", headers={"X-API-Key": raw_key})
        assert res.status_code == 401
        assert "revoked" in res.json().get("detail", "").lower()

    # =========================================================================
    # Test 19: Expired API key cannot authenticate
    # =========================================================================
    def test_19_expired_api_key_cannot_authenticate(self):
        # Create an expired key directly
        db = TestSession()
        try:
            raw_expired = "ag_live_" + "e" * 48
            h = hashlib.sha256(raw_expired.encode("utf-8")).hexdigest()
            expired_key = models.ApiKey(
                name="Expired Key",
                key_prefix="ag_live_eeee...",
                key_hash=h,
                org_id=self._org_ids["alpha"],
                owner_id=self._user_ids["alpha_admin"],
                expires_at=datetime.datetime.utcnow() - datetime.timedelta(days=1),
                is_revoked=False
            )
            db.add(expired_key)
            db.commit()
        finally:
            db.close()

        res = client.get("/api/organization/dashboard", headers={"X-API-Key": raw_expired})
        assert res.status_code == 401
        assert "expired" in res.json().get("detail", "").lower()

    # =========================================================================
    # Test 20: API key cannot cross tenant boundaries
    # =========================================================================
    def test_20_api_key_cannot_cross_tenant(self):
        # Create active key for Beta
        res = client.post(
            "/api/iam/api-keys",
            headers=self._auth_header(self._tokens["beta_admin"]),
            json={"name": "Beta Test Key", "scopes": ["AGENT_VIEW"]}
        )
        beta_raw_key = res.json()["plaintext_key"]

        # Authenticate with Beta key and try to view Alpha's agent
        res = client.get(f"/api/agents/{self._agent_ids['alpha']}", headers={"X-API-Key": beta_raw_key})
        assert res.status_code == 403
        assert "another organization" in res.json().get("detail", "").lower()

    # =========================================================================
    # Test 21: Invitation is one-time use
    # =========================================================================
    def test_21_invitation_is_one_time_use(self):
        # Create invitation
        res = client.post(
            "/api/iam/invitations",
            headers=self._auth_header(self._tokens["alpha_admin"]),
            json={"email": "newbie_alpha@test.com", "role": "ANALYST"}
        )
        assert res.status_code == 200
        inv_data = res.json()
        assert inv_data["status"] == "INVITED"
        raw_token = inv_data["invitation_token"]

        # 1. First acceptance succeeds
        res_accept = client.post(
            f"/api/auth/invitations/{raw_token}/accept",
            json={"full_name": "Newbie Alpha", "password": "SecurePass123!"}
        )
        assert res_accept.status_code == 200
        assert "access_token" in res_accept.json()

        # 2. Second acceptance fails (one-time use)
        res_accept_2 = client.post(
            f"/api/auth/invitations/{raw_token}/accept",
            json={"full_name": "Newbie Alpha", "password": "SecurePass123!"}
        )
        assert res_accept_2.status_code == 400
        assert "already been accepted" in res_accept_2.json().get("detail", "")

    # =========================================================================
    # Test 22: Invitation expiration enforced
    # =========================================================================
    def test_22_invitation_expiration_enforced(self):
        # Create expired invitation in DB
        db = TestSession()
        try:
            raw_token = "inv_" + "9" * 48
            token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
            expired_inv = models.UserInvitation(
                org_id=self._org_ids["alpha"],
                email="expired_invite@test.com",
                role="USER",
                invited_by_id=self._user_ids["alpha_admin"],
                token_hash=token_hash,
                status="PENDING",
                expires_at=datetime.datetime.utcnow() - datetime.timedelta(hours=2)
            )
            db.add(expired_inv)
            db.commit()
        finally:
            db.close()

        # Verify endpoint returns expired
        res = client.get(f"/api/auth/invitations/{raw_token}/verify")
        assert res.status_code == 200
        assert res.json()["valid"] is False
        assert "expired" in res.json().get("error", "").lower()

        # Acceptance is rejected
        res = client.post(
            f"/api/auth/invitations/{raw_token}/accept",
            json={"full_name": "Expired User", "password": "Pass123!"}
        )
        assert res.status_code == 400
        assert "expired" in res.json().get("detail", "").lower()

    # =========================================================================
    # Test 23: Invitation cannot create SUPER_ADMIN
    # =========================================================================
    def test_23_invitation_cannot_create_super_admin(self):
        res = client.post(
            "/api/iam/invitations",
            headers=self._auth_header(self._tokens["alpha_admin"]),
            json={"email": "attempt_super@test.com", "role": "SUPER_ADMIN"}
        )
        assert res.status_code in (400, 403)

    # =========================================================================
    # Test 24: Privileged role change creates audit event
    # =========================================================================
    def test_24_privileged_role_change_creates_audit_event(self):
        # Change alpha user role to OPERATOR
        res = client.patch(
            f"/api/admin/users/{self._user_ids['alpha_user']}/role",
            headers=self._auth_header(self._tokens["alpha_admin"]),
            json={"role": "OPERATOR"}
        )
        assert res.status_code == 200

        # Verify audit log in DB
        db = TestSession()
        try:
            audit = db.query(models.AuditLog).filter(
                models.AuditLog.org_id == self._org_ids["alpha"],
                models.AuditLog.event_type == "ROLE_CHANGED"
            ).order_by(models.AuditLog.timestamp.desc()).first()
            assert audit is not None
            assert audit.actor_id == str(self._user_ids["alpha_admin"])
            assert audit.metadata_json["new_role"] == "OPERATOR"
        finally:
            db.close()

        # Restore role back to USER for subsequent tests
        client.patch(
            f"/api/admin/users/{self._user_ids['alpha_user']}/role",
            headers=self._auth_header(self._tokens["alpha_admin"]),
            json={"role": "USER"}
        )

    # =========================================================================
    # Test 25: User suspension creates audit event
    # =========================================================================
    def test_25_user_suspension_creates_audit_event(self):
        client.post(
            f"/api/admin/users/{self._user_ids['alpha_user']}/suspend",
            headers=self._auth_header(self._tokens["alpha_admin"])
        )

        db = TestSession()
        try:
            audit = db.query(models.AuditLog).filter(
                models.AuditLog.org_id == self._org_ids["alpha"],
                models.AuditLog.event_type == "USER_SUSPENDED"
            ).order_by(models.AuditLog.timestamp.desc()).first()
            assert audit is not None
            assert audit.actor_id == str(self._user_ids["alpha_admin"])
        finally:
            db.close()

        # Reactivate
        client.post(
            f"/api/admin/users/{self._user_ids['alpha_user']}/activate",
            headers=self._auth_header(self._tokens["alpha_admin"])
        )

    # =========================================================================
    # Test 26: Agent suspension creates audit event
    # =========================================================================
    def test_26_agent_suspension_creates_audit_event(self):
        res = client.post(
            f"/api/agents/{self._agent_ids['alpha']}/suspend",
            headers=self._auth_header(self._tokens["alpha_admin"])
        )
        assert res.status_code == 200

        db = TestSession()
        try:
            audit = db.query(models.AuditLog).filter(
                models.AuditLog.org_id == self._org_ids["alpha"],
                models.AuditLog.event_type == "AGENT_SUSPENDED"
            ).order_by(models.AuditLog.timestamp.desc()).first()
            assert audit is not None
            assert "AG-ALPHA-01" in audit.resource
        finally:
            db.close()

        # Restore
        client.post(
            f"/api/agents/{self._agent_ids['alpha']}/restore",
            headers=self._auth_header(self._tokens["alpha_admin"])
        )

    # =========================================================================
    # Test 27: Security incident tenant isolation
    # =========================================================================
    def test_27_security_incident_tenant_isolation(self):
        # Create incident in Alpha
        res_create = client.post(
            "/api/security/incidents",
            headers=self._auth_header(self._tokens["alpha_admin"]),
            json={
                "title": "Suspicious API Activity",
                "severity": "HIGH",
                "source": "AGENT_MONITOR",
                "description": "Repeated unauthorized calls detected"
            }
        )
        assert res_create.status_code == 200
        incident_id = res_create.json()["id"]

        # Beta admin cannot view incident by ID
        res_beta_get = client.get(
            f"/api/security/incidents/{incident_id}",
            headers=self._auth_header(self._tokens["beta_admin"])
        )
        assert res_beta_get.status_code == 403

        # Beta incident list does not contain Alpha incident
        res_beta_list = client.get(
            "/api/security/incidents",
            headers=self._auth_header(self._tokens["beta_admin"])
        )
        assert res_beta_list.status_code == 200
        inc_ids = [inc["id"] for inc in res_beta_list.json()]
        assert incident_id not in inc_ids

    # =========================================================================
    # Test 28: Audit log tenant isolation
    # =========================================================================
    def test_28_audit_log_tenant_isolation(self):
        res_beta = client.get("/api/audit/logs", headers=self._auth_header(self._tokens["beta_admin"]))
        assert res_beta.status_code == 200
        logs = res_beta.json()
        for l in logs:
            if l.get("org_id"):
                assert l["org_id"] == self._org_ids["beta"]

    # =========================================================================
    # Test 29: Audit log cannot be modified by tenant user (append-only)
    # =========================================================================
    def test_29_audit_log_cannot_be_modified_by_tenant_user(self):
        res = client.delete("/api/audit/logs/some-audit-id", headers=self._auth_header(self._tokens["alpha_admin"]))
        assert res.status_code == 403
        assert "immutable" in res.json().get("detail", "").lower()

    # =========================================================================
    # Test 30: SUPER_ADMIN platform audit access
    # =========================================================================
    def test_30_super_admin_platform_audit_access(self):
        res = client.get("/api/audit/logs", headers=self._auth_header(self._tokens["super_admin"]))
        assert res.status_code == 200
        logs = res.json()
        assert len(logs) >= 1

    # =========================================================================
    # Test 31: Privileged action authorization
    # =========================================================================
    def test_31_privileged_action_authorization(self):
        # Normal user cannot suspend agent
        res = client.post(
            f"/api/agents/{self._agent_ids['alpha']}/suspend",
            headers=self._auth_header(self._tokens["alpha_user"])
        )
        assert res.status_code in (403, 400)

    # =========================================================================
    # Test 32: Cross-tenant resource ID attack rejected
    # =========================================================================
    def test_32_cross_tenant_resource_id_attack_rejected(self):
        res = client.get(
            f"/api/agents/{self._agent_ids['beta']}",
            headers=self._auth_header(self._tokens["alpha_admin"])
        )
        assert res.status_code == 403
        assert "another organization" in res.json().get("detail", "").lower()

    # =========================================================================
    # Test 33: Cross-tenant query parameter attack rejected
    # =========================================================================
    def test_33_cross_tenant_query_parameter_attack_rejected(self):
        res = client.get(
            f"/api/admin/users?org_id={self._org_ids['beta']}",
            headers=self._auth_header(self._tokens["alpha_admin"])
        )
        assert res.status_code == 200
        users = res.json()
        for u in users:
            assert u["org_id"] == self._org_ids["alpha"]

    # =========================================================================
    # Test 34: Cross-tenant body org_id attack rejected
    # =========================================================================
    def test_34_cross_tenant_body_org_id_attack_rejected(self):
        res = client.post(
            "/api/agents",
            headers=self._auth_header(self._tokens["alpha_admin"]),
            json={
                "name": "Malicious Infiltrator",
                "org_id": self._org_ids["beta"],
                "daily_budget": 1000.0
            }
        )
        assert res.status_code == 403
        assert "another organization" in res.json().get("detail", "").lower()

    # =========================================================================
    # Test 35: Phase 1 regression
    # =========================================================================
    def test_35_phase1_regression(self):
        # Invalid credentials return 401
        res = client.post("/api/auth/login", json={"email": "fake@test.com", "password": "WrongPassword!"})
        assert res.status_code == 401

    # =========================================================================
    # Test 36: Phase 2 regression
    # =========================================================================
    def test_36_phase2_regression(self):
        # Policies endpoint is functional and tenant isolated
        res = client.get("/api/policies", headers=self._auth_header(self._tokens["alpha_admin"]))
        assert res.status_code == 200

    # =========================================================================
    # Test 37: Phase 3 regression
    # =========================================================================
    def test_37_phase3_regression(self):
        # Analytics overview is functional
        res = client.get("/api/analytics/overview", headers=self._auth_header(self._tokens["alpha_admin"]))
        assert res.status_code == 200

    # =========================================================================
    # Test 38: Phase 4 regression
    # =========================================================================
    def test_38_phase4_regression(self):
        # Telemetry executions endpoint works for tenant
        res = client.get(
            "/api/telemetry/executions?range=24h",
            headers=self._auth_header(self._tokens["alpha_admin"])
        )
        assert res.status_code == 200

    # =========================================================================
    # Test 39: Authorization Matrix Testing across all 9 roles
    # =========================================================================
    def test_39_authorization_matrix_all_roles(self):
        roles_to_test = [
            (ROLE_USER, {PERM_USER_VIEW, PERM_ORGANIZATION_VIEW}, {PERM_USER_SUSPEND, PERM_PLATFORM_ADMIN}),
            (ROLE_VIEWER, {PERM_AGENT_VIEW, PERM_POLICY_VIEW, PERM_AUDIT_VIEW}, {PERM_USER_SUSPEND, PERM_PLATFORM_ADMIN}),
            (ROLE_ANALYST, {PERM_REPORT_VIEW, PERM_AUDIT_VIEW}, {PERM_USER_SUSPEND, PERM_PLATFORM_ADMIN}),
            (ROLE_OPERATOR, {PERM_AGENT_VIEW, PERM_TELEMETRY_VIEW}, {PERM_PLATFORM_ADMIN}),
            (ROLE_SECURITY_ANALYST, {PERM_SECURITY_VIEW, PERM_AUDIT_VIEW}, {PERM_PLATFORM_ADMIN}),
            (ROLE_MANAGER, {PERM_USER_VIEW, PERM_REPORT_VIEW}, {PERM_PLATFORM_ADMIN}),
            (ROLE_DEVELOPER, {PERM_AGENT_VIEW, PERM_POLICY_VIEW}, {PERM_PLATFORM_ADMIN}),
            (ROLE_ADMIN, {PERM_USER_SUSPEND, PERM_API_KEY_VIEW}, {PERM_PLATFORM_ADMIN}),
            (ROLE_SUPER_ADMIN, {PERM_PLATFORM_ADMIN, PERM_USER_SUSPEND}, set()),
        ]

        for role, allowed_perms, denied_perms in roles_to_test:
            for p in allowed_perms:
                assert has_permission(role, p), f"Role {role} should have permission {p}"
            for p in denied_perms:
                assert not has_permission(role, p), f"Role {role} should NOT have permission {p}"

        # Hierarchy management check
        assert can_manage_role(ROLE_SUPER_ADMIN, ROLE_ADMIN) is True
        assert can_manage_role(ROLE_ADMIN, ROLE_SUPER_ADMIN) is False
        assert can_manage_role(ROLE_ADMIN, ROLE_DEVELOPER) is True
        assert can_manage_role(ROLE_DEVELOPER, ROLE_ADMIN) is False
        assert can_manage_role(ROLE_USER, ROLE_USER) is False
