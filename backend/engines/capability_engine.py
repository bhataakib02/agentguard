import uuid
import datetime
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import models

logger = logging.getLogger("agentguard.capability_engine")

class CapabilityEngine:
    """
    Cryptographic & Policy-Bounded Capability Token Engine.
    Handles token generation, scope/amount verification, replay prevention,
    and single-use lifecycle enforcement.
    """

    def issue_token(
        self,
        agent_id: str,
        capability_name: str,
        scope: str,
        amount_limit: float = 0.0,
        ttl_seconds: int = 60
    ) -> Dict[str, Any]:
        clean_cap = capability_name.replace(":", "_").replace(".", "_")
        token_code = f"tok_{uuid.uuid4().hex[:12]}_{clean_cap}"
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

    def validate_token(
        self,
        db: Session,
        token_code: str,
        agent: models.Agent,
        required_capability: Optional[str] = None,
        requested_amount: float = 0.0,
        requested_scope: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authoritatively validates a capability token for a runtime action.
        Verifies agent ownership, active status, expiration, replay (already used),
        capability match, amount limits, and parameter scope.
        """
        if not token_code:
            return {"valid": False, "reason": "No capability token provided."}

        token = db.query(models.CapabilityToken).filter(
            models.CapabilityToken.token_code == token_code
        ).first()

        if not token:
            return {"valid": False, "reason": f"Capability token '{token_code}' not found in registry."}

        # Verify agent ownership
        if str(token.agent_id) != str(agent.id):
            return {"valid": False, "reason": "Capability token was issued to a different agent. Cross-agent token use rejected."}

        # Verify status
        if token.status == "REVOKED":
            return {"valid": False, "reason": "Capability token has been revoked."}

        if token.status == "USED":
            return {"valid": False, "reason": "Capability token has already been consumed (replay prevented)."}

        # Verify expiration
        now = datetime.datetime.utcnow()
        if token.expires_at < now:
            token.status = "EXPIRED"
            db.commit()
            return {"valid": False, "reason": f"Capability token expired on {token.expires_at.isoformat()}."}

        # Verify capability name match if required
        if required_capability:
            norm_token_cap = token.capability_name.lower().replace(":", ".").replace("_", ".")
            norm_req_cap = required_capability.lower().replace(":", ".").replace("_", ".")
            if norm_token_cap != norm_req_cap and norm_token_cap != "*":
                return {
                    "valid": False,
                    "reason": f"Token capability '{token.capability_name}' does not permit requested action '{required_capability}'."
                }

        # Verify amount limit
        if token.amount_limit > 0 and requested_amount > token.amount_limit:
            return {
                "valid": False,
                "reason": f"Requested amount {requested_amount} exceeds capability token limit {token.amount_limit}."
            }

        # Verify scope
        if requested_scope and token.scope != "*":
            if requested_scope not in token.scope:
                return {
                    "valid": False,
                    "reason": f"Target scope '{requested_scope}' is outside token permitted scope '{token.scope}'."
                }

        return {
            "valid": True,
            "token": token,
            "reason": "Capability token verified successfully."
        }

    def consume_token(
        self,
        db: Session,
        token_code: str,
        actor_id: str = "runtime_kernel"
    ) -> bool:
        """
        Marks a capability token as USED upon successful action authorization/execution
        to prevent token replay.
        """
        token = db.query(models.CapabilityToken).filter(
            models.CapabilityToken.token_code == token_code
        ).first()

        if not token:
            return False

        token.status = "USED"
        
        # Look up agent for tenant audit
        agent = db.query(models.Agent).filter(models.Agent.id == token.agent_id).first()
        org_id = agent.org_id if agent else None

        audit = models.AuditLog(
            org_id=org_id,
            event_type="CAPABILITY_USED",
            actor_type="MACHINE",
            actor_id=str(token.agent_id),
            action="CONSUME_CAPABILITY",
            resource=f"capability:{token.token_code}:{token.capability_name}",
            result="SUCCESS",
            metadata_json={
                "agent_id": str(token.agent_id),
                "token_code": token.token_code,
                "capability": token.capability_name,
                "scope": token.scope,
                "consumed_by": actor_id
            }
        )
        db.add(audit)
        db.commit()

        logger.info(f"[CapabilityEngine] Consumed token {token_code} for agent {token.agent_id}")
        return True

capability_engine = CapabilityEngine()
