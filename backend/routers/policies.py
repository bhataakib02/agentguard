from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from core.deps import get_current_user
import models
from engines.policy_engine import policy_engine

router = APIRouter(prefix="/policies", tags=["Governance Policies"])

@router.get("")
def list_policies(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Policy)
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.Policy.org_id == current_user.org_id)
    return query.all()

@router.post("/evaluate")
def evaluate_policy(
    agent_name: str,
    action: str,
    resource: str,
    amount: float = 0.0,
    risk_score: int = 15,
    agent_status: str = "NORMAL",
    current_user: models.User = Depends(get_current_user)
):
    return policy_engine.evaluate_action(
        agent_name=agent_name,
        action=action,
        resource=resource,
        amount=amount,
        risk_score=risk_score,
        agent_status=agent_status
    )
