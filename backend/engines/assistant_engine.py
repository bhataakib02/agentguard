from typing import Dict, Any
from sqlalchemy.orm import Session
import models

class AssistantEngine:
    def process_query(self, query: str, db: Session) -> Dict[str, Any]:
        q_lower = query.lower()

        # 1. Suspicious / High Risk Agents Query
        if "suspicious" in q_lower or "high risk" in q_lower or "risky" in q_lower:
            high_risk_agents = db.query(models.Agent).filter(models.Agent.risk_score > 50).all()
            agent_list = [
                {
                    "agent_code": a.agent_code,
                    "name": a.name,
                    "risk_score": a.risk_score,
                    "status": a.status,
                    "department": a.department
                }
                for a in high_risk_agents
            ]

            if agent_list:
                first = agent_list[0]
                answer = f"Found {len(agent_list)} agent(s) exhibiting elevated risk scores (> 50). Agent {first['agent_code']} ({first['name']}) currently shows a risk score of {first['risk_score']}/100."
            else:
                answer = "No agents currently exhibit high risk scores (> 50). All registered AI employees are operating within normal parameters."

            return {
                "question": query,
                "answer": answer,
                "data": {"high_risk_agents": agent_list},
                "recommendations": [
                    "Review recent approval requests.",
                    "Verify capability token expiry settings.",
                    "Run automated Red-Team security tests."
                ]
            }

        # 2. Blocked / Refused Decisions Query
        elif "blocked" in q_lower or "refused" in q_lower or "why" in q_lower or "decision" in q_lower:
            recent_refusals = db.query(models.Decision).filter(models.Decision.decision.in_(["REFUSE", "REVIEW"])).all()
            dec_list = [
                {
                    "decision_id": d.id,
                    "agent_id": d.agent_id,
                    "action": d.action_requested,
                    "amount": d.amount,
                    "decision": d.decision,
                    "explanation": d.explanation
                }
                for d in recent_refusals[:5]
            ]

            if dec_list:
                latest = dec_list[0]
                answer = f"Found {len(recent_refusals)} decision(s) requiring review or refused. Most recent: Action '{latest['action']}' (₹{latest['amount']:,.2f}) outcome: {latest['decision']}. Explanation: {latest['explanation']}"
            else:
                answer = "No decisions have been blocked or escalated for human review yet."

            return {
                "question": query,
                "answer": answer,
                "data": {"recent_governance_decisions": dec_list},
                "recommendations": [
                    "Inspect Decision Black Box records.",
                    "Check Human Approval Queue for pending reviews.",
                    "Verify policy thresholds in Governance Policy Center."
                ]
            }

        # 3. Spending / Budget Query
        elif "spent" in q_lower or "cost" in q_lower or "spending" in q_lower or "budget" in q_lower:
            budgets = db.query(models.Budget).all()
            spend_data = [
                {
                    "agent_id": b.agent_id,
                    "daily_spend": b.current_daily_spend,
                    "monthly_spend": b.current_monthly_spend,
                    "daily_limit": b.daily_limit
                }
                for b in budgets
            ]
            total_monthly = sum(b.current_monthly_spend for b in budgets)

            answer = f"Monitored financial budgets for {len(budgets)} agent(s). Total monthly platform spend is ₹{total_monthly:,.2f}."

            return {
                "question": query,
                "answer": answer,
                "data": {"spending_overview": spend_data},
                "recommendations": [
                    "Consider routing low-priority queries to lighter LLM models.",
                    "Enforce strict per-transaction limits on autonomous execution."
                ]
            }

        # 4. Incident Query
        elif "incident" in q_lower or "security" in q_lower:
            incidents = db.query(models.SecurityIncident).all()
            inc_list = [
                {
                    "title": i.title,
                    "severity": i.severity,
                    "status": i.status
                }
                for i in incidents
            ]

            if inc_list:
                answer = f"Found {len(inc_list)} active or recorded security incident(s). Latest incident: '{inc_list[0]['title']}' [{inc_list[0]['status']}]."
            else:
                answer = "No security incidents recorded. All monitoring systems report clean operation."

            return {
                "question": query,
                "answer": answer,
                "data": {"security_incidents": inc_list},
                "recommendations": [
                    "Inspect Security Operations Center (SOC) feed.",
                    "Verify circuit breaker state machine status."
                ]
            }

        # 5. Default General Answer
        total_agents = db.query(models.Agent).count()
        total_decisions = db.query(models.Decision).count()
        return {
            "question": query,
            "answer": f"AgentGuard is actively monitoring {total_agents} AI employee(s) and has processed {total_decisions} total governance decision(s). All systems operating from live database records.",
            "data": {
                "active_agents": total_agents,
                "total_decisions_evaluated": total_decisions,
                "circuit_breaker_status": "HEALTHY"
            },
            "recommendations": [
                "Create a new AI agent from the Directory.",
                "Visit Live Activity Feed for real-time WebSocket events."
            ]
        }

assistant_engine = AssistantEngine()
