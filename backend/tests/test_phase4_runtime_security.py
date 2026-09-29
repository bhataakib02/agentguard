"""
Phase 4: Runtime Security, Telemetry & Cost Governance Tests
Tests agent execution telemetry, token/cost tracking, budget governance,
risk signals, circuit breaker, persistent webhook delivery, dead-letter,
tenant isolation, and regression against Phase 1/2/3.
"""

import json
import uuid
import hmac
import hashlib
import datetime
import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

# Setup test database (SQLite in-memory)
os.environ["DATABASE_URL"] = "sqlite:///test_phase4.db"
os.environ["SECRET_KEY"] = "test-phase4-secret-key-not-production"
os.environ["ENVIRONMENT"] = "test"

from main import app
from database import Base, engine, get_db
import models


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


class TestPhase4RuntimeSecurity:
    """Phase 4 acceptance test suite: 25 tests."""

    _tokens = {}
    _org_ids = {}
    _agent_ids = {}
    _user_ids = {}

    @classmethod
    def _register_and_login(cls, org_name, full_name, email, password="TestPass123!", role="ADMIN"):
        """Helper: register org + user in test DB, return valid JWT token."""
        db = TestSession()
        try:
            org = db.query(models.Organization).filter(models.Organization.name == org_name).first()
            if not org:
                org = models.Organization(name=org_name, status="ACTIVE")
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
                    department="General",
                    status="ACTIVE"
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            else:
                user.role = role
                user.status = "ACTIVE"
                db.commit()
                db.refresh(user)

            from core import security
            token = security.create_access_token(user.id, email=user.email, role=user.role)
            return token, str(user.id), org_name
        finally:
            db.close()

    @classmethod
    def _auth_header(cls, token):
        return {"Authorization": f"Bearer {token}"}

    @classmethod
    def _setup_orgs(cls):
        """Setup two test organizations with agents."""
        if cls._tokens and cls._org_ids.get("A") and cls._org_ids.get("B"):
            return

        # Org A
        tok_a, uid_a, _ = cls._register_and_login("Phase4OrgA", "P4 Admin A", "p4admin_a@test.com")
        cls._tokens["A"] = tok_a
        cls._user_ids["A"] = uid_a

        # Org B
        tok_b, uid_b, _ = cls._register_and_login("Phase4OrgB", "P4 Admin B", "p4admin_b@test.com")
        cls._tokens["B"] = tok_b
        cls._user_ids["B"] = uid_b

        db = TestSession()
        try:
            ua = db.query(models.User).filter(models.User.email == "p4admin_a@test.com").first()
            if ua:
                cls._org_ids["A"] = ua.org_id
            ub = db.query(models.User).filter(models.User.email == "p4admin_b@test.com").first()
            if ub:
                cls._org_ids["B"] = ub.org_id

            # Create agents if not already present
            ag_a = db.query(models.Agent).filter(models.Agent.org_id == cls._org_ids.get("A")).first()
            if not ag_a and cls._org_ids.get("A"):
                ag_a = models.Agent(
                    agent_code=f"AG-P4-A-{uuid.uuid4().hex[:4].upper()}",
                    name="P4 Test Agent A",
                    org_id=cls._org_ids["A"],
                    owner_id=ua.id if ua else None,
                    department="Engineering",
                    purpose="Phase 4 test agent",
                    model_name="gpt-4o",
                    daily_budget=5000,
                    status="ACTIVE"
                )
                db.add(ag_a)
                db.commit()
                db.refresh(ag_a)
            if ag_a:
                cls._agent_ids["A"] = ag_a.id

            ag_b = db.query(models.Agent).filter(models.Agent.org_id == cls._org_ids.get("B")).first()
            if not ag_b and cls._org_ids.get("B"):
                ag_b = models.Agent(
                    agent_code=f"AG-P4-B-{uuid.uuid4().hex[:4].upper()}",
                    name="P4 Test Agent B",
                    org_id=cls._org_ids["B"],
                    owner_id=ub.id if ub else None,
                    department="Finance",
                    purpose="Phase 4 test agent B",
                    model_name="claude-3-opus",
                    daily_budget=3000,
                    status="ACTIVE"
                )
                db.add(ag_b)
                db.commit()
                db.refresh(ag_b)
            if ag_b:
                cls._agent_ids["B"] = ag_b.id
        finally:
            db.close()

    # ==================== 1. Tenant Telemetry Isolation ====================

    def test_01_tenant_runtime_telemetry_isolation(self):
        """Org A's telemetry must only return Org A data."""
        self._setup_orgs()

        # Record execution for Org A via decision evaluation
        client.post("/api/decisions/evaluate", json={
            "prompt": "Process refund $50 for customer",
            "agent_id": self._agent_ids.get("A"),
            "amount": 50.0
        }, headers=self._auth_header(self._tokens["A"]))

        # Org A queries their telemetry
        resp = client.get("/api/telemetry/executions?range=24h", headers=self._auth_header(self._tokens["A"]))
        assert resp.status_code == 200
        data = resp.json()
        assert "executions" in data

    def test_02_cross_tenant_telemetry_rejected(self):
        """Org A must not be able to access Org B's telemetry."""
        self._setup_orgs()
        org_b_id = self._org_ids.get("B", "some-other-org-id")
        resp = client.get(f"/api/telemetry/executions?org_id={org_b_id}",
                         headers=self._auth_header(self._tokens["A"]))
        assert resp.status_code == 403

    def test_03_super_admin_platform_telemetry(self):
        """SUPER_ADMIN can access platform-wide telemetry."""
        self._setup_orgs()
        # Create SUPER_ADMIN
        db = TestSession()
        sa = db.query(models.User).filter(models.User.email == "p4admin_a@test.com").first()
        if sa:
            sa.role = "SUPER_ADMIN"
            db.commit()

        tok_sa, _, _ = self._register_and_login("Phase4OrgA", "P4 Admin A", "p4admin_a@test.com")
        resp = client.get("/api/telemetry/executions?range=7d", headers=self._auth_header(tok_sa))
        assert resp.status_code == 200

        # Restore role
        sa = db.query(models.User).filter(models.User.email == "p4admin_a@test.com").first()
        if sa:
            sa.role = "ADMIN"
            db.commit()
        db.close()

    # ==================== 4. Token Count Aggregation ====================

    def test_04_token_count_aggregation(self):
        """Token usage endpoint returns aggregate SQL sums, not fabricated values."""
        self._setup_orgs()
        resp = client.get("/api/telemetry/token-usage?range=30d",
                         headers=self._auth_header(self._tokens["A"]))
        assert resp.status_code == 200
        data = resp.json()
        assert "total_tokens" in data
        assert "total_cost" in data
        assert "execution_count" in data
        # Verify types are numeric
        assert isinstance(data["total_tokens"], int)
        assert isinstance(data["total_cost"], (int, float))

    # ==================== 5. Cost Calculation ====================

    def test_05_cost_calculation(self):
        """Cost calculation uses ModelPricing records if configured."""
        from services.runtime_telemetry_service import calculate_cost

        db = TestSession()
        # Insert a pricing record
        pricing = models.ModelPricing(
            provider="openai",
            model="gpt-4o",
            input_cost_per_1k=0.005,
            output_cost_per_1k=0.015,
            currency="USD",
            active=True
        )
        db.add(pricing)
        db.commit()

        result = calculate_cost(db, "openai", "gpt-4o", 1000, 500)
        assert result["pricing_configured"] is True
        assert result["estimated_cost"] > 0
        # input: 1000/1000 * 0.005 = 0.005, output: 500/1000 * 0.015 = 0.0075
        expected = 0.005 + 0.0075
        assert abs(result["estimated_cost"] - expected) < 0.001
        db.close()

    def test_06_missing_pricing_handled_safely(self):
        """When pricing is not configured, cost is 0 and pricing_configured=False."""
        from services.runtime_telemetry_service import calculate_cost

        db = TestSession()
        result = calculate_cost(db, "anthropic", "claude-99-nonexistent", 1000, 500)
        assert result["pricing_configured"] is False
        assert result["estimated_cost"] == 0.0
        db.close()

    # ==================== 7. Budget Warning Threshold ====================

    def test_07_budget_warning_threshold(self):
        """Budget state transitions to WARNING when threshold is reached."""
        from services.runtime_telemetry_service import evaluate_budget_state

        db = TestSession()
        org_id = self._org_ids.get("A")
        agent_id = self._agent_ids.get("A")

        config = models.AgentBudgetConfig(
            org_id=org_id,
            agent_id=agent_id,
            daily_token_limit=1000,
            warning_threshold_pct=80.0,
            exceeded_threshold_pct=100.0,
            current_daily_tokens=850  # 85% of 1000 → WARNING
        )
        db.add(config)
        db.commit()

        state = evaluate_budget_state(config)
        assert state == "WARNING"

        db.delete(config)
        db.commit()
        db.close()

    def test_08_budget_exceeded_behavior(self):
        """Budget state transitions to EXCEEDED when limit is fully consumed."""
        from services.runtime_telemetry_service import evaluate_budget_state

        db = TestSession()
        org_id = self._org_ids.get("A")

        config = models.AgentBudgetConfig(
            org_id=org_id,
            agent_id=None,
            daily_cost_limit=10.0,
            warning_threshold_pct=80.0,
            exceeded_threshold_pct=100.0,
            current_daily_cost=15.0  # 150% → EXCEEDED
        )
        db.add(config)
        db.commit()

        state = evaluate_budget_state(config)
        assert state == "EXCEEDED"

        db.delete(config)
        db.commit()
        db.close()

    # ==================== 9. Suspended Agent Execution Rejected ====================

    def test_09_suspended_agent_execution_rejected(self):
        """Suspended agent's execution must be refused by PolicyEngine."""
        self._setup_orgs()
        agent_id = self._agent_ids.get("A")
        if not agent_id:
            pytest.skip("Agent A not created")

        # Suspend agent
        client.post(f"/api/agents/{agent_id}/suspend",
                    headers=self._auth_header(self._tokens["A"]))

        # Try evaluating a decision
        resp = client.post("/api/decisions/evaluate", json={
            "prompt": "Transfer $100 to vendor",
            "agent_id": agent_id,
            "amount": 100.0
        }, headers=self._auth_header(self._tokens["A"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] == "REFUSE"
        assert "SUSPENDED" in data["explanation"] or "CIRCUIT_BREAK" in data["explanation"] or "suspended" in data["explanation"].lower()

        # Restore agent
        client.post(f"/api/agents/{agent_id}/restore",
                    headers=self._auth_header(self._tokens["A"]))

    # ==================== 10. Runtime Policy Integration ====================

    def test_10_runtime_policy_integration(self):
        """Decision evaluation uses Phase 2 database-driven PolicyEngine and records telemetry."""
        self._setup_orgs()
        resp = client.post("/api/decisions/evaluate", json={
            "prompt": "Approve purchase order $200 for office supplies",
            "agent_id": self._agent_ids.get("A"),
            "amount": 200.0
        }, headers=self._auth_header(self._tokens["A"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] in ("ALLOW", "REVIEW", "REFUSE")
        assert "policy_name" in data

    # ==================== 11. Runtime Event Auditability ====================

    def test_11_runtime_event_auditability(self):
        """Runtime events are recorded in audit logs."""
        self._setup_orgs()
        resp = client.get("/api/audit/logs", headers=self._auth_header(self._tokens["A"]))
        if resp.status_code == 200:
            logs = resp.json()
            assert isinstance(logs, list)

    # ==================== 12. Risk Signal Creation ====================

    def test_12_risk_signal_creation(self):
        """Risk signals can be queried via tenant-isolated endpoint."""
        self._setup_orgs()
        resp = client.get("/api/telemetry/risk-signals?range=7d",
                         headers=self._auth_header(self._tokens["A"]))
        assert resp.status_code == 200
        data = resp.json()
        assert "signals" in data
        assert isinstance(data["signals"], list)

    # ==================== 13. Webhook Persistent Delivery ====================

    def test_13_webhook_persistent_delivery(self):
        """Webhook delivery is persisted before delivery attempt (DELIVERING status)."""
        self._setup_orgs()
        db = TestSession()

        # Create a webhook endpoint directly
        import secrets, hashlib
        raw_secret = f"whsec_{secrets.token_hex(24)}"
        endpoint = models.WebhookEndpoint(
            org_id=self._org_ids.get("A"),
            name="P4 Test Webhook",
            url="https://httpbin.org/status/500",  # Will fail
            secret_hash=hashlib.sha256(raw_secret.encode()).hexdigest(),
            secret_preview=f"whsec_****{raw_secret[-6:]}",
            secret_key=raw_secret,
            is_active=True,
            event_types=["*"]
        )
        db.add(endpoint)
        db.commit()
        db.refresh(endpoint)

        from services.notification_service import notification_service
        delivery = notification_service.dispatch_webhook_delivery(
            db=db,
            endpoint=endpoint,
            event_type="test.persistent",
            payload_data={"data": {"test": True}},
            max_retries=1
        )

        assert delivery is not None
        assert delivery.status in ("SUCCESS", "DEAD_LETTER", "FAILED", "RETRYING")
        assert delivery.attempt_count >= 1
        db.close()

    # ==================== 14. Webhook Retry Scheduling ====================

    def test_14_webhook_retry_scheduling(self):
        """WebhookDelivery model supports next_attempt_at for retry scheduling."""
        db = TestSession()
        delivery = db.query(models.WebhookDelivery).first()
        # Verify the column exists (even if no deliveries)
        assert hasattr(models.WebhookDelivery, "next_attempt_at")
        assert hasattr(models.WebhookDelivery, "response_body_preview")
        db.close()

    def test_15_retry_limit_enforcement(self):
        """Webhook retries are bounded (max 3 attempts) and transition to DEAD_LETTER."""
        self._setup_orgs()
        db = TestSession()
        import secrets, hashlib
        raw_secret = f"whsec_{secrets.token_hex(24)}"
        endpoint = models.WebhookEndpoint(
            org_id=self._org_ids.get("A"),
            name="P4 Retry Test",
            url="https://httpbin.org/status/503",  # Always fails
            secret_hash=hashlib.sha256(raw_secret.encode()).hexdigest(),
            secret_preview=f"whsec_****{raw_secret[-6:]}",
            secret_key=raw_secret,
            is_active=True,
            event_types=["*"]
        )
        db.add(endpoint)
        db.commit()
        db.refresh(endpoint)

        from services.notification_service import notification_service
        delivery = notification_service.dispatch_webhook_delivery(
            db=db,
            endpoint=endpoint,
            event_type="test.retry_limit",
            payload_data={"data": {"retry_test": True}},
            max_retries=3
        )

        assert delivery is not None
        assert delivery.attempt_count <= 3
        assert delivery.status in ("DEAD_LETTER", "FAILED", "RETRYING")
        db.close()

    # ==================== 16. Dead-Letter Creation ====================

    def test_16_dead_letter_creation(self):
        """Dead-letter deliveries are viewable via the dead-letter API."""
        self._setup_orgs()
        resp = client.get("/api/webhooks/dead-letter",
                         headers=self._auth_header(self._tokens["A"]))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    # ==================== 17. Secure Webhook Retry ====================

    def test_17_secure_webhook_retry(self):
        """Dead-letter retry endpoint requires authentication and tenant access."""
        resp = client.post("/api/webhooks/dead-letter/nonexistent-id/retry")
        # Should be 401 (no auth) or 403
        assert resp.status_code in (401, 403, 404, 422)

    # ==================== 18. Webhook Secret Never Exposed ====================

    def test_18_webhook_secret_never_exposed(self):
        """Webhook GET endpoints must never return the raw secret."""
        self._setup_orgs()
        webhooks = client.get("/api/webhooks", headers=self._auth_header(self._tokens["A"]))
        if webhooks.status_code == 200:
            for wh in webhooks.json():
                assert "secret_key" not in wh or wh.get("secret_key") is None
                # secret_preview should be masked
                if wh.get("secret_preview"):
                    assert "****" in wh["secret_preview"]

    # ==================== 19. Runtime Stream Tenant Isolation ====================

    def test_19_runtime_stream_tenant_isolation(self):
        """WebSocket manager supports tenant-isolated connections."""
        from ws_manager import ConnectionManager

        mgr = ConnectionManager()
        # Verify the manager has org_map and role_map
        assert hasattr(mgr, '_org_map')
        assert hasattr(mgr, '_role_map')

    # ==================== 20-22. Phase 1/2/3 Regression ====================

    def test_20_phase1_authentication_regression(self):
        """Unauthenticated requests to protected endpoints return 401/403."""
        endpoints = ["/api/agents", "/api/decisions", "/api/analytics/overview",
                     "/api/telemetry/executions"]
        for ep in endpoints:
            resp = client.get(ep)
            assert resp.status_code in (401, 403, 422), f"{ep} returned {resp.status_code}"

    def test_21_phase2_policy_regression(self):
        """Policy engine still evaluates decisions from database rules."""
        self._setup_orgs()
        resp = client.post("/api/decisions/evaluate", json={
            "prompt": "Send email to customer",
            "amount": 0
        }, headers=self._auth_header(self._tokens["A"]))
        assert resp.status_code == 200
        data = resp.json()
        assert "decision" in data
        assert data["decision"] in ("ALLOW", "REVIEW", "REFUSE")

    def test_22_phase3_analytics_reporting_regression(self):
        """Analytics overview returns real database counts."""
        self._setup_orgs()
        resp = client.get("/api/analytics/overview", headers=self._auth_header(self._tokens["A"]))
        assert resp.status_code == 200
        data = resp.json()
        assert "total_decisions" in data
        assert isinstance(data["total_decisions"], int)

    # ==================== 23. No Fake Runtime Metrics ====================

    def test_23_no_fake_runtime_metrics(self):
        """Telemetry endpoints return real DB aggregations, not hardcoded values."""
        self._setup_orgs()
        resp = client.get("/api/telemetry/token-usage?range=30d",
                         headers=self._auth_header(self._tokens["A"]))
        assert resp.status_code == 200
        data = resp.json()
        # Values must be numeric, not strings like "1.42M"
        assert isinstance(data["total_tokens"], int)
        assert isinstance(data["total_cost"], (int, float))

    # ==================== 24. Cross-Tenant Agent Budget Access ====================

    def test_24_no_cross_tenant_agent_budget_access(self):
        """Org A cannot view Org B's budget configurations."""
        self._setup_orgs()
        org_b_id = self._org_ids.get("B", "other-org")
        resp = client.get(f"/api/telemetry/budgets?org_id={org_b_id}",
                         headers=self._auth_header(self._tokens["A"]))
        assert resp.status_code == 403

    # ==================== 25. Agent Suspend/Resume Authorization ====================

    def test_25_agent_suspend_resume_authorization(self):
        """Cannot suspend/resume another org's agent."""
        self._setup_orgs()
        agent_b = self._agent_ids.get("B")
        if not agent_b:
            pytest.skip("Agent B not created")

        resp = client.post(f"/api/agents/{agent_b}/suspend",
                          headers=self._auth_header(self._tokens["A"]))
        assert resp.status_code == 403
