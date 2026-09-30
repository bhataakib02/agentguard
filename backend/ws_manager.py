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

    async def connect(self, websocket: WebSocket, org_id: Optional[str] = None, role: str = "USER"):
        await websocket.accept()
        self.active_connections.append(websocket)
        ws_id = id(websocket)
        self._org_map[ws_id] = org_id
        self._role_map[ws_id] = role

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        ws_id = id(websocket)
        self._org_map.pop(ws_id, None)
        self._role_map.pop(ws_id, None)

    async def broadcast(self, message: dict, org_id: Optional[str] = None):
        """
        Broadcasts a message. If org_id is specified, only sends to connections
        for that organization or SUPER_ADMIN connections. If org_id is None,
        broadcasts to all (backward compatible).
        Also publishes to Redis channel if Redis is active.
        """
        # 1. Local delivery to active connections
        for connection in list(self.active_connections):
            try:
                ws_id = id(connection)
                conn_org = self._org_map.get(ws_id)
                conn_role = self._role_map.get(ws_id, "USER")

                # If org_id filter is set, only send to matching org or SUPER_ADMIN
                if org_id is not None:
                    if conn_role == "SUPER_ADMIN" or conn_org == org_id:
                        await connection.send_json(message)
                else:
                    # No org filter — broadcast to all
                    await connection.send_json(message)
            except Exception:
                pass

        # 2. Redis Pub/Sub publishing for cross-node replication (if available)
        r = self._get_redis()
        if r:
            try:
                channel = f"agentguard:org:{org_id}" if org_id else "agentguard:events"
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
            "organization_id": org_id,
            **data
        }
        await self.broadcast(message, org_id=org_id)


manager = ConnectionManager()
