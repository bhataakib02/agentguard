from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(prefix="/permissions", tags=["Permission Management"])

@router.get("")
def list_permissions(db: Session = Depends(get_db)):
    return db.query(models.Permission).all()

@router.get("/matrix")
def get_permission_matrix(db: Session = Depends(get_db)):
    agents = db.query(models.Agent).all()
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
def list_permission_templates():
    return [
        {"name": "Customer Support Agent", "default_permissions": ["Orders:READ", "Customers:READ", "Refunds:READ"]},
        {"name": "Finance Refund Agent", "default_permissions": ["Refunds:WRITE", "PaymentGateway:EXECUTE", "Transactions:CREATE"]},
        {"name": "Security Auditor Agent", "default_permissions": ["AuditLogs:READ", "Incidents:READ", "Behavior:READ"]}
    ]
