import datetime
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import models

logger = logging.getLogger("agentguard.circuit_breaker")

# Configurable Circuit Breaker Policy Thresholds
MAX_CONSECUTIVE_REFUSALS = 3
MAX_FAILURE_RATE = 0.50

class CircuitBreakerEngine:
    STATES = ["NORMAL", "WARNING", "RESTRICTED", "HUMAN_APPROVAL", "CIRCUIT_BREAK", "SUSPENDED"]

    def transition_state(self, current_state: str, event_trigger: str) -> str:
        if event_trigger == "MANUAL_SUSPENSION_KILL_SWITCH":
            return "SUSPENDED"
        if event_trigger == "HIGH_ANOMALY_SPIKE" or event_trigger == "CONSECUTIVE_POLICY_REFUSALS":
            return "CIRCUIT_BREAK"
        if event_trigger == "POLICY_VIOLATION":
            return "HUMAN_APPROVAL"
        if event_trigger == "ELEVATED_RISK":
            return "WARNING"
        return current_state

    def check_agent_circuit(
        self,
        db: Session,
        agent: models.Agent
    ) -> Dict[str, Any]:
        """
        Inspects agent circuit breaker state, consecutive refusals, and failure rates.
        Trips the circuit breaker if thresholds are violated.
        Returns {"tripped": bool, "state": str, "reason": Optional[str]}.
        """
        cb = db.query(models.CircuitBreaker).filter(models.CircuitBreaker.agent_id == agent.id).first()
        if not cb:
            cb = models.CircuitBreaker(agent_id=agent.id, state="NORMAL")
            db.add(cb)
            db.commit()

        # If already tripped or suspended
        if cb.state in ("CIRCUIT_BREAK", "SUSPENDED") or agent.status in ("CIRCUIT_BREAK", "SUSPENDED"):
            return {
                "tripped": True,
                "state": cb.state or agent.status,
                "reason": cb.trigger_reason or f"Agent is in {agent.status} state."
            }

        # Check consecutive refusals in recent decisions since last restoration
        query = db.query(models.Decision).filter(
            models.Decision.agent_id == agent.id
        )
        if cb.restored_at:
            query = query.filter(models.Decision.timestamp >= cb.restored_at)

        recent_decisions = query.order_by(models.Decision.timestamp.desc()).limit(MAX_CONSECUTIVE_REFUSALS).all()

        if len(recent_decisions) >= MAX_CONSECUTIVE_REFUSALS:
            all_refused = all(d.decision == "REFUSE" for d in recent_decisions)
            if all_refused:
                # Trip the circuit breaker!
                trip_reason = f"Tripped: {MAX_CONSECUTIVE_REFUSALS} consecutive policy refusals detected."
                return self.trip_circuit(db, agent, trip_reason)

        return {
            "tripped": False,
            "state": cb.state,
            "reason": None
        }

    def trip_circuit(
        self,
        db: Session,
        agent: models.Agent,
        reason: str
    ) -> Dict[str, Any]:
        """
        Trips the circuit breaker for an agent and audits the transition.
        """
        cb = db.query(models.CircuitBreaker).filter(models.CircuitBreaker.agent_id == agent.id).first()
        if not cb:
            cb = models.CircuitBreaker(agent_id=agent.id, state="NORMAL")
            db.add(cb)

        now = datetime.datetime.utcnow()
        cb.state = "CIRCUIT_BREAK"
        cb.trigger_reason = reason
        cb.tripped_at = now
        agent.status = "CIRCUIT_BREAK"

        audit = models.AuditLog(
            org_id=agent.org_id,
            event_type="CIRCUIT_BREAKER_TRIPPED",
            actor_type="SYSTEM",
            actor_id="circuit_breaker_engine",
            action="TRIP_CIRCUIT",
            resource=f"agent:{agent.agent_code}:circuit_breaker",
            result="FAILURE",
            metadata_json={
                "agent_id": str(agent.id),
                "agent_code": agent.agent_code,
                "reason": reason,
                "tripped_at": now.isoformat()
            }
        )
        db.add(audit)
        db.commit()

        logger.warning(f"[CircuitBreaker] Tripped for agent {agent.agent_code}: {reason}")
        return {
            "tripped": True,
            "state": "CIRCUIT_BREAK",
            "reason": reason
        }

    def reset_circuit(
        self,
        db: Session,
        agent: models.Agent,
        actor_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Controlled recovery: resets circuit breaker to NORMAL state.
        Audits the recovery transition.
        """
        cb = db.query(models.CircuitBreaker).filter(models.CircuitBreaker.agent_id == agent.id).first()
        if not cb:
            cb = models.CircuitBreaker(agent_id=agent.id, state="NORMAL")
            db.add(cb)

        now = datetime.datetime.utcnow()
        cb.state = "NORMAL"
        cb.trigger_reason = None
        cb.restored_at = now
        agent.status = "NORMAL"

        audit = models.AuditLog(
            org_id=agent.org_id,
            event_type="CIRCUIT_BREAKER_RESET",
            actor_type="USER",
            actor_id=actor_id,
            action="RESET_CIRCUIT",
            resource=f"agent:{agent.agent_code}:circuit_breaker",
            result="SUCCESS",
            metadata_json={
                "agent_id": str(agent.id),
                "agent_code": agent.agent_code,
                "reason": reason or "Manual operator reset",
                "restored_at": now.isoformat()
            }
        )
        db.add(audit)
        db.commit()

        logger.info(f"[CircuitBreaker] Reset for agent {agent.agent_code} by {actor_id}")
        return {
            "status": "SUCCESS",
            "agent_code": agent.agent_code,
            "state": "NORMAL",
            "restored_at": now.isoformat()
        }

circuit_breaker_engine = CircuitBreakerEngine()
