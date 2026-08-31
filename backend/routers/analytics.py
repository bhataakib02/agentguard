from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
import models

router = APIRouter(prefix="/analytics", tags=["Analytics & Intelligence"])

@router.get("/overview")
def get_analytics_overview(db: Session = Depends(get_db)):
    total_agents = db.query(models.Agent).count()
    active_agents = db.query(models.Agent).filter(models.Agent.status == "NORMAL").count()
    suspended_agents = db.query(models.Agent).filter(models.Agent.status == "SUSPENDED").count()
    high_risk_agents = db.query(models.Agent).filter(models.Agent.risk_score > 60).count()

    total_decisions = db.query(models.Decision).count()
    allowed_decisions = db.query(models.Decision).filter(models.Decision.decision == "ALLOW").count()
    review_decisions = db.query(models.Decision).filter(models.Decision.decision == "REVIEW").count()
    blocked_decisions = db.query(models.Decision).filter(models.Decision.decision == "REFUSE").count()
    pending_approvals = db.query(models.ApprovalRequest).filter(models.ApprovalRequest.status == "PENDING").count()

    avg_risk = db.query(func.avg(models.Agent.risk_score)).scalar()
    avg_trust = db.query(func.avg(models.Agent.trust_score)).scalar()

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
        "avg_risk_score": round(float(avg_risk), 1) if avg_risk is not None else 0,
        "avg_trust_score": round(float(avg_trust), 1) if avg_trust is not None else 0
    }
