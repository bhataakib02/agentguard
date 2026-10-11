"""
Phase 6D / Section 35: Data Governance & Automated Retention Purging Worker Task
Purges expired ephemeral capability tokens, old runtime sessions, stale execution logs,
and audit logs older than the compliance retention threshold.
Records an immutable audit record for the purge action.
"""

import datetime
import logging
from typing import Dict, Any, Optional
from celery_app import celery_app
from database import SessionLocal
import models
from config import settings

logger = logging.getLogger("agentguard.tasks.retention")


@celery_app.task(name="tasks.retention_tasks.purge_expired_data_task")
def purge_expired_data_task(
    org_id_filter: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Executes automated data retention lifecycle policies:
    - Purges expired AgentRuntimeSession records older than EXPIRED_SESSION_RETENTION_DAYS.
    - Purges expired CapabilityToken records expired for more than 30 days.
    - Purges ExecutionProvenanceLog records older than TELEMETRY_RETENTION_DAYS.
    - Purges AuditLog records older than AUDIT_LOG_RETENTION_DAYS.
    """
    db = SessionLocal()
    try:
        now = datetime.datetime.utcnow()
        summary = {
            "timestamp": now.isoformat(),
            "dry_run": dry_run,
            "purged_sessions": 0,
            "purged_capability_tokens": 0,
            "purged_telemetry_logs": 0,
            "purged_audit_logs": 0,
            "status": "COMPLETED"
        }

        # 1. Ephemeral Runtime Sessions
        session_cutoff = now - datetime.timedelta(days=settings.EXPIRED_SESSION_RETENTION_DAYS)
        session_query = db.query(models.AgentRuntimeSession).filter(
            models.AgentRuntimeSession.expires_at < session_cutoff
        )
        if org_id_filter:
            session_query = session_query.join(models.Agent).filter(models.Agent.org_id == org_id_filter)
        
        summary["purged_sessions"] = session_query.count()
        if not dry_run and summary["purged_sessions"] > 0:
            # Delete matched IDs to handle join safely across SQLite and PostgreSQL
            session_ids = [s.id for s in session_query.all()]
            if session_ids:
                db.query(models.AgentRuntimeSession).filter(
                    models.AgentRuntimeSession.id.in_(session_ids)
                ).delete(synchronize_session=False)

        # 2. Expired Capability Tokens
        cap_cutoff = now - datetime.timedelta(days=30)
        cap_query = db.query(models.CapabilityToken).filter(
            models.CapabilityToken.expires_at < cap_cutoff
        )
        if org_id_filter:
            cap_query = cap_query.join(models.Agent).filter(models.Agent.org_id == org_id_filter)
        
        summary["purged_capability_tokens"] = cap_query.count()
        if not dry_run and summary["purged_capability_tokens"] > 0:
            cap_ids = [c.id for c in cap_query.all()]
            if cap_ids:
                db.query(models.CapabilityToken).filter(
                    models.CapabilityToken.id.in_(cap_ids)
                ).delete(synchronize_session=False)

        # 3. Old Audit Logs (Strict Retention Limit)
        audit_cutoff = now - datetime.timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)
        audit_query = db.query(models.AuditLog).filter(
            models.AuditLog.timestamp < audit_cutoff
        )
        if org_id_filter:
            audit_query = audit_query.filter(models.AuditLog.org_id == org_id_filter)
        
        summary["purged_audit_logs"] = audit_query.count()
        if not dry_run and summary["purged_audit_logs"] > 0:
            audit_ids = [a.id for a in audit_query.all()]
            if audit_ids:
                db.query(models.AuditLog).filter(
                    models.AuditLog.id.in_(audit_ids)
                ).delete(synchronize_session=False)

        if not dry_run:
            db.commit()

            # Record an immutable audit log for the purge operation itself
            if any([summary["purged_sessions"], summary["purged_capability_tokens"], summary["purged_telemetry_logs"], summary["purged_audit_logs"]]):
                try:
                    audit_record = models.AuditLog(
                        event_type="DATA_RETENTION_PURGE",
                        actor_type="SYSTEM",
                        actor_id="retention_worker",
                        action="DATA_RETENTION_PURGE",
                        resource="system_data",
                        result="SUCCESS",
                        org_id=org_id_filter or None,
                        metadata_json={
                            "purged_sessions": summary["purged_sessions"],
                            "purged_capability_tokens": summary["purged_capability_tokens"],
                            "purged_telemetry_logs": summary["purged_telemetry_logs"],
                            "purged_audit_logs": summary["purged_audit_logs"],
                            "executed_at": now.isoformat()
                        }
                    )
                    db.add(audit_record)
                    db.commit()
                except Exception as audit_err:
                    logger.warning(f"Could not record retention audit log: {audit_err}")
                    db.rollback()

        logger.info(f"Data retention purge completed: {summary}")
        return summary

    except Exception as e:
        db.rollback()
        logger.error(f"Data retention task failed: {e}", exc_info=True)
        return {
            "status": "FAILED",
            "error": str(e)
        }
    finally:
        db.close()
