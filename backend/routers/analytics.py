import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, Header, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database import get_db
from core.deps import get_current_user
import models

router = APIRouter(prefix="/analytics", tags=["Analytics & Intelligence"])


def _resolve_tenant_org_id(current_user: models.User, org_id_param: Optional[str] = None) -> Optional[str]:
    """
    Derives trusted org_id. Normal users are strictly locked to current_user.org_id.
    SUPER_ADMIN can optionally filter by target org_id, or None for platform-wide.
    """
    if current_user.role != "SUPER_ADMIN":
        if org_id_param and str(org_id_param) != str(current_user.org_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Cannot access analytics for another organization"
            )
        return str(current_user.org_id)
    return org_id_param if org_id_param and org_id_param != "ALL" else None


@router.get("/overview")
def get_analytics_overview(
    org_id: Optional[str] = Query(None),
    x_org_context: Optional[str] = Header(None, alias="X-Organization-Context"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_org_id = _resolve_tenant_org_id(current_user, org_id or x_org_context)

    # Base queries
    agent_q = db.query(models.Agent)
    dec_q = db.query(models.Decision)
    app_q = db.query(models.ApprovalRequest)
    inc_q = db.query(models.SecurityIncident)
    pol_q = db.query(models.Policy)

    if target_org_id:
        agent_q = agent_q.filter(models.Agent.org_id == target_org_id)
        dec_q = dec_q.join(models.Agent).filter(models.Agent.org_id == target_org_id)
        app_q = app_q.join(models.Agent).filter(models.Agent.org_id == target_org_id)
        inc_q = inc_q.filter(models.SecurityIncident.org_id == target_org_id)
        pol_q = pol_q.filter(models.Policy.org_id == target_org_id)

    # Real DB aggregations
    total_agents = agent_q.count()
    active_agents = agent_q.filter(models.Agent.status == "NORMAL").count()
    suspended_agents = agent_q.filter(models.Agent.status == "SUSPENDED").count()
    high_risk_agents = agent_q.filter(models.Agent.risk_score > 60).count()

    total_decisions = dec_q.count()
    allowed_decisions = dec_q.filter(models.Decision.decision == "ALLOW").count()
    review_decisions = dec_q.filter(models.Decision.decision == "REVIEW").count()
    blocked_decisions = dec_q.filter(models.Decision.decision == "REFUSE").count()

    # Risk metrics from decisions
    risk_stats = dec_q.with_entities(
        func.avg(models.Decision.risk_score),
        func.max(models.Decision.risk_score)
    ).first()
    avg_decision_risk = round(float(risk_stats[0] or 0.0), 1) if risk_stats and risk_stats[0] is not None else 0.0
    max_decision_risk = int(risk_stats[1] or 0) if risk_stats and risk_stats[1] is not None else 0
    high_risk_decisions = dec_q.filter(models.Decision.risk_score > 60).count()

    # Approvals
    pending_approvals = app_q.filter(models.ApprovalRequest.status == "PENDING").count()
    approved_approvals = app_q.filter(models.ApprovalRequest.status == "APPROVED").count()
    rejected_approvals = app_q.filter(models.ApprovalRequest.status == "REJECTED").count()

    # Rates
    refusal_rate = round((blocked_decisions / total_decisions * 100.0), 1) if total_decisions > 0 else 0.0
    approval_rate = round((allowed_decisions / total_decisions * 100.0), 1) if total_decisions > 0 else 0.0

    # Incidents & Policies
    total_incidents = inc_q.count()
    open_incidents = inc_q.filter(models.SecurityIncident.status == "OPEN").count()
    resolved_incidents = inc_q.filter(models.SecurityIncident.status == "RESOLVED").count()

    total_policies = pol_q.count()
    active_policies = pol_q.filter(models.Policy.status == "ACTIVE").count()

    return {
        "organization_id": target_org_id or "PLATFORM_GLOBAL",
        "total_agents": total_agents,
        "active_agents": active_agents,
        "suspended_agents": suspended_agents,
        "high_risk_agents": high_risk_agents,
        "total_decisions": total_decisions,
        "allowed_decisions": allowed_decisions,
        "review_decisions": review_decisions,
        "blocked_decisions": blocked_decisions,
        "allowed": allowed_decisions,
        "refused": blocked_decisions,
        "review": review_decisions,
        "avg_risk_score": avg_decision_risk,
        "max_risk_score": max_decision_risk,
        "high_risk_decisions": high_risk_decisions,
        "refusal_rate": refusal_rate,
        "approval_rate": approval_rate,
        "pending_approvals": pending_approvals,
        "approved_approvals": approved_approvals,
        "rejected_approvals": rejected_approvals,
        "total_incidents": total_incidents,
        "open_incidents": open_incidents,
        "resolved_incidents": resolved_incidents,
        "total_policies": total_policies,
        "active_policies": active_policies,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }


@router.get("/time-series")
def get_time_series_analytics(
    time_range: str = Query("7d", alias="range"),
    org_id: Optional[str] = Query(None),
    x_org_context: Optional[str] = Header(None, alias="X-Organization-Context"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_org_id = _resolve_tenant_org_id(current_user, org_id or x_org_context)

    # Determine time window
    now = datetime.datetime.utcnow()
    range_map = {
        "24h": datetime.timedelta(hours=24),
        "7d": datetime.timedelta(days=7),
        "30d": datetime.timedelta(days=30),
        "90d": datetime.timedelta(days=90)
    }
    delta = range_map.get(time_range.lower(), datetime.timedelta(days=7))
    start_time = now - delta

    # Fetch decisions in window
    q = db.query(models.Decision).filter(models.Decision.timestamp >= start_time)
    if target_org_id:
        q = q.join(models.Agent).filter(models.Agent.org_id == target_org_id)
    decisions = q.order_by(models.Decision.timestamp.asc()).all()

    # Bucket grouping (hourly for 24h, daily for others)
    is_hourly = time_range.lower() == "24h"
    buckets: Dict[str, Dict[str, Any]] = {}

    if is_hourly:
        # Pre-populate all 24 hours
        for i in range(24, -1, -1):
            h_time = now - datetime.timedelta(hours=i)
            key = h_time.strftime("%Y-%m-%d %H:00")
            buckets[key] = {"timestamp": key, "label": h_time.strftime("%H:00"), "decisions": 0, "allowed": 0, "review": 0, "refused": 0, "total_risk": 0}
    else:
        num_days = delta.days
        for i in range(num_days, -1, -1):
            d_time = now - datetime.timedelta(days=i)
            key = d_time.strftime("%Y-%m-%d")
            buckets[key] = {"timestamp": key, "label": d_time.strftime("%b %d"), "decisions": 0, "allowed": 0, "review": 0, "refused": 0, "total_risk": 0}

    # Aggregate real decision events
    for d in decisions:
        if not d.timestamp:
            continue
        key = d.timestamp.strftime("%Y-%m-%d %H:00" if is_hourly else "%Y-%m-%d")
        if key in buckets:
            buckets[key]["decisions"] += 1
            if d.decision == "ALLOW":
                buckets[key]["allowed"] += 1
            elif d.decision == "REVIEW":
                buckets[key]["review"] += 1
            elif d.decision == "REFUSE":
                buckets[key]["refused"] += 1
            buckets[key]["total_risk"] += (d.risk_score or 0)

    # Format result list
    result = []
    for k in sorted(buckets.keys()):
        b = buckets[k]
        cnt = b["decisions"]
        avg_risk = round(b["total_risk"] / cnt, 1) if cnt > 0 else 0.0
        result.append({
            "timestamp": b["timestamp"],
            "date": b["timestamp"][:10],
            "label": b["label"],
            "decisions": cnt,
            "allowed": b["allowed"],
            "review": b["review"],
            "refused": b["refused"],
            "avg_risk": avg_risk
        })

    return {
        "range": time_range,
        "organization_id": target_org_id or "PLATFORM_GLOBAL",
        "data_points": len(result),
        "data": result,
        "series": result
    }


@router.get("/by-policy")
def get_analytics_by_policy(
    org_id: Optional[str] = Query(None),
    x_org_context: Optional[str] = Header(None, alias="X-Organization-Context"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_org_id = _resolve_tenant_org_id(current_user, org_id or x_org_context)

    q = db.query(models.Decision)
    if target_org_id:
        q = q.join(models.Agent).filter(models.Agent.org_id == target_org_id)
    decisions = q.all()

    policy_map: Dict[str, Dict[str, Any]] = {}
    for d in decisions:
        pol_name = d.policy_name or "Baseline Governance Policy"
        if pol_name not in policy_map:
            policy_map[pol_name] = {
                "policy_name": pol_name,
                "total_decisions": 0,
                "allowed": 0,
                "review": 0,
                "refused": 0,
                "total_risk": 0
            }
        policy_map[pol_name]["total_decisions"] += 1
        if d.decision == "ALLOW":
            policy_map[pol_name]["allowed"] += 1
        elif d.decision == "REVIEW":
            policy_map[pol_name]["review"] += 1
        elif d.decision == "REFUSE":
            policy_map[pol_name]["refused"] += 1
        policy_map[pol_name]["total_risk"] += (d.risk_score or 0)

    res = []
    for k, v in policy_map.items():
        cnt = v["total_decisions"]
        res.append({
            "policy_name": v["policy_name"],
            "total_decisions": cnt,
            "allowed": v["allowed"],
            "review": v["review"],
            "refused": v["refused"],
            "avg_risk": round(v["total_risk"] / cnt, 1) if cnt > 0 else 0.0
        })

    res.sort(key=lambda x: x["total_decisions"], reverse=True)
    return res


@router.get("/by-agent")
def get_analytics_by_agent(
    org_id: Optional[str] = Query(None),
    x_org_context: Optional[str] = Header(None, alias="X-Organization-Context"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_org_id = _resolve_tenant_org_id(current_user, org_id or x_org_context)

    agent_q = db.query(models.Agent)
    if target_org_id:
        agent_q = agent_q.filter(models.Agent.org_id == target_org_id)
    agents = agent_q.all()

    res = []
    for a in agents:
        dec_q = db.query(models.Decision).filter(models.Decision.agent_id == a.id)
        total_d = dec_q.count()
        allowed = dec_q.filter(models.Decision.decision == "ALLOW").count()
        review = dec_q.filter(models.Decision.decision == "REVIEW").count()
        refused = dec_q.filter(models.Decision.decision == "REFUSE").count()
        avg_risk_raw = dec_q.with_entities(func.avg(models.Decision.risk_score)).scalar()
        avg_risk = round(float(avg_risk_raw), 1) if avg_risk_raw is not None else float(a.risk_score)

        res.append({
            "agent_id": str(a.id),
            "agent_code": a.agent_code,
            "name": a.name,
            "department": a.department,
            "status": a.status,
            "total_decisions": total_d,
            "allowed": allowed,
            "review": review,
            "refused": refused,
            "avg_decision_risk": avg_risk,
            "agent_risk_score": a.risk_score
        })

    res.sort(key=lambda x: x["total_decisions"], reverse=True)
    return res


@router.get("/risk-distribution")
def get_risk_distribution(
    org_id: Optional[str] = Query(None),
    x_org_context: Optional[str] = Header(None, alias="X-Organization-Context"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_org_id = _resolve_tenant_org_id(current_user, org_id or x_org_context)

    dec_q = db.query(models.Decision)
    agent_q = db.query(models.Agent)
    if target_org_id:
        dec_q = dec_q.join(models.Agent).filter(models.Agent.org_id == target_org_id)
        agent_q = agent_q.filter(models.Agent.org_id == target_org_id)

    decisions = dec_q.all()
    agents = agent_q.all()

    # Risk bands: Low (0-30), Medium (31-60), High (61-80), Critical (81-100)
    decision_bands = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for d in decisions:
        s = d.risk_score or 0
        if s <= 30:
            decision_bands["LOW"] += 1
        elif s <= 60:
            decision_bands["MEDIUM"] += 1
        elif s <= 80:
            decision_bands["HIGH"] += 1
        else:
            decision_bands["CRITICAL"] += 1

    agent_bands = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for a in agents:
        s = a.risk_score or 0
        if s <= 30:
            agent_bands["LOW"] += 1
        elif s <= 60:
            agent_bands["MEDIUM"] += 1
        elif s <= 80:
            agent_bands["HIGH"] += 1
        else:
            agent_bands["CRITICAL"] += 1

    return {
        "organization_id": target_org_id or "PLATFORM_GLOBAL",
        "decision_risk_distribution": decision_bands,
        "agent_risk_distribution": agent_bands,
        "total_decisions_analyzed": len(decisions),
        "total_agents_analyzed": len(agents)
    }
