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
def list_decisions(db: Session = Depends(get_db)):
    return db.query(models.Decision).order_by(models.Decision.timestamp.desc()).all()

@router.post("/evaluate", response_model=schemas.DecisionSchema)
async def evaluate_decision(
    req: schemas.ActionEvaluateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Fetch Agent (by ID or agent_code if provided, else use first agent in user's org)
    agent = None
    if req.agent_id:
        agent = db.query(models.Agent).filter((models.Agent.id == req.agent_id) | (models.Agent.agent_code == req.agent_id)).first()
    
    if not agent:
        agent = db.query(models.Agent).filter(models.Agent.org_id == current_user.org_id).first()

    if not agent:
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

    # 3. Calculate Risk Score
    risk_res = risk_engine.calculate_risk(
        agent_autonomy=agent.autonomy_level,
        action=action,
        amount=amount,
        daily_budget=agent.daily_budget
    )
    risk_score = risk_res["overall_score"]

    # 4. Policy Engine Evaluation
    policy_res = policy_engine.evaluate_action(
        agent_name=agent.name,
        action=action,
        resource=resource,
        amount=amount,
        risk_score=risk_score,
        agent_status=agent.status
    )
    decision_outcome = policy_res["decision"]

    # 5. Persist Decision Record
    decision = models.Decision(
        agent_id=agent.id,
        user_id=current_user.id,
        intent_summary=intent_data["intent"],
        action_requested=action,
        resource_target=resource,
        amount=amount,
        decision=decision_outcome,
        risk_score=risk_score,
        policy_name=policy_res["policy_applied"],
        explanation=policy_res["reason"],
        execution_status=policy_res["execution_status"]
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)

    # 6. Create Approval Request if REVIEW required
    if decision_outcome == "REVIEW":
        app_req = models.ApprovalRequest(
            decision_id=decision.id,
            agent_id=agent.id,
            approver_id=current_user.id,
            amount=amount,
            reason=f"Governance Escalation: Amount ₹{amount:,.2f} requires managerial approval.",
            status="PENDING"
        )
        db.add(app_req)

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
            decision_outcome=decision_outcome
        )
    )
    audit = models.AuditLog(
        event_type="GOVERNANCE_DECISION",
        actor_type="AGENT",
        actor_id=agent.agent_code,
        action=action,
        resource=resource,
        result=decision_outcome,
        metadata_json={"amount": amount, "risk_score": risk_score, "policy": policy_res["policy_applied"]}
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
def get_decision_detail(id: str, db: Session = Depends(get_db)):
    dec = db.query(models.Decision).filter(models.Decision.id == id).first()
    if not dec:
        raise HTTPException(status_code=404, detail="Decision record not found")
    
    prov = db.query(models.ProvenanceEvent).filter(models.ProvenanceEvent.decision_id == dec.id).first()
    app_req = db.query(models.ApprovalRequest).filter(models.ApprovalRequest.decision_id == dec.id).first()

    return {
        "decision": dec,
        "provenance": prov.causal_chain_json if prov else None,
        "approval_request": app_req
    }
