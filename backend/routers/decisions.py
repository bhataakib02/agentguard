import datetime, uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from engines.intent_engine import intent_engine
from engines.risk_engine import risk_engine
from engines.policy_engine import policy_engine
from engines.provenance_engine import provenance_engine
from ws_manager import manager as ws_manager
from core.deps import get_current_user

router = APIRouter(prefix="/decisions", tags=["Decision Engine & Black Box"])

@router.get("", response_model=list[schemas.DecisionSchema])
def list_decisions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Decision)
    if current_user.role != "SUPER_ADMIN":
        query = query.join(models.Agent).filter(models.Agent.org_id == current_user.org_id)
    return query.order_by(models.Decision.timestamp.desc()).all()

@router.post("/evaluate", response_model=schemas.DecisionSchema)
async def evaluate_decision(
    req: schemas.ActionEvaluateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Fetch Agent (by ID or agent_code if provided, else use first agent in user's org)
    agent = None
    if req.agent_id:
        agent = db.query(models.Agent).filter(
            (models.Agent.id == req.agent_id) | (models.Agent.agent_code == req.agent_id)
        ).first()
        if not agent:
            raise HTTPException(
                status_code=404,
                detail="Specified AI agent not found."
            )
        if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Cannot evaluate actions for an AI agent belonging to another organization"
            )
    else:
        agent = db.query(models.Agent).filter(models.Agent.org_id == current_user.org_id).first()
        if not agent and current_user.role == "SUPER_ADMIN":
            agent = db.query(models.Agent).first()

    if not agent:
        raise HTTPException(
            status_code=404,
            detail="No registered AI agent available. Please create an AI agent in the directory first."
        )

    # 2. Intent Extraction
    intent_data = intent_engine.extract_intent(req.prompt)
    amount = req.amount if req.amount > 0 else intent_data["amount"]
    action = intent_data["action"]
    resource = intent_data["resource"]

    # 2b. Phase 4: Budget Pre-Check
    import time as _time
    _exec_start = _time.monotonic()
    try:
        from services.runtime_telemetry_service import check_budget_before_execution
        budget_check = check_budget_before_execution(db, str(agent.org_id), str(agent.id))
        if not budget_check["allowed"]:
            # Budget exceeded — refuse execution with clear policy decision
            decision = models.Decision(
                agent_id=agent.id,
                user_id=current_user.id,
                intent_summary=intent_data["intent"],
                action_requested=action,
                resource_target=resource,
                amount=amount,
                decision="REFUSE",
                risk_score=0,
                policy_name="Budget Governance Policy",
                explanation=budget_check["reason"],
                execution_status="BLOCKED"
            )
            db.add(decision)
            db.commit()
            db.refresh(decision)
            return decision
    except Exception as budget_err:
        import logging
        logging.getLogger("agentguard.decisions").warning(f"Budget check notice: {budget_err}")

    # 3. Calculate Risk Score
    risk_res = risk_engine.calculate_risk(
        agent_autonomy=agent.autonomy_level,
        action=action,
        amount=amount,
        daily_budget=agent.daily_budget
    )
    risk_score = risk_res["overall_score"]

    # 4. Policy Engine Evaluation (Real Database-Driven Evaluation)
    policy_res = policy_engine.evaluate_action(
        db=db,
        org_id=agent.org_id,
        agent_name=agent.name,
        action=action,
        resource=resource,
        amount=amount,
        risk_score=risk_score,
        agent_status=agent.status,
        agent_autonomy=agent.autonomy_level,
        agent_department=agent.department,
        agent_code=agent.agent_code,
        user_role=current_user.role,
        intent=intent_data["intent"]
    )
    decision_outcome = policy_res["decision"]
    final_risk_score = policy_res.get("risk_score", risk_score)

    # 5. Persist Decision Record
    decision = models.Decision(
        agent_id=agent.id,
        user_id=current_user.id,
        intent_summary=intent_data["intent"],
        action_requested=action,
        resource_target=resource,
        amount=amount,
        decision=decision_outcome,
        risk_score=final_risk_score,
        policy_name=policy_res["policy_applied"],
        explanation=policy_res["reason"],
        execution_status=policy_res["execution_status"]
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)

    # 5b. Phase 4: Record Runtime Telemetry
    try:
        from services.runtime_telemetry_service import record_execution, detect_risk_signals
        _latency = int((_time.monotonic() - _exec_start) * 1000)
        record_execution(
            db=db,
            org_id=str(agent.org_id),
            agent_id=str(agent.id),
            action=action,
            resource=resource,
            outcome=policy_res["execution_status"],
            risk_score=final_risk_score,
            policy_decision=decision_outcome,
            policy_id=policy_res.get("policy_id"),
            policy_rule_id=policy_res.get("rule_id"),
            decision_id=str(decision.id),
            provider=agent.model_name.split("-")[0] if agent.model_name and "-" in agent.model_name else (agent.model_name or "unknown"),
            model_name=agent.model_name,
            latency_ms=_latency,
            status="COMPLETED",
            metadata={"amount": amount, "user_role": current_user.role}
        )
        # Async risk signal detection (non-blocking)
        try:
            detect_risk_signals(db, str(agent.org_id), str(agent.id))
        except Exception:
            pass
    except Exception as telem_err:
        import logging
        logging.getLogger("agentguard.decisions").warning(f"Telemetry recording notice: {telem_err}")

    # 6. Create Approval Request if REVIEW required
    app_req = None
    if decision_outcome == "REVIEW":
        app_req = models.ApprovalRequest(
            decision_id=decision.id,
            agent_id=agent.id,
            approver_id=current_user.id,
            amount=amount,
            reason=f"Governance Escalation: Amount ₹{amount:,.2f} requires managerial approval ({policy_res['policy_applied']}).",
            status="PENDING"
        )
        db.add(app_req)
        db.commit()
        db.refresh(app_req)

    # 6b. Dispatch Real Governance Notifications & Webhooks
    try:
        from services.notification_service import notification_service
        if decision_outcome == "REVIEW" and app_req:
            notification_service.notify_governance_event(
                db=db,
                org_id=str(agent.org_id),
                event_type="approval.created",
                resource_type="approval",
                resource_id=str(app_req.id),
                title="Approval Required",
                message=f"Action '{action}' by agent {agent.name} requires human review (₹{amount:,.2f}).",
                data={"decision_id": str(decision.id), "agent_code": agent.agent_code, "action": action, "amount": amount, "risk_score": final_risk_score},
                user_id=str(current_user.id),
                severity="WARNING"
            )
        elif decision_outcome == "REFUSE":
            notification_service.notify_governance_event(
                db=db,
                org_id=str(agent.org_id),
                event_type="decision.refused",
                resource_type="decision",
                resource_id=str(decision.id),
                title="Action Refused by Governance Policy",
                message=f"Action '{action}' blocked by policy '{policy_res['policy_applied']}': {policy_res['reason']}",
                data={"decision_id": str(decision.id), "agent_code": agent.agent_code, "action": action, "policy": policy_res["policy_applied"], "reason": policy_res["reason"]},
                user_id=str(current_user.id),
                severity="CRITICAL"
            )
        elif final_risk_score > 60:
            notification_service.notify_governance_event(
                db=db,
                org_id=str(agent.org_id),
                event_type="decision.high_risk",
                resource_type="decision",
                resource_id=str(decision.id),
                title="High-Risk Action Flagged",
                message=f"Action '{action}' on {resource} evaluated with risk score {final_risk_score}/100.",
                data={"decision_id": str(decision.id), "agent_code": agent.agent_code, "action": action, "risk_score": final_risk_score},
                user_id=str(current_user.id),
                severity="HIGH"
            )
    except Exception as notify_err:
        import logging
        logging.getLogger("agentguard.decisions").warning(f"Notification dispatch notice: {notify_err}")

    # 7. Record Provenance & Audit Log
    provenance = models.ProvenanceEvent(
        decision_id=decision.id,
        human_initiator_id=current_user.id,
        agent_id=agent.id,
        tool_used=resource,
        data_accessed=f"Target: {intent_data['customer_id'] or 'Database Resource'}",
        causal_chain_json=provenance_engine.build_causal_tree(
            decision_id=decision.id,
            human_initiator_id=current_user.id,
            human_initiator_name=current_user.full_name,
            agent_code=agent.agent_code,
            agent_name=agent.name,
            action_requested=action,
            tool_used=resource,
            amount=amount,
            decision_outcome=decision_outcome,
            policy_name=policy_res.get("policy_applied"),
            policy_id=policy_res.get("policy_id"),
            rule_id=policy_res.get("rule_id"),
            matched_rules=policy_res.get("matched_rules")
        )
    )
    audit = models.AuditLog(
        event_type="GOVERNANCE_DECISION",
        actor_type="AGENT",
        actor_id=agent.agent_code,
        action=action,
        resource=resource,
        result=decision_outcome,
        metadata_json={
            "amount": amount,
            "risk_score": final_risk_score,
            "policy": policy_res["policy_applied"],
            "policy_id": policy_res.get("policy_id"),
            "rule_id": policy_res.get("rule_id"),
            "matched_rules_count": len(policy_res.get("matched_rules", []))
        }
    )
    db.add_all([provenance, audit])
    db.commit()

    # 8. Broadcast Real-Time WebSocket Event
    await ws_manager.broadcast({
        "type": "GOVERNANCE_DECISION",
        "decision_id": decision.id,
        "agent_code": agent.agent_code,
        "action": action,
        "amount": amount,
        "decision": decision_outcome,
        "risk_score": risk_score,
        "explanation": policy_res["reason"],
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

    return decision

@router.get("/{id}")
def get_decision_detail(
    id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    dec = db.query(models.Decision).filter(models.Decision.id == id).first()
    if not dec:
        raise HTTPException(status_code=404, detail="Decision record not found")
    
    agent = db.query(models.Agent).filter(models.Agent.id == dec.agent_id).first()
    if agent and current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(status_code=403, detail="Forbidden: Decision record belongs to another organization")
    
    prov = db.query(models.ProvenanceEvent).filter(models.ProvenanceEvent.decision_id == dec.id).first()
    app_req = db.query(models.ApprovalRequest).filter(models.ApprovalRequest.decision_id == dec.id).first()

    return {
        "decision": dec,
        "provenance": prov.causal_chain_json if prov else None,
        "approval_request": app_req
    }
