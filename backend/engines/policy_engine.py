from typing import Dict, Any

class PolicyEngine:
    def evaluate_action(
        self,
        agent_name: str,
        action: str,
        resource: str,
        amount: float,
        risk_score: int,
        agent_status: str
    ) -> Dict[str, Any]:
        if agent_status in ["SUSPENDED", "CIRCUIT_BREAK"]:
            return {
                "decision": "REFUSE",
                "policy_applied": "Runtime Circuit Breaker Policy",
                "reason": f"Agent '{agent_name}' is currently in {agent_status} state and cannot execute actions.",
                "color": "#E53935",
                "execution_status": "BLOCKED"
            }

        if "delete" in action and "production" in resource:
            return {
                "decision": "REFUSE",
                "policy_applied": "Production Data Safety Policy",
                "reason": "Direct production database deletion is strictly prohibited for autonomous agents.",
                "color": "#E53935",
                "execution_status": "BLOCKED"
            }

        if amount > 50000:
            return {
                "decision": "REFUSE",
                "policy_applied": "Hard Financial Cap Policy",
                "reason": f"Requested transaction amount ₹{amount:,.2f} exceeds absolute autonomous maximum limit of ₹50,000.00.",
                "color": "#E53935",
                "execution_status": "BLOCKED"
            }

        if amount > 5000:
            return {
                "decision": "REVIEW",
                "policy_applied": "Financial Approval Policy (Threshold > ₹5,000)",
                "reason": f"Requested transaction amount ₹{amount:,.2f} exceeds automatic approval limit of ₹5,000.00. Human approval required.",
                "color": "#F59A23",
                "execution_status": "PENDING_APPROVAL"
            }

        if risk_score > 60:
            return {
                "decision": "REVIEW",
                "policy_applied": "High-Risk Escalation Policy",
                "reason": f"Action risk score ({risk_score}/100) exceeds maximum automated threshold (60). Manager review required.",
                "color": "#F59A23",
                "execution_status": "PENDING_APPROVAL"
            }

        return {
            "decision": "ALLOW",
            "policy_applied": "Standard Autonomous Access Policy",
            "reason": f"Action '{action}' on resource '{resource}' is safe, within financial bounds (₹{amount:,.2f} <= ₹5,000.00), and policy compliant.",
            "color": "#2E9D50",
            "execution_status": "EXECUTED"
        }

policy_engine = PolicyEngine()
