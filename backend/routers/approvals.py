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

    # Action validation
    if req.action not in ["APPROVE", "REJECT"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action '{req.action}'. Action must be 'APPROVE' or 'REJECT'."
        )

    app_req = db.query(models.ApprovalRequest).filter(models.ApprovalRequest.id == id).first()
    if not app_req:
        raise HTTPException(status_code=404, detail="Approval request not found")

    # Org isolation check
    agent = db.query(models.Agent).filter(models.Agent.id == app_req.agent_id).first()
    if agent and current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Approval belongs to another organization")

    # State transition integrity: Only PENDING requests may be resolved
    if app_req.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot resolve approval request in '{app_req.status}' state. Only 'PENDING' requests may be resolved."
        )

    # Expiry verification (24-hour SLA window)
    now = datetime.datetime.utcnow()
    created_dt = app_req.created_at
    if created_dt and created_dt.tzinfo is not None:
        created_dt = created_dt.replace(tzinfo=None)
    if created_dt and created_dt <= (now - datetime.timedelta(hours=24)):
        app_req.status = "EXPIRED"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Approval request has expired and cannot be resolved."
        )

    new_status = "APPROVED" if req.action == "APPROVE" else "REJECTED"

    # Atomic State Transition under Concurrency
    update_data = {
        "status": new_status,
        "resolved_at": now,
        "approver_id": current_user.id
    }
    updated_rows = db.query(models.ApprovalRequest).filter(
        models.ApprovalRequest.id == id,
        models.ApprovalRequest.status == "PENDING"
    ).update(update_data, synchronize_session=False)
    db.commit()

    if updated_rows == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Approval request is no longer PENDING (concurrent resolution conflict)."
        )

    # Reload record
    app_req = db.query(models.ApprovalRequest).filter(models.ApprovalRequest.id == id).first()

    dec = db.query(models.Decision).filter(models.Decision.id == app_req.decision_id).first()
    if dec:
        if new_status == "APPROVED":
            dec.decision = "ALLOW"
            # Truthful provenance: action is approved pending tool proxy execution
            dec.execution_status = "APPROVED_PENDING_EXECUTION"
            if not dec.execution_gate_token:
                import uuid
                dec.execution_gate_token = f"gate_{uuid.uuid4().hex[:16]}"
                dec.gate_token_used = False
        else:
            dec.decision = "REFUSE"
            dec.execution_status = "BLOCKED"
            dec.gate_token_used = True

    # Immutable Audit Log for Approval Resolution
    if agent:
        audit = models.AuditLog(
            org_id=agent.org_id,
            event_type=f"APPROVAL_{new_status}",
            actor_type="USER",
            actor_id=str(current_user.id),
            action="RESOLVE_APPROVAL",
            resource=f"approval:{id}",
            result="SUCCESS" if new_status == "APPROVED" else "DENIED",
            metadata_json={
                "approval_id": id,
                "decision_id": str(app_req.decision_id),
                "resolution": new_status,
                "resolver_email": current_user.email
            }
        )
        db.add(audit)

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


