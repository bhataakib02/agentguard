from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from database import get_db
from core.deps import get_current_user
import models
import schemas

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=List[schemas.NotificationSchema])
def list_notifications(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    unread_only: bool = Query(False),
    severity: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns in-app notifications for the authenticated user with strict user-level ownership,
    accurate read states, category/severity filtering, and pagination support.
    """
    query = db.query(models.Notification)

    # Super Admin can view all or filter; regular users are strictly isolated to their own user_id
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.Notification.user_id == current_user.id)

    if unread_only:
        query = query.filter(models.Notification.is_read == False)

    if severity:
        query = query.filter(models.Notification.severity == severity.upper())

    if type:
        query = query.filter(models.Notification.type.ilike(f"%{type}%"))

    items = query.order_by(models.Notification.created_at.desc()).offset(offset).limit(limit).all()
    return items


@router.get("/unread-count", response_model=Dict[str, int])
def get_unread_count(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns real database-backed count of unread notifications for navbar badges.
    """
    query = db.query(models.Notification).filter(models.Notification.is_read == False)
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.Notification.user_id == current_user.id)
    count = query.count()
    return {"unread_count": count}


@router.get("/{id}", response_model=schemas.NotificationSchema)
def get_notification(
    id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves a single notification by ID with strict ownership validation.
    """
    notif = db.query(models.Notification).filter(models.Notification.id == id).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    if current_user.role != "SUPER_ADMIN":
        if not notif.user_id or str(notif.user_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Cannot access notifications of another user"
            )

    return notif


@router.patch("/{id}/read")
def mark_notification_read(
    id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Marks an individual notification as read.
    """
    notif = db.query(models.Notification).filter(models.Notification.id == id).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    if current_user.role != "SUPER_ADMIN":
        if not notif.user_id or str(notif.user_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Cannot modify notifications of another user"
            )

    notif.is_read = True
    db.commit()
    return {"status": "SUCCESS", "id": id, "is_read": True, "read": True}


@router.post("/read-all")
def mark_all_notifications_read(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Marks all unread notifications for current user as read.
    """
    query = db.query(models.Notification)
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.Notification.user_id == current_user.id)
    notifs = query.filter(models.Notification.is_read == False).all()
    for n in notifs:
        n.is_read = True
    db.commit()
    return {"status": "SUCCESS", "count": len(notifs)}


@router.delete("/{id}")
def delete_notification(
    id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Dismisses/deletes a notification with strict ownership enforcement.
    """
    notif = db.query(models.Notification).filter(models.Notification.id == id).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    if current_user.role != "SUPER_ADMIN":
        if not notif.user_id or str(notif.user_id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Cannot delete notifications of another user"
            )

    db.delete(notif)
    db.commit()
    return {"status": "SUCCESS", "id": id, "message": "Notification dismissed"}
