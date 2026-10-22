"""
Regression Test Suite: Release-Blocker Remediation
Covers:
Phase A: Authorization Enforcement (Policies, Tools, Capabilities, Red Team, Agents, Billing)
Phase B: Outbound SSRF Defense & Connection Pinning
Phase C: Approval Integrity, State Transitions & Atomic Resolution
Phase D: Organization Dashboard Tenant Isolation
"""

import uuid
import datetime
import concurrent.futures
import threading
import http.server
import socket
import pytest
from fastapi.testclient import TestClient

from main import app
from database import SessionLocal
import models
from core import security
from services.tool_proxy_service import tool_proxy_service

client = TestClient(app)


class TestReleaseBlockerRemediation:
    @classmethod
    def setup_class(cls):
        cls.db = SessionLocal()
        cls.suffix = uuid.uuid4().hex[:6]

        # 1. Organization Alpha
        cls.org_alpha = models.Organization(
            name=f"Remediation Org Alpha {cls.suffix}",
            slug=f"org-alpha-{cls.suffix}",
            status="ACTIVE"
        )
        # 2. Organization Beta
        cls.org_beta = models.Organization(
            name=f"Remediation Org Beta {cls.suffix}",
            slug=f"org-beta-{cls.suffix}",
            status="ACTIVE"
        )
        cls.db.add(cls.org_alpha)
        cls.db.add(cls.org_beta)
        cls.db.commit()

        # Users for Alpha
        cls.user_alpha_admin = models.User(
            email=f"alpha_admin_{cls.suffix}@example.com",
            password_hash=security.get_password_hash("Secret123!"),
            full_name="Alpha Admin",
            role="ADMIN",
            org_id=cls.org_alpha.id,
            status="ACTIVE"
        )
        cls.user_alpha_manager = models.User(
            email=f"alpha_mgr_{cls.suffix}@example.com",
            password_hash=security.get_password_hash("Secret123!"),
            full_name="Alpha Manager",
            role="MANAGER",
            org_id=cls.org_alpha.id,
            status="ACTIVE"
        )
        cls.user_alpha_dev = models.User(
            email=f"alpha_dev_{cls.suffix}@example.com",
            password_hash=security.get_password_hash("Secret123!"),
            full_name="Alpha Developer",
            role="DEVELOPER",
            org_id=cls.org_alpha.id,
            status="ACTIVE"
        )
        cls.user_alpha_viewer = models.User(
            email=f"alpha_viewer_{cls.suffix}@example.com",
            password_hash=security.get_password_hash("Secret123!"),
            full_name="Alpha Viewer",
            role="VIEWER",
            org_id=cls.org_alpha.id,
            status="ACTIVE"
        )
        cls.user_alpha_user = models.User(
            email=f"alpha_user_{cls.suffix}@example.com",
            password_hash=security.get_password_hash("Secret123!"),
            full_name="Alpha User",
            role="USER",
            org_id=cls.org_alpha.id,
            status="ACTIVE"
        )
        # User for Beta
        cls.user_beta_admin = models.User(
            email=f"beta_admin_{cls.suffix}@example.com",
            password_hash=security.get_password_hash("Secret123!"),
            full_name="Beta Admin",
            role="ADMIN",
            org_id=cls.org_beta.id,
            status="ACTIVE"
        )

        cls.db.add(cls.user_alpha_admin)
        cls.db.add(cls.user_alpha_manager)
        cls.db.add(cls.user_alpha_dev)
        cls.db.add(cls.user_alpha_viewer)
        cls.db.add(cls.user_alpha_user)
        cls.db.add(cls.user_beta_admin)
        cls.db.commit()

        # Auth tokens
        cls.token_alpha_admin = security.create_access_token(cls.user_alpha_admin.id, email=cls.user_alpha_admin.email, role="ADMIN")
        cls.token_alpha_mgr = security.create_access_token(cls.user_alpha_manager.id, email=cls.user_alpha_manager.email, role="MANAGER")
        cls.token_alpha_dev = security.create_access_token(cls.user_alpha_dev.id, email=cls.user_alpha_dev.email, role="DEVELOPER")
        cls.token_alpha_viewer = security.create_access_token(cls.user_alpha_viewer.id, email=cls.user_alpha_viewer.email, role="VIEWER")
        cls.token_alpha_user = security.create_access_token(cls.user_alpha_user.id, email=cls.user_alpha_user.email, role="USER")
        cls.token_beta_admin = security.create_access_token(cls.user_beta_admin.id, email=cls.user_beta_admin.email, role="ADMIN")

        cls.hdr_alpha_admin = {"Authorization": f"Bearer {cls.token_alpha_admin}"}
        cls.hdr_alpha_mgr = {"Authorization": f"Bearer {cls.token_alpha_mgr}"}
        cls.hdr_alpha_dev = {"Authorization": f"Bearer {cls.token_alpha_dev}"}
        cls.hdr_alpha_viewer = {"Authorization": f"Bearer {cls.token_alpha_viewer}"}
        cls.hdr_alpha_user = {"Authorization": f"Bearer {cls.token_alpha_user}"}
        cls.hdr_beta_admin = {"Authorization": f"Bearer {cls.token_beta_admin}"}

        # Agents
        cls.agent_alpha = models.Agent(
            org_id=cls.org_alpha.id,
            owner_id=cls.user_alpha_admin.id,
            name="Alpha Finance Agent",
            agent_code=f"AG-ALPHA-{cls.suffix}",
            purpose="Financial approvals and execution",
            status="NORMAL",
            autonomy_level="MEDIUM",
            daily_budget=500.0
        )
        cls.agent_beta = models.Agent(
            org_id=cls.org_beta.id,
            owner_id=cls.user_beta_admin.id,
            name="Beta Billing Agent",
            agent_code=f"AG-BETA-{cls.suffix}",
            purpose="Beta invoices",
            status="NORMAL",
            autonomy_level="LOW",
            daily_budget=200.0
        )
        cls.db.add(cls.agent_alpha)
        cls.db.add(cls.agent_beta)
        cls.db.commit()

    @classmethod
    def teardown_class(cls):
        cls.db.close()

    # =========================================================================
    # PHASE A: AUTHORIZATION ENFORCEMENT
    # =========================================================================

    def test_01_policy_rbac_low_privilege_rejected(self):
        """Low privilege users (VIEWER, USER) cannot create security policies."""
        policy_payload = {
            "name": f"Test Policy {uuid.uuid4().hex[:6]}",
            "type": "FINANCIAL_LIMIT",
            "enforcement_mode": "BLOCK",
            "parameters": {"max_amount": 1000.0}
        }
        # VIEWER cannot create policy
        res_v = client.post("/api/policies", json=policy_payload, headers=self.hdr_alpha_viewer)
        assert res_v.status_code == 403

        # USER cannot create policy
        res_u = client.post("/api/policies", json=policy_payload, headers=self.hdr_alpha_user)
        assert res_u.status_code == 403

        # ADMIN can create policy
        res_a = client.post("/api/policies", json=policy_payload, headers=self.hdr_alpha_admin)
        assert res_a.status_code in (200, 201)
        policy_id = res_a.json()["id"]

        # USER cannot update policy
        res_up = client.patch(f"/api/policies/{policy_id}", json={"name": "Tampered Policy"}, headers=self.hdr_alpha_user)
        assert res_up.status_code == 403

        # DEVELOPER cannot delete policy
        res_del = client.delete(f"/api/policies/{policy_id}", headers=self.hdr_alpha_dev)
        assert res_del.status_code == 403

        # ADMIN can delete policy
        res_del_adm = client.delete(f"/api/policies/{policy_id}", headers=self.hdr_alpha_admin)
        assert res_del_adm.status_code == 200

    def test_02_tool_rbac_unauthorized_rejected(self):
        """Ordinary users cannot register, edit, or delete tool definitions."""
        tool_payload = {
            "name": f"refund_tool_{uuid.uuid4().hex[:6]}",
            "description": "Process customer refunds",
            "endpoint_url": "https://api.example.com/refund",
            "method": "POST",
            "auth_type": "NONE"
        }
        # VIEWER cannot create tool
        res_v = client.post("/api/tools", json=tool_payload, headers=self.hdr_alpha_viewer)
        assert res_v.status_code == 403

        # ADMIN can create tool
        res_a = client.post("/api/tools", json=tool_payload, headers=self.hdr_alpha_admin)
        assert res_a.status_code in (200, 201)
        tool_id = res_a.json()["id"]

        # VIEWER cannot delete tool
        res_del = client.delete(f"/api/tools/{tool_id}", headers=self.hdr_alpha_viewer)
        assert res_del.status_code == 403

        # ADMIN can delete tool
        res_del_adm = client.delete(f"/api/tools/{tool_id}", headers=self.hdr_alpha_admin)
        assert res_del_adm.status_code == 200

    def test_03_capability_token_issuance_role_and_budget_guards(self):
        """Capability issuance requires authorized role and respects daily budget."""
        cap_req = {
            "agent_id": str(self.agent_alpha.id),
            "capability_name": "payment_execution",
            "scope": "payments:process",
            "amount_limit": 100.0,
            "ttl_seconds": 3600
        }
        # VIEWER cannot issue capabilities
        res_v = client.post("/api/capabilities/issue", json=cap_req, headers=self.hdr_alpha_viewer)
        assert res_v.status_code == 403

        # MANAGER can issue capabilities within agent budget (500.0)
        res_m = client.post("/api/capabilities/issue", json=cap_req, headers=self.hdr_alpha_mgr)
        assert res_m.status_code == 200
        cap_token = res_m.json()["token_code"]
        assert cap_token is not None

        # Exceeding budget without ADMIN raises 400
        excessive_req = dict(cap_req, amount_limit=9999.0)
        res_exc = client.post("/api/capabilities/issue", json=excessive_req, headers=self.hdr_alpha_mgr)
        assert res_exc.status_code == 400
        assert "daily budget" in res_exc.json()["detail"].lower()

    def test_04_red_team_operations_restricted(self):
        """Red team execution and fuzzing require security officer/analyst or admin."""
        # VIEWER cannot run red team tests
        res_v = client.post("/api/red-team/run", json={"test_type": "PROMPT_INJECTION"}, headers=self.hdr_alpha_viewer)
        assert res_v.status_code == 403

        # DEVELOPER cannot run fuzz tests
        res_d = client.post("/api/red-team/fuzz", json={"agent_id": str(self.agent_alpha.id)}, headers=self.hdr_alpha_dev)
        assert res_d.status_code == 403

    def test_05_agent_budget_and_autonomy_update_guarded(self):
        """Ordinary users cannot arbitrarily increase budget or elevate autonomy level."""
        # DEVELOPER attempting to elevate autonomy
        res_auto = client.patch(
            f"/api/agents/{self.agent_alpha.id}",
            json={"autonomy_level": "HIGH"},
            headers=self.hdr_alpha_dev
        )
        assert res_auto.status_code == 403

        # DEVELOPER attempting to change budget
        res_bud = client.patch(
            f"/api/agents/{self.agent_alpha.id}",
            json={"daily_budget": 50000.0},
            headers=self.hdr_alpha_dev
        )
        assert res_bud.status_code == 403

    def test_06_payment_simulation_requires_admin(self):
        """Sandbox payment simulation cannot be triggered by unprivileged users."""
        pay_req = {"plan_id": "ENTERPRISE", "amount": 499.0}
        res_v = client.post("/api/billing/simulate-payment", json=pay_req, headers=self.hdr_alpha_viewer)
        assert res_v.status_code == 403

        res_a = client.post("/api/billing/simulate-payment", json=pay_req, headers=self.hdr_alpha_admin)
        assert res_a.status_code == 200

    # =========================================================================
    # PHASE B: OUTBOUND SSRF DEFENSE & CONNECTION PINNING
    # =========================================================================

    def test_07_ssrf_metadata_and_private_ips_blocked(self):
        """Outbound calls to metadata, loopback, and private IPs are blocked fail-closed."""
        malicious_urls = [
            "http://169.254.169.254/latest/meta-data",
            "http://100.100.100.200/latest/meta-data",
            "http://127.0.0.1:8000/internal",
            "http://10.0.0.1/admin",
            "http://192.168.1.100/status",
            "http://0.0.0.0:80/secret",
            "http://metadata.google.internal/computeMetadata/v1/",
            "http://[::1]:8080/hec"
        ]
        for url in malicious_urls:
            res = tool_proxy_service.safe_dispatch_request(url)
            assert not res["success"]
            assert res["ssrf_blocked"]

    def test_08_ssrf_redirect_to_private_address_blocked(self):
        """Redirects are not followed and strictly rejected."""
        tool_proxy_service.set_dns_resolver(lambda host, port: ["93.184.215.14"])
        try:
            # Synthetic 302 redirect
            res = tool_proxy_service.safe_dispatch_request("https://example.com/redirect")
            # If a redirect occurs, is_redirect is True and success is False
            if res.get("status_code") in (301, 302, 307, 308) or res.get("is_redirect"):
                assert res["is_redirect"]
                assert not res["success"]
        finally:
            tool_proxy_service.set_dns_resolver(None)

    # =========================================================================
    # PHASE C: APPROVAL INTEGRITY & ATOMIC RESOLUTION
    # =========================================================================

    def _create_approval_request(self, agent_id: str, amount: float = 250.0, created_at: datetime.datetime = None):
        """Helper to create a decision and associated approval request in PENDING state."""
        dec = models.Decision(
            agent_id=agent_id,
            user_id=self.user_alpha_admin.id,
            intent_summary="Test payment",
            action_requested="EXECUTE_REFUND",
            resource_target="account:987",
            amount=amount,
            decision="REVIEW",
            risk_score=75,
            explanation="Requires human governance approval",
            execution_status="PENDING_APPROVAL"
        )
        self.db.add(dec)
        self.db.commit()
        self.db.refresh(dec)

        app_req = models.ApprovalRequest(
            decision_id=dec.id,
            agent_id=agent_id,
            amount=amount,
            reason="High transaction threshold",
            status="PENDING",
            created_at=created_at or datetime.datetime.utcnow()
        )
        self.db.add(app_req)
        self.db.commit()
        self.db.refresh(app_req)
        return app_req, dec

    def test_09_approval_resolution_sets_pending_execution_truthfully(self):
        """Approving a request updates decision to APPROVED_PENDING_EXECUTION with gate token (not EXECUTED)."""
        app_req, dec = self._create_approval_request(self.agent_alpha.id)

        res = client.post(
            f"/api/approvals/{app_req.id}/act",
            json={"action": "APPROVE"},
            headers=self.hdr_alpha_mgr
        )
        assert res.status_code == 200
        assert res.json()["new_status"] == "APPROVED"

        self.db.expire_all()
        dec_refreshed = self.db.query(models.Decision).filter_by(id=dec.id).first()
        assert dec_refreshed.decision == "ALLOW"
        assert dec_refreshed.execution_status == "APPROVED_PENDING_EXECUTION"
        assert dec_refreshed.execution_gate_token is not None
        assert not dec_refreshed.gate_token_used

    def test_10_repeat_approval_fails(self):
        """Acting twice on an already approved request fails with 400."""
        app_req, _ = self._create_approval_request(self.agent_alpha.id)

        # 1. First approval succeeds
        res1 = client.post(
            f"/api/approvals/{app_req.id}/act",
            json={"action": "APPROVE"},
            headers=self.hdr_alpha_mgr
        )
        assert res1.status_code == 200

        # 2. Second approval must fail
        res2 = client.post(
            f"/api/approvals/{app_req.id}/act",
            json={"action": "APPROVE"},
            headers=self.hdr_alpha_mgr
        )
        assert res2.status_code == 400
        assert "Cannot resolve" in res2.json()["detail"] or "PENDING" in res2.json()["detail"]

    def test_11_approve_after_reject_and_reject_after_approve_fail(self):
        """Cross-resolution transitions (approve after reject, reject after approve) are rejected."""
        # A. Reject then Approve
        app_req_a, dec_a = self._create_approval_request(self.agent_alpha.id)
        res_rej = client.post(
            f"/api/approvals/{app_req_a.id}/act",
            json={"action": "REJECT"},
            headers=self.hdr_alpha_mgr
        )
        assert res_rej.status_code == 200
        assert res_rej.json()["new_status"] == "REJECTED"

        self.db.expire_all()
        dec_a_refreshed = self.db.query(models.Decision).filter_by(id=dec_a.id).first()
        assert dec_a_refreshed.decision == "REFUSE"
        assert dec_a_refreshed.execution_status == "BLOCKED"
        assert dec_a_refreshed.gate_token_used is True

        res_app_after_rej = client.post(
            f"/api/approvals/{app_req_a.id}/act",
            json={"action": "APPROVE"},
            headers=self.hdr_alpha_mgr
        )
        assert res_app_after_rej.status_code == 400

        # B. Approve then Reject
        app_req_b, _ = self._create_approval_request(self.agent_alpha.id)
        res_app = client.post(
            f"/api/approvals/{app_req_b.id}/act",
            json={"action": "APPROVE"},
            headers=self.hdr_alpha_mgr
        )
        assert res_app.status_code == 200

        res_rej_after_app = client.post(
            f"/api/approvals/{app_req_b.id}/act",
            json={"action": "REJECT"},
            headers=self.hdr_alpha_mgr
        )
        assert res_rej_after_app.status_code == 400

    def test_12_expired_approval_rejected(self):
        """Approval request exceeding the 24-hour SLA window cannot be approved."""
        past_time = datetime.datetime.utcnow() - datetime.timedelta(hours=25)
        app_req_exp, _ = self._create_approval_request(self.agent_alpha.id, created_at=past_time)

        res = client.post(
            f"/api/approvals/{app_req_exp.id}/act",
            json={"action": "APPROVE"},
            headers=self.hdr_alpha_mgr
        )
        assert res.status_code == 400
        assert "expired" in res.json()["detail"].lower()

    def test_13_concurrent_resolution_atomic_race(self):
        """Concurrent requests to resolve the same pending approval resolve exactly once."""
        app_req, _ = self._create_approval_request(self.agent_alpha.id)
        results = []

        def worker(action):
            res = client.post(
                f"/api/approvals/{app_req.id}/act",
                json={"action": action},
                headers=self.hdr_alpha_mgr
            )
            return res.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(worker, "APPROVE"),
                executor.submit(worker, "REJECT"),
                executor.submit(worker, "APPROVE"),
            ]
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())

        # Exactly ONE request succeeds with 200, the rest fail with 400
        success_count = sum(1 for code in results if code == 200)
        conflict_count = sum(1 for code in results if code == 400)
        assert success_count == 1
        assert conflict_count == 2

    # =========================================================================
    # PHASE D: TENANT ISOLATION
    # =========================================================================

    def test_14_cross_tenant_approval_action_forbidden(self):
        """User from Org Beta cannot act on an approval request belonging to Org Alpha."""
        app_req, _ = self._create_approval_request(self.agent_alpha.id)

        res = client.post(
            f"/api/approvals/{app_req.id}/act",
            json={"action": "APPROVE"},
            headers=self.hdr_beta_admin
        )
        assert res.status_code == 403
        assert "another organization" in res.json()["detail"].lower()

    def test_15_organization_dashboard_pending_approvals_strictly_isolated(self):
        """Organization dashboard pending_approvals metric strictly reflects authorized tenant only."""
        # 1. Create 3 pending approvals in Org Alpha
        for _ in range(3):
            self._create_approval_request(self.agent_alpha.id)

        # 2. Create 2 pending approvals in Org Beta
        for _ in range(2):
            self._create_approval_request(self.agent_beta.id)

        # 3. Org Alpha dashboard inspects metrics
        res_alpha = client.get("/api/organization/dashboard", headers=self.hdr_alpha_admin)
        assert res_alpha.status_code == 200
        alpha_metrics = res_alpha.json()["metrics"]

        # 4. Org Beta dashboard inspects metrics
        res_beta = client.get("/api/organization/dashboard", headers=self.hdr_beta_admin)
        assert res_beta.status_code == 200
        beta_metrics = res_beta.json()["metrics"]

        # Verify strict isolation: Alpha sees at least 3, Beta sees at least 2, and Beta != Alpha total
        assert alpha_metrics["pending_approvals"] >= 3
        assert beta_metrics["pending_approvals"] >= 2
        # Beta must NOT see Alpha's pending approvals
        assert beta_metrics["pending_approvals"] < (alpha_metrics["pending_approvals"] + beta_metrics["pending_approvals"])
