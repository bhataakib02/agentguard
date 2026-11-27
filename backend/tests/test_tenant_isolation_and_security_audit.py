import os
import sys
import uuid
import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test_secret_key_security_audit_32_bytes_long"
os.environ["AUTO_BOOTSTRAP_DB"] = "false"

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from main import app
from database import get_db, Base
import models
from core import security

# In-memory SQLite for isolated security test execution
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_security_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    prev_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    if prev_override is not None:
        app.dependency_overrides[get_db] = prev_override
    else:
        app.dependency_overrides.pop(get_db, None)

def create_tenant_fixtures(db):
    """Creates two distinct organizations, users, and agents for cross-tenant testing."""
    suffix = uuid.uuid4().hex[:6]
    # Org 1
    org1 = models.Organization(
        id=str(uuid.uuid4()),
        name="Tenant Alpha Corp",
        slug=f"alpha-corp-{suffix}",
        domain=f"alpha-{suffix}.example.com",
        status="ACTIVE"
    )
    db.add(org1)

    # Org 2
    org2 = models.Organization(
        id=str(uuid.uuid4()),
        name="Tenant Beta Ltd",
        slug=f"beta-ltd-{suffix}",
        domain=f"beta-{suffix}.example.com",
        status="ACTIVE"
    )
    db.add(org2)
    db.commit()

    # User 1 (Admin in Org 1)
    user1 = models.User(
        id=str(uuid.uuid4()),
        org_id=org1.id,
        email=f"admin-{suffix}@alpha.example.com",
        full_name="Alpha Admin",
        role="ADMIN",
        status="ACTIVE",
        password_hash=security.get_password_hash("AlphaPass123!")
    )
    db.add(user1)

    # User 2 (Manager in Org 2)
    user2 = models.User(
        id=str(uuid.uuid4()),
        org_id=org2.id,
        email=f"manager-{suffix}@beta.example.com",
        full_name="Beta Manager",
        role="MANAGER",
        status="ACTIVE",
        password_hash=security.get_password_hash("BetaPass123!")
    )
    db.add(user2)

    # Super Admin (Global Platform Scope)
    super_admin = models.User(
        id=str(uuid.uuid4()),
        org_id=org1.id,
        email=f"superadmin-{suffix}@agentguard.internal",
        full_name="Global Super Admin",
        role="SUPER_ADMIN",
        status="ACTIVE",
        password_hash=security.get_password_hash("SuperSecurePass123!")
    )
    db.add(super_admin)
    db.commit()

    # Agent in Org 1
    agent1 = models.Agent(
        id=str(uuid.uuid4()),
        agent_code=f"AGT-ALPHA-{suffix}",
        org_id=org1.id,
        owner_id=user1.id,
        name="Alpha Financial Agent",
        purpose="Automated bookkeeping and invoice approval",
        status="NORMAL"
    )
    db.add(agent1)

    # Agent in Org 2
    agent2 = models.Agent(
        id=str(uuid.uuid4()),
        agent_code=f"AGT-BETA-{suffix}",
        org_id=org2.id,
        owner_id=user2.id,
        name="Beta Operations Agent",
        purpose="Support desk automation",
        status="NORMAL"
    )
    db.add(agent2)
    db.commit()

    return {
        "org1": org1,
        "org2": org2,
        "user1": user1,
        "user2": user2,
        "super_admin": super_admin,
        "agent1": agent1,
        "agent2": agent2,
        "token_user1": security.create_access_token(str(user1.id), email=user1.email, role=user1.role),
        "token_user2": security.create_access_token(str(user2.id), email=user2.email, role=user2.role),
        "token_super": security.create_access_token(str(super_admin.id), email=super_admin.email, role=super_admin.role)
    }


class TestTenantIsolationAndSecurity:
    """Rigorous tenant isolation, authorization, and fail-closed security tests."""

    def test_01_decision_detail_fail_closed_on_cross_tenant_access(self, client, db_session):
        fx = create_tenant_fixtures(db_session)
        # Create decision for Agent 1 (Org 1)
        dec = models.Decision(
            id=str(uuid.uuid4()),
            agent_id=fx["agent1"].id,
            user_id=fx["user1"].id,
            intent_summary="Transfer $50,000 to vendor",
            action_requested="WIRE_TRANSFER",
            resource_target="bank_api",
            amount=50000.0,
            decision="REVIEW",
            risk_score=75,
            explanation="Requires multi-sig human approval"
        )
        db_session.add(dec)
        db_session.commit()

        # User 1 (Org 1) can view the decision
        resp1 = client.get(
            f"/api/decisions/{dec.id}",
            headers={"Authorization": f"Bearer {fx['token_user1']}"}
        )
        assert resp1.status_code == 200

        # User 2 (Org 2) is forbidden from viewing Org 1's decision
        resp2 = client.get(
            f"/api/decisions/{dec.id}",
            headers={"Authorization": f"Bearer {fx['token_user2']}"}
        )
        assert resp2.status_code == 403
        assert "another organization" in resp2.json()["detail"].lower()

    def test_02_decision_detail_fail_closed_when_agent_missing(self, client, db_session):
        fx = create_tenant_fixtures(db_session)
        # Decision with non-existent agent_id (orphaned)
        fake_agent_id = str(uuid.uuid4())
        dec = models.Decision(
            id=str(uuid.uuid4()),
            agent_id=fake_agent_id,
            intent_summary="Orphaned action",
            action_requested="SYSTEM_EXEC",
            resource_target="terminal",
            decision="ALLOW",
            explanation="Orphaned record"
        )
        db_session.add(dec)
        db_session.commit()

        # Non-super admin is rejected (fail-closed)
        resp = client.get(
            f"/api/decisions/{dec.id}",
            headers={"Authorization": f"Bearer {fx['token_user1']}"}
        )
        assert resp.status_code == 403
        assert "another organization" in resp.json()["detail"].lower()

    def test_03_approval_action_fail_closed_on_cross_tenant_access(self, client, db_session):
        fx = create_tenant_fixtures(db_session)
        # Create decision and approval request for Agent 1 (Org 1)
        dec = models.Decision(
            id=str(uuid.uuid4()),
            agent_id=fx["agent1"].id,
            intent_summary="Execute payroll",
            action_requested="PAYROLL_SUBMIT",
            resource_target="adp_api",
            decision="REVIEW",
            explanation="Requires review"
        )
        db_session.add(dec)
        app_req = models.ApprovalRequest(
            id=str(uuid.uuid4()),
            decision_id=dec.id,
            agent_id=fx["agent1"].id,
            reason="High value payroll execution",
            status="PENDING"
        )
        db_session.add(app_req)
        db_session.commit()

        # User 2 (Manager in Org 2) attempts to approve Org 1's request -> 403 Forbidden
        resp = client.post(
            f"/api/approvals/{app_req.id}/act",
            headers={"Authorization": f"Bearer {fx['token_user2']}"},
            json={"action": "APPROVE", "reason": "Unauthorized cross-tenant attempt"}
        )
        assert resp.status_code == 403
        assert "another organization" in resp.json()["detail"].lower()

    def test_04_session_revocation_fail_closed_on_cross_tenant(self, client, db_session):
        fx = create_tenant_fixtures(db_session)
        # Session belonging to User 2 (Org 2)
        sess = models.Session(
            id=str(uuid.uuid4()),
            user_id=fx["user2"].id,
            token="test_token_sess_user2",
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            revoked=False
        )
        db_session.add(sess)
        db_session.commit()

        # Admin of Org 1 attempts to revoke session of User 2 (Org 2)
        resp = client.delete(
            f"/api/iam/sessions/{sess.id}",
            headers={"Authorization": f"Bearer {fx['token_user1']}"}
        )
        assert resp.status_code == 403
        assert "another organization" in resp.json()["detail"].lower()

    def test_05_notification_read_fail_closed_on_other_users(self, client, db_session):
        fx = create_tenant_fixtures(db_session)
        # Notification for User 2
        notif = models.Notification(
            id=str(uuid.uuid4()),
            user_id=fx["user2"].id,
            title="Confidential Security Warning",
            message="Suspicious access attempt detected",
            is_read=False
        )
        db_session.add(notif)
        db_session.commit()

        # User 1 attempts to mark User 2's notification as read
        resp = client.patch(
            f"/api/notifications/{notif.id}/read",
            headers={"Authorization": f"Bearer {fx['token_user1']}"}
        )
        assert resp.status_code == 403

    def test_06_capability_validate_requires_auth_and_blocks_cross_tenant(self, client, db_session):
        fx = create_tenant_fixtures(db_session)
        # Create capability token for Agent 2 (Org 2)
        cap = models.CapabilityToken(
            id=str(uuid.uuid4()),
            token_code="tok_beta_secret_cap_123",
            agent_id=fx["agent2"].id,
            capability_name="database:drop_table",
            scope="production.db",
            amount_limit=0.0,
            status="ACTIVE",
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        )
        db_session.add(cap)
        db_session.commit()

        # 1. Unauthenticated request -> 401 Unauthorized
        resp_unauth = client.post(
            "/api/capabilities/validate",
            json={"token_code": "tok_beta_secret_cap_123"}
        )
        assert resp_unauth.status_code == 401

        # 2. User 1 (Org 1) attempts to validate Agent 2's token -> 403 Forbidden
        resp_cross = client.post(
            "/api/capabilities/validate",
            headers={"Authorization": f"Bearer {fx['token_user1']}"},
            json={"token_code": "tok_beta_secret_cap_123"}
        )
        assert resp_cross.status_code == 403
        assert "another organization" in resp_cross.json()["detail"].lower()

    def test_07_runtime_scan_pii_requires_auth(self, client):
        # Unauthenticated request to /runtime/scan-pii -> 401 Unauthorized
        resp = client.post(
            "/api/runtime/scan-pii",
            json={"text": "My phone is 555-1234 and SSN is 000-12-3456"}
        )
        assert resp.status_code == 401

    def test_08_immutable_audit_logs_reject_modification(self, client, db_session):
        fx = create_tenant_fixtures(db_session)
        # Attempting to delete an audit log must return 403 Forbidden
        resp = client.delete(
            f"/api/audit/logs/{str(uuid.uuid4())}",
            headers={"Authorization": f"Bearer {fx['token_super']}"}
        )
        assert resp.status_code == 403
        assert "immutable" in resp.json()["detail"].lower()

    def test_09_capability_revoke_fail_closed_on_cross_tenant_and_orphaned(self, client, db_session):
        fx = create_tenant_fixtures(db_session)
        # Token for Agent 2 (Org 2)
        tok_beta = models.CapabilityToken(
            id=str(uuid.uuid4()),
            token_code=f"tok_beta_revoke_{uuid.uuid4().hex[:8]}",
            agent_id=fx["agent2"].id,
            capability_name="db:drop",
            scope="prod",
            amount_limit=0.0,
            status="ACTIVE",
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        )
        # Orphaned token (agent does not exist)
        tok_orphan = models.CapabilityToken(
            id=str(uuid.uuid4()),
            token_code=f"tok_orphan_{uuid.uuid4().hex[:8]}",
            agent_id=str(uuid.uuid4()),
            capability_name="system:root",
            scope="all",
            amount_limit=0.0,
            status="ACTIVE",
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        )
        db_session.add_all([tok_beta, tok_orphan])
        db_session.commit()

        # 1. User 1 (Admin Org 1) attempts to revoke Org 2 token -> 403
        resp1 = client.post(
            f"/api/capabilities/revoke/{tok_beta.token_code}",
            headers={"Authorization": f"Bearer {fx['token_user1']}"}
        )
        assert resp1.status_code == 403
        assert "another organization" in resp1.json()["detail"].lower()

        # 2. User 1 attempts to revoke orphaned token -> 403 (fail-closed)
        resp2 = client.post(
            f"/api/capabilities/revoke/{tok_orphan.token_code}",
            headers={"Authorization": f"Bearer {fx['token_user1']}"}
        )
        assert resp2.status_code == 403
        assert "another organization" in resp2.json()["detail"].lower()

        # 3. Super admin can revoke cross-org or orphaned token -> 200
        resp3 = client.post(
            f"/api/capabilities/revoke/{tok_beta.token_code}",
            headers={"Authorization": f"Bearer {fx['token_super']}"}
        )
        assert resp3.status_code == 200
        assert resp3.json()["status"] == "SUCCESS"

    def test_10_super_admin_cross_tenant_access_allowed(self, client, db_session):
        fx = create_tenant_fixtures(db_session)
        dec = models.Decision(
            id=str(uuid.uuid4()),
            agent_id=fx["agent1"].id,
            user_id=fx["user1"].id,
            intent_summary="Super admin audit verification",
            action_requested="SYSTEM_AUDIT",
            resource_target="audit_system",
            decision="ALLOW",
            explanation="Normal operation"
        )
        db_session.add(dec)
        db_session.commit()

        # SUPER_ADMIN can view decision from any org
        resp = client.get(
            f"/api/decisions/{dec.id}",
            headers={"Authorization": f"Bearer {fx['token_super']}"}
        )
        assert resp.status_code == 200
        assert resp.json()["decision"]["id"] == str(dec.id)

    def test_11_simulation_fail_closed_on_cross_tenant(self, client, db_session):
        fx = create_tenant_fixtures(db_session)
        # Attempt to access non-existent / cross-tenant simulation run
        fake_run_id = f"sim_run_{uuid.uuid4().hex[:12]}"
        resp = client.get(
            f"/api/simulation/runs/{fake_run_id}",
            headers={"Authorization": f"Bearer {fx['token_user1']}"}
        )
        # Should return 404 (not found or cross-tenant)
        assert resp.status_code == 404
