"""
AGENTGUARD P0 Critical Security Remediation Regression Suite - Phase 1
Tests:
- P0-1: Strict Gate Token Binding (Tool, Tenant, Endpoint snapshot, Canonical Parameters, rejection of override_endpoint)
- P0-2: Atomic Gate Token Single-Use Consumption & Multi-Threaded Race Defense
- P0-3: Strict Separation of Machine Identity and Human Authentication (Token Types, WS Ticket restriction)
- P0-4: Fail-Closed Billing Webhook HMAC Verification (Stripe, Razorpay, Idempotency, Unknown Tenant Rejection)
- P0-5: Decision Token Confidentiality & Runtime IAM/RBAC Enforcement
"""

import unittest
import uuid
import datetime
import json
import hmac
import hashlib
import time
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from starlette.testclient import TestClient
from main import app
from database import SessionLocal
import models
from core.security import create_access_token, get_password_hash
from services.machine_auth_service import machine_auth_service
from services.passport_service import passport_service

client = TestClient(app)


class TestP0Phase1Remediation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bootstrap import ensure_canonical_plans
        ensure_canonical_plans()
        cls.db = SessionLocal()
        cls.suffix = uuid.uuid4().hex[:6]

        # 1. Tenant Alpha Organization
        cls.org_a = models.Organization(
            name=f"P0 Rem Alpha {cls.suffix}",
            slug=f"p0-alpha-{cls.suffix}",
            status="ACTIVE"
        )
        cls.db.add(cls.org_a)

        # 2. Tenant Beta Organization
        cls.org_b = models.Organization(
            name=f"P0 Rem Beta {cls.suffix}",
            slug=f"p0-beta-{cls.suffix}",
            status="ACTIVE"
        )
        cls.db.add(cls.org_b)
        cls.db.commit()
        cls.db.refresh(cls.org_a)
        cls.db.refresh(cls.org_b)

        # 3. Users in Org Alpha
        cls.owner_user_a = models.User(
            org_id=cls.org_a.id,
            email=f"owner-a-{cls.suffix}@alpha.test",
            password_hash=get_password_hash("OwnerPass123!"),
            full_name="Alpha Agent Owner",
            role="USER",
            status="ACTIVE"
        )
        cls.admin_user_a = models.User(
            org_id=cls.org_a.id,
            email=f"admin-a-{cls.suffix}@alpha.test",
            password_hash=get_password_hash("AdminPass123!"),
            full_name="Alpha Org Admin",
            role="ADMIN",
            status="ACTIVE"
        )
        cls.auditor_user_a = models.User(
            org_id=cls.org_a.id,
            email=f"auditor-a-{cls.suffix}@alpha.test",
            password_hash=get_password_hash("AuditorPass123!"),
            full_name="Alpha Auditor",
            role="AUDITOR",
            status="ACTIVE"
        )
        cls.unrelated_user_a = models.User(
            org_id=cls.org_a.id,
            email=f"unrelated-a-{cls.suffix}@alpha.test",
            password_hash=get_password_hash("UnrelatedPass123!"),
            full_name="Alpha Unrelated User",
            role="USER",
            status="ACTIVE"
        )

        # 4. Users in Org Beta
        cls.user_b = models.User(
            org_id=cls.org_b.id,
            email=f"user-b-{cls.suffix}@beta.test",
            password_hash=get_password_hash("BetaPass123!"),
            full_name="Beta User",
            role="USER",
            status="ACTIVE"
        )
        cls.db.add_all([
            cls.owner_user_a, cls.admin_user_a, cls.auditor_user_a,
            cls.unrelated_user_a, cls.user_b
        ])
        cls.db.commit()

        # 5. Agent A in Org Alpha (owned by owner_user_a)
        cls.agent_a = models.Agent(
            org_id=cls.org_a.id,
            owner_id=cls.owner_user_a.id,
            name="Alpha Payment Agent",
            agent_code=f"AG-A-{cls.suffix}",
            purpose="Financial processing",
            status="NORMAL",
            autonomy_level="MEDIUM",
            daily_budget=10000.0
        )
        cls.agent_a_second = models.Agent(
            org_id=cls.org_a.id,
            owner_id=cls.owner_user_a.id,
            name="Alpha Secondary Agent",
            agent_code=f"AG-A2-{cls.suffix}",
            purpose="Secondary operations",
            status="NORMAL",
            autonomy_level="MEDIUM",
            daily_budget=5000.0
        )
        cls.agent_b = models.Agent(
            org_id=cls.org_b.id,
            owner_id=cls.user_b.id,
            name="Beta Agent",
            agent_code=f"AG-B-{cls.suffix}",
            purpose="Beta operations",
            status="NORMAL",
            autonomy_level="LOW",
            daily_budget=2000.0
        )
        cls.db.add_all([cls.agent_a, cls.agent_a_second, cls.agent_b])
        cls.db.commit()
        cls.db.refresh(cls.agent_a)
        cls.db.refresh(cls.agent_a_second)
        cls.db.refresh(cls.agent_b)

        # Passports
        for ag in [cls.agent_a, cls.agent_a_second, cls.agent_b]:
            p = models.AgentPassport(
                agent_id=ag.id,
                passport_number=f"PASSPORT-{ag.agent_code}",
                digital_signature="pending",
                issued_at=datetime.datetime.utcnow(),
                expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=365),
                verification_status="VERIFIED"
            )
            passport_service.sign_passport(ag, p)
            cls.db.add(p)
        cls.db.commit()

        # Credentials & Machine JWTs
        cls.cred_a, cls.raw_key_a = machine_auth_service.create_agent_credential(cls.db, cls.agent_a, name="Key A")
        cls.jwt_agent_a = machine_auth_service.issue_machine_jwt(cls.agent_a, cls.cred_a)["access_token"]

        cls.cred_a2, cls.raw_key_a2 = machine_auth_service.create_agent_credential(cls.db, cls.agent_a_second, name="Key A2")
        cls.jwt_agent_a2 = machine_auth_service.issue_machine_jwt(cls.agent_a_second, cls.cred_a2)["access_token"]

        cls.cred_b, cls.raw_key_b = machine_auth_service.create_agent_credential(cls.db, cls.agent_b, name="Key B")
        cls.jwt_agent_b = machine_auth_service.issue_machine_jwt(cls.agent_b, cls.cred_b)["access_token"]

        # User tokens
        cls.token_owner_a = create_access_token(user_id=str(cls.owner_user_a.id), email=cls.owner_user_a.email, role=cls.owner_user_a.role)
        cls.token_admin_a = create_access_token(user_id=str(cls.admin_user_a.id), email=cls.admin_user_a.email, role=cls.admin_user_a.role)
        cls.token_auditor_a = create_access_token(user_id=str(cls.auditor_user_a.id), email=cls.auditor_user_a.email, role=cls.auditor_user_a.role)
        cls.token_unrelated_a = create_access_token(user_id=str(cls.unrelated_user_a.id), email=cls.unrelated_user_a.email, role=cls.unrelated_user_a.role)
        cls.token_user_b = create_access_token(user_id=str(cls.user_b.id), email=cls.user_b.email, role=cls.user_b.role)

        # Tools
        cls.tool_payment = models.Tool(
            org_id=cls.org_a.id,
            name=f"tool_payment_{cls.suffix}",
            category="PAYMENT",
            endpoint="https://api.payment.internal/charge",
            risk_level="HIGH",
            status="ACTIVE",
            schema_definition={
                "type": "object",
                "required": ["amount", "account_id"],
                "properties": {
                    "amount": {"type": "number"},
                    "account_id": {"type": "string"}
                }
            }
        )
        cls.tool_payout = models.Tool(
            org_id=cls.org_a.id,
            name=f"tool_payout_{cls.suffix}",
            category="PAYMENT",
            endpoint="https://api.payout.internal/payout",
            risk_level="HIGH",
            status="ACTIVE",
            schema_definition={"type": "object"}
        )
        cls.tool_tenant_b = models.Tool(
            org_id=cls.org_b.id,
            name=f"tool_b_private_{cls.suffix}",
            category="API",
            endpoint="https://api.tenant-b.internal/action",
            risk_level="HIGH",
            status="ACTIVE",
            schema_definition={"type": "object"}
        )
        cls.db.add_all([cls.tool_payment, cls.tool_payout, cls.tool_tenant_b])

        # Permissions for Agent A
        cls.perm1 = models.Permission(
            agent_id=cls.agent_a.id,
            resource_type="TOOL",
            resource_name=cls.tool_payment.name,
            action="payment:charge",
            is_allowed=True
        )
        cls.perm2 = models.Permission(
            agent_id=cls.agent_a.id,
            resource_type="TOOL",
            resource_name=cls.tool_payout.name,
            action="payment:payout",
            is_allowed=True
        )
        cls.db.add_all([cls.perm1, cls.perm2])

        # Policy
        cls.policy = models.Policy(
            org_id=cls.org_a.id,
            name=f"P0 Rem Policy {cls.suffix}",
            category="FINANCE",
            status="ACTIVE"
        )
        cls.db.add(cls.policy)
        cls.db.commit()
        cls.db.refresh(cls.policy)

        cls.rule = models.PolicyRule(
            policy_id=cls.policy.id,
            condition_expression="amount < 5000",
            decision_output="ALLOW"
        )
        cls.db.add(cls.rule)
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def _authorize_agent_a(self, tool_name=None, action=None, amount=100.0, params=None):
        target_tool = tool_name or self.tool_payment.name
        target_action = action or "payment:charge"
        target_params = params or {"amount": amount, "account_id": "acc_001"}

        resp = client.post(
            "/api/runtime/authorize",
            headers={"Authorization": f"Bearer {self.jwt_agent_a}"},
            json={
                "action": target_action,
                "resource": target_tool,
                "amount": amount,
                "parameters": target_params
            }
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(data["decision"], "ALLOW")
        self.assertIsNotNone(data["execution_gate_token"])
        return data["execution_gate_token"], data["decision_id"], target_params

    # =========================================================================
    # PHASE 1 — P0-1: Strict Gate Token Binding
    # =========================================================================

    def test_p0_1_gate_token_cannot_execute_different_tool(self):
        """Token authorized for Tool A cannot be repurposed to execute Tool B."""
        gate_token, _, params = self._authorize_agent_a(tool_name=self.tool_payment.name, action="payment:charge")

        # Attempt to execute tool_payout using tool_payment's gate token
        resp = client.post(
            "/api/runtime/execute",
            headers={"Authorization": f"Bearer {self.jwt_agent_a}"},
            json={
                "execution_gate_token": gate_token,
                "tool_name": self.tool_payout.name,
                "parameters": params
            }
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("cannot execute", resp.json()["detail"])

    def test_p0_1_gate_token_cannot_execute_cross_tenant_tool(self):
        """Token for tenant Alpha cannot execute tool owned by tenant Beta."""
        gate_token, _, params = self._authorize_agent_a(tool_name=self.tool_payment.name)

        resp = client.post(
            "/api/runtime/execute",
            headers={"Authorization": f"Bearer {self.jwt_agent_a}"},
            json={
                "execution_gate_token": gate_token,
                "tool_name": self.tool_tenant_b.name,
                "parameters": params
            }
        )
        self.assertEqual(resp.status_code, 403)

    def test_p0_1_gate_token_cannot_be_reused_with_altered_parameters(self):
        """Token cannot be executed with altered parameters (parameter tampering rejected)."""
        gate_token, _, _ = self._authorize_agent_a(
            tool_name=self.tool_payment.name,
            params={"amount": 100.0, "account_id": "acc_legit"}
        )

        # Attacker tampers with parameters
        resp = client.post(
            "/api/runtime/execute",
            headers={"Authorization": f"Bearer {self.jwt_agent_a}"},
            json={
                "execution_gate_token": gate_token,
                "tool_name": self.tool_payment.name,
                "parameters": {"amount": 9999.0, "account_id": "acc_attacker"}
            }
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("parameters do not match", resp.json()["detail"])

    def test_p0_1_override_endpoint_cannot_redirect_execution(self):
        """Caller-supplied override_endpoint capability is rejected."""
        gate_token, _, params = self._authorize_agent_a()

        resp = client.post(
            "/api/runtime/execute",
            headers={"Authorization": f"Bearer {self.jwt_agent_a}"},
            json={
                "execution_gate_token": gate_token,
                "tool_name": self.tool_payment.name,
                "parameters": params,
                "override_endpoint": "https://attacker-controlled.net/steal"
            }
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("override_endpoint", resp.json()["detail"])

    def test_p0_1_endpoint_configuration_change_invalidates_token(self):
        """If tool endpoint is changed in DB after authorization, gate token is rejected."""
        gate_token, decision_id, params = self._authorize_agent_a()

        # Temporarily mutate tool endpoint in database to simulate silent tool redirection
        orig_ep = self.tool_payment.endpoint
        try:
            self.tool_payment.endpoint = "https://hijacked.internal/charge"
            self.db.commit()

            resp = client.post(
                "/api/runtime/execute",
                headers={"Authorization": f"Bearer {self.jwt_agent_a}"},
                json={
                    "execution_gate_token": gate_token,
                    "tool_name": self.tool_payment.name,
                    "parameters": params
                }
            )
            self.assertEqual(resp.status_code, 403)
            self.assertIn("configuration has changed", resp.json()["detail"])
        finally:
            self.tool_payment.endpoint = orig_ep
            self.db.commit()

    # =========================================================================
    # PHASE 2 — P0-2: Atomic Gate Token Single-Use Consumption
    # =========================================================================

    def test_p0_2_sequential_replay_rejected(self):
        """First consumption succeeds; sequential replay of the same token is rejected."""
        gate_token, _, params = self._authorize_agent_a()

        # Run 1: initial consumption
        resp1 = client.post(
            "/api/runtime/execute",
            headers={"Authorization": f"Bearer {self.jwt_agent_a}"},
            json={
                "execution_gate_token": gate_token,
                "tool_name": self.tool_payment.name,
                "parameters": params
            }
        )
        self.assertEqual(resp1.status_code, 200)

        # Run 2: sequential replay attempt
        resp2 = client.post(
            "/api/runtime/execute",
            headers={"Authorization": f"Bearer {self.jwt_agent_a}"},
            json={
                "execution_gate_token": gate_token,
                "tool_name": self.tool_payment.name,
                "parameters": params
            }
        )
        self.assertEqual(resp2.status_code, 400)
        self.assertIn("already been consumed", resp2.json()["detail"])

    def test_p0_2_atomic_concurrency_race_defense(self):
        """10 concurrent threads attempt to consume the same gate token. Exactly 1 must succeed."""
        gate_token, decision_id, params = self._authorize_agent_a()

        results = []

        def _fire():
            c = TestClient(app)
            r = c.post(
                "/api/runtime/execute",
                headers={"Authorization": f"Bearer {self.jwt_agent_a}"},
                json={
                    "execution_gate_token": gate_token,
                    "tool_name": self.tool_payment.name,
                    "parameters": params
                }
            )
            return r.status_code

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(_fire) for _ in range(10)]
            for f in futures:
                results.append(f.result())

        success_count = results.count(200)
        
        rejection_count = results.count(400)

        self.assertEqual(success_count, 1, f"Expected exactly 1 successful execution, got {success_count}. Results: {results}")
        self.assertEqual(rejection_count, 9, f"Expected 9 rejections, got {rejection_count}. Results: {results}")

        # Verify DB final state
        self.db.expire_all()
        dec = self.db.query(models.Decision).filter(models.Decision.id == decision_id).first()
        self.assertTrue(dec.gate_token_used)
        self.assertIn(dec.execution_status, ("EXECUTED", "EXECUTION_FAILED", "CLAIMED"))

    # =========================================================================
    # PHASE 3 — P0-3: Machine / Human Authentication Separation
    # =========================================================================

    def test_p0_3_machine_jwt_rejected_at_human_login(self):
        """Machine JWT cannot be presented as Bearer token to /api/auth/login."""
        resp = client.post(
            "/api/auth/login",
            headers={"Authorization": f"Bearer {self.jwt_agent_a}"},
            json={"email": self.owner_user_a.email, "password": "AnyPassword"}
        )
        self.assertEqual(resp.status_code, 401)
        self.assertIn("machine token cannot be used", resp.json()["detail"].lower())

    def test_p0_3_machine_jwt_cannot_obtain_super_admin_session(self):
        """Machine JWT cannot spoof an admin email to obtain an elevated human session."""
        resp = client.post(
            "/api/auth/login",
            headers={"Authorization": f"Bearer {self.jwt_agent_a}"},
            json={"email": "superadmin@platform.test", "password": "WrongPassword"}
        )
        self.assertEqual(resp.status_code, 401)

    def test_p0_3_websocket_ticket_cannot_authenticate_rest(self):
        """WebSocket tickets are restricted to handshake and rejected at REST endpoints."""
        from ws_manager import ws_ticket_manager
        ticket = ws_ticket_manager.issue_ticket(user_id=str(self.owner_user_a.id), org_id=str(self.org_a.id), role=self.owner_user_a.role)

        resp = client.get(
            "/api/agents",
            headers={"Authorization": f"Bearer {ticket}"}
        )
        self.assertEqual(resp.status_code, 401)
        self.assertIn("websocket tickets cannot be used", resp.json()["detail"].lower())

    def test_p0_3_machine_jwt_rejected_at_human_user_endpoints(self):
        """Machine JWT presented to get_current_user dependencies is rejected with 401."""
        resp = client.get(
            "/api/agents",
            headers={"Authorization": f"Bearer {self.jwt_agent_a}"}
        )
        self.assertEqual(resp.status_code, 401)
        self.assertIn("cannot authenticate human user endpoints", resp.json()["detail"].lower())

    def test_p0_3_legitimate_human_and_machine_auth_work(self):
        """Legitimate human login and legitimate machine authentication both succeed."""
        # Human login via local-login endpoint
        login_resp = client.post(
            "/api/auth/local-login",
            json={"email": self.owner_user_a.email, "password": "OwnerPass123!"}
        )
        self.assertEqual(login_resp.status_code, 200)
        self.assertIn("access_token", login_resp.json())

        # Machine credential exchange
        mach_resp = client.post(
            "/api/runtime/auth",
            json={"credential": self.raw_key_a, "agent_code": self.agent_a.agent_code}
        )
        self.assertEqual(mach_resp.status_code, 200)
        self.assertIn("access_token", mach_resp.json())

    # =========================================================================
    # PHASE 4 — P0-4: Billing Webhook HMAC Fail-Closed Verification
    # =========================================================================

    def test_p0_4_stripe_webhook_fail_closed_missing_empty_invalid_signature(self):
        """When webhook secret is configured, missing, empty, and invalid signatures are rejected."""
        os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_secret_123456789"
        payload = json.dumps({
            "id": f"evt_stripe_{uuid.uuid4().hex[:6]}",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": str(self.org_a.id),
                    "metadata": {"plan_id": "STARTER"}
                }
            }
        }).encode("utf-8")

        try:
            # 1. Missing header
            r1 = client.post("/api/billing/webhook/stripe", content=payload, headers={"Content-Type": "application/json"})
            self.assertEqual(r1.status_code, 400)
            self.assertIn("Missing", r1.json()["detail"])

            # 2. Empty header
            r2 = client.post("/api/billing/webhook/stripe", content=payload, headers={"Content-Type": "application/json", "Stripe-Signature": ""})
            self.assertEqual(r2.status_code, 400)

            # 3. Invalid signature
            r3 = client.post("/api/billing/webhook/stripe", content=payload, headers={"Content-Type": "application/json", "Stripe-Signature": "t=12345,v1=bad_signature_hex"})
            self.assertEqual(r3.status_code, 400)
            self.assertIn("Invalid", r3.json()["detail"])

            # 4. Valid signature
            t = str(int(time.time()))
            signed_payload = f"{t}.".encode("utf-8") + payload
            valid_sig = hmac.new("whsec_test_secret_123456789".encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
            r4 = client.post(
                "/api/billing/webhook/stripe",
                content=payload,
                headers={"Content-Type": "application/json", "Stripe-Signature": f"t={t},v1={valid_sig}"}
            )
            self.assertEqual(r4.status_code, 200)
            self.assertTrue(r4.json().get("received"))
        finally:
            os.environ.pop("STRIPE_WEBHOOK_SECRET", None)

    def test_p0_4_razorpay_webhook_fail_closed_verification(self):
        """Razorpay webhook fails closed on missing, empty, and invalid HMAC signatures."""
        os.environ["RAZORPAY_WEBHOOK_SECRET"] = "rzp_sec_test_987654321"
        payload = json.dumps({
            "id": f"evt_rzp_{uuid.uuid4().hex[:6]}",
            "event": "order.paid",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_test_01",
                        "notes": {"org_id": str(self.org_a.id), "plan_id": "PROFESSIONAL"}
                    }
                }
            }
        }).encode("utf-8")

        try:
            # 1. Missing header
            r1 = client.post("/api/billing/webhook/razorpay", content=payload, headers={"Content-Type": "application/json"})
            self.assertEqual(r1.status_code, 400)

            # 2. Invalid signature
            r2 = client.post("/api/billing/webhook/razorpay", content=payload, headers={"Content-Type": "application/json", "X-Razorpay-Signature": "invalid_hex"})
            self.assertEqual(r2.status_code, 400)

            # 3. Valid signature
            valid_sig = hmac.new("rzp_sec_test_987654321".encode("utf-8"), payload, hashlib.sha256).hexdigest()
            r3 = client.post(
                "/api/billing/webhook/razorpay",
                content=payload,
                headers={"Content-Type": "application/json", "X-Razorpay-Signature": valid_sig}
            )
            self.assertEqual(r3.status_code, 200)
            self.assertTrue(r3.json().get("received"))
        finally:
            os.environ.pop("RAZORPAY_WEBHOOK_SECRET", None)

    def test_p0_4_unknown_tenant_webhook_rejected(self):
        """Billing event referencing a non-existent organization is rejected with 404."""
        fake_org_id = str(uuid.uuid4())
        payload = json.dumps({
            "id": f"evt_stripe_{uuid.uuid4().hex[:6]}",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": fake_org_id,
                    "metadata": {"plan_id": "STARTER"}
                }
            }
        }).encode("utf-8")

        r = client.post("/api/billing/webhook/stripe", content=payload, headers={"Content-Type": "application/json"})
        self.assertEqual(r.status_code, 404)
        self.assertIn("does not exist", r.json()["detail"])

    def test_p0_4_replayed_billing_webhook_is_idempotent(self):
        """Replaying identical billing event ID does not duplicate license side effects."""
        event_id = f"evt_idempotent_{uuid.uuid4().hex[:8]}"
        payload = json.dumps({
            "id": event_id,
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": str(self.org_a.id),
                    "metadata": {"plan_id": "ENTERPRISE"}
                }
            }
        }).encode("utf-8")

        # First delivery
        r1 = client.post("/api/billing/webhook/stripe", content=payload, headers={"Content-Type": "application/json"})
        self.assertEqual(r1.status_code, 200)
        self.assertFalse(r1.json().get("duplicate", False))

        # Replayed delivery
        r2 = client.post("/api/billing/webhook/stripe", content=payload, headers={"Content-Type": "application/json"})
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(r2.json().get("duplicate"))

    # =========================================================================
    # PHASE 5 — P0-5: Decision Confidentiality & Runtime RBAC
    # =========================================================================

    def test_p0_5_decision_detail_does_not_leak_gate_token(self):
        """GET /api/decisions/{id} does not leak execution gate token in decision or provenance."""
        gate_token, decision_id, _ = self._authorize_agent_a()

        resp = client.get(
            f"/api/decisions/{decision_id}",
            headers={"Authorization": f"Bearer {self.token_owner_a}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Decision object must not contain gate token
        self.assertNotIn("execution_gate_token", data["decision"])

        # Provenance must not contain raw gate token
        prov = data.get("provenance")
        if prov and isinstance(prov, dict):
            self.assertNotEqual(prov.get("gate_token"), gate_token)

    def test_p0_5_auditor_cannot_authorize_actions(self):
        """Auditor role has read-only privileges and cannot authorize runtime actions."""
        resp = client.post(
            "/api/runtime/authorize",
            headers={"Authorization": f"Bearer {self.token_auditor_a}"},
            json={
                "agent_id": str(self.agent_a.id),
                "action": "payment:charge",
                "resource": self.tool_payment.name,
                "amount": 50.0,
                "parameters": {"amount": 50.0, "account_id": "acc_auditor"}
            }
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Insufficient privileges", resp.json()["detail"])

    def test_p0_5_unrelated_user_cannot_invoke_agent(self):
        """User who does not own the agent and lacks admin role cannot invoke the agent."""
        resp = client.post(
            "/api/runtime/invoke",
            headers={"Authorization": f"Bearer {self.token_unrelated_a}"},
            json={
                "agent_id": str(self.agent_a.id),
                "action": "payment:charge",
                "resource": self.tool_payment.name,
                "amount": 50.0,
                "parameters": {"amount": 50.0, "account_id": "acc_unrelated"}
            }
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Insufficient privileges", resp.json()["detail"])

    def test_p0_5_cross_tenant_runtime_authorization_denied(self):
        """User from Org B cannot authorize or invoke Agent in Org A."""
        resp = client.post(
            "/api/runtime/authorize",
            headers={"Authorization": f"Bearer {self.token_user_b}"},
            json={
                "agent_id": str(self.agent_a.id),
                "action": "payment:charge",
                "resource": self.tool_payment.name,
                "amount": 50.0
            }
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Cross-tenant", resp.json()["detail"])

    def test_p0_5_cross_agent_token_theft_rejected(self):
        """Agent A2 presenting gate token issued to Agent A is rejected."""
        gate_token, _, params = self._authorize_agent_a()

        resp = client.post(
            "/api/runtime/execute",
            headers={"Authorization": f"Bearer {self.jwt_agent_a2}"},
            json={
                "execution_gate_token": gate_token,
                "tool_name": self.tool_payment.name,
                "parameters": params
            }
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("issued to agent", resp.json()["detail"].lower())

    def test_p0_5_authorized_owner_and_admin_can_execute(self):
        """Authorized agent owner and org admin can legitimately authorize and execute."""
        # 1. Owner authorizes
        auth_resp = client.post(
            "/api/runtime/authorize",
            headers={"Authorization": f"Bearer {self.token_owner_a}"},
            json={
                "agent_id": str(self.agent_a.id),
                "action": "payment:charge",
                "resource": self.tool_payment.name,
                "amount": 25.0,
                "parameters": {"amount": 25.0, "account_id": "acc_owner"}
            }
        )
        self.assertEqual(auth_resp.status_code, 200)
        gate_token = auth_resp.json()["execution_gate_token"]
        self.assertIsNotNone(gate_token)

        # 2. Owner executes
        exec_resp = client.post(
            "/api/runtime/execute",
            headers={"Authorization": f"Bearer {self.token_owner_a}"},
            json={
                "execution_gate_token": gate_token,
                "tool_name": self.tool_payment.name,
                "parameters": {"amount": 25.0, "account_id": "acc_owner"}
            }
        )
        self.assertEqual(exec_resp.status_code, 200)

    def test_phase_g_schema_migration_and_idempotence(self):
        """
        Phase G Invariant:
        1. Fresh database initialization includes authorized_endpoint on decisions.
        2. Schema upgrade from an older table missing authorized_endpoint adds the column.
        3. Existing table data is preserved during migration.
        4. Re-running the migration is strictly idempotent and safe.
        """
        from sqlalchemy import create_engine, text, inspect
        from database import Base
        from bootstrap import ensure_schema_compatibility

        test_db_path = "test_phase_g_migration.db"
        if os.path.exists(test_db_path):
            os.remove(test_db_path)

        mig_engine = create_engine(f"sqlite:///{test_db_path}")

        try:
            # 1. Simulate legacy database with old decisions schema and existing production-like record
            with mig_engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE decisions (
                        id VARCHAR PRIMARY KEY,
                        agent_id VARCHAR,
                        action_requested VARCHAR,
                        resource_target VARCHAR,
                        decision VARCHAR,
                        explanation TEXT,
                        timestamp DATETIME
                    );
                """))
                conn.execute(text("""
                    INSERT INTO decisions (id, agent_id, action_requested, resource_target, decision, explanation, timestamp)
                    VALUES ('dec-legacy-1', 'ag-1', 'tool_query', 'db', 'ALLOW', 'Legacy test decision', '2026-01-01 00:00:00');
                """))
                conn.commit()

            # Verify column is missing initially
            inspector = inspect(mig_engine)
            cols_before = {c["name"] for c in inspector.get_columns("decisions")}
            self.assertNotIn("authorized_endpoint", cols_before)

            # 2. Run schema compatibility upgrade
            ensure_schema_compatibility(mig_engine)

            # Verify column exists after upgrade
            inspector = inspect(mig_engine)
            cols_after = {c["name"] for c in inspector.get_columns("decisions")}
            self.assertIn("authorized_endpoint", cols_after)

            # 3. Verify existing row data preserved
            with mig_engine.connect() as conn:
                row = conn.execute(text("SELECT id, action_requested, authorized_endpoint FROM decisions WHERE id = 'dec-legacy-1';")).fetchone()
                self.assertEqual(row[0], "dec-legacy-1")
                self.assertEqual(row[1], "tool_query")
                self.assertIsNone(row[2])

            # 4. Idempotence: running upgrade second time must succeed without error
            ensure_schema_compatibility(mig_engine)

            # 5. Insert row with authorized_endpoint into upgraded schema
            with mig_engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO decisions (id, agent_id, action_requested, resource_target, decision, explanation, timestamp, authorized_endpoint)
                    VALUES ('dec-new-2', 'ag-1', 'tool_query', 'db', 'ALLOW', 'New upgraded decision', '2026-10-20 00:00:00', 'https://api.internal/tool');
                """))
                conn.commit()
                new_row = conn.execute(text("SELECT authorized_endpoint FROM decisions WHERE id = 'dec-new-2';")).fetchone()
                self.assertEqual(new_row[0], "https://api.internal/tool")

        finally:
            mig_engine.dispose()
            if os.path.exists(test_db_path):
                os.remove(test_db_path)
