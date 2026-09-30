"""
Phase 6D: Approval Escalation Worker Task
Identifies overdue approvals and approaching SLA windows.
Enforces strict idempotency to prevent repeated notifications on successive ticks.
"""

import datetime
import logging
from typing import Dict, Any
from celery_app import celery_app
from database import SessionLocal
import models
from services.notification_service import notify_governance_event

logger = logging.getLogger("agentguard.tasks.escalation")


@celery_app.task(name="tasks.escalation_tasks.escalate_approvals_task")
def escalate_approvals_task(org_id_filter: str = None) -> Dict[str, Any]:
    """
    Periodic task to inspect pending approval requests, escalate overdue items,
    and alert on approaching SLA thresholds with strict idempotency.
    """
    db = SessionLocal()
    try:
        now = datetime.datetime.utcnow()
        sla_limit = now - datetime.timedelta(hours=24)
        approaching_sla_limit = now - datetime.timedelta(hours=18)

        query = db.query(models.ApprovalRequest).filter(models.ApprovalRequest.status == "PENDING")
        if org_id_filter:
            query = query.join(models.Agent).filter(models.Agent.org_id == org_id_filter)

        pending_list = query.all()
        overdue_count = 0
        approaching_count = 0
        skipped_idempotent = 0

        for app in pending_list:
            agent = db.query(models.Agent).filter(models.Agent.id == app.agent_id).first()
            target_org_id = str(agent.org_id) if agent else str(org_id_filter or "")

            created_dt = app.created_at
            if created_dt and created_dt.tzinfo is not None:
                created_dt = created_dt.replace(tzinfo=None)

            if not created_dt:
                continue

            # Determine Tier
            if created_dt <= sla_limit:
                tier = "OVERDUE"
                event_type = "approval.overdue"
                notif_title = f"Approval Overdue: {agent.name if agent else 'Agent'}"
                notif_msg = f"Approval request {str(app.id)[:8]} has exceeded the 24-hour SLA window."
                severity = "WARNING"
            elif created_dt <= approaching_sla_limit:
                tier = "APPROACHING_SLA"
                event_type = "approval.approaching_sla"
                notif_title = f"Approval Approaching SLA: {agent.name if agent else 'Agent'}"
                notif_msg = f"Approval request {str(app.id)[:8]} is within 6 hours of SLA breach."
                severity = "INFO"
            else:
                continue

            # Idempotency Check: Check if an audit log or notification already fired for this approval & tier
            # within the past 24 hours
            existing_audit = db.query(models.AuditLog).filter(
                models.AuditLog.event_type == f"APPROVAL_ESCALATED_{tier}",
                models.AuditLog.resource == f"approval_request:{app.id}",
                models.AuditLog.timestamp >= (now - datetime.timedelta(hours=24))
            ).first()

            if existing_audit:
                skipped_idempotent += 1
                continue

            # Send Notification & Dispatch Webhooks
            notify_governance_event(
                db=db,
                org_id=target_org_id,
                event_type=event_type,
                resource_type="approval_request",
                resource_id=str(app.id),
                data={
                    "approval_id": str(app.id),
                    "agent_id": str(app.agent_id),
                    "agent_name": agent.name if agent else "Agent",
                    "reason": app.reason,
                    "amount": app.amount,
                    "created_at": app.created_at.isoformat() if app.created_at else None,
                    "sla_status": tier
                },
                notification_title=notif_title,
                notification_message=notif_msg,
                severity=severity
            )

            # Record Escalation Audit Log for Idempotency tracking
            audit = models.AuditLog(
                event_type=f"APPROVAL_ESCALATED_{tier}",
                actor_type="SYSTEM",
                actor_id="ESCALATION_WORKER",
                action=f"Escalated approval request {app.id} (tier: {tier})",
                resource=f"approval_request:{app.id}",
                result="ESCALATED",
                metadata_json={
                    "approval_id": str(app.id),
                    "agent_id": str(app.agent_id),
                    "tier": tier,
                    "org_id": target_org_id
                }
            )
            db.add(audit)
            db.commit()

            if tier == "OVERDUE":
                overdue_count += 1
            else:
                approaching_count += 1

        return {
            "status": "SUCCESS",
            "overdue_escalated": overdue_count,
            "approaching_sla": approaching_count,
            "skipped_idempotent": skipped_idempotent,
            "total_pending_checked": len(pending_list)
        }

    finally:
        db.close()
