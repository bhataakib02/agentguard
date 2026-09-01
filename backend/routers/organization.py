from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import datetime

from database import get_db
from core.deps import get_current_user, require_admin, check_org_isolation, check_license_limit, get_effective_org_id, HUMAN_ROLES
from core import security
import models

router = APIRouter(prefix="/organization", tags=["Organization Tenant Administration"])

class OrgSettingsUpdateRequest(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    timezone: Optional[str] = None
    security_level: Optional[str] = None

class BrandingUpdateRequest(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    logo_url: Optional[str] = None

class InviteUserRequest(BaseModel):
    email: str
    full_name: str
    role: str  # USER, VIEWER, ANALYST, OPERATOR, SECURITY_ANALYST, MANAGER, DEVELOPER, ADMIN
    department: Optional[str] = "General"
    job_title: Optional[str] = None
    password: Optional[str] = "Blackbird@12."

def get_org_initials(name: str) -> str:
    parts = name.strip().split(" ")
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[1][0]}".upper()
    return name[:2].upper()

@router.get("/dashboard")
def get_organization_dashboard(
    current_user: models.User = Depends(get_current_user),
    x_org_context: Optional[str] = Header(None, alias="X-Organization-Context"),
    db: Session = Depends(get_db)
):
    target_org_id = get_effective_org_id(current_user, x_org_context)
    org = db.query(models.Organization).filter(models.Organization.id == target_org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    lic = db.query(models.License).filter(models.License.org_id == target_org_id).first()
    lic_usage = db.query(models.LicenseUsage).filter(models.LicenseUsage.org_id == target_org_id).first()

    user_count = db.query(models.User).filter(
        models.User.org_id == target_org_id,
        models.User.role != "SUPER_ADMIN"
    ).count()
    agent_count = db.query(models.Agent).filter(models.Agent.org_id == target_org_id).count()

    plan_id = lic.plan_id if lic else "FREE"
    lic_status = lic.status if lic else "ACTIVE"
    max_users = lic.max_users if lic else 5
    max_agents = lic.max_ai_agents if lic else 3
    max_api_requests = lic.max_monthly_api_requests if lic else 50000

    api_count = lic_usage.api_requests_count if lic_usage else 0
    api_pct = round((api_count / max_api_requests) * 100, 1) if max_api_requests > 0 else 0.0

    alerts_count = db.query(models.SecurityIncident).filter(
        models.SecurityIncident.org_id == current_user.org_id if hasattr(models.SecurityIncident, 'org_id') else True
    ).count()

    pending_approvals = db.query(models.ApprovalRequest).count()

    return {
        "org_id": str(org.id),
        "org_name": org.name,
        "display_name": org.display_name or org.name,
        "logo_url": org.logo_url,
        "initials": get_org_initials(org.name),
        "domain": org.domain or "",
        "status": org.status or "ACTIVE",
        "plan_id": plan_id,
        "license_status": lic_status,
        "expiry_date": lic.expiry_date.isoformat() if (lic and lic.expiry_date) else None,
        "metrics": {
            "users": {"current": user_count, "max": max_users},
            "ai_agents": {"current": agent_count, "max": max_agents},
            "api_requests": {"current": api_count, "max": max_api_requests, "percentage": api_pct},
            "security_alerts": alerts_count,
            "pending_approvals": pending_approvals
        }
    }

@router.get("/branding")
def get_organization_branding(
    current_user: models.User = Depends(get_current_user),
    x_org_context: Optional[str] = Header(None, alias="X-Organization-Context"),
    db: Session = Depends(get_db)
):
    target_org_id = get_effective_org_id(current_user, x_org_context)
    org = db.query(models.Organization).filter(models.Organization.id == target_org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return {
        "org_id": str(org.id),
        "name": org.name,
        "display_name": org.display_name or org.name,
        "logo_url": org.logo_url,
        "initials": get_org_initials(org.name)
    }

@router.patch("/branding")
def update_organization_branding(
    payload: BrandingUpdateRequest,
    current_user: models.User = Depends(require_admin),
    x_org_context: Optional[str] = Header(None, alias="X-Organization-Context"),
    db: Session = Depends(get_db)
):
    target_org_id = get_effective_org_id(current_user, x_org_context)
    check_org_isolation(current_user, target_org_id)

    org = db.query(models.Organization).filter(models.Organization.id == target_org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if payload.name:
        org.name = payload.name.strip()
    if payload.display_name:
        org.display_name = payload.display_name.strip()
    if payload.logo_url is not None:
        org.logo_url = payload.logo_url.strip() if payload.logo_url else None

    db.commit()
    db.refresh(org)

    audit = models.AuditLog(
        event_type="ORGANIZATION_BRANDING_UPDATED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action=f"Updated organization {org.name} branding & custom identity",
        resource="organizations",
        result="SUCCESS",
        metadata_json={"org_id": str(org.id), "logo_url": org.logo_url}
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "org_id": str(org.id),
        "name": org.name,
        "display_name": org.display_name,
        "logo_url": org.logo_url,
        "initials": get_org_initials(org.name)
    }

@router.delete("/branding/logo")
def remove_organization_logo(
    current_user: models.User = Depends(require_admin),
    x_org_context: Optional[str] = Header(None, alias="X-Organization-Context"),
    db: Session = Depends(get_db)
):
    target_org_id = get_effective_org_id(current_user, x_org_context)
    check_org_isolation(current_user, target_org_id)

    org = db.query(models.Organization).filter(models.Organization.id == target_org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.logo_url = None
    org.logo_path = None
    db.commit()

    audit = models.AuditLog(
        event_type="ORGANIZATION_LOGO_REMOVED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action=f"Removed organization logo for {org.name}",
        resource="organizations",
        result="SUCCESS",
        metadata_json={"org_id": str(org.id)}
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "org_id": str(org.id),
        "logo_url": None,
        "initials": get_org_initials(org.name)
    }

@router.get("/settings")
def get_organization_settings(
    current_user: models.User = Depends(get_current_user),
    x_org_context: Optional[str] = Header(None, alias="X-Organization-Context"),
    db: Session = Depends(get_db)
):
    target_org_id = get_effective_org_id(current_user, x_org_context)
    org = db.query(models.Organization).filter(models.Organization.id == target_org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    lic = db.query(models.License).filter(models.License.org_id == target_org_id).first()

    return {
        "org_id": str(org.id),
        "name": org.name,
        "display_name": org.display_name or org.name,
        "logo_url": org.logo_url,
        "initials": get_org_initials(org.name),
        "domain": org.domain or "",
        "status": org.status or "ACTIVE",
        "admin_email": org.admin_email or "",
        "created_at": org.created_at.isoformat() if org.created_at else None,
        "license": {
            "plan_id": lic.plan_id if lic else "FREE",
            "status": lic.status if lic else "ACTIVE",
            "max_users": lic.max_users if lic else 5,
            "max_ai_agents": lic.max_ai_agents if lic else 3,
            "max_monthly_api_requests": lic.max_monthly_api_requests if lic else 50000,
            "expiry_date": lic.expiry_date.isoformat() if (lic and lic.expiry_date) else None
        }
    }

@router.patch("/settings")
def update_organization_settings(
    payload: OrgSettingsUpdateRequest,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    org = db.query(models.Organization).filter(models.Organization.id == current_user.org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if payload.name:
        org.name = payload.name.strip()
    if payload.domain:
        org.domain = payload.domain.strip()

    db.commit()
    db.refresh(org)

    audit = models.AuditLog(
        event_type="ORGANIZATION_UPDATED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action=f"Updated organization {org.name} settings",
        resource="organizations",
        result="SUCCESS",
        metadata_json={"org_id": str(org.id)}
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "org_id": str(org.id), "name": org.name, "domain": org.domain}

@router.post("/invite-user")
def invite_user_to_organization(
    payload: InviteUserRequest,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    # 1. Enforce License User Limit
    check_license_limit(str(current_user.org_id), "users", db)

    # 2. Reject privilege escalation / invalid human role assignment
    target_role = payload.role.upper()
    if target_role == "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Organization ADMIN cannot assign SUPER_ADMIN role to any user"
        )

    if target_role not in HUMAN_ROLES or target_role == "AGENT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid human organization role. Allowed human roles: {', '.join(HUMAN_ROLES[:-1])}"
        )

    # 3. Duplicate Email Check
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        if str(existing.org_id) == str(current_user.org_id):
            return {
                "status": "SUCCESS",
                "message": f"User {payload.email} is already a member of this organization (idempotent).",
                "user_id": str(existing.id),
                "email": existing.email,
                "role": existing.role,
                "org_id": str(existing.org_id)
            }
        else:
            raise HTTPException(status_code=400, detail="User with this email already belongs to another organization")

    # 4. Create User
    new_user = models.User(
        org_id=current_user.org_id,
        email=payload.email,
        full_name=payload.full_name,
        role=target_role,
        department=payload.department or "General",
        job_title=payload.job_title,
        password_hash=security.get_password_hash(payload.password or "Blackbird@12."),
        status="ACTIVE"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Record Audit Log
    audit = models.AuditLog(
        event_type="USER_INVITED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action=f"Invited user {payload.email} with role {target_role}",
        resource="users",
        result="SUCCESS",
        metadata_json={"invited_user_id": str(new_user.id), "org_id": str(current_user.org_id), "role": target_role}
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "user_id": str(new_user.id),
        "email": new_user.email,
        "role": new_user.role,
        "org_id": str(new_user.org_id)
    }
