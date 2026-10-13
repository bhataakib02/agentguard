import unittest
import uuid
import datetime
import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from jose import jwt

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from database import SessionLocal
from config import settings
from core import security
from ws_manager import manager as ws_manager
from services.machine_auth_service import machine_auth_service
import models

client = TestClient(app)


class TestP0SecurityRemediation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

        # 1. Platform Organization
        cls.platform_org = cls.db.query(models.Organization).filter(models.Organization.name == "P0 Platform Org").first()
        if not cls.platform_org:
            cls.platform_org = models.Organization(name="P0 Platform Org", domain="p0.platform", status="ACTIVE")
            cls.db.add(cls.platform_org)
            cls.db.commit()
            cls.db.refresh(cls.platform_org)

        # 2. Tenant Alpha Organization
        cls.org_alpha = cls.db.query(models.Organization).filter(models.Organization.name == "P0 Tenant Alpha Org").first()
        if not cls.org_alpha:
            cls.org_alpha = models.Organization(name="P0 Tenant Alpha Org", domain="p0.alpha", status="ACTIVE")
            cls.db.add(cls.org_alpha)
            cls.db.commit()
            cls.db.refresh(cls.org_alpha)

        # 3. Tenant Beta Organization
        cls.org_beta = cls.db.query(models.Organization).filter(models.Organization.name == "P0 Tenant Beta Org").first()
        if not cls.org_beta:
            cls.org_beta = models.Organization(name="P0 Tenant Beta Org", domain="p0.beta", status="ACTIVE")
            cls.db.add(cls.org_beta)
            cls.db.commit()
            cls.db.refresh(cls.org_beta)

        # 4. Inactive Organization
        cls.org_suspended = cls.db.query(models.Organization).filter(models.Organization.name == "P0 Suspended Org").first()
        if not cls.org_suspended:
            cls.org_suspended = models.Organization(name="P0 Suspended Org", domain="p0.suspended", status="SUSPENDED")
            cls.db.add(cls.org_suspended)
            cls.db.commit()
            cls.db.refresh(cls.org_suspended)

        # 5. Super Admin User
        cls.super_admin = models.User(
            org_id=cls.platform_org.id,
            email=f"sa_p0_{uuid.uuid4().hex[:6]}@p0.platform",
            full_name="P0 Super Admin",
            role="SUPER_ADMIN",
            status="ACTIVE"
        )
        cls.db.add(cls.super_admin)

        # 6. Tenant Alpha Normal User
        cls.user_alpha = models.User(
            org_id=cls.org_alpha.id,
            email=f"alpha_{uuid.uuid4().hex[:6]}@p0.alpha",
            full_name="Alpha User",
            role="USER",
            status="ACTIVE"
        )
        cls.db.add(cls.user_alpha)

        # 7. Tenant Beta Normal User
        cls.user_beta = models.User(
            org_id=cls.org_beta.id,
            email=f"beta_{uuid.uuid4().hex[:6]}@p0.beta",
            full_name="Beta User",
            role="USER",
            status="ACTIVE"
        )
        cls.db.add(cls.user_beta)

        # 8. Suspended User in Org Alpha
        cls.user_suspended = models.User(
            org_id=cls.org_alpha.id,
            email=f"suspended_{uuid.uuid4().hex[:6]}@p0.alpha",
            full_name="Suspended Alpha User",
            role="USER",
            status="SUSPENDED"
        )
        cls.db.add(cls.user_suspended)

        # 9. User in Suspended Org
        cls.user_in_suspended_org = models.User(
            org_id=cls.org_suspended.id,
            email=f"inactive_org_{uuid.uuid4().hex[:6]}@p0.suspended",
            full_name="User In Suspended Org",
            role="USER",
            status="ACTIVE"
        )
        cls.db.add(cls.user_in_suspended_org)
        cls.db.commit()
        cls.db.refresh(cls.super_admin)
        cls.db.refresh(cls.user_alpha)
        cls.db.refresh(cls.user_beta)
        cls.db.refresh(cls.user_suspended)
        cls.db.refresh(cls.user_in_suspended_org)

        # 10. Agent Alpha (NORMAL)
        cls.agent_alpha = models.Agent(
            agent_code=f"AG-P0-A-{uuid.uuid4().hex[:4]}",
            org_id=cls.org_alpha.id,
            owner_id=cls.user_alpha.id,
            name="Alpha Machine Agent",
            purpose="Test Agent Operations",
            status="NORMAL"
        )
        cls.db.add(cls.agent_alpha)

        # 11. Agent Suspended
        cls.agent_suspended = models.Agent(
            agent_code=f"AG-P0-SUSP-{uuid.uuid4().hex[:4]}",
            org_id=cls.org_alpha.id,
            owner_id=cls.user_alpha.id,
            name="Suspended Machine Agent",
            purpose="Test Suspended Agent Operations",
            status="SUSPENDED"
        )
        cls.db.add(cls.agent_suspended)

        cls.db.commit()
        cls.db.refresh(cls.agent_alpha)
        cls.db.refresh(cls.agent_suspended)

        # Tokens
        cls.token_super_admin = security.create_access_token(cls.super_admin.id, email=cls.super_admin.email, role=cls.super_admin.role)
        cls.token_user_alpha = security.create_access_token(cls.user_alpha.id, email=cls.user_alpha.email, role=cls.user_alpha.role)
        cls.token_user_beta = security.create_access_token(cls.user_beta.id, email=cls.user_beta.email, role=cls.user_beta.role)
        cls.token_user_suspended = security.create_access_token(cls.user_suspended.id, email=cls.user_suspended.email, role=cls.user_suspended.role)
        cls.token_in_suspended_org = security.create_access_token(cls.user_in_suspended_org.id, email=cls.user_in_suspended_org.email, role=cls.user_in_suspended_org.role)

    @classmethod
    def teardownClass(cls):
        cls.db.close()

    # =========================================================================
    # A. WEBSOCKET AUTHENTICATION & TENANT ISOLATION TESTS
    # =========================================================================

    def test_ws_01_anonymous_connection_rejected(self):
        """Anonymous WebSocket connection without token must be closed immediately with 1008 policy violation."""
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect("/ws"):
                pass
        self.assertEqual(excinfo.value.code, 1008)

    def test_ws_02_query_param_spoofing_without_token_rejected(self):
        """Supplying ?role=SUPER_ADMIN or ?org_id=... without verified token must be rejected."""
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect(f"/ws?role=SUPER_ADMIN&org_id={self.platform_org.id}"):
                pass
        self.assertEqual(excinfo.value.code, 1008)

    def test_ws_03_forged_jwt_token_rejected(self):
        """Connecting with forged token signed by attacker secret must be rejected."""
        forged_token = jwt.encode(
            {"sub": str(self.super_admin.id), "email": self.super_admin.email, "role": "SUPER_ADMIN"},
            "malicious-attacker-secret-key-9999",
            algorithm="HS256"
        )
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect(f"/ws?token={forged_token}"):
                pass
        self.assertEqual(excinfo.value.code, 1008)

    def test_ws_04_suspended_user_connection_rejected(self):
        """Suspended user token must be rejected upon connection."""
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect(f"/ws?token={self.token_user_suspended}"):
                pass
        self.assertEqual(excinfo.value.code, 1008)

    def test_ws_05_inactive_organization_user_rejected(self):
        """User belonging to inactive/suspended organization must be rejected."""
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect(f"/ws?token={self.token_in_suspended_org}"):
                pass
        self.assertEqual(excinfo.value.code, 1008)

    def test_ws_06_verified_user_connects_and_pings(self):
        """Legitimate verified user connects successfully using ticket and can ping/pong."""
        from ws_manager import ws_ticket_manager
        ticket = ws_ticket_manager.issue_ticket(user_id=str(self.user_alpha.id), org_id=str(self.org_alpha.id), role=self.user_alpha.role)
        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            ws.send_text("PING")
            data = ws.receive_text()
            self.assertEqual(data, "PONG")

    def test_ws_07_verified_role_derived_from_db_not_query_params(self):
        """A normal user attempting to pass ?role=SUPER_ADMIN in query param does NOT get SUPER_ADMIN privilege."""
        import asyncio
        from ws_manager import ws_ticket_manager
        ticket = ws_ticket_manager.issue_ticket(user_id=str(self.user_alpha.id), org_id=str(self.org_alpha.id), role=self.user_alpha.role)
        # Connect user_alpha with ticket and ?role=SUPER_ADMIN
        with client.websocket_connect(f"/ws?ticket={ticket}&role=SUPER_ADMIN") as ws_alpha:
            self.assertTrue(len(ws_manager.active_connections) > 0)
            server_conn = ws_manager.active_connections[-1]
            server_id = id(server_conn)
            
            # Role MUST be "USER", never "SUPER_ADMIN"
            assigned_role = ws_manager._role_map.get(server_id)
            self.assertEqual(assigned_role, "USER", "Role must be derived from database profile, not query params")
            assigned_org = ws_manager._org_map.get(server_id)
            self.assertEqual(assigned_org, str(self.org_alpha.id), "Org must be derived from database profile")

            # Deliver message for org_alpha: user_alpha receives it
            asyncio.run(ws_manager.broadcast({"type": "ALPHA_ALERT", "msg": "hello alpha"}, org_id=str(self.org_alpha.id)))
            rec = ws_alpha.receive_json()
            self.assertEqual(rec["type"], "ALPHA_ALERT")

            # Deliver message for org_beta: user_alpha must NOT receive it
            asyncio.run(ws_manager.broadcast({"type": "BETA_ALERT", "msg": "hello beta"}, org_id=str(self.org_beta.id)))

            # Deliver platform-wide message (SUPER_ADMIN only): user_alpha must NOT receive it
            asyncio.run(ws_manager.broadcast({"type": "PLATFORM_GLOBAL_ALERT"}, org_id=None))

            # Send ping to confirm user_alpha received no spurious cross-tenant messages
            ws_alpha.send_text("PING")
            pong = ws_alpha.receive_text()
            self.assertEqual(pong, "PONG")

    # =========================================================================
    # B. MACHINE AGENT AUTHENTICATION & STATUS TESTS
    # =========================================================================

    def test_machine_01_suspended_agent_refused_at_runtime_and_execution_gate(self):
        """A suspended agent cannot authenticate new credentials, is refused by runtime gate, and blocked from tool execution."""
        # 1. Credential authentication fails closed
        cred, raw_key = machine_auth_service.create_agent_credential(
            db=self.db,
            agent=self.agent_suspended,
            name="Suspended Agent Key"
        )
        with pytest.raises(ValueError) as excinfo:
            machine_auth_service.authenticate_agent_credential(self.db, raw_key, agent_code=self.agent_suspended.agent_code)
        self.assertIn("SUSPENDED", str(excinfo.value))

        # 2. Runtime authorization refuses with AGENT_STATUS stage
        jwt_info = machine_auth_service.issue_machine_jwt(agent=self.agent_suspended)
        token = jwt_info["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post(
            "/api/runtime/authorize",
            headers=headers,
            json={"action": "EXECUTE", "resource": "PAYMENTS", "amount": 100.0}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["decision"], "REFUSE")
        self.assertEqual(data["stage_failed"], "AGENT_STATUS")

    def test_machine_02_revoked_credential_token_rejected(self):
        """A machine JWT issued with a credential that was subsequently revoked must fail verification."""
        cred, raw = machine_auth_service.create_agent_credential(
            db=self.db,
            agent=self.agent_alpha,
            name="Temporary Credential to Revoke"
        )
        jwt_info = machine_auth_service.issue_machine_jwt(agent=self.agent_alpha, credential=cred)
        token = jwt_info["access_token"]

        # Token is valid before revocation
        res = machine_auth_service.decode_and_verify_machine_jwt(token, self.db)
        self.assertEqual(res["agent_id"], str(self.agent_alpha.id))

        # Revoke the credential
        machine_auth_service.revoke_agent_credential(self.db, str(self.agent_alpha.id), str(cred.id))

        # Token must now fail verification
        with pytest.raises(ValueError) as excinfo:
            machine_auth_service.decode_and_verify_machine_jwt(token, self.db)
        self.assertIn("revoked", str(excinfo.value).lower())

    def test_machine_03_cross_tenant_token_rejected(self):
        """A machine token with mismatched org_id must fail verification."""
        import time
        forged_cross_tenant_jwt = jwt.encode(
            {
                "sub": str(self.agent_alpha.id),
                "agent_id": str(self.agent_alpha.id),
                "org_id": str(self.org_beta.id),  # Wrong org!
                "token_type": "machine",
                "exp": int(time.time()) + 3600
            },
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        with pytest.raises(ValueError) as excinfo:
            machine_auth_service.decode_and_verify_machine_jwt(forged_cross_tenant_jwt, self.db)
        self.assertIn("Cross-tenant machine identity mismatch", str(excinfo.value))


if __name__ == "__main__":
    unittest.main()
