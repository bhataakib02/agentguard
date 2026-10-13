"""
Phase 4 & Phase 6D: Tenant-Isolated WebSocket Connection Manager
Supports organization-scoped event streaming, optional Redis Pub/Sub multi-node broadcasting,
and graceful degradation to single-node in-memory delivery.
SUPER_ADMIN receives platform-wide events. Normal tenant users receive only their organization's events.
"""

from typing import List, Dict, Optional, Any
from fastapi import WebSocket
import json
import logging
from config import settings

logger = logging.getLogger("agentguard.ws_manager")


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        # Map websocket to org_id for tenant filtering
        self._org_map: Dict[int, Optional[str]] = {}
        # Map websocket to role for SUPER_ADMIN detection
        self._role_map: Dict[int, str] = {}
        # Map websocket to authenticated user_id
        self._user_map: Dict[int, Optional[str]] = {}
        self._redis_client = None
        self._redis_checked = False

    def _get_redis(self):
        if not self._redis_checked:
            self._redis_checked = True
            if settings.REDIS_URL:
                try:
                    import redis
                    r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1.0, socket_timeout=1.0)
                    r.ping()
                    self._redis_client = r
                    logger.info("[ConnectionManager] Connected to Redis Pub/Sub for distributed WebSockets")
                except Exception as e:
                    logger.info(f"[ConnectionManager] Redis Pub/Sub unavailable ({type(e).__name__}); running in SINGLE_NODE mode.")
                    self._redis_client = None
        return self._redis_client

    def get_status(self) -> Dict[str, Any]:
        """
        Reports WebSocket infrastructure state without exposing credentials.
        """
        r = self._get_redis()
        mode = "REDIS_DISTRIBUTED" if r is not None else "SINGLE_NODE"
        return {
            "mode": mode,
            "redis_pubsub": r is not None,
            "active_connections": len(self.active_connections),
            "status": "HEALTHY"
        }

    async def connect(
        self,
        websocket: WebSocket,
        org_id: Optional[str] = None,
        role: str = "USER",
        user_id: Optional[str] = None
    ):
        await websocket.accept()
        self.active_connections.append(websocket)
        ws_id = id(websocket)
        self._org_map[ws_id] = str(org_id) if org_id else None
        self._role_map[ws_id] = role
        self._user_map[ws_id] = str(user_id) if user_id else None

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        ws_id = id(websocket)
        self._org_map.pop(ws_id, None)
        self._role_map.pop(ws_id, None)
        self._user_map.pop(ws_id, None)

    async def disconnect_user(self, user_id: str):
        """Disconnects all active connections belonging to a user (e.g. upon suspension or logout)."""
        target_uid = str(user_id)
        for ws in list(self.active_connections):
            if self._user_map.get(id(ws)) == target_uid:
                try:
                    await ws.close(code=1008, reason="User session revoked or suspended")
                except Exception:
                    pass
                self.disconnect(ws)

    async def disconnect_organization(self, org_id: str):
        """Disconnects all active connections belonging to an organization (e.g. upon org suspension)."""
        target_oid = str(org_id)
        for ws in list(self.active_connections):
            if self._org_map.get(id(ws)) == target_oid:
                try:
                    await ws.close(code=1008, reason="Organization suspended")
                except Exception:
                    pass
                self.disconnect(ws)

    async def broadcast(self, message: dict, org_id: Optional[str] = None):
        """
        Broadcasts a message with strict tenant isolation.
        If org_id is specified:
          - Only connections belonging to that exact organization or authenticated SUPER_ADMIN receive the message.
        If org_id is None (platform-wide event):
          - Only authenticated SUPER_ADMIN connections receive the message.
        Also publishes to the appropriate Redis channel if Redis is active.
        """
        target_org_str = str(org_id) if org_id is not None else None

        # 1. Local delivery to active connections
        for connection in list(self.active_connections):
            try:
                ws_id = id(connection)
                conn_org = self._org_map.get(ws_id)
                conn_role = self._role_map.get(ws_id, "USER")

                if target_org_str is not None:
                    # Tenant-scoped event: deliver to matching tenant or SUPER_ADMIN
                    if conn_role == "SUPER_ADMIN" or (conn_org and str(conn_org) == target_org_str):
                        await connection.send_json(message)
                else:
                    # Platform-wide event: deliver ONLY to SUPER_ADMIN
                    if conn_role == "SUPER_ADMIN":
                        await connection.send_json(message)
            except Exception:
                pass

        # 2. Redis Pub/Sub publishing for cross-node replication (if available)
        r = self._get_redis()
        if r:
            try:
                channel = f"agentguard:org:{target_org_str}" if target_org_str else "agentguard:platform"
                r.publish(channel, json.dumps(message, default=str))
            except Exception as e:
                logger.warning(f"[ConnectionManager] Redis publish failed: {e}")

    async def send_tenant_event(self, org_id: str, event_type: str, data: dict):
        """
        Sends a tenant-scoped event. Only connections for the specified org or SUPER_ADMIN
        receive the event.
        """
        message = {
            "type": event_type,
            "organization_id": str(org_id),
            **data
        }
        await self.broadcast(message, org_id=str(org_id))


manager = ConnectionManager()
ws_manager = manager


import threading
import time
import uuid
from jose import jwt, JWTError


class WebSocketTicketManager:
    """
    Manages short-lived, single-use authenticated tickets for WebSocket handshakes.
    Eliminates persistent bearer tokens from WebSocket query strings.
    Supports multi-instance distributed deployments via Redis, with automatic
    thread-safe in-memory fallback when running in single-instance mode.
    """
    def __init__(self, ttl_seconds: int = 60, redis_client=None):
        self.ttl_seconds = ttl_seconds
        self._active_tickets: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._redis_client = redis_client
        self._redis_checked = False

    def _get_redis(self):
        if self._redis_client is not None:
            return self._redis_client
        if not self._redis_checked:
            self._redis_checked = True
            if settings.REDIS_URL:
                try:
                    import redis
                    r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=1.0, socket_timeout=1.0)
                    r.ping()
                    self._redis_client = r
                    logger.info("[WebSocketTicketManager] Connected to Redis for distributed ticket store (MULTI_INSTANCE mode)")
                except Exception as e:
                    logger.info(f"[WebSocketTicketManager] Redis unavailable ({type(e).__name__}); using in-memory store (SINGLE_INSTANCE mode).")
                    self._redis_client = None
        return self._redis_client

    def get_mode(self) -> str:
        r = self._get_redis()
        return "REDIS_DISTRIBUTED" if r is not None else "SINGLE_INSTANCE_IN_MEMORY"

    def _is_production(self) -> bool:
        env = getattr(settings, "ENVIRONMENT", "production").lower()
        return env == "production"

    def issue_ticket(
        self,
        user_id: str,
        org_id: Optional[str],
        role: str,
        email: Optional[str] = None,
        ttl_seconds: Optional[float] = None
    ) -> str:
        now = time.time()
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
        exp = now + ttl
        ticket_id = str(uuid.uuid4())

        r = self._get_redis()
        if self._is_production():
            if r is None:
                raise RuntimeError(
                    "[AgentGuard Security Error] Production environment requires shared Redis ticket storage for multi-instance WebSocket security. "
                    "In-memory fallback is strictly prohibited in production."
                )
            try:
                # Distributed store: store ticket ID with TTL in Redis
                r.set(f"agentguard:ws_ticket:{ticket_id}", "ACTIVE", ex=max(int(ttl), 1))
            except Exception as e:
                logger.error(f"[WebSocketTicketManager] Production Redis ticket storage write failure: {e}")
                raise RuntimeError(
                    f"[AgentGuard Security Error] Failed to persist distributed WebSocket ticket in Redis: {e}"
                )
        else:
            if r is not None:
                try:
                    r.set(f"agentguard:ws_ticket:{ticket_id}", "ACTIVE", ex=max(int(ttl), 1))
                except Exception as e:
                    logger.warning(f"[WebSocketTicketManager] Redis set ticket failed in dev: {e}; using local memory.")
                    with self._lock:
                        self._cleanup_expired(now)
                        self._active_tickets[ticket_id] = exp
            else:
                with self._lock:
                    self._cleanup_expired(now)
                    self._active_tickets[ticket_id] = exp

        payload = {
            "ticket_id": ticket_id,
            "sub": str(user_id),
            "user_id": str(user_id),
            "org_id": str(org_id) if org_id else None,
            "role": role,
            "email": email or "",
            "token_type": "ws_ticket",
            "iat": int(now),
            "exp": int(exp)
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def consume_ticket(self, ticket_token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(ticket_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except JWTError:
            return None

        if payload.get("token_type") != "ws_ticket":
            return None

        ticket_id = payload.get("ticket_id")
        if not ticket_id:
            return None

        now = time.time()
        r = self._get_redis()

        if self._is_production():
            if r is None:
                logger.error(
                    "[AgentGuard Security Error] Production environment requires Redis for ticket redemption. In-memory fallback is disallowed."
                )
                return None
            try:
                # Atomic single-use redemption in Redis
                deleted = r.delete(f"agentguard:ws_ticket:{ticket_id}")
                if deleted != 1:
                    # Already consumed or expired
                    return None
            except Exception as e:
                logger.error(f"[WebSocketTicketManager] Production Redis ticket redemption error: {e}")
                return None
        else:
            if r is not None:
                try:
                    deleted = r.delete(f"agentguard:ws_ticket:{ticket_id}")
                    if deleted == 1:
                        return payload
                except Exception as e:
                    logger.warning(f"[WebSocketTicketManager] Redis delete ticket error in dev: {e}")

            with self._lock:
                self._cleanup_expired(now)
                if ticket_id not in self._active_tickets:
                    return None
                exp = self._active_tickets.pop(ticket_id)
                if now > exp:
                    return None

        return payload

    def _cleanup_expired(self, now: float):
        expired = [tid for tid, exp in self._active_tickets.items() if exp < now]
        for tid in expired:
            del self._active_tickets[tid]


ws_ticket_manager = WebSocketTicketManager()

