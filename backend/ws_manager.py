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
