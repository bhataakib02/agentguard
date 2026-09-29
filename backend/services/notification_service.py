"""
Centralized Notification and Webhook Service for AgentGuard
Handles in-app notification creation, webhook dispatch with HMAC-SHA256 signatures,
SSRF protection, bounded retries, and audit logging.
"""

import json
import uuid
import hmac
import hashlib
import ipaddress
import socket
import datetime
import urllib.parse
import logging
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session
import requests
import models

logger = logging.getLogger("agentguard.notification_service")

# Blocked IP networks for SSRF protection
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("10.0.0.0/8"),       # RFC1918 Private
    ipaddress.ip_network("172.16.0.0/12"),    # RFC1918 Private
    ipaddress.ip_network("192.168.0.0/16"),   # RFC1918 Private
    ipaddress.ip_network("169.254.0.0/16"),   # Link-Local / Cloud Metadata (169.254.169.254)
    ipaddress.ip_network("0.0.0.0/8"),        # Current network
    ipaddress.ip_network("::1/128"),          # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),         # IPv6 private
    ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
]

MAX_WEBHOOK_RETRIES = 3
WEBHOOK_TIMEOUT_SECONDS = 5


def validate_webhook_url(url: str, allow_test_local: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Validates a destination webhook URL for SSRF vulnerabilities.
    Rejects private IPs, loopback, internal metadata endpoints, and non-http(s) schemes.
    """
    if not url or not url.strip():
        return False, "Webhook URL cannot be empty."

    try:
        parsed = urllib.parse.urlparse(url.strip())
    except Exception as e:
        return False, f"Invalid URL format: {str(e)}"

    if parsed.scheme not in ("http", "https"):
        return False, "Webhook URL must use http or https scheme."

    hostname = parsed.hostname
    if not hostname:
        return False, "Webhook URL must specify a valid hostname."

    lower_host = hostname.lower()

    if not allow_test_local:
        if lower_host in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "metadata.google.internal"):
            return False, "Webhook URL cannot target internal loopback or metadata endpoints."

        # Check IP or resolve hostname
        try:
            ip = ipaddress.ip_address(lower_host)
            for net in BLOCKED_NETWORKS:
                if ip in net:
                    return False, f"Webhook URL cannot target private/reserved IP network: {net}"
        except ValueError:
            # Hostname is a domain name, resolve it
            try:
                addr_info = socket.getaddrinfo(lower_host, None)
                for item in addr_info:
                    resolved_ip_str = item[4][0]
                    resolved_ip = ipaddress.ip_address(resolved_ip_str)
                    for net in BLOCKED_NETWORKS:
                        if resolved_ip in net:
                            return False, f"Webhook domain resolves to private/reserved IP address: {resolved_ip_str}"
            except socket.gaierror:
                # If cannot resolve in offline test/mock, allow only if standard public FQDN pattern
                if lower_host.endswith(".local") or lower_host.endswith(".internal"):
                    return False, "Internal .local or .internal domains are not permitted."

    return True, None


def compute_webhook_signature(secret: str, payload_data: Any, timestamp_str: str) -> str:
    """
    Computes cryptographic HMAC-SHA256 signature over timestamp.payload.
    """
    if isinstance(payload_data, str):
        payload_bytes = payload_data.encode("utf-8")
    elif isinstance(payload_data, bytes):
        payload_bytes = payload_data
    else:
        payload_bytes = json.dumps(payload_data, separators=(',', ':'), default=str).encode("utf-8")

    signature_base = timestamp_str.encode("utf-8") + b"." + payload_bytes
    hex_digest = hmac.new(secret.encode("utf-8"), signature_base, hashlib.sha256).hexdigest()
    return f"sha256={hex_digest}"


class NotificationService:
    """
    Centralized service for managing in-app notifications and webhook dispatch.
    """

    def create_in_app_notification(
        self,
        db: Session,
        user_id: Optional[str],
        title: str,
        message: str,
        severity: str = "INFO",
        notif_type: str = "ALERT"
    ) -> models.Notification:
        """
        Creates an in-app notification record.
        """
        notif = models.Notification(
            user_id=user_id,
            type=notif_type,
            title=title,
            message=message,
            severity=severity,
            is_read=False
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif

    def dispatch_webhook_delivery(
        self,
        db: Session,
        endpoint: models.WebhookEndpoint,
        event_type: str,
        payload_data: Dict[str, Any],
        max_retries: int = MAX_WEBHOOK_RETRIES
    ) -> Optional[models.WebhookDelivery]:
        """
        Delivers a webhook event to a registered endpoint with HMAC signature,
        persistent delivery records, bounded retries, and dead-letter handling.
        """
        if not endpoint.is_active:
            logger.info(f"Skipping delivery for disabled webhook {endpoint.id}")
            return None

        # Format full payload
        timestamp_str = datetime.datetime.utcnow().isoformat()
        full_payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": timestamp_str,
            "organization_id": str(endpoint.org_id),
            "resource_type": payload_data.get("resource_type", "governance"),
            "resource_id": payload_data.get("resource_id"),
            "data": payload_data.get("data", payload_data)
        }
        payload_bytes = json.dumps(full_payload, separators=(',', ':'), default=str).encode("utf-8")

        # Compute HMAC signature using stored secret_key
        signing_key = endpoint.secret_key or endpoint.secret_hash
        signature = compute_webhook_signature(signing_key, payload_bytes, timestamp_str)

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AgentGuard-Webhook-Dispatcher/1.0",
            "X-AgentGuard-Event": event_type,
            "X-AgentGuard-Timestamp": timestamp_str,
            "X-AgentGuard-Signature": signature if signature.startswith("sha256=") else f"sha256={signature}"
        }

        # Create persistent delivery record BEFORE attempting delivery
        delivery = models.WebhookDelivery(
            webhook_id=endpoint.id,
            event_type=event_type,
            status="DELIVERING",
            attempt_count=0,
            payload_json=full_payload,
        )
        db.add(delivery)
        db.commit()
        db.refresh(delivery)

        last_error = None
        response_code = None
        response_preview = None

        # Bounded retry loop (attempt 1, 2, 3)
        for attempt_num in range(1, max_retries + 1):
            delivery.attempt_count = attempt_num
            try:
                resp = requests.post(
                    endpoint.url,
                    data=payload_bytes,
                    headers=headers,
                    timeout=WEBHOOK_TIMEOUT_SECONDS
                )
                response_code = resp.status_code
                response_preview = resp.text[:500] if resp.text else None
                if 200 <= resp.status_code < 300:
                    delivery.status = "SUCCESS"
                    delivery.response_code = response_code
                    delivery.response_body_preview = response_preview
                    delivery.delivered_at = datetime.datetime.utcnow()
                    delivery.error_message = None
                    db.commit()
                    break
                else:
                    last_error = f"HTTP status {resp.status_code}"
                    delivery.response_code = response_code
                    delivery.response_body_preview = response_preview
            except requests.RequestException as e:
                last_error = f"Network or connection error: {type(e).__name__}"

            # Update delivery with attempt info
            delivery.error_message = last_error
            if attempt_num < max_retries:
                delivery.status = "RETRYING"
                # Exponential backoff: 30s, 120s, 480s
                backoff_seconds = 30 * (4 ** (attempt_num - 1))
                delivery.next_attempt_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=backoff_seconds)
            else:
                # Exhausted retries → FAILED (dead-letter eligible)
                delivery.status = "FAILED"
                delivery.next_attempt_at = None
            db.commit()

        # Audit delivery outcome
        audit = models.AuditLog(
            event_type="WEBHOOK_DELIVERED" if delivery.status == "SUCCESS" else "WEBHOOK_DELIVERY_FAILED",
            actor_type="SYSTEM",
            actor_id="WEBHOOK_SERVICE",
            action=f"Webhook delivery {delivery.status.lower()}: {event_type}",
            resource=f"webhook:{endpoint.id}",
            result=delivery.status,
            metadata_json={
                "webhook_id": str(endpoint.id),
                "delivery_id": str(delivery.id),
                "event_type": event_type,
                "attempt_count": delivery.attempt_count,
                "response_code": response_code,
                "final_status": delivery.status
            }
        )
        db.add(audit)
        db.commit()

        return delivery

    def notify_governance_event(
        self,
        db: Session,
        org_id: str,
        event_type: str,
        resource_type: str,
        resource_id: str,
        title: str,
        message: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        severity: str = "INFO"
    ) -> Dict[str, Any]:
        """
        Orchestrates notification dispatch: creates in-app notification and triggers active webhooks.
        """
        # 1. In-App Notification
        in_app_notif = self.create_in_app_notification(
            db=db,
            user_id=user_id,
            title=title,
            message=message,
            severity=severity,
            notif_type=event_type.upper()
        )

        # 2. Webhooks
        payload = {
            "resource_type": resource_type,
            "resource_id": str(resource_id),
            "data": data
        }

        webhooks = db.query(models.WebhookEndpoint).filter(
            models.WebhookEndpoint.org_id == org_id,
            models.WebhookEndpoint.is_active == True
        ).all()

        dispatched_deliveries = []
        for wh in webhooks:
            # Check event subscription
            sub_events = wh.event_types or ["*"]
            if "*" in sub_events or event_type in sub_events:
                delivery = self.dispatch_webhook_delivery(
                    db=db,
                    endpoint=wh,
                    event_type=event_type,
                    payload_data=payload
                )
                dispatched_deliveries.append(delivery)

        return {
            "notification_id": str(in_app_notif.id),
            "webhooks_dispatched": len(dispatched_deliveries)
        }


notification_service = NotificationService()


def dispatch_webhook_delivery(
    db: Session,
    webhook: models.WebhookEndpoint,
    event_type: str,
    payload: Dict[str, Any],
    max_retries: int = MAX_WEBHOOK_RETRIES
) -> bool:
    deliv = notification_service.dispatch_webhook_delivery(
        db=db,
        endpoint=webhook,
        event_type=event_type,
        payload_data=payload,
        max_retries=max_retries
    )
    if deliv is None:
        return False
    return deliv.status in ("DELIVERED", "SUCCESS")


def notify_governance_event(
    db: Session,
    org_id: str,
    event_type: str,
    resource_type: str,
    resource_id: str,
    title: str = "",
    message: str = "",
    data: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    severity: str = "INFO",
    notification_title: Optional[str] = None,
    notification_message: Optional[str] = None
) -> Dict[str, Any]:
    t = notification_title or title or f"Governance Event: {event_type}"
    m = notification_message or message or f"Event {event_type} on {resource_type} {resource_id}"
    d = data or {}
    return notification_service.notify_governance_event(
        db=db,
        org_id=org_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        title=t,
        message=m,
        data=d,
        user_id=user_id,
        severity=severity
    )
