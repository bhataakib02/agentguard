from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from core.deps import get_current_user
import models

router = APIRouter(prefix="/permissions", tags=["Permission Management"])

@router.get("")
def list_permissions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Permission)
    if current_user.role != "SUPER_ADMIN":
        query = query.join(models.Agent).filter(models.Agent.org_id == current_user.org_id)
    return query.all()

@router.get("/matrix")
def get_permission_matrix(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Agent)
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.Agent.org_id == current_user.org_id)
    agents = query.all()

    matrix = []
    for agent in agents:
        perms = db.query(models.Permission).filter(models.Permission.agent_id == agent.id).all()
        perm_map = {p.resource_name: p.action for p in perms}
        matrix.append({
            "agent_id": agent.id,
            "agent_code": agent.agent_code,
            "name": agent.name,
            "department": agent.department,
            "permissions": perm_map
        })
    return matrix

@router.get("/templates")
def list_permission_templates(
    current_user: models.User = Depends(get_current_user)
):
    return [
        {"name": "Customer Support Agent", "default_permissions": ["Orders:READ", "Customers:READ", "Refunds:READ"]},
        {"name": "Finance Refund Agent", "default_permissions": ["Refunds:WRITE", "PaymentGateway:EXECUTE", "Transactions:CREATE"]},
        {"name": "Security Auditor Agent", "default_permissions": ["AuditLogs:READ", "Incidents:READ", "Behavior:READ"]}
    ]
