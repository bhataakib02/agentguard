"""
Official AgentGuard Python Client
Provides synchronous HTTP client for AgentGuard machine identity,
runtime pre-flight authorization, egress tool proxy execution, and security intelligence.
"""

import json
import logging
from typing import Dict, Any, Optional
import requests

from .exceptions import (
    AgentGuardException,
    AgentGuardAuthError,
    AgentGuardGovernanceRefusal,
    AgentGuardCircuitBreakerError,
    AgentGuardExecutionError
)

logger = logging.getLogger("agentguard.client")


class AgentGuardClient:
    """
    Client for interacting with the AgentGuard Runtime Control Plane.
    
    Usage:
        client = AgentGuardClient(
            agent_code="AG-FIN-01",
            agent_key="ag_agent_...",
            base_url="http://localhost:8000"
        )
        
        # 1. Machine Authentication
        token = client.authenticate()
        
        # 2. Pre-flight Action Authorization
        decision = client.authorize(
            action_requested="execute_wire_transfer",
            amount=250.0,
            parameters={"recipient": "ACC-9921", "amount": 250.0}
        )
        
        # 3. Secure Tool Execution Proxy
        result = client.execute(
            tool_name="stripe_payout",
            parameters={"amount": 250.0},
            execution_gate_token=decision["execution_gate_token"]
        )
    """

    def __init__(
        self,
        agent_code: str,
        agent_key: str,
        base_url: str = "http://localhost:8000",
        org_id: Optional[str] = None,
        timeout: float = 10.0,
        raise_on_refusal: bool = True,
        session_token: Optional[str] = None,
        session: Optional[Any] = None
    ):
        self.agent_code = agent_code.strip()
        self.agent_key = agent_key.strip()
        self.base_url = base_url.rstrip("/")
        self.org_id = org_id
        self.timeout = timeout
        self.raise_on_refusal = raise_on_refusal
        self.session_token = session_token
        self.passport: Optional[Dict[str, Any]] = None
        self._session = session if session is not None else requests.Session()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """Closes the underlying HTTP session."""
        self._session.close()

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "X-Agent-Code": self.agent_code,
            "X-Agent-Key": self.agent_key,
        }
        if self.session_token:
            headers["Authorization"] = f"Bearer {self.session_token}"
        if self.org_id:
            headers["X-Org-Id"] = self.org_id
        return headers

    def authenticate(self) -> str:
        """
        Authenticates the agent against POST /api/runtime/auth.
        Acquires machine session JWT and asymmetric Ed25519 passport.
        """
        url = f"{self.base_url}/api/runtime/auth"
        payload = {
            "credential": self.agent_key,
            "agent_code": self.agent_code
        }
        try:
            res = self._session.post(url, json=payload, timeout=self.timeout)
            if res.status_code == 200:
                data = res.json()
                self.session_token = data.get("access_token")
                self.passport = data.get("passport")
                logger.info(f"AgentGuard: Authenticated agent {self.agent_code}")
                return self.session_token
            elif res.status_code in (401, 403):
                raise AgentGuardAuthError(f"Authentication failed: {res.text}", status_code=res.status_code)
            else:
                raise AgentGuardException(f"AgentGuard auth endpoint returned {res.status_code}: {res.text}")
        except requests.RequestException as e:
            raise AgentGuardException(f"Network error connecting to AgentGuard: {e}") from e

    def authorize(
        self,
        action_requested: str,
        amount: float = 0.0,
        target_resource: Optional[str] = None,
        intent_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        effective_prompt: Optional[str] = None,
        capability_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates an action against the full 15-stage AgentGuard Runtime Kernel.
        Calls POST /api/runtime/authorize.
        
        If decision is REFUSE and raise_on_refusal is True, raises AgentGuardGovernanceRefusal.
        Returns the full decision payload.
        """
        url = f"{self.base_url}/api/runtime/authorize"
        action_val = action_requested or intent_name or "EXECUTE"
        resource_val = target_resource or action_requested or "API"
        payload = {
            "action": action_val,
            "resource": resource_val,
            "target": target_resource,
            "parameters": parameters or {},
            "amount": amount,
            "prompt": effective_prompt,
            "capability_token": capability_token,
            "agent_code": self.agent_code
        }

        try:
            res = self._session.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
            
            # Handle automatic re-auth if token expired
            if res.status_code == 401 and self.session_token:
                logger.info("Session token expired, attempting re-authentication...")
                self.authenticate()
                res = self._session.post(url, headers=self._headers(), json=payload, timeout=self.timeout)

            if res.status_code == 200:
                data = res.json()
                decision = data.get("decision", "ALLOW")
                reason_val = data.get("reason") or data.get("explanation") or "Action refused by governance policy"
                if decision == "REFUSE" and self.raise_on_refusal:
                    raise AgentGuardGovernanceRefusal(
                        explanation=reason_val,
                        decision_id=data.get("decision_id"),
                        risk_score=data.get("risk_score"),
                        decision_payload=data
                    )
                return data
            elif res.status_code == 403 and "Circuit breaker" in res.text:
                raise AgentGuardCircuitBreakerError(res.text, agent_code=self.agent_code)
            elif res.status_code in (401, 403):
                raise AgentGuardAuthError(f"Authorization refused: {res.text}", status_code=res.status_code)
            else:
                raise AgentGuardException(f"AgentGuard authorize failed with status {res.status_code}: {res.text}")

        except requests.RequestException as e:
            raise AgentGuardException(f"Network error during authorize: {e}") from e

    def execute(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        execution_gate_token: str,
        action_intent: Optional[str] = None,
        call_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes an approved tool call via the Egress Tool Proxy Gateway.
        Calls POST /api/runtime/execute.
        """
        url = f"{self.base_url}/api/runtime/execute"
        payload = {
            "tool_name": tool_name,
            "parameters": parameters,
            "execution_gate_token": execution_gate_token
        }

        try:
            res = self._session.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
            if res.status_code == 200:
                return res.json()
            elif res.status_code in (400, 403):
                raise AgentGuardExecutionError(f"Tool execution gate refused: {res.text}", status_code=res.status_code)
            else:
                raise AgentGuardExecutionError(f"Tool proxy execution failed [{res.status_code}]: {res.text}", status_code=res.status_code)
        except requests.RequestException as e:
            raise AgentGuardException(f"Network error during execute: {e}") from e

    def invoke(
        self,
        action_requested: str,
        tool_name: str,
        parameters: Dict[str, Any],
        amount: float = 0.0,
        target_resource: Optional[str] = None,
        effective_prompt: Optional[str] = None,
        capability_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Unified atomic invocation: performs pre-flight authorization and egress tool execution in one step.
        Calls POST /api/runtime/invoke.
        """
        url = f"{self.base_url}/api/runtime/invoke"
        action_val = action_requested or "EXECUTE"
        resource_val = target_resource or tool_name or "TOOL"
        payload = {
            "action": action_val,
            "resource": resource_val,
            "tool_name": tool_name,
            "parameters": parameters,
            "amount": amount,
            "target": target_resource,
            "prompt": effective_prompt,
            "capability_token": capability_token,
            "agent_code": self.agent_code
        }

        try:
            res = self._session.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
            if res.status_code == 200:
                data = res.json()
                reason_val = data.get("reason") or data.get("explanation") or "Action refused by governance policy"
                if data.get("decision") == "REFUSE" and self.raise_on_refusal:
                    raise AgentGuardGovernanceRefusal(
                        explanation=reason_val,
                        decision_id=data.get("decision_id"),
                        risk_score=data.get("risk_score"),
                        decision_payload=data
                    )
                return data
            elif res.status_code in (401, 403):
                raise AgentGuardAuthError(f"Invoke refused: {res.text}", status_code=res.status_code)
            else:
                raise AgentGuardException(f"AgentGuard invoke failed [{res.status_code}]: {res.text}")
        except requests.RequestException as e:
            raise AgentGuardException(f"Network error during invoke: {e}") from e

    def scan_pii(
        self,
        text: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        mode: str = "MASK"
    ) -> Dict[str, Any]:
        """Scans and sanitizes sensitive data via POST /api/runtime/scan-pii."""
        url = f"{self.base_url}/api/runtime/scan-pii"
        payload = {
            "text": text,
            "payload": parameters,
            "mode": mode
        }
        try:
            res = self._session.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
            if res.status_code == 200:
                return res.json()
            else:
                raise AgentGuardException(f"Scan PII failed [{res.status_code}]: {res.text}")
        except requests.RequestException as e:
            raise AgentGuardException(f"Network error during scan_pii: {e}") from e

    def scan_output(
        self,
        text: str,
        grounding_context: Optional[str] = None,
        policy_mode: str = "BLOCK",
        toxicity_threshold: float = 50.0
    ) -> Dict[str, Any]:
        """
        Scans model/tool output for toxicity, threats, and factual hallucination.
        Calls POST /api/runtime/scan-output.
        """
        url = f"{self.base_url}/api/runtime/scan-output"
        payload = {
            "text": text,
            "grounding_context": grounding_context,
            "policy_mode": policy_mode,
            "toxicity_threshold": toxicity_threshold
        }
        try:
            res = self._session.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
            if res.status_code == 200:
                return res.json()
            else:
                raise AgentGuardException(f"Scan output failed [{res.status_code}]: {res.text}")
        except requests.RequestException as e:
            raise AgentGuardException(f"Network error during scan_output: {e}") from e

    def heartbeat(
        self,
        status: str = "HEALTHY",
        session_token_jti: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sends an agent liveness heartbeat.
        Calls POST /api/runtime/heartbeat.
        """
        url = f"{self.base_url}/api/runtime/heartbeat"
        payload = {
            "status": status,
            "session_token_jti": session_token_jti,
            "metrics": metrics or {}
        }
        try:
            res = self._session.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
            if res.status_code == 200:
                return res.json()
            else:
                raise AgentGuardException(f"Heartbeat failed [{res.status_code}]: {res.text}")
        except requests.RequestException as e:
            raise AgentGuardException(f"Network error during heartbeat: {e}") from e

    def execute_sandbox(
        self,
        code: str,
        execution_gate_token: str,
        language: str = "python",
        tool_name: str = "python_sandbox",
        stdin: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
        network_enabled: bool = False,
        env_vars: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Executes untrusted code within an external isolated sandbox environment.
        Enforces pre-flight gate token validation, resource limits, and output sanitization.
        Calls POST /api/runtime/sandbox/execute.
        """
        url = f"{self.base_url}/api/runtime/sandbox/execute"
        payload = {
            "execution_gate_token": execution_gate_token,
            "tool_name": tool_name,
            "language": language,
            "code": code,
            "stdin": stdin,
            "parameters": parameters or {},
            "timeout_seconds": timeout_seconds,
            "network_enabled": network_enabled,
            "env_vars": env_vars or {}
        }
        try:
            res = self._session.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
            if res.status_code == 200:
                return res.json()
            elif res.status_code in (400, 403, 404):
                raise AgentGuardExecutionError(f"Sandbox execution rejected [{res.status_code}]: {res.text}", status_code=res.status_code)
            elif res.status_code == 503:
                raise AgentGuardException(f"Sandbox provider unavailable or not configured [{res.status_code}]: {res.text}")
            else:
                raise AgentGuardException(f"Sandbox execution failed [{res.status_code}]: {res.text}")
        except requests.RequestException as e:
            raise AgentGuardException(f"Network error during execute_sandbox: {e}") from e

    def get_sandbox_status(self) -> Dict[str, Any]:
        """
        Queries operational health, provider type, and resource boundaries of the sandbox runtime.
        Calls GET /api/runtime/sandbox/status.
        """
        url = f"{self.base_url}/api/runtime/sandbox/status"
        try:
            res = self._session.get(url, headers=self._headers(), timeout=self.timeout)
            if res.status_code == 200:
                return res.json()
            else:
                raise AgentGuardException(f"Failed to retrieve sandbox status [{res.status_code}]: {res.text}")
        except requests.RequestException as e:
            raise AgentGuardException(f"Network error during get_sandbox_status: {e}") from e

    def get_sandbox_job(self, job_id: str) -> Dict[str, Any]:
        """
        Retrieves execution logs, resource usage, and artifacts for a sandbox job.
        Calls GET /api/runtime/sandbox/jobs/{job_id}.
        """
        url = f"{self.base_url}/api/runtime/sandbox/jobs/{job_id}"
        try:
            res = self._session.get(url, headers=self._headers(), timeout=self.timeout)
            if res.status_code == 200:
                return res.json()
            elif res.status_code == 404:
                raise AgentGuardException(f"Sandbox job '{job_id}' not found.")
            else:
                raise AgentGuardException(f"Failed to retrieve sandbox job [{res.status_code}]: {res.text}")
        except requests.RequestException as e:
            raise AgentGuardException(f"Network error during get_sandbox_job: {e}") from e

    def cancel_sandbox_job(self, job_id: str) -> Dict[str, Any]:
        """
        Cancels an active sandbox job and triggers immediate resource cleanup.
        Calls POST /api/runtime/sandbox/jobs/{job_id}/cancel.
        """
        url = f"{self.base_url}/api/runtime/sandbox/jobs/{job_id}/cancel"
        try:
            res = self._session.post(url, headers=self._headers(), timeout=self.timeout)
            if res.status_code == 200:
                return res.json()
            else:
                raise AgentGuardException(f"Failed to cancel sandbox job [{res.status_code}]: {res.text}")
        except requests.RequestException as e:
            raise AgentGuardException(f"Network error during cancel_sandbox_job: {e}") from e



