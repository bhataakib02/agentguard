"""
CrewAI Integration Middleware for AgentGuard
Wraps CrewAI tools, agents, and task pipelines with non-bypassable runtime governance.
"""

import functools
import logging
from typing import Callable, Any, Optional, Dict

from .client import AgentGuardClient
from .exceptions import AgentGuardGovernanceRefusal

logger = logging.getLogger("agentguard.crewai")


class CrewAIAgentGuardMiddleware:
    """
    Governance middleware for CrewAI agents and tools.
    
    Usage:
        client = AgentGuardClient(agent_code="AG-CREW-01", agent_key="ag_agent_...")
        guard = CrewAIAgentGuardMiddleware(client=client)
        
        @guard.guard_tool(tool_name="database_query")
        def run_database_query(query: str):
            return db.execute(query)
            
        # Or patch an entire Crew instance:
        # guard.patch_crew(my_crew)
    """

    def __init__(
        self,
        client: AgentGuardClient,
        raise_on_refusal: bool = True,
        scan_pii: bool = True,
        block_on_pii: bool = False
    ):
        self.client = client
        self.raise_on_refusal = raise_on_refusal
        self.scan_pii = scan_pii
        self.block_on_pii = block_on_pii

    def guard_tool(
        self,
        tool_name: Optional[str] = None,
        amount: float = 0.0
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator that wraps a tool function with AgentGuard pre-flight authorization.
        """
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            name = tool_name or func.__name__

            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                logger.info(f"AgentGuard CrewAI: Intercepting execution of tool '{name}'")
                
                # Check PII if enabled
                params = kwargs.copy()
                if args:
                    params["_args"] = list(args)

                if self.scan_pii:
                    mode = "BLOCK" if self.block_on_pii else "MASK"
                    scan_res = self.client.scan_pii(parameters=params, mode=mode)
                    if scan_res.get("pii_detected") and self.block_on_pii:
                        raise AgentGuardGovernanceRefusal(
                            explanation=f"CrewAI Tool '{name}' blocked: Sensitive PII detected in arguments.",
                            decision_id="PII_GUARDRAIL_BLOCK",
                            risk_score=95
                        )

                # Authorize via Kernel
                decision = self.client.authorize(
                    action_requested=name,
                    amount=amount,
                    parameters=params,
                    intent_name=f"crewai_tool_{name}"
                )

                if decision.get("decision") == "REFUSE" and self.raise_on_refusal:
                    raise AgentGuardGovernanceRefusal(
                        explanation=decision.get("explanation", f"Governance refused CrewAI tool '{name}'"),
                        decision_id=decision.get("decision_id"),
                        risk_score=decision.get("risk_score"),
                        decision_payload=decision
                    )

                # Execute original tool function
                return func(*args, **kwargs)

            return wrapper
        return decorator

    def patch_crew(self, crew: Any) -> None:
        """
        Reflectively inspects and wraps all tools registered on all agents in a CrewAI Crew.
        """
        agents = getattr(crew, "agents", [])
        for agent in agents:
            tools = getattr(agent, "tools", [])
            for i, tool in enumerate(tools):
                # If tool has run / _run method
                run_method = getattr(tool, "_run", None) or getattr(tool, "run", None)
                if run_method and callable(run_method):
                    tool_name = getattr(tool, "name", f"tool_{i}")
                    wrapped = self.guard_tool(tool_name=tool_name)(run_method)
                    if hasattr(tool, "_run"):
                        tool._run = wrapped
                    else:
                        tool.run = wrapped
        logger.info(f"AgentGuard CrewAI: Successfully patched {len(agents)} agent(s) in crew.")
