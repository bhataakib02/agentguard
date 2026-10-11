"""
Milestone 5 / Section 34 & 37: Real AI Admin Assistant Engine
Integrates live multi-tenant governance data with external LLM providers (OpenAI, Anthropic, Gemini)
with structured local synthesis fallback when API keys are not configured.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import httpx

import models
from config import settings

logger = logging.getLogger("agentguard.assistant")


class AssistantEngine:
    """
    Intelligent Governance Copilot Engine.
    Provides natural language querying over live tenant runtime databases.
    Connects to OpenAI / Anthropic / Gemini when keys are present,
    or falls back to high-fidelity structured analysis when not configured.
    """

    def process_query(self, query: str, db: Session, org_id: Optional[str] = None) -> Dict[str, Any]:
        # 1. Fetch Tenant Context Safely
        context = self._gather_tenant_context(db, org_id)

        # 2. Determine LLM Provider Strategy
        provider = self._resolve_provider()

        # 3. Call External LLM if Configured
        if provider == "OPENAI":
            res = self._call_openai(query, context)
            if res:
                return res
        elif provider == "ANTHROPIC":
            res = self._call_anthropic(query, context)
            if res:
                return res
        elif provider == "GEMINI":
            res = self._call_gemini(query, context)
            if res:
                return res

        # 4. Fallback / Default Local DB Synthesis Engine
        return self._local_synthesis(query, context)

    def _resolve_provider(self) -> str:
        """Determines the active LLM provider based on settings and available API keys."""
        configured = settings.LLM_PROVIDER.upper()
        if configured == "OPENAI" and settings.OPENAI_API_KEY:
            return "OPENAI"
        if configured == "ANTHROPIC" and settings.ANTHROPIC_API_KEY:
            return "ANTHROPIC"
        if configured == "GEMINI" and settings.GEMINI_API_KEY:
            return "GEMINI"

        # AUTO mode: select first available key
        if configured == "AUTO":
            if settings.OPENAI_API_KEY:
                return "OPENAI"
            if settings.ANTHROPIC_API_KEY:
                return "ANTHROPIC"
            if settings.GEMINI_API_KEY:
                return "GEMINI"

        return "NONE"

    def _gather_tenant_context(self, db: Session, org_id: Optional[str]) -> Dict[str, Any]:
        """Gathers tenant-scoped telemetry, agent profiles, decisions, and incidents."""
        # Query scopes
        agent_q = db.query(models.Agent)
        decision_q = db.query(models.Decision)
        budget_q = db.query(models.Budget)
        incident_q = db.query(models.SecurityIncident)
        circuit_q = db.query(models.CircuitBreaker)

        if org_id:
            agent_q = agent_q.filter(models.Agent.org_id == org_id)
            # Decision has no direct org_id — filter through Agent join
            decision_q = decision_q.join(models.Agent, models.Decision.agent_id == models.Agent.id).filter(
                models.Agent.org_id == org_id
            )
            incident_q = incident_q.filter(models.SecurityIncident.org_id == org_id)
            # CircuitBreaker has no direct org_id — join through Agent
            circuit_q = circuit_q.join(models.Agent).filter(models.Agent.org_id == org_id)
            # Budget joins agent
            budget_q = budget_q.join(models.Agent).filter(models.Agent.org_id == org_id)

        agents = agent_q.all()
        high_risk_agents = [a for a in agents if (a.risk_score or 0) > 50]
        recent_decisions = decision_q.order_by(models.Decision.executed_at.desc()).limit(15).all()
        refused_decisions = [d for d in recent_decisions if d.decision in ("REFUSE", "REVIEW")]
        budgets = budget_q.all()
        incidents = incident_q.order_by(models.SecurityIncident.created_at.desc()).limit(10).all()
        tripped_circuits = circuit_q.filter(models.CircuitBreaker.state == "TRIPPED").all()

        total_daily_spend = sum(float(b.current_daily_spend or 0.0) for b in budgets)
        total_monthly_spend = sum(float(b.current_monthly_spend or 0.0) for b in budgets)

        return {
            "org_id": org_id or "GLOBAL",
            "total_agents": len(agents),
            "active_agents": len([a for a in agents if a.status == "ACTIVE"]),
            "suspended_agents": len([a for a in agents if a.status == "SUSPENDED"]),
            "high_risk_agents": [
                {
                    "agent_code": a.agent_code,
                    "name": a.name,
                    "risk_score": a.risk_score,
                    "status": a.status,
                    "department": a.department
                }
                for a in high_risk_agents
            ],
            "recent_refusals": [
                {
                    "decision_id": d.id,
                    "agent_id": d.agent_id,
                    "action": d.action_requested,
                    "amount": float(d.amount or 0.0),
                    "decision": d.decision,
                    "explanation": d.explanation
                }
                for d in refused_decisions
            ],
            "financial_summary": {
                "monitored_budgets_count": len(budgets),
                "total_daily_spend": total_daily_spend,
                "total_monthly_spend": total_monthly_spend
            },
            "security_incidents": [
                {
                    "id": i.id,
                    "title": i.title,
                    "severity": i.severity,
                    "status": i.status
                }
                for i in incidents
            ],
            "tripped_circuit_breakers": [
                {"agent_id": c.agent_id, "state": c.state, "trigger_reason": c.trigger_reason}
                for c in tripped_circuits
            ]
        }

    def _call_openai(self, query: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Invokes OpenAI Chat Completions API with tenant governance grounding."""
        system_prompt = (
            "You are AgentGuard AI Governance Copilot, an enterprise runtime intelligence assistant. "
            "Analyze the tenant's current AI agents, risk scores, decisions, budgets, and security incidents. "
            "Always be factual, security-oriented, and refer directly to the live context provided. "
            "Return a JSON response with keys: 'answer' (string), 'data' (object or array of relevant entities), "
            "and 'recommendations' (list of strings)."
        )
        payload = {
            "model": settings.OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Tenant Context:\n{json.dumps(context, indent=2)}\n\nUser Question: {query}"}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    content = json.loads(data["choices"][0]["message"]["content"])
                    return {
                        "question": query,
                        "answer": content.get("answer", ""),
                        "data": content.get("data", {}),
                        "recommendations": content.get("recommendations", []),
                        "provider": "OPENAI",
                        "model": settings.OPENAI_MODEL,
                        "tokens_used": data.get("usage", {}).get("total_tokens", 0)
                    }
                else:
                    logger.warning(f"OpenAI call returned status {res.status_code}: {res.text}")
        except Exception as e:
            logger.error(f"OpenAI assistant call failed: {e}")
        return None

    def _call_anthropic(self, query: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Invokes Anthropic Messages API with tenant governance grounding."""
        system_prompt = (
            "You are AgentGuard AI Governance Copilot. Analyze the provided tenant context and user query. "
            "Respond in JSON format with keys: 'answer' (str), 'data' (dict or list), 'recommendations' (list of str)."
        )
        payload = {
            "model": settings.ANTHROPIC_MODEL,
            "max_tokens": 1024,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": f"Tenant Context:\n{json.dumps(context, indent=2)}\n\nQuestion: {query}"}
            ]
        }
        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    raw_text = data["content"][0]["text"]
                    parsed = json.loads(raw_text)
                    return {
                        "question": query,
                        "answer": parsed.get("answer", raw_text),
                        "data": parsed.get("data", {}),
                        "recommendations": parsed.get("recommendations", []),
                        "provider": "ANTHROPIC",
                        "model": settings.ANTHROPIC_MODEL,
                        "tokens_used": data.get("usage", {}).get("output_tokens", 0)
                    }
        except Exception as e:
            logger.error(f"Anthropic assistant call failed: {e}")
        return None

    def _call_gemini(self, query: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Invokes Google Gemini API with tenant governance grounding."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
        prompt = (
            f"You are AgentGuard AI Governance Copilot. Analyze this context:\n{json.dumps(context, indent=2)}\n\n"
            f"Answer the user query: {query}\n"
            f"Provide response strictly in JSON format with keys: 'answer', 'data', 'recommendations'."
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(raw_text)
                    return {
                        "question": query,
                        "answer": parsed.get("answer", raw_text),
                        "data": parsed.get("data", {}),
                        "recommendations": parsed.get("recommendations", []),
                        "provider": "GEMINI",
                        "model": settings.GEMINI_MODEL,
                        "tokens_used": 0
                    }
        except Exception as e:
            logger.error(f"Gemini assistant call failed: {e}")
        return None

    def _local_synthesis(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Truthful, deterministic local governance synthesis engine
        operating directly over tenant live database records when LLM provider is NOT_CONFIGURED.
        """
        q_lower = query.lower()

        # 1. High Risk / Suspicious Agents
        if any(term in q_lower for term in ("suspicious", "high risk", "risky", "risk score")):
            high_risk = context["high_risk_agents"]
            if high_risk:
                top = high_risk[0]
                answer = (
                    f"Found {len(high_risk)} agent(s) exhibiting elevated risk scores (> 50). "
                    f"Highest risk agent is {top['agent_code']} ({top['name']}) with score {top['risk_score']}/100 "
                    f"in department '{top['department']}' [Status: {top['status']}]."
                )
            else:
                answer = "No agents currently exhibit high risk scores (> 50). All registered AI employees are operating within normal baseline parameters."
            return {
                "question": query,
                "answer": answer,
                "data": {"high_risk_agents": high_risk},
                "recommendations": [
                    "Review recent approval requests for elevated agents.",
                    "Verify capability token expiry and permission scopes.",
                    "Run automated Red-Team security tests via the Security Center."
                ],
                "provider": "NOT_CONFIGURED (local_db_synthesis)",
                "model": "rule_based_synthesis"
            }

        # 2. Blocked / Refused Decisions
        if any(term in q_lower for term in ("blocked", "refused", "rejected", "why", "decision")):
            refusals = context["recent_refusals"]
            if refusals:
                latest = refusals[0]
                answer = (
                    f"Found {len(refusals)} recent decision(s) blocked or escalated for human review. "
                    f"Most recent refusal: Action '{latest['action']}' (Amount: ₹{latest['amount']:,.2f}) "
                    f"was marked {latest['decision']}. Reason: {latest['explanation']}."
                )
            else:
                answer = "No decisions have been refused or escalated for human review in recent activity."
            return {
                "question": query,
                "answer": answer,
                "data": {"recent_governance_decisions": refusals},
                "recommendations": [
                    "Inspect the Decision Black Box records for detailed telemetry.",
                    "Review pending items in the Human Approval Queue.",
                    "Verify policy thresholds in the Governance Policy Center."
                ],
                "provider": "NOT_CONFIGURED (local_db_synthesis)",
                "model": "rule_based_synthesis"
            }

        # 3. Budget & Spending
        if any(term in q_lower for term in ("spent", "cost", "spending", "budget", "finance")):
            fin = context["financial_summary"]
            answer = (
                f"Monitored financial limits across {fin['monitored_budgets_count']} agent budget(s). "
                f"Total daily spend is ₹{fin['total_daily_spend']:,.2f} and total monthly platform spend is ₹{fin['total_monthly_spend']:,.2f}."
            )
            return {
                "question": query,
                "answer": answer,
                "data": fin,
                "recommendations": [
                    "Ensure high-frequency agents have strict per-transaction budget limits.",
                    "Enable dynamic circuit breaker trip thresholds on rapid spending acceleration."
                ],
                "provider": "NOT_CONFIGURED (local_db_synthesis)",
                "model": "rule_based_synthesis"
            }

        # 4. Security Incidents & Circuit Breakers
        if any(term in q_lower for term in ("incident", "security", "attack", "circuit", "trip")):
            incidents = context["security_incidents"]
            circuits = context["tripped_circuit_breakers"]
            circuit_status = f"{len(circuits)} circuit breaker(s) TRIPPED" if circuits else "HEALTHY"
            if incidents:
                answer = f"Found {len(incidents)} security incident(s). Latest: '{incidents[0]['title']}' [{incidents[0]['severity']}]. Circuit breaker status: {circuit_status}."
            else:
                answer = f"No security incidents recorded. Circuit breakers are {circuit_status}."
            return {
                "question": query,
                "answer": answer,
                "data": {"incidents": incidents, "tripped_circuits": circuits},
                "recommendations": [
                    "Inspect the Security Operations Center (SOC) live feed.",
                    "Verify agent credentials and passport validity."
                ],
                "provider": "NOT_CONFIGURED (local_db_synthesis)",
                "model": "rule_based_synthesis"
            }

        # 5. Default General Overview
        tot = context["total_agents"]
        act = context["active_agents"]
        susp = context["suspended_agents"]
        answer = (
            f"AgentGuard is currently governing {tot} AI employee(s) ({act} active, {susp} suspended). "
            f"All operations are continuously monitored against active governance policies and cryptographic passports."
        )
        return {
            "question": query,
            "answer": answer,
            "data": {
                "total_agents": tot,
                "active_agents": act,
                "suspended_agents": susp,
                "circuit_breaker_status": "TRIPPED" if context["tripped_circuit_breakers"] else "HEALTHY"
            },
            "recommendations": [
                "Inspect the AI Agent Directory to manage employee lifecycles.",
                "Review the Live Activity Feed for real-time WebSocket events."
            ],
            "provider": "NOT_CONFIGURED (local_db_synthesis)",
            "model": "rule_based_synthesis"
        }


assistant_engine = AssistantEngine()
