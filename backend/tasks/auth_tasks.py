"""
Celery Background Tasks for Authentication and Identity Maintenance.
Handles periodic scrubbing and cleanup of expired/abandoned OTP challenges.
"""
import datetime
import logging
from typing import Dict, Any, Optional

from celery_app import celery_app
from database import SessionLocal
from services.otp_service import OtpService

logger = logging.getLogger("agentguard.tasks.auth")


@celery_app.task(name="tasks.auth_tasks.cleanup_expired_otp_challenges_task")
def cleanup_expired_otp_challenges_task(
    batch_size: int = 500,
    max_batches: Optional[int] = None
) -> Dict[str, Any]:
    """
    Periodic task to clean up and scrub sensitive metadata from expired and abandoned OTP challenges.
    Executes in bounded batches with reliable session lifecycle and multi-worker safety.
    Guarantees zero logging of secrets, passwords, or raw OTP credentials.
    """
    db = SessionLocal()
    try:
        now = datetime.datetime.utcnow()
        cleaned_count = OtpService.cleanup_expired_challenges(
            db=db,
            batch_size=batch_size,
            max_batches=max_batches
        )
        logger.info(f"[AuthCleanup] Successfully processed {cleaned_count} expired/abandoned OTP challenges.")
        return {
            "status": "COMPLETED",
            "cleaned_count": cleaned_count,
            "timestamp": now.isoformat()
        }
    except Exception as e:
        logger.error(f"[AuthCleanup Error] Failed to clean up expired OTP challenges: {type(e).__name__}")
        db.rollback()
        return {
            "status": "ERROR",
            "error": str(e),
            "cleaned_count": 0
        }
    finally:
        db.close()
