import datetime
from typing import Dict, Any, Optional, List

class ProvenanceEngine:
    def build_causal_tree(
        self,
        decision_id: str,
        human_initiator_id: str,
        human_initiator_name: str,
        agent_code: str,
        agent_name: str,
        action_requested: str,
        tool_used: str,
        amount: float,
        decision_outcome: str,
        policy_name: Optional[str] = None,
        policy_id: Optional[str] = None,
        rule_id: Optional[str] = None,
        matched_rules: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        user_label = human_initiator_name if human_initiator_name else "Authenticated User"
        agent_label = f"{agent_code} ({agent_name})" if agent_code and agent_name else agent_code or "Agent"
        
        causal_steps = [
            f"1. Human Initiator ({user_label}) issued command action: '{action_requested}'",
            f"2. Intent Engine parsed action: {action_requested}, amount: ₹{amount:,.2f}",
            f"3. Agent {agent_label} requested capability authority token",
        ]

        if policy_name:
            causal_steps.append(f"4. Policy Engine evaluated database policy: '{policy_name}' (ID: {policy_id or 'N/A'}, Rule: {rule_id or 'N/A'})")
        else:
            causal_steps.append(f"4. Policy Engine evaluated runtime baseline governance limits")

        causal_steps.append(f"5. Governance evaluation outcome: {decision_outcome}")
        causal_steps.append("6. Decision event recorded in immutable audit log")

        return {
            "decision_id": decision_id,
            "root_initiator": {
                "type": "HUMAN",
                "id": human_initiator_id or "user-authenticated",
                "label": user_label
            },
            "primary_agent": {
                "type": "AGENT",
                "id": agent_code,
                "label": agent_label
            },
            "action_executed": action_requested,
            "tool_invoked": {
                "type": "TOOL",
                "id": tool_used,
                "label": f"{tool_used.capitalize()} Service API"
            },
            "target_resource": f"Resource Target: {tool_used}",
            "impact_amount": amount,
            "governance_decision": decision_outcome,
            "policy_applied": policy_name,
            "policy_id": policy_id,
            "rule_id": rule_id,
            "matched_rules_count": len(matched_rules) if matched_rules else 0,
            "causal_chain": causal_steps,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

provenance_engine = ProvenanceEngine()
