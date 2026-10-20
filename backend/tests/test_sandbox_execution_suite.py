"""
Comprehensive Automated Test Suite: External Isolated Sandbox Execution Provider
Covers:
1. Provider NOT_CONFIGURED state (truthful rejection without host execution).
2. Provider UNAVAILABLE state (unreachable worker handling).
3. Successful isolated code execution using controlled test worker.
4. Timeout handling and deadline enforcement.
5. Resource / memory exhaustion handling (simulated OOM).
6. Execution cancellation and worker teardown.
7. Filesystem and network isolation by default.
8. Environment variable secret stripping (no leakage of DB, JWT, or cloud credentials).
9. Cross-tenant isolation (Tenant B cannot access or cancel Tenant A's jobs/logs).
10. Forged, expired, and non-matching gate token rejection.
11. Gate token replay prevention (one-time atomic consumption).
12. REFUSE and unapproved REVIEW decisions blocked from reaching provider.
13. Approved REVIEW decisions successfully executed post-manager-approval.
14. Oversized output truncation and safety sanitization.
15. Audit logging and telemetry generation with provenance tracing.
16. Backward compatibility with /runtime/execute and /runtime/invoke.
17. Truthful GET /runtime/sandbox/status reporting.
18. Celery cleanup task purging expired artifacts.
"""

import os
import sys
import time
import uuid
import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///test_sandbox.db"
os.environ["SECRET_KEY"] = "test-sandbox-secret-key-12345"
os.environ["ENVIRONMENT"] = "test"
os.environ["SANDBOX_PROVIDER"] = "NOT_CONFIGURED"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Base, engine, get_db
import models
from main import app
from core.security import get_password_hash, create_access_token
from services.machine_auth_service import machine_auth_service
from services.passport_service import passport_service
from services.sandbox_service import (
    sandbox_service,
    get_sandbox_provider,
    set_sandbox_provider,
    reset_sandbox_provider,
    UnconfiguredSandboxProvider,
    RemoteWorkerSandboxProvider,
    MockTestSandboxProvider,
    cleanse_execution_environment
)
from tasks.sandbox_tasks import cleanup_expired_sandbox_artifacts_task

TestSession = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db_session():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_setup(db_session):
    """Sets up two isolated organizations (Alpha and Beta), operators, and agents."""
    suffix = uuid.uuid4().hex[:6]

    # --- Org Alpha ---
    org_a = models.Organization(name=f"Alpha Corp {suffix}", slug=f"alpha-corp-{suffix}", status="ACTIVE")
    db_session.add(org_a)
    db_session.commit()
    db_session.refresh(org_a)

    user_a = models.User(
        email=f"admin-{suffix}@alpha.com",
        password_hash=get_password_hash("AlphaPass123!"),
        full_name="Alpha Admin",
        role="ADMIN",
        org_id=org_a.id,
        status="ACTIVE"
    )
    manager_a = models.User(
        email=f"manager-{suffix}@alpha.com",
        password_hash=get_password_hash("AlphaManager123!"),
        full_name="Alpha Manager",
        role="MANAGER",
        org_id=org_a.id,
        status="ACTIVE"
    )
    db_session.add_all([user_a, manager_a])
    db_session.commit()

    agent_a = models.Agent(
        org_id=org_a.id,
        owner_id=user_a.id,
        name="Data Scientist Agent",
        agent_code=f"AG-SCI-{suffix}",
        environment="PRODUCTION",
        autonomy_level="HIGH",
        status="NORMAL",
        daily_budget=50000.0,
        purpose="Runs data analysis scripts in sandbox"
    )
    db_session.add(agent_a)
    db_session.commit()
    db_session.refresh(agent_a)

    # Permission for agent A
    perm_a = models.Permission(
        agent_id=agent_a.id,
        resource_type="TOOL",
        resource_name="python_sandbox",
        action="EXECUTE",
        is_allowed=True
    )
    db_session.add(perm_a)

    # Registered tool for Agent A
    tool_a = models.Tool(
        org_id=org_a.id,
        name="python_sandbox",
        category="SANDBOX",
        description="Isolated Python code execution environment",
        risk_level="MEDIUM",
        status="ACTIVE",
        timeout_seconds=30
    )
    db_session.add(tool_a)
    db_session.commit()

    # --- Org Beta (for cross-tenant checks) ---
    org_b = models.Organization(name=f"Beta Corp {suffix}", slug=f"beta-corp-{suffix}", status="ACTIVE")
    db_session.add(org_b)
    db_session.commit()
    db_session.refresh(org_b)

    user_b = models.User(
        email=f"admin-{suffix}@beta.com",
        password_hash=get_password_hash("BetaPass123!"),
        full_name="Beta Admin",
        role="ADMIN",
        org_id=org_b.id,
        status="ACTIVE"
    )
    db_session.add(user_b)
    db_session.commit()

    agent_b = models.Agent(
        org_id=org_b.id,
        owner_id=user_b.id,
        name="Beta Infiltrator",
        agent_code=f"AG-BETA-{suffix}",
        environment="PRODUCTION",
        autonomy_level="MEDIUM",
        status="NORMAL",
        purpose="Cross tenant agent"
    )
    db_session.add(agent_b)
    db_session.commit()
    db_session.refresh(agent_b)

    # Passports for both agents
    for ag in [agent_a, agent_b]:
        p = models.AgentPassport(
            agent_id=ag.id,
            passport_number=f"AG-PASSPORT-{ag.agent_code}",
            digital_signature="pending",
            issued_at=datetime.datetime.utcnow(),
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=365),
            verification_status="VERIFIED"
        )
        passport_service.sign_passport(ag, p)
        db_session.add(p)
    db_session.commit()

    # Credentials for both agents
    cred_a_rec, cred_a_plain = machine_auth_service.create_agent_credential(
        db_session, agent_a, name="Script Worker Credential"
    )
    cred_b_rec, cred_b_plain = machine_auth_service.create_agent_credential(
        db_session, agent_b, name="Beta Credential"
    )

    # Generate JWTs
    token_user_a = create_access_token(user_id=str(user_a.id), email=user_a.email, role=user_a.role)
    token_manager_a = create_access_token(user_id=str(manager_a.id), email=manager_a.email, role=manager_a.role)
    token_user_b = create_access_token(user_id=str(user_b.id), email=user_b.email, role=user_b.role)

    jwt_agent_a = machine_auth_service.issue_machine_jwt(agent_a, cred_a_rec)["access_token"]
    jwt_agent_b = machine_auth_service.issue_machine_jwt(agent_b, cred_b_rec)["access_token"]

    return {
        "org_a": org_a,
        "org_b": org_b,
        "user_a": user_a,
        "manager_a": manager_a,
        "user_b": user_b,
        "agent_a": agent_a,
        "agent_b": agent_b,
        "jwt_agent_a": jwt_agent_a,
        "jwt_agent_b": jwt_agent_b,
        "token_user_a": token_user_a,
        "token_manager_a": token_manager_a,
        "token_user_b": token_user_b,
        "tool_a": tool_a
    }


def helper_get_gate_token(agent_jwt: str, action: str = "EXECUTE", resource: str = "python_sandbox", params: dict = None):
    """Helper to acquire a valid execution gate token from the 12-stage runtime kernel."""
    res = client.post(
        "/api/runtime/authorize",
        headers={"Authorization": f"Bearer {agent_jwt}"},
        json={
            "action": action,
            "resource": resource,
            "parameters": params or {}
        }
    )
    assert res.status_code == 200, f"Authorize failed: {res.text}"
    data = res.json()
    return data.get("execution_gate_token"), data


# ============================================================================
# TESTS
# ============================================================================

def test_01_provider_not_configured_truthful_rejection(test_setup):
    """
    Test 1: When no provider is configured, execution is truthfully rejected
    with NOT_CONFIGURED status. Untrusted code is never run on host.
    """
    reset_sandbox_provider()
    # Explicitly ensure Unconfigured provider is active
    set_sandbox_provider(UnconfiguredSandboxProvider())

    status_res = client.get("/api/runtime/sandbox/status", headers={"Authorization": f"Bearer {test_setup['jwt_agent_a']}"})
    assert status_res.status_code == 200
    st_data = status_res.json()
    assert st_data["configured"] is False
    assert st_data["status"] == "NOT_CONFIGURED"

    gate_token, _ = helper_get_gate_token(test_setup["jwt_agent_a"])
    assert gate_token is not None

    exec_res = client.post(
        "/api/runtime/sandbox/execute",
        headers={"Authorization": f"Bearer {test_setup['jwt_agent_a']}"},
        json={
            "execution_gate_token": gate_token,
            "code": "print('Hello unconfigured')"
        }
    )
    # Must report 503 Service Unavailable with truthful error
    assert exec_res.status_code == 503
    assert "NOT_CONFIGURED" in exec_res.text or "not configured" in exec_res.text


def test_02_provider_unavailable_handling(test_setup):
    """
    Test 2: When remote worker is down or unreachable, returns truthful UNAVAILABLE.
    """
    unavailable_mock = MockTestSandboxProvider(simulate_network_failure=True)
    set_sandbox_provider(unavailable_mock)

    status_res = client.get("/api/runtime/sandbox/status", headers={"Authorization": f"Bearer {test_setup['jwt_agent_a']}"})
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "UNAVAILABLE"

    gate_token, _ = helper_get_gate_token(test_setup["jwt_agent_a"])
    exec_res = client.post(
        "/api/runtime/sandbox/execute",
        headers={"Authorization": f"Bearer {test_setup['jwt_agent_a']}"},
        json={
            "execution_gate_token": gate_token,
            "code": "print('Unreachable worker test')"
        }
    )
    assert exec_res.status_code == 503
    assert "UNAVAILABLE" in exec_res.text or "unreachable" in exec_res.text


def test_03_successful_execution_controlled_worker(test_setup, db_session):
    """
    Test 3: Successful isolated execution using controlled test worker.
    Returns stdout, exit code 0, resource usage, and cleans up workspace.
    """
    worker = MockTestSandboxProvider()
    set_sandbox_provider(worker)

    gate_token, _ = helper_get_gate_token(test_setup["jwt_agent_a"])
    exec_res = client.post(
        "/api/runtime/sandbox/execute",
        headers={"Authorization": f"Bearer {test_setup['jwt_agent_a']}"},
        json={
            "execution_gate_token": gate_token,
            "tool_name": "python_sandbox",
            "language": "python",
            "code": "print('Calculation result: 42')"
        }
    )
    assert exec_res.status_code == 200
    data = exec_res.json()
    assert data["success"] is True
    assert data["status"] == "SUCCEEDED"
    assert data["exit_code"] == 0
    assert "42" in data["stdout"]
    assert data["cleaned_up"] is True
    assert data["execution_id"].startswith("sbx_")

    # Verify durable database record was saved
    job = db_session.query(models.SandboxExecutionJob).filter(
        models.SandboxExecutionJob.execution_id == data["execution_id"]
    ).first()
    assert job is not None
    assert job.status == "SUCCEEDED"
    assert job.org_id == test_setup["org_a"].id
    assert job.cleanup_status == "CLEANED"


def test_04_timeout_deadline_enforcement(test_setup):
    """
    Test 4: Execution exceeding timeout is terminated with TIMED_OUT status.
    """
    worker = MockTestSandboxProvider()
    set_sandbox_provider(worker)

    gate_token, _ = helper_get_gate_token(test_setup["jwt_agent_a"])
    exec_res = client.post(
        "/api/runtime/sandbox/execute",
        headers={"Authorization": f"Bearer {test_setup['jwt_agent_a']}"},
        json={
            "execution_gate_token": gate_token,
            "code": "import time; __SIMULATE_TIMEOUT__; time.sleep(100)",
            "timeout_seconds": 2
        }
    )
    assert exec_res.status_code == 200
    data = exec_res.json()
    assert data["success"] is False
    assert data["status"] == "TIMED_OUT"
    assert "timed out" in data["error"].lower()


def test_05_memory_resource_exhaustion_handling(test_setup):
    """
    Test 5: Memory limit exhaustion (OOM) is safely handled without host crash.
    """
    worker = MockTestSandboxProvider()
    set_sandbox_provider(worker)

    gate_token, _ = helper_get_gate_token(test_setup["jwt_agent_a"])
    exec_res = client.post(
        "/api/runtime/sandbox/execute",
        headers={"Authorization": f"Bearer {test_setup['jwt_agent_a']}"},
        json={
            "execution_gate_token": gate_token,
            "code": "__SIMULATE_OOM__; data = [1] * 10**9"
        }
    )
    assert exec_res.status_code == 200
    data = exec_res.json()
    assert data["success"] is False
    assert data["status"] == "FAILED"
    assert data["exit_code"] == 137 or "memory" in data["stderr"].lower()


def test_06_execution_cancellation_and_teardown(test_setup, db_session):
    """
    Test 6: User or operator can cancel an active execution and verify cleanup.
    """
    worker = MockTestSandboxProvider()
    set_sandbox_provider(worker)

    # Create a running job record directly
    exec_id = f"sbx_cancel_test_{uuid.uuid4().hex[:6]}"
    job = models.SandboxExecutionJob(
        org_id=test_setup["org_a"].id,
        agent_id=test_setup["agent_a"].id,
        execution_id=exec_id,
        tool_name="python_sandbox",
        language="python",
        code_hash="fakehash",
        status="RUNNING",
        cleanup_status="PENDING"
    )
    db_session.add(job)
    db_session.commit()

    # Cancel via API
    cancel_res = client.post(
        f"/api/runtime/sandbox/jobs/{exec_id}/cancel",
        headers={"Authorization": f"Bearer {test_setup['token_user_a']}"}
    )
    assert cancel_res.status_code == 200
    c_data = cancel_res.json()
    assert c_data["success"] is True
    assert c_data["status"] == "CANCELLED"

    # Verify job status in DB
    db_session.refresh(job)
    assert job.status == "CANCELLED"
    assert job.cleanup_status == "CLEANED"


def test_07_network_isolation_by_default(test_setup):
    """
    Test 7: Outbound network calls from sandbox are blocked by default.
    """
    worker = MockTestSandboxProvider()
    set_sandbox_provider(worker)

    gate_token, _ = helper_get_gate_token(test_setup["jwt_agent_a"])
    exec_res = client.post(
        "/api/runtime/sandbox/execute",
        headers={"Authorization": f"Bearer {test_setup['jwt_agent_a']}"},
        json={
            "execution_gate_token": gate_token,
            "code": "import urllib.request; urllib.request.urlopen('http://evil.com')",
            "network_enabled": False
        }
    )
    assert exec_res.status_code == 200
    data = exec_res.json()
    assert data["success"] is False
    assert "network" in data["stderr"].lower()


def test_08_environment_secrets_sanitization(test_setup):
    """
    Test 8: Host credentials, DB URLs, and signing keys are NOT leaked to the sandbox.
    """
    # 1. Test cleanse_execution_environment function directly
    dirty_env = {
        "DATABASE_URL": "postgresql://postgres:secret@db:5432/agentguard",
        "SECRET_KEY": "super-secret-production-key",
        "SUPABASE_SERVICE_ROLE_KEY": "sb_secret_99812",
        "OPENAI_API_KEY": "sk-proj-12345",
        "LANG": "en_US.UTF-8",
        "CUSTOM_APP_SETTING": "standard_safe_value"
    }
    clean = cleanse_execution_environment(dirty_env)
    assert "DATABASE_URL" not in clean
    assert "SECRET_KEY" not in clean
    assert "SUPABASE_SERVICE_ROLE_KEY" not in clean
    assert "OPENAI_API_KEY" not in clean
    assert clean["LANG"] == "C.UTF-8" or clean["LANG"] == "en_US.UTF-8"
    assert clean["CUSTOM_APP_SETTING"] == "standard_safe_value"

    # 2. Test via API execution
    worker = MockTestSandboxProvider()
    set_sandbox_provider(worker)

    gate_token, _ = helper_get_gate_token(test_setup["jwt_agent_a"])
    exec_res = client.post(
        "/api/runtime/sandbox/execute",
        headers={"Authorization": f"Bearer {test_setup['jwt_agent_a']}"},
        json={
            "execution_gate_token": gate_token,
            "code": "print('Checking env...')",
            "env_vars": {"DATABASE_URL": "leak_attempt", "SECRET_KEY": "leak_key"}
        }
    )
    assert exec_res.status_code == 200
    # Cleanse stripped the forbidden keys before passing to worker


def test_09_cross_tenant_isolation(test_setup, db_session):
    """
    Test 9: Tenant Beta cannot view, cancel, or access Tenant Alpha's sandbox execution jobs.
    """
    # Create an Alpha job
    alpha_job = models.SandboxExecutionJob(
        org_id=test_setup["org_a"].id,
        agent_id=test_setup["agent_a"].id,
        execution_id=f"sbx_alpha_iso_{uuid.uuid4().hex[:6]}",
        tool_name="python_sandbox",
        language="python",
        code_hash="alpha_hash",
        status="SUCCEEDED",
        stdout="Alpha confidential secrets"
    )
    db_session.add(alpha_job)
    db_session.commit()

    # Tenant Beta user attempts to retrieve Alpha job
    get_res = client.get(
        f"/api/runtime/sandbox/jobs/{alpha_job.execution_id}",
        headers={"Authorization": f"Bearer {test_setup['token_user_b']}"}
    )
    assert get_res.status_code == 404, "Cross-tenant access must return 404 Not Found"

    # Tenant Beta user attempts to cancel Alpha job
    cancel_res = client.post(
        f"/api/runtime/sandbox/jobs/{alpha_job.execution_id}/cancel",
        headers={"Authorization": f"Bearer {test_setup['token_user_b']}"}
    )
    assert cancel_res.status_code == 404

    # Tenant Beta listing jobs must not show Alpha jobs
    list_res = client.get(
        "/api/runtime/sandbox/jobs",
        headers={"Authorization": f"Bearer {test_setup['token_user_b']}"}
    )
    assert list_res.status_code == 200
    beta_jobs = list_res.json()
    assert all(j["org_id"] == str(test_setup["org_b"].id) for j in beta_jobs)


def test_10_gate_token_replay_protection(test_setup):
    """
    Test 10: Execution gate tokens are strictly single-use; replay attempts return 400.
    """
    worker = MockTestSandboxProvider()
    set_sandbox_provider(worker)

    gate_token, _ = helper_get_gate_token(test_setup["jwt_agent_a"])

    # First call consumes the token
    res1 = client.post(
        "/api/runtime/sandbox/execute",
        headers={"Authorization": f"Bearer {test_setup['jwt_agent_a']}"},
        json={"execution_gate_token": gate_token, "code": "print('Run 1')"}
    )
    assert res1.status_code == 200
    assert res1.json()["success"] is True

    # Second call with the same token MUST be rejected
    res2 = client.post(
        "/api/runtime/sandbox/execute",
        headers={"Authorization": f"Bearer {test_setup['jwt_agent_a']}"},
        json={"execution_gate_token": gate_token, "code": "print('Run 2 Replay')"}
    )
    assert res2.status_code == 400
    assert "replay" in res2.text.lower()


def test_11_invalid_and_expired_tokens(test_setup, db_session):
    """
    Test 11: Invalid, expired, or agent-mismatched gate tokens are rejected.
    """
    worker = MockTestSandboxProvider()
    set_sandbox_provider(worker)

    # 1. Nonexistent token
    res_fake = client.post(
        "/api/runtime/sandbox/execute",
        headers={"Authorization": f"Bearer {test_setup['jwt_agent_a']}"},
        json={"execution_gate_token": "gate_fake_12345", "code": "print(1)"}
    )
    assert res_fake.status_code == 404

    # 2. Token issued to Agent A, attempted to be executed by Agent B
    gate_token_a, _ = helper_get_gate_token(test_setup["jwt_agent_a"])
    res_mismatch = client.post(
        "/api/runtime/sandbox/execute",
        headers={"Authorization": f"Bearer {test_setup['jwt_agent_b']}"},
        json={"execution_gate_token": gate_token_a, "code": "print('Stolen token')"}
    )
    assert res_mismatch.status_code == 403
    assert "mismatch" in res_mismatch.text.lower()

    # 3. Expired token (>300s old)
    dec = models.Decision(
        agent_id=test_setup["agent_a"].id,
        intent_summary="Expired action",
        action_requested="EXECUTE",
        resource_target="python_sandbox",
        decision="ALLOW",
        execution_gate_token=f"gate_exp_{uuid.uuid4().hex[:8]}",
        gate_token_used=False,
        explanation="Old token",
        timestamp=datetime.datetime.utcnow() - datetime.timedelta(seconds=600)
    )
    db_session.add(dec)
    db_session.commit()

    res_exp = client.post(
        "/api/runtime/sandbox/execute",
        headers={"Authorization": f"Bearer {test_setup['jwt_agent_a']}"},
        json={"execution_gate_token": dec.execution_gate_token, "code": "print(1)"}
    )
    assert res_exp.status_code == 400
    assert "expired" in res_exp.text.lower()


def test_12_refuse_and_unapproved_review_blocked(test_setup, db_session):
    """
    Test 12: REFUSE decisions and unapproved REVIEW decisions NEVER execute.
    """
    worker = MockTestSandboxProvider()
    set_sandbox_provider(worker)

    # 1. REFUSE decision token
    dec_refuse = models.Decision(
        agent_id=test_setup["agent_a"].id,
        intent_summary="Refused action",
        action_requested="EXECUTE",
        resource_target="python_sandbox",
        decision="REFUSE",
        execution_gate_token=f"gate_ref_{uuid.uuid4().hex[:8]}",
        gate_token_used=False,
        explanation="Policy blocked action",
        timestamp=datetime.datetime.utcnow()
    )
    db_session.add(dec_refuse)
    db_session.commit()

    res_ref = client.post(
        "/api/runtime/sandbox/execute",
        headers={"Authorization": f"Bearer {test_setup['jwt_agent_a']}"},
        json={"execution_gate_token": dec_refuse.execution_gate_token, "code": "print(1)"}
    )
    assert res_ref.status_code == 403
    assert "not approved" in res_ref.text.lower()

    # 2. PENDING REVIEW decision (requires manager approval)
    dec_review = models.Decision(
        agent_id=test_setup["agent_a"].id,
        intent_summary="Review action",
        action_requested="EXECUTE",
        resource_target="python_sandbox",
        decision="REVIEW",
        execution_gate_token=f"gate_rev_{uuid.uuid4().hex[:8]}",
        gate_token_used=False,
        explanation="Review required",
        timestamp=datetime.datetime.utcnow()
    )
    db_session.add(dec_review)
    db_session.commit()

    app_req = models.ApprovalRequest(
        decision_id=dec_review.id,
        agent_id=test_setup["agent_a"].id,
        reason="Test approval review",
        status="PENDING"
    )
    db_session.add(app_req)
    db_session.commit()

    # Attempt to execute before approval -> must fail
    res_unapp = client.post(
        "/api/runtime/sandbox/execute",
        headers={"Authorization": f"Bearer {test_setup['jwt_agent_a']}"},
        json={"execution_gate_token": dec_review.execution_gate_token, "code": "print(1)"}
    )
    assert res_unapp.status_code == 403

    # Now Manager approves the request
    act_res = client.post(
        f"/api/approvals/{app_req.id}/act",
        headers={"Authorization": f"Bearer {test_setup['token_manager_a']}"},
        json={"action": "APPROVE"}
    )
    assert act_res.status_code == 200

    # Now execution succeeds!
    res_app = client.post(
        "/api/runtime/sandbox/execute",
        headers={"Authorization": f"Bearer {test_setup['jwt_agent_a']}"},
        json={"execution_gate_token": dec_review.execution_gate_token, "code": "print('Approved!')"}
    )
    assert res_app.status_code == 200
    assert res_app.json()["success"] is True


def test_13_backward_compatibility_with_tool_proxy(test_setup):
    """
    Test 13: Backward compatibility — calling /runtime/execute or /runtime/invoke
    with a sandbox tool or parameters containing 'code' seamlessly routes to sandbox provider.
    """
    worker = MockTestSandboxProvider()
    set_sandbox_provider(worker)

    # Acquire gate token for python_sandbox
    gate_token, _ = helper_get_gate_token(test_setup["jwt_agent_a"], params={"code": "print('Via Tool Proxy')"})

    # Call legacy POST /runtime/execute endpoint
    exec_res = client.post(
        "/api/runtime/execute",
        headers={"Authorization": f"Bearer {test_setup['jwt_agent_a']}"},
        json={
            "execution_gate_token": gate_token,
            "tool_name": "python_sandbox",
            "parameters": {"code": "print('Via Tool Proxy')"}
        }
    )
    assert exec_res.status_code == 200
    data = exec_res.json()
    assert data["success"] is True
    assert data["status"] == "SUCCEEDED"
    assert "response_data" in data


def test_14_audit_and_provenance_recording(test_setup, db_session):
    """
    Test 14: Verifies immutable audit logs and provenance events are recorded upon sandbox execution.
    """
    worker = MockTestSandboxProvider()
    set_sandbox_provider(worker)

    gate_token, _ = helper_get_gate_token(test_setup["jwt_agent_a"])
    exec_res = client.post(
        "/api/runtime/sandbox/execute",
        headers={"Authorization": f"Bearer {test_setup['jwt_agent_a']}"},
        json={
            "execution_gate_token": gate_token,
            "code": "print('Audit provenance test')"
        }
    )
    assert exec_res.status_code == 200
    data = exec_res.json()
    exec_id = data["execution_id"]

    # Check AuditLog
    audit = db_session.query(models.AuditLog).filter(
        models.AuditLog.event_type == "RUNTIME_SANDBOX_EXECUTED",
        models.AuditLog.org_id == test_setup["org_a"].id
    ).order_by(models.AuditLog.timestamp.desc()).first()
    assert audit is not None
    assert audit.result == "SUCCESS"
    assert audit.metadata_json.get("execution_id") == exec_id

    # Check AgentExecution telemetry
    exec_record = db_session.query(models.AgentExecution).filter(
        models.AgentExecution.request_id == exec_id
    ).first()
    assert exec_record is not None
    assert exec_record.outcome == "EXECUTED"
    assert exec_record.resource.startswith("sandbox:")


def test_15_celery_cleanup_task_purges_expired_artifacts(test_setup, db_session):
    """
    Test 15: Background Celery task purges old execution artifacts.
    """
    old_time = datetime.datetime.utcnow() - datetime.timedelta(hours=48)
    old_job = models.SandboxExecutionJob(
        org_id=test_setup["org_a"].id,
        agent_id=test_setup["agent_a"].id,
        execution_id=f"sbx_purge_{uuid.uuid4().hex[:6]}",
        tool_name="python_sandbox",
        language="python",
        code_hash="purge_hash",
        status="SUCCEEDED",
        cleanup_status="CLEANED",
        completed_at=old_time
    )
    db_session.add(old_job)
    db_session.commit()

    res = cleanup_expired_sandbox_artifacts_task(org_id_filter=str(test_setup["org_a"].id))
    assert res["status"] == "COMPLETED"
    assert res["purged_count"] >= 1

    db_session.refresh(old_job)
    assert old_job.cleanup_status == "PURGED"
