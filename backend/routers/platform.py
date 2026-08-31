from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import datetime

from database import get_db
from core.deps import get_current_user, require_super_admin, HUMAN_ROLES
from core import security
import models

router = APIRouter(prefix="/platform", tags=["Platform Administration & Multi-Tenancy"])

class CreateOrgRequest(BaseModel):
    name: str
    domain: Optional[str] = None
    plan_id: Optional[str] = "STARTER"
    admin_email: str
    admin_full_name: str
    admin_password: Optional[str] = "Blackbird@12."

class UpdateOrgStatusRequest(BaseModel):
    status: str  # ACTIVE, SUSPENDED, RESTRICTED, DEACTIVATED

class UpdateOrgLicenseRequest(BaseModel):
    plan_id: str
    max_users: Optional[int] = None
    max_ai_agents: Optional[int] = None
    status: Optional[str] = None

class ExtendLicenseRequest(BaseModel):
    org_id: str
    days: Optional[int] = 30
    custom_expiry_date: Optional[str] = None

class RevokeLicenseRequest(BaseModel):
    org_id: str
    reason: Optional[str] = "Administrative revocation"

class CreatePlanRequest(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    price_monthly: float = 0.0
    max_users: int = 10
    max_ai_agents: int = 5
    max_api_keys: int = 5
    max_monthly_api_requests: int = 100000
    max_storage_gb: float = 20.0

@router.get("/overview")
def get_platform_overview(
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    total_orgs = db.query(models.Organization).count()
    active_orgs = db.query(models.Organization).filter(models.Organization.status == "ACTIVE").count()
    suspended_orgs = db.query(models.Organization).filter(models.Organization.status == "SUSPENDED").count()
    total_users = db.query(models.User).filter(models.User.role != "SUPER_ADMIN").count()
    total_agents = db.query(models.Agent).count()
    active_licenses = db.query(models.License).filter(models.License.status == "ACTIVE").count()
    expiring_licenses = db.query(models.License).filter(
        models.License.expiry_date != None,
        models.License.expiry_date <= datetime.datetime.utcnow() + datetime.timedelta(days=30)
    ).count()

    total_api_requests = db.query(models.AuditLog).count()

    return {
        "platform": "AgentGuard Multi-Tenant SaaS Engine",
        "total_organizations": total_orgs,
        "active_organizations": active_orgs,
        "suspended_organizations": suspended_orgs,
        "total_users": total_users,
        "total_ai_agents": total_agents,
        "active_licenses": active_licenses,
        "expiring_licenses": expiring_licenses,
        "total_api_requests": total_api_requests,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

@router.get("/plans")
def list_plans(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    plans = db.query(models.Plan).all()
    res = []
    for p in plans:
        res.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "price_monthly": p.price_monthly,
            "max_users": p.max_users,
            "max_ai_agents": p.max_ai_agents,
            "max_api_keys": p.max_api_keys,
            "max_monthly_api_requests": p.max_monthly_api_requests,
            "max_storage_gb": p.max_storage_gb,
            "feature_flags": p.feature_flags or {}
        })
    return res

@router.post("/plans")
def create_or_update_plan(
    payload: CreatePlanRequest,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    existing = db.query(models.Plan).filter(models.Plan.id == payload.id.upper()).first()
    if not existing:
        existing = models.Plan(
            id=payload.id.upper(),
            name=payload.name,
            description=payload.description,
            price_monthly=payload.price_monthly,
            max_users=payload.max_users,
            max_ai_agents=payload.max_ai_agents,
            max_api_keys=payload.max_api_keys,
            max_monthly_api_requests=payload.max_monthly_api_requests,
            max_storage_gb=payload.max_storage_gb
        )
        db.add(existing)
    else:
        existing.name = payload.name
        existing.description = payload.description
        existing.price_monthly = payload.price_monthly
        existing.max_users = payload.max_users
        existing.max_ai_agents = payload.max_ai_agents
        existing.max_api_keys = payload.max_api_keys
        existing.max_monthly_api_requests = payload.max_monthly_api_requests
        existing.max_storage_gb = payload.max_storage_gb

    db.commit()
    db.refresh(existing)
    return {"status": "SUCCESS", "plan_id": existing.id}

@router.get("/organizations")
def list_organizations(
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    orgs = db.query(models.Organization).order_by(models.Organization.created_at.desc()).all()
    res = []
    for o in orgs:
        lic = db.query(models.License).filter(models.License.org_id == o.id).first()
        plan_id = lic.plan_id if lic else "FREE"
        lic_status = lic.status if lic else "ACTIVE"
        max_u = lic.max_users if lic else 5
        max_a = lic.max_ai_agents if lic else 3

        # SUPER_ADMIN is NEVER counted in an organization's user quota or user list
        user_count = db.query(models.User).filter(
            models.User.org_id == o.id,
            models.User.role != "SUPER_ADMIN"
        ).count()
        agent_count = db.query(models.Agent).filter(models.Agent.org_id == o.id).count()

        res.append({
            "id": str(o.id),
            "name": o.name,
            "domain": o.domain or "",
            "status": o.status or "ACTIVE",
            "admin_email": o.admin_email or "unassigned",
            "plan_id": plan_id,
            "license_status": lic_status,
            "user_count": user_count,
            "max_users": max_u,
            "agent_count": agent_count,
            "max_ai_agents": max_a,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "expiry_date": lic.expiry_date.isoformat() if (lic and lic.expiry_date) else None
        })
    return res

@router.get("/licenses")
def list_platform_licenses(
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    licenses = db.query(models.License).all()
    res = []
    now = datetime.datetime.utcnow()

    for l in licenses:
        org = db.query(models.Organization).filter(models.Organization.id == l.org_id).first()
        user_count = db.query(models.User).filter(
            models.User.org_id == l.org_id,
            models.User.role != "SUPER_ADMIN"
        ).count()
        agent_count = db.query(models.Agent).filter(models.Agent.org_id == l.org_id).count()

        days_remaining = None
        expiring_soon = False
        is_expired = False

        if l.expiry_date:
            diff = (l.expiry_date - now).days
            days_remaining = diff
            if diff <= 30 and diff > 0:
                expiring_soon = True
            elif diff <= 0:
                is_expired = True

        res.append({
            "id": str(l.id),
            "org_id": str(l.org_id),
            "org_name": org.name if org else "Unknown",
            "plan_id": l.plan_id,
            "status": "EXPIRED" if is_expired else l.status,
            "start_date": l.start_date.isoformat() if l.start_date else None,
            "expiry_date": l.expiry_date.isoformat() if l.expiry_date else None,
            "user_count": user_count,
            "max_users": l.max_users,
            "agent_count": agent_count,
            "max_ai_agents": l.max_ai_agents,
            "days_remaining": days_remaining,
            "expiring_soon": expiring_soon,
            "is_expired": is_expired
        })
    return res

@router.post("/licenses/extend")
def extend_organization_license(
    payload: ExtendLicenseRequest,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    lic = db.query(models.License).filter(models.License.org_id == payload.org_id).first()
    if not lic:
        raise HTTPException(status_code=404, detail="Organization license not found")

    old_expiry = lic.expiry_date or datetime.datetime.utcnow()
    if payload.custom_expiry_date:
        new_expiry = datetime.datetime.fromisoformat(payload.custom_expiry_date)
    else:
        add_days = payload.days or 30
        new_expiry = old_expiry + datetime.timedelta(days=add_days)

    lic.expiry_date = new_expiry
    if lic.status == "EXPIRED":
        lic.status = "ACTIVE"
    db.commit()

    audit = models.AuditLog(
        event_type="LICENSE_EXTENDED",
        actor_type="SUPER_ADMIN",
        actor_id=str(current_user.id),
        action=f"Extended license for organization {payload.org_id} to {new_expiry.isoformat()}",
        resource="licenses",
        result="SUCCESS",
        metadata_json={"org_id": payload.org_id, "new_expiry": new_expiry.isoformat()}
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "org_id": payload.org_id, "new_expiry_date": new_expiry.isoformat()}

@router.post("/licenses/renew")
def renew_organization_license(
    payload: ExtendLicenseRequest,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    lic = db.query(models.License).filter(models.License.org_id == payload.org_id).first()
    if not lic:
        raise HTTPException(status_code=404, detail="Organization license not found")

    new_expiry = datetime.datetime.utcnow() + datetime.timedelta(days=365)
    lic.expiry_date = new_expiry
    lic.status = "ACTIVE"
    db.commit()

    audit = models.AuditLog(
        event_type="LICENSE_RENEWED",
        actor_type="SUPER_ADMIN",
        actor_id=str(current_user.id),
        action=f"Renewed annual license for organization {payload.org_id}",
        resource="licenses",
        result="SUCCESS",
        metadata_json={"org_id": payload.org_id, "new_expiry": new_expiry.isoformat()}
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "org_id": payload.org_id, "new_expiry_date": new_expiry.isoformat()}

@router.post("/licenses/revoke")
def revoke_organization_license(
    payload: RevokeLicenseRequest,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    lic = db.query(models.License).filter(models.License.org_id == payload.org_id).first()
    if not lic:
        raise HTTPException(status_code=404, detail="Organization license not found")

    lic.status = "CANCELLED"
    db.commit()

    audit = models.AuditLog(
        event_type="LICENSE_REVOKED",
        actor_type="SUPER_ADMIN",
        actor_id=str(current_user.id),
        action=f"Revoked license for organization {payload.org_id} ({payload.reason})",
        resource="licenses",
        result="SUCCESS",
        metadata_json={"org_id": payload.org_id, "reason": payload.reason}
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "org_id": payload.org_id, "license_status": "CANCELLED"}

@router.post("/organizations")
def create_organization(
    payload: CreateOrgRequest,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    # 1. Create Organization
    org = models.Organization(
        name=payload.name,
        domain=payload.domain,
        admin_email=payload.admin_email,
        status="ACTIVE"
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    # 2. Assign Plan & Create License
    target_plan_id = payload.plan_id.upper() if payload.plan_id else "STARTER"
    plan = db.query(models.Plan).filter(models.Plan.id == target_plan_id).first()
    if not plan:
        plan = db.query(models.Plan).filter(models.Plan.id == "STARTER").first()
        target_plan_id = "STARTER"

    max_users = plan.max_users if plan else 10
    max_agents = plan.max_ai_agents if plan else 5
    max_api_keys = plan.max_api_keys if plan else 5
    max_reqs = plan.max_monthly_api_requests if plan else 100000

    lic = models.License(
        org_id=org.id,
        plan_id=target_plan_id,
        status="ACTIVE",
        start_date=datetime.datetime.utcnow(),
        expiry_date=datetime.datetime.utcnow() + datetime.timedelta(days=365),
        max_users=max_users,
        max_ai_agents=max_agents,
        max_api_keys=max_api_keys,
        max_monthly_api_requests=max_reqs
    )
    db.add(lic)

    lic_usage = models.LicenseUsage(
        org_id=org.id,
        api_requests_count=0,
        storage_used_gb=0.0
    )
    db.add(lic_usage)
    db.commit()

    # 3. Provision Organization ADMIN User
    existing_admin = db.query(models.User).filter(models.User.email == payload.admin_email).first()
    if not existing_admin:
        admin_user = models.User(
            org_id=org.id,
            email=payload.admin_email,
            full_name=payload.admin_full_name,
            role="ADMIN",
            department="Executive Management",
            password_hash=security.get_password_hash(payload.admin_password or "Blackbird@12."),
            status="ACTIVE"
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        admin_user_id = str(admin_user.id)
    else:
        existing_admin.org_id = org.id
        existing_admin.role = "ADMIN"
        db.commit()
        admin_user_id = str(existing_admin.id)

    # Record Audit Log
    audit = models.AuditLog(
        event_type="ORGANIZATION_CREATED",
        actor_type="SUPER_ADMIN",
        actor_id=str(current_user.id),
        action=f"Created organization {org.name} under plan {target_plan_id}",
        resource="organizations",
        result="SUCCESS",
        metadata_json={"org_id": str(org.id), "org_name": org.name, "admin_email": payload.admin_email}
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "org_id": str(org.id),
        "name": org.name,
        "plan_id": target_plan_id,
        "admin_user_id": admin_user_id
    }

@router.get("/organizations/{org_id}")
def get_organization_details(
    org_id: str,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    lic = db.query(models.License).filter(models.License.org_id == org.id).first()
    lic_usage = db.query(models.LicenseUsage).filter(models.LicenseUsage.org_id == org.id).first()

    # SUPER_ADMIN is NEVER returned inside an organization's user list
    users = db.query(models.User).filter(
        models.User.org_id == org.id,
        models.User.role != "SUPER_ADMIN"
    ).all()
    agents = db.query(models.Agent).filter(models.Agent.org_id == org.id).all()

    user_list = [{"id": str(u.id), "name": u.full_name, "email": u.email, "role": u.role, "status": u.status} for u in users]
    agent_list = [{"id": str(a.id), "name": a.name, "role": a.role, "autonomy": a.autonomy_level, "status": a.status} for a in agents]

    return {
        "id": str(org.id),
        "name": org.name,
        "domain": org.domain,
        "status": org.status,
        "admin_email": org.admin_email,
        "created_at": org.created_at.isoformat() if org.created_at else None,
        "license": {
            "id": str(lic.id) if lic else None,
            "plan_id": lic.plan_id if lic else "FREE",
            "status": lic.status if lic else "ACTIVE",
            "max_users": lic.max_users if lic else 5,
            "max_ai_agents": lic.max_ai_agents if lic else 3,
            "max_api_keys": lic.max_api_keys if lic else 2,
            "expiry_date": lic.expiry_date.isoformat() if (lic and lic.expiry_date) else None
        },
        "usage": {
            "api_requests_count": lic_usage.api_requests_count if lic_usage else 0,
            "storage_used_gb": lic_usage.storage_used_gb if lic_usage else 0.0
        },
        "users": user_list,
        "agents": agent_list
    }

@router.patch("/organizations/{org_id}/status")
def update_organization_status(
    org_id: str,
    payload: UpdateOrgStatusRequest,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    old_status = org.status
    org.status = payload.status.upper()

    # Also update license status
    lic = db.query(models.License).filter(models.License.org_id == org.id).first()
    if lic:
        if payload.status.upper() == "SUSPENDED":
            lic.status = "SUSPENDED"
        elif payload.status.upper() == "ACTIVE":
            lic.status = "ACTIVE"

    db.commit()

    # Audit Log
    audit = models.AuditLog(
        event_type="ORGANIZATION_STATUS_CHANGED",
        actor_type="SUPER_ADMIN",
        actor_id=str(current_user.id),
        action=f"Changed organization {org.name} status from {old_status} to {org.status}",
        resource="organizations",
        result="SUCCESS",
        metadata_json={"org_id": str(org.id), "old_status": old_status, "new_status": org.status}
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "org_id": str(org.id), "new_status": org.status}

@router.patch("/organizations/{org_id}/license")
def update_organization_license(
    org_id: str,
    payload: UpdateOrgLicenseRequest,
    current_user: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    lic = db.query(models.License).filter(models.License.org_id == org_id).first()
    if not lic:
        raise HTTPException(status_code=404, detail="Organization license not found")

    plan = db.query(models.Plan).filter(models.Plan.id == payload.plan_id.upper()).first()
    if not plan:
        raise HTTPException(status_code=400, detail=f"Plan {payload.plan_id} does not exist")

    lic.plan_id = plan.id
    lic.max_users = payload.max_users if payload.max_users is not None else plan.max_users
    lic.max_ai_agents = payload.max_ai_agents if payload.max_ai_agents is not None else plan.max_ai_agents
    if payload.status:
        lic.status = payload.status.upper()

    db.commit()

    audit = models.AuditLog(
        event_type="LICENSE_CHANGED",
        actor_type="SUPER_ADMIN",
        actor_id=str(current_user.id),
        action=f"Updated organization {org_id} license to {plan.id}",
        resource="licenses",
        result="SUCCESS",
        metadata_json={"org_id": org_id, "plan_id": plan.id}
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "org_id": org_id, "plan_id": plan.id, "max_users": lic.max_users, "max_ai_agents": lic.max_ai_agents}
