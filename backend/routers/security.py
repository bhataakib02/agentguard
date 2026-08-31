from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(prefix="/security", tags=["Security Operations Center"])

@router.get("/incidents")
def list_incidents(db: Session = Depends(get_db)):
    return db.query(models.SecurityIncident).all()

@router.get("/overview")
def get_security_overview(db: Session = Depends(get_db)):
    total_incidents = db.query(models.SecurityIncident).count()
    open_incidents = db.query(models.SecurityIncident).filter(models.SecurityIncident.status == "OPEN").count()
    critical_agents = db.query(models.Agent).filter(models.Agent.risk_score > 60).count()
    suspended_agents = db.query(models.Agent).filter(models.Agent.status == "SUSPENDED").count()

    return {
        "total_incidents": total_incidents,
        "open_incidents": open_incidents,
        "critical_agents": critical_agents,
        "suspended_agents": suspended_agents,
        "security_status": "MONITORED"
    }
