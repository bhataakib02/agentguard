import uuid, datetime
from typing import Dict, Any

class CapabilityEngine:
    def issue_token(
        self,
        agent_id: str,
        capability_name: str,
        scope: str,
        amount_limit: float = 0.0,
        ttl_seconds: int = 60
    ) -> Dict[str, Any]:
        token_code = f"tok_{uuid.uuid4().hex[:8]}_{capability_name.replace(':', '_')}"
        issued_at = datetime.datetime.utcnow()
        expires_at = issued_at + datetime.timedelta(seconds=ttl_seconds)

        return {
            "token_code": token_code,
            "agent_id": agent_id,
            "capability_name": capability_name,
            "scope": scope,
            "amount_limit": amount_limit,
            "issued_at": issued_at,
            "expires_at": expires_at
        }

capability_engine = CapabilityEngine()
