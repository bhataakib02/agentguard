from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from engines.red_team_engine import red_team_engine

router = APIRouter(prefix="/red-team", tags=["AgentGuard Red-Team Lab"])

@router.get("/tests")
def list_security_tests(db: Session = Depends(get_db)):
    return db.query(models.SecurityTest).all()

@router.post("/run")
def run_security_test(req: schemas.RedTeamRunRequest, db: Session = Depends(get_db)):
    agent = db.query(models.Agent).filter((models.Agent.id == req.agent_id) | (models.Agent.agent_code == req.agent_id)).first()
    if not agent:
        agent = db.query(models.Agent).first()

    if not agent:
        raise HTTPException(status_code=404, detail="No registered AI agent available to test.")

    res = red_team_engine.execute_test(agent_id=agent.id, attack_type=req.attack_type)

    test_rec = models.SecurityTest(
        agent_id=agent.id,
        test_type=res["test_type"],
        attack_payload=res["attack_payload"],
        defense_result=res["defense_result"],
        security_score=res["security_score"]
    )
    db.add(test_rec)
    db.commit()
    db.refresh(test_rec)

    return {
        "test": test_rec,
        "mitigation_detail": res["mitigation_detail"],
        "recommendation": res["recommendation"]
    }
