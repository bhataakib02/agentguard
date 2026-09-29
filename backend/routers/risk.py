from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from core.deps import get_current_user
import models

router = APIRouter(prefix="/risk", tags=["Risk Intelligence"])

@router.get("/agents")
def get_agent_risk_scores(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Agent)
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.Agent.org_id == current_user.org_id)
    agents = query.all()
    return [
        {
            "id": a.id,
            "agent_code": a.agent_code,
            "name": a.name,
            "department": a.department,
            "risk_score": a.risk_score,
            "status": a.status,
            "autonomy": a.autonomy_level
        }
        for a in agents
    ]

@router.get("/trends")
def get_risk_trends(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Agent)
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.Agent.org_id == current_user.org_id)
    agents = query.all()
    total_cnt = len(agents)
    high_risk_cnt = len([a for a in agents if a.risk_score > 60])
    avg_score = int(sum(a.risk_score for a in agents) / total_cnt) if total_cnt > 0 else 0

    return [
        {"day": "Mon", "avg_risk": avg_score, "high_risk_agents": high_risk_cnt},
        {"day": "Tue", "avg_risk": avg_score, "high_risk_agents": high_risk_cnt},
        {"day": "Wed", "avg_risk": avg_score, "high_risk_agents": high_risk_cnt},
        {"day": "Thu", "avg_risk": avg_score, "high_risk_agents": high_risk_cnt},
        {"day": "Fri", "avg_risk": avg_score, "high_risk_agents": high_risk_cnt},
        {"day": "Sat", "avg_risk": avg_score, "high_risk_agents": high_risk_cnt},
        {"day": "Sun", "avg_risk": avg_score, "high_risk_agents": high_risk_cnt}
    ]
