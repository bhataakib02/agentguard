from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from engines.policy_engine import policy_engine

router = APIRouter(prefix="/policies", tags=["Governance Policies"])

@router.get("")
def list_policies(db: Session = Depends(get_db)):
    return db.query(models.Policy).all()

@router.post("/evaluate")
def evaluate_policy(
    agent_name: str,
    action: str,
    resource: str,
    amount: float = 0.0,
    risk_score: int = 15,
    agent_status: str = "NORMAL"
):
    return policy_engine.evaluate_action(
        agent_name=agent_name,
        action=action,
        resource=resource,
        amount=amount,
        risk_score=risk_score,
        agent_status=agent_status
    )
