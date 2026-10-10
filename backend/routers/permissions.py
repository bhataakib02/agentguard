from typing import Optional, List
import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from database import get_db
from core.deps import get_current_user
import models
import schemas

router = APIRouter(prefix="/permissions", tags=["Permission Management"])

@router.get("", response_model=List[schemas.PermissionSchema])
def list_permissions(
    agent_id: Optional[str] = Query(None, description="Optional agent ID or code filter"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Permission).join(models.Agent)
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.Agent.org_id == current_user.org_id)

    if agent_id:
        query = query.filter((models.Agent.id == agent_id) | (models.Agent.agent_code == agent_id))

    return query.all()

@router.post("", response_model=schemas.PermissionSchema, status_code=status.HTTP_201_CREATED)
def create_permission(
    req: schemas.PermissionCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Grants a runtime resource permission to an AI agent.
    Enforces tenant isolation and audits permission grant.
    """
    if current_user.role not in ("SUPER_ADMIN", "ADMIN", "OPERATOR", "DEVELOPER", "SECURITY_ANALYST"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Insufficient privileges to grant agent permissions"
        )

    if not req.agent_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="agent_id is required")

    agent = db.query(models.Agent).filter(
        (models.Agent.id == req.agent_id) | (models.Agent.agent_code == req.agent_id)
    ).first()

    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot grant permissions to agent in another organization"
        )

    perm = models.Permission(
        agent_id=agent.id,
        resource_type=req.resource_type.upper(),
        resource_name=req.resource_name,
        action=req.action.upper(),
        is_allowed=req.is_allowed,
        created_at=datetime.datetime.utcnow()
    )
    db.add(perm)
    db.commit()
    db.refresh(perm)

    audit = models.AuditLog(
        org_id=agent.org_id,
        event_type="PERMISSION_GRANTED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="GRANT_PERMISSION",
        resource=f"agent:{agent.agent_code}:perm:{perm.id}",
        result="SUCCESS",
        metadata_json={
            "agent_id": str(agent.id),
            "agent_code": agent.agent_code,
            "resource_type": perm.resource_type,
            "resource_name": perm.resource_name,
            "action": perm.action,
            "is_allowed": perm.is_allowed,
            "permission_id": str(perm.id)
        }
    )
    db.add(audit)
    db.commit()

    return perm

@router.get("/matrix")
def get_permission_matrix(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Agent)
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.Agent.org_id == current_user.org_id)
    agents = query.all()

    matrix = []
    for agent in agents:
        perms = db.query(models.Permission).filter(models.Permission.agent_id == agent.id).all()
        perm_map = {p.resource_name: p.action for p in perms}
        matrix.append({
            "agent_id": agent.id,
            "agent_code": agent.agent_code,
            "name": agent.name,
            "department": agent.department,
            "permissions": perm_map
        })
    return matrix

@router.get("/templates")
def list_permission_templates(
    current_user: models.User = Depends(get_current_user)
):
    return [
        {"name": "Customer Support Agent", "default_permissions": ["Orders:READ", "Customers:READ", "Refunds:READ"]},
        {"name": "Finance Refund Agent", "default_permissions": ["Refunds:WRITE", "PaymentGateway:EXECUTE", "Transactions:CREATE"]},
        {"name": "Security Auditor Agent", "default_permissions": ["AuditLogs:READ", "Incidents:READ", "Behavior:READ"]}
    ]

@router.get("/{permission_id}", response_model=schemas.PermissionSchema)
def get_permission(
    permission_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    perm = db.query(models.Permission).filter(models.Permission.id == permission_id).first()
    if not perm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

    agent = db.query(models.Agent).filter(models.Agent.id == perm.agent_id).first()
    if agent and current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Cross-tenant access denied")

    return perm

@router.delete("/{permission_id}")
def revoke_permission(
    permission_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revokes / deletes an agent permission.
    Enforces tenant isolation and audits permission revocation.
    """
    if current_user.role not in ("SUPER_ADMIN", "ADMIN", "OPERATOR", "DEVELOPER", "SECURITY_ANALYST"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Insufficient privileges to revoke agent permissions"
        )

    perm = db.query(models.Permission).filter(models.Permission.id == permission_id).first()
    if not perm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

    agent = db.query(models.Agent).filter(models.Agent.id == perm.agent_id).first()
    if agent and current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Cross-tenant access denied")

    perm_id_str = str(perm.id)
    agent_code = agent.agent_code if agent else "UNKNOWN"
    org_id = agent.org_id if agent else current_user.org_id

    db.delete(perm)

    audit = models.AuditLog(
        org_id=org_id,
        event_type="PERMISSION_REVOKED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="REVOKE_PERMISSION",
        resource=f"agent:{agent_code}:perm:{perm_id_str}",
        result="SUCCESS",
        metadata_json={
            "agent_code": agent_code,
            "permission_id": perm_id_str,
            "revoked_by": current_user.email
        }
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "message": f"Permission {perm_id_str} revoked successfully."}

