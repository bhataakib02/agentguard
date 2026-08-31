from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(prefix="/economics", tags=["Agent Economics"])

@router.get("/budgets")
def list_budgets(db: Session = Depends(get_db)):
    return db.query(models.Budget).all()

@router.get("/transactions")
def list_transactions(db: Session = Depends(get_db)):
    return db.query(models.Transaction).order_by(models.Transaction.timestamp.desc()).all()
