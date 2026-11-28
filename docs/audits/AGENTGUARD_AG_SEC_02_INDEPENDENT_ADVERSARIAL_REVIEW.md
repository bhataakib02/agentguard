# AGENTGUARD — Independent Adversarial Security Audit of AG-SEC-02

**Document Reference**: `AG-AUDIT-RATELIMIT-ADV-2026-11-28`  
**Classification**: `Restricted / Independent Security Review`  
**Target Subsystem**: `AG-SEC-02 Global Distributed Rate Limiting Subsystem`  
**Auditor**: `Independent Application Security Reviewer`  
**Target Codebase Baseline**: Commit `5e8523e1acf5d96c31b570330f5cbca1f942bf92` + AG-SEC-02 implementation  
**Reviewed Artifacts**:
- `backend/core/rate_limiter.py`
- `backend/config.py`
- `backend/main.py`
- `backend/tests/test_global_rate_limiting.py`
- `docs/security/AGENTGUARD_GLOBAL_RATE_LIMITING_IMPLEMENTATION_SPEC.md`
- `docs/audits/AGENTGUARD_AG_SEC_02_RATE_LIMITING_IMPLEMENTATION_REPORT.md`
- Related modules: `backend/routers/auth.py`, `backend/core/security.py`, `backend/core/deps.py`, `backend/routers/runtime.py`

**Final Audit Verdict**: **APPROVED FOR STAGING WITH CONDITIONS**  
*(Production Release: Strictly HELD pending remediation of Findings ADV-01, ADV-02, and ADV-03)*

---

## 1. Executive Summary

An independent adversarial security review was performed on the newly implemented global distributed rate-limiting subsystem (`AG-SEC-02`). The objective was to test the implementation for architectural weaknesses, bypasses, spoofing vulnerabilities, error-handling flaws, identity and tenant isolation breaks, and test integrity gaps.

### Summary of Audit Outcome
- **Core Algorithm**: The atomic Redis Lua script and sliding-window logic are mathematically sound. The sliding-window counter effectively eliminates fixed-window boundary burst vulnerabilities. Key expiration (`math.ceil(window * 2)`) prevents memory leaks.
- **Fail-Closed Policy**: The implementation correctly fails closed (returning HTTP 503) for sensitive authentication routes during Redis outages.
- **Fail-Open Policy**: General business APIs correctly fail open with HTTP 200, attaching operational telemetry headers without crashing downstream handlers.
- **Adversarial Discoveries**: The audit uncovered **2 High-severity findings**, **3 Medium-severity findings**, and **3 Low/Informational findings** that require remediation before production release. Most critically, an inverted middleware registration order causes CORS headers to be dropped on all rate-limited (429) and fail-closed (503) responses, causing browser clients to fail with CORS errors rather than displaying rate-limit messages.

---

## 2. Findings Matrix

| Finding ID | Severity | Category | Target Location | Summary | Blocks Staging? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ADV-01** | **HIGH** | CORS / Middleware | `backend/main.py:83-88` | CORS headers dropped on 429 and 503 responses due to inverted middleware registration order. | **Condition** |
| **ADV-02** | **HIGH** | IP Spoofing | `backend/core/rate_limiter.py:206-224` | Unconditional trust in `CF-Connecting-IP` and `X-Real-IP` behind private proxies enables rate-limit reset. | **Condition** |
| **ADV-03** | **MEDIUM** | Tenant Isolation | `backend/core/rate_limiter.py:599` & `backend/routers/auth.py` | AI tenant quota (100 req/min) bypassed across multi-user tenants due to missing `org_id` in issued JWTs. | **Condition** |
| **ADV-04** | **MEDIUM** | Brute Force | `backend/core/rate_limiter.py:545` | Separate rate-limit keys for `/auth/login` and `/auth/local-login` allows 2x credential stuffing throughput. | **Condition** |
| **ADV-05** | **MEDIUM** | Classification | `backend/core/rate_limiter.py:90-101` | Machine Agent Auth (`/runtime/auth`) omitted from `AUTH` tier; defaults to public 60 req/min fail-open. | **Condition** |
| **ADV-06** | **LOW** | Redis Cluster | `backend/core/rate_limiter.py:33-72` | Multi-key Lua script lacks Redis Cluster hash tags `{...}`, risking `CROSSSLOT` error on sharded Redis. | No |
| **ADV-07** | **LOW** | Auth Integration | `backend/core/rate_limiter.py:501-512` | Supabase Auth JWTs unverified by rate limiter; valid enterprise users fall back to anonymous IP quotas. | No |
| **ADV-08** | **INFO** | Test Integrity | `backend/tests/test_global_rate_limiting.py:46` | Multi-instance tests use in-memory Python mock adapters rather than live Redis cluster verification. | No |

---

## 3. Detailed Adversarial Findings

### FINDING ADV-01: CORS Headers Dropped on 429 and 503 Responses Due to Inverted Middleware Registration Order

- **Severity**: **HIGH**
- **Location**: `backend/main.py:83-88`
- **Description**: In FastAPI / Starlette, the middleware onion stack wraps applications in reverse order of `app.add_middleware()` calls:
  ```python
  app.add_middleware(CORSMiddleware, ...)      # Added first -> executed innermost
  app.add_middleware(RateLimitingMiddleware)  # Added second -> executed outermost
  ```
  Because `RateLimitingMiddleware` is outermost, when it intercepts a request and returns a `JSONResponse(status_code=429)` or `JSONResponse(status_code=503)`, the execution short-circuits and returns to the client **without ever passing through `CORSMiddleware`**.
- **Security / Operational Impact**: Cross-origin frontend single-page apps (such as the Next.js production frontend at `https://agentguard-beta-ten.vercel.app` calling the Render API) receive 429 and 503 responses completely lacking `Access-Control-Allow-Origin`. Web browsers immediately drop the response with a `Cross-Origin Request Blocked (CORS Missing Allow Origin)` error. The user is shown a broken connection error, and the client JavaScript application is unable to parse the JSON error body or read the `Retry-After` header.
- **Proof-of-Concept Evidence**:
  Live execution verified in isolated test harness:
  ```
  App1 (CORSMiddleware added first, then RateLimitingMiddleware):
    Status: 503
    Access-Control-Allow-Origin: None   <-- CORS Header DROPPED

  App2 (RateLimitingMiddleware added first, then CORSMiddleware):
    Status: 503
    Access-Control-Allow-Origin: *      <-- CORS Header PRESERVED
  ```
- **Remediation**:
  In `backend/main.py`, mount `RateLimitingMiddleware` *before* `CORSMiddleware` so that `CORSMiddleware` is outermost and appends CORS headers to all responses:
  ```python
  # 1. Mount RateLimitingMiddleware
  from core.rate_limiter import RateLimitingMiddleware
  app.add_middleware(RateLimitingMiddleware)

  # 2. Mount CORSMiddleware (outermost wrapper)
  app.add_middleware(
      CORSMiddleware,
      allow_origins=settings.CORS_ORIGINS,
      ...
  )
  ```

---

### FINDING ADV-02: Client IP Spoofing via Unverified `CF-Connecting-IP` and `X-Real-IP` behind Cloudflare-less Proxies

- **Severity**: **HIGH**
- **Location**: `backend/core/rate_limiter.py:206-224`
- **Description**: In `get_trusted_client_ip()`:
  ```python
  cf_ip = request.headers.get("cf-connecting-ip")
  if cf_ip and is_direct_trusted:
      return clean_cf
  real_ip = request.headers.get("x-real-ip")
  if real_ip and is_direct_trusted:
      return clean_real
  ```
  `is_direct_trusted` evaluates whether `request.client.host` is within `DEFAULT_TRUSTED_PROXIES` (`127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
- **Security Impact**: On cloud platforms like Render, requests arrive at the container from private load balancers within `10.0.0.0/8`, making `is_direct_trusted = True`. If the application domain is NOT routed through Cloudflare (or if Render does not actively strip inbound client headers), an attacker can supply an arbitrary `CF-Connecting-IP: <random_ip>` header. The rate limiter trusts this header over `X-Forwarded-For`. By rotating this header on every request, an attacker can completely reset their rate limit bucket on `/auth/login`, `/auth/register`, and `/auth/send-otp`, performing unlimited brute-force attacks from a single machine.
- **Remediation**:
  1. Do not trust `CF-Connecting-IP` unless `request.client.host` is verified against official Cloudflare IP ranges (`173.245.48.0/20`, `103.21.244.0/22`, etc.), OR make Cloudflare header trust an explicit configuration toggle (`TRUST_CLOUDFLARE_HEADERS=False` by default).
  2. Rely exclusively on right-to-left traversal of `X-Forwarded-For` where the cloud load balancer (Render) appends the true connection IP to the end of the chain.

---

### FINDING ADV-03: AI Tenant Quota (100 req/min) Bypassed Across Multi-User Tenants Due to Missing `org_id` in JWTs

- **Severity**: **MEDIUM**
- **Location**: `backend/core/rate_limiter.py:507-510, 599` & `backend/routers/auth.py:390, 562, 931, 1056, 1124, 1342`
- **Description**: In `backend/core/rate_limiter.py`:
  ```python
  user_id = payload.get("sub")
  org_id = payload.get("org_id") or payload.get("tenant_id")
  ...
  effective_org = org_id or actor_id
  tenant_key = self._make_key("org", effective_org, "ai", window)
  ```
  However, in `backend/routers/auth.py`, every single call to `security.create_access_token()` supplies only:
  `security.create_access_token(str(user.id), email=str(user.email), role=str(user.role))`
  without passing `additional_claims={"org_id": str(user.org_id)}`.
- **Security Impact**: In production, every JWT issued to human users contains only `sub`, `email`, and `role`. `org_id` is **always `None`**. When evaluating AI assistant requests, `effective_org` falls back to `actor_id` (the user ID). Consequently, every user in an organization receives their own separate "tenant" bucket. In an organization with 50 users, instead of all 50 users collectively sharing the 100 req/min tenant fair-use quota, the organization can send up to $50 \times 20 = 1,000$ requests/minute, completely bypassing the tenant-wide fair-use quota.
- **Proof-of-Concept Evidence**:
  ```python
  token = security.create_access_token('usr_123', email='test@example.com', role='USER')
  auth_type, actor_id, org_id, _ = rate_limiter.extract_caller_identity(MockReq(token))
  # Output: Auth type: JWT, Actor id: usr_123, Org id: None
  ```
  The test suite `test_global_rate_limiting.py` passed only because it artificially injected `additional_claims={"org_id": ...}` during test setup, which does not reflect production token issuance.
- **Remediation**:
  In `backend/routers/auth.py`, update all 6 `create_access_token` calls to pass `additional_claims={"org_id": str(user.org_id)}` whenever `user.org_id` is present.

---

### FINDING ADV-04: Separate Rate-Limit Keys for `/auth/login` and `/auth/local-login` Allow 2x Brute-Force Throughput

- **Severity**: **MEDIUM**
- **Location**: `backend/core/rate_limiter.py:545`
- **Description**: Key construction for sensitive auth routes uses:
  `key = self._make_key("ip", client_ip, f"auth_{path.replace('/', '_')}", window)`
  Because `path` is included directly in the scope, `/api/v1/auth/login` produces key `rl:ip:{hash}:auth_auth_login:60`, while `/api/v1/auth/local-login` produces key `rl:ip:{hash}:auth_auth_local-login:60`.
- **Security Impact**: The specification (`AGENTGUARD_GLOBAL_RATE_LIMITING_IMPLEMENTATION_SPEC.md` Section 3) intended password authentication to share a single unified `auth_login` quota. Under the current implementation, an attacker can interleave 5 requests to `/auth/login` and 5 requests to `/auth/local-login` within the same 60 seconds from the same IP, achieving 10 attempts/minute (2x intended quota) without triggering HTTP 429.
- **Remediation**:
  Normalize all password authentication endpoints into a single unified scope:
  ```python
  auth_scope = "auth_login" if path in ("auth/login", "auth/local-login") else f"auth_{path.replace('/', '_')}"
  key = self._make_key("ip", client_ip, auth_scope, window)
  ```

---

### FINDING ADV-05: Machine Agent Auth (`/runtime/auth`) Omitted from Sensitive `AUTH` Tier

- **Severity**: **MEDIUM**
- **Location**: `backend/core/rate_limiter.py:90-101, 536`
- **Description**: `AUTH_CANONICAL_PREFIXES` only matches routes beginning with `auth/*`. The machine agent authentication endpoint (`POST /api/v1/runtime/auth`), which verifies `agent_code` and `api_secret`, does not start with `auth/`.
- **Security Impact**: Machine agent credential verification falls into the generic `PUBLIC` tier (60 req/min, fail-open) instead of the `AUTH` tier (5 req/min, fail-closed). In the event of a Redis outage, brute-force dictionary attacks against machine agent credentials fail open, violating zero-trust principles.
- **Remediation**:
  Add `"runtime/auth"` to `AUTH_CANONICAL_PREFIXES` with a dedicated 30 req/min threshold and fail-closed policy.

---

### FINDING ADV-06: Multi-Key Lua Script Lacks Redis Cluster Hash Tags `{...}`

- **Severity**: **LOW / INFORMATIONAL**
- **Location**: `backend/core/rate_limiter.py:33-72`
- **Description**: The sliding-window Lua script accesses two distinct Redis keys in a single script: `KEYS[1]` (the sorted set) and `KEYS[1] .. ':seq'` (the sequence counter). In Redis Cluster mode, keys are distributed across 16,384 hash slots based on `CRC16(key)`. Without curly braces `{...}` (hash tags), `key` and `key:seq` hash to different slots, causing Redis Cluster to fail with:
  `CROSSSLOT Keys in request don't hash to the same slot`
- **Security / Operational Impact**: Zero impact on standalone Redis (Render single-node Redis). However, if AGENTGUARD is migrated to AWS ElastiCache Cluster or GCP Memorystore Redis Cluster in enterprise deployments, rate limiting will crash with `CROSSSLOT` errors.
- **Remediation**:
  Wrap the base key in curly braces:
  `key = f"{{rl:{dimension}:{safe_hash}:{scope}:{window}}}"`
  This guarantees that `key` and `key .. ':seq'` hash to the identical cluster slot.

---

### FINDING ADV-07: Unauthenticated Supabase JWT Users Default to IP Quotas

- **Severity**: **LOW / INFORMATIONAL**
- **Location**: `backend/core/rate_limiter.py:501-512`
- **Description**: `extract_caller_identity()` only attempts to decode tokens using `settings.SECRET_KEY` (HS256). It does not verify Supabase JWTs using `settings.SUPABASE_JWT_SECRET`.
- **Security / Operational Impact**: Legitimate enterprise users authenticating with Supabase Auth JWTs fail local JWT decoding and are classified as `ANONYMOUS`. They are throttled under the public IP quota (60 req/min) rather than the authenticated user quota (120 req/min), potentially causing false-positive throttling for multiple users sharing an office egress IP.
- **Remediation**:
  In `extract_caller_identity`, add a fallback decode using `settings.SUPABASE_JWT_SECRET` when configured.

---

### FINDING ADV-08: Test Suite Uses Simulated In-Memory Mocks Rather than Real Redis

- **Severity**: **INFORMATIONAL**
- **Location**: `backend/tests/test_global_rate_limiting.py:46-59`
- **Description**: Tests `test_03_multi_instance_shared_quota` and `test_04_atomic_concurrency_under_parallel_threads` use `SharedMockRedisAdapter`, an in-memory Python class that delegates to `MemorySlidingWindowEngine`.
- **Operational Impact**: While these tests verify the sliding-window arithmetic and mutex synchronization in Python, they do NOT execute the actual Redis Lua script on a real Redis server or test actual network socket timeouts, connection pool exhaustion, or Redis cluster replication lag. Real Redis integration testing remains a required milestone for live staging deployment.
- **Remediation**:
  Execute live integration tests against `agentguard-staging-redis` during Phase 8 of the Staging Deployment runbook.

---

## 4. Test Evidence & Validation of Controls

### Verified Functioning Controls
1. **Sliding Window Roll-Over**: Verified that `MemorySlidingWindowEngine` correctly rolls over timestamps and computes exact `retry_after` values.
2. **Boundary Burst Resistance**: Verified that an attacker submitting 100% quota at $t=59$ and attempting an immediate burst at $t=61$ is blocked with positive `Retry-After`.
3. **Fail-Closed on Auth Routes**: Verified live with `TestClient` that when Redis is unreachable, `/api/v1/auth/login` returns **HTTP 503 Service Unavailable** with detail `"Authentication rate limiting service temporarily unavailable"`.
4. **Fail-Open on General Routes**: Verified that general APIs return HTTP 200 with `X-RateLimit-Degraded: fail_open` when Redis is down.
5. **Path Normalization**: Verified that `/api/v1/auth/login`, `/api/auth/login`, `/auth/login/`, and `/API/V1/AUTH/LOGIN` are normalized into unified canonical scopes.
6. **Route Exemptions**: Verified that `/health`, `/health/live`, `/health/ready`, `/docs`, `/`, and WebSocket `/ws` connections are not blocked.
7. **Zero Regression**: Verified that all 24 authentication/OTP tests, 10 WebSocket auth tests, and 26 IAM/tenant penetration tests pass 100% green.

---

## 5. Staging Readiness Verdict & Release Conditions

### Verdict: **APPROVED FOR STAGING WITH CONDITIONS**

The global rate-limiting subsystem provides substantial defense-in-depth protection and is safe for provisioning in the isolated staging environment. However, **production release is strictly HELD** pending resolution of the following conditions:

### Required Remediation Conditions Before Production Promotion:
1. **[Condition 1 — Fix Middleware Ordering]**: In `backend/main.py`, mount `RateLimitingMiddleware` before `CORSMiddleware` so `CORSMiddleware` wraps the rate limiter and attaches CORS headers to 429 and 503 responses.
2. **[Condition 2 — IP Spoofing Hardening]**: In `backend/core/rate_limiter.py`, disable unverified trust in `CF-Connecting-IP` / `X-Real-IP` unless verified against Cloudflare IP ranges.
3. **[Condition 3 — JWT Tenant ID Injection]**: In `backend/routers/auth.py`, update `create_access_token` calls to include `additional_claims={"org_id": str(user.org_id)}` so AI tenant fair-use quotas function across users.
4. **[Condition 4 — Unify Password Login Scopes]**: Unify `/auth/login` and `/auth/local-login` into a single `auth_login` rate-limit bucket.
5. **[Condition 5 — Machine Auth Protection]**: Add `"runtime/auth"` to `AUTH_CANONICAL_PREFIXES` with fail-closed protection.
6. **[Condition 6 — Real Redis Staging Verification]**: Run tests against live `agentguard-staging-redis` on Render to verify real Redis network latency, connection pooling, and Lua execution.
