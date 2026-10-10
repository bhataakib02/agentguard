from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from core.deps import get_current_user
import models

router = APIRouter(prefix="/runtime", tags=["Circuit Breaker & Runtime Safety"])

@router.get("/circuit-breakers")
def get_circuit_breakers(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.CircuitBreaker)
    if current_user.role != "SUPER_ADMIN":
        query = query.join(models.Agent).filter(models.Agent.org_id == current_user.org_id)
    cbs = query.all()

    res = []
    for cb in cbs:
        agent = db.query(models.Agent).filter(models.Agent.id == cb.agent_id).first()
        res.append({
            "agent_id": cb.agent_id,
            "agent_code": agent.agent_code if agent else "AG-000",
            "name": agent.name if agent else "Agent",
            "state": cb.state,
            "trigger_reason": cb.trigger_reason,
            "tripped_at": cb.tripped_at
        })
    return res


# ============================================================================
# MACHINE AGENT AUTHENTICATION & RUNTIME SESSION GATEWAYS
# ============================================================================

import datetime
from typing import Any, Optional
from fastapi import HTTPException, status, Request
from core.deps import get_current_machine_agent, AuthenticatedAgent
from services.machine_auth_service import machine_auth_service
from services.passport_service import passport_service
import schemas


@router.post("/auth", response_model=schemas.MachineAuthResponse)
async def runtime_machine_auth(
    req: schemas.MachineAuthRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Primary machine authentication endpoint for AI agents.
    Validates machine credentials (ag_agent_...), checks agent and organization status,
    and issues short-lived cryptographically signed Machine JWT.
    """
    client_ip = request.client.host if request.client else "unknown"

    try:
        agent, cred = machine_auth_service.authenticate_agent_credential(
            db=db,
            credential_plaintext=req.credential,
            agent_code=req.agent_code
        )
    except ValueError as e:
        # Audit failed machine authentication attempt
        audit = models.AuditLog(
            org_id=None,
            event_type="RUNTIME_AUTH_FAILED",
            actor_type="MACHINE",
            actor_id=req.agent_code or "anonymous",
            action="MACHINE_AUTH",
            resource="runtime:auth",
            result="FAILURE",
            metadata_json={
                "agent_code": req.agent_code,
                "error": str(e),
                "client_ip": client_ip
            }
        )
        db.add(audit)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Machine authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Issue Short-Lived Machine JWT
    jwt_data = machine_auth_service.issue_machine_jwt(agent, cred, expires_in_hours=1)

    # Record / start runtime session
    session_jti = jwt_data["jti"]
    runtime_session = models.AgentRuntimeSession(
        agent_id=agent.id,
        session_token_jti=session_jti,
        status="ACTIVE",
        started_at=datetime.datetime.utcnow(),
        last_heartbeat_at=datetime.datetime.utcnow(),
        expires_at=datetime.datetime.fromisoformat(jwt_data["expires_at"]),
        client_ip=client_ip,
        user_agent=request.headers.get("User-Agent")
    )
    db.add(runtime_session)

    # Audit successful machine authentication
    audit = models.AuditLog(
        org_id=agent.org_id,
        event_type="RUNTIME_AUTHENTICATED",
        actor_type="MACHINE",
        actor_id=str(agent.id),
        action="MACHINE_AUTH",
        resource=f"agent:{agent.agent_code}",
        result="SUCCESS",
        metadata_json={
            "agent_id": str(agent.id),
            "agent_code": agent.agent_code,
            "credential_id": str(cred.id),
            "jti": session_jti,
            "client_ip": client_ip
        }
    )
    db.add(audit)
    db.commit()

    return schemas.MachineAuthResponse(
        access_token=jwt_data["access_token"],
        token_type=jwt_data["token_type"],
        expires_in=jwt_data["expires_in"],
        agent_id=jwt_data["agent_id"],
        agent_code=jwt_data["agent_code"],
        org_id=jwt_data["org_id"],
        autonomy_level=jwt_data["autonomy_level"],
        jti=jwt_data["jti"],
        expires_at=jwt_data["expires_at"]
    )


@router.get("/me")
def get_current_machine_identity(
    current_agent: AuthenticatedAgent = Depends(get_current_machine_agent),
    db: Session = Depends(get_db)
):
    """
    Returns verified machine identity, organization context, and cryptographic passport
    verification status for the currently authenticated machine agent.
    """
    agent = current_agent.agent
    passport = db.query(models.AgentPassport).filter(models.AgentPassport.agent_id == agent.id).first()
    
    passport_status = "UNKNOWN"
    passport_valid = False
    if passport:
        p_check = passport_service.verify_passport(passport, agent)
        passport_status = p_check["status"]
        passport_valid = p_check["valid"]

    # Active capabilities
    tokens = db.query(models.CapabilityToken).filter(
        models.CapabilityToken.agent_id == agent.id,
        models.CapabilityToken.status == "ACTIVE"
    ).all()

    return {
        "authenticated": True,
        "identity_type": "MACHINE_AGENT",
        "auth_method": current_agent.auth_method,
        "agent_id": current_agent.agent_id,
        "agent_code": current_agent.agent_code,
        "name": agent.name,
        "department": agent.department,
        "purpose": agent.purpose,
        "org_id": current_agent.org_id,
        "autonomy_level": current_agent.autonomy_level,
        "status": agent.status,
        "daily_budget": agent.daily_budget,
        "passport": {
            "passport_number": passport.passport_number if passport else None,
            "verification_status": passport.verification_status if passport else "MISSING",
            "is_cryptographically_valid": passport_valid,
            "cryptographic_status": passport_status,
            "algorithm": getattr(passport, "algorithm", "Ed25519") if passport else None
        },
        "active_capabilities_count": len(tokens),
        "active_capabilities": [t.capability_name for t in tokens]
    }


@router.post("/heartbeat", response_model=schemas.AgentRuntimeHeartbeatResponse)
async def runtime_agent_heartbeat(
    req: schemas.AgentRuntimeHeartbeatRequest,
    current_agent: AuthenticatedAgent = Depends(get_current_machine_agent),
    db: Session = Depends(get_db)
):
    """
    Heartbeat and liveness reporting endpoint for running AI agent instances.
    Keeps machine runtime session alive and confirms agent status.
    """
    now = datetime.datetime.utcnow()
    agent = current_agent.agent

    # Look up active session
    session_query = db.query(models.AgentRuntimeSession).filter(
        models.AgentRuntimeSession.agent_id == agent.id,
        models.AgentRuntimeSession.status == "ACTIVE"
    )
    if req.session_token_jti:
        session_query = session_query.filter(models.AgentRuntimeSession.session_token_jti == req.session_token_jti)
    elif current_agent.jti:
        session_query = session_query.filter(models.AgentRuntimeSession.session_token_jti == current_agent.jti)

    session_rec = session_query.order_by(models.AgentRuntimeSession.started_at.desc()).first()
    session_active = False

    if session_rec:
        session_rec.last_heartbeat_at = now
        session_rec.expires_at = now + datetime.timedelta(hours=1)
        session_active = True
        db.commit()

    return schemas.AgentRuntimeHeartbeatResponse(
        status="HEALTHY",
        agent_code=agent.agent_code,
        agent_status=agent.status,
        heartbeat_at=now,
        session_active=session_active
    )


# ============================================================================
# RUNTIME AUTHORIZATION KERNEL (12-STAGE INTERCEPTION GATE)
# ============================================================================

from core.deps import get_authenticated_entity
from services.runtime_authorization_service import runtime_authorization_service
from engines.circuit_breaker import circuit_breaker_engine
from ws_manager import manager as ws_manager


@router.post("/authorize", response_model=schemas.RuntimeAuthorizeResponse)
async def runtime_authorize_action(
    req: schemas.RuntimeAuthorizeRequest,
    entity: Any = Depends(get_authenticated_entity),
    db: Session = Depends(get_db)
):
    """
    Non-bypassable 12-Stage Pre-Flight Runtime Authorization Gate.
    Evaluates: Tenant -> Agent Lifecycle -> Passport Crypto -> Permissions ->
    Capabilities -> Budget -> Circuit Breaker -> Policy -> Human Review -> Execution Gate.
    """
    actor_id = None
    user_id = None
    agent = None

    if isinstance(entity, AuthenticatedAgent):
        agent = entity.agent
        actor_id = entity.agent_id
        user_id = None
        # Verify requested agent matches caller machine agent
        if req.agent_code and req.agent_code != agent.agent_code:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Machine credential for {agent.agent_code} cannot authorize actions for {req.agent_code}"
            )
        if req.agent_id and str(req.agent_id) != str(agent.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Machine credential cannot authorize actions for another agent ID"
            )
    elif isinstance(entity, models.User):
        actor_id = str(entity.id)
        user_id = str(entity.id)
        # Human user executing or testing on behalf of an agent
        if not req.agent_id and not req.agent_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing agent_id or agent_code in authorization request"
            )
        target_agent_id = req.agent_id or req.agent_code
        agent = db.query(models.Agent).filter(
            (models.Agent.id == target_agent_id) | (models.Agent.agent_code == target_agent_id)
        ).first()

        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target agent not found")

        if entity.role != "SUPER_ADMIN" and agent.org_id != entity.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Cross-tenant agent authorization denied"
            )
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    # Execute 12-stage pre-flight authorization
    auth_res = runtime_authorization_service.authorize_action(
        db=db,
        agent=agent,
        action=req.action,
        resource=req.resource,
        target=req.target,
        parameters=req.parameters,
        amount=req.amount or 0.0,
        capability_token=req.capability_token,
        context=req.context,
        prompt=req.prompt,
        actor_id=actor_id,
        user_id=user_id
    )

    return auth_res


@router.post("/circuit-breakers/{agent_id}/reset")
async def reset_circuit_breaker(
    agent_id: str,
    req: Optional[schemas.CircuitBreakerResetRequest] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Operator / Security Analyst endpoint to reset a tripped circuit breaker back to NORMAL state.
    """
    if current_user.role not in ("SUPER_ADMIN", "ADMIN", "OPERATOR", "SECURITY_ANALYST"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Insufficient privileges to reset circuit breakers"
        )

    agent = db.query(models.Agent).filter(
        (models.Agent.id == agent_id) | (models.Agent.agent_code == agent_id)
    ).first()

    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if current_user.role != "SUPER_ADMIN" and agent.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot reset circuit breaker for agent in another organization"
        )

    reason = (req.reason if req and req.reason else None) or "Manual operator reset"
    result = circuit_breaker_engine.reset_circuit(
        db=db,
        agent=agent,
        actor_id=str(current_user.id),
        reason=reason
    )

    await ws_manager.broadcast({
        "type": "CIRCUIT_BREAKER_RESET",
        "agent_code": agent.agent_code,
        "name": agent.name,
        "reset_by": current_user.email,
        "reason": reason,
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

    return {
        "status": "SUCCESS",
        "message": f"Circuit breaker for agent {agent.agent_code} successfully reset to NORMAL.",
        "agent_code": agent.agent_code,
        "state": result["state"],
        "restored_at": result["restored_at"]
    }


# ============================================================================
# FORWARD EXECUTION TOOL PROXY & AUTONOMOUS INVOCATION GATEWAYS
# ============================================================================

from services.tool_proxy_service import tool_proxy_service
from engines.intent_engine import intent_engine


@router.post("/execute", response_model=schemas.RuntimeExecuteResponse)
async def runtime_execute_action(
    req: schemas.RuntimeExecuteRequest,
    entity: Any = Depends(get_authenticated_entity),
    db: Session = Depends(get_db)
):
    """
    Forward Execution Tool Proxy Gate.
    Consumes a valid, single-use execution gate token issued during pre-flight authorization,
    dispatches the approved call to downstream tool endpoints, and records execution telemetry.
    """
    agent = None
    if isinstance(entity, AuthenticatedAgent):
        agent = entity.agent
    elif isinstance(entity, models.User):
        decision = db.query(models.Decision).filter(
            models.Decision.execution_gate_token == req.execution_gate_token
        ).first()
        if decision:
            agent = db.query(models.Agent).filter(models.Agent.id == decision.agent_id).first()
            if agent and entity.role != "SUPER_ADMIN" and agent.org_id != entity.org_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: Cannot execute gate token for an agent in another organization."
                )
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot resolve agent associated with execution request."
        )

    exec_result = tool_proxy_service.execute_tool(
        db=db,
        agent=agent,
        gate_token=req.execution_gate_token,
        tool_name=req.tool_name,
        parameters=req.parameters,
        override_endpoint=req.override_endpoint
    )

    if not exec_result["success"]:
        status_label = exec_result.get("status")
        if status_label == "GATE_TOKEN_INVALID":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exec_result["error"])
        elif status_label in ("GATE_TOKEN_REPLAYED", "GATE_TOKEN_EXPIRED", "SCHEMA_VALIDATION_FAILED"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exec_result["error"])
        elif status_label in ("AGENT_MISMATCH", "SSRF_BLOCKED"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exec_result["error"])

    return exec_result


@router.post("/invoke", response_model=schemas.RuntimeInvokeResponse)
async def runtime_invoke_action(
    req: schemas.RuntimeInvokeRequest,
    entity: Any = Depends(get_authenticated_entity),
    db: Session = Depends(get_db)
):
    """
    Combined Autonomous Agent Pre-Flight Authorize + Execute Gateway.
    Authorizes proposed action via 12-stage kernel. If allowed, immediately dispatches
    execution through the Forward Tool Proxy and returns both decision provenance
    and execution telemetry.
    """
    actor_id = None
    user_id = None
    agent = None

    if isinstance(entity, AuthenticatedAgent):
        agent = entity.agent
        actor_id = entity.agent_id
        if req.agent_code and req.agent_code != agent.agent_code:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-agent invocation forbidden.")
        if req.agent_id and str(req.agent_id) != str(agent.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-agent invocation forbidden.")
    elif isinstance(entity, models.User):
        actor_id = str(entity.id)
        user_id = str(entity.id)
        target_agent_id = req.agent_id or req.agent_code
        if not target_agent_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing agent_id or agent_code.")
        agent = db.query(models.Agent).filter(
            (models.Agent.id == target_agent_id) | (models.Agent.agent_code == target_agent_id)
        ).first()
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
        if entity.role != "SUPER_ADMIN" and agent.org_id != entity.org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant invocation forbidden.")
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    # 1. Authorize Action
    auth_res = runtime_authorization_service.authorize_action(
        db=db,
        agent=agent,
        action=req.action,
        resource=req.resource,
        target=req.target,
        parameters=req.parameters,
        amount=req.amount,
        capability_token=req.capability_token,
        prompt=req.prompt,
        context=req.context,
        actor_id=actor_id,
        user_id=user_id
    )

    execution_res = None
    # 2. If ALLOW, execute immediately through Tool Proxy
    if auth_res.decision == "ALLOW" and auth_res.execution_gate_token:
        exec_payload = tool_proxy_service.execute_tool(
            db=db,
            agent=agent,
            gate_token=auth_res.execution_gate_token,
            tool_name=req.tool_name or req.resource,
            parameters=req.parameters
        )
        execution_res = exec_payload

    return schemas.RuntimeInvokeResponse(
        authorized=(auth_res.decision == "ALLOW"),
        decision=auth_res.decision,
        decision_id=auth_res.decision_id,
        reason=auth_res.reason,
        approval_required=auth_res.approval_required,
        approval_id=auth_res.approval_id,
        risk_score=auth_res.risk_score,
        policy_name=auth_res.policy_name,
        execution_gate_token=auth_res.execution_gate_token,
        execution=execution_res
    )


@router.post("/validate-intent", response_model=schemas.IntentValidationResponse)
def validate_intent(
    req: schemas.IntentValidationRequest,
    entity: Any = Depends(get_authenticated_entity),
    db: Session = Depends(get_db)
):
    """
    Diagnostics endpoint to parse and validate tool parameters against schemas
    and test prompt injection detection heuristics.
    """
    structured_call = req.function_call or (
        {"name": req.tool_name, "arguments": req.arguments} if req.tool_name else None
    )

    extracted = intent_engine.extract_intent(req.prompt or "", structured_call=structured_call)
    inj = extracted.get("prompt_injection", {})

    schema = req.schema_definition
    if not schema and req.tool_name:
        tool_rec = db.query(models.Tool).filter(models.Tool.name == req.tool_name).first()
        if tool_rec and tool_rec.schema_definition:
            schema = tool_rec.schema_definition

    args = req.arguments or extracted.get("arguments", {})
    val_res = intent_engine.validate_parameters(schema, args)

    return schemas.IntentValidationResponse(
        intent=extracted["intent"],
        action=extracted["action"],
        resource=extracted["resource"],
        amount=extracted["amount"],
        customer_id=extracted["customer_id"],
        tool_name=extracted["tool_name"] or req.tool_name,
        arguments=args,
        schema_valid=val_res["valid"],
        schema_errors=val_res["errors"],
        is_prompt_injection=inj.get("is_injection", False),
        injection_confidence=inj.get("confidence", 0.0),
        injection_threat_level=inj.get("threat_level", "NONE"),
        injection_patterns=inj.get("matched_patterns", [])
    )


from engines.pii_engine import pii_engine


@router.post("/scan-pii", response_model=schemas.PIIScanResponse)
async def runtime_scan_pii(
    req: schemas.PIIScanRequest
):
    """
    AI Guardrails PII Diagnostic & Redaction Endpoint.
    Scans arbitrary prompts or JSON payloads, detects PII entities,
    and returns redacted/masked/tokenized versions.
    """
    sanitized_text = None
    sanitized_payload = None
    findings = []

    if req.text:
        redacted_t, t_findings = pii_engine.redact_text(req.text, mode=req.mode)
        sanitized_text = redacted_t
        findings.extend(t_findings)

    if req.payload:
        redacted_p, p_findings = pii_engine.scan_and_redact_payload(req.payload, mode=req.mode)
        sanitized_payload = redacted_p
        findings.extend(p_findings)

    return schemas.PIIScanResponse(
        has_pii=len(findings) > 0,
        findings_count=len(findings),
        findings=[f.to_dict() for f in findings],
        sanitized_text=sanitized_text,
        sanitized_payload=sanitized_payload,
        mode_applied=req.mode.upper()
    )




