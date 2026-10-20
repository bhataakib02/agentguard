"""
AgentGuard Phase 2B Regression Test Suite:
SSRF Prevention, Strict Destination IP Validation, DNS-Rebinding Defense,
and TOCTOU Connection Pinning.

Tests:
1. Public hostname resolving to public IP (Allowed).
2. Hostname resolving to private IP (Blocked).
3. Mixed public and private DNS answers (Fail closed).
4. Loopback, link-local, cloud metadata, IPv4-mapped IPv6, multicast, unspecified.
5. Noncanonical numeric host representations (octal, hex, dword, BSD shorthand).
6. Destination port policy enforcement and illegal schemes.
7. Userinfo / embedded credentials in URL rejected.
8. Malformed URLs rejected.
9. Redirects to private / metadata destinations blocked.
10. DNS rebinding / TOCTOU connection pinning verification exercising actual socket connection.
11. Production fail-closed enforcement and prohibition of test transport/resolver injection.
12. Full end-to-end tool proxy execution with gate token lifecycle, single-use consumption, and endpoint binding.
"""

import http.server
import ipaddress
import os
import socket
import sys
import threading
import time
import unittest
import uuid
import datetime
from typing import Any

import httpx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import settings
from database import SessionLocal
import models
from services.tool_proxy_service import (
    tool_proxy_service,
    PinningTransport,
    PinningNetworkBackend,
    parse_numeric_ipv4,
    DEFAULT_ALLOWED_PORTS,
    BLOCKED_HOSTNAMES,
    BLOCKED_METADATA_IPS,
)


class TestSSRFAndDNSRebinding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from database import Base, engine
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()
        cls.suffix = uuid.uuid4().hex[:6]

        cls.org = models.Organization(
            name=f"SSRF Test Org {cls.suffix}",
            slug=f"ssrf-test-org-{cls.suffix}",
            status="ACTIVE"
        )
        cls.db.add(cls.org)
        cls.db.commit()
        cls.db.refresh(cls.org)

        cls.user = models.User(
            email=f"ssrf_admin_{cls.suffix}@agentguard.test",
            password_hash="fake_hash_12345678",
            full_name="SSRF Admin",
            role="ADMIN",
            org_id=cls.org.id,
            status="ACTIVE"
        )
        cls.db.add(cls.user)
        cls.db.commit()
        cls.db.refresh(cls.user)

        cls.agent = models.Agent(
            org_id=cls.org.id,
            owner_id=cls.user.id,
            name="SSRF Verification Agent",
            agent_code=f"AG-SSRF-{cls.suffix}",
            purpose="SSRF and Rebinding Validation",
            status="NORMAL",
            autonomy_level="MEDIUM",
            daily_budget=1000.0
        )
        cls.db.add(cls.agent)
        cls.db.commit()
        cls.db.refresh(cls.agent)

    @classmethod
    def tearDownClass(cls):
        tool_proxy_service.set_dns_resolver(None)
        tool_proxy_service.set_mock_transport(None)
        tool_proxy_service.set_mock_client(None)
        cls.db.close()

    def setUp(self):
        self._orig_allow_local = os.environ.get("AGENTGUARD_ALLOW_LOCAL_TOOLS")
        tool_proxy_service.set_dns_resolver(None)
        tool_proxy_service.set_mock_transport(None)
        tool_proxy_service.set_mock_client(None)
        os.environ["AGENTGUARD_ALLOW_LOCAL_TOOLS"] = "false"

    def tearDown(self):
        tool_proxy_service.set_dns_resolver(None)
        tool_proxy_service.set_mock_transport(None)
        tool_proxy_service.set_mock_client(None)
        if self._orig_allow_local is not None:
            os.environ["AGENTGUARD_ALLOW_LOCAL_TOOLS"] = self._orig_allow_local
        else:
            os.environ.pop("AGENTGUARD_ALLOW_LOCAL_TOOLS", None)

    # =========================================================================
    # 1. PUBLIC HOSTNAME RESOLUTION
    # =========================================================================

    def test_public_hostname_resolving_to_public_address_is_allowed(self):
        """Public hostname resolving strictly to public IPs passes validation with pinned_ip."""
        tool_proxy_service.set_dns_resolver(lambda host, port: ["93.184.215.14"])
        res = tool_proxy_service._validate_ssrf_safety("https://legit-api.corp.com/v1/action")
        self.assertTrue(res["safe"], f"Expected safe, got: {res.get('reason')}")
        self.assertEqual(res["pinned_ip"], "93.184.215.14")
        self.assertEqual(res["port"], 443)

    # =========================================================================
    # 2. PRIVATE & INTERNAL HOSTNAME RESOLUTION
    # =========================================================================

    def test_hostname_resolving_to_private_address_is_blocked(self):
        """Hostname resolving to RFC 1918 private address must be blocked."""
        private_ips = ["10.0.0.1", "172.16.0.10", "192.168.1.100", "fc00::1"]
        for priv in private_ips:
            tool_proxy_service.set_dns_resolver(lambda host, port, ip=priv: [ip])
            res = tool_proxy_service._validate_ssrf_safety("http://internal-lookup.corp.com/api")
            self.assertFalse(res["safe"], f"Private IP {priv} should have been blocked")
            self.assertIn("prohibited address", res["reason"].lower())

    # =========================================================================
    # 3. MIXED PUBLIC / PRIVATE DNS RESPONSES
    # =========================================================================

    def test_mixed_public_and_private_dns_answers_fails_closed(self):
        """If DNS returns both public and private IP addresses, the request must fail closed."""
        tool_proxy_service.set_dns_resolver(lambda host, port: ["93.184.215.14", "10.0.0.1"])
        res = tool_proxy_service._validate_ssrf_safety("https://mixed-dns.corp.com/v1")
        self.assertFalse(res["safe"])
        self.assertIn("prohibited address '10.0.0.1'", res["reason"])

        # Reversed order: private first, then public
        tool_proxy_service.set_dns_resolver(lambda host, port: ["192.168.1.5", "8.8.8.8"])
        res2 = tool_proxy_service._validate_ssrf_safety("https://mixed-dns-2.corp.com/v1")
        self.assertFalse(res2["safe"])
        self.assertIn("prohibited address '192.168.1.5'", res2["reason"])

    # =========================================================================
    # 4. LOOPBACK, LINK-LOCAL, METADATA, IPV4-MAPPED IPV6, MULTICAST, UNSPECIFIED
    # =========================================================================

    def test_loopback_destinations_blocked(self):
        """Loopback addresses in IPv4 and IPv6 must be strictly blocked."""
        loopbacks = [
            "http://127.0.0.1:8080/metrics",
            "http://127.0.0.2:8000/api",
            "http://127.10.20.30:80/data",
            "http://[::1]:8080/status",
            "http://localhost:8080/test",
            "http://app.localhost:8000/test"
        ]
        for url in loopbacks:
            res = tool_proxy_service._validate_ssrf_safety(url)
            self.assertFalse(res["safe"], f"URL {url} should have been blocked")
            self.assertTrue(any(w in res["reason"].lower() for w in ("loopback", "localhost", "prohibited")))

    def test_cloud_metadata_destinations_blocked(self):
        """AWS/GCP/Azure/Alibaba cloud metadata IPs and hostnames must be strictly blocked."""
        metadata_targets = [
            "http://169.254.169.254/latest/meta-data/",
            "http://metadata.google.internal/computeMetadata/v1/",
            "http://metadata.goog/",
            "http://instance-data/latest/",
            "http://100.100.100.200/latest/meta-data/",
            "http://sub.metadata.google.internal/v1"
        ]
        for url in metadata_targets:
            res = tool_proxy_service._validate_ssrf_safety(url)
            self.assertFalse(res["safe"], f"Metadata URL {url} should have been blocked")
            self.assertTrue(any(w in res["reason"].lower() for w in ("metadata", "link-local", "prohibited")))

    def test_ipv4_mapped_ipv6_destinations_blocked(self):
        """IPv4-mapped IPv6 addresses targeting loopback, private, or metadata must be blocked."""
        mapped_targets = [
            "http://[::ffff:127.0.0.1]:8080/",
            "http://[::ffff:169.254.169.254]/latest/",
            "http://[::ffff:10.0.0.1]:8000/admin",
            "http://[::ffff:192.168.1.1]/"
        ]
        for url in mapped_targets:
            res = tool_proxy_service._validate_ssrf_safety(url)
            self.assertFalse(res["safe"], f"Mapped target {url} should have been blocked")

    def test_unspecified_and_multicast_destinations_blocked(self):
        """Unspecified (0.0.0.0, ::) and Multicast destinations must be blocked."""
        unspecified_multicast = [
            "http://0.0.0.0:8000/",
            "http://[::]:8080/",
            "http://224.0.0.1:8000/",
            "http://239.255.255.250:80/",
            "http://[ff02::1]:80/"
        ]
        for url in unspecified_multicast:
            res = tool_proxy_service._validate_ssrf_safety(url)
            self.assertFalse(res["safe"], f"Target {url} should have been blocked")

    # =========================================================================
    # 5. NONCANONICAL NUMERIC HOST REPRESENTATIONS
    # =========================================================================

    def test_noncanonical_numeric_address_edge_cases_blocked(self):
        """Octal, hex, dword, and BSD shorthand representations resolving to loopback/private must be blocked."""
        noncanonical_urls = [
            ("http://0177.0.0.1:8080/admin", "Octal loopback"),
            ("http://2130706433:8080/admin", "Dword integer 127.0.0.1"),
            ("http://0x7f000001:8080/admin", "Hexadecimal 127.0.0.1"),
            ("http://0x7f.1:8080/admin", "Hex shorthand 127.0.0.1"),
            ("http://127.1:8080/admin", "BSD 2-part shorthand 127.0.0.1"),
            ("http://0:8080/admin", "Single integer 0 -> 0.0.0.0"),
            ("http://017700000001:8080/admin", "Single octal 127.0.0.1")
        ]
        for url, desc in noncanonical_urls:
            res = tool_proxy_service._validate_ssrf_safety(url)
            self.assertFalse(res["safe"], f"{desc} ({url}) should have been blocked: {res}")

    def test_parse_numeric_ipv4_helper(self):
        """Unit test for parse_numeric_ipv4 decoding accuracy."""
        self.assertEqual(parse_numeric_ipv4("0177.0.0.1"), ipaddress.IPv4Address("127.0.0.1"))
        self.assertEqual(parse_numeric_ipv4("2130706433"), ipaddress.IPv4Address("127.0.0.1"))
        self.assertEqual(parse_numeric_ipv4("0x7f000001"), ipaddress.IPv4Address("127.0.0.1"))
        self.assertEqual(parse_numeric_ipv4("127.1"), ipaddress.IPv4Address("127.0.0.1"))
        self.assertEqual(parse_numeric_ipv4("0"), ipaddress.IPv4Address("0.0.0.0"))
        self.assertIsNone(parse_numeric_ipv4("example.com"))

    # =========================================================================
    # 6. PORT POLICY, SCHEMES, AND CREDENTIALS
    # =========================================================================

    def test_disallowed_destination_ports_blocked(self):
        """Non-web ports like SSH (22), SMTP (25), Postgres (5432), Redis (6379) must be rejected."""
        disallowed = [
            ("http://example.com:22/exec", 22),
            ("http://example.com:25/mail", 25),
            ("http://example.com:53/dns", 53),
            ("http://example.com:445/smb", 445),
            ("http://example.com:3306/sql", 3306),
            ("http://example.com:5432/db", 5432),
            ("http://example.com:6379/keys", 6379),
            ("http://example.com:9200/search", 9200),
            ("http://example.com:11211/cache", 11211),
            ("http://example.com:27017/mongo", 27017)
        ]
        for url, port in disallowed:
            res = tool_proxy_service._validate_ssrf_safety(url)
            self.assertFalse(res["safe"], f"Port {port} should have been rejected")
            self.assertIn("not permitted", res["reason"].lower())

    def test_allowed_ports_accepted(self):
        """Standard web ports (80, 443, 8000, 8080, 8443) must be accepted."""
        tool_proxy_service.set_dns_resolver(lambda host, port: ["93.184.215.14"])
        for p in [80, 443, 8000, 8080, 8443]:
            url = f"https://example.com:{p}/api" if p != 80 else f"http://example.com:{p}/api"
            res = tool_proxy_service._validate_ssrf_safety(url)
            self.assertTrue(res["safe"], f"Port {p} should be allowed: {res.get('reason')}")

    def test_embedded_credentials_in_url_rejected(self):
        """URLs containing userinfo/embedded credentials must be rejected."""
        bad_urls = [
            "http://user:password@example.com/api",
            "https://admin@example.com:8443/exec",
            "http://user:pass@127.0.0.1:8080/"
        ]
        for url in bad_urls:
            res = tool_proxy_service._validate_ssrf_safety(url)
            self.assertFalse(res["safe"])
            self.assertIn("embedded user credentials", res["reason"].lower())

    def test_illegal_schemes_and_malformed_urls_rejected(self):
        """Illegal schemes (ftp, gopher, file) and malformed URLs must be rejected."""
        bad_targets = [
            "file:///etc/passwd",
            "ftp://example.com/resource",
            "gopher://127.0.0.1:6379/_INFO",
            "http://",
            "https://",
            "http://   /test",
            "http://example .com/api"
        ]
        for target in bad_targets:
            res = tool_proxy_service._validate_ssrf_safety(target)
            self.assertFalse(res["safe"])

    # =========================================================================
    # 7. REDIRECTS TO PRIVATE / METADATA DESTINATIONS
    # =========================================================================

    def test_redirect_to_private_or_metadata_destination_is_blocked(self):
        """
        When downstream server returns a 302 redirect to metadata or private IP,
        the redirect must NOT be followed, and execution must record an error.
        """
        requests_received = []

        class RedirectHandler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length > 0:
                    self.rfile.read(content_length)
                requests_received.append(self.path)
                self.send_response(302)
                self.send_header("Location", "http://169.254.169.254/latest/meta-data/")
                self.end_headers()

            def log_message(self, format: str, *args: Any) -> None:
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), RedirectHandler)
        server_port = server.server_port
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()

        os.environ["AGENTGUARD_ALLOW_LOCAL_TOOLS"] = "true"
        try:
            tool_name = f"redirect_tool_{uuid.uuid4().hex[:6]}"
            target_url = f"http://127.0.0.1:{server_port}/redirect-me"

            tool = models.Tool(
                org_id=self.org.id,
                name=tool_name,
                endpoint=target_url,
                status="ACTIVE"
            )
            self.db.add(tool)
            self.db.commit()

            gate_token = f"gate_redir_{uuid.uuid4().hex}"
            dec = models.Decision(
                agent_id=self.agent.id,
                user_id=self.user.id,
                intent_summary="Redirect Test",
                action_requested="test_redirect",
                resource_target=tool_name,
                decision="ALLOW",
                explanation="Testing redirect prevention",
                execution_status="EXECUTED",
                execution_gate_token=gate_token,
                execution_parameters={"action": "test"},
                authorized_endpoint=target_url,
                gate_token_used=False,
                tool_id=tool.id,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            self.db.add(dec)
            self.db.commit()

            exec_res = tool_proxy_service.execute_tool(
                db=self.db,
                agent=self.agent,
                gate_token=gate_token,
                tool_name=tool_name,
                parameters={"action": "test"}
            )

            self.assertFalse(exec_res["success"])
            self.assertEqual(exec_res["status"], "EXECUTION_FAILED")
            self.assertIn("redirects are disabled for ssrf protection", exec_res["error"].lower())
            self.assertEqual(len(requests_received), 1)
        finally:
            server.shutdown()

    # =========================================================================
    # 8. DNS REBINDING / TOCTOU CONNECTION PINNING (ACTUAL NETWORK CONNECTION)
    # =========================================================================

    def test_dns_rebinding_connection_pinning_exercises_actual_socket(self):
        """
        Rigorous DNS-Rebinding Test:
        Exercises actual network TCP connection.
        Server A (Legitimate server, port A) and Server B (Internal target, port B).
        Simulated DNS:
          - At validation time: resolves to Server A's IP (127.0.0.1).
          - Immediately after validation (rebind): DNS switches to Server B's IP (127.0.0.2).
        Because PinningTransport pins the socket connection to Server A's IP,
        the HTTP request MUST arrive at Server A, and Server B MUST receive ZERO requests.
        """
        server_a_hits = []
        server_b_hits = []

        class HandlerA(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length > 0:
                    self.rfile.read(content_length)
                server_a_hits.append(self.path)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"server": "A", "status": "legit_executed"}')

            def log_message(self, format: str, *args: Any) -> None:
                pass

        class HandlerB(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length > 0:
                    self.rfile.read(content_length)
                server_b_hits.append(self.path)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"server": "B", "status": "ATTACK_SUCCESS"}')

            def log_message(self, format: str, *args: Any) -> None:
                pass

        # Bind both servers to ephemeral port on 127.0.0.1 and 127.0.0.2
        server_a = http.server.HTTPServer(("127.0.0.1", 0), HandlerA)
        port = server_a.server_port

        # Server B on 127.0.0.2 on the same port
        server_b = http.server.HTTPServer(("127.0.0.2", port), HandlerB)

        t_a = threading.Thread(target=server_a.serve_forever, daemon=True)
        t_b = threading.Thread(target=server_b.serve_forever, daemon=True)
        t_a.start()
        t_b.start()

        os.environ["AGENTGUARD_ALLOW_LOCAL_TOOLS"] = "true"
        dns_query_count = 0

        def rebinding_resolver(host, p):
            nonlocal dns_query_count
            dns_query_count += 1
            if dns_query_count == 1:
                # Time of check: returns Server A
                return ["127.0.0.1"]
            else:
                # Time of use (rebinding): returns Server B
                return ["127.0.0.2"]

        tool_proxy_service.set_dns_resolver(rebinding_resolver)

        try:
            tool_name = f"rebind_tool_{uuid.uuid4().hex[:6]}"
            target_url = f"http://rebind-test.internal:{port}/api/endpoint"

            tool = models.Tool(
                org_id=self.org.id,
                name=tool_name,
                endpoint=target_url,
                status="ACTIVE"
            )
            self.db.add(tool)
            self.db.commit()

            gate_token = f"gate_rebind_{uuid.uuid4().hex}"
            dec = models.Decision(
                agent_id=self.agent.id,
                user_id=self.user.id,
                intent_summary="Rebinding Defense Test",
                action_requested="call_rebind",
                resource_target=tool_name,
                decision="ALLOW",
                explanation="Validating connection pinning against DNS rebinding",
                execution_status="EXECUTED",
                execution_gate_token=gate_token,
                execution_parameters={"action": "test"},
                authorized_endpoint=target_url,
                gate_token_used=False,
                tool_id=tool.id,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            self.db.add(dec)
            self.db.commit()

            # Execute tool through proxy
            exec_res = tool_proxy_service.execute_tool(
                db=self.db,
                agent=self.agent,
                gate_token=gate_token,
                tool_name=tool_name,
                parameters={"action": "test"}
            )

            self.assertTrue(exec_res["success"], f"Execution failed: {exec_res}")
            self.assertEqual(exec_res["status"], "EXECUTED")
            self.assertEqual(exec_res["response_data"].get("server"), "A")

            # CRITICAL ASSERTION:
            # Server A received exactly 1 request.
            # Server B received 0 requests (DNS rebinding was completely neutralized by PinningTransport).
            self.assertEqual(len(server_a_hits), 1, "Server A must have received the connection")
            self.assertEqual(len(server_b_hits), 0, "Server B must NOT receive any connection (rebinding defeated)")
        finally:
            server_a.shutdown()
            server_b.shutdown()

    # =========================================================================
    # 9. PRODUCTION FAIL-CLOSED & MOCK PROHIBITION
    # =========================================================================

    def test_production_environment_blocks_mock_and_resolver_injection(self):
        """In production environment, setting mock transport, mock client, or DNS resolver raises RuntimeError."""
        old_env = getattr(settings, "ENVIRONMENT", "testing")
        try:
            settings.ENVIRONMENT = "production"
            self.assertFalse(tool_proxy_service.allow_local_egress)

            with self.assertRaises(RuntimeError):
                tool_proxy_service.set_mock_transport(httpx.MockTransport(lambda r: httpx.Response(200)))

            with self.assertRaises(RuntimeError):
                tool_proxy_service.set_mock_client(httpx.Client())

            with self.assertRaises(RuntimeError):
                tool_proxy_service.set_dns_resolver(lambda h, p: ["1.2.3.4"])
        finally:
            settings.ENVIRONMENT = old_env

    # =========================================================================
    # 10. ENDPOINT SNAPSHOT BINDING & GATE TOKEN LIFECYCLE PRESERVATION
    # =========================================================================

    def test_endpoint_snapshot_tamper_rejected_and_single_use_consumed(self):
        """Endpoint snapshot tampering is rejected; authorized execution consumes token atomically."""
        tool_name = f"snap_tool_{uuid.uuid4().hex[:6]}"
        ep_original = "https://example.com/v1/api"

        tool = models.Tool(
            org_id=self.org.id,
            name=tool_name,
            endpoint=ep_original,
            status="ACTIVE"
        )
        self.db.add(tool)
        self.db.commit()

        # Decision authorized for ep_original
        gate_token = f"gate_snap_{uuid.uuid4().hex}"
        dec = models.Decision(
            agent_id=self.agent.id,
            user_id=self.user.id,
            intent_summary="Snapshot Test",
            action_requested="call_snap",
            resource_target=tool_name,
            decision="ALLOW",
            explanation="Testing snapshot binding",
            execution_status="EXECUTED",
            execution_gate_token=gate_token,
            execution_parameters={"action": "test"},
            authorized_endpoint=ep_original,
            gate_token_used=False,
            tool_id=tool.id,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        self.db.add(dec)
        self.db.commit()

        # Tamper: update tool endpoint in database to a different URL
        setattr(tool, "endpoint", "https://example.com/v2/tampered")
        self.db.commit()

        res_tampered = tool_proxy_service.execute_tool(
            db=self.db,
            agent=self.agent,
            gate_token=gate_token,
            tool_name=tool_name,
            parameters={"action": "test"}
        )
        self.assertFalse(res_tampered["success"])
        self.assertEqual(res_tampered["status"], "NOT_AUTHORIZED")
        self.assertIn("endpoint configuration has changed", res_tampered["error"].lower())

        # Restore endpoint and execute with mock transport
        setattr(tool, "endpoint", ep_original)
        self.db.commit()

        mock_transport = httpx.MockTransport(lambda req: httpx.Response(200, json={"status": "snapshot_ok"}))
        tool_proxy_service.set_mock_transport(mock_transport)

        res_valid = tool_proxy_service.execute_tool(
            db=self.db,
            agent=self.agent,
            gate_token=gate_token,
            tool_name=tool_name,
            parameters={"action": "test"}
        )
        self.assertTrue(res_valid["success"], f"Expected success: {res_valid}")
        self.assertEqual(res_valid["status"], "EXECUTED")

        # Sequential replay of consumed token must fail
        res_replay = tool_proxy_service.execute_tool(
            db=self.db,
            agent=self.agent,
            gate_token=gate_token,
            tool_name=tool_name,
            parameters={"action": "test"}
        )
        self.assertFalse(res_replay["success"])
        self.assertEqual(res_replay["status"], "GATE_TOKEN_REPLAYED")
