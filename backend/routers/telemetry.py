"""
Phase 4: Runtime Telemetry & Cost Governance API Router
Tenant-isolated endpoints for agent execution telemetry, token usage, cost analytics,
budget management, risk signals, circuit breaker status, and webhook delivery health.
"""

import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from database import get_db
from core.deps import get_current_user
import models
from services.runtime_telemetry_service import (
    check_budget_before_execution,
    detect_risk_signals,
    evaluate_budget_state,
)

router = APIRouter(prefix="/telemetry", tags=["Runtime Telemetry & Cost Governance"])


def _resolve_tenant_org_id(current_user: models.User, org_id_param: Optional[str] = None) -> Optional[str]:
    """Strict tenant resolution. Normal users locked to own org."""
    if current_user.role != "SUPER_ADMIN":
        if org_id_param and str(org_id_param) != str(current_user.org_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Cannot access telemetry for another organization"
            )
        return str(current_user.org_id)
    return org_id_param if org_id_param and org_id_param != "ALL" else None


# ==================== EXECUTION TELEMETRY ====================

@router.get("/executions")
def list_executions(
    agent_id: Optional[str] = Query(None),
    range: str = Query("24h"),
    limit: int = Query(100, le=500),
    org_id: Optional[str] = Query(None),
    x_org_context: Optional[str] = Header(None, alias="X-Organization-Context"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_org_id = _resolve_tenant_org_id(current_user, org_id or x_org_context)

    now = datetime.datetime.utcnow()
    range_map = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
    days = range_map.get(range, 1)
    since = now - datetime.timedelta(days=days)

    q = db.query(models.AgentExecution).filter(models.AgentExecution.timestamp >= since)
    if target_org_id:
        q = q.filter(models.AgentExecution.org_id == target_org_id)
    if agent_id:
        q = q.filter(models.AgentExecution.agent_id == agent_id)

    executions = q.order_by(desc(models.AgentExecution.timestamp)).limit(limit).all()

    return {
        "range": range,
        "count": len(executions),
        "executions": [
            {
                "id": str(e.id),
                "agent_id": str(e.agent_id),
                "execution_id": e.execution_id,
                "action": e.action,
                "resource": e.resource,
                "outcome": e.outcome,
                "risk_score": e.risk_score,
                "policy_decision": e.policy_decision,
                "input_tokens": e.input_token_count,
                "output_tokens": e.output_token_count,
                "total_tokens": e.total_token_count,
                "estimated_cost": e.estimated_cost,
                "provider": e.provider,
                "model_name": e.model_name,
                "latency_ms": e.latency_ms,
                "status": e.status,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None
            }
            for e in executions
        ]
    }


# ==================== TOKEN & COST ANALYTICS ====================

@router.get("/token-usage")
def get_token_usage(
    range: str = Query("30d"),
    agent_id: Optional[str] = Query(None),
    org_id: Optional[str] = Query(None),
    x_org_context: Optional[str] = Header(None, alias="X-Organization-Context"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_org_id = _resolve_tenant_org_id(current_user, org_id or x_org_context)

    now = datetime.datetime.utcnow()
    range_map = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
    days = range_map.get(range, 30)
    since = now - datetime.timedelta(days=days)

    q = db.query(models.AgentExecution).filter(models.AgentExecution.timestamp >= since)
    if target_org_id:
        q = q.filter(models.AgentExecution.org_id == target_org_id)
    if agent_id:
        q = q.filter(models.AgentExecution.agent_id == agent_id)

    stats = q.with_entities(
        func.sum(models.AgentExecution.input_token_count),
        func.sum(models.AgentExecution.output_token_count),
        func.sum(models.AgentExecution.total_token_count),
        func.sum(models.AgentExecution.estimated_cost),
        func.count(models.AgentExecution.id),
        func.avg(models.AgentExecution.latency_ms)
    ).first()

    return {
        "range": range,
        "input_tokens": int(stats[0] or 0),
        "output_tokens": int(stats[1] or 0),
        "total_tokens": int(stats[2] or 0),
        "total_cost": round(float(stats[3] or 0.0), 6),
        "execution_count": int(stats[4] or 0),
        "avg_latency_ms": round(float(stats[5] or 0.0), 1)
    }


@router.get("/cost-by-model")
def get_cost_by_model(
    range: str = Query("30d"),
    org_id: Optional[str] = Query(None),
    x_org_context: Optional[str] = Header(None, alias="X-Organization-Context"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_org_id = _resolve_tenant_org_id(current_user, org_id or x_org_context)

    now = datetime.datetime.utcnow()
    range_map = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
    days = range_map.get(range, 30)
    since = now - datetime.timedelta(days=days)

    q = db.query(
        models.AgentExecution.provider,
        models.AgentExecution.model_name,
        func.sum(models.AgentExecution.total_token_count),
        func.sum(models.AgentExecution.estimated_cost),
        func.count(models.AgentExecution.id)
    ).filter(
        models.AgentExecution.timestamp >= since
    ).group_by(
        models.AgentExecution.provider,
        models.AgentExecution.model_name
    )

    if target_org_id:
        q = q.filter(models.AgentExecution.org_id == target_org_id)

    results = q.all()

    return {
        "range": range,
        "models": [
            {
                "provider": row[0] or "unknown",
                "model": row[1] or "unknown",
                "total_tokens": int(row[2] or 0),
                "total_cost": round(float(row[3] or 0.0), 6),
                "execution_count": int(row[4] or 0)
            }
            for row in results
        ]
    }


@router.get("/cost-by-agent")
def get_cost_by_agent(
    range: str = Query("30d"),
    org_id: Optional[str] = Query(None),
    x_org_context: Optional[str] = Header(None, alias="X-Organization-Context"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_org_id = _resolve_tenant_org_id(current_user, org_id or x_org_context)

    now = datetime.datetime.utcnow()
    range_map = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
    days = range_map.get(range, 30)
    since = now - datetime.timedelta(days=days)

    q = db.query(
        models.AgentExecution.agent_id,
        func.sum(models.AgentExecution.total_token_count),
        func.sum(models.AgentExecution.estimated_cost),
        func.count(models.AgentExecution.id),
        func.avg(models.AgentExecution.risk_score)
    ).filter(
        models.AgentExecution.timestamp >= since
    ).group_by(
        models.AgentExecution.agent_id
    )

    if target_org_id:
        q = q.filter(models.AgentExecution.org_id == target_org_id)

    results = q.all()

    agent_ids = [str(row[0]) for row in results]
    agents = {str(a.id): a for a in db.query(models.Agent).filter(models.Agent.id.in_(agent_ids)).all()} if agent_ids else {}

    return {
        "range": range,
        "agents": [
            {
                "agent_id": str(row[0]),
                "agent_code": agents.get(str(row[0]), None) and agents[str(row[0])].agent_code or "UNKNOWN",
                "agent_name": agents.get(str(row[0]), None) and agents[str(row[0])].name or "Unknown",
                "total_tokens": int(row[1] or 0),
                "total_cost": round(float(row[2] or 0.0), 6),
                "execution_count": int(row[3] or 0),
                "avg_risk_score": round(float(row[4] or 0.0), 1)
            }
            for row in results
        ]
    }


@router.get("/cost-over-time")
def get_cost_over_time(
    range: str = Query("30d"),
    org_id: Optional[str] = Query(None),
    x_org_context: Optional[str] = Header(None, alias="X-Organization-Context"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_org_id = _resolve_tenant_org_id(current_user, org_id or x_org_context)

    now = datetime.datetime.utcnow()
    range_map = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
    days = range_map.get(range, 30)
    since = now - datetime.timedelta(days=days)

    q = db.query(models.AgentExecution).filter(models.AgentExecution.timestamp >= since)
    if target_org_id:
        q = q.filter(models.AgentExecution.org_id == target_org_id)

    executions = q.all()

    # Group by date
    daily_map = {}
    for e in executions:
        day = e.timestamp.strftime("%Y-%m-%d") if e.timestamp else "unknown"
        if day not in daily_map:
            daily_map[day] = {"date": day, "tokens": 0, "cost": 0.0, "executions": 0}
        daily_map[day]["tokens"] += (e.total_token_count or 0)
        daily_map[day]["cost"] = round(daily_map[day]["cost"] + (e.estimated_cost or 0.0), 6)
        daily_map[day]["executions"] += 1

    result = sorted(daily_map.values(), key=lambda x: x["date"])

    return {
        "range": range,
        "data": result
    }


# ==================== BUDGET GOVERNANCE ====================

@router.get("/budgets")
def list_budgets(
    agent_id: Optional[str] = Query(None),
    org_id: Optional[str] = Query(None),
    x_org_context: Optional[str] = Header(None, alias="X-Organization-Context"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_org_id = _resolve_tenant_org_id(current_user, org_id or x_org_context)

    q = db.query(models.AgentBudgetConfig)
    if target_org_id:
        q = q.filter(models.AgentBudgetConfig.org_id == target_org_id)
    if agent_id:
        q = q.filter(models.AgentBudgetConfig.agent_id == agent_id)

    budgets = q.all()

    result = []
    for b in budgets:
        agent = None
        if b.agent_id:
            agent = db.query(models.Agent).filter(models.Agent.id == b.agent_id).first()

        result.append({
            "id": str(b.id),
            "org_id": str(b.org_id),
            "agent_id": str(b.agent_id) if b.agent_id else None,
            "agent_code": agent.agent_code if agent else None,
            "agent_name": agent.name if agent else "Organization Default",
            "daily_token_limit": b.daily_token_limit,
            "monthly_token_limit": b.monthly_token_limit,
            "daily_cost_limit": b.daily_cost_limit,
            "monthly_cost_limit": b.monthly_cost_limit,
            "execution_count_limit": b.execution_count_limit,
            "warning_threshold_pct": b.warning_threshold_pct,
            "exceeded_threshold_pct": b.exceeded_threshold_pct,
            "auto_suspend_on_exceeded": b.auto_suspend_on_exceeded,
            "budget_state": b.budget_state,
            "current_daily_tokens": b.current_daily_tokens,
            "current_monthly_tokens": b.current_monthly_tokens,
            "current_daily_cost": b.current_daily_cost,
            "current_monthly_cost": b.current_monthly_cost,
            "current_daily_executions": b.current_daily_executions,
        })

    return result


@router.post("/budgets")
def create_budget_config(
    req: dict,
    org_id: Optional[str] = Query(None),
    x_org_context: Optional[str] = Header(None, alias="X-Organization-Context"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_org_id = _resolve_tenant_org_id(current_user, org_id or x_org_context)
    if not target_org_id:
        target_org_id = str(current_user.org_id)

    # Authorization: only ADMIN+ roles
    if current_user.role not in ("SUPER_ADMIN", "ADMIN", "MANAGER"):
        raise HTTPException(status_code=403, detail="Insufficient permissions to manage budget configurations")

    agent_id = req.get("agent_id")
    if agent_id:
        agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        if current_user.role != "SUPER_ADMIN" and str(agent.org_id) != target_org_id:
            raise HTTPException(status_code=403, detail="Cannot configure budget for another org's agent")

    config = models.AgentBudgetConfig(
        org_id=target_org_id,
        agent_id=agent_id,
        daily_token_limit=req.get("daily_token_limit"),
        monthly_token_limit=req.get("monthly_token_limit"),
        daily_cost_limit=req.get("daily_cost_limit"),
        monthly_cost_limit=req.get("monthly_cost_limit"),
        execution_count_limit=req.get("execution_count_limit"),
        warning_threshold_pct=req.get("warning_threshold_pct", 80.0),
        exceeded_threshold_pct=req.get("exceeded_threshold_pct", 100.0),
        auto_suspend_on_exceeded=req.get("auto_suspend_on_exceeded", False),
    )
    db.add(config)
    db.commit()
    db.refresh(config)

    audit = models.AuditLog(
        event_type="BUDGET_CONFIG_CREATED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="CREATE_BUDGET_CONFIG",
        resource=f"budget_config:{config.id}",
        result="SUCCESS",
        metadata_json={"agent_id": agent_id, "org_id": target_org_id}
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "id": str(config.id), "budget_state": config.budget_state}


# ==================== RISK SIGNALS ====================

@router.get("/risk-signals")
def list_risk_signals(
    agent_id: Optional[str] = Query(None),
    signal_status: Optional[str] = Query(None),
    range: str = Query("7d"),
    org_id: Optional[str] = Query(None),
    x_org_context: Optional[str] = Header(None, alias="X-Organization-Context"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_org_id = _resolve_tenant_org_id(current_user, org_id or x_org_context)

    now = datetime.datetime.utcnow()
    range_map = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
    days = range_map.get(range, 7)
    since = now - datetime.timedelta(days=days)

    q = db.query(models.RuntimeRiskSignal).filter(models.RuntimeRiskSignal.timestamp >= since)
    if target_org_id:
        q = q.filter(models.RuntimeRiskSignal.org_id == target_org_id)
    if agent_id:
        q = q.filter(models.RuntimeRiskSignal.agent_id == agent_id)
    if signal_status:
        q = q.filter(models.RuntimeRiskSignal.status == signal_status)

    signals = q.order_by(desc(models.RuntimeRiskSignal.timestamp)).limit(200).all()

    return {
        "range": range,
        "count": len(signals),
        "signals": [
            {
                "id": str(s.id),
                "agent_id": str(s.agent_id) if s.agent_id else None,
                "signal_type": s.signal_type,
                "severity": s.severity,
                "title": s.title,
                "description": s.description,
                "evidence": s.evidence_json,
                "status": s.status,
                "timestamp": s.timestamp.isoformat() if s.timestamp else None
            }
            for s in signals
        ]
    }


@router.patch("/risk-signals/{signal_id}")
def update_risk_signal(
    signal_id: str,
    req: dict,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    signal = db.query(models.RuntimeRiskSignal).filter(models.RuntimeRiskSignal.id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="Risk signal not found")

    if current_user.role != "SUPER_ADMIN" and str(signal.org_id) != str(current_user.org_id):
        raise HTTPException(status_code=403, detail="Forbidden: Risk signal belongs to another organization")

    new_status = req.get("status")
    if new_status and new_status in ("ACKNOWLEDGED", "RESOLVED", "DISMISSED"):
        signal.status = new_status
        if new_status == "RESOLVED":
            signal.resolved_at = datetime.datetime.utcnow()
            signal.resolved_by = str(current_user.id)
        db.commit()

    return {"status": "SUCCESS", "signal_status": signal.status}


# ==================== CIRCUIT BREAKER ENHANCED ====================

@router.get("/circuit-breakers")
def get_circuit_breakers_enhanced(
    org_id: Optional[str] = Query(None),
    x_org_context: Optional[str] = Header(None, alias="X-Organization-Context"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_org_id = _resolve_tenant_org_id(current_user, org_id or x_org_context)

    q = db.query(models.CircuitBreaker)
    if target_org_id:
        q = q.join(models.Agent).filter(models.Agent.org_id == target_org_id)

    cbs = q.all()
    result = []
    for cb in cbs:
        agent = db.query(models.Agent).filter(models.Agent.id == cb.agent_id).first()
        budget = db.query(models.AgentBudgetConfig).filter(
            models.AgentBudgetConfig.agent_id == cb.agent_id
        ).first()

        result.append({
            "agent_id": str(cb.agent_id),
            "agent_code": agent.agent_code if agent else "AG-000",
            "name": agent.name if agent else "Agent",
            "agent_status": agent.status if agent else "UNKNOWN",
            "circuit_breaker_state": cb.state,
            "trigger_reason": cb.trigger_reason,
            "tripped_at": cb.tripped_at.isoformat() if cb.tripped_at else None,
            "restored_at": cb.restored_at.isoformat() if cb.restored_at else None,
            "budget_state": budget.budget_state if budget else "UNCONFIGURED"
        })

    return result


# ==================== WEBHOOK DELIVERY HEALTH ====================

@router.get("/webhook-health")
def get_webhook_health(
    range: str = Query("7d"),
    org_id: Optional[str] = Query(None),
    x_org_context: Optional[str] = Header(None, alias="X-Organization-Context"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_org_id = _resolve_tenant_org_id(current_user, org_id or x_org_context)

    now = datetime.datetime.utcnow()
    range_map = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
    days = range_map.get(range, 7)
    since = now - datetime.timedelta(days=days)

    endpoint_q = db.query(models.WebhookEndpoint)
    if target_org_id:
        endpoint_q = endpoint_q.filter(models.WebhookEndpoint.org_id == target_org_id)

    endpoints = endpoint_q.all()
    endpoint_ids = [str(e.id) for e in endpoints]

    if not endpoint_ids:
        return {"total_endpoints": 0, "active_endpoints": 0, "total_deliveries": 0,
                "successful": 0, "failed": 0, "dead_letter": 0, "pending": 0}

    delivery_q = db.query(models.WebhookDelivery).filter(
        models.WebhookDelivery.webhook_id.in_(endpoint_ids),
        models.WebhookDelivery.created_at >= since
    )

    total_deliveries = delivery_q.count()
    successful = delivery_q.filter(models.WebhookDelivery.status.in_(["SUCCESS", "DELIVERED"])).count()
    failed = delivery_q.filter(models.WebhookDelivery.status == "FAILED").count()
    dead_letter = delivery_q.filter(models.WebhookDelivery.status == "DEAD_LETTER").count()
    pending = delivery_q.filter(models.WebhookDelivery.status.in_(["PENDING", "RETRYING"])).count()

    return {
        "total_endpoints": len(endpoints),
        "active_endpoints": sum(1 for e in endpoints if e.is_active),
        "total_deliveries": total_deliveries,
        "successful": successful,
        "failed": failed,
        "dead_letter": dead_letter,
        "pending": pending,
        "success_rate": round(successful / total_deliveries * 100, 1) if total_deliveries > 0 else 0.0
    }


# ==================== MODEL PRICING MANAGEMENT ====================

@router.get("/pricing")
def list_pricing(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pricing = db.query(models.ModelPricing).filter(models.ModelPricing.active == True).all()
    return [
        {
            "id": str(p.id),
            "provider": p.provider,
            "model": p.model,
            "input_cost_per_1k": p.input_cost_per_1k,
            "output_cost_per_1k": p.output_cost_per_1k,
            "currency": p.currency,
            "effective_from": p.effective_from.isoformat() if p.effective_from else None
        }
        for p in pricing
    ]


@router.post("/pricing")
def create_pricing(
    req: dict,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in ("SUPER_ADMIN", "ADMIN"):
        raise HTTPException(status_code=403, detail="Only ADMIN or SUPER_ADMIN can configure model pricing")

    pricing = models.ModelPricing(
        provider=req.get("provider", "").lower(),
        model=req.get("model", "").lower(),
        input_cost_per_1k=req.get("input_cost_per_1k", 0.0),
        output_cost_per_1k=req.get("output_cost_per_1k", 0.0),
        currency=req.get("currency", "USD"),
        active=True
    )
    db.add(pricing)
    db.commit()
    db.refresh(pricing)

    return {"status": "SUCCESS", "id": str(pricing.id), "provider": pricing.provider, "model": pricing.model}


# ==================== AGENT RUNTIME SUMMARY ====================

@router.get("/agent-summary/{agent_id}")
def get_agent_runtime_summary(
    agent_id: str,
    range: str = Query("30d"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    agent = db.query(models.Agent).filter(
        (models.Agent.id == agent_id) | (models.Agent.agent_code == agent_id)
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if current_user.role != "SUPER_ADMIN" and str(agent.org_id) != str(current_user.org_id):
        raise HTTPException(status_code=403, detail="Forbidden: Agent belongs to another organization")

    now = datetime.datetime.utcnow()
    range_map = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
    days = range_map.get(range, 30)
    since = now - datetime.timedelta(days=days)

    exec_q = db.query(models.AgentExecution).filter(
        models.AgentExecution.agent_id == agent.id,
        models.AgentExecution.timestamp >= since
    )

    stats = exec_q.with_entities(
        func.count(models.AgentExecution.id),
        func.sum(models.AgentExecution.total_token_count),
        func.sum(models.AgentExecution.estimated_cost),
        func.avg(models.AgentExecution.risk_score),
        func.avg(models.AgentExecution.latency_ms)
    ).first()

    allowed = exec_q.filter(models.AgentExecution.policy_decision == "ALLOW").count()
    refused = exec_q.filter(models.AgentExecution.policy_decision == "REFUSE").count()
    review = exec_q.filter(models.AgentExecution.policy_decision == "REVIEW").count()

    # Circuit breaker
    cb = db.query(models.CircuitBreaker).filter(models.CircuitBreaker.agent_id == agent.id).first()

    # Budget
    budget = db.query(models.AgentBudgetConfig).filter(
        models.AgentBudgetConfig.agent_id == agent.id
    ).first()

    # Active risk signals
    active_signals = db.query(models.RuntimeRiskSignal).filter(
        models.RuntimeRiskSignal.agent_id == agent.id,
        models.RuntimeRiskSignal.status == "ACTIVE"
    ).count()

    return {
        "agent_id": str(agent.id),
        "agent_code": agent.agent_code,
        "name": agent.name,
        "status": agent.status,
        "range": range,
        "executions": int(stats[0] or 0),
        "total_tokens": int(stats[1] or 0),
        "total_cost": round(float(stats[2] or 0.0), 6),
        "avg_risk_score": round(float(stats[3] or 0.0), 1),
        "avg_latency_ms": round(float(stats[4] or 0.0), 1),
        "allowed": allowed,
        "refused": refused,
        "review": review,
        "circuit_breaker_state": cb.state if cb else "NORMAL",
        "budget_state": budget.budget_state if budget else "UNCONFIGURED",
        "active_risk_signals": active_signals
    }
