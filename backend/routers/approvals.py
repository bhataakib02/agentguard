import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from ws_manager import manager as ws_manager

router = APIRouter(prefix="/approvals", tags=["Human Approvals"])

@router.get("")
def list_approvals(db: Session = Depends(get_db)):
    reqs = db.query(models.ApprovalRequest).all()
    res = []
    for r in reqs:
        agent = db.query(models.Agent).filter(models.Agent.id == r.agent_id).first()
        decision = db.query(models.Decision).filter(models.Decision.id == r.decision_id).first()
        res.append({
            "id": r.id,
            "decision_id": r.decision_id,
            "agent_code": agent.agent_code if agent else "AG-000",
            "agent_name": agent.name if agent else "Agent",
            "action": decision.action_requested if decision else "UNKNOWN",
            "amount": r.amount,
            "reason": r.reason,
            "status": r.status,
            "created_at": r.created_at
        })
    return res

@router.post("/{id}/act")
async def act_on_approval(id: str, req: schemas.ApprovalActionRequest, db: Session = Depends(get_db)):
    app_req = db.query(models.ApprovalRequest).filter(models.ApprovalRequest.id == id).first()
    if not app_req:
        raise HTTPException(status_code=404, detail="Approval request not found")

    new_status = "APPROVED" if req.action == "APPROVE" else "REJECTED"
    app_req.status = new_status
    app_req.resolved_at = datetime.datetime.utcnow()

    dec = db.query(models.Decision).filter(models.Decision.id == app_req.decision_id).first()
    if dec:
        dec.execution_status = "EXECUTED" if new_status == "APPROVED" else "BLOCKED"

    db.commit()

    await ws_manager.broadcast({
        "type": "APPROVAL_RESOLVED",
        "approval_id": app_req.id,
        "action": req.action,
        "status": new_status,
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

    return {"status": "SUCCESS", "approval_id": id, "new_status": new_status}
