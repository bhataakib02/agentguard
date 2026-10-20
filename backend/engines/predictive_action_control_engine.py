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

        # Respect operator circuit-breaker resets: do not treat pre-restoration events as active refusal cascade
        cb = db.query(models.CircuitBreaker).filter(models.CircuitBreaker.agent_id == agent_id).first()
        if cb and cb.restored_at and cb.restored_at > cutoff_time:
            cutoff_time = cb.restored_at

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


class FutureActionRiskEstimator:
    """
    Estimates candidate next actions from available historical events, agent permissions,
    autonomy level, and policy constraints.
    - Uses real persisted history from models.Decision scoped strictly by agent_id and org_id.
    - Requires at least 3 historical events to produce statistical predictions; returns INSUFFICIENT_DATA otherwise.
    - Distinguishes OBSERVED facts from INFERRED possibilities.
    - Never fabricates events or presents heuristic scores as probabilities.
    - Distinguishes prediction confidence from risk severity.
    """

    MIN_HISTORY_SAMPLES = 3

    def estimate_future_actions(
        self,
        db: Session,
        agent_id: str,
        org_id: str,
        current_action: str,
        current_resource: str,
        autonomy_level: str,
        granted_permissions: List[models.Permission],
        history_window_size: int = 20
    ) -> schemas.FutureActionEstimation:
        # Strictly query decisions for this agent, scoped to tenant org
        recent_decisions = db.query(models.Decision).join(
            models.Agent, models.Decision.agent_id == models.Agent.id
        ).filter(
            models.Decision.agent_id == agent_id,
            models.Agent.org_id == org_id
        ).order_by(models.Decision.timestamp.desc()).limit(history_window_size).all()

        sample_size = len(recent_decisions)
        supporting_event_ids = [str(d.id) for d in recent_decisions]

        # Requirement: Return explicit INSUFFICIENT_DATA if < 3 historical observations
        if sample_size < self.MIN_HISTORY_SAMPLES:
            return schemas.FutureActionEstimation(
                status="INSUFFICIENT_DATA",
                confidence=0.0,
                sample_size=sample_size,
                candidates=[],
                contributing_factors=[
                    f"Sparse historical action trace ({sample_size} recorded events, minimum threshold is {self.MIN_HISTORY_SAMPLES})"
                ],
                supporting_events=supporting_event_ids,
                explanation=(
                    f"Insufficient historical observations ({sample_size}/{self.MIN_HISTORY_SAMPLES}) to compute "
                    "reliable statistical next-action predictions. Predictions withheld to prevent fabricated probabilities."
                )
            )

        # Reverse to chronological order for Markov transition analysis
        chronological = list(reversed(recent_decisions))

        # Build empirical 1st-order transition counts: P(action_{t+1} | action_t)
        transitions: Dict[str, Dict[str, int]] = {}
        for i in range(len(chronological) - 1):
            curr_a = (chronological[i].action_requested or "UNKNOWN").upper().strip()
            next_a = (chronological[i+1].action_requested or "UNKNOWN").upper().strip()
            if curr_a not in transitions:
                transitions[curr_a] = {}
            transitions[curr_a][next_a] = transitions[curr_a].get(next_a, 0) + 1

        curr_key = (current_action or "UNKNOWN").upper().strip()
        candidates: List[schemas.CandidateNextAction] = []
        contributing_factors = [
            f"Evaluated {sample_size} chronological decisions in tenant scope",
            f"Agent autonomy level: {autonomy_level}"
        ]

        if curr_key in transitions and transitions[curr_key]:
            # Observed transitions exist from this action
            total_curr_transitions = sum(transitions[curr_key].values())
            for next_action, count in sorted(transitions[curr_key].items(), key=lambda x: x[1], reverse=True)[:3]:
                prob = round(count / total_curr_transitions, 3)

                candidate_risk = risk_engine.calculate_risk(
                    agent_autonomy=autonomy_level,
                    action=next_action,
                    amount=0.0,
                    daily_budget=10000.0
                )
                pred_risk_score = candidate_risk.get("overall_score", 20)
                pred_risk_level = candidate_risk.get("level", "LOW")

                candidates.append(schemas.CandidateNextAction(
                    action=next_action,
                    resource=current_resource,
                    probability=prob,
                    confidence=round(min(0.95, 0.5 + (count / total_curr_transitions) * 0.4), 2),
                    transition_type="OBSERVED",
                    predicted_risk_score=pred_risk_score,
                    predicted_risk_level=pred_risk_level,
                    rationale=f"Observed {count}/{total_curr_transitions} times in historical trace following '{curr_key}'."
                ))

            confidence = round(min(0.90, 0.45 + (sample_size / 20.0) * 0.45), 2)
            explanation = (
                f"Statistical Markov estimation identified {len(candidates)} candidate next actions "
                f"with empirical transition probabilities derived from {sample_size} historical events."
            )
        else:
            # Current action has not been followed by other actions in history yet.
            contributing_factors.append(f"Action '{curr_key}' has no historical successors in this agent's trace.")

            permitted_actions = set()
            for p in granted_permissions:
                if p.is_allowed and p.action and p.action != "*":
                    permitted_actions.add(p.action.upper().strip())

            inferred_actions = [a for a in permitted_actions if a != curr_key][:2]

            for inf_action in inferred_actions:
                candidate_risk = risk_engine.calculate_risk(
                    agent_autonomy=autonomy_level,
                    action=inf_action,
                    amount=0.0,
                    daily_budget=10000.0
                )
                pred_risk_score = candidate_risk.get("overall_score", 25)
                pred_risk_level = candidate_risk.get("level", "LOW")

                candidates.append(schemas.CandidateNextAction(
                    action=inf_action,
                    resource=current_resource,
                    probability=None,  # Explicitly None - no fabricated probability for inferred actions!
                    confidence=0.40,
                    transition_type="INFERRED",
                    predicted_risk_score=pred_risk_score,
                    predicted_risk_level=pred_risk_level,
                    rationale=f"Inferred possibility based on granted agent permissions; no prior transition observed from '{curr_key}'."
                ))

            confidence = 0.40 if candidates else 0.20
            explanation = (
                f"No direct empirical transitions recorded from '{curr_key}'. "
                f"Generated {len(candidates)} inferred candidate actions from granted permissions without simulated probabilities."
            )

        return schemas.FutureActionEstimation(
            status="AVAILABLE",
            confidence=confidence,
            sample_size=sample_size,
            candidates=candidates,
            contributing_factors=contributing_factors,
            supporting_events=supporting_event_ids,
            explanation=explanation
        )


class ActionChainReachabilityAnalyzer:
    """
    Structured model / bounded graph evaluating whether a sequence of individually requested
    or permitted actions could reach a prohibited state.
    Enforces bounded depth (<= 4), bounded states (<= 50), and safe cycle handling.
    Evaluates:
    - Unauthorized resource access
    - Sensitive-data reconnaissance followed by attempted export (RECON_TO_EXFILTRATION)
    - Privilege escalation outside agent's scope
    - Repeated policy refusals followed by alternate evasive actions
    NEVER executes hypothetical actions during reachability analysis.
    """

    MAX_SEARCH_DEPTH = 4
    MAX_STATES = 50

    PROHIBITED_PATTERNS = {
        "UNAUTHORIZED_RESOURCE": {
            "policy": "Data Classification & Boundary Access Policy",
            "severity": "CRITICAL",
            "targets": ["INTERNAL_CREDENTIALS", "PAYMENT_KEYS", "PRODUCTION_AUTH", "ROOT_SECRETS"]
        },
        "RECON_TO_EXFILTRATION": {
            "policy": "Data Loss Prevention (DLP) & Exfiltration Prevention Policy",
            "severity": "HIGH",
            "actions": ["EXPORT", "DUMP", "DOWNLOAD", "EXFILTRATE", "SEND_EXTERNAL"]
        },
        "PRIVILEGE_ESCALATION": {
            "policy": "Principle of Least Privilege (PoLP) Enforcement Policy",
            "severity": "CRITICAL",
            "actions": ["GRANT_ROLE", "UPDATE_PERMISSIONS", "BECOME_ADMIN", "SUDO", "OVERRIDE_POLICY"]
        },
        "EVASION_POST_REFUSAL": {
            "policy": "Adversarial Action Evasion Countermeasure Policy",
            "severity": "HIGH",
            "actions": ["DROP_TABLE", "FORCE_DELETE", "DISABLE_AUDIT", "BYPASS_GATE", "TRUNCATE_TABLE"]
        }
    }

    def analyze_reachability(
        self,
        db: Session,
        agent: models.Agent,
        current_action: str,
        current_resource: str,
        granted_permissions: List[models.Permission],
        history_decisions: List[models.Decision],
        estimated_future: schemas.FutureActionEstimation
    ) -> schemas.ReachabilityAnalysis:
        states_explored = 0
        chains: List[schemas.ReachabilityChain] = []
        visited = set()

        curr_act_norm = (current_action or "").upper().strip()
        curr_res_norm = (current_resource or "").upper().strip()

        # Check Recent History for Observed Action Chains
        recent_recon = [
            d for d in history_decisions[:5]
            if any(k in (d.action_requested or "").upper() for k in ["READ", "QUERY", "SELECT", "LIST", "SCAN"])
            and any(r in (d.resource_target or "").upper() for r in ["DB", "DATABASE", "TABLE", "USER", "CUSTOMER"])
        ]

        if any(k in curr_act_norm for k in ["EXPORT", "DUMP", "DOWNLOAD", "EXFILTRATE", "DISPATCH_EXTERNAL"]) and recent_recon:
            chain_path = [f"{d.action_requested}:{d.resource_target}" for d in reversed(recent_recon[:2])] + [f"{current_action}:{current_resource}"]
            chains.append(schemas.ReachabilityChain(
                chain_id=f"reach_{uuid.uuid4().hex[:8]}",
                path=chain_path,
                path_type="OBSERVED",
                prohibited_target="DATA_EXFILTRATION_STATE",
                violating_policy=self.PROHIBITED_PATTERNS["RECON_TO_EXFILTRATION"]["policy"],
                risk_severity="HIGH",
                supporting_observations=[
                    f"Observed {len(recent_recon)} reconnaissance actions in recent history ({recent_recon[0].action_requested})",
                    f"Current action '{current_action}' initiates data aggregation/export on '{current_resource}'"
                ],
                uncertainty_notes="High certainty: prior steps are observed factual history, current step is in flight."
            ))

        recent_refusals = [d for d in history_decisions[:3] if d.decision == "REFUSE"]
        if len(recent_refusals) >= 2 and any(k in curr_act_norm for k in ["DROP", "DELETE", "FORCE", "OVERRIDE", "ALTER", "TRUNCATE"]):
            refusal_path = [f"REFUSED:{d.action_requested}" for d in reversed(recent_refusals)] + [f"{current_action}:{current_resource}"]
            chains.append(schemas.ReachabilityChain(
                chain_id=f"reach_{uuid.uuid4().hex[:8]}",
                path=refusal_path,
                path_type="OBSERVED",
                prohibited_target="ADVERSARIAL_POLICY_BYPASS_STATE",
                violating_policy=self.PROHIBITED_PATTERNS["EVASION_POST_REFUSAL"]["policy"],
                risk_severity="HIGH",
                supporting_observations=[
                    f"Agent experienced {len(recent_refusals)} consecutive refusals in recent sequence window",
                    f"Current action '{current_action}' attempts alternative disruptive operation"
                ],
                uncertainty_notes="High certainty: prior refusals are recorded facts."
            ))

        # Bounded Reachability Graph Search over Permitted / Inferred Actions
        frontier = [(curr_act_norm, curr_res_norm, [f"{curr_act_norm}:{curr_res_norm}"], 1)]
        visited.add((curr_act_norm, curr_res_norm))
        future_candidates_map = {c.action.upper().strip(): c for c in estimated_future.candidates}

        while frontier and states_explored < self.MAX_STATES:
            node_act, node_res, path, depth = frontier.pop(0)
            states_explored += 1

            # Terminal Check A: Privilege Escalation
            if any(k in node_act for k in self.PROHIBITED_PATTERNS["PRIVILEGE_ESCALATION"]["actions"]):
                chains.append(schemas.ReachabilityChain(
                    chain_id=f"reach_{uuid.uuid4().hex[:8]}",
                    path=path,
                    path_type="HYPOTHETICAL" if depth > 1 else "INFERRED",
                    prohibited_target="UNAUTHORIZED_PRIVILEGE_ESCALATION",
                    violating_policy=self.PROHIBITED_PATTERNS["PRIVILEGE_ESCALATION"]["policy"],
                    risk_severity="CRITICAL",
                    supporting_observations=[
                        f"Action '{node_act}' in reachability path targets administrative privilege escalation"
                    ],
                    uncertainty_notes=f"Depth {depth} search reached prohibited state. Hypothetical path modeled from agent graph."
                ))
                continue

            # Terminal Check B: Unauthorized Resource Boundary
            if any(k in node_res for k in self.PROHIBITED_PATTERNS["UNAUTHORIZED_RESOURCE"]["targets"]):
                chains.append(schemas.ReachabilityChain(
                    chain_id=f"reach_{uuid.uuid4().hex[:8]}",
                    path=path,
                    path_type="HYPOTHETICAL",
                    prohibited_target="UNAUTHORIZED_SECURITY_BOUNDARY_VIOLATION",
                    violating_policy=self.PROHIBITED_PATTERNS["UNAUTHORIZED_RESOURCE"]["policy"],
                    risk_severity="CRITICAL",
                    supporting_observations=[
                        f"Resource '{node_res}' in reachability path breaches tenant credential boundary"
                    ],
                    uncertainty_notes="Hypothetical path identified in structural reachability model."
                ))
                continue

            # Terminal Check C: Recon followed by Exfiltration
            if depth > 1 and any(k in node_act for k in self.PROHIBITED_PATTERNS["RECON_TO_EXFILTRATION"]["actions"]):
                cand = future_candidates_map.get(node_act)
                path_type = cand.transition_type if cand else "HYPOTHETICAL"
                chains.append(schemas.ReachabilityChain(
                    chain_id=f"reach_{uuid.uuid4().hex[:8]}",
                    path=path,
                    path_type=path_type,
                    prohibited_target="POTENTIAL_EXFILTRATION_TERMINAL_STATE",
                    violating_policy=self.PROHIBITED_PATTERNS["RECON_TO_EXFILTRATION"]["policy"],
                    risk_severity="HIGH",
                    supporting_observations=[
                        f"Action '{curr_act_norm}' transitions toward exfiltration action '{node_act}' at depth {depth}"
                    ],
                    uncertainty_notes=f"Path type '{path_type}': Model identified transition within bounded depth {depth}."
                ))
                continue

            # Expansion within depth limit
            if depth < self.MAX_SEARCH_DEPTH:
                successors = []
                for cand in estimated_future.candidates:
                    successors.append((cand.action.upper().strip(), node_res))

                for perm in granted_permissions[:10]:
                    if perm.is_allowed and perm.action and perm.action != "*":
                        successors.append((perm.action.upper().strip(), (perm.resource_name or node_res).upper().strip()))

                for next_a, next_r in successors:
                    if (next_a, next_r) not in visited and states_explored < self.MAX_STATES:
                        visited.add((next_a, next_r))
                        frontier.append((next_a, next_r, path + [f"{next_a}:{next_r}"], depth + 1))

        reachable = len(chains) > 0
        explanation = (
            f"Reachability search explored {states_explored} states (bounded depth {self.MAX_SEARCH_DEPTH}, limit {self.MAX_STATES}). "
            f"Found {len(chains)} reachable prohibited state chain(s)." if reachable else
            f"Reachability search explored {states_explored} states (bounded depth {self.MAX_SEARCH_DEPTH}, limit {self.MAX_STATES}). "
            "No prohibited terminal states reachable from current action context."
        )

        return schemas.ReachabilityAnalysis(
            prohibited_state_reachable=reachable,
            search_depth_limit=self.MAX_SEARCH_DEPTH,
            states_explored=states_explored,
            max_states_limit=self.MAX_STATES,
            chains=chains,
            explanation=explanation
        )


class MinimalInterventionPlanner:
    """
    Evaluates detected risk and reachability chains using the existing control vocabulary:
    - ALLOW_WITHOUT_INTERVENTION (level 0)
    - RESTRICT_SCOPE (level 1)
    - REQUIRE_APPROVAL (level 2)
    - DEFER_ACTION (level 3)
    - REFUSE_PROHIBITED (level 4)
    
    Invariants:
    1. Selects the LEAST DISRUPTIVE intervention that satisfies all mandatory policy constraints.
    2. A mandatory policy prohibition MUST NEVER be overridden by prediction, optimization,
       user preference, or low risk score.
    3. Clearly distinguishes recommended interventions from controls actually enforced by the
       execution gate:
       - ALLOW, REVIEW, REFUSE are ENFORCED.
       - RESTRICT_SCOPE, DEFER_ACTION are labeled as RECOMMENDED or PARTIAL if the execution proxy
         cannot directly enforce them without specialized parameter filters.
    4. Explains why the intervention was selected and why alternatives were rejected.
    """

    def plan_intervention(
        self,
        policy_decision: str,
        policy_name: str,
        risk_score: int,
        reachability: schemas.ReachabilityAnalysis,
        future_estimation: schemas.FutureActionEstimation
    ) -> schemas.InterventionPlan:
        # INVARIANT 1: Mandatory Policy Refusal is Absolute
        if policy_decision == "REFUSE":
            return schemas.InterventionPlan(
                selected_intervention="REFUSE_PROHIBITED",
                disruption_level=4,
                enforcement_status="ENFORCED",
                rationale=(
                    f"Mandatory policy refusal triggered by '{policy_name}'. "
                    "In accordance with security invariants, mandatory prohibitions cannot be overridden "
                    "by predictive modeling, low risk scores, or intervention optimization."
                ),
                rejected_alternatives=[
                    schemas.InterventionAlternative(
                        intervention="ALLOW_WITHOUT_INTERVENTION",
                        reason_rejected="Violates authoritative policy constraint; action is explicitly prohibited."
                    ),
                    schemas.InterventionAlternative(
                        intervention="RESTRICT_SCOPE",
                        reason_rejected="Scope restriction cannot satisfy an absolute policy refusal."
                    ),
                    schemas.InterventionAlternative(
                        intervention="REQUIRE_APPROVAL",
                        reason_rejected="Action is strictly prohibited by policy and not eligible for exception review."
                    ),
                    schemas.InterventionAlternative(
                        intervention="DEFER_ACTION",
                        reason_rejected="Action is prohibited regardless of deferral or cooldown delay."
                    )
                ],
                mandatory_constraint_satisfied=True
            )

        # INVARIANT 2: Mandatory Policy Review
        if policy_decision == "REVIEW":
            return schemas.InterventionPlan(
                selected_intervention="REQUIRE_APPROVAL",
                disruption_level=2,
                enforcement_status="ENFORCED",
                rationale=(
                    f"Policy '{policy_name}' mandates human review. "
                    "Requiring human approval satisfies the governance constraint while allowing potential execution upon authorization."
                ),
                rejected_alternatives=[
                    schemas.InterventionAlternative(
                        intervention="ALLOW_WITHOUT_INTERVENTION",
                        reason_rejected="Insufficient control: policy mandates explicit human supervisory sign-off."
                    ),
                    schemas.InterventionAlternative(
                        intervention="RESTRICT_SCOPE",
                        reason_rejected="Cannot replace required human supervisory verification."
                    ),
                    schemas.InterventionAlternative(
                        intervention="REFUSE_PROHIBITED",
                        reason_rejected="Excessively disruptive: action is reviewable under governance policy."
                    )
                ],
                mandatory_constraint_satisfied=True
            )

        # Policy decision is ALLOW: Now evaluate predictive risk and reachability
        critical_chains = [c for c in reachability.chains if c.risk_severity == "CRITICAL"]
        high_chains = [c for c in reachability.chains if c.risk_severity == "HIGH"]

        if critical_chains:
            return schemas.InterventionPlan(
                selected_intervention="REQUIRE_APPROVAL",
                disruption_level=2,
                enforcement_status="ENFORCED",
                rationale=(
                    f"Reachability analysis detected {len(critical_chains)} CRITICAL prohibited terminal state chain(s) "
                    f"[{critical_chains[0].prohibited_target}]. Escalating to human approval to verify intent."
                ),
                rejected_alternatives=[
                    schemas.InterventionAlternative(
                        intervention="ALLOW_WITHOUT_INTERVENTION",
                        reason_rejected="Unacceptable risk: critical prohibited terminal state reachable."
                    ),
                    schemas.InterventionAlternative(
                        intervention="RESTRICT_SCOPE",
                        reason_rejected="Scope restriction insufficient to neutralize critical reachability path."
                    ),
                    schemas.InterventionAlternative(
                        intervention="REFUSE_PROHIBITED",
                        reason_rejected="Approval gate provides necessary human verification with lower disruption than outright refusal."
                    )
                ],
                mandatory_constraint_satisfied=True
            )

        if high_chains or risk_score > 60:
            return schemas.InterventionPlan(
                selected_intervention="RESTRICT_SCOPE",
                disruption_level=1,
                enforcement_status="RECOMMENDED",
                rationale=(
                    f"Moderate-to-high sequence risk (score {risk_score}/100) or high reachability scenario detected. "
                    "Recommending parameter and resource scope tightening. (Marked as RECOMMENDED as parameter-level filtering is advisory)."
                ),
                rejected_alternatives=[
                    schemas.InterventionAlternative(
                        intervention="ALLOW_WITHOUT_INTERVENTION",
                        reason_rejected="Unmitigated risk: action sequence presents elevated exposure."
                    ),
                    schemas.InterventionAlternative(
                        intervention="REFUSE_PROHIBITED",
                        reason_rejected="Excessively disruptive when scope restriction mitigates the exposure."
                    )
                ],
                mandatory_constraint_satisfied=True
            )

        return schemas.InterventionPlan(
            selected_intervention="ALLOW_WITHOUT_INTERVENTION",
            disruption_level=0,
            enforcement_status="ENFORCED",
            rationale="Action satisfies all mandatory policy rules, permissions, and sequence risk constraints with zero prohibited reachability states.",
            rejected_alternatives=[
                schemas.InterventionAlternative(
                    intervention="REQUIRE_APPROVAL",
                    reason_rejected="Unnecessarily disruptive for low-risk, policy-compliant action."
                ),
                schemas.InterventionAlternative(
                    intervention="REFUSE_PROHIBITED",
                    reason_rejected="Action is fully permitted and poses minimal risk."
                )
            ],
            mandatory_constraint_satisfied=True
        )


class PredictiveActionControlEngine:
    """
    Predictive Action Control Engine (PACE) - Phase 2
    Canonical pipeline:
    1. Authenticate caller and resolve server-side agent identity.
    2. Load applicable organization, agent permissions, autonomy level, and policies.
    3. Evaluate mandatory authorization and policy constraints.
    4. Calculate sequence-aware risk assessment.
    5. Future-action risk estimation & Markov transition modeling.
    6. Action-chain reachability analysis with search bounds (depth <= 4, states <= 50).
    7. Minimal-intervention planning (least disruptive satisfying mandatory constraints).
    8. Apply deterministic decision rules (REFUSE > REVIEW > ALLOW).
    9. Produce structured decision and persist state.
    10. Record decision through immutable audit log.
    """

    def __init__(self):
        self.sequence_analyzer = ActionSequenceAnalyzer()
        self.future_estimator = FutureActionRiskEstimator()
        self.reachability_analyzer = ActionChainReachabilityAnalyzer()
        self.intervention_planner = MinimalInterventionPlanner()


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

                ident = target_agent_identifier.strip()
                if models.is_valid_uuid(ident):
                    agent = db.query(models.Agent).filter(
                        (models.Agent.id == ident) |
                        (models.Agent.agent_code == ident)
                    ).first()
                else:
                    agent = db.query(models.Agent).filter(
                        models.Agent.agent_code == ident
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
            # STAGE 5.5: PACE PHASE 2 PREDICTIVE INTELLIGENCE & INTERVENTION
            # ----------------------------------------------------------------
            # 1. Future Action Risk Estimation
            future_estimation = self.future_estimator.estimate_future_actions(
                db=db,
                agent_id=str(agent.id),
                org_id=str(agent.org_id),
                current_action=raw_action,
                current_resource=raw_resource,
                autonomy_level=agent.autonomy_level,
                granted_permissions=agent_permissions,
                history_window_size=window_size * 2
            )

            # 2. Action Chain Reachability Analysis
            recent_history_decisions = db.query(models.Decision).join(
                models.Agent, models.Decision.agent_id == models.Agent.id
            ).filter(
                models.Decision.agent_id == agent.id,
                models.Agent.org_id == agent.org_id
            ).order_by(models.Decision.timestamp.desc()).limit(15).all()

            reachability = self.reachability_analyzer.analyze_reachability(
                db=db,
                agent=agent,
                current_action=raw_action,
                current_resource=raw_resource,
                granted_permissions=agent_permissions,
                history_decisions=recent_history_decisions,
                estimated_future=future_estimation
            )

            # 3. Minimal Intervention Planning
            intervention_plan = self.intervention_planner.plan_intervention(
                policy_decision=decision_outcome,
                policy_name=policy_applied,
                risk_score=final_risk_score,
                reachability=reachability,
                future_estimation=future_estimation
            )

            # If reachability analysis detected critical prohibited terminal paths and policy was ALLOW,
            # escalate to REVIEW to require human oversight (Prediction augments risk; never grants permissions)
            if decision_outcome == "ALLOW" and intervention_plan.selected_intervention == "REQUIRE_APPROVAL":
                decision_outcome = "REVIEW"
                explanation = f"Predictive reachability escalated to human review: {intervention_plan.rationale}"

            # ----------------------------------------------------------------
            # STAGE 6: DECISION RECORDING & HUMAN APPROVAL WORKFLOW
            # ----------------------------------------------------------------
            gate_token = None
            if decision_outcome == "ALLOW":
                gate_token = f"gate_{uuid.uuid4().hex[:16]}"

            resolved_user_id = None
            if isinstance(caller_entity, models.User):
                resolved_user_id = caller_entity.id

            matched_tool = db.query(models.Tool).filter(
                (models.Tool.org_id == agent.org_id) | (models.Tool.org_id == None),
                (models.Tool.name == raw_action) |
                (models.Tool.name == raw_resource) |
                (models.Tool.name == raw_operation)
            ).first()

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
                tool_id=matched_tool.id if matched_tool else None,
                authorized_endpoint=matched_tool.endpoint if matched_tool else None,
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
                    },
                    "future_estimation": {
                        "status": future_estimation.status,
                        "confidence": future_estimation.confidence,
                        "candidates_count": len(future_estimation.candidates)
                    },
                    "reachability_analysis": {
                        "prohibited_state_reachable": reachability.prohibited_state_reachable,
                        "chains_count": len(reachability.chains)
                    },
                    "intervention_plan": {
                        "selected_intervention": intervention_plan.selected_intervention,
                        "disruption_level": intervention_plan.disruption_level,
                        "enforcement_status": intervention_plan.enforcement_status
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
                future_estimation=future_estimation,
                reachability_analysis=reachability,
                intervention_plan=intervention_plan,
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
        target_tool = request.operation or request.target_resource or request.action_type
        exec_payload = tool_proxy_service.execute_tool(
            db=db,
            agent=agent,
            gate_token=eval_res.execution_gate_token,
            tool_name=target_tool,
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
            future_estimation=schemas.FutureActionEstimation(
                status="INSUFFICIENT_DATA",
                confidence=0.0,
                sample_size=0,
                candidates=[],
                contributing_factors=["Evaluation halted by pre-flight gate refusal."],
                supporting_events=[],
                explanation="Action refused prior to predictive estimation."
            ),
            reachability_analysis=schemas.ReachabilityAnalysis(
                prohibited_state_reachable=True,
                search_depth_limit=4,
                states_explored=1,
                max_states_limit=50,
                chains=[],
                explanation="Action refused by mandatory authorization check."
            ),
            intervention_plan=schemas.InterventionPlan(
                selected_intervention="REFUSE_PROHIBITED",
                disruption_level=4,
                enforcement_status="ENFORCED",
                rationale=reason,
                rejected_alternatives=[
                    schemas.InterventionAlternative(
                        intervention="ALLOW_WITHOUT_INTERVENTION",
                        reason_rejected="Violates authoritative policy constraint; action is explicitly prohibited."
                    ),
                    schemas.InterventionAlternative(
                        intervention="RESTRICT_SCOPE",
                        reason_rejected="Scope restriction cannot satisfy an absolute policy refusal."
                    )
                ],
                mandatory_constraint_satisfied=True
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
