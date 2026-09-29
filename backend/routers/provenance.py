from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from core.deps import get_current_user
import models

router = APIRouter(prefix="/provenance", tags=["Provenance Graph"])

@router.get("/events")
def list_provenance_events(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.ProvenanceEvent)
    if current_user.role != "SUPER_ADMIN":
        query = query.join(models.Decision).join(models.Agent).filter(models.Agent.org_id == current_user.org_id)
    return query.all()

@router.get("/{id}")
def get_provenance_detail(
    id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ev = db.query(models.ProvenanceEvent).filter((models.ProvenanceEvent.id == id) | (models.ProvenanceEvent.decision_id == id)).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Provenance record not found")

    dec = db.query(models.Decision).filter(models.Decision.id == ev.decision_id).first()
    if dec:
        agent = db.query(models.Agent).filter(models.Agent.id == dec.agent_id).first()
        if agent and current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Provenance record belongs to another organization")

    return ev
