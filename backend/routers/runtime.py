from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(prefix="/runtime", tags=["Circuit Breaker & Runtime Safety"])

@router.get("/circuit-breakers")
def get_circuit_breakers(db: Session = Depends(get_db)):
    cbs = db.query(models.CircuitBreaker).all()
    res = []
    for cb in cbs:
        agent = db.query(models.Agent).filter(models.Agent.id == cb.agent_id).first()
        res.append({
            "agent_id": cb.agent_id,
            "agent_code": agent.agent_code if agent else "AG-000",
            "name": agent.name if agent else "Agent",
            "state": cb.state,
            "trigger_reason": cb.trigger_reason,
            "tripped_at": cb.tripped_at
        })
    return res
