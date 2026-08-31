from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import datetime

from database import get_db
from core.deps import get_current_user, HUMAN_ROLES, ROLE_PERMISSIONS, check_org_isolation
import models

router = APIRouter(prefix="/profile", tags=["User Profile & Security"])

HUMAN_ROLE_LEVELS: Dict[str, int] = {
    "USER": 1,
    "VIEWER": 2,
    "ANALYST": 3,
    "OPERATOR": 4,
    "SECURITY_ANALYST": 5,
    "MANAGER": 6,
    "DEVELOPER": 7,
    "ADMIN": 8,
    "SUPER_ADMIN": 9
}

ROLE_DESCRIPTIONS: Dict[str, str] = {
    "USER": "Default authenticated human user with basic dashboard access",
    "VIEWER": "Read-only access to general platform information, analytics & trust metrics",
    "ANALYST": "AI governance analysis and investigation across agents, risk & audit logs",
    "OPERATOR": "Operational management of AI agents, capabilities & runtime circuit breakers",
    "SECURITY_ANALYST": "Security operations, incident response, SOC events & red-team testing",
    "MANAGER": "Operational & governance management with human request approval authority",
    "DEVELOPER": "Developer platform, REST API documentation, webhooks & integration management",
    "ADMIN": "Organization administrator with user management & policy controls",
    "SUPER_ADMIN": "Highest platform-level control & cross-organization administration"
}

FORBIDDEN_PROFILE_FIELDS = {"role", "org_id", "permissions", "status", "is_admin", "is_super_admin"}

class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    phone: Optional[str] = None

class ResendVerificationRequest(BaseModel):
    email: str

def build_profile_response(user: models.User, db: Session) -> Dict[str, Any]:
    org = db.query(models.Organization).filter(models.Organization.id == user.org_id).first()
    org_name = org.name if org else "AgentGuard Enterprise"

    role_code = user.role or "USER"
    role_level = HUMAN_ROLE_LEVELS.get(role_code, 1)
    role_desc = ROLE_DESCRIPTIONS.get(role_code, "Standard User")
    permissions = ROLE_PERMISSIONS.get(role_code, ["dashboard:read", "profile:read"])

    # Query real Supabase Auth email_confirmed_at
    is_email_verified = True
    try:
        auth_row = db.execute(text("SELECT email_confirmed_at FROM auth.users WHERE email = :email;"), {"email": user.email}).first()
        if auth_row and auth_row.email_confirmed_at is None:
            is_email_verified = False
    except Exception:
        is_email_verified = True

    return {
        "id": str(user.id),
        "auth_user_id": user.auth_user_id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone or "",
        "department": user.department or "General",
        "job_title": user.job_title or "Team Member",
        "org_id": str(user.org_id),
        "org_name": org_name,
        "role": role_code,
        "role_level": role_level,
        "role_description": role_desc,
        "status": user.status or "ACTIVE",
        "email_verified": is_email_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "effective_permissions": permissions
    }

# --- STATIC PATH ROUTES (MUST BE DECLARED BEFORE /{target_user_id}) ---

@router.get("/me")
def get_current_user_profile(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return build_profile_response(current_user, db)

@router.patch("/me")
async def update_user_profile(
    request: Request,
    payload: ProfileUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    raw_body = await request.json()

    # Reject privilege escalation attempts
    attempted_keys = set(raw_body.keys())
    intersection = attempted_keys.intersection(FORBIDDEN_PROFILE_FIELDS)
    if intersection:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Modifying security attributes ({', '.join(intersection)}) via profile update is strictly prohibited"
        )

    if payload.full_name is not None:
        name_val = payload.full_name.strip()
        if not name_val:
            raise HTTPException(status_code=400, detail="Full name cannot be blank")
        current_user.full_name = name_val

    if payload.department is not None:
        current_user.department = payload.department.strip()
    if payload.job_title is not None:
        current_user.job_title = payload.job_title.strip()
    if payload.phone is not None:
        current_user.phone = payload.phone.strip()

    current_user.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(current_user)

    # Record Audit Log
    audit = models.AuditLog(
        event_type="PROFILE_UPDATED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="Updated personal profile details",
        resource="users",
        result="SUCCESS",
        metadata_json={"updated_fields": list(raw_body.keys())}
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "message": "Profile updated successfully"}

@router.get("/sessions")
def get_user_sessions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sessions = db.query(models.Session).filter(
        models.Session.user_id == current_user.id,
        models.Session.revoked == False
    ).order_by(models.Session.created_at.desc()).all()

    res = []
    if not sessions:
        res.append({
            "id": "sess_current",
            "device": "Web Browser / Desktop Client",
            "ip_address": "127.0.0.1 (Local)",
            "created_at": datetime.datetime.utcnow().isoformat(),
            "expires_at": (datetime.datetime.utcnow() + datetime.timedelta(days=1)).isoformat(),
            "is_current": True
        })
    else:
        for idx, s in enumerate(sessions):
            res.append({
                "id": str(s.id),
                "device": "Web Browser / Desktop Client",
                "ip_address": "127.0.0.1 (Local)",
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
                "is_current": (idx == 0)
            })
    return res

@router.delete("/sessions/{session_id}")
def revoke_user_session(
    session_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if session_id != "sess_current":
        target_session = db.query(models.Session).filter(
            models.Session.id == session_id,
            models.Session.user_id == current_user.id
        ).first()

        if target_session:
            target_session.revoked = True
            db.commit()

    # Record Audit Log
    audit = models.AuditLog(
        event_type="SESSION_REVOKED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="Revoked authenticated session",
        resource="sessions",
        result="SUCCESS",
        metadata_json={"session_id": session_id}
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "message": "Session revoked successfully"}

@router.post("/sessions/revoke-others")
def revoke_other_user_sessions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db.query(models.Session).filter(
        models.Session.user_id == current_user.id
    ).update({"revoked": True})
    db.commit()

    audit = models.AuditLog(
        event_type="SESSION_REVOKED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="Revoked all other active sessions",
        resource="sessions",
        result="SUCCESS",
        metadata_json={"action": "revoke_others"}
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "message": "All other sessions revoked"}

@router.get("/activity")
def get_user_activity(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logs = db.query(models.AuditLog).filter(
        models.AuditLog.actor_id == str(current_user.id)
    ).order_by(models.AuditLog.timestamp.desc()).limit(50).all()

    res = []
    for l in logs:
        res.append({
            "id": str(l.id),
            "event_type": l.event_type,
            "action": l.action,
            "resource": l.resource,
            "result": l.result,
            "timestamp": l.timestamp.isoformat() if l.timestamp else None,
            "metadata_json": l.metadata_json
        })
    return res

# --- DYNAMIC PARAMETER ROUTE (MUST BE DECLARED LAST) ---

@router.get("/{target_user_id}")
def get_user_profile_by_id(
    target_user_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Self-access is always allowed
    if str(current_user.id) == target_user_id:
        return build_profile_response(current_user, db)

    # Cross-access requires ADMIN or SUPER_ADMIN
    if current_user.role not in ["ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Standard users are not authorized to view other user profiles"
        )

    target = db.query(models.User).filter(models.User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User profile not found")

    check_org_isolation(current_user, target.org_id)
    return build_profile_response(target, db)
