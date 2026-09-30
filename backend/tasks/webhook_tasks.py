"""
Phase 6D: Durable Webhook Delivery Worker Tasks
Replaces synchronous delivery loops with persistent Celery task execution,
enforcing SSRF protection, HMAC signing, bounded exponential backoff,
dead-letter queueing, and tenant isolation.
"""

import json
import uuid
import datetime
import logging
from typing import Dict, Any, Optional
import requests
from celery_app import celery_app
from database import SessionLocal
import models
from services.notification_service import (
    validate_webhook_url,
    compute_webhook_signature,
    MAX_WEBHOOK_RETRIES,
    WEBHOOK_TIMEOUT_SECONDS,
)

logger = logging.getLogger("agentguard.tasks.webhook")


@celery_app.task(bind=True, name="tasks.webhook_tasks.dispatch_webhook_task", max_retries=MAX_WEBHOOK_RETRIES)
def dispatch_webhook_task(self, delivery_id: str, max_attempts: int = MAX_WEBHOOK_RETRIES) -> Dict[str, Any]:
    """
    Durable Celery task to dispatch a single webhook delivery with SSRF checks,
    HMAC authentication, exponential backoff, and dead-letter handling.
    """
    db = SessionLocal()
    try:
        delivery = db.query(models.WebhookDelivery).filter(models.WebhookDelivery.id == delivery_id).first()
        if not delivery:
            logger.error(f"[dispatch_webhook_task] Delivery record not found: {delivery_id}")
            return {"status": "NOT_FOUND", "delivery_id": delivery_id}

        # Idempotency check: if already successful, skip
        if delivery.status in ("SUCCESS", "DELIVERED"):
            logger.info(f"[dispatch_webhook_task] Delivery {delivery_id} already completed ({delivery.status}). Skipping.")
            return {"status": "ALREADY_COMPLETED", "delivery_id": delivery_id}

        endpoint = db.query(models.WebhookEndpoint).filter(models.WebhookEndpoint.id == delivery.webhook_id).first()
        if not endpoint:
            delivery.status = "DEAD_LETTER"
            delivery.error_message = "Webhook endpoint not found or deleted"
            db.commit()
            return {"status": "DEAD_LETTER", "error": "Endpoint not found"}

        if not endpoint.is_active:
            delivery.status = "FAILED"
            delivery.error_message = "Webhook endpoint is disabled"
            db.commit()
            return {"status": "SKIPPED", "reason": "Endpoint inactive"}

        # Enforce SSRF protection before dispatch
        is_safe, ssrf_err = validate_webhook_url(endpoint.url)
        if not is_safe:
            delivery.status = "DEAD_LETTER"
            delivery.error_message = f"SSRF Protection: {ssrf_err}"
            db.commit()

            audit = models.AuditLog(
                event_type="WEBHOOK_SSRF_BLOCKED",
                actor_type="SYSTEM",
                actor_id="WEBHOOK_WORKER",
                action=f"Blocked webhook dispatch to prohibited destination: {endpoint.url}",
                resource=f"webhook:{endpoint.id}",
                result="BLOCKED",
                metadata_json={"delivery_id": str(delivery.id), "reason": ssrf_err}
            )
            db.add(audit)
            db.commit()
            return {"status": "SSRF_BLOCKED", "reason": ssrf_err}

        # Prepare payload and HMAC signature
        payload_data = delivery.payload_json or {}
        timestamp_str = datetime.datetime.utcnow().isoformat()
        full_payload = {
            "event_id": payload_data.get("event_id") or str(uuid.uuid4()),
            "event_type": delivery.event_type,
            "timestamp": timestamp_str,
            "organization_id": str(endpoint.org_id),
            "resource_type": payload_data.get("resource_type", "governance"),
            "resource_id": payload_data.get("resource_id"),
            "data": payload_data.get("data", payload_data)
        }
        payload_bytes = json.dumps(full_payload, separators=(',', ':'), default=str).encode("utf-8")

        signing_key = endpoint.secret_key or endpoint.secret_hash
        signature = compute_webhook_signature(signing_key, payload_bytes, timestamp_str)

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AgentGuard-Webhook-Worker/1.0",
            "X-AgentGuard-Event": delivery.event_type,
            "X-AgentGuard-Timestamp": timestamp_str,
            "X-AgentGuard-Signature": signature if signature.startswith("sha256=") else f"sha256={signature}",
            "X-AgentGuard-Delivery": str(delivery.id),
        }

        # Update status to DELIVERING
        delivery.status = "DELIVERING"
        delivery.attempt_count = (delivery.attempt_count or 0) + 1
        db.commit()

        # Execute HTTP POST
        try:
            resp = requests.post(
                endpoint.url,
                data=payload_bytes,
                headers=headers,
                timeout=WEBHOOK_TIMEOUT_SECONDS
            )
            delivery.response_code = resp.status_code
            delivery.response_body_preview = resp.text[:500] if resp.text else None

            if 200 <= resp.status_code < 300:
                delivery.status = "DELIVERED"
                delivery.delivered_at = datetime.datetime.utcnow()
                delivery.error_message = None
                delivery.next_attempt_at = None
                db.commit()

                audit = models.AuditLog(
                    event_type="WEBHOOK_DELIVERED",
                    actor_type="SYSTEM",
                    actor_id="WEBHOOK_WORKER",
                    action=f"Webhook delivered: {delivery.event_type}",
                    resource=f"webhook:{endpoint.id}",
                    result="DELIVERED",
                    metadata_json={
                        "webhook_id": str(endpoint.id),
                        "delivery_id": str(delivery.id),
                        "response_code": resp.status_code,
                        "attempt_count": delivery.attempt_count
                    }
                )
                db.add(audit)
                db.commit()
                return {"status": "DELIVERED", "response_code": resp.status_code}
            else:
                last_err = f"HTTP {resp.status_code}"
        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)}"
            delivery.response_code = None

        # Failure / Retry logic
        delivery.error_message = last_err
        if delivery.attempt_count < max_attempts:
            delivery.status = "RETRYING"
            # Bounded exponential backoff: 30s, 120s, 480s
            backoff_secs = 30 * (4 ** (delivery.attempt_count - 1))
            delivery.next_attempt_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=backoff_secs)
            db.commit()

            logger.warning(
                f"[dispatch_webhook_task] Delivery {delivery.id} failed (attempt {delivery.attempt_count}). "
                f"Retrying in {backoff_secs}s. Error: {last_err}"
            )

            # Retry via Celery countdown if not eager
            try:
                self.retry(countdown=backoff_secs, exc=Exception(last_err))
            except Exception:
                # If retry raised or eager mode
                pass

            return {"status": "RETRY_SCHEDULED", "attempt": delivery.attempt_count, "next_attempt_seconds": backoff_secs}
        else:
            # Exhausted retries -> DEAD_LETTER
            delivery.status = "DEAD_LETTER"
            delivery.next_attempt_at = None
            db.commit()

            audit = models.AuditLog(
                event_type="WEBHOOK_DEAD_LETTER",
                actor_type="SYSTEM",
                actor_id="WEBHOOK_WORKER",
                action=f"Webhook delivery exhausted retries, moved to DEAD_LETTER: {delivery.event_type}",
                resource=f"webhook:{endpoint.id}",
                result="DEAD_LETTER",
                metadata_json={
                    "webhook_id": str(endpoint.id),
                    "delivery_id": str(delivery.id),
                    "attempts": delivery.attempt_count,
                    "last_error": last_err
                }
            )
            db.add(audit)
            db.commit()
            return {"status": "DEAD_LETTER", "attempts": delivery.attempt_count, "error": last_err}

    finally:
        db.close()


@celery_app.task(name="tasks.webhook_tasks.retry_pending_webhooks_task")
def retry_pending_webhooks_task() -> Dict[str, Any]:
    """
    Periodic task to poll and enqueue due retry webhooks whose next_attempt_at is in the past.
    """
    db = SessionLocal()
    try:
        now = datetime.datetime.utcnow()
        due_deliveries = db.query(models.WebhookDelivery).filter(
            models.WebhookDelivery.status.in_(["RETRY_SCHEDULED", "RETRYING"]),
            models.WebhookDelivery.next_attempt_at <= now
        ).limit(50).all()

        enqueued_count = 0
        for d in due_deliveries:
            d.status = "QUEUED"
            db.commit()
            dispatch_webhook_task.delay(str(d.id))
            enqueued_count += 1

        return {"status": "SUCCESS", "enqueued_retries": enqueued_count}
    finally:
        db.close()
