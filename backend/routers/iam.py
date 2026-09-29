from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from core.deps import get_current_user, require_admin, HUMAN_ROLES
import models

router = APIRouter(prefix="/iam", tags=["Identity & Access Management"])

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
            "is_machine": r_code == "AGENT"
        })
    return res

@router.get("/api-keys")
def list_api_keys(
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(models.ApiKey)
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.ApiKey.org_id == current_user.org_id)
    return query.all()

@router.get("/sessions")
def list_sessions(
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(models.Session).join(models.User).filter(models.Session.revoked == False)
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.User.org_id == current_user.org_id)
    return query.all()
