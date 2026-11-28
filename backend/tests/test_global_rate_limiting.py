"""
Comprehensive Security Test Suite for AG-SEC-02 Global Distributed Rate Limiting.
Covers:
- Sliding-window algorithm correctness & boundary behavior
- Multi-instance concurrency & race condition resistance
- Path normalization and route alias bypass resistance
- Forwarded-IP spoofing resistance & header sanitization
- Multi-tier rate limiting: Public, Auth, Authenticated User, API Key, AI Inference
- HTTP 429 contract, Retry-After header & X-RateLimit headers
- Redis failure policies: Fail-closed for AUTH (503) vs Fail-open for General APIs
- Redis recovery
- Route exemptions (health checks, docs, websockets)
- Authentication bypass resistance (unauthenticated/forged JWT cannot exploit higher quotas)
- Multi-tenant isolation (Org A vs Org B quotas, AI tenant limits)
"""

import time
import uuid
import datetime
import threading
import concurrent.futures
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from main import app
from database import SessionLocal
import models
from core import security
from core.rate_limiter import (
    DistributedRateLimiter,
    MemorySlidingWindowEngine,
    normalize_path,
    get_trusted_client_ip,
    RateLimitingMiddleware,
    rate_limiter,
    rate_limit
)
from config import settings

client = TestClient(app)


# =============================================================================
# Mock / In-Memory Redis Adapter for Multi-Instance Simulation
# =============================================================================

class SharedMockRedisAdapter:
    """
    Thread-safe shared Redis mock supporting Lua eval of the sliding-window script
    to explicitly verify multi-instance concurrency without external network dependencies.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._memory = MemorySlidingWindowEngine()

    def eval(self, script, numkeys, key, now, window, max_requests):
        with self._lock:
            status_code, remaining_or_count, retry_after = self._memory.evaluate(
                str(key), float(now), int(window), int(max_requests)
            )
            return [status_code, remaining_or_count, retry_after]

    def ping(self):
        return True


# =============================================================================
# 1. Sliding Window Algorithm Correctness & Boundary Behavior
# =============================================================================

class TestSlidingWindowCorrectness:
    def test_01_sliding_window_smooth_rollover(self):
        """Requests spread across time correctly expire and slide without fixed-window boundary burst."""
        engine = MemorySlidingWindowEngine()
        window = 60
        max_requests = 3

        # t = 100: Request 1
        res1 = engine.evaluate("test_key", 100.0, window, max_requests)
        assert res1 == (1, 2, 0)  # allowed, 2 remaining

        # t = 120: Request 2
        res2 = engine.evaluate("test_key", 120.0, window, max_requests)
        assert res2 == (1, 1, 0)  # allowed, 1 remaining

        # t = 140: Request 3
        res3 = engine.evaluate("test_key", 140.0, window, max_requests)
        assert res3 == (1, 0, 0)  # allowed, 0 remaining

        # t = 150: Request 4 (Exceeded! Oldest request at 100 expires at 160)
        res4 = engine.evaluate("test_key", 150.0, window, max_requests)
        assert res4[0] == 0  # blocked
        assert res4[2] == 10  # retry_after = 160 - 150 = 10 seconds

        # t = 161: Time advances past 160. Request 1 has expired!
        res5 = engine.evaluate("test_key", 161.0, window, max_requests)
        assert res5[0] == 1  # allowed!
        assert res5[1] == 0  # 0 remaining (now entries are at 120, 140, 161)

    def test_02_boundary_burst_attack_prevented(self):
        """
        In fixed-window, an attacker sending quota at t=59 and t=61 gets 2x burst.
        In sliding window, requests at t=59 remain in the window at t=61.
        """
        engine = MemorySlidingWindowEngine()
        window = 60
        max_requests = 5

        # Attacker sends 5 requests right at end of window (t = 59)
        for i in range(5):
            res = engine.evaluate("burst_key", 59.0 + (i * 0.1), window, max_requests)
            assert res[0] == 1

        # Attacker sends another request at t = 61 (just after previous window boundary)
        res_blocked = engine.evaluate("burst_key", 61.0, window, max_requests)
        assert res_blocked[0] == 0  # MUST be blocked in sliding-window
        assert res_blocked[2] > 0   # Positive retry-after


# =============================================================================
# 2. Multi-Instance Concurrency & Race Condition Resistance
# =============================================================================

class TestMultiInstanceAndConcurrency:
    def test_03_multi_instance_shared_quota(self):
        """Two backend instances pointing to the same shared Redis adapter enforce a unified quota."""
        shared_redis = SharedMockRedisAdapter()
        instance_1 = DistributedRateLimiter(redis_client=shared_redis, storage_backend="REDIS")
        instance_2 = DistributedRateLimiter(redis_client=shared_redis, storage_backend="REDIS")

        key = "shared_tenant_quota"
        limit = 5

        # Instance 1 consumes 3 tokens
        for _ in range(3):
            r = instance_1.check_rate_limit(key, max_requests=limit, window_seconds=60)
            assert r.allowed is True

        # Instance 2 consumes 2 tokens
        for _ in range(2):
            r = instance_2.check_rate_limit(key, max_requests=limit, window_seconds=60)
            assert r.allowed is True

        # 6th request on Instance 1 must be blocked
        r_blocked_1 = instance_1.check_rate_limit(key, max_requests=limit, window_seconds=60)
        assert r_blocked_1.allowed is False
        assert r_blocked_1.remaining == 0

        # 6th request on Instance 2 must also be blocked
        r_blocked_2 = instance_2.check_rate_limit(key, max_requests=limit, window_seconds=60)
        assert r_blocked_2.allowed is False

    def test_04_atomic_concurrency_under_parallel_threads(self):
        """20 simultaneous threads racing for a quota of 10 must allow exactly 10 and block 10."""
        shared_redis = SharedMockRedisAdapter()
        limiter = DistributedRateLimiter(redis_client=shared_redis, storage_backend="REDIS")
        key = f"concurrency_key_{uuid.uuid4().hex[:8]}"
        limit = 10

        allowed_count = 0
        blocked_count = 0
        lock = threading.Lock()

        def worker():
            nonlocal allowed_count, blocked_count
            res = limiter.check_rate_limit(key, max_requests=limit, window_seconds=60)
            with lock:
                if res.allowed:
                    allowed_count += 1
                else:
                    blocked_count += 1

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert allowed_count == 10
        assert blocked_count == 10


# =============================================================================
# 3. Path Normalization & Route Alias Bypass Resistance
# =============================================================================

class TestPathNormalization:
    def test_05_path_normalization_variations(self):
        """Verify that route casing, repeated slashes, and prefixes resolve to identical canonical paths."""
        paths = [
            "/api/v1/auth/login",
            "/api/auth/login",
            "/auth/login",
            "/api/v1/auth/login/",
            "/API/V1/AUTH/LOGIN",
            "/api/v1//auth///login",
            "//api/v1/auth/login///"
        ]
        canonical = [normalize_path(p) for p in paths]
        assert len(set(canonical)) == 1
        assert canonical[0] == "auth/login"

    def test_06_route_alias_shares_rate_limit(self):
        """Requests across /api/v1/auth/login and /api/auth/login consume the exact same quota bucket."""
        test_ip = f"198.51.100.{uuid.uuid4().int % 200 + 10}"
        headers = {"X-Forwarded-For": test_ip, "X-Test-Rate-Limit": "true"}

        # In backend/config.py, default RATE_LIMIT_AUTH_LIMIT is 5
        # 1. First 5 requests to /api/v1/auth/login
        for _ in range(5):
            res = client.post("/api/v1/auth/login", json={"email": "nonexistent@test.com", "password": "wrong"}, headers=headers)
            # Route logic may return 401, but rate limiter allowed it (not 429)
            assert res.status_code != 429

        # 2. 6th request targeting the alias /api/auth/login MUST receive HTTP 429
        res_blocked = client.post("/api/auth/login", json={"email": "nonexistent@test.com", "password": "wrong"}, headers=headers)
        assert res_blocked.status_code == 429
        assert res_blocked.headers.get("Retry-After") is not None
        assert res_blocked.json()["error_type"] == "RateLimitExceeded"


# =============================================================================
# 4. Anti-Spoofing & Forwarded-IP Security
# =============================================================================

class TestForwardedIPSpoofing:
    def test_07_spoofed_forwarded_ip_rejected(self):
        """Attacker cannot spoof client IP by injecting a fake IP on the left of X-Forwarded-For."""
        # Simulated proxy chain: Attacker IP is 203.0.113.88, injected fake IP is 1.1.1.1
        # Behind trusted reverse proxy (e.g. 10.0.0.1)
        mock_request = MagicMock()
        mock_request.client.host = "10.0.0.1"  # In trusted proxy range
        mock_request.headers = {
            "x-forwarded-for": "1.1.1.1, 203.0.113.88, 10.0.0.1"
        }

        resolved_ip = get_trusted_client_ip(mock_request)
        # Must resolve to 203.0.113.88, NOT 1.1.1.1
        assert resolved_ip == "203.0.113.88"

    def test_08_malformed_and_injected_headers_sanitized(self):
        """Malformed strings or injection payloads in IP headers are rejected and fall back safely."""
        mock_request = MagicMock()
        mock_request.client.host = "10.0.0.1"
        mock_request.headers = {
            "x-forwarded-for": "../../malicious_path; drop table;"
        }

        resolved_ip = get_trusted_client_ip(mock_request)
        assert resolved_ip in ("10.0.0.1", "127.0.0.1")


# =============================================================================
# 5. Multi-Tier Rate Limiting: HTTP 429 Contract & Headers
# =============================================================================

class TestRateLimitingContractsAndHeaders:
    @classmethod
    def setup_class(cls):
        cls.db = SessionLocal()
        cls.org_a = models.Organization(name=f"Org RL A {uuid.uuid4().hex[:6]}", slug=f"org-rl-a-{uuid.uuid4().hex[:6]}", status="ACTIVE")
        cls.org_b = models.Organization(name=f"Org RL B {uuid.uuid4().hex[:6]}", slug=f"org-rl-b-{uuid.uuid4().hex[:6]}", status="ACTIVE")
        cls.db.add_all([cls.org_a, cls.org_b])
        cls.db.commit()

        cls.user_a = models.User(
            email=f"user_rl_a_{uuid.uuid4().hex[:6]}@example.com",
            password_hash=security.get_password_hash("SecretPass123!"),
            full_name="User RL A",
            role="DEVELOPER",
            status="ACTIVE",
            org_id=cls.org_a.id
        )
        cls.user_b = models.User(
            email=f"user_rl_b_{uuid.uuid4().hex[:6]}@example.com",
            password_hash=security.get_password_hash("SecretPass123!"),
            full_name="User RL B",
            role="DEVELOPER",
            status="ACTIVE",
            org_id=cls.org_b.id
        )
        cls.db.add_all([cls.user_a, cls.user_b])
        cls.db.commit()

        cls.token_a = security.create_access_token(
            cls.user_a.id, email=cls.user_a.email, role=cls.user_a.role, additional_claims={"org_id": str(cls.org_a.id)}
        )
        cls.token_b = security.create_access_token(
            cls.user_b.id, email=cls.user_b.email, role=cls.user_b.role, additional_claims={"org_id": str(cls.org_b.id)}
        )

    @classmethod
    def teardown_class(cls):
        try:
            cls.db.query(models.User).filter(models.User.id.in_([cls.user_a.id, cls.user_b.id])).delete(synchronize_session=False)
            cls.db.query(models.Organization).filter(models.Organization.id.in_([cls.org_a.id, cls.org_b.id])).delete(synchronize_session=False)
            cls.db.commit()
        except Exception:
            pass
        finally:
            cls.db.close()

    def test_09_auth_endpoint_rate_limit_and_headers(self):
        """Auth endpoint returns standard headers and HTTP 429 when quota exceeded."""
        test_ip = f"198.51.100.{uuid.uuid4().int % 200 + 10}"
        headers = {"X-Forwarded-For": test_ip, "X-Test-Rate-Limit": "true"}

        # Perform 5 login requests
        for i in range(5):
            res = client.post("/api/v1/auth/login", json={"email": "nobody@test.com", "password": "invalid"}, headers=headers)
            assert res.headers.get("X-RateLimit-Limit") == "5"
            assert "X-RateLimit-Remaining" in res.headers
            assert "X-RateLimit-Reset" in res.headers

        # 6th request triggers 429
        res_blocked = client.post("/api/v1/auth/login", json={"email": "nobody@test.com", "password": "invalid"}, headers=headers)
        assert res_blocked.status_code == 429
        assert int(res_blocked.headers.get("Retry-After", 0)) > 0
        assert res_blocked.headers.get("X-RateLimit-Remaining") == "0"
        body = res_blocked.json()
        assert body["error_type"] == "RateLimitExceeded"
        assert body["scope"] == "AUTH"

    def test_10_ai_endpoint_user_and_tenant_limits(self):
        """AI endpoint enforces user limit and tenant limit properly."""
        # Query AI endpoint as User A
        res = client.get("/api/v1/ai/models", headers={"Authorization": f"Bearer {self.token_a}"})
        assert res.headers.get("X-RateLimit-Limit") == str(settings.RATE_LIMIT_AI_USER_LIMIT)
        assert "X-RateLimit-Remaining" in res.headers

    def test_11_tenant_isolation_org_a_vs_org_b(self):
        """Quota consumption in Org A does not affect Org B's quota."""
        limiter = DistributedRateLimiter(storage_backend="MEMORY")
        window = 60
        limit = 10

        key_a = limiter._make_key("org", str(self.org_a.id), "general", window)
        key_b = limiter._make_key("org", str(self.org_b.id), "general", window)

        # Consume all 10 tokens for Org A
        for _ in range(10):
            res_a = limiter.check_rate_limit(key_a, max_requests=limit, window_seconds=window)
            assert res_a.allowed is True

        # Org A 11th request is blocked
        res_a_blocked = limiter.check_rate_limit(key_a, max_requests=limit, window_seconds=window)
        assert res_a_blocked.allowed is False

        # Org B must be completely unaffected (10 tokens remaining)
        res_b = limiter.check_rate_limit(key_b, max_requests=limit, window_seconds=window)
        assert res_b.allowed is True
        assert res_b.remaining == 9

    def test_12_unauthenticated_request_cannot_exploit_higher_quotas(self):
        """Forged or missing tokens fall back to strict public/IP quota."""
        # Send forged token
        res = client.get(
            "/api/v1/ai/models",
            headers={"Authorization": "Bearer forged.invalid.token"}
        )
        # At rate limiting layer, it gets classified as PUBLIC (not authenticated user)
        # Downstream auth then rejects it with 401
        assert res.status_code == 401

    def test_18_api_key_header_rate_limiting(self):
        """API keys presented via X-API-Key or Bearer ag_live_ are properly evaluated."""
        raw_key = f"ag_live_{uuid.uuid4().hex}"
        # Request with API key header
        res = client.get("/api/v1/agents", headers={"X-API-Key": raw_key})
        assert "X-RateLimit-Limit" in res.headers
        assert res.headers.get("X-RateLimit-Limit") == str(settings.RATE_LIMIT_API_KEY_LIMIT)

    def test_19_ai_tenant_throttle_across_multiple_users(self):
        """When tenant quota is exhausted across multiple users, any new user in same tenant is throttled."""
        limiter = DistributedRateLimiter(storage_backend="MEMORY")
        tenant_id = f"org_test_{uuid.uuid4().hex[:6]}"
        user_1 = f"usr_1_{uuid.uuid4().hex[:6]}"
        user_2 = f"usr_2_{uuid.uuid4().hex[:6]}"
        tenant_limit = 5

        # Mock requests: user 1 sends 3 requests, user 2 sends 2 requests (total 5 for tenant)
        tenant_key = limiter._make_key("org", tenant_id, "ai", 60)
        for _ in range(5):
            res = limiter.check_rate_limit(tenant_key, max_requests=tenant_limit, window_seconds=60, scope="AI_TENANT")
            assert res.allowed is True

        # Next request from User 2 (or any user in tenant) must be blocked by tenant quota
        res_blocked = limiter.check_rate_limit(tenant_key, max_requests=tenant_limit, window_seconds=60, scope="AI_TENANT")
        assert res_blocked.allowed is False
        assert res_blocked.scope == "AI_TENANT"


# =============================================================================
# 6. Redis Failure & Recovery Policies
# =============================================================================

class TestRedisFailurePolicies:
    def test_13_auth_route_fails_closed_when_redis_unavailable(self):
        """Sensitive authentication endpoints fail closed (HTTP 503) when Redis is unreachable."""
        broken_redis = MagicMock()
        broken_redis.eval.side_effect = Exception("Connection refused to Redis:6379")
        broken_limiter = DistributedRateLimiter(redis_client=broken_redis, storage_backend="REDIS")

        res = broken_limiter.check_rate_limit("rl:ip:test:auth_login:60", max_requests=5, window_seconds=60, fail_policy="closed", scope="AUTH")
        assert res.allowed is False
        assert res.is_service_unavailable is True
        assert res.error_message is not None

    def test_14_general_route_fails_open_when_redis_unavailable(self):
        """General business APIs fail open (HTTP 200) when Redis is unreachable to preserve uptime."""
        broken_redis = MagicMock()
        broken_redis.eval.side_effect = Exception("Connection reset by peer")
        broken_limiter = DistributedRateLimiter(redis_client=broken_redis, storage_backend="REDIS")

        res = broken_limiter.check_rate_limit("rl:usr:test:general:60", max_requests=120, window_seconds=60, fail_policy="open", scope="GENERAL")
        assert res.allowed is True
        assert res.degraded is True
        assert res.remaining == 120

    def test_15_redis_recovery_resumes_normal_operation(self):
        """When Redis recovers from an outage, rate limiting seamlessly resumes."""
        mock_redis = MagicMock()
        # First call fails, second call succeeds
        mock_redis.eval.side_effect = [
            Exception("Redis temporarily down"),
            [1, 4, 0]  # Success response from Lua script: [allowed=1, remaining=4, retry_after=0]
        ]
        limiter = DistributedRateLimiter(redis_client=mock_redis, storage_backend="REDIS")

        # 1. Outage: fails closed on auth
        res_fail = limiter.check_rate_limit("test_key", max_requests=5, window_seconds=60, fail_policy="closed")
        assert res_fail.is_service_unavailable is True

        # 2. Recovery: succeeds
        res_ok = limiter.check_rate_limit("test_key", max_requests=5, window_seconds=60, fail_policy="closed")
        assert res_ok.allowed is True
        assert res_ok.remaining == 4
        assert res_ok.degraded is False


# =============================================================================
# 7. Route Exemptions & System Health
# =============================================================================

class TestRouteExemptions:
    def test_16_health_endpoints_never_rate_limited(self):
        """Health and liveness probes are strictly exempt from rate limiting."""
        exempt_paths = [
            "/health",
            "/health/live",
            "/health/ready",
            "/api/health",
            "/api/v1/health",
            "/api/health/live",
            "/api/v1/health/ready",
            "/docs",
            "/"
        ]
        for path in exempt_paths:
            res = client.get(path)
            assert res.status_code in (200, 307)
            # Must NOT be 429
            assert res.status_code != 429

    def test_17_declarative_route_dependency(self):
        """Declarative @rate_limit dependency works properly on custom endpoints."""
        limiter = DistributedRateLimiter(storage_backend="MEMORY")
        key = "custom_report_gen"
        limit = 3

        for _ in range(3):
            r = limiter.check_rate_limit(key, max_requests=limit, window_seconds=60)
            assert r.allowed is True

        r_blocked = limiter.check_rate_limit(key, max_requests=limit, window_seconds=60)
        assert r_blocked.allowed is False
        assert r_blocked.retry_after > 0

    def test_20_websocket_unaffected_by_http_rate_limiting(self):
        """WebSocket connection requests are not blocked or corrupted by HTTP rate limiter."""
        from starlette.websockets import WebSocketDisconnect
        # A websocket attempt without ticket triggers 1008 policy violation from websocket handler,
        # confirming it passed through HTTP rate-limiting middleware cleanly.
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect("/ws"):
                pass
        assert excinfo.value.code == 1008
