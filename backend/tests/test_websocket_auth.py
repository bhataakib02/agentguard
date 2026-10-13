"""
Dedicated test suite for WebSocket Authentication, Single-Use Ticket Exchange,
Multi-Instance Behavior, Session Revocation, and Multi-Tenant Broadcast Isolation.
Verifies requirement B3 & Post-Remediation Security Rules:
- Legacy bearer token path (?token=... or Authorization: Bearer ...) is strictly rejected.
- Only authenticated users can acquire tickets.
- Tickets are short-lived, single-use, tenant-bound, and resistant to replay.
- Multi-instance distributed ticket issuance and redemption works safely across instances.
- Account suspension and session revocation are strictly enforced.
- Cross-tenant broadcast events remain isolated.
"""

import time
import uuid
import datetime
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from sqlalchemy.orm import Session

from main import app
from database import SessionLocal
import models
from core import security
from ws_manager import ws_ticket_manager, ws_manager, WebSocketTicketManager

client = TestClient(app)

class TestWebSocketAuthAndTickets:
    @classmethod
    def setup_class(cls):
        cls.db: Session = SessionLocal()
        cls.org_a = models.Organization(
            name=f"Org WS A {uuid.uuid4().hex[:6]}",
            slug=f"org-ws-a-{uuid.uuid4().hex[:6]}",
            status="ACTIVE"
        )
        cls.org_b = models.Organization(
            name=f"Org WS B {uuid.uuid4().hex[:6]}",
            slug=f"org-ws-b-{uuid.uuid4().hex[:6]}",
            status="ACTIVE"
        )
        cls.db.add_all([cls.org_a, cls.org_b])
        cls.db.commit()

        cls.user_a = models.User(
            email=f"usera_{uuid.uuid4().hex[:6]}@example.com",
            password_hash=security.get_password_hash("SecretPassword123!"),
            full_name="User WS A",
            role="USER",
            status="ACTIVE",
            org_id=cls.org_a.id
        )
        cls.user_b = models.User(
            email=f"userb_{uuid.uuid4().hex[:6]}@example.com",
            password_hash=security.get_password_hash("SecretPassword123!"),
            full_name="User WS B",
            role="USER",
            status="ACTIVE",
            org_id=cls.org_b.id
        )
        cls.user_suspended = models.User(
            email=f"suspended_{uuid.uuid4().hex[:6]}@example.com",
            password_hash=security.get_password_hash("SecretPassword123!"),
            full_name="User WS Suspended",
            role="USER",
            status="SUSPENDED",
            org_id=cls.org_a.id
        )
        cls.db.add_all([cls.user_a, cls.user_b, cls.user_suspended])
        cls.db.commit()

        cls.token_user_a = security.create_access_token(cls.user_a.id, email=cls.user_a.email, role=cls.user_a.role)
        cls.token_user_b = security.create_access_token(cls.user_b.id, email=cls.user_b.email, role=cls.user_b.role)
        cls.token_user_suspended = security.create_access_token(cls.user_suspended.id, email=cls.user_suspended.email, role=cls.user_suspended.role)

    @classmethod
    def teardown_class(cls):
        try:
            cls.db.query(models.User).filter(models.User.id.in_([cls.user_a.id, cls.user_b.id, cls.user_suspended.id])).delete(synchronize_session=False)
            cls.db.query(models.Organization).filter(models.Organization.id.in_([cls.org_a.id, cls.org_b.id])).delete(synchronize_session=False)
            cls.db.commit()
        except Exception:
            pass
        finally:
            cls.db.close()

    def test_01_ticket_issue_and_consume(self):
        """Single-use ticket can be issued and consumed exactly once."""
        ticket = ws_ticket_manager.issue_ticket(
            user_id=str(self.user_a.id),
            org_id=str(self.org_a.id),
            email=self.user_a.email,
            role=self.user_a.role
        )
        assert isinstance(ticket, str) and len(ticket) > 20

        # Consume once
        claims = ws_ticket_manager.consume_ticket(ticket)
        assert claims is not None
        assert claims["user_id"] == str(self.user_a.id)
        assert claims["org_id"] == str(self.org_a.id)
        assert claims["role"] == "USER"

        # Replay attempt must fail
        replay = ws_ticket_manager.consume_ticket(ticket)
        assert replay is None

    def test_02_ticket_expiry(self):
        """Expired ticket cannot be consumed."""
        ticket = ws_ticket_manager.issue_ticket(
            user_id=str(self.user_a.id),
            org_id=str(self.org_a.id),
            email=self.user_a.email,
            role=self.user_a.role,
            ttl_seconds=0.1
        )
        time.sleep(0.2)
        claims = ws_ticket_manager.consume_ticket(ticket)
        assert claims is None

    def test_03_ws_ticket_endpoint_and_connect(self):
        """Exchange JWT for short-lived ticket via API and connect to /ws using ticket."""
        res = client.post(
            "/api/v1/auth/ws-ticket",
            headers={"Authorization": f"Bearer {self.token_user_a}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert "ticket" in data
        ticket = data["ticket"]

        # Connect with ticket
        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            ws.send_text("PING")
            msg = ws.receive_text()
            assert msg == "PONG"

        # Reusing the ticket must fail immediately (single-use enforcement)
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect(f"/ws?ticket={ticket}"):
                pass
        assert excinfo.value.code == 1008

    def test_04_ws_legacy_bearer_token_strictly_rejected(self):
        """Connecting with legacy ?token=... or Authorization: Bearer must be rejected with 1008."""
        # 1. Query parameter token
        with pytest.raises(WebSocketDisconnect) as excinfo1:
            with client.websocket_connect(f"/ws?token={self.token_user_a}"):
                pass
        assert excinfo1.value.code == 1008

        # 2. Authorization header without ticket
        with pytest.raises(WebSocketDisconnect) as excinfo2:
            with client.websocket_connect("/ws", headers={"Authorization": f"Bearer {self.token_user_a}"}):
                pass
        assert excinfo2.value.code == 1008

        # 3. Anonymous connection without ticket
        with pytest.raises(WebSocketDisconnect) as excinfo3:
            with client.websocket_connect("/ws"):
                pass
        assert excinfo3.value.code == 1008

    def test_05_ticket_acquisition_requires_authenticated_user(self):
        """Anonymous ticket acquisition attempt returns 401 Unauthorized."""
        res = client.post("/api/v1/auth/ws-ticket")
        assert res.status_code == 401

    def test_06_ws_revoked_session_blocks_ticket_issuance(self):
        """If a session record is marked revoked in the database, ticket acquisition is refused."""
        revoked_token = security.create_access_token(
            self.user_a.id,
            email=self.user_a.email,
            role=self.user_a.role
        )
        
        session_rec = models.Session(
            user_id=self.user_a.id,
            token=revoked_token,
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            revoked=True
        )
        self.db.add(session_rec)
        self.db.commit()

        try:
            res = client.post(
                "/api/v1/auth/ws-ticket",
                headers={"Authorization": f"Bearer {revoked_token}"}
            )
            assert res.status_code == 401
        finally:
            self.db.delete(session_rec)
            self.db.commit()

    def test_07_ws_suspended_user_ticket_issuance_and_connection_rejected(self):
        """Suspended user cannot acquire ticket, and any ticket presenting suspended status is closed with 1008."""
        # Ticket issuance blocked
        res = client.post(
            "/api/v1/auth/ws-ticket",
            headers={"Authorization": f"Bearer {self.token_user_suspended}"}
        )
        assert res.status_code in (401, 403)

        # Forged ticket presenting suspended user id is rejected on /ws connection
        forged_ticket = ws_ticket_manager.issue_ticket(
            user_id=str(self.user_suspended.id),
            org_id=str(self.org_a.id),
            role="USER"
        )
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect(f"/ws?ticket={forged_ticket}"):
                pass
        assert excinfo.value.code == 1008

    def test_08_multi_instance_ticket_sharing_simulation(self):
        """Simulate two backend instances sharing a distributed Redis-like storage adapter."""
        class MockRedisAdapter:
            def __init__(self):
                self._store = {}
            def set(self, key, val, ex=None):
                self._store[key] = val
                return True
            def delete(self, key):
                if key in self._store:
                    del self._store[key]
                    return 1
                return 0

        shared_mock_redis = MockRedisAdapter()
        instance_1 = WebSocketTicketManager(redis_client=shared_mock_redis)
        instance_2 = WebSocketTicketManager(redis_client=shared_mock_redis)

        # Instance 1 issues the ticket
        ticket = instance_1.issue_ticket(
            user_id=str(self.user_a.id),
            org_id=str(self.org_a.id),
            role="USER"
        )

        # Instance 2 redeems the ticket
        claims = instance_2.consume_ticket(ticket)
        assert claims is not None
        assert claims["user_id"] == str(self.user_a.id)

        # Replay on Instance 1 must fail
        replay_1 = instance_1.consume_ticket(ticket)
        assert replay_1 is None

        # Replay on Instance 2 must fail
        replay_2 = instance_2.consume_ticket(ticket)
        assert replay_2 is None

    def test_09_cross_tenant_broadcast_isolation_with_tickets(self):
        """Messages broadcast to Org A must never be received by Org B client."""
        import asyncio
        ticket_a = ws_ticket_manager.issue_ticket(user_id=str(self.user_a.id), org_id=str(self.org_a.id), role=self.user_a.role)
        ticket_b = ws_ticket_manager.issue_ticket(user_id=str(self.user_b.id), org_id=str(self.org_b.id), role=self.user_b.role)

        with client.websocket_connect(f"/ws?ticket={ticket_a}") as ws_a:
            with client.websocket_connect(f"/ws?ticket={ticket_b}") as ws_b:
                # Broadcast only to Org A
                asyncio.run(ws_manager.broadcast({"type": "ORG_A_CONFIDENTIAL", "data": "123"}, org_id=str(self.org_a.id)))
                
                # ws_a receives it
                msg_a = ws_a.receive_json()
                assert msg_a["type"] == "ORG_A_CONFIDENTIAL"

                # Send ping to ws_b to verify it did not receive ORG_A_CONFIDENTIAL
                ws_b.send_text("PING")
                pong_b = ws_b.receive_text()
                assert pong_b == "PONG"

    def test_10_production_fails_closed_when_redis_unavailable(self):
        """
        Production environment MUST fail closed if Redis is unavailable or unconfigured.
        In-memory fallback is strictly prohibited in production.
        """
        from unittest.mock import patch
        from config import settings

        prod_manager = WebSocketTicketManager()
        prod_manager._redis_client = None
        prod_manager._redis_checked = True

        with patch.object(settings, "ENVIRONMENT", "production"):
            # 1. Issue ticket must raise RuntimeError in production without Redis
            with pytest.raises(RuntimeError, match="Production environment requires shared Redis ticket storage"):
                prod_manager.issue_ticket(
                    user_id=str(self.user_a.id),
                    org_id=str(self.org_a.id),
                    role="USER"
                )

            # 2. Consume ticket must fail closed and return None
            test_token = security.create_access_token({"ticket_id": "fake_id", "token_type": "ws_ticket", "sub": str(self.user_a.id)})
            consumed = prod_manager.consume_ticket(test_token)
            assert consumed is None, "Production without Redis must fail closed on ticket redemption"

            # 3. HTTP endpoint /auth/ws-ticket returns 503 Service Unavailable
            with patch("ws_manager.ws_ticket_manager", prod_manager):
                headers = {"Authorization": f"Bearer {self.token_user_a}"}
                res = client.post("/api/v1/auth/ws-ticket", headers=headers)
                assert res.status_code == 503
                assert "Distributed session storage unavailable in production" in res.json()["detail"]
