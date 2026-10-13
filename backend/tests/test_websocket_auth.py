"""
Dedicated test suite for WebSocket Authentication, Single-Use Ticket Exchange,
Session Revocation, and Multi-Tenant Broadcast Isolation.
Verifies requirement B3.
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
from ws_manager import ws_ticket_manager, ws_manager

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

        # Reusing the ticket must fail immediately
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect(f"/ws?ticket={ticket}"):
                pass
        assert excinfo.value.code == 1008

    def test_04_ws_revoked_session_rejected(self):
        """If a session record is marked revoked in the database, WS connection is rejected."""
        revoked_token = security.create_access_token(
            self.user_a.id,
            email=self.user_a.email,
            role=self.user_a.role
        )
        
        # Add revoked session record to DB
        session_rec = models.Session(
            user_id=self.user_a.id,
            token=revoked_token,
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            revoked=True  # Explicitly revoked
        )
        self.db.add(session_rec)
        self.db.commit()

        try:
            with pytest.raises(WebSocketDisconnect) as excinfo:
                with client.websocket_connect(f"/ws?token={revoked_token}"):
                    pass
            assert excinfo.value.code == 1008
        finally:
            self.db.delete(session_rec)
            self.db.commit()

    def test_05_ws_suspended_user_rejected(self):
        """Suspended user token is rejected with 1008."""
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect(f"/ws?token={self.token_user_suspended}"):
                pass
        assert excinfo.value.code == 1008

    def test_06_cross_tenant_broadcast_isolation(self):
        """Messages broadcast to Org A must never be received by Org B client."""
        import asyncio
        with client.websocket_connect(f"/ws?token={self.token_user_a}") as ws_a:
            with client.websocket_connect(f"/ws?token={self.token_user_b}") as ws_b:
                # Broadcast only to Org A
                asyncio.run(ws_manager.broadcast({"type": "ORG_A_CONFIDENTIAL", "data": "123"}, org_id=str(self.org_a.id)))
                
                # ws_a receives it
                msg_a = ws_a.receive_json()
                assert msg_a["type"] == "ORG_A_CONFIDENTIAL"

                # Send ping to ws_b to verify it did not receive ORG_A_CONFIDENTIAL
                ws_b.send_text("PING")
                pong_b = ws_b.receive_text()
                assert pong_b == "PONG"
