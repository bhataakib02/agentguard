"""
Asynchronous Enterprise SIEM Event Forwarding Worker Tasks
Handles distributed batch execution, tenant-isolated audit log serialization,
worker claim concurrency locking, bounded retries with exponential backoff,
SSRF re-validation, and truthful dead-letter audit tracking.
"""

import uuid
import datetime
import logging
from typing import Dict, Any, Optional
import requests
from sqlalchemy import or_, and_
from celery_app import celery_app
from database import SessionLocal
import models
from services.notification_service import validate_webhook_url
from services.siem_forwarder_service import (
    resolve_siem_config,
    get_adapter,
    sanitize_error,
    SIEM_CONNECT_TIMEOUT_SECONDS,
    SIEM_READ_TIMEOUT_SECONDS,
)

logger = logging.getLogger("agentguard.tasks.siem")
MAX_SIEM_RETRIES = 3


@celery_app.task(bind=True, name="tasks.siem_tasks.forward_siem_batch_task", max_retries=MAX_SIEM_RETRIES)
def forward_siem_batch_task(self, delivery_id: str, max_attempts: int = MAX_SIEM_RETRIES) -> Dict[str, Any]:
    """
    Durable Celery task to dispatch an audit event batch to the configured SIEM collector.
    Guarantees at-least-once delivery with worker claim concurrency locking,
    strict tenant isolation, and sanitized error reporting.
    """
    db = SessionLocal()
    try:
        delivery = db.query(models.SiemDelivery).filter(models.SiemDelivery.id == delivery_id).first()
        if not delivery:
            logger.error(f"[forward_siem_batch_task] SiemDelivery record not found: {delivery_id}")
            return {"status": "NOT_FOUND", "delivery_id": delivery_id}

        # Idempotency check: if already completed, exit cleanly
        if delivery.status in ("DELIVERED", "SUCCESS"):
            logger.info(f"[forward_siem_batch_task] Delivery {delivery_id} already completed ({delivery.status}). Skipping.")
            return {"status": "ALREADY_COMPLETED", "delivery_id": delivery_id}

        # Atomic Concurrency Claim:
        # Prevents concurrent workers from simultaneously dispatching the exact same batch
        worker_lock = uuid.uuid4().hex
        now = datetime.datetime.utcnow()
        stale_lock_cutoff = now - datetime.timedelta(minutes=5)

        claimed_rows = db.query(models.SiemDelivery).filter(
            models.SiemDelivery.id == delivery_id,
            or_(
                models.SiemDelivery.status.in_(["PENDING", "RETRYING", "RETRY_SCHEDULED", "QUEUED"]),
                and_(
                    models.SiemDelivery.status == "CLAIMED",
                    models.SiemDelivery.locked_at < stale_lock_cutoff
                )
            )
        ).update({
            "status": "CLAIMED",
            "lock_token": worker_lock,
            "locked_at": now,
            "attempt_count": models.SiemDelivery.attempt_count + 1
        }, synchronize_session=False)
        db.commit()

        if claimed_rows == 0:
            logger.info(f"[forward_siem_batch_task] Delivery {delivery_id} is already claimed or handled by another worker.")
            return {"status": "ALREADY_CLAIMED", "delivery_id": delivery_id}

        # Reload delivery record after claim
        delivery = db.query(models.SiemDelivery).filter(models.SiemDelivery.id == delivery_id).first()

        # 1. Resolve SIEM collector configuration
        cfg = resolve_siem_config(db, org_id=str(delivery.org_id))
        if not cfg.configured:
            delivery.status = "DEAD_LETTER"
            delivery.error_message = "SIEM collector is NOT_CONFIGURED"
            db.commit()
            return {"status": "NOT_CONFIGURED", "delivery_id": delivery_id}

        # 2. SSRF Destination Safety Check
        is_safe, ssrf_err = validate_webhook_url(cfg.collector_url)
        if not is_safe:
            delivery.status = "DEAD_LETTER"
            delivery.error_message = f"SSRF Protection: {ssrf_err}"
            db.commit()

            audit = models.AuditLog(
                org_id=delivery.org_id,
                event_type="SIEM_SSRF_BLOCKED",
                actor_type="SYSTEM",
                actor_id="SIEM_WORKER",
                action=f"Blocked SIEM dispatch to prohibited destination: {cfg.collector_url}",
                resource=f"siem_delivery:{delivery.id}",
                result="BLOCKED",
                metadata_json={"delivery_id": str(delivery.id), "reason": ssrf_err}
            )
            db.add(audit)
            db.commit()
            return {"status": "SSRF_BLOCKED", "reason": ssrf_err}

        # 3. Retrieve eligible audit events strictly within the authorized organization scope
        limit_size = delivery.event_count if delivery.event_count > 0 else cfg.batch_size
        audit_query = db.query(models.AuditLog).filter(
            models.AuditLog.org_id == delivery.org_id
        )
        events = audit_query.order_by(models.AuditLog.timestamp.desc()).limit(limit_size).all()

        # Invariant: Prevent tenant A's events from entering tenant B's payload
        for ev in events:
            if str(ev.org_id) != str(delivery.org_id):
                logger.critical(f"[forward_siem_batch_task] Tenant isolation violation: Event org {ev.org_id} != Delivery org {delivery.org_id}")
                delivery.status = "FAILED"
                delivery.error_message = "Cross-tenant isolation violation detected"
                db.commit()
                return {"status": "TENANT_VIOLATION_ABORTED"}

        if not events:
            delivery.status = "DELIVERED"
            delivery.delivered_at = datetime.datetime.utcnow()
            delivery.event_count = 0
            delivery.error_message = None
            db.commit()
            return {"status": "DELIVERED", "event_count": 0, "message": "No audit events to forward"}

        delivery.event_count = len(events)
        delivery.start_event_id = str(events[-1].id)
        delivery.end_event_id = str(events[0].id)
        delivery.format = delivery.format or cfg.format_type
        delivery.provider = cfg.provider
        db.commit()

        # 4. Prepare batch payload using the appropriate provider adapter
        adapter = get_adapter(cfg.provider)
        target_url, headers, body_bytes = adapter.prepare_request(
            events=events,
            collector_url=cfg.collector_url,
            auth_token=cfg.auth_token,
            format_type=delivery.format,
            batch_id=delivery.batch_id
        )

        delivery.status = "DELIVERING"
        db.commit()

        # 5. Dispatch HTTP POST to external collector with bounded timeouts
        last_err = None
        try:
            resp = requests.post(
                target_url,
                data=body_bytes,
                headers=headers,
                timeout=(SIEM_CONNECT_TIMEOUT_SECONDS, SIEM_READ_TIMEOUT_SECONDS)
            )
            delivery.response_code = resp.status_code
            if 200 <= resp.status_code < 300:
                delivery.status = "DELIVERED"
                delivery.delivered_at = datetime.datetime.utcnow()
                delivery.error_message = None
                delivery.next_attempt_at = None
                db.commit()

                # Record immutable audit log for delivery provenance
                audit = models.AuditLog(
                    org_id=delivery.org_id,
                    event_type="SIEM_BATCH_DELIVERED",
                    actor_type="SYSTEM",
                    actor_id="SIEM_WORKER",
                    action=f"SIEM batch delivered ({delivery.format}): {delivery.batch_id}",
                    resource=f"siem_delivery:{delivery.id}",
                    result="DELIVERED",
                    metadata_json={
                        "delivery_id": str(delivery.id),
                        "batch_id": delivery.batch_id,
                        "provider": cfg.provider,
                        "event_count": len(events),
                        "response_code": resp.status_code
                    }
                )
                db.add(audit)
                db.commit()

                return {
                    "status": "DELIVERED",
                    "delivery_id": str(delivery.id),
                    "response_code": resp.status_code,
                    "events_forwarded": len(events)
                }
            else:
                last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)}"
            delivery.response_code = None

        # 6. Retry & Dead-Letter handling with sanitized error messages
        sanitized_err = sanitize_error(last_err)
        delivery.error_message = sanitized_err

        if delivery.attempt_count < max_attempts:
            delivery.status = "RETRYING"
            # Exponential backoff: 15s, 60s, 240s
            backoff_secs = 15 * (4 ** (delivery.attempt_count - 1))
            delivery.next_attempt_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=backoff_secs)
            db.commit()

            logger.warning(
                f"[forward_siem_batch_task] Delivery {delivery.id} failed (attempt {delivery.attempt_count}). "
                f"Retrying in {backoff_secs}s. Error: {sanitized_err}"
            )

            try:
                self.retry(countdown=backoff_secs, exc=Exception(sanitized_err))
            except Exception:
                pass

            return {
                "status": "RETRY_SCHEDULED",
                "delivery_id": str(delivery.id),
                "attempt": delivery.attempt_count,
                "next_attempt_seconds": backoff_secs,
                "error": sanitized_err
            }
        else:
            # Retries exhausted -> DEAD_LETTER
            delivery.status = "DEAD_LETTER"
            delivery.next_attempt_at = None
            db.commit()

            audit = models.AuditLog(
                org_id=delivery.org_id,
                event_type="SIEM_BATCH_DEAD_LETTER",
                actor_type="SYSTEM",
                actor_id="SIEM_WORKER",
                action=f"SIEM batch forwarding exhausted retries: {delivery.batch_id}",
                resource=f"siem_delivery:{delivery.id}",
                result="DEAD_LETTER",
                metadata_json={
                    "delivery_id": str(delivery.id),
                    "batch_id": delivery.batch_id,
                    "attempts": delivery.attempt_count,
                    "last_error": sanitized_err
                }
            )
            db.add(audit)
            db.commit()

            return {
                "status": "DEAD_LETTER",
                "delivery_id": str(delivery.id),
                "attempts": delivery.attempt_count,
                "error": sanitized_err
            }

    finally:
        db.close()


@celery_app.task(name="tasks.siem_tasks.retry_pending_siem_deliveries_task")
def retry_pending_siem_deliveries_task() -> Dict[str, Any]:
    """
    Periodic task to poll and enqueue due SIEM batches whose next_attempt_at has passed.
    """
    db = SessionLocal()
    try:
        now = datetime.datetime.utcnow()
        due_deliveries = db.query(models.SiemDelivery).filter(
            models.SiemDelivery.status.in_(["RETRYING", "RETRY_SCHEDULED"]),
            models.SiemDelivery.next_attempt_at <= now
        ).limit(50).all()

        enqueued_count = 0
        for d in due_deliveries:
            d.status = "QUEUED"
            db.commit()
            forward_siem_batch_task.delay(str(d.id))
            enqueued_count += 1

        return {"status": "SUCCESS", "enqueued_retries": enqueued_count}
    finally:
        db.close()
