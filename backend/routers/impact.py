"""
Phase 6C: Real Governance Impact Aggregation Engine
Aggregates business and security impact strictly from database decisions,
prevented actions, and execution latency.
Never fabricates impact metrics or financial amounts.
"""

from fastapi import APIRouter, Depends, Query, Header, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from database import get_db
from core.deps import get_current_user
import models

router = APIRouter(prefix="/impact", tags=["Impact Analysis"])

def _resolve_tenant_org_id(current_user: models.User, org_id_param: Optional[str] = None) -> Optional[str]:
    if current_user.role != "SUPER_ADMIN":
        if org_id_param and str(org_id_param) != str(current_user.org_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Cannot access impact metrics for another organization"
            )
        return str(current_user.org_id)
    return org_id_param if org_id_param and org_id_param != "ALL" else None


@router.get("/metrics")
def get_impact_metrics(
    org_id: Optional[str] = Query(None),
    x_org_context: Optional[str] = Header(None, alias="X-Organization-Context"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns actual observed impact metrics aggregated from database records.
    Calculates prevented financial exposure from real REFUSE decisions.
    """
    target_org_id = _resolve_tenant_org_id(current_user, org_id or x_org_context)

    # Base query for decisions
    dec_q = db.query(models.Decision)
    exec_q = db.query(models.AgentExecution)

    if target_org_id:
        dec_q = dec_q.join(models.Agent).filter(models.Agent.org_id == target_org_id)
        exec_q = exec_q.filter(models.AgentExecution.org_id == target_org_id)

    total_decisions = dec_q.count()
    refused_decisions = dec_q.filter(models.Decision.decision == "REFUSE").all()
    review_count = dec_q.filter(models.Decision.decision == "REVIEW").count()
    allowed_count = dec_q.filter(models.Decision.decision == "ALLOW").count()

    prevented_amount = sum(d.amount or 0.0 for d in refused_decisions)
    prevented_count = len(refused_decisions)

    # Escalation & Autonomous rates
    if total_decisions > 0:
        human_escalation_rate_pct = round((review_count / total_decisions) * 100.0, 2)
        autonomous_execution_rate_pct = round((allowed_count / total_decisions) * 100.0, 2)
    else:
        human_escalation_rate_pct = None
        autonomous_execution_rate_pct = None

    # Decision Latency from actual AgentExecution telemetry
    latency_stat = exec_q.with_entities(func.avg(models.AgentExecution.latency_ms)).first()
    avg_latency = round(float(latency_stat[0]), 1) if (latency_stat and latency_stat[0] is not None) else None

    return {
        "status": "REAL_AGGREGATION",
        "data_sufficiency": "SUFFICIENT" if total_decisions > 0 else "NO_DECISIONS_EVALUATED",
        "total_decisions_evaluated": total_decisions,
        "prevented_financial_risk_amount": round(float(prevented_amount), 2),
        "prevented_actions_count": prevented_count,
        "allowed_actions_count": allowed_count,
        "human_escalation_count": review_count,
        "human_escalation_rate_pct": human_escalation_rate_pct,
        "autonomous_execution_rate_pct": autonomous_execution_rate_pct,
        "avg_decision_latency_ms": avg_latency,
        "currency": "INR"
    }
