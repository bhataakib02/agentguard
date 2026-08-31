from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(prefix="/provenance", tags=["Provenance Graph"])

@router.get("/events")
def list_provenance_events(db: Session = Depends(get_db)):
    return db.query(models.ProvenanceEvent).all()

@router.get("/{id}")
def get_provenance_detail(id: str, db: Session = Depends(get_db)):
    ev = db.query(models.ProvenanceEvent).filter((models.ProvenanceEvent.id == id) | (models.ProvenanceEvent.decision_id == id)).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Provenance record not found")
    return ev
