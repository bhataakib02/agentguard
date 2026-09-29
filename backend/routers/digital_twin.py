from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from core.deps import get_current_user
import models, schemas
from engines.digital_twin_engine import digital_twin_engine

router = APIRouter(prefix="/digital-twin", tags=["Agent Digital Twin"])

@router.get("/simulations")
def list_simulations(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Simulation)
    if current_user.role != "SUPER_ADMIN":
        query = query.join(models.Agent).filter(models.Agent.org_id == current_user.org_id)
    return query.all()

@router.post("/run")
def run_simulation(
    req: schemas.DigitalTwinRunRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Agent).filter((models.Agent.id == req.agent_id) | (models.Agent.agent_code == req.agent_id))
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.Agent.org_id == current_user.org_id)
    agent = query.first()

    if not agent:
        raise HTTPException(status_code=404, detail="No authorized registered AI agent available to simulate.")

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
