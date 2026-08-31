from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from engines.digital_twin_engine import digital_twin_engine

router = APIRouter(prefix="/digital-twin", tags=["Agent Digital Twin"])

@router.get("/simulations")
def list_simulations(db: Session = Depends(get_db)):
    return db.query(models.Simulation).all()

@router.post("/run")
def run_simulation(req: schemas.DigitalTwinRunRequest, db: Session = Depends(get_db)):
    agent = db.query(models.Agent).filter((models.Agent.id == req.agent_id) | (models.Agent.agent_code == req.agent_id)).first()
    if not agent:
        agent = db.query(models.Agent).first()

    if not agent:
        raise HTTPException(status_code=404, detail="No registered AI agent available to simulate.")

    res = digital_twin_engine.run_simulation(agent_id=agent.id, scenario_type=req.scenario_type)

    sim = models.Simulation(
        agent_id=agent.id,
        scenario_type=res["scenario_type"],
        readiness_score=res["readiness_score"],
        metrics_json=res["metrics"]
    )
    db.add(sim)
    db.commit()

    return res
