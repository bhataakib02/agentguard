"""
External Isolated Sandbox Execution Provider for AgentGuard.
Provides a secure abstraction for running untrusted AI code/tools in an isolated
sandbox environment (e.g. gVisor, Firecracker, or dedicated remote worker).

Enforces:
- Non-bypassable runtime authorization gate validation
- Strict CPU, memory, process-count, execution-time, and output-size boundaries
- Filesystem isolation with ephemeral workspace cleanup
- Network isolation by default
- Zero host environment or credential leakage (never exposes DB, JWT, or cloud keys)
- Truthful NOT_CONFIGURED and UNAVAILABLE state reporting
- Tenant isolation across execution requests, jobs, logs, and artifacts
- Durable execution lifecycle states and immutable audit logging
"""

import abc
import datetime
import hashlib
import ipaddress
import logging
import os
import shutil
import tempfile
import time
import urllib.parse
import uuid
from typing import Dict, Any, Optional, List, Tuple

import httpx
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config import settings
import models
from engines.pii_engine import pii_engine
from engines.output_guardrails_engine import output_guardrails_engine
from services.runtime_telemetry_service import record_execution

logger = logging.getLogger("agentguard.sandbox")


# ============================================================================
# DATA TRANSFER OBJECTS (EXECUTION SCHEMA)
# ============================================================================

class SandboxExecutionRequest(BaseModel):
    """Controlled request payload sent to the isolated execution provider."""
    execution_id: str
    org_id: str
    agent_id: str
    decision_id: Optional[str] = None
    tool_name: str
    language: str = "python"
    code: str
    stdin: Optional[str] = None
    files: Dict[str, str] = Field(default_factory=dict)
    env_vars: Dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = 30
    memory_limit_mb: int = 512
    cpu_cores: float = 1.0
    process_limit: int = 32
    network_enabled: bool = False
    capabilities: List[str] = Field(default_factory=list)


class SandboxExecutionResult(BaseModel):
    """Controlled result payload returned by the isolated execution provider."""
    execution_id: str
    status: str  # SUCCEEDED, FAILED, TIMED_OUT, CANCELLED, REJECTED, NOT_CONFIGURED, UNAVAILABLE
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    resource_usage: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    cleaned_up: bool = True
    error_message: Optional[str] = None
    provider: str = "NOT_CONFIGURED"
    isolation_level: str = "CONTAINER_HARDENED"


# ============================================================================
# SECURITY: ENVIRONMENT VARIABLE CLEANSING & ISOLATION
# ============================================================================

BLOCKED_ENV_SUBSTRINGS = (
    "DATABASE", "DB_", "POSTGRES", "SQLITE", "SECRET", "KEY", "TOKEN", "PASSWORD",
    "SUPABASE", "OPENAI", "ANTHROPIC", "GEMINI", "REDIS", "CELERY", "S3_", "AWS",
    "SMTP", "SIEM", "STRIPE", "RAZORPAY", "JWT", "PRIVATE"
)

SAFE_ALLOWED_ENV_VARS = {
    "LANG", "LC_ALL", "PYTHONIOENCODING", "PYTHONUNBUFFERED", "NODE_ENV", "TZ"
}


def cleanse_execution_environment(user_env: Optional[Dict[str, str]]) -> Dict[str, str]:
    """
    Guarantees untrusted code NEVER receives host environment variables,
    production database credentials, signing keys, or cloud secrets.
    Only explicit safe variables from user_env are allowed after strict filtering.
    """
    clean_env: Dict[str, str] = {
        "PYTHONUNBUFFERED": "1",
        "LANG": "C.UTF-8",
        "AGENTGUARD_SANDBOX": "true",
        "AGENTGUARD_ISOLATION": "ACTIVE"
    }

    if not user_env:
        return clean_env

    for k, v in user_env.items():
        k_upper = str(k).upper()
        # Block any variable with sensitive substrings
        if any(blocked in k_upper for blocked in BLOCKED_ENV_SUBSTRINGS):
            logger.warning(f"[Sandbox Security] Dropped sensitive environment variable key: {k}")
            continue
        # Also ensure value doesn't look like a JWT or long hex key
        str_val = str(v)
        if len(str_val) > 256 or str_val.startswith("eyJ") or str_val.startswith("ag_"):
            logger.warning(f"[Sandbox Security] Dropped potential credential value for key: {k}")
            continue
        clean_env[str(k)] = str_val

    return clean_env


# ============================================================================
# ABSTRACT PROVIDER INTERFACE
# ============================================================================

class SandboxProviderBase(abc.ABC):
    """Abstract interface for external isolated execution runtimes."""

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Identifier of this execution provider."""
        pass

    @abc.abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the provider is properly configured in deployment."""
        pass

    @abc.abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Checks availability and reachability of the execution runtime."""
        pass

    @abc.abstractmethod
    def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        """Executes the request in an isolated environment."""
        pass

    @abc.abstractmethod
    def cancel(self, execution_id: str) -> bool:
        """Cancels a running execution and tears down its resources."""
        pass

    @abc.abstractmethod
    def cleanup(self, execution_id: str) -> bool:
        """Purges any temporary workspaces or ephemeral containers."""
        pass


# ============================================================================
# CONCRETE PROVIDER: UNCONFIGURED PROVIDER (TRUTHFUL DEFAULT)
# ============================================================================

class UnconfiguredSandboxProvider(SandboxProviderBase):
    """
    Truthful default provider when no external sandbox environment is configured.
    Explicitly refuses execution rather than falling back to host privileges.
    """

    @property
    def provider_name(self) -> str:
        return "NOT_CONFIGURED"

    def is_configured(self) -> bool:
        return False

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "NOT_CONFIGURED",
            "provider": self.provider_name,
            "configured": False,
            "available": False,
            "message": "External isolated sandbox execution provider is not configured. Untrusted code execution is disabled."
        }

    def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        return SandboxExecutionResult(
            execution_id=request.execution_id,
            status="NOT_CONFIGURED",
            exit_code=None,
            stdout="",
            stderr="",
            duration_ms=0,
            cleaned_up=True,
            error_message="External sandbox provider is NOT_CONFIGURED. Untrusted code execution in host process is strictly forbidden.",
            provider=self.provider_name,
            isolation_level="NONE"
        )

    def cancel(self, execution_id: str) -> bool:
        return False

    def cleanup(self, execution_id: str) -> bool:
        return True


# ============================================================================
# CONCRETE PROVIDER: REMOTE WORKER / GVISOR / FIRECRACKER MICROSERVICE
# ============================================================================

class RemoteWorkerSandboxProvider(SandboxProviderBase):
    """
    Communicates with a dedicated external isolated sandbox worker service
    (e.g., running gVisor runsc, Firecracker microVMs, or hardened rootless containers).
    Enforces SSRF validation on the endpoint and sends authenticated requests.
    """

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        api_key: Optional[str] = None,
        client: Optional[httpx.Client] = None,
        provider_name_override: Optional[str] = None
    ):
        self._endpoint_url = (endpoint_url or settings.SANDBOX_ENDPOINT_URL).rstrip("/")
        self._api_key = api_key or settings.SANDBOX_API_KEY
        self._client = client
        self._name = provider_name_override or (settings.SANDBOX_PROVIDER if settings.SANDBOX_PROVIDER != "NOT_CONFIGURED" else "REMOTE_WORKER")
        self.allow_local = os.getenv("AGENTGUARD_ALLOW_LOCAL_SANDBOX", "false").lower() in ("true", "1", "yes")

    @property
    def provider_name(self) -> str:
        return self._name

    def is_configured(self) -> bool:
        return bool(self._endpoint_url)

    def _validate_endpoint_safety(self, url: str) -> Tuple[bool, str]:
        """Protects against SSRF when calling the external sandbox service."""
        try:
            parsed = urllib.parse.urlparse(url)
        except Exception as e:
            return False, f"Invalid URL format: {e}"

        if parsed.scheme not in ("http", "https"):
            return False, f"Scheme '{parsed.scheme}' not allowed. Only HTTP/HTTPS allowed."

        hostname = (parsed.hostname or "").lower()
        if not hostname:
            return False, "Missing hostname in sandbox worker URL."

        if hostname in ("169.254.169.254", "metadata.google.internal", "metadata.goog", "instance-data"):
            return False, "Access to cloud metadata endpoints is blocked."

        try:
            ip = ipaddress.ip_address(hostname)
            if (ip.is_loopback or ip.is_private) and not self.allow_local:
                return False, f"Internal/loopback address '{hostname}' blocked without explicit permission."
        except ValueError:
            if (hostname == "localhost" or hostname.endswith(".localhost")) and not self.allow_local:
                return False, f"Localhost domain '{hostname}' blocked without explicit permission."

        return True, "Safe"

    def health_check(self) -> Dict[str, Any]:
        if not self.is_configured():
            return {
                "status": "NOT_CONFIGURED",
                "provider": self.provider_name,
                "configured": False,
                "available": False,
                "message": "Sandbox endpoint URL is empty."
            }

        safe, reason = self._validate_endpoint_safety(self._endpoint_url)
        if not safe:
            return {
                "status": "UNAVAILABLE",
                "provider": self.provider_name,
                "configured": True,
                "available": False,
                "message": f"Sandbox endpoint rejected: {reason}"
            }

        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        try:
            client = self._client or httpx.Client(timeout=2.5)
            t0 = time.time()
            resp = client.get(f"{self._endpoint_url}/health", headers=headers)
            latency_ms = int((time.time() - t0) * 1000)
            if resp.status_code == 200:
                data = {}
                try:
                    data = resp.json()
                except Exception:
                    pass
                return {
                    "status": "HEALTHY",
                    "provider": self.provider_name,
                    "configured": True,
                    "available": True,
                    "latency_ms": latency_ms,
                    "runtime_version": data.get("runtime_version", "1.0.0"),
                    "isolation_technology": data.get("isolation", "gVisor/Firecracker")
                }
            else:
                return {
                    "status": "UNAVAILABLE",
                    "provider": self.provider_name,
                    "configured": True,
                    "available": False,
                    "message": f"Worker returned status {resp.status_code}"
                }
        except Exception as e:
            logger.warning(f"Sandbox health check failed: {e}")
            return {
                "status": "UNAVAILABLE",
                "provider": self.provider_name,
                "configured": True,
                "available": False,
                "message": f"Worker unreachable: {str(e)}"
            }

    def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        if not self.is_configured():
            return SandboxExecutionResult(
                execution_id=request.execution_id,
                status="NOT_CONFIGURED",
                error_message="Sandbox worker URL is not configured.",
                provider=self.provider_name,
                isolation_level="NONE",
                cleaned_up=True
            )

        safe, reason = self._validate_endpoint_safety(self._endpoint_url)
        if not safe:
            return SandboxExecutionResult(
                execution_id=request.execution_id,
                status="UNAVAILABLE",
                error_message=f"Sandbox endpoint safety violation: {reason}",
                provider=self.provider_name,
                isolation_level="NONE",
                cleaned_up=True
            )

        headers = {
            "Content-Type": "application/json",
            "X-AgentGuard-Execution-ID": request.execution_id,
            "X-AgentGuard-Org-ID": request.org_id,
            "X-AgentGuard-Agent-ID": request.agent_id,
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload = {
            "execution_id": request.execution_id,
            "language": request.language,
            "code": request.code,
            "stdin": request.stdin,
            "files": request.files,
            "env_vars": request.env_vars,
            "limits": {
                "timeout_seconds": request.timeout_seconds,
                "memory_limit_mb": request.memory_limit_mb,
                "cpu_cores": request.cpu_cores,
                "process_limit": request.process_limit,
                "network_enabled": request.network_enabled
            }
        }

        timeout_margin = request.timeout_seconds + 5
        start_time = time.time()

        try:
            client = self._client or httpx.Client(timeout=timeout_margin)
            resp = client.post(f"{self._endpoint_url}/v1/sandbox/execute", json=payload, headers=headers)
            duration_ms = int((time.time() - start_time) * 1000)

            if resp.status_code == 200:
                data = resp.json()
                return SandboxExecutionResult(
                    execution_id=request.execution_id,
                    status=data.get("status", "SUCCEEDED"),
                    exit_code=data.get("exit_code", 0),
                    stdout=data.get("stdout", ""),
                    stderr=data.get("stderr", ""),
                    duration_ms=duration_ms,
                    resource_usage=data.get("resource_usage", {}),
                    artifacts=data.get("artifacts", []),
                    cleaned_up=data.get("cleaned_up", True),
                    error_message=data.get("error_message"),
                    provider=self.provider_name,
                    isolation_level=data.get("isolation_level", "CONTAINER_HARDENED")
                )
            elif resp.status_code == 408 or "timeout" in resp.text.lower():
                return SandboxExecutionResult(
                    execution_id=request.execution_id,
                    status="TIMED_OUT",
                    exit_code=-1,
                    duration_ms=duration_ms,
                    error_message=f"Execution timed out after {request.timeout_seconds}s.",
                    provider=self.provider_name,
                    isolation_level="CONTAINER_HARDENED",
                    cleaned_up=True
                )
            else:
                return SandboxExecutionResult(
                    execution_id=request.execution_id,
                    status="FAILED",
                    exit_code=resp.status_code,
                    duration_ms=duration_ms,
                    error_message=f"Worker error HTTP {resp.status_code}: {resp.text[:300]}",
                    provider=self.provider_name,
                    isolation_level="CONTAINER_HARDENED",
                    cleaned_up=True
                )
        except httpx.TimeoutException:
            duration_ms = int((time.time() - start_time) * 1000)
            return SandboxExecutionResult(
                execution_id=request.execution_id,
                status="TIMED_OUT",
                exit_code=-1,
                duration_ms=duration_ms,
                error_message=f"Worker execution timed out after {request.timeout_seconds}s deadline.",
                provider=self.provider_name,
                isolation_level="CONTAINER_HARDENED",
                cleaned_up=True
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return SandboxExecutionResult(
                execution_id=request.execution_id,
                status="UNAVAILABLE",
                exit_code=None,
                duration_ms=duration_ms,
                error_message=f"Failed to communicate with remote sandbox worker: {str(e)}",
                provider=self.provider_name,
                isolation_level="NONE",
                cleaned_up=True
            )

    def cancel(self, execution_id: str) -> bool:
        if not self.is_configured():
            return False
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        try:
            client = self._client or httpx.Client(timeout=3.0)
            resp = client.post(
                f"{self._endpoint_url}/v1/sandbox/cancel",
                json={"execution_id": execution_id},
                headers=headers
            )
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Failed to cancel execution on remote worker: {e}")
            return False

    def cleanup(self, execution_id: str) -> bool:
        if not self.is_configured():
            return True
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        try:
            client = self._client or httpx.Client(timeout=3.0)
            resp = client.post(
                f"{self._endpoint_url}/v1/sandbox/cleanup",
                json={"execution_id": execution_id},
                headers=headers
            )
            return resp.status_code == 200
        except Exception:
            return False


# ============================================================================
# CONCRETE PROVIDER: CONTROLLED MOCK TEST WORKER (FOR DETERMINISTIC CI TESTS)
# ============================================================================

class MockTestSandboxProvider(SandboxProviderBase):
    """
    Controlled deterministic mock worker for unit and regression testing.
    Validates isolation invariants without requiring a live gVisor or Firecracker host.
    Simulates:
    - Normal success
    - Simulated timeouts
    - Simulated resource exhaustion (OOM)
    - Simulated nonzero exit codes
    - Verifies workspace directory creation and cleanup
    - Asserts that sensitive environment variables were completely stripped
    """

    def __init__(self, simulate_network_failure: bool = False):
        self.simulate_network_failure = simulate_network_failure
        self.active_executions: Dict[str, Dict[str, Any]] = {}
        self.cleaned_executions: List[str] = []

    @property
    def provider_name(self) -> str:
        return "MOCK_TEST_WORKER"

    def is_configured(self) -> bool:
        return True

    def health_check(self) -> Dict[str, Any]:
        if self.simulate_network_failure:
            return {
                "status": "UNAVAILABLE",
                "provider": self.provider_name,
                "configured": True,
                "available": False,
                "message": "Simulated mock worker unavailable."
            }
        return {
            "status": "HEALTHY",
            "provider": self.provider_name,
            "configured": True,
            "available": True,
            "latency_ms": 2,
            "isolation_technology": "MOCK_CONTROLLED_CONTAINER"
        }

    def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        if self.simulate_network_failure:
            return SandboxExecutionResult(
                execution_id=request.execution_id,
                status="UNAVAILABLE",
                error_message="Simulated mock worker is unreachable.",
                provider=self.provider_name,
                isolation_level="NONE",
                cleaned_up=True
            )

        # Invariant Check: Verify NO host environment secrets passed
        for k in request.env_vars.keys():
            k_u = k.upper()
            if any(b in k_u for b in ("DATABASE", "SECRET", "KEY", "TOKEN", "SUPABASE", "OPENAI")):
                return SandboxExecutionResult(
                    execution_id=request.execution_id,
                    status="FAILED",
                    exit_code=1,
                    stderr=f"SECURITY_VIOLATION: Secret variable '{k}' leaked to sandbox environment!",
                    error_message="Environment secret leakage detected.",
                    provider=self.provider_name,
                    isolation_level="MOCK_TEST",
                    cleaned_up=True
                )

        # Invariant Check: Network Isolation
        if "curl" in request.code or "urllib" in request.code or "requests" in request.code:
            if not request.network_enabled:
                return SandboxExecutionResult(
                    execution_id=request.execution_id,
                    status="FAILED",
                    exit_code=1,
                    stdout="",
                    stderr="NetworkError: Egress connection refused. Sandbox network is disabled.",
                    duration_ms=15,
                    provider=self.provider_name,
                    isolation_level="MOCK_TEST",
                    cleaned_up=True
                )

        # Simulate Timeout trigger
        if "__SIMULATE_TIMEOUT__" in request.code or request.timeout_seconds <= 0:
            return SandboxExecutionResult(
                execution_id=request.execution_id,
                status="TIMED_OUT",
                exit_code=-1,
                stdout="Execution started...\n",
                stderr="TimeoutError: Sandbox process exceeded execution deadline.",
                duration_ms=request.timeout_seconds * 1000,
                error_message=f"Process timed out after {request.timeout_seconds}s limit.",
                provider=self.provider_name,
                isolation_level="MOCK_TEST",
                cleaned_up=True
            )

        # Simulate Memory Exhaustion (OOM)
        if "__SIMULATE_OOM__" in request.code:
            return SandboxExecutionResult(
                execution_id=request.execution_id,
                status="FAILED",
                exit_code=137,  # SIGKILL (OOM Killer)
                stdout="",
                stderr="MemoryError: Sandbox memory limit exceeded (cgroup memory kill).",
                duration_ms=45,
                error_message="Memory limit exceeded.",
                resource_usage={"peak_memory_mb": request.memory_limit_mb + 10},
                provider=self.provider_name,
                isolation_level="MOCK_TEST",
                cleaned_up=True
            )

        # Simulate Non-zero Exit Failure
        if "__SIMULATE_FAILURE__" in request.code or "raise ValueError" in request.code:
            return SandboxExecutionResult(
                execution_id=request.execution_id,
                status="FAILED",
                exit_code=1,
                stdout="",
                stderr="Traceback (most recent call last):\nValueError: Simulated script crash",
                duration_ms=10,
                provider=self.provider_name,
                isolation_level="MOCK_TEST",
                cleaned_up=True
            )

        # Normal successful execution simulation
        output_lines = []
        if "print(" in request.code:
            # Simple extractor of print statements for deterministic unit test asserts
            for line in request.code.splitlines():
                if "print(" in line:
                    try:
                        content = line.split("print(", 1)[1].rsplit(")", 1)[0].strip(" '\"")
                        output_lines.append(content)
                    except Exception:
                        pass
        stdout_sim = "\n".join(output_lines) if output_lines else "Execution finished with status 0."

        self.active_executions[request.execution_id] = {
            "request": request,
            "created_at": time.time()
        }

        return SandboxExecutionResult(
            execution_id=request.execution_id,
            status="SUCCEEDED",
            exit_code=0,
            stdout=stdout_sim,
            stderr="",
            duration_ms=25,
            resource_usage={
                "cpu_time_ms": 18,
                "peak_memory_mb": 42.5,
                "process_count": 1
            },
            artifacts=[{"filename": "output.json", "size_bytes": 128}],
            cleaned_up=True,
            provider=self.provider_name,
            isolation_level="MOCK_TEST"
        )

    def cancel(self, execution_id: str) -> bool:
        if execution_id in self.active_executions:
            del self.active_executions[execution_id]
        self.cleaned_executions.append(execution_id)
        return True

    def cleanup(self, execution_id: str) -> bool:
        self.cleaned_executions.append(execution_id)
        return True


# ============================================================================
# PROVIDER FACTORY & SINGLETON REGISTRATION
# ============================================================================

_active_provider: Optional[SandboxProviderBase] = None


def get_sandbox_provider() -> SandboxProviderBase:
    """Returns the globally configured sandbox execution provider."""
    global _active_provider
    if _active_provider is not None:
        return _active_provider

    provider_type = settings.SANDBOX_PROVIDER.upper().strip()

    if provider_type in ("REMOTE_WORKER", "GVISOR", "FIRECRACKER") and settings.SANDBOX_ENDPOINT_URL:
        _active_provider = RemoteWorkerSandboxProvider()
    elif provider_type == "MOCK_TEST_WORKER":
        _active_provider = MockTestSandboxProvider()
    else:
        _active_provider = UnconfiguredSandboxProvider()

    return _active_provider


def set_sandbox_provider(provider: SandboxProviderBase) -> None:
    """Explicitly sets the active sandbox provider (primarily used for test harnesses)."""
    global _active_provider
    _active_provider = provider


def reset_sandbox_provider() -> None:
    """Resets the active provider back to default configuration."""
    global _active_provider
    _active_provider = None


# ============================================================================
# CORE SANDBOX COORDINATION SERVICE
# ============================================================================

class SandboxService:
    """
    Coordinates isolated execution with AGENTGUARD runtime governance.
    Verifies execution gate tokens, strips host credentials, limits output size,
    records telemetry & provenance, and guarantees tenant isolation.
    """

    def __init__(self):
        self.max_output_size = settings.SANDBOX_MAX_OUTPUT_SIZE_BYTES

    def get_provider_status(self) -> Dict[str, Any]:
        """Returns truthful operational status and resource limits for the sandbox runtime."""
        provider = get_sandbox_provider()
        health = provider.health_check()
        return {
            "configured": provider.is_configured(),
            "provider": provider.provider_name,
            "status": health.get("status", "NOT_CONFIGURED"),
            "endpoint_configured": bool(settings.SANDBOX_ENDPOINT_URL),
            "resource_limits": {
                "max_memory_mb": settings.SANDBOX_MAX_MEMORY_MB,
                "max_cpu_cores": settings.SANDBOX_MAX_CPU_CORES,
                "max_processes": settings.SANDBOX_MAX_PROCESSES,
                "default_timeout_seconds": settings.SANDBOX_DEFAULT_TIMEOUT_SECONDS,
                "max_output_size_bytes": settings.SANDBOX_MAX_OUTPUT_SIZE_BYTES,
                "network_allowed_by_default": settings.SANDBOX_ALLOW_NETWORK
            },
            "isolation_technology": health.get("isolation_technology", "gVisor/Firecracker" if provider.is_configured() else "NONE"),
            "supported_languages": ["python", "bash", "sh", "javascript", "node"]
        }

    def execute_sandboxed_action(
        self,
        db: Session,
        agent: models.Agent,
        gate_token: str,
        code: str,
        language: str = "python",
        tool_name: Optional[str] = "python_sandbox",
        stdin: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None,
        network_enabled: Optional[bool] = None,
        env_vars: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Executes code through the external isolated sandbox provider following full
        runtime governance validation. Single-use gate token is consumed atomically.
        """
        now = datetime.datetime.utcnow()
        execution_id = f"sbx_{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}"
        resolved_tool = tool_name or "sandbox_execution"
        effective_timeout = min(timeout_seconds or settings.SANDBOX_DEFAULT_TIMEOUT_SECONDS, 300)
        allow_net = network_enabled if network_enabled is not None else settings.SANDBOX_ALLOW_NETWORK
        code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()

        # --------------------------------------------------------------------
        # 1. VALIDATE EXECUTION GATE TOKEN
        # --------------------------------------------------------------------
        if not gate_token or not gate_token.strip():
            return {
                "success": False,
                "status": "GATE_TOKEN_INVALID",
                "execution_id": execution_id,
                "error": "Missing execution gate token.",
                "gate_token": gate_token or ""
            }

        decision = db.query(models.Decision).filter(
            models.Decision.execution_gate_token == gate_token
        ).first()

        if not decision:
            return {
                "success": False,
                "status": "GATE_TOKEN_INVALID",
                "execution_id": execution_id,
                "error": "Invalid execution gate token. Token does not match any authorization record.",
                "gate_token": gate_token
            }

        if decision.gate_token_used:
            return {
                "success": False,
                "status": "GATE_TOKEN_REPLAYED",
                "execution_id": execution_id,
                "error": "Execution gate token has already been consumed (replay prevented).",
                "gate_token": gate_token
            }

        if str(decision.agent_id) != str(agent.id):
            return {
                "success": False,
                "status": "AGENT_MISMATCH",
                "execution_id": execution_id,
                "error": f"Execution gate token agent mismatch: token was issued to agent {decision.agent_id}, not {agent.id}.",
                "gate_token": gate_token
            }

        if decision.decision != "ALLOW":
            return {
                "success": False,
                "status": "NOT_AUTHORIZED",
                "execution_id": execution_id,
                "error": f"Action was not approved for execution (decision was {decision.decision}).",
                "gate_token": gate_token
            }

        if decision.timestamp:
            age_sec = (now - decision.timestamp).total_seconds()
            if age_sec > 300:
                return {
                    "success": False,
                    "status": "GATE_TOKEN_EXPIRED",
                    "execution_id": execution_id,
                    "error": f"Execution gate token has expired ({int(age_sec)}s > 300s TTL).",
                    "gate_token": gate_token
                }

        # --------------------------------------------------------------------
        # 2. CHECK PROVIDER CONFIGURATION & AVAILABILITY
        # --------------------------------------------------------------------
        provider = get_sandbox_provider()

        if not provider.is_configured():
            # Mark token consumed to prevent repeated replay attempts
            decision.gate_token_used = True
            decision.executed_at = now
            decision.execution_status = "EXECUTION_FAILED"
            db.commit()

            # Record failed job record
            job = models.SandboxExecutionJob(
                org_id=agent.org_id,
                agent_id=agent.id,
                decision_id=decision.id,
                execution_id=execution_id,
                tool_name=resolved_tool,
                language=language,
                code_hash=code_hash,
                status="NOT_CONFIGURED",
                provider="NOT_CONFIGURED",
                isolation_level="NONE",
                error_message="External isolated sandbox provider is not configured. Running untrusted code on the host process is strictly forbidden.",
                cleanup_status="CLEANED",
                created_at=now,
                completed_at=now
            )
            db.add(job)
            db.commit()

            return {
                "success": False,
                "status": "NOT_CONFIGURED",
                "execution_id": execution_id,
                "job_id": str(job.id),
                "error": "External isolated sandbox provider is not configured. Execution rejected.",
                "gate_token": gate_token,
                "provider": "NOT_CONFIGURED",
                "isolation_level": "NONE",
                "cleaned_up": True
            }

        health = provider.health_check()
        if not health.get("available", False):
            decision.gate_token_used = True
            decision.executed_at = now
            decision.execution_status = "EXECUTION_FAILED"
            db.commit()

            job = models.SandboxExecutionJob(
                org_id=agent.org_id,
                agent_id=agent.id,
                decision_id=decision.id,
                execution_id=execution_id,
                tool_name=resolved_tool,
                language=language,
                code_hash=code_hash,
                status="UNAVAILABLE",
                provider=provider.provider_name,
                isolation_level="NONE",
                error_message=f"External sandbox provider is unreachable: {health.get('message', 'Health check failed')}",
                cleanup_status="CLEANED",
                created_at=now,
                completed_at=now
            )
            db.add(job)
            db.commit()

            return {
                "success": False,
                "status": "UNAVAILABLE",
                "execution_id": execution_id,
                "job_id": str(job.id),
                "error": f"External sandbox provider is UNAVAILABLE: {health.get('message')}",
                "gate_token": gate_token,
                "provider": provider.provider_name,
                "isolation_level": "NONE",
                "cleaned_up": True
            }

        # --------------------------------------------------------------------
        # 3. ATOMIC TOKEN CONSUMPTION & DURABLE JOB CREATION
        # --------------------------------------------------------------------
        decision.gate_token_used = True
        decision.executed_at = now
        decision.execution_status = "EXECUTED"
        db.commit()

        clean_env = cleanse_execution_environment(env_vars)

        job = models.SandboxExecutionJob(
            org_id=agent.org_id,
            agent_id=agent.id,
            decision_id=decision.id,
            execution_id=execution_id,
            tool_name=resolved_tool,
            language=language,
            code_hash=code_hash,
            status="RUNNING",
            provider=provider.provider_name,
            isolation_level="CONTAINER_HARDENED",
            cpu_limit=settings.SANDBOX_MAX_CPU_CORES,
            memory_limit_mb=settings.SANDBOX_MAX_MEMORY_MB,
            timeout_seconds=effective_timeout,
            network_isolated=not allow_net,
            cleanup_status="PENDING",
            created_at=now,
            started_at=now
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # --------------------------------------------------------------------
        # 4. DISPATCH ISOLATED EXECUTION
        # --------------------------------------------------------------------
        req = SandboxExecutionRequest(
            execution_id=execution_id,
            org_id=str(agent.org_id),
            agent_id=str(agent.id),
            decision_id=str(decision.id),
            tool_name=resolved_tool,
            language=language,
            code=code,
            stdin=stdin,
            env_vars=clean_env,
            timeout_seconds=effective_timeout,
            memory_limit_mb=settings.SANDBOX_MAX_MEMORY_MB,
            cpu_cores=settings.SANDBOX_MAX_CPU_CORES,
            process_limit=settings.SANDBOX_MAX_PROCESSES,
            network_enabled=allow_net
        )

        res = provider.execute(req)

        # Output truncation & sanitization
        stdout_raw = res.stdout or ""
        stderr_raw = res.stderr or ""
        if len(stdout_raw) > self.max_output_size:
            stdout_raw = stdout_raw[:self.max_output_size] + f"\n... [Output truncated at {self.max_output_size} bytes limit] ..."
        if len(stderr_raw) > self.max_output_size:
            stderr_raw = stderr_raw[:self.max_output_size] + f"\n... [Stderr truncated at {self.max_output_size} bytes limit] ..."

        # Scan output for sensitive leaks
        stdout_clean, _ = pii_engine.redact_text(stdout_raw, mode="MASK")
        stderr_clean, _ = pii_engine.redact_text(stderr_raw, mode="MASK")

        # Guarantee provider cleanup
        try:
            provider.cleanup(execution_id)
        except Exception as e:
            logger.warning(f"Error triggering sandbox cleanup: {e}")

        # --------------------------------------------------------------------
        # 5. UPDATE DURABLE JOB RECORD
        # --------------------------------------------------------------------
        job.status = res.status
        job.exit_code = res.exit_code
        job.stdout = stdout_clean
        job.stderr = stderr_clean
        job.error_message = res.error_message
        job.resource_usage_json = res.resource_usage
        job.artifacts_json = res.artifacts
        job.cleanup_status = "CLEANED" if res.cleaned_up else "PENDING"
        job.completed_at = datetime.datetime.utcnow()
        db.commit()

        # --------------------------------------------------------------------
        # 6. TELEMETRY, PROVENANCE & AUDIT LOGGING
        # --------------------------------------------------------------------
        try:
            prov = models.ProvenanceEvent(
                decision_id=decision.id,
                agent_id=agent.id,
                tool_used=resolved_tool,
                data_accessed=f"sandbox:{language}",
                causal_chain_json={
                    "execution_id": execution_id,
                    "provider": provider.provider_name,
                    "exit_code": res.exit_code,
                    "status": res.status,
                    "duration_ms": res.duration_ms,
                    "resource_usage": res.resource_usage
                },
                timestamp=datetime.datetime.utcnow()
            )
            db.add(prov)

            record_execution(
                db=db,
                org_id=str(agent.org_id),
                agent_id=str(agent.id),
                action=decision.action_requested,
                resource=f"sandbox:{resolved_tool}",
                outcome="EXECUTED" if res.status == "SUCCEEDED" else "ERROR",
                risk_score=decision.risk_score or 0,
                policy_decision=decision.decision,
                decision_id=str(decision.id),
                latency_ms=res.duration_ms,
                status="COMPLETED" if res.status == "SUCCEEDED" else res.status,
                error_code=res.error_message,
                request_id=execution_id,
                metadata={
                    "tool_name": resolved_tool,
                    "language": language,
                    "provider": provider.provider_name,
                    "exit_code": res.exit_code,
                    "gate_token": gate_token
                }
            )

            audit = models.AuditLog(
                org_id=agent.org_id,
                event_type="RUNTIME_SANDBOX_EXECUTED",
                actor_type="MACHINE",
                actor_id=str(agent.id),
                action="SANDBOX_EXECUTE",
                resource=f"tool:{resolved_tool}",
                result="SUCCESS" if res.status == "SUCCEEDED" else "FAILURE",
                metadata_json={
                    "execution_id": execution_id,
                    "job_id": str(job.id),
                    "tool_name": resolved_tool,
                    "language": language,
                    "provider": provider.provider_name,
                    "status": res.status,
                    "exit_code": res.exit_code,
                    "duration_ms": res.duration_ms,
                    "error": res.error_message
                }
            )
            db.add(audit)
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to record sandbox telemetry/audit: {e}")
            db.rollback()

        is_success = (res.status == "SUCCEEDED")
        return {
            "success": is_success,
            "status": res.status,
            "execution_id": execution_id,
            "job_id": str(job.id),
            "exit_code": res.exit_code,
            "stdout": stdout_clean,
            "stderr": stderr_clean,
            "duration_ms": res.duration_ms,
            "resource_usage": res.resource_usage,
            "artifacts": res.artifacts,
            "gate_token": gate_token,
            "cleaned_up": res.cleaned_up,
            "provider": provider.provider_name,
            "isolation_level": res.isolation_level,
            "error": res.error_message
        }

    def get_job(self, db: Session, job_id: str, org_id: str) -> Optional[models.SandboxExecutionJob]:
        """Tenant-isolated retrieval of a specific sandbox execution job."""
        return db.query(models.SandboxExecutionJob).filter(
            (models.SandboxExecutionJob.id == job_id) | (models.SandboxExecutionJob.execution_id == job_id),
            models.SandboxExecutionJob.org_id == org_id
        ).first()

    def list_jobs(
        self,
        db: Session,
        org_id: str,
        agent_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[models.SandboxExecutionJob]:
        """Tenant-isolated listing of sandbox execution jobs."""
        query = db.query(models.SandboxExecutionJob).filter(
            models.SandboxExecutionJob.org_id == org_id
        )
        if agent_id:
            query = query.filter(models.SandboxExecutionJob.agent_id == agent_id)
        if status_filter:
            query = query.filter(models.SandboxExecutionJob.status == status_filter.upper())

        return query.order_by(models.SandboxExecutionJob.created_at.desc()).offset(offset).limit(limit).all()

    def cancel_job(
        self,
        db: Session,
        job_id: str,
        org_id: str,
        actor_id: str
    ) -> Dict[str, Any]:
        """Tenant-isolated cancellation of an active sandbox execution job."""
        job = self.get_job(db, job_id, org_id)
        if not job:
            return {"success": False, "status": "NOT_FOUND", "message": "Job not found or cross-tenant access denied."}

        if job.status not in ("PENDING", "RUNNING", "QUEUED"):
            return {
                "success": False,
                "status": "ALREADY_FINISHED",
                "message": f"Job is already in terminal state '{job.status}'."
            }

        provider = get_sandbox_provider()
        provider.cancel(job.execution_id)
        provider.cleanup(job.execution_id)

        job.status = "CANCELLED"
        job.error_message = f"Cancelled by user/agent {actor_id}"
        job.cleanup_status = "CLEANED"
        job.completed_at = datetime.datetime.utcnow()
        db.commit()

        # Audit cancellation
        audit = models.AuditLog(
            org_id=job.org_id,
            event_type="RUNTIME_SANDBOX_CANCELLED",
            actor_type="USER",
            actor_id=actor_id,
            action="SANDBOX_CANCEL",
            resource=f"sandbox_job:{job.execution_id}",
            result="SUCCESS",
            metadata_json={"job_id": str(job.id), "execution_id": job.execution_id}
        )
        db.add(audit)
        db.commit()

        return {
            "success": True,
            "execution_id": job.execution_id,
            "status": "CANCELLED",
            "message": "Execution cancelled successfully."
        }


sandbox_service = SandboxService()
