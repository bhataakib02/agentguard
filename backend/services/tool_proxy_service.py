"""
Forward Execution Tool Proxy Gateway for AgentGuard.
Validates execution gate tokens issued by the 12-stage runtime authorization kernel,
enforces SSRF protection, dispatches outbound HTTP requests to downstream tools/APIs,
captures execution latency, and records provenance & execution telemetry.
"""

import datetime
import ipaddress
import json
import logging
import os
import time
import urllib.parse
from typing import Dict, Any, Optional

import httpx
from sqlalchemy.orm import Session

import models
from config import settings
from engines.intent_engine import intent_engine
from engines.pii_engine import pii_engine
from engines.output_guardrails_engine import output_guardrails_engine
from services.runtime_telemetry_service import record_execution

logger = logging.getLogger("agentguard.tool_proxy")


class ToolProxyService:
    def __init__(self):
        self._mock_client: Optional[httpx.Client] = None
        self._mock_transport: Optional[httpx.BaseTransport] = None

    @property
    def allow_local_egress(self) -> bool:
        """Dynamically inspect environment setting for allowing local test endpoints (strictly disabled in production)."""
        if getattr(settings, "ENVIRONMENT", "production").lower() == "production":
            return False
        return os.getenv("AGENTGUARD_ALLOW_LOCAL_TOOLS", "false").lower() in ("true", "1", "yes")

    def set_mock_client(self, client: Optional[httpx.Client]):
        """Inject an explicit mock httpx.Client for test isolation only. Strictly forbidden in production."""
        if getattr(settings, "ENVIRONMENT", "production").lower() == "production":
            raise RuntimeError("Mock client injection is strictly prohibited in production environment.")
        self._mock_client = client

    def set_mock_transport(self, transport: Optional[httpx.BaseTransport]):
        """Inject an explicit mock httpx transport for test isolation only. Strictly forbidden in production."""
        if getattr(settings, "ENVIRONMENT", "production").lower() == "production":
            raise RuntimeError("Mock transport injection is strictly prohibited in production environment.")
        self._mock_transport = transport

    def _validate_ssrf_safety(self, url: str) -> Dict[str, Any]:
        """
        Validates target URL against SSRF attacks. Blocks loopback, link-local,
        cloud metadata endpoints (e.g. 169.254.169.254), and illegal schemes.
        """
        try:
            parsed = urllib.parse.urlparse(url)
        except Exception as e:
            return {"safe": False, "reason": f"Invalid URL format: {str(e)}"}

        if parsed.scheme not in ("http", "https"):
            return {"safe": False, "reason": f"Scheme '{parsed.scheme}' is not allowed. Only HTTP/HTTPS allowed."}

        hostname = parsed.hostname
        if not hostname:
            return {"safe": False, "reason": "Missing hostname in target endpoint."}

        host_lower = hostname.lower()

        # Block cloud metadata hostnames
        blocked_hostnames = {
            "metadata.google.internal",
            "metadata.goog",
            "169.254.169.254",
            "instance-data"
        }
        if host_lower in blocked_hostnames:
            return {"safe": False, "reason": f"Access to cloud metadata host '{hostname}' is blocked."}

        # Check IP address restrictions
        try:
            ip = ipaddress.ip_address(host_lower)
            if ip.is_loopback:
                if not self.allow_local_egress:
                    return {"safe": False, "reason": f"Loopback address '{hostname}' is blocked."}
            elif ip.is_link_local:
                return {"safe": False, "reason": f"Link-local address '{hostname}' is blocked."}
            elif ip.is_private and not self.allow_local_egress:
                return {"safe": False, "reason": f"Private network address '{hostname}' is blocked."}
        except ValueError:
            # Hostname is a domain name, not a raw IP
            if (host_lower == "localhost" or host_lower.endswith(".localhost")) and not self.allow_local_egress:
                return {"safe": False, "reason": f"Localhost domain '{hostname}' is blocked."}

        return {"safe": True, "reason": "URL is safe for egress."}

    def execute_tool(
        self,
        db: Session,
        agent: models.Agent,
        gate_token: str,
        tool_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        override_endpoint: Optional[str] = None,
        http_client: Optional[httpx.Client] = None
    ) -> Dict[str, Any]:
        """
        Executes an approved action through the Forward Execution Tool Proxy.
        Validates the single-use execution gate token, resolves the tool endpoint,
        enforces schema and SSRF constraints, dispatches the HTTP call, and
        records execution telemetry and provenance.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        execution_id = f"exec_{int(time.time()*1000)}"

        # --------------------------------------------------------------------
        # 1. VALIDATE EXECUTION GATE TOKEN
        # --------------------------------------------------------------------
        if not gate_token or not gate_token.strip():
            return {
                "success": False,
                "status": "GATE_TOKEN_INVALID",
                "error": "Missing execution gate token.",
                "gate_token": gate_token or ""
            }

        # Reject caller-controlled override_endpoint unconditionally
        if override_endpoint and override_endpoint.strip():
            return {
                "success": False,
                "status": "NOT_AUTHORIZED",
                "error": "Security policy blocked outbound execution: override_endpoint is strictly forbidden.",
                "gate_token": gate_token,
                "tool_name": tool_name or ""
            }

        decision = db.query(models.Decision).filter(
            models.Decision.execution_gate_token == gate_token
        ).first()

        if not decision:
            return {
                "success": False,
                "status": "GATE_TOKEN_INVALID",
                "error": "Invalid execution gate token. Token does not match any authorization record.",
                "gate_token": gate_token
            }

        # Check for replay attack (one-time use gate token)
        if decision.gate_token_used:
            return {
                "success": False,
                "status": "GATE_TOKEN_REPLAYED",
                "error": "Execution gate token has already been consumed (replay prevented).",
                "gate_token": gate_token
            }

        # Check agent ownership (token must match calling agent)
        if str(decision.agent_id) != str(agent.id):
            return {
                "success": False,
                "status": "AGENT_MISMATCH",
                "error": f"Execution gate token was issued to agent {decision.agent_id}, not {agent.id}.",
                "gate_token": gate_token
            }

        # Check tenant isolation match
        decision_agent = db.query(models.Agent).filter(models.Agent.id == decision.agent_id).first()
        if not decision_agent or str(decision_agent.org_id) != str(agent.org_id):
            return {
                "success": False,
                "status": "NOT_AUTHORIZED",
                "error": "Forbidden: Execution gate token belongs to another organization.",
                "gate_token": gate_token
            }

        # Check agent lifecycle status
        if agent.status in ("SUSPENDED", "CIRCUIT_BREAK"):
            return {
                "success": False,
                "status": "NOT_AUTHORIZED",
                "error": f"Agent {agent.agent_code} is currently in {agent.status} state. Tool execution blocked.",
                "gate_token": gate_token
            }

        # Check decision outcome
        if decision.decision != "ALLOW":
            return {
                "success": False,
                "status": "NOT_AUTHORIZED",
                "error": f"Action was not approved for execution (decision was {decision.decision}).",
                "gate_token": gate_token
            }

        # Check token expiration (TTL: 300 seconds / 5 minutes)
        if decision.timestamp:
            dec_time = decision.timestamp
            if dec_time.tzinfo is None:
                # Naive timestamp (e.g. SQLite / legacy contract): interpret explicitly as UTC
                dec_time = dec_time.replace(tzinfo=datetime.timezone.utc)
            else:
                # Timezone-aware timestamp (e.g. PostgreSQL timestamptz): normalize to UTC
                dec_time = dec_time.astimezone(datetime.timezone.utc)

            age_seconds = (now - dec_time).total_seconds()
            if age_seconds > 300:
                return {
                    "success": False,
                    "status": "GATE_TOKEN_EXPIRED",
                    "error": f"Execution gate token has expired ({int(age_seconds)}s > 300s TTL).",
                    "gate_token": gate_token
                }

        # --------------------------------------------------------------------
        # 2. RESOLVE TARGET TOOL & BINDING VALIDATION (ORGANIZATION SCOPED)
        # --------------------------------------------------------------------
        tool_record = None
        if decision.tool_id:
            tool_record = db.query(models.Tool).filter(
                models.Tool.id == decision.tool_id,
                (models.Tool.org_id == agent.org_id) | (models.Tool.org_id == None)
            ).first()
        if not tool_record:
            tool_record = db.query(models.Tool).filter(
                (models.Tool.name == decision.action_requested) |
                (models.Tool.name == decision.resource_target),
                (models.Tool.org_id == agent.org_id) | (models.Tool.org_id == None)
            ).first()

        authorized_tool_name = tool_record.name if tool_record else decision.action_requested

        # If caller specified tool_name, verify it matches the authorized tool
        if tool_name and tool_name != authorized_tool_name:
            return {
                "success": False,
                "status": "NOT_AUTHORIZED",
                "error": f"Execution gate token was authorized for tool '{authorized_tool_name}', cannot execute '{tool_name}'.",
                "gate_token": gate_token,
                "tool_name": tool_name
            }
        resolved_tool_name = authorized_tool_name

        # Ensure tool belongs to calling organization
        if tool_record and tool_record.org_id and str(tool_record.org_id) != str(agent.org_id):
            return {
                "success": False,
                "status": "NOT_AUTHORIZED",
                "error": "Forbidden: Tool belongs to another organization.",
                "gate_token": gate_token,
                "tool_name": resolved_tool_name
            }

        # Verify endpoint snapshot binding
        authorized_ep = getattr(decision, "authorized_endpoint", None)
        if tool_record and tool_record.endpoint:
            if not authorized_ep:
                return {
                    "success": False,
                    "status": "NOT_AUTHORIZED",
                    "error": "Security policy violation: Decision record is missing required authorized endpoint snapshot.",
                    "gate_token": gate_token,
                    "tool_name": resolved_tool_name
                }
            if tool_record.endpoint != authorized_ep:
                return {
                    "success": False,
                    "status": "NOT_AUTHORIZED",
                    "error": "Security violation: Tool endpoint configuration has changed since authorization was granted.",
                    "gate_token": gate_token,
                    "tool_name": resolved_tool_name
                }

        # Parameter canonicalization and deterministic binding
        def _canonical_json(data: Any) -> str:
            if data is None:
                return "{}"
            return json.dumps(data, sort_keys=True, separators=(',', ':'), default=str)

        authorized_params = decision.execution_parameters or {}
        if parameters is not None:
            if _canonical_json(parameters) != _canonical_json(authorized_params):
                return {
                    "success": False,
                    "status": "NOT_AUTHORIZED",
                    "error": "Execution parameters do not match authorized decision parameters.",
                    "gate_token": gate_token,
                    "tool_name": resolved_tool_name
                }
            effective_params = parameters
        else:
            effective_params = authorized_params

        if tool_record:
            if tool_record.status != "ACTIVE":
                return {
                    "success": False,
                    "status": "TOOL_INACTIVE",
                    "error": f"Tool '{tool_record.name}' is currently {tool_record.status}.",
                    "gate_token": gate_token,
                    "tool_name": resolved_tool_name
                }

            # Parameter validation against tool schema definition
            if tool_record.schema_definition:
                val = intent_engine.validate_parameters(tool_record.schema_definition, effective_params)
                if not val["valid"]:
                    return {
                        "success": False,
                        "status": "SCHEMA_VALIDATION_FAILED",
                        "error": f"Tool parameter validation failed: {'; '.join(val['errors'])}",
                        "gate_token": gate_token,
                        "tool_name": resolved_tool_name
                    }

        # --------------------------------------------------------------------
        # 3. ENDPOINT RESOLUTION (NEVER TRUST CALLER OVERRIDE)
        # --------------------------------------------------------------------
        target_endpoint = tool_record.endpoint if tool_record else None

        # --------------------------------------------------------------------
        # 4. OUTBOUND DISPATCH / SANDBOX DELEGATION
        # --------------------------------------------------------------------
        start_time = time.time()
        status_code = None
        response_data = None
        error_msg = None
        exec_outcome = "EXECUTED"

        # Check if tool requires isolated sandbox code execution
        is_sandbox_tool = (
            (tool_record and tool_record.category in ("SANDBOX", "CODE_EXECUTION")) or
            (resolved_tool_name and "sandbox" in resolved_tool_name.lower()) or
            (isinstance(effective_params, dict) and ("code" in effective_params or "script" in effective_params))
        )

        if not is_sandbox_tool:
            # ATOMIC GATE TOKEN CONSUMPTION
            rows_updated = db.query(models.Decision).filter(
                models.Decision.id == decision.id,
                models.Decision.gate_token_used == False,
                models.Decision.decision == "ALLOW"
            ).update(
                {
                    models.Decision.gate_token_used: True,
                    models.Decision.execution_status: "CLAIMED",
                    models.Decision.executed_at: now
                },
                synchronize_session=False
            )
            db.commit()

            if rows_updated != 1:
                return {
                    "success": False,
                    "status": "GATE_TOKEN_REPLAYED",
                    "error": "Execution gate token has already been consumed (replay prevented).",
                    "gate_token": gate_token,
                    "tool_name": resolved_tool_name
                }

        # Check if tool requires isolated sandbox code execution
        is_sandbox_tool = (
            (tool_record and tool_record.category in ("SANDBOX", "CODE_EXECUTION")) or
            (resolved_tool_name and "sandbox" in resolved_tool_name.lower()) or
            (isinstance(effective_params, dict) and ("code" in effective_params or "script" in effective_params))
        )

        if is_sandbox_tool:
            from services.sandbox_service import sandbox_service
            code_str = ""
            lang = "python"
            stdin_val = None
            timeout_val = (tool_record.timeout_seconds if tool_record else None)
            net_val = False
            env_val = None

            if isinstance(effective_params, dict):
                code_str = effective_params.get("code") or effective_params.get("script") or ""
                lang = effective_params.get("language") or "python"
                stdin_val = effective_params.get("stdin")
                timeout_val = effective_params.get("timeout_seconds") or timeout_val
                net_val = effective_params.get("network_enabled", False)
                env_val = effective_params.get("env_vars")

            sbx_res = sandbox_service.execute_sandboxed_action(
                db=db,
                agent=agent,
                gate_token=gate_token,
                code=code_str,
                language=lang,
                tool_name=resolved_tool_name,
                stdin=stdin_val,
                parameters=effective_params,
                timeout_seconds=timeout_val,
                network_enabled=net_val,
                env_vars=env_val
            )
            return {
                "success": sbx_res["success"],
                "status": sbx_res["status"],
                "execution_id": sbx_res.get("execution_id", execution_id),
                "tool_name": resolved_tool_name,
                "status_code": 200 if sbx_res["success"] else (400 if "REPLAY" in sbx_res.get("status", "") else 500),
                "response_data": {
                    "stdout": sbx_res.get("stdout"),
                    "stderr": sbx_res.get("stderr"),
                    "exit_code": sbx_res.get("exit_code"),
                    "job_id": sbx_res.get("job_id"),
                    "provider": sbx_res.get("provider"),
                    "artifacts": sbx_res.get("artifacts")
                },
                "latency_ms": sbx_res.get("duration_ms", 0),
                "gate_token": gate_token,
                "error": sbx_res.get("error")
            }

        if target_endpoint:
            # Validate SSRF safety
            ssrf_check = self._validate_ssrf_safety(target_endpoint)
            if not ssrf_check["safe"]:
                return {
                    "success": False,
                    "status": "SSRF_BLOCKED",
                    "error": f"Security policy blocked outbound execution: {ssrf_check['reason']}",
                    "gate_token": gate_token,
                    "tool_name": resolved_tool_name
                }

            headers = {
                "Content-Type": "application/json",
                "X-AgentGuard-Execution-ID": execution_id,
                "X-AgentGuard-Agent-Code": agent.agent_code,
                "X-AgentGuard-Gate-Token": gate_token
            }
            if tool_record and tool_record.headers_json:
                headers.update(tool_record.headers_json)

            timeout_sec = (tool_record.timeout_seconds if tool_record else 30) or 30

            try:
                if getattr(settings, "ENVIRONMENT", "production").lower() == "production":
                    client = httpx.Client(timeout=timeout_sec)
                elif http_client is not None:
                    client = http_client
                elif self._mock_client is not None:
                    client = self._mock_client
                elif self._mock_transport is not None:
                    client = httpx.Client(transport=self._mock_transport, timeout=timeout_sec)
                else:
                    client = httpx.Client(timeout=timeout_sec)

                resp = client.post(target_endpoint, json=effective_params, headers=headers)
                status_code = resp.status_code
                try:
                    response_data = resp.json()
                except Exception:
                    response_data = resp.text

                if status_code >= 400:
                    exec_outcome = "ERROR"
                    error_msg = f"Downstream service returned HTTP {status_code}"
            except httpx.TimeoutException:
                exec_outcome = "TIMEOUT"
                error_msg = f"Downstream service timed out after {timeout_sec}s."
            except Exception as e:
                exec_outcome = "ERROR"
                error_msg = f"Downstream connection error: {str(e)}"
        else:
            # Local / Virtual Tool execution (e.g., standard internal operations)
            status_code = 200
            response_data = {
                "message": f"Action '{decision.action_requested}' executed successfully via AgentGuard Tool Proxy.",
                "tool": resolved_tool_name,
                "parameters": effective_params,
                "timestamp": now.isoformat()
            }

        # Sanitize response data to prevent sensitive data exfiltration & toxic output
        if response_data is not None:
            sanitized_response, _ = pii_engine.scan_and_redact_payload(response_data, mode="MASK")
            if isinstance(sanitized_response, dict) and "message" in sanitized_response and isinstance(sanitized_response["message"], str):
                safety_eval = output_guardrails_engine.evaluate_output(sanitized_response["message"], policy_mode="REDACT")
                if safety_eval.get("sanitized_text"):
                    sanitized_response["message"] = safety_eval["sanitized_text"]
            elif isinstance(sanitized_response, str):
                safety_eval = output_guardrails_engine.evaluate_output(sanitized_response, policy_mode="REDACT")
                if safety_eval.get("sanitized_text"):
                    sanitized_response = safety_eval["sanitized_text"]
            response_data = sanitized_response

        latency_ms = int((time.time() - start_time) * 1000)

        # --------------------------------------------------------------------
        # 5. STATE TRANSITION & OUTCOME RECORDING
        # --------------------------------------------------------------------
        final_status = "EXECUTED" if exec_outcome == "EXECUTED" else "EXECUTION_FAILED"
        decision.execution_status = final_status
        if tool_record:
            decision.tool_id = tool_record.id
        db.query(models.Decision).filter(models.Decision.id == decision.id).update(
            {
                models.Decision.execution_status: final_status,
                models.Decision.tool_id: (tool_record.id if tool_record else decision.tool_id)
            },
            synchronize_session=False
        )
        db.commit()

        # --------------------------------------------------------------------
        # 6. TELEMETRY & PROVENANCE RECORDING
        # --------------------------------------------------------------------
        masked_token = f"{gate_token[:8]}...{gate_token[-4:]}" if len(gate_token) > 12 else "gate_***"
        try:
            prov = models.ProvenanceEvent(
                decision_id=decision.id,
                agent_id=agent.id,
                tool_used=resolved_tool_name,
                data_accessed=str(list(effective_params.keys())) if effective_params else None,
                causal_chain_json={
                    "execution_id": execution_id,
                    "gate_token": gate_token,
                    "target_endpoint": target_endpoint,
                    "status_code": status_code,
                    "latency_ms": latency_ms,
                    "outcome": exec_outcome
                },
                timestamp=datetime.datetime.utcnow()
            )
            db.add(prov)

            record_execution(
                db=db,
                org_id=str(agent.org_id),
                agent_id=str(agent.id),
                action=decision.action_requested,
                resource=decision.resource_target,
                outcome=exec_outcome,
                risk_score=decision.risk_score or 0,
                policy_decision=decision.decision,
                decision_id=str(decision.id),
                latency_ms=latency_ms,
                status="COMPLETED" if exec_outcome == "EXECUTED" else exec_outcome,
                error_code=error_msg,
                request_id=execution_id,
                metadata={
                    "tool_name": resolved_tool_name,
                    "gate_token": gate_token,
                    "status_code": status_code
                }
            )

            audit = models.AuditLog(
                org_id=agent.org_id,
                event_type="RUNTIME_TOOL_EXECUTED",
                actor_type="MACHINE",
                actor_id=str(agent.id),
                action="TOOL_PROXY_EXECUTE",
                resource=f"tool:{resolved_tool_name}",
                result="SUCCESS" if exec_outcome == "EXECUTED" else "FAILURE",
                metadata_json={
                    "execution_id": execution_id,
                    "tool_name": resolved_tool_name,
                    "gate_token": gate_token,
                    "status_code": status_code,
                    "latency_ms": latency_ms,
                    "error": error_msg
                }
            )
            db.add(audit)
            db.commit()
        except Exception as e:
            logger.warning(f"Telemetry/Provenance recording error: {e}")
            db.rollback()

        is_success = exec_outcome == "EXECUTED"
        return {
            "success": is_success,
            "status": "EXECUTED" if is_success else "EXECUTION_FAILED",
            "execution_id": execution_id,
            "tool_name": resolved_tool_name,
            "status_code": status_code,
            "response_data": response_data,
            "latency_ms": latency_ms,
            "gate_token": gate_token,
            "error": error_msg
        }


tool_proxy_service = ToolProxyService()
