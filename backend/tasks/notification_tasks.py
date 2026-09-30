"""
Phase 6D: Notification Worker Tasks
Handles asynchronous dispatch of external notifications (email delivery)
preserving database notification records as authoritative source of truth.
"""

import logging
from typing import Dict, Any, Optional
from celery_app import celery_app
from database import SessionLocal
import models
from services.email_service import email_service

logger = logging.getLogger("agentguard.tasks.notifications")


@celery_app.task(name="tasks.notification_tasks.deliver_notification_task")
def deliver_notification_task(
    notification_id: str,
    recipient_email: Optional[str] = None
) -> Dict[str, Any]:
    """
    Asynchronously delivers a notification via email if recipient is provided
    and email provider is configured.
    """
    db = SessionLocal()
    try:
        notif = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
        if not notif:
            return {"status": "NOT_FOUND", "notification_id": notification_id}

        email_status = "NOT_REQUESTED"
        if recipient_email:
            res = email_service.send_email(
                to_email=recipient_email,
                subject=f"[AgentGuard {notif.severity}] {notif.title}",
                body_text=f"{notif.title}\n\n{notif.message}\n\nSeverity: {notif.severity}"
            )
            email_status = res.get("status", "FAILED")

        return {
            "status": "PROCESSED",
            "notification_id": str(notif.id),
            "email_status": email_status
        }
    finally:
        db.close()
