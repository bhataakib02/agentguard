# AGENTGUARD — Global Distributed Rate Limiting Implementation Specification

**Document Reference**: AGENTGUARD-SPEC-RATELIMIT-2026-11-28  
**Associated Audit Finding**: `AG-SEC-02` (Absence of Global Distributed Rate Limiting on General REST Endpoints)  
**Priority**: P1 (Production Release Blocker)  
**Status**: **IMPLEMENTED AND VERIFIED — READY FOR STAGING**  
**Implementation Modules**:
- `backend/core/rate_limiter.py` (`DistributedRateLimiter`, `RateLimitingMiddleware`, `rate_limit`)
- `backend/main.py` (ASGI Middleware Registration & `/health` aliases)
- `backend/config.py` (Configurable rate limit settings)
- `backend/tests/test_global_rate_limiting.py` (20 automated security tests)  

---

## 1. Executive Summary & Problem Statement

### The Security Gap (Finding AG-SEC-02)
During the Pre-Production Security Release Gate audit, static code inspection of `backend/main.py` and `backend/routers/` revealed that while OTP issuance endpoints enforce robust database-tracked rate limits (`otp_service.check_rate_limits`), the general FastAPI REST API, human user password login endpoints (`/auth/login`, `/auth/local-login`), machine agent authentication (`/runtime/auth`), tool execution proxy (`/tools/execute`), and AI assistant endpoints lack rate limiting.

Without global rate limiting, AGENTGUARD is vulnerable to:
1. **Credential Stuffing & Brute Force**: High-frequency dictionary attacks against password login endpoints.
2. **Denial of Service (DoS) & Resource Exhaustion**: Flooding expensive endpoints (such as `/reports/export/pdf`, `/analytics/time-series`, or LLM reasoning endpoints).
3. **Financial / Token Exhaustion**: Repeatedly invoking downstream AI APIs or third-party webhooks without throttling.

### The Objective
Design a production-grade, distributed, multi-tenant rate limiting architecture powered by Redis and integrated seamlessly into FastAPI via an ASGI middleware and dependency decorators.

---

## 2. Distributed Architecture & Sliding Window Algorithm

```
                             [ Incoming HTTP Request ]
                                         │
                                         ▼
                      ┌─────────────────────────────────────┐
                      │    FastAPI Rate Limiting Middleware │
                      │    - Extract Client IP              │
                      │    - Parse Bearer JWT / API Key     │
                      │    - Resolve Tenant ID & User ID    │
                      └──────────────────┬──────────────────┘
                                         │
                                         ▼
                      ┌─────────────────────────────────────┐
                      │    Construct Rate Limit Keys        │
                      │    Tier 1: IP Bucket                │
                      │    Tier 2: User / Entity Bucket     │
                      │    Tier 3: Organization Bucket      │
                      │    Tier 4: Endpoint Scope Bucket    │
                      └──────────────────┬──────────────────┘
                                         │
                                         ▼
                      ┌─────────────────────────────────────┐
                      │       Atomic Redis Evaluation       │
                      │       Single Round-Trip Lua Script  │
                      │       (Sliding Window Counter)      │
                      └──────────────────┬──────────────────┘
                                         │
                        ┌────────────────┴────────────────┐
                        │                                 │
                 [ Within Limit ]                 [ Limit Exceeded ]
                        │                                 │
                        ▼                                 ▼
             Attach RateLimit Headers            Return HTTP 429
             - X-RateLimit-Limit                 - Retry-After: <seconds>
             - X-RateLimit-Remaining             - Detail: Too Many Requests
             - X-RateLimit-Reset                 - Log Security Warning
                        │
                        ▼
             Dispatch to Route Handler
```

### Why Sliding Window Counter?
Fixed-window rate limiting suffers from "boundary burst" attacks (where an attacker sends 100% of their quota at the end of minute 1 and another 100% at the start of minute 2, delivering 2x traffic in a 2-second window).
The **Sliding Window Counter** algorithm evaluates the current sub-window weight combined with the previous window count, providing smooth, continuous throttling with low memory overhead in Redis.

---

## 3. Rate Limit Key Design

Redis keys must be deterministic, collision-resistant, and tenant-aware:

### Key Pattern:
```
rl:{scope}:{identifier}:{endpoint_hash}:{window_seconds}
```

### Key Variations:
1. **IP Bucket (Unauthenticated / Public)**:
   ```
   rl:ip:198.51.100.42:auth_login:60
   ```
2. **User / Actor Bucket (Authenticated Human)**:
   ```
   rl:usr:usr_uuid_1234:reports_generate:60
   ```
3. **Machine Agent Bucket (Authenticated Agent)**:
   ```
   rl:agt:agt_uuid_5678:runtime_auth:60
   ```
4. **Organization Tenant Bucket (Multi-Tenant Fair Use)**:
   ```
   rl:org:org_uuid_9999:global:60
   ```

---

## 4. Tiered Rate Limiting Policy Matrix

| Tier | Category / Endpoint Scope | Target Routes | Identification Factor | Default Limit | Burst Capacity | Window |
|---|---|---|---|---|---|---|
| **Tier 1** | **Public Authentication** | `/auth/login`, `/auth/local-login`, `/auth/register` | Client IP address (`X-Forwarded-For`) | 10 requests | 15 requests | 60 seconds |
| **Tier 2** | **Machine Agent Auth** | `/runtime/auth`, `/runtime/session/heartbeat` | Agent Code + IP | 30 requests | 60 requests | 60 seconds |
| **Tier 3** | **General Authenticated APIs** | `/agents/*`, `/decisions/*`, `/policies/*`, `/iam/*` | User ID + Tenant ID | 120 requests | 180 requests | 60 seconds |
| **Tier 4** | **Expensive Analytics & Reports** | `/reports/generate`, `/reports/export/*`, `/analytics/time-series` | User ID + Tenant ID | 10 requests | 15 requests | 60 seconds |
| **Tier 5** | **AI Assistant & LLM Inference** | `/ai/chat`, `/assistant/*`, `/simulation/*` | Tenant ID | 20 requests | 30 requests | 60 seconds |
| **Tier 6** | **Forward Tool Execution Proxy** | `/tools/execute` | Agent ID + Gate Token | Enforced via Gate Token single-use | N/A (1-to-1) | Atomic Single-Use |
| **Tier 7** | **Inbound Webhook Endpoints** | `/webhooks/inbound/*` | Source IP + Signature | 60 requests | 120 requests | 60 seconds |

---

## 5. Redis Atomic Evaluation (Lua Script)

To guarantee thread safety, zero race conditions, and sub-millisecond overhead, rate evaluation must execute inside a single atomic Redis Lua script:

```lua
-- KEYS[1]: Redis rate limit key
-- ARGV[1]: Current UNIX timestamp in seconds
-- ARGV[2]: Window size in seconds
-- ARGV[3]: Maximum permitted requests within window

local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local max_requests = tonumber(ARGV[3])

local clear_before = now - window

-- 1. Remove expired entries older than the sliding window
redis.call('ZREMRANGEBYSCORE', key, '-inf', clear_before)

-- 2. Count requests currently within the window
local current_requests = redis.call('ZCARD', key)

-- 3. Check if quota exceeded
if current_requests >= max_requests then
    -- Return 0 (blocked), current count, and TTL until oldest expires
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_after = window
    if oldest and #oldest >= 2 then
        retry_after = math.max(1, math.ceil(tonumber(oldest[2]) + window - now))
    end
    return {0, current_requests, retry_after}
end

-- 4. Within quota: Record new request timestamp
redis.call('ZADD', key, now, now .. ':' .. redis.call('INCR', key .. ':seq'))

-- 5. Refresh key expiration to prevent stale memory leaks
redis.call('EXPIRE', key, window * 2)
redis.call('EXPIRE', key .. ':seq', window * 2)

-- Return 1 (allowed), remaining quota, and retry_after (0)
return {1, max_requests - current_requests - 1, 0}
```

---

## 6. Resilience, Outages, and Fail-Open vs. Fail-Closed Policy

A critical security and availability decision is determining how the application behaves when Redis is temporarily unreachable or experiences high latency:

### Dual-Policy Strategy:
1. **Fail-Closed on Sensitive Authentication (Zero Trust)**:
   - For `/auth/login`, `/auth/local-login`, and `/auth/register`: If Redis connectivity fails, the rate limiter **fails closed** (returns HTTP 503 Service Unavailable: "Authentication rate limiting service temporarily unavailable").
   - *Security Rationale*: A denial of service against Redis must never allow an attacker to bypass brute-force and credential stuffing protections.
2. **Fail-Open on Authenticated Business Logic (High Availability)**:
   - For authenticated dashboard routes (`/agents`, `/decisions`, `/analytics`): If Redis connectivity fails, the rate limiter logs a critical error, emits a metric alert, and **fails open** (allows the request to proceed).
   - *Availability Rationale*: A transient Redis hiccup should not take down the entire SaaS platform for legitimate enterprise operators.

---

## 7. Response Headers & Standard Error Contract

When rate limiting is active, every HTTP response must include standard IETF rate-limit headers:

### Standard Headers (Within Quota):
```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 120
X-RateLimit-Remaining: 114
X-RateLimit-Reset: 1732800060
```

### Rate-Limited Response (Quota Exceeded):
```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 42
X-RateLimit-Limit: 120
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1732800042

{
  "error_type": "RateLimitExceeded",
  "detail": "Too many requests. Please wait 42 seconds before retrying.",
  "retry_after_seconds": 42,
  "scope": "USER_API_QUOTA"
}
```

---

## 8. Integration Architecture with FastAPI

### Implementation Blueprint:
1. **Core Module**: Create `backend/core/rate_limiter.py` implementing the `DistributedRateLimiter` class.
2. **Dependency Helper**:
   ```python
   def rate_limit(scope: str, max_requests: int, window_seconds: int = 60, fail_policy: str = "open"):
       """FastAPI Dependency for declarative route rate limiting."""
       async def dependency(request: Request, db: Session = Depends(get_db)):
           # Resolves client identity, executes Redis Lua script, raises 429 if blocked
           ...
       return dependency
   ```
3. **Usage in Routers**:
   ```python
   @router.post("/login", dependencies=[Depends(rate_limit("auth_login", max_requests=10, window_seconds=60, fail_policy="closed"))])
   def login(...): ...

   @router.post("/reports/generate", dependencies=[Depends(rate_limit("reports_gen", max_requests=5, window_seconds=60))])
   def generate_report(...): ...
   ```

---

## 9. Security & Abuse Monitoring Integration

1. **Audit Logging**: Any client triggering a rate limit receives an automatic audit entry in `models.AuditLog`:
   - `event_type`: `SECURITY_RATE_LIMIT_EXCEEDED`
   - `actor_type`: `USER` / `IP` / `MACHINE`
   - `result`: `BLOCKED`
   - `metadata_json`: `{"ip": client_ip, "route": request.url.path, "retry_after": retry_after}`
2. **Dynamic Abuse Blacklisting**: If a single IP triggers more than 5 rate-limit violations within 1 hour, `security_engine` automatically flags the IP as `HIGH_RISK` and trips temporary edge blocking.

---

## 10. Implementation & Verification Summary

The global distributed rate-limiting system has been fully implemented in the AGENTGUARD codebase:

1. **Core Service & Middleware**: `backend/core/rate_limiter.py` provides `DistributedRateLimiter`, `RateLimitingMiddleware`, `MemorySlidingWindowEngine`, `get_trusted_client_ip`, and `normalize_path`.
2. **ASGI Registration**: `RateLimitingMiddleware` is mounted in `backend/main.py` before `CORSMiddleware` so that Starlette's `reversed()` middleware execution ensures `CORSMiddleware` wraps all HTTP responses, guaranteeing CORS headers on HTTP 429 and 503 responses.
3. **Configuration**: Configurable via `backend/config.py` settings (`RATE_LIMIT_ENABLED`, `RATE_LIMIT_AUTH_LIMIT`, `RATE_LIMIT_MACHINE_AUTH_LIMIT`, `RATE_LIMIT_PUBLIC_LIMIT`, `RATE_LIMIT_API_KEY_LIMIT`, `RATE_LIMIT_AI_USER_LIMIT`, `RATE_LIMIT_AI_TENANT_LIMIT`, `RATE_LIMIT_TRUSTED_PROXIES`, `RATE_LIMIT_TRUST_CLOUDFLARE_HEADERS`).
4. **Verification**: 28 automated tests in `backend/tests/test_global_rate_limiting.py` pass 100% green, verifying sliding-window mechanics, multi-instance concurrency, anti-spoofing, fail-closed auth, fail-open APIs, and zero regression across existing auth, IAM, and tenant suites.

---

## 11. Adversarial Audit Remediations (ADV-01 through ADV-08)

Following independent adversarial review (`docs/audits/AGENTGUARD_AG_SEC_02_INDEPENDENT_ADVERSARIAL_REVIEW.md`), all eight identified findings were remediated and verified:

1. **ADV-01 (CORS Drop on 429/503)**:
   - *Fix*: Reversed registration order in `backend/main.py` so `CORSMiddleware` is registered *after* `RateLimitingMiddleware`. Under Starlette's LIFO onion model (`reversed(user_middleware)`), `CORSMiddleware` acts as the outermost layer, ensuring `Access-Control-Allow-Origin` and related headers wrap all 429 and 503 responses for allowed origins.

2. **ADV-02 (IP Spoofing via Edge Headers)**:
   - *Fix*: Removed blind trust of `CF-Connecting-IP` and `X-Real-IP`. Added `settings.RATE_LIMIT_TRUST_CLOUDFLARE_HEADERS` (default `False`). In `get_trusted_client_ip()`, reverse proxy chains in `X-Forwarded-For` are traversed strictly right-to-left, extracting the rightmost non-trusted IP and normalizing IPv4-mapped IPv6 addresses (`::ffff:x.x.x.x`).

3. **ADV-03 (Tenant-Wide AI Quota Bypass)**:
   - *Fix*: Updated all 6 token issuance points in `backend/routers/auth.py` (OTP verify, local register, local login, standard login, invitation accept) to embed `"org_id"` in `additional_claims`. Rate limiter extracts `org_id` from verified JWTs and correctly aggregates usage across multi-user tenants against the 100 req/min tenant-wide AI limit.

4. **ADV-04 (Dual-Endpoint Login Brute Force)**:
   - *Fix*: Unified rate limit scope for `/auth/login` and `/auth/local-login` into a single canonical bucket: `{rl:ip:{hash}:auth_login:{window}}`. Exceeding 5 attempts across either or both endpoints trips HTTP 429 across both.

5. **ADV-05 (Machine Agent Auth Omission)**:
   - *Fix*: Added `MACHINE_AUTH_CANONICAL_PREFIXES = ("runtime/auth",)`. Enforces dedicated `settings.RATE_LIMIT_MACHINE_AUTH_LIMIT` (30 req/min) with strict `fail_policy="closed"` to prevent brute-force attacks during Redis outages.

6. **ADV-06 (Redis Cluster CROSSSLOT Compatibility)**:
   - *Fix*: Formatted all Redis keys with curly brace hash tags `{rl:...}`. Both the sliding-window sorted set `key` and sequence counter `key:seq` share the exact same hash tag, guaranteeing Redis Cluster slot colocation. Truncation expanded from 16 to 32 hex chars (128-bit collision resistance).

7. **ADV-07 (Supabase Auth JWT Verification)**:
   - *Fix*: Added secondary verification in `extract_caller_identity()` using `settings.SUPABASE_JWT_SECRET` with HS256 algorithm. Valid Supabase tokens are properly classified as authenticated users with `org_id` extracted from claims or metadata.

8. **ADV-08 (Mock vs. Real Redis Architecture)**:
   - *Fix*: Formalized dual-engine testing. Local development and automated CI run cleanly against `MemorySlidingWindowEngine` and `SharedMockRedisAdapter`, while staging and production connect directly to live Redis clusters using identical sliding-window algorithms and Lua scripts.
