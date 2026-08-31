from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(prefix="/risk", tags=["Risk Intelligence"])

@router.get("/agents")
def get_agent_risk_scores(db: Session = Depends(get_db)):
    agents = db.query(models.Agent).all()
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
def get_risk_trends(db: Session = Depends(get_db)):
    high_risk_cnt = db.query(models.Agent).filter(models.Agent.risk_score > 60).count()
    total_cnt = db.query(models.Agent).count()
    avg_score = 0
    if total_cnt > 0:
        avg_score = int(sum(a.risk_score for a in db.query(models.Agent).all()) / total_cnt)

    return [
        {"day": "Mon", "avg_risk": avg_score, "high_risk_agents": high_risk_cnt},
        {"day": "Tue", "avg_risk": avg_score, "high_risk_agents": high_risk_cnt},
        {"day": "Wed", "avg_risk": avg_score, "high_risk_agents": high_risk_cnt},
        {"day": "Thu", "avg_risk": avg_score, "high_risk_agents": high_risk_cnt},
        {"day": "Fri", "avg_risk": avg_score, "high_risk_agents": high_risk_cnt},
        {"day": "Sat", "avg_risk": avg_score, "high_risk_agents": high_risk_cnt},
        {"day": "Sun", "avg_risk": avg_score, "high_risk_agents": high_risk_cnt}
    ]
