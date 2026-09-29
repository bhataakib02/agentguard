from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from core.deps import get_current_user
import models

router = APIRouter(prefix="/security", tags=["Security Operations Center"])

@router.get("/incidents")
def list_incidents(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.SecurityIncident)
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.SecurityIncident.org_id == current_user.org_id)
    return query.all()

@router.get("/overview")
def get_security_overview(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inc_query = db.query(models.SecurityIncident)
    agent_query = db.query(models.Agent)
    if current_user.role != "SUPER_ADMIN":
        inc_query = inc_query.filter(models.SecurityIncident.org_id == current_user.org_id)
        agent_query = agent_query.filter(models.Agent.org_id == current_user.org_id)

    total_incidents = inc_query.count()
    open_incidents = inc_query.filter(models.SecurityIncident.status == "OPEN").count()
    critical_agents = agent_query.filter(models.Agent.risk_score > 60).count()
    suspended_agents = agent_query.filter(models.Agent.status == "SUSPENDED").count()

    return {
        "total_incidents": total_incidents,
        "open_incidents": open_incidents,
        "critical_agents": critical_agents,
        "suspended_agents": suspended_agents,
        "security_status": "MONITORED"
    }
