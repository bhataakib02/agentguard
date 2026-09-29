from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from core.deps import get_current_user
import models

router = APIRouter(prefix="/economics", tags=["Agent Economics"])

@router.get("/budgets")
def list_budgets(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Budget)
    if current_user.role != "SUPER_ADMIN":
        query = query.join(models.Agent).filter(models.Agent.org_id == current_user.org_id)
    return query.all()

@router.get("/transactions")
def list_transactions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Transaction)
    if current_user.role != "SUPER_ADMIN":
        query = query.join(models.Agent).filter(models.Agent.org_id == current_user.org_id)
    return query.order_by(models.Transaction.timestamp.desc()).all()
