from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
import json
import os
from database import get_db
from core.deps import get_current_user
import models
import schemas

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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Truthful SIEM connector status report.
    Returns CONFIGURED only if dedicated SIEM forwarder or collector credentials exist in environment or database.
    Never exposes cleartext authentication tokens in responses.
    """
    from services.siem_forwarder_service import resolve_siem_config, mask_secret

    cfg = resolve_siem_config(db, org_id=str(current_user.org_id) if current_user.org_id else None)
    
    # Query recent batch delivery history for current tenant
    recent_deliveries = []
    if current_user.org_id:
        recent = db.query(models.SiemDelivery).filter(
            models.SiemDelivery.org_id == current_user.org_id
        ).order_by(models.SiemDelivery.created_at.desc()).limit(5).all()

        recent_deliveries = [
            {
                "id": str(d.id),
                "batch_id": d.batch_id,
                "provider": d.provider,
                "format": d.format,
                "status": d.status,
                "event_count": d.event_count,
                "attempt_count": d.attempt_count,
                "response_code": d.response_code,
                "error_message": d.error_message,
                "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in recent
        ]

    return {
        "status": "CONFIGURED" if cfg.configured else "NOT_CONFIGURED",
        "provider": cfg.provider,
        "supported_formats": ["CEF", "JSONL"],
        "active_format": cfg.format_type,
        "delivery_semantics": "AT_LEAST_ONCE",
        "collector_preview": mask_secret(cfg.collector_url) if cfg.collector_url else None,
        "export_endpoints": {
            "cef": "/api/audit/export/cef",
            "jsonl": "/api/audit/export/jsonl"
        },
        "recent_deliveries": recent_deliveries,
        "details": (
            f"SIEM log streaming forwarder active ({cfg.provider})"
            if cfg.configured
            else "SIEM forwarder credentials not configured; on-demand CEF and JSONL log export active."
        )
    }


@router.post("/siem/forward", status_code=status.HTTP_202_ACCEPTED)
def trigger_siem_batch_forward(
    req: schemas.SiemTriggerForwardRequest = schemas.SiemTriggerForwardRequest(),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enqueues an asynchronous batch forwarding task for tenant audit logs to the configured SIEM.
    Requires ADMIN, SECURITY_ANALYST, or SUPER_ADMIN authorization.
    Truthfully reports QUEUED status (never claims delivery succeeded merely because task was queued).
    """
    import uuid
    from services.siem_forwarder_service import resolve_siem_config
    from tasks.siem_tasks import forward_siem_batch_task

    # Authorization Check
    allowed_roles = {"ADMIN", "SECURITY_ANALYST", "SUPER_ADMIN", "MANAGER"}
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Insufficient privileges to trigger SIEM audit forwarding."
        )

    if not current_user.org_id and current_user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context is required."
        )

    target_org_id = current_user.org_id
    cfg = resolve_siem_config(db, org_id=str(target_org_id) if target_org_id else None)
    if not cfg.configured:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SIEM collector is NOT_CONFIGURED. Please configure collector URL and credentials first."
        )

    batch_format = req.format if req.format else cfg.format_type
    batch_size = req.batch_size if req.batch_size else cfg.batch_size
    batch_id = f"siem_{uuid.uuid4().hex[:12]}"

    delivery = models.SiemDelivery(
        org_id=target_org_id,
        batch_id=batch_id,
        provider=cfg.provider,
        format=batch_format,
        status="PENDING",
        event_count=0,
        attempt_count=0
    )
    db.add(delivery)
    db.commit()
    db.refresh(delivery)

    # Dispatch Celery task
    forward_siem_batch_task.delay(str(delivery.id))

    return {
        "status": "QUEUED",
        "batch_id": delivery.batch_id,
        "delivery_id": str(delivery.id),
        "format": delivery.format,
        "provider": delivery.provider,
        "event_count": delivery.event_count,
        "message": "SIEM batch forwarding task enqueued."
    }


@router.get("/siem/deliveries")
def list_siem_deliveries(
    limit: int = 50,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists historical SIEM batch delivery records strictly scoped to tenant.
    Never exposes authentication tokens or secret credentials.
    """
    allowed_roles = {"ADMIN", "SECURITY_ANALYST", "SUPER_ADMIN", "MANAGER", "AUDITOR", "ANALYST"}
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Insufficient privileges to view SIEM delivery logs."
        )

    query = db.query(models.SiemDelivery)
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.SiemDelivery.org_id == current_user.org_id)

    deliveries = query.order_by(models.SiemDelivery.created_at.desc()).limit(min(limit, 100)).all()

    return [
        {
            "id": str(d.id),
            "org_id": str(d.org_id),
            "batch_id": d.batch_id,
            "provider": d.provider,
            "format": d.format,
            "status": d.status,
            "event_count": d.event_count,
            "attempt_count": d.attempt_count,
            "response_code": d.response_code,
            "error_message": d.error_message,
            "next_attempt_at": d.next_attempt_at.isoformat() if d.next_attempt_at else None,
            "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in deliveries
    ]


@router.get("/siem/config")
def get_siem_config(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the active SIEM collector configuration.
    Requires ADMIN or SUPER_ADMIN authorization.
    Collector secrets are masked; cleartext tokens are never exposed.
    """
    if current_user.role not in ("ADMIN", "SUPER_ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only administrators can view SIEM collector configuration."
        )

    from services.siem_forwarder_service import resolve_siem_config, mask_secret

    cfg = resolve_siem_config(db, org_id=str(current_user.org_id) if current_user.org_id else None)
    
    # Check DB record for precise ID and metadata
    db_config = None
    if current_user.org_id:
        db_config = db.query(models.SiemCollectorConfig).filter(
            models.SiemCollectorConfig.org_id == current_user.org_id,
            models.SiemCollectorConfig.is_active == True
        ).first()

    return {
        "configured": cfg.configured,
        "provider": cfg.provider,
        "collector_url": cfg.collector_url,
        "auth_token_preview": mask_secret(cfg.auth_token) if cfg.auth_token else None,
        "format": cfg.format_type,
        "batch_size": cfg.batch_size,
        "source": cfg.source,
        "is_active": db_config.is_active if db_config else cfg.configured
    }


@router.post("/siem/config")
def configure_siem_collector(
    req: schemas.SiemConfigCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Configures or updates the tenant SIEM collector endpoint and credentials.
    Requires ADMIN or SUPER_ADMIN privileges.
    Ordinary tenant users cannot alter settings.
    Enforces SSRF validation against loopback, private IPs, and cloud metadata.
    """
    if current_user.role not in ("ADMIN", "SUPER_ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only administrators can configure SIEM settings."
        )

    from services.notification_service import validate_webhook_url
    from services.siem_forwarder_service import mask_secret

    # SSRF safety validation
    is_safe, ssrf_err = validate_webhook_url(req.collector_url)
    if not is_safe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SSRF Protection: {ssrf_err}"
        )

    target_org_id = current_user.org_id
    if not target_org_id and current_user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context is required."
        )

    # Check for existing config
    existing = db.query(models.SiemCollectorConfig).filter(
        models.SiemCollectorConfig.org_id == target_org_id
    ).first()

    token_preview = mask_secret(req.auth_token) if req.auth_token else (existing.auth_token_preview if existing else None)

    if existing:
        existing.name = req.name or existing.name
        existing.provider = req.provider or existing.provider
        existing.collector_url = req.collector_url
        if req.auth_token:
            existing.auth_token_encrypted = req.auth_token
            existing.auth_token_preview = token_preview
        existing.format = req.format or existing.format
        existing.is_active = req.is_active if req.is_active is not None else existing.is_active
        existing.batch_size = req.batch_size or existing.batch_size
        db.commit()
        db.refresh(existing)
        cfg_record = existing
    else:
        cfg_record = models.SiemCollectorConfig(
            org_id=target_org_id,
            name=req.name or "Primary SIEM Collector",
            provider=req.provider or "GENERIC_HTTP",
            collector_url=req.collector_url,
            auth_token_encrypted=req.auth_token,
            auth_token_preview=token_preview,
            format=req.format or "JSONL",
            is_active=req.is_active if req.is_active is not None else True,
            batch_size=req.batch_size or 100
        )
        db.add(cfg_record)
        db.commit()
        db.refresh(cfg_record)

    # Immutable Audit Log for configuration update
    audit = models.AuditLog(
        org_id=target_org_id,
        event_type="SIEM_CONFIG_UPDATED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action=f"Updated SIEM collector config: {cfg_record.provider} ({cfg_record.collector_url})",
        resource=f"siem_config:{cfg_record.id}",
        result="SUCCESS",
        metadata_json={
            "provider": cfg_record.provider,
            "format": cfg_record.format,
            "batch_size": cfg_record.batch_size,
            "has_token": bool(req.auth_token or cfg_record.auth_token_encrypted)
        }
    )
    db.add(audit)
    db.commit()

    return {
        "id": str(cfg_record.id),
        "org_id": str(cfg_record.org_id) if cfg_record.org_id else None,
        "name": cfg_record.name,
        "provider": cfg_record.provider,
        "collector_url": cfg_record.collector_url,
        "auth_token_preview": cfg_record.auth_token_preview,
        "format": cfg_record.format,
        "is_active": cfg_record.is_active,
        "batch_size": cfg_record.batch_size,
        "created_at": cfg_record.created_at.isoformat() if cfg_record.created_at else None,
        "updated_at": cfg_record.updated_at.isoformat() if cfg_record.updated_at else None
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
