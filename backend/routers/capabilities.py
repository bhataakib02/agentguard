from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from engines.capability_engine import capability_engine
from ws_manager import manager as ws_manager
from core.deps import get_current_user
import datetime

router = APIRouter(prefix="/capabilities", tags=["Dynamic Capabilities"])

@router.get("", response_model=list[schemas.CapabilityTokenSchema])
def list_capability_tokens(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.CapabilityToken)
    if current_user.role != "SUPER_ADMIN":
        query = query.join(models.Agent).filter(models.Agent.org_id == current_user.org_id)
    return query.all()

@router.post("/issue", response_model=schemas.CapabilityTokenSchema)
async def issue_capability_token(
    req: schemas.CapabilityTokenRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Agent).filter((models.Agent.id == req.agent_id) | (models.Agent.agent_code == req.agent_id))
    if current_user.role != "SUPER_ADMIN":
        query = query.filter(models.Agent.org_id == current_user.org_id)
    agent = query.first()

    if not agent:
        raise HTTPException(status_code=404, detail="No authorized registered agent found to issue capability token")

    tok_dict = capability_engine.issue_token(
        agent_id=agent.id,
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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    token = db.query(models.CapabilityToken).filter(models.CapabilityToken.token_code == token_code).first()
    if not token:
        raise HTTPException(status_code=404, detail="Capability token not found")

    agent = db.query(models.Agent).filter(models.Agent.id == token.agent_id).first()
    if agent and current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Token belongs to another organization")

    token.status = "REVOKED"
    db.commit()

    return {"status": "SUCCESS", "message": f"Capability token {token_code} has been revoked."}
