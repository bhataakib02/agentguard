from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from core.deps import get_current_user
import models, schemas
from engines.red_team_engine import red_team_engine

router = APIRouter(prefix="/red-team", tags=["AgentGuard Red-Team Lab"])

@router.get("/tests")
def list_security_tests(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.SecurityTest)
    if current_user.role != "SUPER_ADMIN":
        query = query.join(models.Agent).filter(models.Agent.org_id == current_user.org_id)
    return query.all()

@router.post("/run")
def run_security_test(
    req: schemas.RedTeamRunRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Agent).filter((models.Agent.id == req.agent_id) | (models.Agent.agent_code == req.agent_id))
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.Agent.org_id == current_user.org_id)
    agent = query.first()

    if not agent:
        raise HTTPException(status_code=404, detail="No authorized registered AI agent available to test.")

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
