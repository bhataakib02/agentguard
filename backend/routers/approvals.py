import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from ws_manager import manager as ws_manager
from core.deps import get_current_user

router = APIRouter(prefix="/approvals", tags=["Human Approvals"])

@router.get("")
def list_approvals(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.ApprovalRequest)
    if current_user.role != "SUPER_ADMIN":
        query = query.join(models.Agent).filter(models.Agent.org_id == current_user.org_id)
    reqs = query.all()

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
async def act_on_approval(
    id: str,
    req: schemas.ApprovalActionRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Role-based authorization: Only MANAGER, ADMIN, or SUPER_ADMIN may act on approvals
    if current_user.role not in ["MANAGER", "ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only Managers, Admins, or Super Admins can resolve approval requests"
        )

    app_req = db.query(models.ApprovalRequest).filter(models.ApprovalRequest.id == id).first()
    if not app_req:
        raise HTTPException(status_code=404, detail="Approval request not found")

    # Org isolation check
    agent = db.query(models.Agent).filter(models.Agent.id == app_req.agent_id).first()
    if agent and current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Approval belongs to another organization")

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


@router.post("/escalate")
def escalate_overdue_approvals(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from tasks.escalation_tasks import escalate_approvals_task
    org_filter = None if current_user.role == "SUPER_ADMIN" else str(current_user.org_id)
    return escalate_approvals_task(org_id_filter=org_filter)


