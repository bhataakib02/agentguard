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
from services.tool_proxy_service import tool_proxy_service
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
            setattr(delivery, "status", "DEAD_LETTER")
            setattr(delivery, "error_message", "Webhook endpoint not found or deleted")
            db.commit()
            return {"status": "DEAD_LETTER", "error": "Endpoint not found"}

        if not bool(getattr(endpoint, "is_active", True)):
            setattr(delivery, "status", "FAILED")
            setattr(delivery, "error_message", "Webhook endpoint is disabled")
            db.commit()
            return {"status": "SKIPPED", "reason": "Endpoint inactive"}

        # Enforce SSRF protection before dispatch
        is_safe, ssrf_err = validate_webhook_url(str(endpoint.url))
        if not is_safe:
            setattr(delivery, "status", "DEAD_LETTER")
            setattr(delivery, "error_message", f"SSRF Protection: {ssrf_err}")
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
        timestamp_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        full_payload = {
            "event_id": payload_data.get("event_id") or str(uuid.uuid4()),
            "event_type": str(delivery.event_type),
            "timestamp": timestamp_str,
            "organization_id": str(endpoint.org_id),
            "resource_type": payload_data.get("resource_type", "governance"),
            "resource_id": payload_data.get("resource_id"),
            "data": payload_data.get("data", payload_data)
        }
        payload_bytes = json.dumps(full_payload, separators=(',', ':'), default=str).encode("utf-8")

        from core.security import decrypt_secret_at_rest
        raw_key = str(endpoint.secret_key) if getattr(endpoint, "secret_key", None) else None
        if raw_key:
            if raw_key.startswith("enc:aesgcm:"):
                signing_key = decrypt_secret_at_rest(raw_key)
                if not signing_key:
                    logger.error(f"[dispatch_webhook_task] Decryption failed for webhook {endpoint.id} secret. Failing closed.")
                    setattr(delivery, "status", "FAILED")
                    setattr(delivery, "error_message", "Cryptographic integrity failure: webhook secret could not be decrypted.")
                    db.commit()
                    return {"status": "FAILED", "error": "Decryption failed (tampered ciphertext)"}
            else:
                signing_key = raw_key
        else:
            signing_key = str(endpoint.secret_hash or "")

        signature = compute_webhook_signature(str(signing_key), payload_bytes, timestamp_str)

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "AgentGuard-Webhook-Worker/1.0",
            "X-AgentGuard-Event": str(delivery.event_type),
            "X-AgentGuard-Timestamp": timestamp_str,
            "X-AgentGuard-Signature": signature if signature.startswith("sha256=") else f"sha256={signature}",
            "X-AgentGuard-Delivery": str(delivery.id),
        }

        # Update status to DELIVERING
        setattr(delivery, "status", "DELIVERING")
        raw_attempts = getattr(delivery, "attempt_count", 0)
        curr_attempts = int(raw_attempts or 0) + 1
        setattr(delivery, "attempt_count", curr_attempts)
        db.commit()

        # Execute HTTP POST with DNS rebinding and redirect protection
        dispatch_res = tool_proxy_service.safe_dispatch_request(
            str(endpoint.url),
            method="POST",
            data=payload_bytes,
            headers=headers,
            timeout=WEBHOOK_TIMEOUT_SECONDS
        )

        if dispatch_res.get("ssrf_blocked"):
            setattr(delivery, "status", "DEAD_LETTER")
            setattr(delivery, "error_message", f"SSRF Protection: {dispatch_res.get('reason') or dispatch_res.get('error')}")
            db.commit()

            audit = models.AuditLog(
                event_type="WEBHOOK_SSRF_BLOCKED",
                actor_type="SYSTEM",
                actor_id="WEBHOOK_WORKER",
                action=f"Blocked webhook dispatch to prohibited destination: {endpoint.url}",
                resource=f"webhook:{endpoint.id}",
                result="BLOCKED",
                metadata_json={"delivery_id": str(delivery.id), "reason": dispatch_res.get("reason")}
            )
            db.add(audit)
            db.commit()
            return {"status": "SSRF_BLOCKED", "reason": dispatch_res.get("reason")}

        setattr(delivery, "response_code", dispatch_res.get("status_code"))
        resp_preview = (dispatch_res.get("response_text") or "")[:500] if dispatch_res.get("response_text") else None
        setattr(delivery, "response_body_preview", resp_preview)

        if dispatch_res.get("is_redirect"):
            last_err = str(dispatch_res.get("error") or "Automatic redirects are blocked for SSRF protection")
        elif dispatch_res.get("success"):
            setattr(delivery, "status", "DELIVERED")
            setattr(delivery, "delivered_at", datetime.datetime.now(datetime.timezone.utc))
            setattr(delivery, "error_message", None)
            setattr(delivery, "next_attempt_at", None)
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
                    "response_code": dispatch_res.get("status_code"),
                    "attempt_count": delivery.attempt_count
                }
            )
            db.add(audit)
            db.commit()
            return {"status": "DELIVERED", "response_code": dispatch_res.get("status_code")}
        else:
            last_err = str(dispatch_res.get("error") or "Outbound delivery failed")

        # Failure / Retry logic
        setattr(delivery, "error_message", last_err)
        if curr_attempts < max_attempts:
            setattr(delivery, "status", "RETRYING")
            # Bounded exponential backoff: 30s, 120s, 480s
            backoff_secs = 30 * (4 ** max(0, curr_attempts - 1))
            setattr(delivery, "next_attempt_at", datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=backoff_secs))
            db.commit()

            logger.warning(
                f"[dispatch_webhook_task] Delivery {delivery.id} failed (attempt {curr_attempts}). "
                f"Retrying in {backoff_secs}s. Error: {last_err}"
            )

            # Retry via Celery countdown if not eager
            try:
                self.retry(countdown=backoff_secs, exc=Exception(last_err))
            except Exception:
                # If retry raised or eager mode
                pass

            return {"status": "RETRY_SCHEDULED", "attempt": curr_attempts, "next_attempt_seconds": backoff_secs}
        else:
            # Exhausted retries -> DEAD_LETTER
            setattr(delivery, "status", "DEAD_LETTER")
            setattr(delivery, "next_attempt_at", None)
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
            return {"status": "DEAD_LETTER", "attempts": curr_attempts, "error": last_err}

    finally:
        db.close()


@celery_app.task(name="tasks.webhook_tasks.retry_pending_webhooks_task")
def retry_pending_webhooks_task() -> Dict[str, Any]:
    """
    Periodic task to poll and enqueue due retry webhooks whose next_attempt_at is in the past.
    """
    db = SessionLocal()
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        due_deliveries = db.query(models.WebhookDelivery).filter(
            models.WebhookDelivery.status.in_(["RETRY_SCHEDULED", "RETRYING"]),
            models.WebhookDelivery.next_attempt_at <= now
        ).limit(50).all()

        enqueued_count = 0
        for d in due_deliveries:
            setattr(d, "status", "QUEUED")
            db.commit()
            getattr(dispatch_webhook_task, "delay")(str(d.id))
            enqueued_count += 1

        return {"status": "SUCCESS", "enqueued_retries": enqueued_count}
    finally:
        db.close()
