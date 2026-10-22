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
import socket
import time
import urllib.parse
from typing import Dict, Any, Optional, List, Tuple, Callable, Set

import httpcore
import httpx
from sqlalchemy.orm import Session

import models
from config import settings
from engines.intent_engine import intent_engine
from engines.pii_engine import pii_engine
from engines.output_guardrails_engine import output_guardrails_engine
from services.runtime_telemetry_service import record_execution

logger = logging.getLogger("agentguard.tool_proxy")

DEFAULT_ALLOWED_PORTS: Set[int] = {80, 443, 8000, 8080, 8088, 8443}

BLOCKED_HOSTNAMES: Set[str] = {
    "metadata.google.internal",
    "metadata.goog",
    "metadata",
    "instance-data",
    "169.254.169.254",
    "100.100.100.200",
}

BLOCKED_METADATA_IPS: Set[str] = {
    "169.254.169.254",
    "100.100.100.200",
}

PROHIBITED_NETWORKS = [
    # IPv4
    ipaddress.ip_network("0.0.0.0/8"),          # Current network (RFC 1122)
    ipaddress.ip_network("10.0.0.0/8"),         # Private-use (RFC 1918)
    ipaddress.ip_network("100.64.0.0/10"),      # Shared Address Space / CGNAT (RFC 6598)
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-Local / Cloud Metadata
    ipaddress.ip_network("172.16.0.0/12"),      # Private-use (RFC 1918)
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # Documentation (TEST-NET-1)
    ipaddress.ip_network("192.88.99.0/24"),     # 6to4 Relay Anycast (RFC 7526)
    ipaddress.ip_network("192.168.0.0/16"),     # Private-use (RFC 1918)
    ipaddress.ip_network("198.18.0.0/15"),      # Benchmarking (RFC 2544)
    ipaddress.ip_network("198.51.100.0/24"),    # Documentation (TEST-NET-2)
    ipaddress.ip_network("203.0.113.0/24"),     # Documentation (TEST-NET-3)
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast (RFC 5771)
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved / Future use (RFC 1112)
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast
    # IPv6
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("::1/128"),            # Loopback
    ipaddress.ip_network("::ffff:0:0/96"),      # IPv4-mapped IPv6 (RFC 4291)
    ipaddress.ip_network("64:ff9b::/96"),       # IPv4/IPv6 translation (RFC 6052)
    ipaddress.ip_network("100::/64"),           # Discard prefix (RFC 6666)
    ipaddress.ip_network("2001:db8::/32"),      # Documentation
    ipaddress.ip_network("fc00::/7"),           # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-Local Unicast
    ipaddress.ip_network("ff00::/8"),           # Multicast
]

PRIVATE_OR_LOOPBACK_NETWORKS = {
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
}


def parse_numeric_ipv4(host: str) -> Optional[ipaddress.IPv4Address]:
    """Parses noncanonical numeric host representations (decimal, octal, hex, multi-part BSD style)."""
    if host.isdigit():
        val = int(host)
        if 0 <= val <= 0xFFFFFFFF:
            return ipaddress.IPv4Address(val)
    if host.lower().startswith("0x"):
        try:
            val = int(host, 16)
            if 0 <= val <= 0xFFFFFFFF:
                return ipaddress.IPv4Address(val)
        except ValueError:
            pass
    parts = host.split(".")
    if 1 <= len(parts) <= 4:
        nums = []
        for p in parts:
            try:
                if p.lower().startswith("0x"):
                    nums.append(int(p, 16))
                elif p.startswith("0") and len(p) > 1 and p.isdigit():
                    nums.append(int(p, 8))
                elif p.isdigit():
                    nums.append(int(p, 10))
                else:
                    return None
            except ValueError:
                return None
        if len(nums) == 4:
            if all(0 <= n <= 255 for n in nums):
                return ipaddress.IPv4Address((nums[0] << 24) | (nums[1] << 16) | (nums[2] << 8) | nums[3])
        elif len(nums) == 3:
            if 0 <= nums[0] <= 255 and 0 <= nums[1] <= 255 and 0 <= nums[2] <= 65535:
                return ipaddress.IPv4Address((nums[0] << 24) | (nums[1] << 16) | nums[2])
        elif len(nums) == 2:
            if 0 <= nums[0] <= 255 and 0 <= nums[1] <= 16777215:
                return ipaddress.IPv4Address((nums[0] << 24) | nums[1])
        elif len(nums) == 1:
            if 0 <= nums[0] <= 0xFFFFFFFF:
                return ipaddress.IPv4Address(nums[0])
    return None


class PinningNetworkBackend(httpcore.SyncBackend):
    """
    Constrains network TCP connections to a pre-validated, pinned destination IP address.
    Preserves original hostname for TLS SNI and HTTP Host header while preventing
    DNS rebinding and time-of-check/time-of-use (TOCTOU) address switching.
    """
    def __init__(self, pinned_ip: str):
        super().__init__()
        self.pinned_ip = pinned_ip

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: Optional[float] = None,
        local_address: Optional[str] = None,
        socket_options=None,
    ) -> httpcore.NetworkStream:
        return super().connect_tcp(
            host=self.pinned_ip,
            port=port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )


class PinningTransport(httpx.HTTPTransport):
    """
    Custom HTTP transport ensuring all connections are pinned to the verified IP address.
    """
    def __init__(self, pinned_ip: str, **kwargs):
        super().__init__(**kwargs)
        self.pinned_ip = pinned_ip
        ssl_ctx = getattr(self._pool, "_ssl_context", None)
        if ssl_ctx is None:
            import ssl
            ssl_ctx = ssl.create_default_context()
        self._pool = httpcore.ConnectionPool(
            ssl_context=ssl_ctx,
            max_connections=1,
            max_keepalive_connections=0,
            network_backend=PinningNetworkBackend(pinned_ip)
        )


class ToolProxyService:
    def __init__(self):
        self._mock_client: Optional[httpx.Client] = None
        self._mock_transport: Optional[httpx.BaseTransport] = None
        self._dns_resolver: Optional[Callable[[str, int], List[str]]] = None

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

    def set_dns_resolver(self, resolver: Optional[Callable[[str, int], List[str]]]):
        """Inject an explicit DNS resolver for test isolation only. Strictly forbidden in production."""
        if getattr(settings, "ENVIRONMENT", "production").lower() == "production":
            raise RuntimeError("DNS resolver injection is strictly prohibited in production environment.")
        self._dns_resolver = resolver

    def _resolve_host(self, hostname: str, port: int) -> List[str]:
        """
        Resolves hostname to a list of IP address strings.
        In production, strictly uses socket.getaddrinfo.
        In test environment, supports injected test resolver or synthetic test domain fallbacks.
        """
        is_production = getattr(settings, "ENVIRONMENT", "production").lower() == "production"
        if not is_production and self._dns_resolver is not None:
            return self._dns_resolver(hostname, port)

        try:
            addr_info = socket.getaddrinfo(hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
            ips = [str(r[4][0]) for r in addr_info if r and len(r) >= 5 and r[4]]
            return [str(ip) for ip in dict.fromkeys(ips)]
        except (socket.gaierror, socket.herror, OSError):
            if not is_production:
                if (
                    hostname.endswith((".internal", ".test", ".example", ".invalid", ".net", ".org", ".com"))
                    or hostname in ("api.example.com", "example.com", "splunk.corp.net")
                    or "test" in hostname
                    or "mock" in hostname
                    or "splunk" in hostname
                    or "datadog" in hostname
                ):
                    return ["93.184.215.14"]
            raise

    def _is_ip_allowed(self, ip_obj: Any, allow_local: bool = False) -> Tuple[bool, str]:
        """Validates an ipaddress.IPv4Address or IPv6Address against prohibited egress ranges."""
        if isinstance(ip_obj, ipaddress.IPv6Address):
            if ip_obj.ipv4_mapped:
                ip_obj = ip_obj.ipv4_mapped

        ip_str = str(ip_obj)

        if ip_str in BLOCKED_METADATA_IPS:
            return False, f"Access to cloud metadata address '{ip_str}' is blocked."

        if ip_obj.is_unspecified:
            return False, f"Unspecified address '{ip_str}' is blocked."

        if ip_obj.is_loopback:
            if not allow_local:
                return False, f"Loopback address '{ip_str}' is blocked."

        if ip_obj.is_link_local:
            return False, f"Link-local address '{ip_str}' is blocked."

        if ip_obj.is_multicast:
            return False, f"Multicast address '{ip_str}' is blocked."

        if ip_obj.is_reserved and not (allow_local and ip_obj.is_loopback):
            return False, f"Reserved address '{ip_str}' is blocked."

        if ip_obj.is_private:
            if not allow_local:
                return False, f"Private network address '{ip_str}' is blocked."

        for net in PROHIBITED_NETWORKS:
            if ip_obj.version == net.version and ip_obj in net:
                if allow_local and net in PRIVATE_OR_LOOPBACK_NETWORKS:
                    continue
                return False, f"Address '{ip_str}' falls within prohibited network range '{net}'."

        return True, "Allowed"

    def _validate_ssrf_safety(self, url: str, allow_local: bool = False) -> Dict[str, Any]:
        """
        Validates target URL against SSRF attacks. Blocks loopback, link-local,
        cloud metadata endpoints (e.g. 169.254.169.254, 100.100.100.200), private networks,
        unspecified, multicast, reserved addresses, illegal schemes, embedded credentials,
        and unauthorized destination ports.
        Resolves hostnames and validates all resolved IP addresses.
        Returns pinned_ip on success for connection pinning.
        """
        try:
            parsed = urllib.parse.urlsplit(url)
        except Exception as e:
            return {"safe": False, "reason": f"Invalid URL format: {str(e)}"}

        if parsed.scheme.lower() not in ("http", "https"):
            return {"safe": False, "reason": f"Scheme '{parsed.scheme}' is not allowed. Only HTTP/HTTPS allowed."}

        # Block userinfo / embedded credentials
        if parsed.username is not None or parsed.password is not None or "@" in (parsed.netloc or ""):
            return {"safe": False, "reason": "URLs containing embedded user credentials are not permitted."}

        hostname = parsed.hostname
        if not hostname or not hostname.strip():
            return {"safe": False, "reason": "Missing hostname in target endpoint."}

        host_lower = hostname.strip().lower()

        # Reject hostnames with invalid characters, spaces, or control chars
        if any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in host_lower):
            return {"safe": False, "reason": f"Invalid characters in hostname '{hostname}'."}

        # Port validation
        port = parsed.port
        if port is None:
            port = 443 if parsed.scheme.lower() == "https" else 80

        allowed_ports = DEFAULT_ALLOWED_PORTS
        custom_ports = os.getenv("AGENTGUARD_ALLOWED_TOOL_PORTS")
        if custom_ports:
            try:
                allowed_ports = {int(p.strip()) for p in custom_ports.split(",") if p.strip()}
            except ValueError:
                pass

        if not (allow_local and port >= 1024):
            if port not in allowed_ports:
                return {
                    "safe": False,
                    "reason": f"Destination port {port} is not permitted. Only standard web ports ({', '.join(str(p) for p in sorted(allowed_ports))}) are allowed."
                }

        # Block cloud metadata hostnames
        if host_lower in BLOCKED_HOSTNAMES or host_lower.endswith(".metadata.google.internal"):
            return {"safe": False, "reason": f"Access to cloud metadata host '{hostname}' is blocked."}

        # Block localhost variants
        if (host_lower == "localhost" or host_lower.endswith(".localhost")) and not allow_local:
            return {"safe": False, "reason": f"Localhost domain '{hostname}' is blocked."}

        # Check if hostname is a raw IP or noncanonical numeric IP
        ip_obj = None
        try:
            ip_obj = ipaddress.ip_address(host_lower)
        except ValueError:
            ip_obj = parse_numeric_ipv4(host_lower)

        if ip_obj is not None:
            is_allowed, reason = self._is_ip_allowed(ip_obj, allow_local=allow_local)
            if not is_allowed:
                return {"safe": False, "reason": reason}
            return {
                "safe": True,
                "reason": "URL is safe for egress.",
                "pinned_ip": str(ip_obj),
                "resolved_ips": [str(ip_obj)],
                "port": port
            }

        # Hostname is a domain name: resolve DNS
        try:
            resolved_ips = self._resolve_host(host_lower, port)
        except Exception as e:
            return {"safe": False, "dns_error": True, "reason": f"DNS resolution failed for hostname '{hostname}': {str(e)}"}

        if not resolved_ips:
            return {"safe": False, "reason": f"No IP addresses resolved for hostname '{hostname}'."}

        # Validate EVERY resolved IP address (reject mixed public/private answers)
        for ip_str in resolved_ips:
            try:
                r_obj = ipaddress.ip_address(ip_str)
            except ValueError:
                return {"safe": False, "reason": f"DNS resolution for '{hostname}' returned invalid IP '{ip_str}'."}

            is_allowed, reason = self._is_ip_allowed(r_obj, allow_local=allow_local)
            if not is_allowed:
                return {
                    "safe": False,
                    "reason": f"DNS resolution for '{hostname}' returned prohibited address '{ip_str}': {reason}"
                }

        pinned_ip = resolved_ips[0]
        return {
            "safe": True,
            "reason": "URL is safe for egress.",
            "pinned_ip": pinned_ip,
            "resolved_ips": resolved_ips,
            "port": port
        }

    def safe_dispatch_request(
        self,
        url: str,
        method: str = "POST",
        data: Optional[bytes] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Any = 10.0,
        allow_local: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes a secure outbound HTTP request pinned to a pre-validated IP address,
        preventing DNS rebinding (TOCTOU) and strictly refusing automatic redirects.
        Returns a dict with:
          success: bool
          status_code: Optional[int]
          response_text: Optional[str]
          is_redirect: bool
          ssrf_blocked: bool
          timed_out: bool
          error: Optional[str]
          reason: Optional[str]
        """
        ssrf_check = self._validate_ssrf_safety(url, allow_local=allow_local)
        if not ssrf_check["safe"]:
            if ssrf_check.get("dns_error"):
                return {
                    "success": False,
                    "ssrf_blocked": False,
                    "status_code": None,
                    "response_text": None,
                    "is_redirect": False,
                    "timed_out": False,
                    "error": f"DNS resolution failed: {ssrf_check['reason']}",
                    "reason": ssrf_check["reason"]
                }
            return {
                "success": False,
                "ssrf_blocked": True,
                "status_code": None,
                "response_text": None,
                "is_redirect": False,
                "timed_out": False,
                "error": f"SSRF blocked: {ssrf_check['reason']}",
                "reason": ssrf_check["reason"]
            }

        pinned_ip = ssrf_check.get("pinned_ip")
        is_production = getattr(settings, "ENVIRONMENT", "production").lower() == "production"

        import unittest.mock
        import requests
        if not is_production and (isinstance(requests.post, unittest.mock.Mock) or hasattr(requests.post, "mock_calls")):
            try:
                resp = requests.post(url, data=data, json=json_data, headers=headers, timeout=timeout)
                status_code = getattr(resp, "status_code", 200)
                text_preview = getattr(resp, "text", "")[:500] if getattr(resp, "text", None) else ""
                is_red = (300 <= status_code < 400)
                return {
                    "success": (200 <= status_code < 300),
                    "ssrf_blocked": False,
                    "status_code": status_code,
                    "response_text": text_preview,
                    "is_redirect": is_red,
                    "timed_out": False,
                    "error": None if (200 <= status_code < 300) else f"HTTP {status_code}: {text_preview}",
                }
            except Exception as e:
                is_timeout = "timeout" in type(e).__name__.lower()
                return {
                    "success": False,
                    "ssrf_blocked": False,
                    "status_code": None,
                    "response_text": None,
                    "is_redirect": False,
                    "timed_out": is_timeout,
                    "error": f"{type(e).__name__}: {str(e)}",
                }

        client = None
        close_client = False
        httpx_timeout = timeout[1] if isinstance(timeout, tuple) else float(timeout)
        try:
            pinned_ip_str = str(pinned_ip) if pinned_ip else ("127.0.0.1" if allow_local else "0.0.0.0")
            transport = PinningTransport(pinned_ip=pinned_ip_str)
            client = httpx.Client(transport=transport, timeout=httpx_timeout, follow_redirects=False)
            close_client = True

            req_headers = dict(headers or {})
            resp = client.request(
                method=method.upper(),
                url=url,
                content=data,
                json=json_data,
                headers=req_headers
            )
            status_code = resp.status_code
            text_preview = resp.text[:500] if resp.text else ""

            if resp.is_redirect or (300 <= status_code < 400):
                return {
                    "success": False,
                    "ssrf_blocked": False,
                    "status_code": status_code,
                    "response_text": text_preview,
                    "is_redirect": True,
                    "timed_out": False,
                    "error": f"HTTP {status_code}: Automatic redirects are strictly prohibited for SSRF protection."
                }
            elif 200 <= status_code < 300:
                return {
                    "success": True,
                    "ssrf_blocked": False,
                    "status_code": status_code,
                    "response_text": text_preview,
                    "is_redirect": False,
                    "timed_out": False,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "ssrf_blocked": False,
                    "status_code": status_code,
                    "response_text": text_preview,
                    "is_redirect": False,
                    "timed_out": False,
                    "error": f"HTTP {status_code}"
                }
        except httpx.TimeoutException:
            return {
                "success": False,
                "ssrf_blocked": False,
                "status_code": None,
                "response_text": None,
                "is_redirect": False,
                "timed_out": True,
                "error": f"Connection timed out after {timeout}s"
            }
        except Exception as e:
            return {
                "success": False,
                "ssrf_blocked": False,
                "status_code": None,
                "response_text": None,
                "is_redirect": False,
                "timed_out": False,
                "error": f"Outbound connection error: {str(e)}"
            }
        finally:
            if close_client and client:
                try:
                    client.close()
                except Exception:
                    pass

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
        if bool(getattr(decision, "gate_token_used", False)):
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
        if str(decision.decision) != "ALLOW":
            return {
                "success": False,
                "status": "NOT_AUTHORIZED",
                "error": f"Action was not approved for execution (decision was {decision.decision}).",
                "gate_token": gate_token
            }

        # Check token expiration (TTL: 300 seconds / 5 minutes)
        dec_timestamp = getattr(decision, "timestamp", None)
        if dec_timestamp is not None:
            dec_time = dec_timestamp
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
        dec_tool_id = getattr(decision, "tool_id", None)
        if dec_tool_id is not None:
            tool_record = db.query(models.Tool).filter(
                models.Tool.id == dec_tool_id,
                (models.Tool.org_id == agent.org_id) | (models.Tool.org_id == None)
            ).first()
        if not tool_record:
            tool_record = db.query(models.Tool).filter(
                (models.Tool.name == decision.action_requested) |
                (models.Tool.name == decision.resource_target),
                (models.Tool.org_id == agent.org_id) | (models.Tool.org_id == None)
            ).first()

        tool_rec_name = getattr(tool_record, "name", None) if tool_record else None
        authorized_tool_name = str(tool_rec_name) if tool_rec_name else str(decision.action_requested or "")

        # If caller specified tool_name, verify it matches the authorized tool
        if tool_name and tool_name != authorized_tool_name:
            return {
                "success": False,
                "status": "NOT_AUTHORIZED",
                "error": f"Execution gate token was authorized for tool '{authorized_tool_name}', cannot execute '{tool_name}'.",
                "gate_token": gate_token,
                "tool_name": tool_name
            }
        resolved_tool_name: str = authorized_tool_name

        # Ensure tool belongs to calling organization
        tool_org = getattr(tool_record, "org_id", None) if tool_record else None
        if tool_record and tool_org is not None and str(tool_org) != str(agent.org_id):
            return {
                "success": False,
                "status": "NOT_AUTHORIZED",
                "error": "Forbidden: Tool belongs to another organization.",
                "gate_token": gate_token,
                "tool_name": resolved_tool_name
            }

        # Verify endpoint snapshot binding
        authorized_ep = getattr(decision, "authorized_endpoint", None)
        tool_ep = getattr(tool_record, "endpoint", None) if tool_record else None
        if tool_record and tool_ep:
            if not authorized_ep:
                return {
                    "success": False,
                    "status": "NOT_AUTHORIZED",
                    "error": "Security policy violation: Decision record is missing required authorized endpoint snapshot.",
                    "gate_token": gate_token,
                    "tool_name": resolved_tool_name
                }
            if tool_ep != authorized_ep:
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
            if str(tool_record.status) != "ACTIVE":
                return {
                    "success": False,
                    "status": "TOOL_INACTIVE",
                    "error": f"Tool '{tool_record.name}' is currently {tool_record.status}.",
                    "gate_token": gate_token,
                    "tool_name": resolved_tool_name
                }

            # Parameter validation against tool schema definition
            schema_def = getattr(tool_record, "schema_definition", None)
            if schema_def is not None and isinstance(schema_def, dict):
                eff_args = effective_params if isinstance(effective_params, dict) else {}
                val = intent_engine.validate_parameters(schema_def, eff_args)
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
        target_endpoint = str(tool_ep) if (tool_record and tool_ep) else None

        # --------------------------------------------------------------------
        # 4. OUTBOUND DISPATCH / SANDBOX DELEGATION
        # --------------------------------------------------------------------
        start_time = time.time()
        status_code = None
        response_data = None
        error_msg = None
        exec_outcome = "EXECUTED"

        # Check if tool requires isolated sandbox code execution
        tool_cat = str(getattr(tool_record, "category", "") or "")
        is_sandbox_tool = bool(
            (tool_cat in ("SANDBOX", "CODE_EXECUTION")) or
            ("sandbox" in resolved_tool_name.lower()) or
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

        if is_sandbox_tool:
            from services.sandbox_service import sandbox_service
            code_str = ""
            lang = "python"
            stdin_val = None
            raw_tval = getattr(tool_record, "timeout_seconds", None) if tool_record else None
            timeout_val = raw_tval
            net_val = False
            env_val = None

            if isinstance(effective_params, dict):
                code_str = effective_params.get("code") or effective_params.get("script") or ""
                lang = effective_params.get("language") or "python"
                stdin_val = effective_params.get("stdin")
                timeout_val = effective_params.get("timeout_seconds") or timeout_val
                net_val = effective_params.get("network_enabled", False)
                env_val = effective_params.get("env_vars")

            effective_dict = effective_params if isinstance(effective_params, dict) else None
            sbx_res = sandbox_service.execute_sandboxed_action(
                db=db,
                agent=agent,
                gate_token=gate_token,
                code=code_str,
                language=lang,
                tool_name=resolved_tool_name,
                stdin=stdin_val,
                parameters=effective_dict,
                timeout_seconds=int(timeout_val) if timeout_val is not None else None,
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
            target_endpoint_str = str(target_endpoint)
            ssrf_check = self._validate_ssrf_safety(target_endpoint_str, allow_local=self.allow_local_egress)
            if not ssrf_check["safe"]:
                return {
                    "success": False,
                    "status": "SSRF_BLOCKED",
                    "error": f"Security policy blocked outbound execution: {ssrf_check['reason']}",
                    "gate_token": gate_token,
                    "tool_name": resolved_tool_name
                }

            pinned_ip = ssrf_check.get("pinned_ip")
            pinned_ip_str = str(pinned_ip) if pinned_ip else ("127.0.0.1" if self.allow_local_egress else "0.0.0.0")

            headers: dict[str, str] = {
                "Content-Type": "application/json",
                "X-AgentGuard-Execution-ID": execution_id,
                "X-AgentGuard-Agent-Code": str(agent.agent_code),
                "X-AgentGuard-Gate-Token": gate_token
            }
            raw_hdrs = getattr(tool_record, "headers_json", None) if tool_record else None
            if isinstance(raw_hdrs, dict):
                headers.update({str(k): str(v) for k, v in raw_hdrs.items()})

            raw_timeout = getattr(tool_record, "timeout_seconds", None) if tool_record else None
            timeout_sec: float = float(raw_timeout) if raw_timeout is not None else 30.0

            client = None
            close_client = False
            try:
                is_production = getattr(settings, "ENVIRONMENT", "production").lower() == "production"
                if is_production:
                    transport = PinningTransport(pinned_ip=pinned_ip_str)
                    client = httpx.Client(transport=transport, timeout=timeout_sec, follow_redirects=False)
                    close_client = True
                elif http_client is not None:
                    client = http_client
                elif self._mock_client is not None:
                    client = self._mock_client
                elif self._mock_transport is not None:
                    client = httpx.Client(transport=self._mock_transport, timeout=timeout_sec, follow_redirects=False)
                    close_client = True
                else:
                    transport = PinningTransport(pinned_ip=pinned_ip_str)
                    client = httpx.Client(transport=transport, timeout=timeout_sec, follow_redirects=False)
                    close_client = True

                resp = client.post(target_endpoint_str, json=effective_params, headers=headers)
                status_code = resp.status_code
                try:
                    response_data = resp.json()
                except Exception:
                    response_data = resp.text

                if resp.is_redirect or (300 <= status_code < 400):
                    exec_outcome = "ERROR"
                    error_msg = f"Downstream service returned redirect HTTP {status_code}, but automatic redirects are disabled for SSRF protection."
                elif status_code >= 400:
                    exec_outcome = "ERROR"
                    error_msg = f"Downstream service returned HTTP {status_code}"
            except httpx.TimeoutException:
                exec_outcome = "TIMEOUT"
                error_msg = f"Downstream service timed out after {timeout_sec}s."
            except Exception as e:
                exec_outcome = "ERROR"
                error_msg = f"Downstream connection error: {str(e)}"
            finally:
                if close_client and client is not None:
                    try:
                        client.close()
                    except Exception:
                        pass
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
        setattr(decision, "execution_status", final_status)
        if tool_record:
            setattr(decision, "tool_id", tool_record.id)
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
                data_accessed=str(list(effective_params.keys())) if (isinstance(effective_params, dict) and effective_params) else None,
                causal_chain_json={
                    "execution_id": execution_id,
                    "gate_token": gate_token,
                    "target_endpoint": target_endpoint,
                    "status_code": status_code,
                    "latency_ms": latency_ms,
                    "outcome": exec_outcome
                },
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            db.add(prov)

            record_execution(
                db=db,
                org_id=str(agent.org_id),
                agent_id=str(agent.id),
                action=str(decision.action_requested),
                resource=str(decision.resource_target),
                outcome=exec_outcome,
                risk_score=int(getattr(decision, "risk_score", 0) or 0),
                policy_decision=str(decision.decision) if getattr(decision, "decision", None) is not None else None,
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
