"""
Celery Background Tasks for External Isolated Sandbox Execution Provider.
Handles asynchronous sandbox job dispatch and periodic purging of expired
execution artifacts and ephemeral workspaces.
"""

import datetime
import logging
from typing import Dict, Any, Optional

from celery_app import celery_app
from database import SessionLocal
import models
from config import settings
from services.sandbox_service import get_sandbox_provider

logger = logging.getLogger("agentguard.tasks.sandbox")


@celery_app.task(name="tasks.sandbox_tasks.cleanup_expired_sandbox_artifacts_task")
def cleanup_expired_sandbox_artifacts_task(
    org_id_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Periodic task to clean up old sandbox workspaces and execution artifacts
    older than SANDBOX_ARTIFACT_RETENTION_HOURS.
    """
    db = SessionLocal()
    provider = get_sandbox_provider()
    try:
        now = datetime.datetime.utcnow()
        retention_hours = getattr(settings, "SANDBOX_ARTIFACT_RETENTION_HOURS", 24)
        cutoff = now - datetime.timedelta(hours=retention_hours)

        query = db.query(models.SandboxExecutionJob).filter(
            models.SandboxExecutionJob.completed_at != None,
            models.SandboxExecutionJob.completed_at < cutoff,
            models.SandboxExecutionJob.cleanup_status != "PURGED"
        )
        if org_id_filter:
            query = query.filter(models.SandboxExecutionJob.org_id == org_id_filter)

        jobs_to_purge = query.limit(200).all()
        purged_count = 0

        for job in jobs_to_purge:
            try:
                provider.cleanup(job.execution_id)
                job.cleanup_status = "PURGED"
                purged_count += 1
            except Exception as e:
                logger.warning(f"Error purging artifacts for execution {job.execution_id}: {e}")

        if purged_count > 0:
            db.commit()

        logger.info(f"[Sandbox Cleanup] Successfully purged {purged_count} expired sandbox execution artifacts.")
        return {
            "status": "COMPLETED",
            "purged_count": purged_count,
            "cutoff_timestamp": cutoff.isoformat(),
            "timestamp": now.isoformat()
        }
    except Exception as e:
        logger.error(f"[Sandbox Cleanup Error] Failed to purge artifacts: {e}")
        db.rollback()
        return {
            "status": "ERROR",
            "error": str(e),
            "purged_count": 0
        }
    finally:
        db.close()
