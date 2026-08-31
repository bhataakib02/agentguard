from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
import datetime

from database import get_db
from core.deps import get_current_user, require_admin, HUMAN_ROLES
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

    # 6. SUPER_ADMIN Protection:
    # Only an existing SUPER_ADMIN can assign SUPER_ADMIN role or modify a SUPER_ADMIN user
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
        event_type="ROLE_CHANGED",
        actor_type="USER",
        actor_id=current_user.id,
        action="CHANGE_ROLE",
        resource=f"user:{target_user.id}",
        result="SUCCESS",
        metadata_json={
            "actor_user_id": current_user.id,
            "target_user_id": target_user.id,
            "organization_id": target_user.org_id,
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
        "user_id": target_user.id,
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

    target_user.status = req.status
    db.commit()
    return {"status": "SUCCESS", "user_id": target_user.id, "new_status": target_user.status}
