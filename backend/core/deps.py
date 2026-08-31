from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from database import get_db
from config import settings
import models

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
    user_id = None
    email = None

    # 1. Try decoding local backend JWT
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")
    except JWTError:
        # 2. Decode Supabase Auth JWT unverified claims
        try:
            payload = jwt.get_unverified_claims(token)
            user_id = payload.get("sub")
            email = payload.get("email")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format"
            )

    user = None
    if user_id:
        user = db.query(models.User).filter(
            (models.User.id == user_id) | (models.User.auth_user_id == user_id)
        ).first()

    if not user and email:
        user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user profile not found in database"
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
