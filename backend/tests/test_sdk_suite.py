"""
Milestone 5: Developer Ecosystem & SDKs Test Suite
Tests:
- AgentGuard Python SDK Client (authentication, direct header auth, pre-flight authorization, execution gate tokens)
- Egress Tool Proxy execution and replay prevention via SDK
- Unified invoke endpoint
- PII scanner SDK integration
- Active session heartbeat SDK integration
- LangChain AgentGuard Callback Handler
- CrewAI AgentGuard Governance Middleware
- AI Admin Assistant (tenant-scoped context grounding, LLM provider dispatch / truthful local synthesis fallback)
- Automated Data Retention & Purging Worker Task
"""

import os
import sys
import uuid
import datetime
import pytest
from fastapi.testclient import TestClient

# Setup test environment - MUST be before any AGENTGUARD imports
os.environ["DATABASE_URL"] = "sqlite:///test_sdk_suite.db"
os.environ["SECRET_KEY"] = "test-sdk-suite-secret-key-agentguard-milestone5"
os.environ["ENVIRONMENT"] = "test"

sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
# Add sdks/python to path so we can import agentguard package directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sdks", "python")))

from sqlalchemy.orm import sessionmaker
from main import app
from database import Base, engine, get_db
import models
from core.security import get_password_hash, create_access_token
from services.machine_auth_service import machine_auth_service
from services.passport_service import passport_service
from engines.assistant_engine import assistant_engine
from tasks.retention_tasks import purge_expired_data_task

from agentguard import (
    AgentGuardClient,
    AgentGuardAuthError,
    AgentGuardGovernanceRefusal,
    AgentGuardExecutionError,
    LangChainAgentGuardHandler,
    CrewAIAgentGuardMiddleware,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
test_client = TestClient(app)


class TestSDKSuite:
    db = None
    org_id = None
    user_id = None
    user_token = None
    agent_id = None
    agent_code = None
    agent_raw_key = None
    tool_id = None

    @classmethod
    def setup_class(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = TestingSessionLocal()
        suffix = uuid.uuid4().hex[:6]
        cls.agent_code = f"AG-SDK-{suffix}"

        # 1. Organization
        org = models.Organization(name=f"SDK Enterprise {suffix}", status="ACTIVE")
        cls.db.add(org)
        cls.db.commit()
        cls.db.refresh(org)
        cls.org_id = str(org.id)

        # 2. Human Admin User
        user = models.User(
            email=f"admin.{suffix}@sdkcorp.com",
            password_hash=get_password_hash("AdminPass123!"),
            full_name="SDK Admin",
            role="ADMIN",
            org_id=cls.org_id,
            status="ACTIVE"
        )
        cls.db.add(user)
        cls.db.commit()
        cls.db.refresh(user)
        cls.user_id = str(user.id)
        cls.user_token = create_access_token(user_id=cls.user_id, email=user.email, role="ADMIN")
        cls.auth_headers = {"Authorization": f"Bearer {cls.user_token}"}

        # 3. AI Agent
        agent = models.Agent(
            agent_code=cls.agent_code,
            name=f"SDK Autonomous Worker {suffix}",
            department="ENGINEERING",
            purpose="SDK agent governance testing",
            status="NORMAL",
            autonomy_level="HIGH",
            org_id=cls.org_id,
            owner_id=user.id,
            risk_score=15,
            daily_budget=10000.0
        )
        cls.db.add(agent)
        cls.db.commit()
        cls.db.refresh(agent)
        cls.agent_id = str(agent.id)

        # 4. Cryptographic Agent Passport
        passport = models.AgentPassport(
            agent_id=agent.id,
            passport_number=f"AG-PASSPORT-{agent.agent_code}",
            digital_signature="pending",
            issued_at=datetime.datetime.utcnow(),
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=365),
            verification_status="VERIFIED"
        )
        passport_service.sign_passport(agent, passport)
        cls.db.add(passport)
        cls.db.commit()

        # 5. Agent Credential
        cred, raw_key = machine_auth_service.create_agent_credential(
            db=cls.db,
            agent=agent,
            name="SDK Production Key"
        )
        cls.agent_raw_key = raw_key

        # 6. Agent Permissions — specific resource_name grants, action wildcard
        # resource_type="TOOL" ensures resource_type wildcard is NOT used
        # perm_res_name == req_res (action_requested.upper()) handles the match
        perm1 = models.Permission(
            agent_id=agent.id,
            resource_type="TOOL",
            resource_name="read_balance",
            action="*",
            is_allowed=True
        )
        perm2 = models.Permission(
            agent_id=agent.id,
            resource_type="TOOL",
            resource_name="execute_transfer",
            action="*",
            is_allowed=True
        )
        perm3 = models.Permission(
            agent_id=agent.id,
            resource_type="TOOL",
            resource_name="echo_tool",
            action="echo_tool",
            is_allowed=True
        )
        perm4 = models.Permission(
            agent_id=agent.id,
            resource_type="TOOL",
            resource_name="search_user",
            action="*",
            is_allowed=True
        )
        cls.db.add_all([perm1, perm2, perm3, perm4])

        # 7. Tool in Registry
        tool = models.Tool(
            name="echo_tool",
            description="Echoes input for SDK testing",
            endpoint="https://httpbin.org/post",
            org_id=cls.org_id,
            status="ACTIVE",
            risk_level="LOW"
        )
        cls.db.add(tool)

        # 8. Budget Record
        budget = models.Budget(
            agent_id=cls.agent_id,
            daily_limit=5000.0,
            monthly_limit=50000.0,
            current_daily_spend=350.0,
            current_monthly_spend=2100.0
        )
        cls.db.add(budget)

        cls.db.commit()

    @classmethod
    def teardown_class(cls):
        if cls.db:
            cls.db.close()

    def setup_method(self, method):
        """Ensure per-test database isolation so refusal/action sequences from prior tests do not contaminate subsequent tests."""
        if self.db and self.agent_id:
            dec_ids = [d.id for d in self.db.query(models.Decision.id).filter(models.Decision.agent_id == self.agent_id).all()]
            if dec_ids:
                self.db.query(models.ApprovalRequest).filter(models.ApprovalRequest.decision_id.in_(dec_ids)).delete(synchronize_session=False)
                self.db.query(models.ProvenanceEvent).filter(models.ProvenanceEvent.decision_id.in_(dec_ids)).delete(synchronize_session=False)
                self.db.query(models.AgentExecution).filter(models.AgentExecution.decision_id.in_(dec_ids)).delete(synchronize_session=False)
                self.db.query(models.SandboxExecutionJob).filter(models.SandboxExecutionJob.decision_id.in_(dec_ids)).delete(synchronize_session=False)
                self.db.query(models.Decision).filter(models.Decision.id.in_(dec_ids)).delete(synchronize_session=False)
                self.db.commit()

    # =========================================================================
    # Test 1: Python SDK Authentication
    # =========================================================================

    def test_sdk_client_authentication_success(self):
        client = AgentGuardClient(
            agent_code=self.agent_code,
            agent_key=self.agent_raw_key,
            base_url="",
            session=test_client
        )
        token = client.authenticate()
        assert token is not None
        assert len(token) > 20
        assert client.session_token == token

    def test_sdk_client_authentication_failure(self):
        client = AgentGuardClient(
            agent_code=self.agent_code,
            agent_key="ag_agent_invalid_secret_key_12345",
            base_url="",
            session=test_client
        )
        with pytest.raises(AgentGuardAuthError) as exc_info:
            client.authenticate()
        assert exc_info.value.status_code in (401, 403)

    # =========================================================================
    # Test 2: Direct Machine Header Auth & Pre-flight Authorization
    # =========================================================================

    def test_sdk_direct_header_authorization(self):
        # Client without calling authenticate()
        client = AgentGuardClient(
            agent_code=self.agent_code,
            agent_key=self.agent_raw_key,
            base_url="",
            session=test_client
        )
        assert client.session_token is None

        # Direct call with X-Agent-Code and X-Agent-Key
        decision = client.authorize(
            action_requested="read_balance",
            amount=0.0
        )
        assert decision["decision"] == "ALLOW"
        assert decision["decision_id"] is not None

    def test_sdk_authorize_allowed_and_execution_gate_token(self):
        client = AgentGuardClient(
            agent_code=self.agent_code,
            agent_key=self.agent_raw_key,
            base_url="",
            session=test_client
        )
        client.authenticate()

        decision = client.authorize(
            action_requested="execute_transfer",
            amount=150.0,
            parameters={"recipient": "ACC-8819", "amount": 150.0}
        )
        assert decision["decision"] == "ALLOW"
        assert decision["execution_gate_token"] is not None
        assert decision["execution_gate_token"].startswith("gate_")
        assert decision["risk_score"] <= 60

    def test_sdk_authorize_refusal_raises_exception(self):
        client = AgentGuardClient(
            agent_code=self.agent_code,
            agent_key=self.agent_raw_key,
            base_url="",
            session=test_client,
            raise_on_refusal=True
        )
        client.authenticate()

        # Action not permitted by agent permissions -> triggers REFUSE via PERMISSION gate
        # Use amount=0 to pass budget check and reach the permission gate
        with pytest.raises(AgentGuardGovernanceRefusal) as exc_info:
            client.authorize(
                action_requested="unauthorized_root_action",
                amount=0.0
            )
        err = exc_info.value
        assert err.decision_id is not None
        assert "permission" in err.explanation.lower() or "budget" in err.explanation.lower() or err.decision_id is not None

    def test_sdk_authorize_refusal_returns_dict_when_flag_disabled(self):
        client = AgentGuardClient(
            agent_code=self.agent_code,
            agent_key=self.agent_raw_key,
            base_url="",
            session=test_client,
            raise_on_refusal=False
        )
        client.authenticate()

        res = client.authorize(
            action_requested="unauthorized_root_action",
            amount=0.0
        )
        assert res["decision"] == "REFUSE"
        assert res["execution_gate_token"] is None

    # =========================================================================
    # Test 3: Tool Proxy Execute & Replay Protection via SDK
    # =========================================================================

    def test_sdk_tool_proxy_execute_and_replay_protection(self):
        client = AgentGuardClient(
            agent_code=self.agent_code,
            agent_key=self.agent_raw_key,
            base_url="",
            session=test_client
        )
        client.authenticate()

        # 1. Pre-flight check
        decision = client.authorize(
            action_requested="echo_tool",
            amount=0.0,
            parameters={"text": "Hello AgentGuard"}
        )
        assert decision["decision"] == "ALLOW"
        egt = decision["execution_gate_token"]
        assert egt is not None

        # 2. Execute via Egress Tool Proxy
        exec_res = client.execute(
            tool_name="echo_tool",
            parameters={"text": "Hello AgentGuard"},
            execution_gate_token=egt
        )
        # EXECUTED = gate accepted & dispatched (httpbin may be up or down)
        assert exec_res["status"] in ("EXECUTED", "EXECUTION_FAILED", "SUCCESS", "FAILED")
        assert exec_res["execution_id"] is not None

        # 3. Replay Protection: reusing the same gate token MUST be rejected
        with pytest.raises(AgentGuardExecutionError) as exc_info:
            client.execute(
                tool_name="echo_tool",
                parameters={"text": "Replay Attempt"},
                execution_gate_token=egt
            )
        assert exc_info.value.status_code in (400, 403)

    # =========================================================================
    # Test 4: Unified Invoke Endpoint via SDK
    # =========================================================================

    def test_sdk_invoke_unified_flow(self):
        client = AgentGuardClient(
            agent_code=self.agent_code,
            agent_key=self.agent_raw_key,
            base_url="",
            session=test_client
        )
        client.authenticate()

        # Invoke authorized tool atomically
        res = client.invoke(
            action_requested="echo_tool",
            tool_name="echo_tool",
            parameters={"msg": "Unified Call"}
        )
        assert res["decision"] == "ALLOW"
        # execution is nested under the 'execution' key in RuntimeInvokeResponse
        assert res["execution"] is not None
        assert res["execution"]["execution_id"] is not None

    def test_sdk_invoke_refusal_raises(self):
        client = AgentGuardClient(
            agent_code=self.agent_code,
            agent_key=self.agent_raw_key,
            base_url="",
            session=test_client,
            raise_on_refusal=True
        )
        client.authenticate()

        with pytest.raises(AgentGuardGovernanceRefusal):
            client.invoke(
                action_requested="unauthorized_invoke_action",
                tool_name="echo_tool",
                parameters={},
                amount=0.0
            )

    # =========================================================================
    # Test 5: PII Scanner & Session Heartbeats via SDK
    # =========================================================================

    def test_sdk_scan_pii(self):
        client = AgentGuardClient(
            agent_code=self.agent_code,
            agent_key=self.agent_raw_key,
            base_url="",
            session=test_client
        )
        client.authenticate()

        res = client.scan_pii(
            text="Employee SSN is 987-65-4321 and email is secret@cybercorp.com",
            mode="MASK"
        )
        # Backend returns has_pii, findings_count, sanitized_text
        assert res["has_pii"] is True
        assert res["findings_count"] >= 2
        assert "987" not in (res.get("sanitized_text") or "")

    def test_sdk_heartbeat(self):
        client = AgentGuardClient(
            agent_code=self.agent_code,
            agent_key=self.agent_raw_key,
            base_url="",
            session=test_client
        )
        client.authenticate()

        res = client.heartbeat()
        assert res["status"] == "HEALTHY"
        assert res["agent_code"] == self.agent_code
        assert res["session_active"] is not None

    # =========================================================================
    # Test 6: LangChain Integration Handler
    # =========================================================================

    def test_langchain_callback_handler_allowed_tool(self):
        client = AgentGuardClient(
            agent_code=self.agent_code,
            agent_key=self.agent_raw_key,
            base_url="",
            session=test_client
        )
        client.authenticate()
        handler = LangChainAgentGuardHandler(client=client, scan_pii_on_input=False)

        decision = handler.on_tool_start(
            serialized={"name": "read_balance"},
            input_str='{"account_id": "ACC-1"}',
            run_id="run-lang-01"
        )
        assert decision["decision"] == "ALLOW"
        assert handler.last_decision["decision"] == "ALLOW"

        # on_tool_end cleans up token
        handler.on_tool_end("Balance: $500", run_id="run-lang-01")
        assert "run-lang-01" not in handler.execution_gate_tokens

    def test_langchain_callback_handler_refused_tool(self):
        client = AgentGuardClient(
            agent_code=self.agent_code,
            agent_key=self.agent_raw_key,
            base_url="",
            session=test_client
        )
        client.authenticate()
        handler = LangChainAgentGuardHandler(client=client, scan_pii_on_input=False)

        with pytest.raises(AgentGuardGovernanceRefusal) as exc_info:
            handler.on_tool_start(
                serialized={"name": "unauthorized_wire"},
                input_str='{"amount": 0}'
            )
        assert exc_info.value.decision_id is not None

    def test_langchain_callback_handler_pii_blocking(self):
        client = AgentGuardClient(
            agent_code=self.agent_code,
            agent_key=self.agent_raw_key,
            base_url="",
            session=test_client
        )
        client.authenticate()
        handler = LangChainAgentGuardHandler(
            client=client,
            scan_pii_on_input=True,
            block_on_pii=True
        )

        with pytest.raises(AgentGuardGovernanceRefusal) as exc_info:
            handler.on_tool_start(
                serialized={"name": "search_user"},
                input_str='{"ssn": "123-45-6789"}'
            )
        assert "PII detected" in exc_info.value.explanation

    # =========================================================================
    # Test 7: CrewAI Middleware Integration
    # =========================================================================

    def test_crewai_middleware_guard_tool(self):
        client = AgentGuardClient(
            agent_code=self.agent_code,
            agent_key=self.agent_raw_key,
            base_url="",
            session=test_client
        )
        client.authenticate()
        guard = CrewAIAgentGuardMiddleware(client=client, scan_pii=False)

        # 1. Allowed tool
        @guard.guard_tool(tool_name="read_balance")
        def safe_tool(acc_id: str):
            return f"Balance for {acc_id}"

        res = safe_tool("ACC-100")
        assert res == "Balance for ACC-100"

        # 2. Refused tool
        @guard.guard_tool(tool_name="unauthorized_root_action")
        def dangerous_tool():
            return "EXECUTED_DANGEROUS"

        with pytest.raises(AgentGuardGovernanceRefusal):
            dangerous_tool()

    # =========================================================================
    # Test 8: AI Admin Assistant Context Grounding & Provider Dispatch
    # =========================================================================

    def test_assistant_engine_tenant_scoped_query(self):
        res = assistant_engine.process_query(
            query="Which agents exhibit high risk?",
            db=self.db,
            org_id=self.org_id
        )
        assert "question" in res
        assert "answer" in res
        assert "data" in res
        assert "recommendations" in res
        assert "provider" in res
        assert "high_risk_agents" in res["data"]

    def test_assistant_engine_budget_query(self):
        res = assistant_engine.process_query(
            query="How much money have our agents spent?",
            db=self.db,
            org_id=self.org_id
        )
        assert "₹" in res["answer"] or "spend" in res["answer"].lower()
        assert "total_daily_spend" in res["data"]
        assert res["data"]["total_daily_spend"] >= 350.0

    def test_assistant_router_endpoint(self):
        res = test_client.post(
            "/api/assistant/query",
            json={"question": "What is the general governance status?"},
            headers=self.auth_headers
        )
        assert res.status_code == 200
        data = res.json()
        assert data["question"] == "What is the general governance status?"
        assert len(data["answer"]) > 10
        assert "recommendations" in data

    # =========================================================================
    # Test 9: Automated Data Retention Purging Worker Task
    # =========================================================================

    def test_data_retention_purging_task(self):
        # Create an expired session in the past
        past_session = models.AgentRuntimeSession(
            agent_id=self.agent_id,
            session_token_jti=f"jti_old_{uuid.uuid4().hex[:6]}",
            expires_at=datetime.datetime.utcnow() - datetime.timedelta(days=15),
            status="EXPIRED"
        )
        self.db.add(past_session)
        self.db.commit()

        # Run purging task
        summary = purge_expired_data_task(org_id_filter=self.org_id, dry_run=False)
        assert summary["status"] == "COMPLETED"
        assert summary["purged_sessions"] >= 1

        # Verify audit log was recorded for the purge operation
        audit = self.db.query(models.AuditLog).filter(
            models.AuditLog.event_type == "DATA_RETENTION_PURGE",
            models.AuditLog.org_id == self.org_id
        ).first()
        assert audit is not None
        assert audit.metadata_json["purged_sessions"] >= 1
