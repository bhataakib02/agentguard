from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(prefix="/behavior", tags=["Behavior Analytics"])

@router.get("/profiles")
def list_behavior_profiles(db: Session = Depends(get_db)):
    profiles = db.query(models.BehaviorProfile).all()
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
def list_behavioral_deviations(db: Session = Depends(get_db)):
    return db.query(models.AnomalyEvent).all()
