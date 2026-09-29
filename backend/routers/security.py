import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from core.deps import (
    get_current_user,
    require_permission,
    PERM_SECURITY_VIEW,
    PERM_SECURITY_INCIDENT_CREATE,
    PERM_SECURITY_INCIDENT_UPDATE,
    PERM_SECURITY_INCIDENT_RESOLVE,
)
import models

router = APIRouter(prefix="/security", tags=["Security Operations Center"])


class IncidentCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    severity: str = "HIGH"  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    agent_id: Optional[str] = None
    affected_user_id: Optional[str] = None
    source: Optional[str] = "MANUAL"


class IncidentUpdateRequest(BaseModel):
    status: Optional[str] = None  # OPEN, INVESTIGATING, CONTAINED, RESOLVED, CLOSED
    severity: Optional[str] = None
    assigned_to_user_id: Optional[str] = None
    resolution_notes: Optional[str] = None


@router.get("/incidents")
def list_incidents(
    status_filter: Optional[str] = Query(None, alias="status"),
    severity_filter: Optional[str] = Query(None, alias="severity"),
    agent_id: Optional[str] = None,
    current_user: models.User = Depends(require_permission(PERM_SECURITY_VIEW)),
    db: Session = Depends(get_db)
):
    """Lists security incidents with strict organization isolation."""
    query = db.query(models.SecurityIncident)
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.SecurityIncident.org_id == current_user.org_id)

    if status_filter:
        query = query.filter(models.SecurityIncident.status == status_filter.upper())
    if severity_filter:
        query = query.filter(models.SecurityIncident.severity == severity_filter.upper())
    if agent_id:
        query = query.filter(models.SecurityIncident.agent_id == agent_id)

    incidents = query.order_by(models.SecurityIncident.created_at.desc()).all()
    res = []
    for inc in incidents:
        agent = db.query(models.Agent).filter(models.Agent.id == inc.agent_id).first() if inc.agent_id else None
        res.append({
            "id": str(inc.id),
            "org_id": str(inc.org_id),
            "agent_id": str(inc.agent_id) if inc.agent_id else None,
            "agent_code": agent.agent_code if agent else None,
            "agent_name": agent.name if agent else None,
            "title": inc.title,
            "description": inc.description,
            "severity": inc.severity,
            "status": inc.status,
            "source": inc.source,
            "affected_user_id": str(inc.affected_user_id) if inc.affected_user_id else None,
            "assigned_to_user_id": str(inc.assigned_to_user_id) if inc.assigned_to_user_id else None,
            "resolution_notes": inc.resolution_notes,
            "timeline": inc.timeline_json or [],
            "created_at": inc.created_at.isoformat() if inc.created_at else None,
            "updated_at": inc.updated_at.isoformat() if inc.updated_at else None,
            "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None,
        })
    return res


@router.post("/incidents")
def create_incident(
    req: IncidentCreateRequest,
    current_user: models.User = Depends(require_permission(PERM_SECURITY_INCIDENT_CREATE)),
    db: Session = Depends(get_db)
):
    """Creates a new security incident within the authenticated user's organization."""
    # Validate agent if provided
    agent = None
    if req.agent_id:
        agent = db.query(models.Agent).filter(models.Agent.id == req.agent_id).first()
        if not agent:
            raise HTTPException(status_code=404, detail="Referenced agent not found")
        if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
            raise HTTPException(status_code=403, detail="Forbidden: Cannot link incident to an agent in another organization")

    # Validate affected user if provided
    if req.affected_user_id:
        aff_user = db.query(models.User).filter(models.User.id == req.affected_user_id).first()
        if not aff_user:
            raise HTTPException(status_code=404, detail="Referenced user not found")
        if current_user.role != "SUPER_ADMIN" and aff_user.org_id != current_user.org_id:
            raise HTTPException(status_code=403, detail="Forbidden: Cannot link incident to a user in another organization")

    valid_severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
    sev = req.severity.upper().strip() if req.severity else "HIGH"
    if sev not in valid_severities:
        sev = "HIGH"

    timeline_entry = {
        "action": "INCIDENT_CREATED",
        "actor": current_user.email,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "notes": "Incident logged via Security Operations Center"
    }

    inc = models.SecurityIncident(
        org_id=current_user.org_id,
        agent_id=agent.id if agent else None,
        affected_user_id=req.affected_user_id,
        title=req.title.strip(),
        description=req.description,
        severity=sev,
        status="OPEN",
        source=req.source or "MANUAL",
        timeline_json=[timeline_entry]
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)

    audit = models.AuditLog(
        org_id=current_user.org_id,
        event_type="SECURITY_INCIDENT_CREATED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="CREATE_INCIDENT",
        resource=f"incident:{inc.id}",
        result="SUCCESS",
        metadata_json={
            "incident_id": str(inc.id),
            "title": inc.title,
            "severity": inc.severity,
            "agent_id": str(agent.id) if agent else None
        }
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "id": str(inc.id),
        "title": inc.title,
        "severity": inc.severity,
        "incident_status": inc.status,
        "created_at": inc.created_at.isoformat()
    }


@router.get("/incidents/{incident_id}")
def get_incident(
    incident_id: str,
    current_user: models.User = Depends(require_permission(PERM_SECURITY_VIEW)),
    db: Session = Depends(get_db)
):
    """Retrieves security incident details. Cross-tenant access is rejected."""
    inc = db.query(models.SecurityIncident).filter(models.SecurityIncident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Security incident not found")

    if current_user.role != "SUPER_ADMIN" and inc.org_id != current_user.org_id:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot access incident of another organization")

    agent = db.query(models.Agent).filter(models.Agent.id == inc.agent_id).first() if inc.agent_id else None
    return {
        "id": str(inc.id),
        "org_id": str(inc.org_id),
        "agent_id": str(inc.agent_id) if inc.agent_id else None,
        "agent_code": agent.agent_code if agent else None,
        "agent_name": agent.name if agent else None,
        "title": inc.title,
        "description": inc.description,
        "severity": inc.severity,
        "status": inc.status,
        "source": inc.source,
        "assigned_to_user_id": str(inc.assigned_to_user_id) if inc.assigned_to_user_id else None,
        "resolution_notes": inc.resolution_notes,
        "timeline": inc.timeline_json or [],
        "created_at": inc.created_at.isoformat() if inc.created_at else None,
        "updated_at": inc.updated_at.isoformat() if inc.updated_at else None,
        "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None,
    }


@router.patch("/incidents/{incident_id}")
def update_incident(
    incident_id: str,
    req: IncidentUpdateRequest,
    current_user: models.User = Depends(require_permission(PERM_SECURITY_INCIDENT_UPDATE)),
    db: Session = Depends(get_db)
):
    """Updates incident status, severity, assignment, or adds resolution notes."""
    inc = db.query(models.SecurityIncident).filter(models.SecurityIncident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Security incident not found")

    if current_user.role != "SUPER_ADMIN" and inc.org_id != current_user.org_id:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot modify incident of another organization")

    timeline = list(inc.timeline_json or [])
    now_dt = datetime.datetime.utcnow()

    if req.status:
        valid_statuses = ["OPEN", "INVESTIGATING", "CONTAINED", "RESOLVED", "CLOSED"]
        new_status = req.status.upper().strip()
        if new_status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

        old_status = inc.status
        inc.status = new_status
        timeline.append({
            "action": f"STATUS_CHANGED_TO_{new_status}",
            "actor": current_user.email,
            "timestamp": now_dt.isoformat(),
            "previous_status": old_status,
            "new_status": new_status
        })

        if new_status in ["RESOLVED", "CLOSED"]:
            inc.resolved_at = now_dt

    if req.severity:
        inc.severity = req.severity.upper().strip()

    if req.assigned_to_user_id:
        assignee = db.query(models.User).filter(models.User.id == req.assigned_to_user_id).first()
        if not assignee:
            raise HTTPException(status_code=404, detail="Assignee user not found")
        if current_user.role != "SUPER_ADMIN" and assignee.org_id != current_user.org_id:
            raise HTTPException(status_code=403, detail="Cannot assign incident to a user in another organization")
        inc.assigned_to_user_id = assignee.id

    if req.resolution_notes:
        inc.resolution_notes = req.resolution_notes.strip()
        timeline.append({
            "action": "RESOLUTION_NOTES_ADDED",
            "actor": current_user.email,
            "timestamp": now_dt.isoformat(),
            "notes": req.resolution_notes.strip()
        })

    inc.timeline_json = timeline
    inc.updated_at = now_dt
    db.commit()

    audit = models.AuditLog(
        org_id=inc.org_id,
        event_type="SECURITY_INCIDENT_UPDATED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="UPDATE_INCIDENT",
        resource=f"incident:{inc.id}",
        result="SUCCESS",
        metadata_json={
            "incident_id": str(inc.id),
            "status": inc.status,
            "severity": inc.severity
        }
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "id": str(inc.id),
        "incident_status": inc.status,
        "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None
    }


@router.get("/overview")
def get_security_overview(
    current_user: models.User = Depends(require_permission(PERM_SECURITY_VIEW)),
    db: Session = Depends(get_db)
):
    inc_query = db.query(models.SecurityIncident)
    agent_query = db.query(models.Agent)
    if current_user.role != "SUPER_ADMIN":
        inc_query = inc_query.filter(models.SecurityIncident.org_id == current_user.org_id)
        agent_query = agent_query.filter(models.Agent.org_id == current_user.org_id)

    total_incidents = inc_query.count()
    open_incidents = inc_query.filter(models.SecurityIncident.status == "OPEN").count()
    critical_agents = agent_query.filter(models.Agent.risk_score > 60).count()
    suspended_agents = agent_query.filter(models.Agent.status == "SUSPENDED").count()

    return {
        "total_incidents": total_incidents,
        "open_incidents": open_incidents,
        "critical_agents": critical_agents,
        "suspended_agents": suspended_agents,
        "security_status": "MONITORED"
    }
