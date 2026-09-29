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
    from services.notification_service import notify_governance_event
    now = datetime.datetime.utcnow()
    sla_limit = now - datetime.timedelta(hours=24)
    approaching_sla_limit = now - datetime.timedelta(hours=18)

    query = db.query(models.ApprovalRequest).filter(models.ApprovalRequest.status == "PENDING")
    if current_user.role != "SUPER_ADMIN":
        query = query.join(models.Agent).filter(models.Agent.org_id == current_user.org_id)

    pending_list = query.all()
    escalated_count = 0
    approaching_count = 0

    for app in pending_list:
        agent = db.query(models.Agent).filter(models.Agent.id == app.agent_id).first()
        org_id = str(agent.org_id) if agent else str(current_user.org_id)
        created_dt = app.created_at
        if created_dt and created_dt.tzinfo is not None:
            created_dt = created_dt.replace(tzinfo=None)

        if created_dt and created_dt <= sla_limit:
            notify_governance_event(
                db=db,
                org_id=org_id,
                event_type="approval.overdue",
                resource_type="approval_request",
                resource_id=str(app.id),
                data={
                    "approval_id": str(app.id),
                    "agent_id": str(app.agent_id),
                    "agent_name": agent.name if agent else "Agent",
                    "reason": app.reason,
                    "amount": app.amount,
                    "created_at": app.created_at.isoformat() if app.created_at else None,
                    "sla_status": "OVERDUE"
                },
                notification_title=f"Approval Overdue: {agent.name if agent else 'Agent'}",
                notification_message=f"Approval request {str(app.id)[:8]} has exceeded the 24-hour SLA window.",
                severity="WARNING"
            )
            escalated_count += 1
        elif created_dt and created_dt <= approaching_sla_limit:
            notify_governance_event(
                db=db,
                org_id=org_id,
                event_type="approval.approaching_sla",
                resource_type="approval_request",
                resource_id=str(app.id),
                data={
                    "approval_id": str(app.id),
                    "agent_id": str(app.agent_id),
                    "agent_name": agent.name if agent else "Agent",
                    "reason": app.reason,
                    "amount": app.amount,
                    "created_at": app.created_at.isoformat() if app.created_at else None,
                    "sla_status": "APPROACHING_SLA"
                },
                notification_title=f"Approval Approaching SLA: {agent.name if agent else 'Agent'}",
                notification_message=f"Approval request {str(app.id)[:8]} is within 6 hours of SLA breach.",
                severity="INFO"
            )
            approaching_count += 1

    return {
        "status": "SUCCESS",
        "overdue_escalated": escalated_count,
        "approaching_sla": approaching_count,
        "total_pending_checked": len(pending_list)
    }

