import os
import time
import json
import datetime
import urllib.request
import urllib.parse
import logging
from typing import Optional, Dict, Tuple
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

HUMAN_ROLES = [
    "USER",
    "VIEWER",
    "ANALYST",
    "OPERATOR",
    "SECURITY_ANALYST",
    "MANAGER",
    "DEVELOPER",
    "ADMIN",
    "SUPER_ADMIN"
]

MACHINE_ROLES = ["AGENT"]

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
    db: Session = Depends(get_db)
) -> models.User:
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

def require_super_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only SUPER_ADMIN can perform this action"
        )
    return current_user

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
