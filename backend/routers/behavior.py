import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from core.deps import get_current_user
import models
import schemas
from engines.behavior_engine import behavior_engine

router = APIRouter(prefix="/behavior", tags=["Behavior Analytics"])

@router.get("/profiles")
def list_behavior_profiles(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.BehaviorProfile)
    if current_user.role != "SUPER_ADMIN":
        query = query.join(models.Agent).filter(models.Agent.org_id == current_user.org_id)
    profiles = query.all()

    res = []
    for p in profiles:
        agent = db.query(models.Agent).filter(models.Agent.id == p.agent_id).first()
        res.append({
            "agent_id": str(p.agent_id),
            "agent_code": agent.agent_code if agent else "AG-000",
            "name": agent.name if agent else "Agent",
            "avg_daily_actions": p.avg_daily_actions,
            "normal_operating_hours": p.normal_operating_hours,
            "allowed_tools": p.allowed_tools_json or [],
            "baseline_spending": p.baseline_spending
        })
    return res

@router.get("/profiles/{agent_id}", response_model=schemas.BehaviorProfileResponse)
def get_behavior_profile(
    agent_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Agent).filter((models.Agent.id == agent_id) | (models.Agent.agent_code == agent_id))
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.Agent.org_id == current_user.org_id)
    agent = query.first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    profile = behavior_engine.get_or_create_profile(agent, db)
    return {
        "agent_id": str(agent.id),
        "agent_code": agent.agent_code,
        "name": agent.name,
        "avg_daily_actions": profile.avg_daily_actions or 150,
        "normal_operating_hours": profile.normal_operating_hours or "09:00 - 18:00",
        "allowed_tools": profile.allowed_tools_json or [],
        "baseline_spending": profile.baseline_spending or 2500.0
    }

@router.put("/profiles/{agent_id}", response_model=schemas.BehaviorProfileResponse)
def update_behavior_profile(
    agent_id: str,
    req: schemas.BehaviorProfileUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Agent).filter((models.Agent.id == agent_id) | (models.Agent.agent_code == agent_id))
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.Agent.org_id == current_user.org_id)
    agent = query.first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    profile = behavior_engine.get_or_create_profile(agent, db)

    if req.avg_daily_actions is not None:
        profile.avg_daily_actions = req.avg_daily_actions
    if req.normal_operating_hours is not None:
        profile.normal_operating_hours = req.normal_operating_hours
    if req.allowed_tools is not None:
        profile.allowed_tools_json = req.allowed_tools
    if req.baseline_spending is not None:
        profile.baseline_spending = req.baseline_spending

    profile.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(profile)

    return {
        "agent_id": str(agent.id),
        "agent_code": agent.agent_code,
        "name": agent.name,
        "avg_daily_actions": profile.avg_daily_actions,
        "normal_operating_hours": profile.normal_operating_hours,
        "allowed_tools": profile.allowed_tools_json or [],
        "baseline_spending": profile.baseline_spending
    }

@router.post("/evaluate/{agent_id}", response_model=schemas.BehaviorEvaluationResponse)
def evaluate_agent_behavior(
    agent_id: str,
    tool_name: Optional[str] = None,
    requested_amount: float = 0.0,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Agent).filter((models.Agent.id == agent_id) | (models.Agent.agent_code == agent_id))
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.Agent.org_id == current_user.org_id)
    agent = query.first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    eval_res = behavior_engine.evaluate_behavior(
        agent=agent,
        db=db,
        tool_name=tool_name,
        requested_amount=requested_amount,
        persist_anomalies=True
    )
    return eval_res

@router.get("/deviations")
def list_behavioral_deviations(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.AnomalyEvent)
    if current_user.role != "SUPER_ADMIN":
        query = query.join(models.Agent).filter(models.Agent.org_id == current_user.org_id)
    return query.order_by(models.AnomalyEvent.timestamp.desc()).all()

@router.get("/deviations/{agent_id}")
def list_agent_deviations(
    agent_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Agent).filter((models.Agent.id == agent_id) | (models.Agent.agent_code == agent_id))
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.Agent.org_id == current_user.org_id)
    agent = query.first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    return db.query(models.AnomalyEvent).filter(
        models.AnomalyEvent.agent_id == agent.id
    ).order_by(models.AnomalyEvent.timestamp.desc()).all()
