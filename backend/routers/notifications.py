from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from core.deps import get_current_user
import models

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("")
def list_notifications(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Notification)
    if current_user.role != "SUPER_ADMIN" and hasattr(models.Notification, "user_id"):
        query = query.filter(models.Notification.user_id == current_user.id)
    return query.order_by(models.Notification.created_at.desc()).all()
