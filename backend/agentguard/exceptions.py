"""
AgentGuard SDK Exceptions
Defines standard errors, auth errors, and governance refusal exceptions.
"""

from typing import Optional, Dict, Any


class AgentGuardException(Exception):
    """Base exception for all AgentGuard SDK errors."""
    pass


class AgentGuardAuthError(AgentGuardException):
    """Raised when machine authentication fails or token is expired."""
    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message)
        self.status_code = status_code


class AgentGuardGovernanceRefusal(AgentGuardException):
    """
    Raised when AgentGuard Runtime Control Plane refuses an agent action.
    Contains decision metadata, explanation, and risk score.
    """
    def __init__(
        self,
        explanation: str,
        decision_id: Optional[str] = None,
        risk_score: Optional[int] = None,
        decision_payload: Optional[Dict[str, Any]] = None
    ):
        super().__init__(f"AgentGuard Refusal [Decision {decision_id}]: {explanation}")
        self.explanation = explanation
        self.decision_id = decision_id
        self.risk_score = risk_score
        self.decision_payload = decision_payload or {}


class AgentGuardCircuitBreakerError(AgentGuardException):
    """Raised when the agent's circuit breaker has been tripped due to consecutive failures."""
    def __init__(self, message: str, agent_code: Optional[str] = None):
        super().__init__(message)
        self.agent_code = agent_code


class AgentGuardExecutionError(AgentGuardException):
    """Raised when an egress tool proxy execution fails downstream."""
    def __init__(self, message: str, execution_id: Optional[str] = None, status_code: int = 502):
        super().__init__(message)
        self.execution_id = execution_id
        self.status_code = status_code
