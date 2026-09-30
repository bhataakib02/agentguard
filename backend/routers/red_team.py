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
    return query.order_by(models.SecurityTest.timestamp.desc()).all()

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No authorized registered AI agent available to test."
        )

    res = red_team_engine.execute_test(agent=agent, attack_type=req.attack_type, db=db)

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

    # Tenant-isolated Audit Log
    audit = models.AuditLog(
        org_id=str(agent.org_id),
        event_type="RED_TEAM_TEST_EXECUTED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action=f"Executed {res['test_category']} ({res['test_type']}) on agent {agent.agent_code}",
        resource=f"agent:{agent.id}",
        result=res["defense_result"],
        metadata_json={
            "test_id": str(test_rec.id),
            "test_category": res["test_category"],
            "expected_outcome": res["expected_outcome"],
            "actual_outcome": res["actual_outcome"],
            "security_score": res["security_score"],
            "policy_applied": res["policy_applied"]
        }
    )
    db.add(audit)
    db.commit()

    return {
        "test": {
            "id": str(test_rec.id),
            "agent_id": str(test_rec.agent_id),
            "test_type": test_rec.test_type,
            "attack_payload": test_rec.attack_payload,
            "defense_result": test_rec.defense_result,
            "security_score": test_rec.security_score,
            "timestamp": test_rec.timestamp.isoformat() if test_rec.timestamp else None
        },
        "test_category": res["test_category"],
        "expected_outcome": res["expected_outcome"],
        "actual_outcome": res["actual_outcome"],
        "defense_result": res["defense_result"],
        "security_score": res["security_score"],
        "policy_applied": res["policy_applied"],
        "mitigation_detail": res["mitigation_detail"],
        "recommendation": res["recommendation"]
    }
