from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from engines.capability_engine import capability_engine
from ws_manager import manager as ws_manager
from core.deps import get_current_user, require_role
import datetime

router = APIRouter(prefix="/capabilities", tags=["Dynamic Capabilities"])

CAPABILITY_ADMIN_ROLES = ["ADMIN", "MANAGER", "SECURITY_OFFICER"]

@router.get("", response_model=list[schemas.CapabilityTokenSchema])
def list_capability_tokens(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.CapabilityToken)
    if str(current_user.role) != "SUPER_ADMIN":
        query = query.join(models.Agent).filter(models.Agent.org_id == current_user.org_id)
    return query.all()

@router.post("/issue", response_model=schemas.CapabilityTokenSchema)
async def issue_capability_token(
    req: schemas.CapabilityTokenRequest,
    current_user: models.User = Depends(require_role(CAPABILITY_ADMIN_ROLES)),
    db: Session = Depends(get_db)
):
    query = db.query(models.Agent).filter((models.Agent.id == req.agent_id) | (models.Agent.agent_code == req.agent_id))
    if str(current_user.role) != "SUPER_ADMIN":
        query = query.filter(models.Agent.org_id == current_user.org_id)
    agent = query.first()

    if not agent:
        raise HTTPException(status_code=404, detail="No authorized registered agent found to issue capability token")

    if agent.status in ("SUSPENDED", "CIRCUIT_BREAK"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot issue capability token: Agent is currently in '{agent.status}' status"
        )

    if req.amount_limit < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Capability amount limit cannot be negative")

    agent_daily_budget = getattr(agent, "daily_budget", None)
    if agent_daily_budget and req.amount_limit > float(agent_daily_budget) and str(current_user.role) not in ("ADMIN", "SUPER_ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requested capability amount limit ({req.amount_limit}) exceeds agent daily budget ({agent.daily_budget})"
        )

    tok_dict = capability_engine.issue_token(
        agent_id=str(agent.id),
        capability_name=req.capability_name,
        scope=req.scope,
        amount_limit=req.amount_limit,
        ttl_seconds=req.ttl_seconds
    )

    db_token = models.CapabilityToken(
        token_code=tok_dict["token_code"],
        agent_id=agent.id,
        capability_name=tok_dict["capability_name"],
        scope=tok_dict["scope"],
        amount_limit=tok_dict["amount_limit"],
        issued_at=tok_dict["issued_at"],
        expires_at=tok_dict["expires_at"],
        status="ACTIVE"
    )
    db.add(db_token)

    audit = models.AuditLog(
        org_id=agent.org_id,
        event_type="CAPABILITY_TOKEN_ISSUED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="ISSUE_CAPABILITY",
        resource=f"agent:{agent.agent_code}",
        result="SUCCESS",
        metadata_json={
            "token_code": db_token.token_code,
            "capability_name": db_token.capability_name,
            "scope": db_token.scope,
            "amount_limit": db_token.amount_limit,
            "issuer_email": current_user.email
        }
    )
    db.add(audit)
    db.commit()
    db.refresh(db_token)

    await ws_manager.broadcast({
        "type": "CAPABILITY_ISSUED",
        "agent_code": agent.agent_code,
        "token_code": db_token.token_code,
        "capability": db_token.capability_name,
        "scope": db_token.scope,
        "expires_at": db_token.expires_at.isoformat()
    })

    return db_token

@router.post("/revoke/{token_code}")
async def revoke_capability_token(
    token_code: str,
    current_user: models.User = Depends(require_role(CAPABILITY_ADMIN_ROLES)),
    db: Session = Depends(get_db)
):
    token = db.query(models.CapabilityToken).filter(models.CapabilityToken.token_code == token_code).first()
    if not token:
        raise HTTPException(status_code=404, detail="Capability token not found")

    agent = db.query(models.Agent).filter(models.Agent.id == token.agent_id).first()
    if agent and str(current_user.role) != "SUPER_ADMIN" and str(agent.org_id) != str(current_user.org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Token belongs to another organization")

    setattr(token, "status", "REVOKED")

    audit = models.AuditLog(
        org_id=agent.org_id if agent else current_user.org_id,
        event_type="CAPABILITY_TOKEN_REVOKED",
        actor_type="USER",
        actor_id=str(current_user.id),
        action="REVOKE_CAPABILITY",
        resource=f"capability_token:{token_code}",
        result="SUCCESS",
        metadata_json={
            "token_code": token_code,
            "revoker_email": current_user.email
        }
    )
    db.add(audit)
    db.commit()

    return {"status": "SUCCESS", "message": f"Capability token {token_code} has been revoked."}


@router.post("/validate")
def validate_capability_token_endpoint(
    req: schemas.CapabilityTokenValidateRequest,
    db: Session = Depends(get_db)
):
    """
    Validates a capability token against agent, capability scope, expiration, and amount limits.
    """
    agent = None
    if req.agent_id:
        agent = db.query(models.Agent).filter(
            (models.Agent.id == req.agent_id) | (models.Agent.agent_code == req.agent_id)
        ).first()

    validation = capability_engine.validate_token(
        db=db,
        token_code=req.token_code,
        agent=agent,
        required_capability=req.capability_name,
        requested_amount=req.amount or 0.0,
        requested_scope=req.scope
    )

    token_rec = validation.get("token")
    return {
        "valid": validation["valid"],
        "reason": validation["reason"],
        "token_code": req.token_code,
        "capability_name": token_rec.capability_name if token_rec else None,
        "scope": token_rec.scope if token_rec else None,
        "amount_limit": token_rec.amount_limit if token_rec else None,
        "expires_at": token_rec.expires_at.isoformat() if token_rec and token_rec.expires_at else None,
        "status": token_rec.status if token_rec else "NOT_FOUND"
    }

