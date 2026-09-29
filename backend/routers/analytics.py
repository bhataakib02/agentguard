from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from core.deps import get_current_user
import models

router = APIRouter(prefix="/analytics", tags=["Analytics & Intelligence"])

@router.get("/overview")
def get_analytics_overview(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    agent_query = db.query(models.Agent)
    dec_query = db.query(models.Decision)
    app_query = db.query(models.ApprovalRequest)

    if current_user.role != "SUPER_ADMIN":
        agent_query = agent_query.filter(models.Agent.org_id == current_user.org_id)
        dec_query = dec_query.join(models.Agent).filter(models.Agent.org_id == current_user.org_id)
        app_query = app_query.join(models.Agent).filter(models.Agent.org_id == current_user.org_id)

    total_agents = agent_query.count()
    active_agents = agent_query.filter(models.Agent.status == "NORMAL").count()
    suspended_agents = agent_query.filter(models.Agent.status == "SUSPENDED").count()
    high_risk_agents = agent_query.filter(models.Agent.risk_score > 60).count()

    total_decisions = dec_query.count()
    allowed_decisions = dec_query.filter(models.Decision.decision == "ALLOW").count()
    review_decisions = dec_query.filter(models.Decision.decision == "REVIEW").count()
    blocked_decisions = dec_query.filter(models.Decision.decision == "REFUSE").count()
    pending_approvals = app_query.filter(models.ApprovalRequest.status == "PENDING").count()

    agents = agent_query.all()
    avg_risk = sum(a.risk_score for a in agents) / total_agents if total_agents > 0 else 0
    avg_trust = sum(a.trust_score for a in agents) / total_agents if total_agents > 0 else 0

    return {
        "total_agents": total_agents,
        "active_agents": active_agents,
        "suspended_agents": suspended_agents,
        "high_risk_agents": high_risk_agents,
        "total_decisions": total_decisions,
        "allowed_decisions": allowed_decisions,
        "review_decisions": review_decisions,
        "blocked_decisions": blocked_decisions,
        "pending_approvals": pending_approvals,
        "avg_risk_score": round(float(avg_risk), 1),
        "avg_trust_score": round(float(avg_trust), 1)
    }
