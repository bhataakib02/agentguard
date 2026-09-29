import os
import time
import json
import datetime
import urllib.request
import urllib.parse
import logging
from typing import Optional, Dict, Tuple, List, Set, Any
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from database import get_db
from config import settings
import models

logger = logging.getLogger("agentguard.auth")

# In-memory cache for cryptographically verified Supabase tokens to avoid network latency on every request
# token -> (cache_timestamp, auth_user_id, email)
_supabase_token_cache: Dict[str, Tuple[float, str, str]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes

def verify_supabase_token(token: str) -> Optional[Tuple[str, str]]:
    """
    Cryptographically verifies a Supabase JWT token.
    1. Checks fast in-memory verification cache.
    2. If SUPABASE_JWT_SECRET is set, decodes & verifies signature locally.
    3. Calls Supabase Auth GET /auth/v1/user endpoint to verify against Supabase server.
    Returns (auth_user_id, email) if valid, None if invalid/expired/forged.
    """
    now = time.time()

    # 1. Check in-memory cache
    if token in _supabase_token_cache:
        cached_time, user_id, email = _supabase_token_cache[token]
        if now - cached_time < CACHE_TTL_SECONDS:
            return user_id, email
        else:
            del _supabase_token_cache[token]

    # 2. Check local JWT secret if SUPABASE_JWT_SECRET is set
    supabase_jwt_secret = getattr(settings, "SUPABASE_JWT_SECRET", None) or os.getenv("SUPABASE_JWT_SECRET")
    if supabase_jwt_secret:
        try:
            payload = jwt.decode(token, supabase_jwt_secret, algorithms=["HS256"], audience="authenticated")
            user_id = payload.get("sub")
            email = payload.get("email")
            if user_id:
                _supabase_token_cache[token] = (now, str(user_id), email or "")
                return str(user_id), email or ""
        except JWTError:
            pass

    # 3. Authoritative verification via Supabase Auth API
    supabase_url = getattr(settings, "SUPABASE_URL", "https://xjragvyzlailmtfwjfnm.supabase.co").rstrip("/")
    api_key = getattr(settings, "SUPABASE_PUBLISHABLE_KEY", "")

    verify_url = f"{supabase_url}/auth/v1/user"
    req = urllib.request.Request(
        verify_url,
        headers={
            "Authorization": f"Bearer {token}",
            "apikey": api_key,
            "User-Agent": "AgentGuard-Auth-Verifier/1.0"
        },
        method="GET"
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                user_id = data.get("id")
                email = data.get("email")
                if user_id:
                    _supabase_token_cache[token] = (now, str(user_id), email or "")
                    return str(user_id), email or ""
    except Exception as e:
        logger.warning(f"Supabase token verification failed: {e}")
        return None

    return None

from core.permissions import (
    HUMAN_ROLES,
    MACHINE_ROLES,
    ROLE_SUPER_ADMIN,
    ROLE_ADMIN,
    ROLE_DEVELOPER,
    ROLE_MANAGER,
    ROLE_SECURITY_ANALYST,
    ROLE_OPERATOR,
    ROLE_ANALYST,
    ROLE_VIEWER,
    ROLE_USER,
    ROLE_AGENT,
    ROLE_LEVELS,
    ROLE_PERMISSIONS_MATRIX,
    get_role_level,
    can_manage_role,
    has_permission,
    get_user_permissions,
    # Permissions
    PERM_ORGANIZATION_VIEW,
    PERM_ORGANIZATION_UPDATE,
    PERM_ORGANIZATION_SECURITY_UPDATE,
    PERM_USER_VIEW,
    PERM_USER_CREATE,
    PERM_USER_UPDATE,
    PERM_USER_SUSPEND,
    PERM_USER_DELETE,
    PERM_USER_ROLE_ASSIGN,
    PERM_USER_INVITE,
    PERM_AGENT_VIEW,
    PERM_AGENT_CREATE,
    PERM_AGENT_UPDATE,
    PERM_AGENT_SUSPEND,
    PERM_AGENT_RESUME,
    PERM_AGENT_DELETE,
    PERM_AGENT_BUDGET_UPDATE,
    PERM_AGENT_POLICY_UPDATE,
    PERM_POLICY_VIEW,
    PERM_POLICY_CREATE,
    PERM_POLICY_UPDATE,
    PERM_POLICY_DELETE,
    PERM_POLICY_ENABLE,
    PERM_POLICY_DISABLE,
    PERM_DECISION_VIEW,
    PERM_DECISION_CREATE,
    PERM_DECISION_REVIEW,
    PERM_DECISION_APPROVE,
    PERM_DECISION_REJECT,
    PERM_AUDIT_VIEW,
    PERM_AUDIT_EXPORT,
    PERM_SECURITY_VIEW,
    PERM_SECURITY_INCIDENT_CREATE,
    PERM_SECURITY_INCIDENT_UPDATE,
    PERM_SECURITY_INCIDENT_RESOLVE,
    PERM_REPORT_VIEW,
    PERM_REPORT_GENERATE,
    PERM_REPORT_DOWNLOAD,
    PERM_WEBHOOK_VIEW,
    PERM_WEBHOOK_CREATE,
    PERM_WEBHOOK_UPDATE,
    PERM_WEBHOOK_DELETE,
    PERM_WEBHOOK_RETRY,
    PERM_TELEMETRY_VIEW,
    PERM_TELEMETRY_EXPORT,
    PERM_API_KEY_VIEW,
    PERM_API_KEY_CREATE,
    PERM_API_KEY_REVOKE,
    PERM_PLATFORM_VIEW,
    PERM_PLATFORM_ADMIN,
)

ROLE_PERMISSIONS = {
    "USER": ["dashboard:read", "profile:read", "profile:write"],
    "VIEWER": ["dashboard:read", "profile:read", "agents:read", "analytics:read"],
    "ANALYST": ["dashboard:read", "profile:read", "agents:read", "decisions:read", "risk:read", "audit:read", "provenance:read", "analytics:read"],
    "OPERATOR": ["dashboard:read", "profile:read", "agents:read", "agents:manage", "capabilities:read", "capabilities:execute", "runtime:read"],
    "SECURITY_ANALYST": ["dashboard:read", "profile:read", "agents:read", "security:read", "security:write", "circuit_breaker:manage", "red_team:execute", "incidents:manage"],
    "MANAGER": ["dashboard:read", "profile:read", "agents:read", "approvals:read", "approvals:write", "budgets:read", "policies:read"],
    "DEVELOPER": ["dashboard:read", "profile:read", "agents:read", "api_keys:read", "api_keys:write", "integrations:manage", "assistant:use"],
    "ADMIN": ["*"],
    "SUPER_ADMIN": ["*"]
}

def get_current_user(
    authorization: str = Header(None),
    x_api_key: str = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> models.User:
    # -------------------------------------------------------------
    # 1. API Key Authentication (X-API-Key or Bearer ag_live_...)
    # -------------------------------------------------------------
    raw_api_key = x_api_key
    if not raw_api_key and authorization:
        candidate = authorization.replace("Bearer ", "").strip()
        if candidate.startswith("ag_live_"):
            raw_api_key = candidate

    if raw_api_key:
        import hashlib
        key_hash = hashlib.sha256(raw_api_key.strip().encode("utf-8")).hexdigest()
        api_key = db.query(models.ApiKey).filter(models.ApiKey.key_hash == key_hash).first()
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid, revoked, or expired API key"
            )
        if api_key.is_revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has been revoked"
            )
        now_dt = datetime.datetime.utcnow()
        if api_key.expires_at and api_key.expires_at < now_dt:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has expired"
            )

        api_key.last_used_at = now_dt
        db.commit()

        if api_key.owner_id:
            user = db.query(models.User).filter(models.User.id == api_key.owner_id).first()
            if user:
                if user.status != "ACTIVE":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Forbidden: Account status is {user.status}"
                    )
                return user

        # Virtual proxy user identity bound strictly to API key's organization
        proxy_user = models.User(
            id=api_key.id,
            org_id=api_key.org_id,
            email=f"apikey-{api_key.key_prefix}@agentguard.internal",
            full_name=f"API Key: {api_key.name}",
            role="DEVELOPER",
            status="ACTIVE"
        )
        return proxy_user

    # -------------------------------------------------------------
    # 2. Bearer JWT Authentication
    # -------------------------------------------------------------
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required"
        )

    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required"
        )

    user_id = None
    email = None

    # Step 1: Decode local backend JWT signed with settings.SECRET_KEY
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")
    except JWTError:
        # Step 2: Cryptographically verify Supabase Auth JWT
        verified = verify_supabase_token(token)
        if not verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid, expired, or unverified authentication token"
            )
        user_id, email = verified

    # Step 3: Authoritative Database Profile Resolution
    user = None
    if user_id:
        user = db.query(models.User).filter(
            (models.User.id == user_id) | (models.User.auth_user_id == user_id)
        ).first()

    if not user and email:
        user = db.query(models.User).filter(models.User.email == email).first()
        if user and user_id and not user.auth_user_id:
            user.auth_user_id = user_id
            db.commit()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user profile not found in database"
        )

    # Step 4: Check if session token was explicitly revoked
    db_session = db.query(models.Session).filter(models.Session.token == token).first()
    if db_session:
        if db_session.revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked. Please log in again."
            )
        if db_session.expires_at:
            exp = db_session.expires_at
            now_dt = datetime.datetime.now(datetime.timezone.utc)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=datetime.timezone.utc)
            if exp < now_dt:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session has expired. Please log in again."
                )

    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Account status is {user.status}"
        )

    return user

def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.role not in ["ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Administrative privileges required"
        )
    return current_user

def require_org_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.role not in ["ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Organization administrator privileges required"
        )
    return current_user

def require_super_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only SUPER_ADMIN can perform this action"
        )
    return current_user

def require_permission(permission: str):
    """Centralized dependency checking if the user's role grants the requested formal permission."""
    def dependency(current_user: models.User = Depends(get_current_user)) -> models.User:
        if current_user.role == "SUPER_ADMIN":
            return current_user
        perms = get_user_permissions(current_user.role)
        if "*" in perms or permission in perms:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Missing required permission '{permission}'"
        )
    return dependency

def require_role(allowed_roles: List[str]):
    """Centralized dependency checking if the user belongs to one of allowed_roles (or SUPER_ADMIN)."""
    def dependency(current_user: models.User = Depends(get_current_user)) -> models.User:
        if current_user.role == "SUPER_ADMIN" or current_user.role in allowed_roles:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Requires one of roles: {', '.join(allowed_roles)}"
        )
    return dependency

def check_org_isolation(current_user: models.User, target_org_id: str):
    if current_user.role == "SUPER_ADMIN":
        return True
    if str(current_user.org_id) != str(target_org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cross-organization access is strictly prohibited"
        )
    return True

def get_effective_org_id(current_user: models.User, x_org_context: Optional[str] = None) -> str:
    if current_user.role == "SUPER_ADMIN" and x_org_context and x_org_context != "ALL":
        return x_org_context
    return str(current_user.org_id)

def check_license_limit(org_id: str, resource_type: str, db: Session):
    lic = db.query(models.License).filter(models.License.org_id == org_id).first()
    if not lic:
        max_users = 10
        max_agents = 5
        lic_status = "ACTIVE"
    else:
        max_users = lic.max_users
        max_agents = lic.max_ai_agents
        lic_status = lic.status

    if lic_status in ["EXPIRED", "SUSPENDED", "CANCELLED"]:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"LICENSE_RESTRICTED: Organization license status is {lic_status}. Resource creation is blocked."
        )

    if resource_type == "users":
        current_count = db.query(models.User).filter(
            models.User.org_id == org_id,
            models.User.role != "SUPER_ADMIN"
        ).count()
        if current_count >= max_users:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"LICENSE_LIMIT_REACHED: Organization has reached maximum user limit ({max_users}) under current plan"
            )
    elif resource_type == "agents":
        current_count = db.query(models.Agent).filter(models.Agent.org_id == org_id).count()
        if current_count >= max_agents:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"LICENSE_LIMIT_REACHED: Organization has reached maximum AI agent limit ({max_agents}) under current plan"
            )
    return True
