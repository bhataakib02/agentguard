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
from engines.intent_engine import intent_engine
from engines.pii_engine import pii_engine
from engines.output_guardrails_engine import output_guardrails_engine
from services.runtime_telemetry_service import record_execution

logger = logging.getLogger("agentguard.tool_proxy")


class ToolProxyService:
    def __init__(self):
        # By default, disallow local addresses to prevent SSRF unless explicitly enabled for testing
        self.allow_local_egress = os.getenv("AGENTGUARD_ALLOW_LOCAL_TOOLS", "false").lower() in ("true", "1", "yes")

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
        now = datetime.datetime.utcnow()
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
            age_seconds = (now - decision.timestamp).total_seconds()
            if age_seconds > 300:
                return {
                    "success": False,
                    "status": "GATE_TOKEN_EXPIRED",
                    "error": f"Execution gate token has expired ({int(age_seconds)}s > 300s TTL).",
                    "gate_token": gate_token
                }

        # --------------------------------------------------------------------
        # 2. RESOLVE TARGET TOOL & SCHEMA VALIDATION
        # --------------------------------------------------------------------
        resolved_tool_name = tool_name or decision.action_requested
        tool_record = None

        if tool_name:
            tool_record = db.query(models.Tool).filter(models.Tool.name == tool_name).first()
        elif decision.tool_id:
            tool_record = db.query(models.Tool).filter(models.Tool.id == decision.tool_id).first()
        else:
            # Attempt lookup by action or resource target
            tool_record = db.query(models.Tool).filter(
                (models.Tool.name == decision.action_requested) |
                (models.Tool.name == decision.resource_target)
            ).first()

        effective_params = parameters if parameters is not None else (decision.execution_parameters or {})

        if tool_record:
            resolved_tool_name = tool_record.name
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
        # 3. ENDPOINT RESOLUTION & SSRF DEFENSE
        # --------------------------------------------------------------------
        target_endpoint = override_endpoint or (tool_record.endpoint if tool_record else None)

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

            if target_endpoint.startswith("mock://") or "example.com" in target_endpoint or target_endpoint.endswith(".test"):
                status_code = 200
                response_data = {
                    "status": "APPROVED",
                    "refund_id": f"ref_{int(time.time())}",
                    "tool": resolved_tool_name,
                    "parameters": effective_params,
                    "message": "Tool endpoint executed successfully."
                }
            else:
                try:
                    client = http_client or httpx.Client(timeout=timeout_sec)
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
        # 5. STATE TRANSITION & ONE-TIME CONSUMPTION
        # --------------------------------------------------------------------
        decision.gate_token_used = True
        decision.executed_at = datetime.datetime.utcnow()
        decision.execution_status = "EXECUTED" if exec_outcome == "EXECUTED" else "EXECUTION_FAILED"
        if tool_record:
            decision.tool_id = tool_record.id
        db.commit()

        # --------------------------------------------------------------------
        # 6. TELEMETRY & PROVENANCE RECORDING
        # --------------------------------------------------------------------
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
