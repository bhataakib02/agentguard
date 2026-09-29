"""
Runtime Telemetry Service for AgentGuard Phase 4
Handles agent execution tracking, token/cost accounting, budget governance,
risk signal generation, and circuit breaker state management.
"""

import datetime
import uuid
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import models

logger = logging.getLogger("agentguard.runtime_telemetry")


def calculate_cost(
    db: Session,
    provider: Optional[str],
    model_name: Optional[str],
    input_tokens: int,
    output_tokens: int
) -> Dict[str, Any]:
    """
    Calculates estimated cost using configurable ModelPricing records.
    Returns cost and whether pricing was configured.
    """
    if not provider or not model_name:
        return {"estimated_cost": 0.0, "pricing_configured": False, "currency": "USD"}

    pricing = db.query(models.ModelPricing).filter(
        models.ModelPricing.provider == provider.lower(),
        models.ModelPricing.model == model_name.lower(),
        models.ModelPricing.active == True
    ).order_by(models.ModelPricing.effective_from.desc()).first()

    if not pricing:
        return {"estimated_cost": 0.0, "pricing_configured": False, "currency": "USD"}

    input_cost = (input_tokens / 1000.0) * pricing.input_cost_per_1k
    output_cost = (output_tokens / 1000.0) * pricing.output_cost_per_1k
    total_cost = round(input_cost + output_cost, 6)

    return {
        "estimated_cost": total_cost,
        "pricing_configured": True,
        "currency": pricing.currency
    }


def record_execution(
    db: Session,
    org_id: str,
    agent_id: str,
    action: str,
    resource: str,
    outcome: str,
    risk_score: int,
    policy_decision: Optional[str] = None,
    policy_id: Optional[str] = None,
    policy_rule_id: Optional[str] = None,
    decision_id: Optional[str] = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    latency_ms: int = 0,
    status: str = "COMPLETED",
    error_code: Optional[str] = None,
    request_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> models.AgentExecution:
    """
    Records a single agent execution event with telemetry data.
    Calculates cost from configurable pricing. Updates budget counters.
    """
    total_tokens = input_tokens + output_tokens
    execution_id = str(uuid.uuid4())

    # Cost calculation
    cost_info = calculate_cost(db, provider, model_name, input_tokens, output_tokens)

    # Sanitize metadata — strip any sensitive-looking keys
    safe_metadata = {}
    if metadata:
        sensitive_patterns = {"password", "secret", "token", "key", "credential", "api_key", "auth"}
        for k, v in metadata.items():
            if not any(pat in k.lower() for pat in sensitive_patterns):
                safe_metadata[k] = v

    execution = models.AgentExecution(
        org_id=org_id,
        agent_id=agent_id,
        request_id=request_id or str(uuid.uuid4()),
        execution_id=execution_id,
        action=action,
        resource=resource,
        outcome=outcome,
        risk_score=risk_score,
        policy_decision=policy_decision,
        policy_id=policy_id,
        policy_rule_id=policy_rule_id,
        decision_id=decision_id,
        input_token_count=input_tokens,
        output_token_count=output_tokens,
        total_token_count=total_tokens,
        estimated_cost=cost_info["estimated_cost"],
        provider=provider,
        model_name=model_name,
        latency_ms=latency_ms,
        status=status,
        error_code=error_code,
        metadata_json=safe_metadata
    )

    db.add(execution)
    db.commit()
    db.refresh(execution)

    # Update budget counters
    _update_budget_counters(
        db, org_id, agent_id,
        tokens=total_tokens,
        cost=cost_info["estimated_cost"]
    )

    return execution


def _update_budget_counters(
    db: Session,
    org_id: str,
    agent_id: str,
    tokens: int,
    cost: float
):
    """Updates agent budget config counters after an execution."""
    # Agent-level budget config
    budget = db.query(models.AgentBudgetConfig).filter(
        models.AgentBudgetConfig.org_id == org_id,
        models.AgentBudgetConfig.agent_id == agent_id
    ).first()

    if not budget:
        # Check org-level default
        budget = db.query(models.AgentBudgetConfig).filter(
            models.AgentBudgetConfig.org_id == org_id,
            models.AgentBudgetConfig.agent_id == None
        ).first()

    if not budget:
        return

    now = datetime.datetime.utcnow()

    # Daily reset check
    if budget.last_reset_daily and (now - budget.last_reset_daily).days >= 1:
        budget.current_daily_tokens = 0
        budget.current_daily_cost = 0.0
        budget.current_daily_executions = 0
        budget.last_reset_daily = now

    # Monthly reset check
    if budget.last_reset_monthly and (now - budget.last_reset_monthly).days >= 30:
        budget.current_monthly_tokens = 0
        budget.current_monthly_cost = 0.0
        budget.last_reset_monthly = now

    # Increment counters
    budget.current_daily_tokens = (budget.current_daily_tokens or 0) + tokens
    budget.current_monthly_tokens = (budget.current_monthly_tokens or 0) + tokens
    budget.current_daily_cost = round((budget.current_daily_cost or 0.0) + cost, 6)
    budget.current_monthly_cost = round((budget.current_monthly_cost or 0.0) + cost, 6)
    budget.current_daily_executions = (budget.current_daily_executions or 0) + 1

    # Evaluate budget state
    new_state = evaluate_budget_state(budget)
    old_state = budget.budget_state
    budget.budget_state = new_state

    db.commit()

    # Generate risk signal if state changed to WARNING or EXCEEDED
    if new_state != old_state and new_state in ("WARNING", "EXCEEDED"):
        _create_budget_risk_signal(db, budget, new_state, org_id, agent_id)


def evaluate_budget_state(budget: models.AgentBudgetConfig) -> str:
    """Evaluates budget state based on configured thresholds."""
    warn_pct = budget.warning_threshold_pct or 80.0
    exceed_pct = budget.exceeded_threshold_pct or 100.0

    # Check each limit dimension
    checks = []

    if budget.daily_token_limit and budget.daily_token_limit > 0:
        pct = (budget.current_daily_tokens or 0) / budget.daily_token_limit * 100.0
        checks.append(pct)

    if budget.monthly_token_limit and budget.monthly_token_limit > 0:
        pct = (budget.current_monthly_tokens or 0) / budget.monthly_token_limit * 100.0
        checks.append(pct)

    if budget.daily_cost_limit and budget.daily_cost_limit > 0:
        pct = (budget.current_daily_cost or 0) / budget.daily_cost_limit * 100.0
        checks.append(pct)

    if budget.monthly_cost_limit and budget.monthly_cost_limit > 0:
        pct = (budget.current_monthly_cost or 0) / budget.monthly_cost_limit * 100.0
        checks.append(pct)

    if budget.execution_count_limit and budget.execution_count_limit > 0:
        pct = (budget.current_daily_executions or 0) / budget.execution_count_limit * 100.0
        checks.append(pct)

    if not checks:
        return "NORMAL"

    max_pct = max(checks)

    if max_pct >= exceed_pct:
        return "EXCEEDED"
    elif max_pct >= warn_pct:
        return "WARNING"
    return "NORMAL"


def _create_budget_risk_signal(
    db: Session,
    budget: models.AgentBudgetConfig,
    state: str,
    org_id: str,
    agent_id: Optional[str]
):
    """Creates a risk signal when budget threshold is breached."""
    severity = "HIGH" if state == "EXCEEDED" else "MEDIUM"
    signal_type = "BUDGET_EXCEEDED" if state == "EXCEEDED" else "BUDGET_WARNING"

    signal = models.RuntimeRiskSignal(
        org_id=org_id,
        agent_id=agent_id,
        signal_type=signal_type,
        severity=severity,
        title=f"Agent Budget {state}",
        description=f"Budget threshold reached: daily_tokens={budget.current_daily_tokens}, "
                    f"daily_cost={budget.current_daily_cost}, "
                    f"monthly_cost={budget.current_monthly_cost}",
        evidence_json={
            "budget_state": state,
            "current_daily_tokens": budget.current_daily_tokens,
            "current_monthly_tokens": budget.current_monthly_tokens,
            "current_daily_cost": budget.current_daily_cost,
            "current_monthly_cost": budget.current_monthly_cost,
            "daily_token_limit": budget.daily_token_limit,
            "monthly_token_limit": budget.monthly_token_limit,
            "daily_cost_limit": budget.daily_cost_limit,
            "monthly_cost_limit": budget.monthly_cost_limit,
        },
        status="ACTIVE"
    )
    db.add(signal)

    # Audit log
    audit = models.AuditLog(
        event_type="BUDGET_THRESHOLD_BREACH",
        actor_type="SYSTEM",
        actor_id="BUDGET_SERVICE",
        action=f"Budget {state} for agent {agent_id or 'org-default'}",
        resource=f"budget_config:{budget.id}",
        result=state,
        metadata_json={
            "org_id": str(org_id),
            "agent_id": str(agent_id) if agent_id else None,
            "budget_state": state
        }
    )
    db.add(audit)
    db.commit()

    # Auto-suspend if configured
    if state == "EXCEEDED" and budget.auto_suspend_on_exceeded and agent_id:
        _auto_suspend_agent(db, agent_id, org_id, "Budget exceeded — auto-suspension triggered")


def _auto_suspend_agent(db: Session, agent_id: str, org_id: str, reason: str):
    """Suspends an agent and updates circuit breaker due to budget/risk policy."""
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if agent and agent.status != "SUSPENDED":
        agent.status = "SUSPENDED"
        cb = db.query(models.CircuitBreaker).filter(models.CircuitBreaker.agent_id == agent_id).first()
        if cb:
            cb.state = "SUSPENDED"
            cb.trigger_reason = reason
            cb.tripped_at = datetime.datetime.utcnow()
        db.commit()

        # Create notification
        try:
            from services.notification_service import notification_service
            notification_service.notify_governance_event(
                db=db,
                org_id=str(org_id),
                event_type="agent.suspended",
                resource_type="agent",
                resource_id=str(agent_id),
                title="Agent Auto-Suspended",
                message=f"Agent {agent.name} ({agent.agent_code}) has been automatically suspended: {reason}",
                data={"agent_id": str(agent_id), "agent_code": agent.agent_code, "reason": reason},
                severity="CRITICAL"
            )
        except Exception as e:
            logger.warning(f"Failed to send suspension notification: {e}")


def check_budget_before_execution(db: Session, org_id: str, agent_id: str) -> Dict[str, Any]:
    """
    Pre-execution budget check. Returns whether execution should proceed.
    """
    # Agent-level first
    budget = db.query(models.AgentBudgetConfig).filter(
        models.AgentBudgetConfig.org_id == org_id,
        models.AgentBudgetConfig.agent_id == agent_id
    ).first()

    if not budget:
        budget = db.query(models.AgentBudgetConfig).filter(
            models.AgentBudgetConfig.org_id == org_id,
            models.AgentBudgetConfig.agent_id == None
        ).first()

    if not budget:
        return {"allowed": True, "budget_state": "UNCONFIGURED", "reason": None}

    state = evaluate_budget_state(budget)

    if state == "EXCEEDED":
        return {
            "allowed": False,
            "budget_state": "EXCEEDED",
            "reason": "Agent budget limit exceeded. Execution blocked by cost governance policy."
        }

    return {"allowed": True, "budget_state": state, "reason": None}


def detect_risk_signals(db: Session, org_id: str, agent_id: str, window_hours: int = 24):
    """
    Detects deterministic runtime risk signals for an agent based on recent telemetry.
    """
    now = datetime.datetime.utcnow()
    window_start = now - datetime.timedelta(hours=window_hours)

    executions = db.query(models.AgentExecution).filter(
        models.AgentExecution.org_id == org_id,
        models.AgentExecution.agent_id == agent_id,
        models.AgentExecution.timestamp >= window_start
    )

    total = executions.count()
    if total == 0:
        return []

    signals = []

    # 1. Repeated refusals (>5 in window)
    refusals = executions.filter(models.AgentExecution.policy_decision == "REFUSE").count()
    if refusals >= 5:
        signals.append({
            "signal_type": "REPEATED_REFUSALS",
            "severity": "HIGH",
            "title": "Repeated Policy Refusals Detected",
            "description": f"Agent has received {refusals} policy refusals in the last {window_hours}h.",
            "evidence": {"refusal_count": refusals, "window_hours": window_hours, "total_executions": total}
        })

    # 2. High-risk volume (>50% of decisions have risk_score > 60)
    high_risk = executions.filter(models.AgentExecution.risk_score > 60).count()
    if total >= 3 and high_risk / total > 0.5:
        signals.append({
            "signal_type": "HIGH_RISK_VOLUME",
            "severity": "HIGH",
            "title": "Abnormal High-Risk Execution Volume",
            "description": f"{high_risk}/{total} executions had risk score >60 in last {window_hours}h.",
            "evidence": {"high_risk_count": high_risk, "total_count": total, "ratio": round(high_risk / total, 2)}
        })

    # 3. Repeated errors (>3 errors in window)
    errors = executions.filter(models.AgentExecution.status == "ERROR").count()
    if errors >= 3:
        signals.append({
            "signal_type": "REPEATED_ERRORS",
            "severity": "MEDIUM",
            "title": "Repeated Execution Errors",
            "description": f"Agent encountered {errors} execution errors in last {window_hours}h.",
            "evidence": {"error_count": errors, "window_hours": window_hours}
        })

    # 4. Abnormal request volume (>100 executions in 24h for a single agent)
    if total > 100:
        signals.append({
            "signal_type": "ABNORMAL_VOLUME",
            "severity": "MEDIUM",
            "title": "Abnormal Request Volume",
            "description": f"Agent executed {total} actions in last {window_hours}h — exceeds normal threshold.",
            "evidence": {"execution_count": total, "window_hours": window_hours}
        })

    # Persist new signals (avoid duplicates for same type within the window)
    for sig in signals:
        existing = db.query(models.RuntimeRiskSignal).filter(
            models.RuntimeRiskSignal.org_id == org_id,
            models.RuntimeRiskSignal.agent_id == agent_id,
            models.RuntimeRiskSignal.signal_type == sig["signal_type"],
            models.RuntimeRiskSignal.status == "ACTIVE",
            models.RuntimeRiskSignal.timestamp >= window_start
        ).first()

        if not existing:
            new_signal = models.RuntimeRiskSignal(
                org_id=org_id,
                agent_id=agent_id,
                signal_type=sig["signal_type"],
                severity=sig["severity"],
                title=sig["title"],
                description=sig["description"],
                evidence_json=sig["evidence"],
                status="ACTIVE"
            )
            db.add(new_signal)

    db.commit()
    return signals
