from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import get_db
from core.deps import get_current_user
import models

router = APIRouter(prefix="/audit", tags=["Global Audit Center"])

@router.get("/logs")
def list_audit_logs(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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

    return query.order_by(models.AuditLog.timestamp.desc()).all()

@router.delete("/logs/{id}")
@router.delete("/logs")
@router.put("/logs/{id}")
@router.patch("/logs/{id}")
def reject_audit_log_modification():
    from fastapi import HTTPException, status
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Forbidden: Audit logs are immutable and append-only. Modification or deletion is strictly prohibited."
    )
