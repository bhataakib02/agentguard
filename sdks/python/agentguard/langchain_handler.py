"""
LangChain Integration Handler for AgentGuard
Intercepts LLM tool executions, validates parameters against the AgentGuard Runtime Kernel,
and prevents unauthorized tool actions before they run.
"""

import json
import logging
from typing import Dict, Any, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.callbacks import BaseCallbackHandler
else:
    try:
        from langchain_core.callbacks import BaseCallbackHandler
    except ImportError:
        class BaseCallbackHandler:
            """Fallback callback handler base class when langchain-core is not installed."""
            pass

from .client import AgentGuardClient
from .exceptions import AgentGuardGovernanceRefusal

logger = logging.getLogger("agentguard.langchain")


class LangChainAgentGuardHandler(BaseCallbackHandler):
    """
    LangChain Callback Handler that injects AgentGuard runtime governance.
    
    Usage:
        client = AgentGuardClient(agent_code="AG-LANG-01", agent_key="ag_agent_...")
        handler = LangChainAgentGuardHandler(client=client)
        
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            callbacks=[handler]
        )
    """

    def __init__(
        self,
        client: AgentGuardClient,
        raise_on_refusal: bool = True,
        scan_pii_on_input: bool = True,
        block_on_pii: bool = False,
        default_amount: float = 0.0
    ):
        super().__init__()
        self.client = client
        self.raise_on_refusal = raise_on_refusal
        self.scan_pii_on_input = scan_pii_on_input
        self.block_on_pii = block_on_pii
        self.default_amount = default_amount
        self.last_decision: Optional[Dict[str, Any]] = None
        self.execution_gate_tokens: Dict[str, str] = {}

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: Optional[Any] = None,
        parent_run_id: Optional[Any] = None,
        tags: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None,
        inputs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Intercepts tool execution *before* the tool executes.
        Evaluates the action against the AgentGuard runtime authorization kernel.
        """
        tool_name = serialized.get("name") or serialized.get("id", ["unknown"])[-1]
        
        # Parse inputs
        parsed_params = {}
        if inputs and isinstance(inputs, dict):
            parsed_params = inputs
        elif input_str:
            try:
                parsed_params = json.loads(input_str)
                if not isinstance(parsed_params, dict):
                    parsed_params = {"input": parsed_params}
            except (json.JSONDecodeError, TypeError):
                parsed_params = {"input": input_str}

        logger.info(f"AgentGuard LangChain: Intercepting tool '{tool_name}' with parameters {parsed_params}")

        # Optional PII Scan
        if self.scan_pii_on_input:
            scan_mode = "BLOCK" if self.block_on_pii else "MASK"
            pii_res = self.client.scan_pii(text=input_str, parameters=parsed_params, mode=scan_mode)
            # Backend returns has_pii (not pii_detected)
            if (pii_res.get("has_pii") or pii_res.get("pii_detected")) and self.block_on_pii:
                types_found = [f.get("pii_type", f.get("type", "PII")) for f in pii_res.get("findings", [])]
                raise AgentGuardGovernanceRefusal(
                    explanation=f"Action blocked: PII detected in tool inputs ({', '.join(types_found) if types_found else 'sensitive data'})",
                    decision_id="PII_GUARDRAIL_BLOCK",
                    risk_score=95
                )

        # Pre-flight Authorization
        decision = self.client.authorize(
            action_requested=tool_name,
            amount=self.default_amount,
            target_resource=None,
            intent_name=f"tool_execution_{tool_name}",
            parameters=parsed_params,
            effective_prompt=input_str
        )

        self.last_decision = decision
        if run_id and decision.get("execution_gate_token"):
            self.execution_gate_tokens[str(run_id)] = decision["execution_gate_token"]

        if decision.get("decision") == "REFUSE" and self.raise_on_refusal:
            raise AgentGuardGovernanceRefusal(
                explanation=decision.get("explanation", f"Governance refused tool {tool_name}"),
                decision_id=decision.get("decision_id"),
                risk_score=decision.get("risk_score"),
                decision_payload=decision
            )

        return decision

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: Optional[Any] = None,
        parent_run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        """Recorded upon successful tool completion."""
        rid = str(run_id) if run_id else None
        if rid and rid in self.execution_gate_tokens:
            del self.execution_gate_tokens[rid]
        logger.debug(f"AgentGuard LangChain: Tool execution completed for run {rid}")

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: Optional[Any] = None,
        parent_run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        """Recorded upon tool error."""
        rid = str(run_id) if run_id else None
        if rid and rid in self.execution_gate_tokens:
            del self.execution_gate_tokens[rid]
        logger.warning(f"AgentGuard LangChain: Tool execution error for run {rid}: {error}")
