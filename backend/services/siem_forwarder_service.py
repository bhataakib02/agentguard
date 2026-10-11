"""
Enterprise SIEM Log Forwarding Service
Provides provider-specific adapters, SSRF destination validation, credential masking,
sensitive payload redaction, and bounded batch serialization (CEF / JSONL).
"""

import json
import logging
import re
import time
import datetime
from typing import Dict, Any, List, Optional, Tuple
import requests
from sqlalchemy.orm import Session
from config import settings
import models
from services.notification_service import validate_webhook_url

logger = logging.getLogger("agentguard.siem")

# Default timeouts
SIEM_CONNECT_TIMEOUT_SECONDS = 5.0
SIEM_READ_TIMEOUT_SECONDS = 10.0
SIEM_TOTAL_TIMEOUT_SECONDS = 10.0

# Sensitive keys to redact inside audit metadata before dispatch
SENSITIVE_KEY_PATTERNS = re.compile(
    r"(token|secret|password|api_key|private_key|auth|credential|access_token|refresh_token)",
    re.IGNORECASE
)


def redact_sensitive_data(obj: Any) -> Any:
    """
    Recursively redacts sensitive keys in dictionaries or lists.
    """
    if isinstance(obj, dict):
        redacted = {}
        for k, v in obj.items():
            if SENSITIVE_KEY_PATTERNS.search(str(k)):
                redacted[k] = "[REDACTED]"
            else:
                redacted[k] = redact_sensitive_data(v)
        return redacted
    elif isinstance(obj, list):
        return [redact_sensitive_data(item) for item in obj]
    return obj


def mask_secret(secret: Optional[str]) -> Optional[str]:
    """
    Returns a safe masked preview for authentication secrets (e.g., 'sec_****3a1f').
    """
    if not secret:
        return None
    secret_str = str(secret).strip()
    if len(secret_str) <= 6:
        return "****"
    return f"{secret_str[:3]}****{secret_str[-4:]}"


def sanitize_error(err_str: str) -> str:
    """
    Strips raw tokens, authorization strings, and URL query credentials from error messages.
    """
    if not err_str:
        return "Unknown error"
    # Redact Bearer or Splunk tokens
    cleaned = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", r"\1[REDACTED]", err_str)
    cleaned = re.sub(r"(Splunk\s+)[A-Za-z0-9_\-\.]+", r"\1[REDACTED]", cleaned)
    cleaned = re.sub(r"(DD-API-KEY[:=]\s*)[A-Za-z0-9_\-\.]+", r"\1[REDACTED]", cleaned)
    cleaned = re.sub(r"([?&](?:token|key|secret|apiKey)=)[^&\s]+", r"\1[REDACTED]", cleaned)
    return cleaned[:500]


def format_audit_log_cef(log: models.AuditLog) -> str:
    """
    Serializes a single AuditLog record into Common Event Format (CEF:0).
    """
    severity = 8 if log.result in ("BLOCKED", "FAILED") else (6 if log.result == "DENIED" else 3)
    ts_str = log.timestamp.isoformat() if hasattr(log.timestamp, "isoformat") else str(log.timestamp)
    action_safe = str(log.action).replace("|", "_")
    event_type_safe = str(log.event_type).replace("|", "_")
    
    cef_line = (
        f"CEF:0|AgentGuard|SecurityKernel|1.0|{action_safe}|{event_type_safe}|{severity}|"
        f"src={log.actor_id} suser={log.actor_type} act={action_safe} outcome={log.result} "
        f"cs1={log.org_id} cs1Label=OrgId cs2={log.resource} cs2Label=Resource deviceCustomDate1={ts_str}"
    )
    return cef_line


def format_audit_log_json(log: models.AuditLog) -> Dict[str, Any]:
    """
    Serializes a single AuditLog record into a sanitized JSON dictionary.
    """
    ts_str = log.timestamp.isoformat() if hasattr(log.timestamp, "isoformat") else str(log.timestamp)
    raw_meta = log.metadata_json or {}
    sanitized_meta = redact_sensitive_data(raw_meta)
    
    return {
        "id": str(log.id),
        "org_id": str(log.org_id) if log.org_id else None,
        "timestamp": ts_str,
        "event_type": log.event_type,
        "actor_type": log.actor_type,
        "actor_id": log.actor_id,
        "action": log.action,
        "resource": log.resource,
        "result": log.result,
        "metadata": sanitized_meta
    }


class ResolvedSiemConfig:
    def __init__(
        self,
        configured: bool,
        provider: str,
        collector_url: str,
        auth_token: Optional[str] = None,
        format_type: str = "JSONL",
        batch_size: int = 100,
        source: str = "NONE"
    ):
        self.configured = configured
        self.provider = provider
        self.collector_url = collector_url
        self.auth_token = auth_token
        self.format_type = format_type
        self.batch_size = batch_size
        self.source = source


def resolve_siem_config(db: Session, org_id: Optional[str] = None) -> ResolvedSiemConfig:
    """
    Resolves the authoritative SIEM collector configuration.
    Priority:
    1. Tenant DB configuration (`SiemCollectorConfig` with matching `org_id` and `is_active == True`)
    2. Platform DB configuration (`SiemCollectorConfig` with `org_id == None` and `is_active == True`)
    3. Dedicated environment variables (SPLUNK_HEC_URL, DATADOG_API_KEY, SIEM_FORWARDER_URL)
    """
    # 1. Tenant DB config
    if org_id:
        tenant_cfg = db.query(models.SiemCollectorConfig).filter(
            models.SiemCollectorConfig.org_id == org_id,
            models.SiemCollectorConfig.is_active == True
        ).first()
        if tenant_cfg and tenant_cfg.collector_url:
            return ResolvedSiemConfig(
                configured=True,
                provider=tenant_cfg.provider or "GENERIC_HTTP",
                collector_url=tenant_cfg.collector_url,
                auth_token=tenant_cfg.auth_token_encrypted,
                format_type=tenant_cfg.format or "JSONL",
                batch_size=tenant_cfg.batch_size or 100,
                source="TENANT_DB"
            )

    # 2. Platform DB config (org_id is None)
    platform_cfg = db.query(models.SiemCollectorConfig).filter(
        models.SiemCollectorConfig.org_id.is_(None),
        models.SiemCollectorConfig.is_active == True
    ).first()
    if platform_cfg and platform_cfg.collector_url:
        return ResolvedSiemConfig(
            configured=True,
            provider=platform_cfg.provider or "GENERIC_HTTP",
            collector_url=platform_cfg.collector_url,
            auth_token=platform_cfg.auth_token_encrypted,
            format_type=platform_cfg.format or "JSONL",
            batch_size=platform_cfg.batch_size or 100,
            source="PLATFORM_DB"
        )

    # 3. Environment variables
    splunk_url = getattr(settings, "SPLUNK_HEC_URL", "") or ""
    splunk_token = getattr(settings, "SPLUNK_HEC_TOKEN", "") or ""
    if splunk_url and splunk_token:
        return ResolvedSiemConfig(
            configured=True,
            provider="SPLUNK_HEC",
            collector_url=splunk_url,
            auth_token=splunk_token,
            format_type=getattr(settings, "SIEM_FORMAT", "JSONL"),
            batch_size=getattr(settings, "SIEM_BATCH_SIZE", 100),
            source="ENV_SPLUNK"
        )

    datadog_key = getattr(settings, "DATADOG_API_KEY", "") or ""
    datadog_url = getattr(settings, "DATADOG_INTAKE_URL", "https://http-intake.logs.datadoghq.com/api/v2/logs")
    if datadog_key:
        return ResolvedSiemConfig(
            configured=True,
            provider="DATADOG",
            collector_url=datadog_url,
            auth_token=datadog_key,
            format_type="JSONL",
            batch_size=getattr(settings, "SIEM_BATCH_SIZE", 100),
            source="ENV_DATADOG"
        )

    generic_url = getattr(settings, "SIEM_FORWARDER_URL", "") or ""
    generic_token = getattr(settings, "SIEM_AUTH_TOKEN", "") or ""
    if generic_url:
        return ResolvedSiemConfig(
            configured=True,
            provider=getattr(settings, "SIEM_PROVIDER", "GENERIC_HTTP"),
            collector_url=generic_url,
            auth_token=generic_token or None,
            format_type=getattr(settings, "SIEM_FORMAT", "JSONL"),
            batch_size=getattr(settings, "SIEM_BATCH_SIZE", 100),
            source="ENV_GENERIC"
        )

    return ResolvedSiemConfig(
        configured=False,
        provider="NONE",
        collector_url="",
        auth_token=None,
        format_type="JSONL",
        batch_size=100,
        source="NONE"
    )


# ============================================================================
# SIEM PROVIDER ADAPTERS
# ============================================================================

class BaseSiemAdapter:
    def prepare_request(
        self,
        events: List[models.AuditLog],
        collector_url: str,
        auth_token: Optional[str],
        format_type: str,
        batch_id: str
    ) -> Tuple[str, Dict[str, str], bytes]:
        raise NotImplementedError


class GenericHttpAdapter(BaseSiemAdapter):
    """
    Standard HTTP/REST Collector adapter for generic SIEM forwarders (Fluentd, Vector, Logstash, ArcSight).
    Supports NDJSON (JSONL) and CEF text lines.
    """
    def prepare_request(
        self,
        events: List[models.AuditLog],
        collector_url: str,
        auth_token: Optional[str],
        format_type: str,
        batch_id: str
    ) -> Tuple[str, Dict[str, str], bytes]:
        headers = {
            "User-Agent": "AgentGuard-SIEM-Forwarder/1.0",
            "X-AgentGuard-Batch-Id": batch_id,
            "X-AgentGuard-Event-Count": str(len(events)),
        }
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        if format_type.upper() == "CEF":
            headers["Content-Type"] = "text/plain; charset=utf-8"
            lines = [format_audit_log_cef(ev) for ev in events]
            body_bytes = ("\n".join(lines) + "\n").encode("utf-8")
        else:
            headers["Content-Type"] = "application/x-ndjson; charset=utf-8"
            lines = [json.dumps(format_audit_log_json(ev), separators=(",", ":")) for ev in events]
            body_bytes = ("\n".join(lines) + "\n").encode("utf-8")

        return collector_url, headers, body_bytes


class SplunkHecAdapter(BaseSiemAdapter):
    """
    Splunk HTTP Event Collector (HEC) adapter.
    Envelopes audit logs in Splunk HEC event wrappers with timestamp and sourcetype.
    """
    def prepare_request(
        self,
        events: List[models.AuditLog],
        collector_url: str,
        auth_token: Optional[str],
        format_type: str,
        batch_id: str
    ) -> Tuple[str, Dict[str, str], bytes]:
        # Normalizes endpoint to /services/collector/event or /services/collector/raw
        target_url = collector_url
        if "/services/collector" not in target_url:
            target_url = f"{collector_url.rstrip('/')}/services/collector/event"

        headers = {
            "User-Agent": "AgentGuard-SIEM-Splunk/1.0",
            "Content-Type": "application/json",
            "X-AgentGuard-Batch-Id": batch_id,
        }
        if auth_token:
            headers["Authorization"] = f"Splunk {auth_token}"

        splunk_items = []
        for ev in events:
            ev_ts = ev.timestamp.timestamp() if hasattr(ev.timestamp, "timestamp") else time.time()
            if format_type.upper() == "CEF":
                cef_str = format_audit_log_cef(ev)
                payload = {
                    "time": ev_ts,
                    "host": "agentguard-security-kernel",
                    "source": "agentguard:audit",
                    "sourcetype": "cef",
                    "event": cef_str
                }
            else:
                json_data = format_audit_log_json(ev)
                payload = {
                    "time": ev_ts,
                    "host": "agentguard-security-kernel",
                    "source": "agentguard:audit",
                    "sourcetype": "agentguard:audit:json",
                    "event": json_data
                }
            splunk_items.append(json.dumps(payload, separators=(",", ":")))

        body_bytes = ("\n".join(splunk_items) + "\n").encode("utf-8")
        return target_url, headers, body_bytes


class DatadogAdapter(BaseSiemAdapter):
    """
    Datadog Logs Intake API (v2) adapter.
    Dispatches JSON array of logs formatted with ddsource and service metadata.
    """
    def prepare_request(
        self,
        events: List[models.AuditLog],
        collector_url: str,
        auth_token: Optional[str],
        format_type: str,
        batch_id: str
    ) -> Tuple[str, Dict[str, str], bytes]:
        target_url = collector_url or "https://http-intake.logs.datadoghq.com/api/v2/logs"
        headers = {
            "User-Agent": "AgentGuard-SIEM-Datadog/1.0",
            "Content-Type": "application/json",
            "X-AgentGuard-Batch-Id": batch_id,
        }
        if auth_token:
            headers["DD-API-KEY"] = auth_token

        dd_records = []
        for ev in events:
            json_entry = format_audit_log_json(ev)
            dd_item = {
                "ddsource": "agentguard",
                "service": "agentguard-security-kernel",
                "ddtags": f"org_id:{ev.org_id},result:{ev.result},event_type:{ev.event_type}",
                "message": f"AgentGuard Audit: {ev.action} by {ev.actor_id} -> {ev.result}",
                "agentguard_audit": json_entry
            }
            dd_records.append(dd_item)

        body_bytes = json.dumps(dd_records, separators=(",", ":")).encode("utf-8")
        return target_url, headers, body_bytes


ADAPTERS: Dict[str, BaseSiemAdapter] = {
    "GENERIC_HTTP": GenericHttpAdapter(),
    "SPLUNK_HEC": SplunkHecAdapter(),
    "DATADOG": DatadogAdapter(),
}


def get_adapter(provider_name: str) -> BaseSiemAdapter:
    normalized = provider_name.upper().strip() if provider_name else "GENERIC_HTTP"
    return ADAPTERS.get(normalized, ADAPTERS["GENERIC_HTTP"])
