from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
import json
import os
from database import get_db
from core.deps import get_current_user
import models

router = APIRouter(prefix="/audit", tags=["Global Audit Center"])

def _get_scoped_audit_query(current_user: models.User, db: Session):
    query = db.query(models.AuditLog)
    if current_user.role != "SUPER_ADMIN":
        org_id_str = str(current_user.org_id)
        org_users = db.query(models.User.id, models.User.email).filter(models.User.org_id == current_user.org_id).all()
        org_user_ids = [str(u[0]) for u in org_users]
        org_user_emails = [str(u[1]) for u in org_users]
        org_agents = db.query(models.Agent.id, models.Agent.agent_code).filter(models.Agent.org_id == current_user.org_id).all()
        org_agent_ids = [str(a[0]) for a in org_agents]
        org_agent_codes = [str(a[1]) for a in org_agents]
        all_actors = set(org_user_ids + org_user_emails + org_agent_ids + org_agent_codes)

        filters = [
            models.AuditLog.org_id == current_user.org_id,
            models.AuditLog.resource.contains(org_id_str)
        ]
        if all_actors:
            filters.append(models.AuditLog.actor_id.in_(all_actors))
        query = query.filter(or_(*filters))
    return query

@router.get("/logs")
def list_audit_logs(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = _get_scoped_audit_query(current_user, db)
    return query.order_by(models.AuditLog.timestamp.desc()).all()

@router.get("/export/cef", response_class=PlainTextResponse)
def export_audit_logs_cef(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Exports tenant-scoped immutable audit logs formatted in Common Event Format (CEF)
    for enterprise SIEM ingestion (Splunk, ArcSight, IBM QRadar, Datadog, Microsoft Sentinel).
    """
    logs = _get_scoped_audit_query(current_user, db).order_by(models.AuditLog.timestamp.desc()).limit(1000).all()
    cef_lines = []
    for log in logs:
        # Severity mapping: BLOCKED/FAILED -> 8, DENIED -> 6, SUCCESS -> 3
        severity = 8 if log.result in ("BLOCKED", "FAILED") else (6 if log.result == "DENIED" else 3)
        ts_str = log.timestamp.isoformat() if hasattr(log.timestamp, "isoformat") else str(log.timestamp)
        cef_line = (
            f"CEF:0|AgentGuard|SecurityKernel|1.0|{log.action}|{log.event_type}|{severity}|"
            f"src={log.actor_id} suser={log.actor_type} act={log.action} outcome={log.result} "
            f"cs1={log.org_id} cs1Label=OrgId cs2={log.resource} cs2Label=Resource deviceCustomDate1={ts_str}"
        )
        cef_lines.append(cef_line)
    return "\n".join(cef_lines)

@router.get("/export/jsonl", response_class=PlainTextResponse)
def export_audit_logs_jsonl(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Exports tenant-scoped immutable audit logs formatted in JSON-Lines (NDJSON)
    for log shipping agents (Fluentd, Vector, Logstash, Datadog Agent).
    """
    logs = _get_scoped_audit_query(current_user, db).order_by(models.AuditLog.timestamp.desc()).limit(1000).all()
    jsonl_lines = []
    for log in logs:
        ts_str = log.timestamp.isoformat() if hasattr(log.timestamp, "isoformat") else str(log.timestamp)
        entry = {
            "id": str(log.id),
            "org_id": str(log.org_id) if log.org_id else None,
            "timestamp": ts_str,
            "event_type": log.event_type,
            "actor_type": log.actor_type,
            "actor_id": log.actor_id,
            "action": log.action,
            "resource": log.resource,
            "result": log.result,
            "metadata": log.metadata_json or {}
        }
        jsonl_lines.append(json.dumps(entry, separators=(",", ":")))
    return "\n".join(jsonl_lines)

@router.get("/siem/status")
def get_siem_forwarder_status(
    current_user: models.User = Depends(get_current_user)
):
    """
    Truthful SIEM connector status report.
    Returns CONFIGURED only if dedicated SIEM forwarder or collector credentials exist in environment.
    """
    siem_url = os.getenv("SIEM_FORWARDER_URL") or os.getenv("SPLUNK_HEC_URL")
    datadog_key = os.getenv("DATADOG_API_KEY")
    is_configured = bool(siem_url or datadog_key)

    return {
        "status": "CONFIGURED" if is_configured else "NOT_CONFIGURED",
        "provider": "SPLUNK_HEC" if os.getenv("SPLUNK_HEC_URL") else ("DATADOG" if datadog_key else ("GENERIC_CEF" if siem_url else "NONE")),
        "supported_formats": ["CEF", "JSONL"],
        "export_endpoints": {
            "cef": "/api/audit/export/cef",
            "jsonl": "/api/audit/export/jsonl"
        },
        "details": "SIEM log streaming forwarder active" if is_configured else "SIEM forwarder credentials not configured; on-demand CEF and JSONL log export active."
    }

@router.delete("/logs/{id}")
@router.delete("/logs")
@router.put("/logs/{id}")
@router.patch("/logs/{id}")
def reject_audit_log_modification():
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Forbidden: Audit logs are immutable and append-only. Modification or deletion is strictly prohibited."
    )
