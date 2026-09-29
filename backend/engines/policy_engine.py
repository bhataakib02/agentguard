"""
Database-Driven Policy Engine for AgentGuard
Evaluates tenant-scoped governance policies and policy rules stored in the database.
Enforces strict tenant isolation, deterministic priority & conflict resolution,
and safe condition evaluation.
"""

from typing import Dict, Any, Optional, List
import logging
from sqlalchemy.orm import Session
from engines.policy_evaluator import evaluate_condition
import models

logger = logging.getLogger("agentguard.policy_engine")


class PolicyEngine:
    """
    Evaluates actions against database-driven policies and rules.
    Outcome hierarchy: REFUSE > REVIEW > ALLOW.
    """

    def evaluate_action(
        self,
        agent_name: str,
        action: str,
        resource: str,
        amount: float = 0.0,
        risk_score: int = 15,
        agent_status: str = "NORMAL",
        db: Optional[Session] = None,
        org_id: Optional[str] = None,
        agent_autonomy: str = "MEDIUM",
        agent_department: str = "Operations",
        agent_code: str = "",
        user_role: str = "USER",
        intent: str = ""
    ) -> Dict[str, Any]:
        """
        Main policy evaluation entrypoint.
        """
        # 1. Hard System Guard: Suspended or circuit-broken agents can NEVER execute actions
        if agent_status in ["SUSPENDED", "CIRCUIT_BREAK"]:
            return {
                "decision": "REFUSE",
                "policy_applied": "Runtime Circuit Breaker Policy",
                "policy_id": None,
                "rule_id": None,
                "reason": f"Agent '{agent_name}' is currently in {agent_status} state and cannot execute actions.",
                "color": "#E53935",
                "execution_status": "BLOCKED",
                "risk_score": risk_score,
                "matched_rules": [],
                "policies_evaluated_count": 0,
                "rules_evaluated_count": 0
            }

        # 2. Prepare Context for Rule Evaluation
        context = {
            "amount": float(amount or 0.0),
            "risk_score": int(risk_score or 0),
            "action": str(action or "").strip(),
            "intent": str(intent or "").strip(),
            "resource": str(resource or "").strip(),
            "agent_status": str(agent_status or "NORMAL").strip(),
            "agent_name": str(agent_name or "").strip(),
            "agent_code": str(agent_code or "").strip(),
            "agent_department": str(agent_department or "Operations").strip(),
            "agent_autonomy": str(agent_autonomy or "MEDIUM").strip(),
            "department": str(agent_department or "Operations").strip(),
            "status": str(agent_status or "NORMAL").strip(),
            "user_role": str(user_role or "USER").strip()
        }

        # 3. Load Active Tenant Policies from Database
        active_policies: List[models.Policy] = []
        if db is not None and org_id is not None:
            # Strictly filter by tenant org_id and status='ACTIVE'
            # Deterministic sorting: priority ASC (1 is highest), created_at ASC, id ASC
            active_policies = db.query(models.Policy).filter(
                models.Policy.org_id == org_id,
                models.Policy.status == "ACTIVE"
            ).order_by(
                models.Policy.priority.asc(),
                models.Policy.created_at.asc(),
                models.Policy.id.asc()
            ).all()

        matched_rules = []
        total_rules_evaluated = 0

        # 4. Evaluate Rules for Each Active Policy
        for policy in active_policies:
            # Query rules associated with this policy deterministically
            rules = db.query(models.PolicyRule).filter(
                models.PolicyRule.policy_id == policy.id
            ).order_by(models.PolicyRule.id.asc()).all()

            for rule in rules:
                total_rules_evaluated += 1
                matched, is_valid, err = evaluate_condition(rule.condition_expression, context)
                if matched:
                    matched_rules.append({
                        "policy_id": str(policy.id),
                        "policy_name": policy.name,
                        "policy_priority": policy.priority,
                        "policy_category": policy.category,
                        "rule_id": str(rule.id),
                        "condition": rule.condition_expression,
                        "decision_output": (rule.decision_output or "REVIEW").upper(),
                        "risk_delta": rule.risk_delta or 0,
                        "description": rule.description or f"Condition '{rule.condition_expression}' matched under policy '{policy.name}'."
                    })

        # 5. Deterministic Conflict Resolution (REFUSE > REVIEW > ALLOW)
        if matched_rules:
            # Separate by decision output
            refuse_matches = [r for r in matched_rules if r["decision_output"] == "REFUSE"]
            review_matches = [r for r in matched_rules if r["decision_output"] == "REVIEW"]
            allow_matches = [r for r in matched_rules if r["decision_output"] == "ALLOW"]

            if refuse_matches:
                primary_rule = refuse_matches[0]
                adj_risk = min(100, max(0, risk_score + primary_rule["risk_delta"]))
                return {
                    "decision": "REFUSE",
                    "policy_applied": primary_rule["policy_name"],
                    "policy_id": primary_rule["policy_id"],
                    "rule_id": primary_rule["rule_id"],
                    "reason": primary_rule["description"],
                    "color": "#E53935",
                    "execution_status": "BLOCKED",
                    "risk_score": adj_risk,
                    "matched_rules": matched_rules,
                    "policies_evaluated_count": len(active_policies),
                    "rules_evaluated_count": total_rules_evaluated
                }

            elif review_matches:
                primary_rule = review_matches[0]
                adj_risk = min(100, max(0, risk_score + primary_rule["risk_delta"]))
                return {
                    "decision": "REVIEW",
                    "policy_applied": primary_rule["policy_name"],
                    "policy_id": primary_rule["policy_id"],
                    "rule_id": primary_rule["rule_id"],
                    "reason": primary_rule["description"],
                    "color": "#F59A23",
                    "execution_status": "PENDING_APPROVAL",
                    "risk_score": adj_risk,
                    "matched_rules": matched_rules,
                    "policies_evaluated_count": len(active_policies),
                    "rules_evaluated_count": total_rules_evaluated
                }

            elif allow_matches:
                primary_rule = allow_matches[0]
                adj_risk = min(100, max(0, risk_score + primary_rule["risk_delta"]))
                return {
                    "decision": "ALLOW",
                    "policy_applied": primary_rule["policy_name"],
                    "policy_id": primary_rule["policy_id"],
                    "rule_id": primary_rule["rule_id"],
                    "reason": primary_rule["description"],
                    "color": "#2E9D50",
                    "execution_status": "EXECUTED",
                    "risk_score": adj_risk,
                    "matched_rules": matched_rules,
                    "policies_evaluated_count": len(active_policies),
                    "rules_evaluated_count": total_rules_evaluated
                }

        # 6. Default / Baseline Governance Rules (when no DB policies exist or none matched)
        # Production data deletion guard
        if "delete" in action.lower() and "production" in resource.lower():
            return {
                "decision": "REFUSE",
                "policy_applied": "Production Data Safety Policy",
                "policy_id": None,
                "rule_id": None,
                "reason": "Direct production database deletion is strictly prohibited for autonomous agents.",
                "color": "#E53935",
                "execution_status": "BLOCKED",
                "risk_score": max(risk_score, 85),
                "matched_rules": [],
                "policies_evaluated_count": len(active_policies),
                "rules_evaluated_count": total_rules_evaluated
            }

        # Hard financial ceiling (₹50,000)
        if amount > 50000:
            return {
                "decision": "REFUSE",
                "policy_applied": "Hard Financial Cap Policy",
                "policy_id": None,
                "rule_id": None,
                "reason": f"Requested transaction amount ₹{amount:,.2f} exceeds absolute autonomous maximum limit of ₹50,000.00.",
                "color": "#E53935",
                "execution_status": "BLOCKED",
                "risk_score": max(risk_score, 75),
                "matched_rules": [],
                "policies_evaluated_count": len(active_policies),
                "rules_evaluated_count": total_rules_evaluated
            }

        # Automatic approval threshold (₹5,000)
        if amount > 5000:
            return {
                "decision": "REVIEW",
                "policy_applied": "Financial Approval Policy (Threshold > ₹5,000)",
                "policy_id": None,
                "rule_id": None,
                "reason": f"Requested transaction amount ₹{amount:,.2f} exceeds automatic approval limit of ₹5,000.00. Human approval required.",
                "color": "#F59A23",
                "execution_status": "PENDING_APPROVAL",
                "risk_score": max(risk_score, 50),
                "matched_rules": [],
                "policies_evaluated_count": len(active_policies),
                "rules_evaluated_count": total_rules_evaluated
            }

        # High-risk escalation (risk_score > 60)
        if risk_score > 60:
            return {
                "decision": "REVIEW",
                "policy_applied": "High-Risk Escalation Policy",
                "policy_id": None,
                "rule_id": None,
                "reason": f"Action risk score ({risk_score}/100) exceeds maximum automated threshold (60). Manager review required.",
                "color": "#F59A23",
                "execution_status": "PENDING_APPROVAL",
                "risk_score": risk_score,
                "matched_rules": [],
                "policies_evaluated_count": len(active_policies),
                "rules_evaluated_count": total_rules_evaluated
            }

        # Default standard autonomous access
        return {
            "decision": "ALLOW",
            "policy_applied": "Standard Autonomous Access Policy",
            "policy_id": None,
            "rule_id": None,
            "reason": f"Action '{action}' on resource '{resource}' is safe, within financial bounds (₹{amount:,.2f} <= ₹5,000.00), and policy compliant.",
            "color": "#2E9D50",
            "execution_status": "EXECUTED",
            "risk_score": risk_score,
            "matched_rules": [],
            "policies_evaluated_count": len(active_policies),
            "rules_evaluated_count": total_rules_evaluated
        }


policy_engine = PolicyEngine()
