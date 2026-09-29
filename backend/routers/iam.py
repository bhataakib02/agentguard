import secrets
import hashlib
import datetime
from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from database import get_db
from core.deps import (
    get_current_user,
    require_admin,
    require_super_admin,
    require_permission,
    check_license_limit,
    HUMAN_ROLES,
    PERM_API_KEY_VIEW,
    PERM_API_KEY_CREATE,
    PERM_API_KEY_REVOKE,
    PERM_USER_INVITE,
    PERM_USER_VIEW,
)
from core.permissions import can_manage_role, get_user_permissions, ROLE_PERMISSIONS_MATRIX
import models

router = APIRouter(prefix="/iam", tags=["Identity & Access Management"])


# ============================================================================
# PYDANTIC SCHEMAS FOR IAM REQUESTS
# ============================================================================

class ApiKeyCreateRequest(BaseModel):
    name: str
    scopes: Optional[Union[str, List[str]]] = "read,write"
    expires_in_days: Optional[int] = 90


class InvitationCreateRequest(BaseModel):
    email: EmailStr
    role: str = "USER"
    expires_in_days: Optional[int] = 7


# ============================================================================
# 1. USER DIRECTORY & ROLES
# ============================================================================

@router.get("/users")
def list_users(
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(models.User).filter(models.User.role != "SUPER_ADMIN")
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.User.org_id == current_user.org_id)
    return query.all()


@router.get("/roles")
def list_roles(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    roles_def = [
        ("USER", "Default role for newly registered human users"),
        ("VIEWER", "Read-only access to general platform information"),
        ("ANALYST", "Analysis and investigation across agents, decisions & risk"),
        ("OPERATOR", "AI agent operational management and monitoring"),
        ("SECURITY_ANALYST", "Security center, SOC incidents, red-team testing & anomaly response"),
        ("MANAGER", "Operational and governance management with approval authority"),
        ("DEVELOPER", "Developer platform, REST APIs, integrations & API configuration"),
        ("ADMIN", "Organization administrator with user & policy management access"),
        ("SUPER_ADMIN", "Highest platform-level control & cross-organization administration"),
        ("AGENT", "Machine identity used by autonomous AI Employees (runtime identity)")
    ]

    res = []
    for r_code, r_desc in roles_def:
        query = db.query(models.User).filter(models.User.role == r_code)
        if current_user.role != "SUPER_ADMIN":
            query = query.filter(models.User.org_id == current_user.org_id)
        cnt = query.count()
        res.append({
            "role": r_code,
            "description": r_desc,
            "users_count": cnt,
            "is_machine": r_code == "AGENT",
            "permissions": sorted(list(ROLE_PERMISSIONS_MATRIX.get(r_code, set())))
        })
    return res


@router.get("/permissions")
def get_current_user_permissions(
    current_user: models.User = Depends(get_current_user)
):
    """Returns the authenticated user's authoritative permissions and role hierarchy."""
    perms = get_user_permissions(current_user.role)
    return {
        "user_id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role,
        "org_id": str(current_user.org_id),
        "permissions": perms
    }


# ============================================================================
# 2. SECURE API KEY MANAGEMENT
# ============================================================================

@router.get("/api-keys")
def list_api_keys(
    current_user: models.User = Depends(require_permission(PERM_API_KEY_VIEW)),
    db: Session = Depends(get_db)
):
    """Lists organization API keys. Secret hashes and plaintext keys are NEVER returned."""
    query = db.query(models.ApiKey)
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.ApiKey.org_id == current_user.org_id)

    keys = query.order_by(models.ApiKey.created_at.desc()).all()
    res = []
    for k in keys:
        res.append({
            "id": str(k.id),
            "org_id": str(k.org_id),
            "owner_id": str(k.owner_id) if k.owner_id else None,
            "name": k.name,
            "key_prefix": k.key_prefix,
            "scopes": k.scopes,
            "is_revoked": bool(k.is_revoked),
            "revoked_at": k.revoked_at.isoformat() if k.revoked_at else None,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            "created_at": k.created_at.isoformat() if k.created_at else None,
        })
    return res


@router.post("/api-keys")
def create_api_key(
    req: ApiKeyCreateRequest,
    current_user: models.User = Depends(require_permission(PERM_API_KEY_CREATE)),
    db: Session = Depends(get_db)
):
    """
    Generates a cryptographically secure API key.
    The raw plaintext key is returned ONCE in this response and NEVER retrievable again.
    """
    # Generate 32 bytes of cryptographic randomness (hex formatted)
    raw_secret = f"ag_live_{secrets.token_hex(24)}"
    prefix = f"{raw_secret[:12]}****{raw_secret[-4:]}"
    key_hash = hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()

    expires_at = None
    if req.expires_in_days and req.expires_in_days > 0:
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=req.expires_in_days)

    scopes_str = "read,write"
    if req.scopes:
        if isinstance(req.scopes, list):
            scopes_str = ",".join(req.scopes)
        else:
            scopes_str = str(req.scopes)

    api_key = models.ApiKey(
        org_id=current_user.org_id,
        owner_id=current_user.id,
        name=req.name.strip(),
        key_prefix=prefix,
        key_hash=key_hash,
        scopes=scopes_str,
        is_revoked=False,
        expires_at=expires_at
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    # Privileged Audit Log (Never log the raw secret)
    audit = models.AuditLog(
        org_id=current_user.org_id,
        event_type="API_KEY_CREATED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="CREATE_API_KEY",
        resource=f"api_key:{api_key.id}",
        result="SUCCESS",
        metadata_json={
            "key_id": str(api_key.id),
            "key_prefix": prefix,
            "name": req.name,
            "scopes": req.scopes,
            "expires_at": expires_at.isoformat() if expires_at else None
        }
    )
    db.add(audit)
    db.commit()

    return {
        "status": "SUCCESS",
        "id": str(api_key.id),
        "name": api_key.name,
        "key_prefix": prefix,
        "api_key": raw_secret,  # RETURNED ONCE ONLY
        "plaintext_key": raw_secret,
        "scopes": api_key.scopes,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "created_at": api_key.created_at.isoformat(),
        "warning": "Copy this key now. It will not be shown again."
    }


@router.delete("/api-keys/{key_id}")
@router.post("/api-keys/{key_id}/revoke")
def revoke_api_key(
    key_id: str,
    current_user: models.User = Depends(require_permission(PERM_API_KEY_REVOKE)),
    db: Session = Depends(get_db)
):
    """Revokes an API key immediately, rendering it unusable."""
    key = db.query(models.ApiKey).filter(models.ApiKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    if current_user.role != "SUPER_ADMIN" and key.org_id != current_user.org_id:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot revoke API key of another organization")

    key.is_revoked = True
    key.revoked_at = datetime.datetime.utcnow()
    key.revoked_by_id = current_user.id
    db.commit()

    audit = models.AuditLog(
        org_id=key.org_id,
        event_type="API_KEY_REVOKED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="REVOKE_API_KEY",
        resource=f"api_key:{key.id}",
        result="SUCCESS",
        metadata_json={
            "key_id": str(key.id),
            "key_prefix": key.key_prefix,
            "name": key.name
        }
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "message": f"API key '{key.name}' successfully revoked", "id": str(key.id)}


# ============================================================================
# 3. SECURE USER INVITATION SYSTEM
# ============================================================================

@router.get("/invitations")
def list_invitations(
    current_user: models.User = Depends(require_permission(PERM_USER_VIEW)),
    db: Session = Depends(get_db)
):
    """Lists organization invitations. Raw invitation tokens and hashes are never exposed."""
    query = db.query(models.UserInvitation)
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.UserInvitation.org_id == current_user.org_id)

    invs = query.order_by(models.UserInvitation.created_at.desc()).all()
    res = []
    for inv in invs:
        # Check expired
        is_expired = inv.expires_at < datetime.datetime.utcnow() and inv.status == "PENDING"
        res.append({
            "id": str(inv.id),
            "org_id": str(inv.org_id),
            "email": inv.email,
            "role": inv.role,
            "status": "EXPIRED" if is_expired else inv.status,
            "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
            "accepted_at": inv.accepted_at.isoformat() if inv.accepted_at else None,
        })
    return res


@router.post("/invitations")
def create_invitation(
    req: InvitationCreateRequest,
    current_user: models.User = Depends(require_permission(PERM_USER_INVITE)),
    db: Session = Depends(get_db)
):
    """
    Creates a secure, one-time invitation to join the organization.
    Stores a SHA-256 hash. Email delivery is explicitly marked NOT_CONFIGURED.
    """
    target_role = req.role.upper().strip()
    if target_role not in HUMAN_ROLES or target_role == "AGENT":
        raise HTTPException(
            status_code=400,
            detail=f"Invalid human role '{target_role}'. Must be one of: {', '.join(HUMAN_ROLES[:-1])}"
        )

    # Privilege escalation protection
    if not can_manage_role(current_user.role, target_role):
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: You do not have permission to invite users with role '{target_role}'"
        )

    # Enforce license limits
    check_license_limit(str(current_user.org_id), "users", db)

    # Check if user already exists
    existing = db.query(models.User).filter(models.User.email == req.email.lower()).first()
    if existing:
        if str(existing.org_id) == str(current_user.org_id):
            raise HTTPException(status_code=409, detail=f"User {req.email} is already a member of this organization")
        else:
            raise HTTPException(status_code=400, detail="User already belongs to another organization")

    # Generate one-time cryptographic token
    raw_token = f"inv_{secrets.token_hex(24)}"
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    expires_days = req.expires_in_days if (req.expires_in_days and req.expires_in_days > 0) else 7
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=expires_days)

    inv = models.UserInvitation(
        org_id=current_user.org_id,
        email=req.email.lower().strip(),
        role=target_role,
        invited_by_id=current_user.id,
        token_hash=token_hash,
        status="PENDING",
        expires_at=expires_at
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)

    audit = models.AuditLog(
        org_id=current_user.org_id,
        event_type="USER_INVITED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="INVITE_USER",
        resource=f"invitation:{inv.id}",
        result="SUCCESS",
        metadata_json={
            "invitation_id": str(inv.id),
            "email": req.email,
            "role": target_role,
            "expires_at": expires_at.isoformat()
        }
    )
    db.add(audit)
    db.commit()

    return {
        "status": "INVITED",
        "invitation_status": inv.status,
        "id": str(inv.id),
        "email": inv.email,
        "role": inv.role,
        "invitation_token": raw_token,  # Provided for dev/direct access; hashed in DB
        "invitation_link": f"/register?invitation={raw_token}",
        "email_delivery": "NOT_CONFIGURED",
        "expires_at": expires_at.isoformat()
    }


@router.delete("/invitations/{invitation_id}")
def revoke_invitation(
    invitation_id: str,
    current_user: models.User = Depends(require_permission(PERM_USER_INVITE)),
    db: Session = Depends(get_db)
):
    inv = db.query(models.UserInvitation).filter(models.UserInvitation.id == invitation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if current_user.role != "SUPER_ADMIN" and inv.org_id != current_user.org_id:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot revoke invitation for another organization")

    inv.status = "REVOKED"
    db.commit()

    audit = models.AuditLog(
        org_id=inv.org_id,
        event_type="INVITATION_REVOKED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="REVOKE_INVITATION",
        resource=f"invitation:{inv.id}",
        result="SUCCESS",
        metadata_json={"invitation_id": str(inv.id), "email": inv.email}
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "message": f"Invitation for {inv.email} revoked"}


# ============================================================================
# 4. SESSIONS (NO TOKEN MATERIAL EXPOSED)
# ============================================================================

@router.get("/sessions")
def list_sessions(
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Lists active sessions for the organization. Sensitive token material is securely masked."""
    query = db.query(models.Session).join(models.User)
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.User.org_id == current_user.org_id)

    sessions = query.order_by(models.Session.created_at.desc()).limit(100).all()
    res = []
    for s in sessions:
        u = s.user
        masked_token = f"sess_****{s.token[-6:]}" if s.token and len(s.token) > 6 else "sess_****"
        res.append({
            "id": str(s.id),
            "user_id": str(s.user_id),
            "user_email": u.email if u else "Unknown",
            "user_name": u.full_name if u else "Unknown",
            "role": u.role if u else "Unknown",
            "token_preview": masked_token,
            "ip_address": s.ip_address,
            "user_agent": s.user_agent,
            "revoked": bool(s.revoked),
            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })
    return res


@router.delete("/sessions/{session_id}")
def revoke_session(
    session_id: str,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Revokes a session by ID."""
    s = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")

    u = s.user
    if current_user.role != "SUPER_ADMIN" and u and u.org_id != current_user.org_id:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot revoke session for another organization")

    s.revoked = True
    db.commit()

    audit = models.AuditLog(
        org_id=u.org_id if u else current_user.org_id,
        event_type="SESSION_REVOKED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="REVOKE_SESSION",
        resource=f"session:{session_id}",
        result="SUCCESS",
        metadata_json={"session_id": session_id, "target_user_id": str(s.user_id)}
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "message": "Session successfully revoked"}
