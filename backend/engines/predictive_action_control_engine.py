"""
Predictive Action Control Engine (PACE) - Phase 1
Authoritative, non-bypassable pre-flight action evaluation and execution boundary.
Integrates machine authentication, tenant isolation, autonomy level governance,
permission enforcement, sequence-aware risk assessment, deterministic policy rules,
and immutable audit logging.
"""

import uuid
import datetime
import logging
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

import models
import schemas
from engines.risk_engine import risk_engine
from engines.policy_engine import policy_engine
from engines.circuit_breaker import circuit_breaker_engine
from services.passport_service import passport_service
from services.tool_proxy_service import tool_proxy_service
from core.deps import AuthenticatedAgent

logger = logging.getLogger("agentguard.pace")


class ActionSequenceAnalyzer:
    """
    Bounded Action-Sequence Risk Analyzer.
    Examines recent historical actions for an authenticated agent within its tenant organization
    over a configurable history window.
    Detects explicit, documented, testable patterns without inventing missing events.
    """

    def analyze_sequence(
        self,
        db: Session,
        agent_id: str,
        org_id: str,
        current_action: str,
        current_resource: str,
        current_amount: float = 0.0,
        window_size: int = 10,
        window_seconds: int = 900
    ) -> schemas.SequenceIndicators:
        now = datetime.datetime.utcnow()
        cutoff_time = now - datetime.timedelta(seconds=window_seconds)

        # Query recent decisions for this agent, strictly scoped to agent_id and tenant org
        recent_decisions = db.query(models.Decision).join(
            models.Agent, models.Decision.agent_id == models.Agent.id
        ).filter(
            models.Decision.agent_id == agent_id,
            models.Agent.org_id == org_id,
            models.Decision.timestamp >= cutoff_time
        ).order_by(models.Decision.timestamp.desc()).limit(window_size).all()

        if not recent_decisions:
            return schemas.SequenceIndicators(
                window_size=window_size,
                window_seconds=window_seconds,
                events_evaluated=0,
                missing_history=True,
                patterns_detected=[],
                sequence_risk_delta=0,
                explanation="No prior sequence history found within the bounded window. Baseline evaluation applied without sequence adjustments.",
                features={
                    "consecutive_refusals": 0,
                    "burst_count_last_60s": 0,
                    "recon_count": 0,
                    "cumulative_window_amount": float(current_amount or 0.0)
                }
            )

        events_evaluated = len(recent_decisions)
        patterns: List[schemas.SequencePatternDetection] = []
        total_risk_delta = 0

        # Pattern 1: REPEATED_REFUSALS_CASCADE
        consecutive_refusals = 0
        for d in recent_decisions:
            if d.decision == "REFUSE":
                consecutive_refusals += 1
            else:
                break

        if consecutive_refusals >= 2:
            p_refusal = schemas.SequencePatternDetection(
                pattern_name="REPEATED_REFUSALS_CASCADE",
                severity="HIGH",
                description=f"Agent experienced {consecutive_refusals} consecutive recent refusals in the sequence window.",
                risk_delta=20
            )
            patterns.append(p_refusal)
            total_risk_delta += 20

        # Pattern 2: RAPID_BURST_ACTIVITY (>= 5 actions in last 60 seconds)
        one_min_ago = now - datetime.timedelta(seconds=60)
        burst_count = sum(1 for d in recent_decisions if d.timestamp >= one_min_ago)
        if burst_count >= 5:
            p_burst = schemas.SequencePatternDetection(
                pattern_name="RAPID_BURST_ACTIVITY",
                severity="MEDIUM",
                description=f"High action burst: {burst_count} actions initiated within the last 60 seconds.",
                risk_delta=15
            )
            patterns.append(p_burst)
            total_risk_delta += 15

        # Pattern 3: RECON_TO_EXFILTRATION_SEQUENCE
        curr_act_lower = (current_action or "").lower()
        is_sensitive_op = any(k in curr_act_lower for k in ["delete", "drop", "export", "dump", "exfiltrate", "download"])
        recon_count = sum(
            1 for d in recent_decisions
            if any(k in (d.action_requested or "").lower() for k in ["read", "query", "select", "list", "search", "scan", "describe"])
            and any(r in (d.resource_target or "").lower() for r in ["db", "database", "table", "user", "customer", "prod", "data"])
        )
        if is_sensitive_op and recon_count >= 1:
            p_recon = schemas.SequencePatternDetection(
                pattern_name="RECON_TO_EXFILTRATION_SEQUENCE",
                severity="HIGH",
                description=f"Multi-step progression pattern detected: sensitive operation '{current_action}' following {recon_count} database/reconnaissance queries.",
                risk_delta=25
            )
            patterns.append(p_recon)
            total_risk_delta += 25

        # Pattern 4: CUMULATIVE_FINANCIAL_SPIKE
        cum_amount = sum(d.amount for d in recent_decisions if d.amount) + float(current_amount or 0.0)
        if cum_amount > 25000:
            p_fin = schemas.SequencePatternDetection(
                pattern_name="CUMULATIVE_FINANCIAL_SPIKE",
                severity="HIGH",
                description=f"Cumulative transaction volume in history window (₹{cum_amount:,.2f}) exceeded threshold ₹25,000.00.",
                risk_delta=20
            )
            patterns.append(p_fin)
            total_risk_delta += 20

        # Cap total sequence delta
        capped_delta = min(50, total_risk_delta)

        if patterns:
            pattern_names = ", ".join(p.pattern_name for p in patterns)
            explanation = (
                f"Sequence-aware evaluation detected {len(patterns)} anomalous pattern(s) [{pattern_names}], "
                f"adjusting sequence risk by +{capped_delta} points across {events_evaluated} recent events."
            )
        else:
            explanation = f"Evaluated {events_evaluated} recent actions in sequence window; no anomalous sequence patterns detected."

        return schemas.SequenceIndicators(
            window_size=window_size,
            window_seconds=window_seconds,
            events_evaluated=events_evaluated,
            missing_history=False,
            patterns_detected=patterns,
            sequence_risk_delta=capped_delta,
            explanation=explanation,
            features={
                "consecutive_refusals": consecutive_refusals,
                "burst_count_last_60s": burst_count,
                "recon_count": recon_count,
                "cumulative_window_amount": cum_amount
            }
        )


class PredictiveActionControlEngine:
    """
    Predictive Action Control Engine (PACE) - Phase 1
    Canonical pipeline:
    1. Authenticate caller and resolve server-side agent identity.
    2. Load applicable organization, agent permissions, autonomy level, and policies.
    3. Evaluate mandatory authorization and policy constraints.
    4. Calculate sequence-aware risk assessment.
    5. Apply deterministic decision rules (REFUSE > REVIEW > ALLOW).
    6. Produce structured decision and persist state.
    7. Record decision through immutable audit log.
    """

    def __init__(self):
        self.sequence_analyzer = ActionSequenceAnalyzer()

    def evaluate_action(
        self,
        db: Session,
        caller_entity: Any,
        request: schemas.ActionControlEvaluationRequest
    ) -> schemas.ActionControlEvaluationResponse:
        now = datetime.datetime.utcnow()
        correlation_id = request.correlation_id or f"corr_{uuid.uuid4().hex[:12]}"

        try:
            # ----------------------------------------------------------------
            # STAGE 1: AUTHENTICATION & AGENT IDENTITY RESOLUTION
            # ----------------------------------------------------------------
            if caller_entity is None:
                return self._build_fail_response(
                    db=db,
                    reason="Authentication required: No valid caller credentials provided.",
                    stage="AUTHENTICATION",
                    request=request,
                    correlation_id=correlation_id,
                    agent=None,
                    org_id="UNAUTHENTICATED"
                )

            agent = None
            actor_type = "USER"
            actor_id = "unknown"

            if isinstance(caller_entity, AuthenticatedAgent):
                agent = caller_entity.agent
                actor_type = "MACHINE"
                actor_id = agent.agent_code

                # Forbid spoofing or cross-agent requests by machine agents
                if request.agent_code and request.agent_code.strip() != agent.agent_code:
                    return self._build_fail_response(
                        db=db,
                        reason=f"Identity mismatch: Machine agent {agent.agent_code} cannot evaluate actions for {request.agent_code}.",
                        stage="IDENTITY_MISMATCH",
                        request=request,
                        correlation_id=correlation_id,
                        agent=agent,
                        org_id=str(agent.org_id)
                    )
                if request.agent_id and str(request.agent_id).strip() != str(agent.id):
                    return self._build_fail_response(
                        db=db,
                        reason="Identity mismatch: Machine agent cannot evaluate actions for another agent ID.",
                        stage="IDENTITY_MISMATCH",
                        request=request,
                        correlation_id=correlation_id,
                        agent=agent,
                        org_id=str(agent.org_id)
                    )

            elif isinstance(caller_entity, models.User):
                actor_type = "USER"
                actor_id = str(caller_entity.id)

                target_agent_identifier = request.agent_id or request.agent_code
                if not target_agent_identifier or not target_agent_identifier.strip():
                    return self._build_fail_response(
                        db=db,
                        reason="Malformed request: Missing target agent identifier (agent_id or agent_code).",
                        stage="VALIDATION",
                        request=request,
                        correlation_id=correlation_id,
                        agent=None,
                        org_id=str(caller_entity.org_id) if caller_entity.org_id else "UNKNOWN"
                    )

                agent = db.query(models.Agent).filter(
                    (models.Agent.id == target_agent_identifier.strip()) |
                    (models.Agent.agent_code == target_agent_identifier.strip())
                ).first()

                if not agent:
                    return self._build_fail_response(
                        db=db,
                        reason=f"Agent not found: No registered AI agent matches '{target_agent_identifier}'.",
                        stage="AGENT_NOT_FOUND",
                        request=request,
                        correlation_id=correlation_id,
                        agent=None,
                        org_id=str(caller_entity.org_id) if caller_entity.org_id else "UNKNOWN"
                    )

                # Strict Tenant Isolation: user cannot act on another organization's agent
                if caller_entity.role != "SUPER_ADMIN" and str(agent.org_id) != str(caller_entity.org_id):
                    return self._build_fail_response(
                        db=db,
                        reason="Forbidden: Cross-tenant agent access prohibited. Agent belongs to another organization.",
                        stage="TENANT_ISOLATION",
                        request=request,
                        correlation_id=correlation_id,
                        agent=agent,
                        org_id=str(caller_entity.org_id)
                    )
            else:
                return self._build_fail_response(
                    db=db,
                    reason="Invalid caller entity type.",
                    stage="AUTHENTICATION",
                    request=request,
                    correlation_id=correlation_id,
                    agent=None,
                    org_id="UNKNOWN"
                )

            # ----------------------------------------------------------------
            # STAGE 2: VALIDATE & NORMALIZE ACTION REQUEST
            # ----------------------------------------------------------------
            raw_action = (request.action_type or "").strip()
            raw_resource = (request.target_resource or "").strip()
            raw_operation = (request.operation or "").strip()
            requested_amount = float(request.amount or 0.0)

            if not raw_action or not raw_resource:
                return self._build_fail_response(
                    db=db,
                    reason="Malformed request: action_type and target_resource must be non-empty strings.",
                    stage="VALIDATION",
                    request=request,
                    correlation_id=correlation_id,
                    agent=agent,
                    org_id=str(agent.org_id)
                )

            effective_prompt = request.prompt or f"{raw_action} on {raw_resource} {raw_operation}".strip()

            # ----------------------------------------------------------------
            # STAGE 3: TENANT CONTEXT & AGENT STATUS CHECKS
            # ----------------------------------------------------------------
            org = db.query(models.Organization).filter(models.Organization.id == agent.org_id).first()
            if not org or org.status != "ACTIVE":
                return self._build_fail_response(
                    db=db,
                    reason=f"Organization {agent.org_id} is inactive or does not exist.",
                    stage="TENANT_STATUS",
                    request=request,
                    correlation_id=correlation_id,
                    agent=agent,
                    org_id=str(agent.org_id)
                )

            # Check Agent Lifecycle Status
            if agent.status in ("SUSPENDED", "CIRCUIT_BREAK"):
                return self._build_fail_response(
                    db=db,
                    reason=f"Agent '{agent.agent_code}' is in {agent.status} state. Action execution is blocked.",
                    stage="AGENT_STATUS",
                    request=request,
                    correlation_id=correlation_id,
                    agent=agent,
                    org_id=str(agent.org_id)
                )

            # Check Cryptographic Agent Passport
            passport = db.query(models.AgentPassport).filter(models.AgentPassport.agent_id == agent.id).first()
            if not passport:
                return self._build_fail_response(
                    db=db,
                    reason="Cryptographic Agent Passport is missing. Machine identity unverified.",
                    stage="PASSPORT",
                    request=request,
                    correlation_id=correlation_id,
                    agent=agent,
                    org_id=str(agent.org_id)
                )

            passport_check = passport_service.verify_passport(passport, agent)
            if not passport_check.get("valid", False):
                return self._build_fail_response(
                    db=db,
                    reason=f"Passport cryptographic verification failed: {passport_check.get('reason', 'Invalid signature')}.",
                    stage="PASSPORT",
                    request=request,
                    correlation_id=correlation_id,
                    agent=agent,
                    org_id=str(agent.org_id)
                )

            # Check Granted Permissions (models.Permission)
            agent_permissions = db.query(models.Permission).filter(
                models.Permission.agent_id == agent.id,
                models.Permission.is_allowed == True
            ).all()

            has_permission = self._check_permission(agent_permissions, raw_resource, raw_operation, raw_action)
            if not has_permission:
                return self._build_fail_response(
                    db=db,
                    reason=f"PERMISSION_DENIED: Agent lacking granted permission for {raw_resource}:{raw_action}.",
                    stage="PERMISSION",
                    request=request,
                    correlation_id=correlation_id,
                    agent=agent,
                    org_id=str(agent.org_id)
                )

            # Check Circuit Breaker Engine
            cb_check = circuit_breaker_engine.check_agent_circuit(db, agent)
            if cb_check.get("tripped", False):
                return self._build_fail_response(
                    db=db,
                    reason=f"CIRCUIT_BREAKER_TRIPPED: {cb_check.get('reason', 'Agent circuit breaker tripped.')}",
                    stage="CIRCUIT_BREAKER",
                    request=request,
                    correlation_id=correlation_id,
                    agent=agent,
                    org_id=str(agent.org_id)
                )

            # Check Agent Daily Budget Ceiling
            if agent.daily_budget and requested_amount > 0 and requested_amount > agent.daily_budget:
                return self._build_fail_response(
                    db=db,
                    reason=f"FINOPS_BUDGET_EXCEEDED: Requested amount ₹{requested_amount:,.2f} exceeds agent daily budget ₹{agent.daily_budget:,.2f}.",
                    stage="BUDGET",
                    request=request,
                    correlation_id=correlation_id,
                    agent=agent,
                    org_id=str(agent.org_id)
                )

            # ----------------------------------------------------------------
            # STAGE 4: SEQUENCE-AWARE RISK ASSESSMENT
            # ----------------------------------------------------------------
            window_size = request.history_window_size or 10
            window_seconds = request.history_window_seconds or 900

            sequence_indicators = self.sequence_analyzer.analyze_sequence(
                db=db,
                agent_id=str(agent.id),
                org_id=str(agent.org_id),
                current_action=raw_action,
                current_resource=raw_resource,
                current_amount=requested_amount,
                window_size=window_size,
                window_seconds=window_seconds
            )

            # Calculate baseline risk + sequence delta
            risk_calc = risk_engine.calculate_risk(
                agent_autonomy=agent.autonomy_level,
                action=raw_action,
                amount=requested_amount,
                daily_budget=agent.daily_budget or 10000.0,
                behavior_deviation=0.0,
                historical_violations=0,
                sequence_risk_delta=sequence_indicators.sequence_risk_delta
            )
            calculated_risk_score = risk_calc.get("overall_score", 15)
            risk_level = risk_calc.get("level", "LOW")
            risk_breakdown = risk_calc.get("breakdown", {})

            # ----------------------------------------------------------------
            # STAGE 5: DETERMINISTIC POLICY EVALUATION
            # ----------------------------------------------------------------
            policy_res = policy_engine.evaluate_action(
                db=db,
                org_id=agent.org_id,
                agent_name=agent.name,
                action=raw_action,
                resource=raw_resource,
                amount=requested_amount,
                risk_score=calculated_risk_score,
                agent_status=agent.status,
                agent_autonomy=agent.autonomy_level,
                agent_department=agent.department,
                agent_code=agent.agent_code,
                user_role=actor_type,
                intent=effective_prompt,
                environmental_context={
                    "correlation_id": correlation_id,
                    "sequence_risk_delta": sequence_indicators.sequence_risk_delta,
                    "patterns_detected_count": len(sequence_indicators.patterns_detected)
                }
            )

            decision_outcome = policy_res.get("decision", "REFUSE")
            policy_applied = policy_res.get("policy_applied", "Global Safety Baseline")
            policy_id = policy_res.get("policy_id")
            rule_id = policy_res.get("rule_id")
            explanation = policy_res.get("reason", "Evaluated by policy engine.")
            final_risk_score = policy_res.get("risk_score", calculated_risk_score)

            # Mandatory Authorization Invariant: A low risk score CAN NEVER override a policy refusal
            # If policy says REFUSE, decision must be REFUSE
            if decision_outcome not in ("ALLOW", "REVIEW", "REFUSE"):
                decision_outcome = "REFUSE"

            # ----------------------------------------------------------------
            # STAGE 6: DECISION RECORDING & HUMAN APPROVAL WORKFLOW
            # ----------------------------------------------------------------
            gate_token = None
            if decision_outcome == "ALLOW":
                gate_token = f"gate_{uuid.uuid4().hex[:16]}"

            resolved_user_id = None
            if isinstance(caller_entity, models.User):
                resolved_user_id = caller_entity.id

            decision_record = models.Decision(
                agent_id=agent.id,
                user_id=resolved_user_id,
                intent_summary=effective_prompt,
                action_requested=raw_action,
                resource_target=f"{raw_resource}:{raw_operation}".rstrip(":"),
                amount=requested_amount,
                decision=decision_outcome,
                risk_score=final_risk_score,
                policy_name=policy_applied,
                explanation=explanation,
                execution_status="EXECUTED" if decision_outcome == "ALLOW" else ("PENDING_APPROVAL" if decision_outcome == "REVIEW" else "BLOCKED"),
                execution_gate_token=gate_token,
                gate_token_used=False,
                execution_parameters=request.parameters or {},
                timestamp=now
            )
            db.add(decision_record)
            db.commit()
            db.refresh(decision_record)

            approval_id = None
            approval_status = "NOT_REQUIRED"
            if decision_outcome == "REVIEW":
                approval_status = "PENDING"
                approval_req = models.ApprovalRequest(
                    decision_id=decision_record.id,
                    agent_id=agent.id,
                    amount=requested_amount,
                    reason=f"Policy '{policy_applied}' triggered review: {explanation}",
                    status="PENDING",
                    created_at=now
                )
                db.add(approval_req)
                db.commit()
                db.refresh(approval_req)
                approval_id = str(approval_req.id)

            # ----------------------------------------------------------------
            # STAGE 7: AUDIT EVENT RECORDING
            # ----------------------------------------------------------------
            audit_result = "SUCCESS" if decision_outcome == "ALLOW" else ("WARNING" if decision_outcome == "REVIEW" else "FAILURE")
            audit = models.AuditLog(
                org_id=agent.org_id,
                event_type=f"PACE_DECISION_{decision_outcome}",
                actor_type=actor_type,
                actor_id=actor_id,
                action=raw_action,
                resource=f"resource:{raw_resource}",
                result=audit_result,
                metadata_json={
                    "correlation_id": correlation_id,
                    "agent_code": agent.agent_code,
                    "decision": decision_outcome,
                    "decision_id": str(decision_record.id),
                    "approval_id": approval_id,
                    "risk_score": final_risk_score,
                    "policy_applied": policy_applied,
                    "policy_id": policy_id,
                    "rule_id": rule_id,
                    "sequence_indicators": {
                        "events_evaluated": sequence_indicators.events_evaluated,
                        "sequence_risk_delta": sequence_indicators.sequence_risk_delta,
                        "patterns_detected": [p.pattern_name for p in sequence_indicators.patterns_detected]
                    }
                }
            )
            db.add(audit)
            db.commit()

            return schemas.ActionControlEvaluationResponse(
                decision=decision_outcome,
                risk_score=final_risk_score,
                risk_level=risk_level,
                risk_scale="0-100 (LOW <=30, MEDIUM <=60, HIGH <=80, CRITICAL >80)",
                reason=explanation,
                policy_applied=policy_applied,
                policy_id=policy_id,
                rule_id=rule_id,
                risk_breakdown=risk_breakdown,
                sequence_indicators=sequence_indicators,
                approval_required=(decision_outcome == "REVIEW"),
                approval_status=approval_status,
                approval_id=approval_id,
                execution_gate_token=gate_token,
                agent_code=agent.agent_code,
                org_id=str(agent.org_id),
                action_type=raw_action,
                target_resource=raw_resource,
                correlation_id=correlation_id,
                evaluated_at=now
            )

        except Exception as ex:
            logger.error(f"[PACE] Evaluation failure (failing safely): {str(ex)}", exc_info=True)
            db.rollback()
            return self._build_fail_response(
                db=db,
                reason=f"Fail-Safe Refusal: Critical internal evaluation error: {str(ex)}",
                stage="INTERNAL_ERROR",
                request=request,
                correlation_id=correlation_id,
                agent=None,
                org_id="ERROR_SAFE_STATE"
            )

    def execute_action(
        self,
        db: Session,
        caller_entity: Any,
        request: schemas.ActionControlEvaluationRequest
    ) -> schemas.ActionControlExecuteResponse:
        """
        Enforces decisions strictly at the action execution boundary.
        - ALLOW: proceeds to real execution through Tool Proxy using single-use gate token.
        - REVIEW: does not execute; returns pending review state.
        - REFUSE: does not execute; returns blocked execution state.
        """
        eval_res = self.evaluate_action(db=db, caller_entity=caller_entity, request=request)

        if eval_res.decision == "REFUSE":
            return schemas.ActionControlExecuteResponse(
                evaluation=eval_res,
                executed=False,
                execution_status="BLOCKED",
                execution_result=None,
                error=f"Execution blocked: {eval_res.reason}"
            )

        if eval_res.decision == "REVIEW":
            return schemas.ActionControlExecuteResponse(
                evaluation=eval_res,
                executed=False,
                execution_status="PENDING_APPROVAL",
                execution_result=None,
                error="Execution withheld: Action requires human managerial approval before dispatch."
            )

        # Decision is ALLOW
        if not eval_res.execution_gate_token:
            return schemas.ActionControlExecuteResponse(
                evaluation=eval_res,
                executed=False,
                execution_status="EXECUTION_FAILED",
                execution_result=None,
                error="Execution gate token missing despite ALLOW decision."
            )

        # Resolve agent record for tool proxy
        agent = db.query(models.Agent).filter(models.Agent.agent_code == eval_res.agent_code).first()
        if not agent:
            return schemas.ActionControlExecuteResponse(
                evaluation=eval_res,
                executed=False,
                execution_status="EXECUTION_FAILED",
                execution_result=None,
                error=f"Agent '{eval_res.agent_code}' not found for execution dispatch."
            )

        # Dispatch real execution through Tool Proxy Gateway
        exec_payload = tool_proxy_service.execute_tool(
            db=db,
            agent=agent,
            gate_token=eval_res.execution_gate_token,
            tool_name=request.operation or request.action_type,
            parameters=request.parameters
        )

        success = exec_payload.get("success", False)
        status_label = "EXECUTED" if success else "EXECUTION_FAILED"

        return schemas.ActionControlExecuteResponse(
            evaluation=eval_res,
            executed=success,
            execution_status=status_label,
            execution_result=exec_payload,
            error=exec_payload.get("error") if not success else None
        )

    def _check_permission(
        self,
        granted_permissions: list,
        resource: str,
        target: Optional[str],
        action: str
    ) -> bool:
        req_action = action.upper().strip()
        req_res = resource.upper().strip()
        req_target = (target or "").upper().strip()

        for perm in granted_permissions:
            perm_action = perm.action.upper().strip()
            perm_res_type = perm.resource_type.upper().strip()
            perm_res_name = perm.resource_name.upper().strip()

            action_match = (perm_action == "*" or perm_action == req_action)
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

    def _build_fail_response(
        self,
        db: Session,
        reason: str,
        stage: str,
        request: schemas.ActionControlEvaluationRequest,
        correlation_id: str,
        agent: Optional[models.Agent] = None,
        org_id: str = "UNKNOWN"
    ) -> schemas.ActionControlEvaluationResponse:
        now = datetime.datetime.utcnow()
        agent_code = agent.agent_code if agent else (request.agent_code or request.agent_id or "UNKNOWN")
        effective_org_id = str(agent.org_id) if agent else org_id

        # Safely record refusal decision if agent exists
        if agent:
            try:
                dec = models.Decision(
                    agent_id=agent.id,
                    user_id=None,
                    intent_summary=request.prompt or f"{request.action_type} on {request.target_resource}",
                    action_requested=request.action_type or "UNKNOWN",
                    resource_target=request.target_resource or "UNKNOWN",
                    amount=float(request.amount or 0.0),
                    decision="REFUSE",
                    risk_score=85,
                    policy_name=f"GATE_CHECK_{stage}",
                    explanation=reason,
                    execution_status="BLOCKED",
                    timestamp=now
                )
                db.add(dec)

                audit = models.AuditLog(
                    org_id=agent.org_id,
                    event_type="PACE_DECISION_REFUSE",
                    actor_type="MACHINE",
                    actor_id=agent_code,
                    action=request.action_type or "UNKNOWN",
                    resource=f"resource:{request.target_resource or 'UNKNOWN'}",
                    result="FAILURE",
                    metadata_json={
                        "correlation_id": correlation_id,
                        "stage_failed": stage,
                        "reason": reason
                    }
                )
                db.add(audit)
                db.commit()
            except Exception as e:
                logger.warning(f"[PACE] Could not persist refusal record: {e}")
                db.rollback()

        return schemas.ActionControlEvaluationResponse(
            decision="REFUSE",
            risk_score=85,
            risk_level="CRITICAL",
            risk_scale="0-100 (LOW <=30, MEDIUM <=60, HIGH <=80, CRITICAL >80)",
            reason=reason,
            policy_applied=f"GATE_CHECK_{stage}",
            policy_id=None,
            rule_id=None,
            risk_breakdown={"mandatory_refusal": 85},
            sequence_indicators=schemas.SequenceIndicators(
                window_size=request.history_window_size or 10,
                window_seconds=request.history_window_seconds or 900,
                events_evaluated=0,
                missing_history=True,
                patterns_detected=[],
                sequence_risk_delta=0,
                explanation="Action refused prior to sequence evaluation.",
                features={}
            ),
            approval_required=False,
            approval_status="NOT_REQUIRED",
            approval_id=None,
            execution_gate_token=None,
            agent_code=agent_code,
            org_id=effective_org_id,
            action_type=request.action_type or "UNKNOWN",
            target_resource=request.target_resource or "UNKNOWN",
            correlation_id=correlation_id,
            evaluated_at=now
        )


predictive_action_control_engine = PredictiveActionControlEngine()
