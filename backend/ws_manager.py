"""
Phase 4: Tenant-Isolated WebSocket Connection Manager
Supports organization-scoped event streaming. SUPER_ADMIN receives platform-wide events.
Normal tenant users receive only their organization's events.
"""

from typing import List, Dict, Optional
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger("agentguard.ws_manager")


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        # Map websocket to org_id for tenant filtering
        self._org_map: Dict[int, Optional[str]] = {}
        # Map websocket to role for SUPER_ADMIN detection
        self._role_map: Dict[int, str] = {}

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
        """
        for connection in self.active_connections:
            try:
                ws_id = id(connection)
                conn_org = self._org_map.get(ws_id)
                conn_role = self._role_map.get(ws_id, "USER")

                # If org_id filter is set, only send to matching org or SUPER_ADMIN
                if org_id is not None:
                    if conn_role == "SUPER_ADMIN" or conn_org == org_id:
                        await connection.send_json(message)
                else:
                    # No org filter — broadcast to all (legacy behavior)
                    await connection.send_json(message)
            except Exception:
                pass

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
