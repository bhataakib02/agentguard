from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from core.deps import get_current_user
import models

router = APIRouter(prefix="/trust", tags=["Trust & Reputation"])

@router.get("")
def get_reputation_overview(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.ReputationScore)
    if current_user.role != "SUPER_ADMIN":
        query = query.join(models.Agent).filter(models.Agent.org_id == current_user.org_id)
    scores = query.all()

    res = []
    for s in scores:
        agent = db.query(models.Agent).filter(models.Agent.id == s.agent_id).first()
        res.append({
            "agent_code": agent.agent_code if agent else "AG-000",
            "name": agent.name if agent else "Unknown Agent",
            "trust_score": s.trust_score,
            "successful_tasks": s.successful_tasks,
            "violations_count": s.violations_count,
            "anomalies_count": s.anomalies_count,
            "overrides_count": s.overrides_count
        })
    return res
