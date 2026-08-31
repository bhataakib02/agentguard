import datetime
from typing import Dict, Any, Optional

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
        decision_outcome: str
    ) -> Dict[str, Any]:
        user_label = human_initiator_name if human_initiator_name else "Authenticated User"
        agent_label = f"{agent_code} ({agent_name})" if agent_code and agent_name else agent_code or "Agent"
        
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
            "causal_chain": [
                f"1. Human Initiator ({user_label}) issued command action: '{action_requested}'",
                f"2. Intent Engine parsed action: {action_requested}, amount: ₹{amount:,.2f}",
                f"3. Agent {agent_label} requested capability authority token",
                f"4. Policy Engine evaluated governance limits (Threshold cap: ₹5,000.00)",
                f"5. Risk & Security Engine outcome: {decision_outcome}",
                "6. Decision event recorded in immutable audit log"
            ],
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

provenance_engine = ProvenanceEngine()
