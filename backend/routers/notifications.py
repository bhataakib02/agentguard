from fastapi import APIRouter, Depends, HTTPException, status
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

@router.patch("/{id}/read")
def mark_notification_read(
    id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notif = db.query(models.Notification).filter(models.Notification.id == id).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    if current_user.role != "SUPER_ADMIN" and notif.user_id and str(notif.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    notif.is_read = True
    db.commit()
    return {"status": "SUCCESS", "id": id, "is_read": True}

@router.post("/read-all")
def mark_all_notifications_read(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Notification)
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.Notification.user_id == current_user.id)
    notifs = query.filter(models.Notification.is_read == False).all()
    for n in notifs:
        n.is_read = True
    db.commit()
    return {"status": "SUCCESS", "count": len(notifs)}

