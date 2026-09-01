import random, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from ws_manager import manager as ws_manager
from core.deps import get_current_user, check_license_limit

router = APIRouter(prefix="/agents", tags=["Agent Management"])

@router.get("", response_model=list[schemas.AgentSchema])
def list_agents(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == "SUPER_ADMIN":
        return db.query(models.Agent).all()
    return db.query(models.Agent).filter(models.Agent.org_id == current_user.org_id).all()

@router.post("", response_model=schemas.AgentSchema)
async def create_agent(req: schemas.AgentCreateRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 1. Reject attempts to create agents under another organization
    if req.org_id and current_user.role != "SUPER_ADMIN" and str(req.org_id) != str(current_user.org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot create an AI agent under another organization"
        )

    # 2. Enforce License Limit for Agents
    check_license_limit(str(current_user.org_id), "agents", db)

    org_id = current_user.org_id
    owner_id = current_user.id

    # Handle requested owner_id within the same organization
    if req.owner_id:
        target_owner = db.query(models.User).filter(models.User.id == req.owner_id).first()
        if target_owner and (current_user.role == "SUPER_ADMIN" or target_owner.org_id == current_user.org_id):
            owner_id = target_owner.id

    code_num = db.query(models.Agent).count() + 101
    agent_code = f"AG-{code_num}"

    agent = models.Agent(
        agent_code=agent_code,
        org_id=org_id,
        owner_id=owner_id,
        name=req.name,
        department=req.department or "Operations",
        purpose=req.purpose or "Autonomous AI Agent Workflow",
        model_name=req.model_name,
        model_version=req.model_version,
        environment=req.environment,
        autonomy_level=req.autonomy_level,
        status="NORMAL",
        risk_score=15,
        trust_score=95,
        daily_budget=req.daily_budget
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)

    # Create Passport
    passport = models.AgentPassport(
        agent_id=agent.id,
        passport_number=f"AG-PASSPORT-{random.randint(100000, 999999)}",
        digital_signature=f"sha256:{random.getrandbits(256):064x}",
        issued_at=datetime.datetime.utcnow(),
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=365),
        verification_status="VERIFIED"
    )
    db.add(passport)

    # Create Behavior Profile, Reputation, Circuit Breaker & Budget
    profile = models.BehaviorProfile(agent_id=agent.id, avg_daily_actions=200, baseline_spending=req.daily_budget * 0.25)
    reputation = models.ReputationScore(agent_id=agent.id, trust_score=95, successful_tasks=0)
    cb = models.CircuitBreaker(agent_id=agent.id, state="NORMAL")
    budget = models.Budget(agent_id=agent.id, daily_limit=req.daily_budget, monthly_limit=req.daily_budget * 30)

    db.add_all([profile, reputation, cb, budget])
    db.commit()
    db.refresh(agent)

    await ws_manager.broadcast({
        "type": "AGENT_CREATED",
        "agent_code": agent.agent_code,
        "name": agent.name,
        "department": agent.department,
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

    return agent

@router.get("/{id}", response_model=schemas.AgentSchema)
def get_agent(
    id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    agent = db.query(models.Agent).filter((models.Agent.id == id) | (models.Agent.agent_code == id)).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot view AI agent belonging to another organization"
        )

    return agent

@router.get("/{id}/passport")
def get_agent_passport(
    id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    agent = db.query(models.Agent).filter((models.Agent.id == id) | (models.Agent.agent_code == id)).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot view Agent Passport belonging to another organization"
        )

    passport = db.query(models.AgentPassport).filter(models.AgentPassport.agent_id == agent.id).first()
    owner = db.query(models.User).filter(models.User.id == agent.owner_id).first()
    permissions = db.query(models.Permission).filter(models.Permission.agent_id == agent.id).all()
    credentials = db.query(models.AgentCredential).filter(models.AgentCredential.agent_id == agent.id).all()

    return {
        "agent": agent,
        "passport": passport,
        "owner_name": owner.full_name if owner else "System Owner",
        "organization_name": agent.organization.name if agent.organization else "AgentGuard Org",
        "permissions_count": len(permissions),
        "credentials": [c.credential_type for c in credentials]
    }

@router.post("/{id}/suspend")
async def suspend_agent(
    id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    agent = db.query(models.Agent).filter((models.Agent.id == id) | (models.Agent.agent_code == id)).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot suspend AI agent belonging to another organization"
        )

    agent.status = "SUSPENDED"
    cb = db.query(models.CircuitBreaker).filter(models.CircuitBreaker.agent_id == agent.id).first()
    if cb:
        cb.state = "SUSPENDED"
        cb.trigger_reason = "MANUAL_SUSPENSION_KILL_SWITCH"
        cb.tripped_at = datetime.datetime.utcnow()

    db.query(models.CapabilityToken).filter(models.CapabilityToken.agent_id == agent.id).update({"status": "REVOKED"})
    db.commit()

    await ws_manager.broadcast({
        "type": "AGENT_SUSPENDED",
        "agent_code": agent.agent_code,
        "name": agent.name,
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

    return {"status": "SUCCESS", "message": f"Agent {agent.agent_code} has been suspended and all active capabilities revoked."}

@router.post("/{id}/restore")
async def restore_agent(
    id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    agent = db.query(models.Agent).filter((models.Agent.id == id) | (models.Agent.agent_code == id)).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot restore AI agent belonging to another organization"
        )

    agent.status = "NORMAL"
    cb = db.query(models.CircuitBreaker).filter(models.CircuitBreaker.agent_id == agent.id).first()
    if cb:
        cb.state = "NORMAL"
        cb.restored_at = datetime.datetime.utcnow()
    db.commit()

    await ws_manager.broadcast({
        "type": "AGENT_RESTORED",
        "agent_code": agent.agent_code,
        "name": agent.name,
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

    return {"status": "SUCCESS", "message": f"Agent {agent.agent_code} restored to NORMAL operational state."}
