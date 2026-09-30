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
    return query.order_by(models.Simulation.timestamp.desc()).all()

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No authorized registered AI agent available to simulate."
        )

    res = digital_twin_engine.run_simulation(agent=agent, scenario_type=req.scenario_type, db=db)

    sim = models.Simulation(
        agent_id=agent.id,
        scenario_type=res["scenario_type"],
        readiness_score=res["readiness_score"],
        metrics_json={
            "classification": res["classification"],
            "disclaimer": res["disclaimer"],
            "metrics": res["metrics"],
            "inputs_real": res["inputs_real"],
            "transformations_simulated": res["transformations_simulated"],
            "deployment_recommendation": res["deployment_recommendation"]
        }
    )
    db.add(sim)
    db.commit()
    db.refresh(sim)

    # Tenant-isolated Audit Log
    audit = models.AuditLog(
        org_id=str(agent.org_id),
        event_type="DIGITAL_TWIN_SIMULATION_EXECUTED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action=f"Executed deterministic digital twin simulation for agent {agent.agent_code} ({res['scenario_type']})",
        resource=f"agent:{agent.id}",
        result="SUCCESS",
        metadata_json={
            "simulation_id": str(sim.id),
            "scenario_type": res["scenario_type"],
            "classification": "SIMULATED",
            "readiness_score": res["readiness_score"]
        }
    )
    db.add(audit)
    db.commit()

    return res
