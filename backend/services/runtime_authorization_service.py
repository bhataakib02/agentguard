import uuid
import datetime
import logging
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from config import settings
import models
import schemas
from services.passport_service import passport_service
from services.runtime_telemetry_service import check_budget_before_execution
from engines.capability_engine import capability_engine
from engines.circuit_breaker import circuit_breaker_engine
from engines.policy_engine import policy_engine
from engines.risk_engine import risk_engine
from engines.intent_engine import intent_engine
from engines.pii_engine import pii_engine
from engines.behavior_engine import behavior_engine
from engines.provenance_engine import provenance_engine
from ws_manager import manager as ws_manager

logger = logging.getLogger("agentguard.runtime_kernel")

class RuntimeAuthorizationService:
    """
    Canonical 12-Stage Runtime Authorization Kernel.
    Enforces non-bypassable pre-flight evaluation across:
    Machine Auth -> Tenant Isolation -> Agent Status -> Passport Cryptography ->
    Permissions -> Capability Tokens -> Intent Context -> FinOps Budget ->
    Circuit Breaker -> Policy Engine Rules -> Human Approval Escalation -> Audit.
    """

    def authorize_action(
        self,
        db: Session,
        agent: models.Agent,
        action: str,
        resource: str,
        target: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        amount: float = 0.0,
        capability_token: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        prompt: Optional[str] = None,
        actor_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> schemas.RuntimeAuthorizeResponse:
        now = datetime.datetime.utcnow()
        agent_code = agent.agent_code
        org_id = str(agent.org_id)
        effective_prompt = prompt or f"{action} on {resource} {target or ''}".strip()
        requested_amount = float(amount or 0.0)

        # --------------------------------------------------------------------
        # STAGE 1 & 2: TENANT VALIDATION
        # --------------------------------------------------------------------
        org = db.query(models.Organization).filter(models.Organization.id == agent.org_id).first()
        if not org or org.status != "ACTIVE":
            return self._build_refusal(
                db=db,
                agent=agent,
                action=action,
                resource=resource,
                amount=requested_amount,
                prompt=effective_prompt,
                stage="TENANT",
                reason="Organization is inactive or not found.",
                actor_id=actor_id,
                user_id=user_id
            )

        # --------------------------------------------------------------------
        # STAGE 3: AGENT LIFECYCLE STATUS
        # --------------------------------------------------------------------
        if agent.status in ("SUSPENDED", "CIRCUIT_BREAK"):
            return self._build_refusal(
                db=db,
                agent=agent,
                action=action,
                resource=resource,
                amount=requested_amount,
                prompt=effective_prompt,
                stage="AGENT_STATUS",
                reason=f"AI agent {agent_code} is currently in {agent.status} state. Execution blocked.",
                actor_id=actor_id,
                user_id=user_id
            )

        # --------------------------------------------------------------------
        # STAGE 4: CRYPTOGRAPHIC PASSPORT VERIFICATION
        # --------------------------------------------------------------------
        passport = db.query(models.AgentPassport).filter(models.AgentPassport.agent_id == agent.id).first()
        if not passport:
            return self._build_refusal(
                db=db,
                agent=agent,
                action=action,
                resource=resource,
                amount=requested_amount,
                prompt=effective_prompt,
                stage="PASSPORT",
                reason="Cryptographic Agent Passport is missing. Machine identity unverified.",
                actor_id=actor_id,
                user_id=user_id
            )

        passport_check = passport_service.verify_passport(passport, agent)
        if not passport_check["valid"]:
            return self._build_refusal(
                db=db,
                agent=agent,
                action=action,
                resource=resource,
                amount=requested_amount,
                prompt=effective_prompt,
                stage="PASSPORT",
                reason=f"Passport verification failed: {passport_check['reason']}",
                actor_id=actor_id,
                user_id=user_id
            )

        # --------------------------------------------------------------------
        # STAGE 5: PERMISSION ENFORCEMENT
        # --------------------------------------------------------------------
        # Look up granted permissions for this agent
        agent_permissions = db.query(models.Permission).filter(
            models.Permission.agent_id == agent.id,
            models.Permission.is_allowed == True
        ).all()

        has_perm = self._check_permission_match(agent_permissions, resource, target, action)
        if not has_perm:
            return self._build_refusal(
                db=db,
                agent=agent,
                action=action,
                resource=resource,
                amount=requested_amount,
                prompt=effective_prompt,
                stage="PERMISSION",
                reason=f"PERMISSION_DENIED: Agent lacking granted permission for {resource}:{action}.",
                actor_id=actor_id,
                user_id=user_id
            )

        # --------------------------------------------------------------------
        # STAGE 6: CAPABILITY TOKEN ENFORCEMENT
        # --------------------------------------------------------------------
        cap_record = None
        if capability_token:
            cap_check = capability_engine.validate_token(
                db=db,
                token_code=capability_token,
                agent=agent,
                required_capability=f"{resource}.{action}",
                requested_amount=requested_amount,
                requested_scope=target
            )
            if not cap_check["valid"]:
                return self._build_refusal(
                    db=db,
                    agent=agent,
                    action=action,
                    resource=resource,
                    amount=requested_amount,
                    prompt=effective_prompt,
                    stage="CAPABILITY",
                    reason=f"CAPABILITY_DENIED: {cap_check['reason']}",
                    actor_id=actor_id,
                    user_id=user_id
                )
            cap_record = cap_check.get("token")

        # --------------------------------------------------------------------
        # STAGE 6.5: INTENT UNDERSTANDING, PROMPT INJECTION & SCHEMA VALIDATION
        # --------------------------------------------------------------------
        injection_check = intent_engine.detect_prompt_injection(effective_prompt)
        if not injection_check["is_injection"] and parameters:
            for p_val in parameters.values():
                if isinstance(p_val, str):
                    p_inj = intent_engine.detect_prompt_injection(p_val)
                    if p_inj["is_injection"]:
                        injection_check = p_inj
                        break

        if injection_check["is_injection"] and injection_check["threat_level"] in ("CRITICAL", "HIGH"):
            return self._build_refusal(
                db=db,
                agent=agent,
                action=action,
                resource=resource,
                amount=requested_amount,
                prompt=effective_prompt,
                stage="PROMPT_INJECTION",
                reason=f"Security Refusal: Prompt injection or jailbreak detected ({injection_check['explanation']}).",
                actor_id=actor_id,
                user_id=user_id
            )

        matched_tool = db.query(models.Tool).filter(
            (models.Tool.name == action) |
            (models.Tool.name == resource) |
            (models.Tool.name == target)
        ).first()

        if matched_tool and matched_tool.schema_definition and parameters:
            param_check = intent_engine.validate_parameters(matched_tool.schema_definition, parameters)
            if not param_check["valid"]:
                return self._build_refusal(
                    db=db,
                    agent=agent,
                    action=action,
                    resource=resource,
                    amount=requested_amount,
                    prompt=effective_prompt,
                    stage="SCHEMA_VALIDATION",
                    reason=f"SCHEMA_VALIDATION_FAILED: {'; '.join(param_check['errors'])}",
                    actor_id=actor_id,
                    user_id=user_id
                )

        # --------------------------------------------------------------------
        # STAGE 6.6: AI GUARDRAILS & PII FILTER
        # --------------------------------------------------------------------
        pii_mode = (context or {}).get("pii_mode", "MASK") if context else "MASK"
        pii_guard = pii_engine.evaluate_guardrail(
            prompt=effective_prompt,
            parameters=parameters,
            policy_mode=pii_mode
        )
        if pii_guard["blocked"]:
            return self._build_refusal(
                db=db,
                agent=agent,
                action=action,
                resource=resource,
                amount=requested_amount,
                prompt=effective_prompt,
                stage="PII_VIOLATION",
                reason=f"DATA_SAFETY_VIOLATION: Unredacted PII detected ({pii_guard['findings_count']} items found). Action blocked by data governance policy.",
                actor_id=actor_id,
                user_id=user_id
            )

        if pii_guard["has_pii"]:
            effective_prompt = pii_guard["sanitized_prompt"] or effective_prompt
            parameters = pii_guard["sanitized_parameters"]

        # --------------------------------------------------------------------
        # STAGE 7: BUDGET & FINOPS LIMITS
        # --------------------------------------------------------------------
        if agent.daily_budget and requested_amount > 0 and requested_amount > agent.daily_budget:
            return self._build_refusal(
                db=db,
                agent=agent,
                action=action,
                resource=resource,
                amount=requested_amount,
                prompt=effective_prompt,
                stage="BUDGET",
                reason=f"FINOPS_BUDGET_EXCEEDED: Requested amount ${requested_amount} exceeds agent daily budget ${agent.daily_budget}.",
                actor_id=actor_id,
                user_id=user_id
            )

        budget_check = check_budget_before_execution(db, org_id, str(agent.id))
        if not budget_check["allowed"]:
            return self._build_refusal(
                db=db,
                agent=agent,
                action=action,
                resource=resource,
                amount=requested_amount,
                prompt=effective_prompt,
                stage="BUDGET",
                reason=f"FINOPS_BUDGET_EXCEEDED: {budget_check['reason']}",
                actor_id=actor_id,
                user_id=user_id
            )

        # --------------------------------------------------------------------
        # STAGE 8: CIRCUIT BREAKER GATE
        # --------------------------------------------------------------------
        cb_check = circuit_breaker_engine.check_agent_circuit(db, agent)
        if cb_check["tripped"]:
            return self._build_refusal(
                db=db,
                agent=agent,
                action=action,
                resource=resource,
                amount=requested_amount,
                prompt=effective_prompt,
                stage="CIRCUIT_BREAKER",
                reason=f"CIRCUIT_BREAKER_TRIPPED: {cb_check['reason']}",
                actor_id=actor_id,
                user_id=user_id
            )

        # --------------------------------------------------------------------
        # STAGE 8.5: STATISTICAL BEHAVIORAL ANOMALY EVALUATION
        # --------------------------------------------------------------------
        behavior_eval = behavior_engine.evaluate_behavior(
            agent=agent,
            db=db,
            tool_name=matched_tool.name if matched_tool else action,
            requested_amount=requested_amount
        )
        behavior_deviation = behavior_eval.get("deviation_score", 0.0)

        # --------------------------------------------------------------------
        # STAGE 8.7: BOUNDED ACTION-SEQUENCE RISK EVALUATION
        # --------------------------------------------------------------------
        from engines.predictive_action_control_engine import predictive_action_control_engine
        sequence_indicators = predictive_action_control_engine.sequence_analyzer.analyze_sequence(
            db=db,
            agent_id=str(agent.id),
            org_id=str(agent.org_id),
            current_action=action,
            current_resource=resource,
            current_amount=requested_amount
        )
        sequence_risk_delta = sequence_indicators.sequence_risk_delta

        # --------------------------------------------------------------------
        # STAGE 9: POLICY ENGINE EVALUATION
        # --------------------------------------------------------------------
        risk_res = risk_engine.calculate_risk(
            agent_autonomy=agent.autonomy_level,
            action=action,
            amount=requested_amount,
            daily_budget=agent.daily_budget,
            behavior_deviation=behavior_deviation,
            sequence_risk_delta=sequence_risk_delta
        )
        calculated_risk_score = risk_res.get("overall_score", 15)

        policy_res = policy_engine.evaluate_action(
            db=db,
            org_id=agent.org_id,
            agent_name=agent.name,
            action=action,
            resource=resource,
            amount=requested_amount,
            risk_score=calculated_risk_score,
            agent_status=agent.status,
            agent_autonomy=agent.autonomy_level,
            agent_department=agent.department,
            agent_code=agent.agent_code,
            user_role="MACHINE",
            intent=effective_prompt,
            environmental_context={
                "is_within_operating_hours": not behavior_eval.get("is_off_hours", False),
                "is_off_hours": behavior_eval.get("is_off_hours", False),
                "behavior_deviation": behavior_deviation,
                "request_velocity": behavior_eval.get("request_velocity", 1.0),
                "ip_address": (context or {}).get("ip_address", "127.0.0.1")
            }
        )

        decision_outcome = policy_res.get("decision", "REFUSE")
        risk_score = policy_res.get("risk_score", calculated_risk_score)
        policy_name = policy_res.get("policy_applied", policy_res.get("policy_name", "Global Safety Policy"))
        explanation = policy_res.get("reason", policy_res.get("explanation", "Evaluated by policy engine."))

        # --------------------------------------------------------------------
        # STAGE 10: DECISION RECORDING & PROVENANCE
        # --------------------------------------------------------------------
        gate_token = None
        if decision_outcome == "ALLOW":
            gate_token = f"gate_{uuid.uuid4().hex[:16]}"
            # Consume one-time capability token if provided
            if capability_token:
                capability_engine.consume_token(db, capability_token, actor_id=agent_code)

        # Safely resolve user_id foreign key
        resolved_user_id = None
        if user_id:
            user_exists = db.query(models.User).filter(models.User.id == user_id).first()
            if user_exists:
                resolved_user_id = user_exists.id

        decision_rec = models.Decision(
            agent_id=agent.id,
            user_id=resolved_user_id,
            intent_summary=effective_prompt,
            action_requested=action,
            resource_target=f"{resource}:{target or ''}".rstrip(":"),
            amount=requested_amount,
            decision=decision_outcome,
            risk_score=risk_score,
            policy_name=policy_name,
            explanation=explanation,
            execution_status="EXECUTED" if decision_outcome == "ALLOW" else ("PENDING_APPROVAL" if decision_outcome == "REVIEW" else "BLOCKED"),
            execution_gate_token=gate_token,
            gate_token_used=False,
            tool_id=matched_tool.id if matched_tool else None,
            execution_parameters=parameters or {},
            timestamp=now
        )
        db.add(decision_rec)
        db.commit()
        db.refresh(decision_rec)

        # --------------------------------------------------------------------
        # STAGE 11: HUMAN APPROVAL ESCALATION (IF REVIEW)
        # --------------------------------------------------------------------
        approval_id = None
        if decision_outcome == "REVIEW":
            approval = models.ApprovalRequest(
                decision_id=decision_rec.id,
                agent_id=agent.id,
                amount=requested_amount,
                reason=f"Policy {policy_name or 'Human-in-the-Loop'} triggered review: {explanation}",
                status="PENDING",
                created_at=now
            )
            db.add(approval)
            db.commit()
            db.refresh(approval)
            approval_id = str(approval.id)

        # Audit event
        audit_event = f"RUNTIME_AUTHORIZED_{decision_outcome}"
        audit = models.AuditLog(
            org_id=agent.org_id,
            event_type=audit_event,
            actor_type="MACHINE",
            actor_id=str(agent.id),
            action="RUNTIME_AUTHORIZE",
            resource=f"action:{resource}:{action}",
            result="SUCCESS" if decision_outcome == "ALLOW" else ("WARNING" if decision_outcome == "REVIEW" else "FAILURE"),
            metadata_json={
                "agent_code": agent_code,
                "decision": decision_outcome,
                "decision_id": str(decision_rec.id),
                "approval_id": approval_id,
                "amount": requested_amount,
                "risk_score": risk_score,
                "policy_name": policy_name
            }
        )
        db.add(audit)
        db.commit()

        # If refused, check if consecutive refusals should trip circuit breaker
        if decision_outcome == "REFUSE":
            circuit_breaker_engine.check_agent_circuit(db, agent)

        return schemas.RuntimeAuthorizeResponse(
            authorized=(decision_outcome == "ALLOW"),
            decision=decision_outcome,
            decision_id=str(decision_rec.id),
            reason=explanation,
            stage_failed=None if decision_outcome in ("ALLOW", "REVIEW") else "POLICY",
            agent_code=agent_code,
            org_id=org_id,
            action=action,
            resource=resource,
            approval_required=(decision_outcome == "REVIEW"),
            approval_id=approval_id,
            risk_score=risk_score,
            policy_name=policy_name,
            execution_gate_token=gate_token
        )

    def _check_permission_match(
        self,
        granted_permissions: list,
        resource: str,
        target: Optional[str],
        action: str
    ) -> bool:
        """
        Evaluates whether any active granted permission covers the requested (resource, target, action).
        Supports wildcard matching (e.g. action='*' or resource_type='*').
        """
        req_action = action.upper().strip()
        req_res = resource.upper().strip()
        req_target = (target or "").upper().strip()

        for perm in granted_permissions:
            perm_action = perm.action.upper().strip()
            perm_res_type = perm.resource_type.upper().strip()
            perm_res_name = perm.resource_name.upper().strip()

            action_match = (perm_action == "*" or perm_action == req_action)
            
            # Match resource type or resource name
            res_match = (
                perm_res_type == "*" or
                perm_res_type == req_res or
                perm_res_name == "*" or
                perm_res_name == req_res or
                (req_target and perm_res_name == req_target)
            )

            if action_match and res_match:
                return True

        return False

    def _build_refusal(
        self,
        db: Session,
        agent: models.Agent,
        action: str,
        resource: str,
        amount: float,
        prompt: str,
        stage: str,
        reason: str,
        actor_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> schemas.RuntimeAuthorizeResponse:
        """
        Helper to record, audit, and return a clean structured refusal.
        """
        now = datetime.datetime.utcnow()

        resolved_user_id = None
        if user_id:
            user_exists = db.query(models.User).filter(models.User.id == user_id).first()
            if user_exists:
                resolved_user_id = user_exists.id

        decision = models.Decision(
            agent_id=agent.id,
            user_id=resolved_user_id,
            intent_summary=prompt,
            action_requested=action,
            resource_target=resource,
            amount=amount,
            decision="REFUSE",
            risk_score=85,
            policy_name=f"GATE_CHECK_{stage}",
            explanation=reason,
            execution_status="BLOCKED",
            timestamp=now
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)

        audit = models.AuditLog(
            org_id=agent.org_id,
            event_type="RUNTIME_REFUSED",
            actor_type="MACHINE",
            actor_id=str(agent.id),
            action="RUNTIME_AUTHORIZE",
            resource=f"action:{resource}:{action}",
            result="FAILURE",
            metadata_json={
                "agent_code": agent.agent_code,
                "stage_failed": stage,
                "reason": reason,
                "decision_id": str(decision.id)
            }
        )
        db.add(audit)
        db.commit()

        # Check circuit breaker on refusal
        circuit_breaker_engine.check_agent_circuit(db, agent)

        logger.warning(f"[RuntimeKernel] Refused action for {agent.agent_code} at {stage}: {reason}")
        return schemas.RuntimeAuthorizeResponse(
            authorized=False,
            decision="REFUSE",
            decision_id=str(decision.id),
            reason=reason,
            stage_failed=stage,
            agent_code=agent.agent_code,
            org_id=str(agent.org_id),
            action=action,
            resource=resource,
            approval_required=False,
            approval_id=None,
            risk_score=85,
            policy_name=f"GATE_CHECK_{stage}"
        )

runtime_authorization_service = RuntimeAuthorizationService()
