from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
import datetime

from database import get_db
from core.deps import get_current_user, require_admin, HUMAN_ROLES
from core.permissions import can_manage_role
import models

router = APIRouter(prefix="/admin", tags=["Admin User Management"])

class RoleChangeRequest(BaseModel):
    role: str

class StatusChangeRequest(BaseModel):
    status: str

@router.get("/users")
def list_admin_users(
    search: Optional[str] = None,
    role_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(models.User)

    # SUPER_ADMIN is a platform identity and must NEVER appear inside any organization's user list
    query = query.filter(models.User.role != "SUPER_ADMIN")

    # Enforce Organization Isolation unless SUPER_ADMIN
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.User.org_id == current_user.org_id)

    if search:
        s = f"%{search}%"
        query = query.filter((models.User.full_name.ilike(s)) | (models.User.email.ilike(s)))

    if role_filter:
        query = query.filter(models.User.role == role_filter)

    if status_filter:
        query = query.filter(models.User.status == status_filter)

    users = query.all()

    # Enrich with organization name
    res = []
    for u in users:
        org = db.query(models.Organization).filter(models.Organization.id == u.org_id).first()
        res.append({
            "id": u.id,
            "auth_user_id": u.auth_user_id,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role,
            "department": u.department,
            "status": u.status,
            "org_id": u.org_id,
            "org_name": org.name if org else "AgentGuard Enterprise",
            "created_at": u.created_at
        })
    return res

@router.get("/users/{user_id}")
def get_admin_user_detail(
    user_id: str,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Enforce Organization Isolation
    if current_user.role != "SUPER_ADMIN" and target_user.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot view users outside your organization"
        )

    org = db.query(models.Organization).filter(models.Organization.id == target_user.org_id).first()
    return {
        "id": target_user.id,
        "auth_user_id": target_user.auth_user_id,
        "full_name": target_user.full_name,
        "email": target_user.email,
        "role": target_user.role,
        "department": target_user.department,
        "status": target_user.status,
        "org_id": target_user.org_id,
        "org_name": org.name if org else "AgentGuard Enterprise",
        "created_at": target_user.created_at
    }

@router.patch("/users/{user_id}/role")
def change_user_role(
    user_id: str,
    req: RoleChangeRequest,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    new_role = req.role.upper().strip()

    # 1. Prevent machine identity assignment to human users
    if new_role == "AGENT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AGENT is a machine identity for AI Employees and cannot be assigned to human users"
        )

    # 2. Validate human role list
    if new_role not in HUMAN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{new_role}'. Must be one of: {', '.join(HUMAN_ROLES)}"
        )

    # 3. Find target user
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")

    # 4. Self-role escalation protection (User cannot change their own role)
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Self-role modification is strictly prohibited"
        )

    # 5. Organization isolation enforcement
    if current_user.role != "SUPER_ADMIN" and target_user.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot modify users belonging to another organization"
        )

    # 6. Role Hierarchy & SUPER_ADMIN Protection:
    if not can_manage_role(current_user.role, target_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: You are not authorized to modify an account with role '{target_user.role}'"
        )

    if not can_manage_role(current_user.role, new_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: You are not authorized to assign role '{new_role}'"
        )

    if new_role == "SUPER_ADMIN" and current_user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only an existing SUPER_ADMIN can assign the SUPER_ADMIN role"
        )

    if target_user.role == "SUPER_ADMIN" and current_user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only an existing SUPER_ADMIN can modify a SUPER_ADMIN account"
        )

    old_role = target_user.role
    target_user.role = new_role
    db.commit()
    db.refresh(target_user)

    # 7. Real PostgreSQL Audit Logging
    audit_entry = models.AuditLog(
        org_id=target_user.org_id,
        event_type="ROLE_CHANGED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="CHANGE_ROLE",
        resource=f"user:{target_user.id}",
        result="SUCCESS",
        metadata_json={
            "actor_user_id": str(current_user.id),
            "target_user_id": str(target_user.id),
            "organization_id": str(target_user.org_id),
            "previous_role": old_role,
            "new_role": new_role,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    )
    db.add(audit_entry)
    db.commit()

    return {
        "status": "SUCCESS",
        "message": f"Successfully updated user role from {old_role} to {new_role}",
        "user_id": str(target_user.id),
        "old_role": old_role,
        "new_role": new_role
    }

@router.patch("/users/{user_id}/status")
def change_user_status(
    user_id: str,
    req: StatusChangeRequest,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot modify own account status"
        )

    if current_user.role != "SUPER_ADMIN" and target_user.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot modify user status outside your organization"
        )

    if target_user.role == "SUPER_ADMIN" and current_user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only SUPER_ADMIN can modify a SUPER_ADMIN account"
        )

    new_status = req.status.upper().strip()
    if new_status not in ["ACTIVE", "SUSPENDED", "DEACTIVATED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Allowed values: ACTIVE, SUSPENDED, DEACTIVATED"
        )

    old_status = target_user.status
    target_user.status = new_status
    if new_status in ["SUSPENDED", "DEACTIVATED"]:
        # Revoke all active sessions immediately
        db.query(models.Session).filter(models.Session.user_id == target_user.id).update({"revoked": True})

    audit_entry = models.AuditLog(
        org_id=target_user.org_id,
        event_type=f"USER_{new_status}",
        actor_type="USER",
        actor_id=str(current_user.id),
        action=f"SET_STATUS_{new_status}",
        resource=f"user:{target_user.id}",
        result="SUCCESS",
        metadata_json={
            "actor_user_id": str(current_user.id),
            "target_user_id": str(target_user.id),
            "organization_id": str(target_user.org_id),
            "previous_status": old_status,
            "new_status": new_status,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    )
    db.add(audit_entry)
    db.commit()

    return {"status": "SUCCESS", "user_id": str(target_user.id), "previous_status": old_status, "new_status": target_user.status}

@router.post("/users/{user_id}/suspend")
def suspend_user(
    user_id: str,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if target_user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Cannot suspend own account")

    if current_user.role != "SUPER_ADMIN" and target_user.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Cannot modify users outside your organization")

    if target_user.role == "SUPER_ADMIN" and current_user.role != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Only SUPER_ADMIN can suspend a SUPER_ADMIN account")

    old_status = target_user.status
    target_user.status = "SUSPENDED"
    db.query(models.Session).filter(models.Session.user_id == target_user.id).update({"revoked": True})

    audit_entry = models.AuditLog(
        org_id=target_user.org_id,
        event_type="USER_SUSPENDED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="SUSPEND_USER",
        resource=f"user:{target_user.id}",
        result="SUCCESS",
        metadata_json={
            "actor_user_id": str(current_user.id),
            "target_user_id": str(target_user.id),
            "organization_id": str(target_user.org_id),
            "previous_status": old_status,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    )
    db.add(audit_entry)
    db.commit()

    return {"status": "SUCCESS", "user_id": str(target_user.id), "status": "SUSPENDED"}

@router.post("/users/{user_id}/activate")
def activate_user(
    user_id: str,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if current_user.role != "SUPER_ADMIN" and target_user.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Cannot modify users outside your organization")

    old_status = target_user.status
    target_user.status = "ACTIVE"

    audit_entry = models.AuditLog(
        org_id=target_user.org_id,
        event_type="USER_ACTIVATED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="ACTIVATE_USER",
        resource=f"user:{target_user.id}",
        result="SUCCESS",
        metadata_json={
            "actor_user_id": str(current_user.id),
            "target_user_id": str(target_user.id),
            "organization_id": str(target_user.org_id),
            "previous_status": old_status,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    )
    db.add(audit_entry)
    db.commit()

    return {"status": "SUCCESS", "user_id": str(target_user.id), "status": "ACTIVE"}

@router.post("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: str,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if target_user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Cannot deactivate own account")

    if current_user.role != "SUPER_ADMIN" and target_user.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Cannot modify users outside your organization")

    if target_user.role == "SUPER_ADMIN" and current_user.role != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Only SUPER_ADMIN can deactivate a SUPER_ADMIN account")

    old_status = target_user.status
    target_user.status = "DEACTIVATED"
    db.query(models.Session).filter(models.Session.user_id == target_user.id).update({"revoked": True})

    audit_entry = models.AuditLog(
        org_id=target_user.org_id,
        event_type="USER_DEACTIVATED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="DEACTIVATE_USER",
        resource=f"user:{target_user.id}",
        result="SUCCESS",
        metadata_json={
            "actor_user_id": str(current_user.id),
            "target_user_id": str(target_user.id),
            "organization_id": str(target_user.org_id),
            "previous_status": old_status,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
    )
    db.add(audit_entry)
    db.commit()

    return {"status": "SUCCESS", "user_id": str(target_user.id), "status": "DEACTIVATED"}
