from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from core.deps import get_current_user
import models

router = APIRouter(prefix="/behavior", tags=["Behavior Analytics"])

@router.get("/profiles")
def list_behavior_profiles(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.BehaviorProfile)
    if current_user.role != "SUPER_ADMIN":
        query = query.join(models.Agent).filter(models.Agent.org_id == current_user.org_id)
    profiles = query.all()

    res = []
    for p in profiles:
        agent = db.query(models.Agent).filter(models.Agent.id == p.agent_id).first()
        res.append({
            "agent_code": agent.agent_code if agent else "AG-000",
            "name": agent.name if agent else "Agent",
            "avg_daily_actions": p.avg_daily_actions,
            "normal_operating_hours": p.normal_operating_hours,
            "baseline_spending": p.baseline_spending
        })
    return res

@router.get("/deviations")
def list_behavioral_deviations(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.AnomalyEvent)
    if current_user.role != "SUPER_ADMIN":
        query = query.join(models.Agent).filter(models.Agent.org_id == current_user.org_id)
    return query.all()
