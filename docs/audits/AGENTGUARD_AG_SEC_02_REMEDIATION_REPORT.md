# AGENTGUARD — AG-SEC-02 Adversarial Audit Remediation Report

**Document Reference**: `AGENTGUARD-AUDIT-REMEDIATION-AG-SEC-02-2026-11-28`  
**Classification**: `Restricted / Pre-Production Security Engineering`  
**Target Release**: `AGENTGUARD Isolated Staging Environment`  
**Audited Target**: `docs/audits/AGENTGUARD_AG_SEC_02_INDEPENDENT_ADVERSARIAL_REVIEW.md` (Findings ADV-01 through ADV-08)  
**Remediation Status**: **100% REMEDIATED & VERIFIED**  
**Final Release Gate Verdict**: **READY FOR ISOLATED STAGING DEPLOYMENT**  

---

## 1. Executive Summary

Following the completion of AG-SEC-02 (Global Distributed Rate Limiting), an independent adversarial security review was performed, uncovering eight specific architectural weaknesses and edge cases (Findings **ADV-01** through **ADV-08**).

This remediation engagement successfully resolved all eight findings in the AGENTGUARD codebase. Comprehensive automated test coverage has been added (`backend/tests/test_global_rate_limiting.py` expanded from 20 to 28 tests), and extensive regression testing confirmed zero regressions across authentication, OTP, WebSockets, IAM, multi-tenant isolation, runtime security invariants, tool proxying, and SSRF mitigations (194 passing automated tests).

Frontend linting verified clean (`✔ No ESLint warnings or errors`).

---

## 2. Findings & Remediations Matrix

| Finding ID | Title | Severity | Status | Remediation Summary |
|:---|:---|:---|:---|:---|
| **ADV-01** | CORS Header Stripping on 429/503 Errors | **Medium** | **REMEDIATED** | Inverted middleware registration order in `backend/main.py`. Starlette's LIFO execution mounts `CORSMiddleware` outermost, guaranteeing CORS headers on rate-limited responses for allowed origins. |
| **ADV-02** | IP Spoofing via Unverified `CF-Connecting-IP` / `X-Real-IP` | **High** | **REMEDIATED** | Removed blind trust of edge headers in `backend/core/rate_limiter.py`. Added `RATE_LIMIT_TRUST_CLOUDFLARE_HEADERS`. Strict right-to-left traversal of `X-Forwarded-For` with IPv4-mapped IPv6 normalization. |
| **ADV-03** | Tenant-Wide AI Quota Bypass Across Multi-User Tenants | **High** | **REMEDIATED** | Updated all 6 token issuance points in `backend/routers/auth.py` to embed `org_id` in JWTs. Rate limiter extracts `org_id` and aggregates tenant usage against the 100 req/min quota. |
| **ADV-04** | Disjoint Rate-Limit Buckets for Login Endpoints | **Medium** | **REMEDIATED** | Unified `/auth/login` and `/auth/local-login` into single canonical scope `auth_login`. Both endpoints share the identical 5 attempts/minute bucket. |
| **ADV-05** | Machine Agent Auth (`/runtime/auth`) Omission from Sensitive Tier | **High** | **REMEDIATED** | Added `MACHINE_AUTH_CANONICAL_PREFIXES` in `backend/core/rate_limiter.py`. Enforces `RATE_LIMIT_MACHINE_AUTH_LIMIT` (30 req/min) and strict `fail_policy="closed"` on Redis outage. |
| **ADV-06** | Redis Cluster Incompatibility (`CROSSSLOT` on `INCR key .. ':seq'`) | **Medium** | **REMEDIATED** | Implemented Redis Cluster hash tag syntax `{rl:...}`. Both base key and `:seq` key share the hash tag, ensuring identical cluster slot colocation. Hash entropy increased to 128-bit (32 hex chars). |
| **ADV-07** | Supabase Auth JWTs Unverified by Rate Limiter | **Medium** | **REMEDIATED** | Added secondary cryptographic verification in `extract_caller_identity()` using `settings.SUPABASE_JWT_SECRET` with HS256, extracting `sub` and `org_id` from claims/metadata. |
| **ADV-08** | Incomplete Mock vs. Real Redis Architecture Documentation | **Low** | **REMEDIATED** | Formalized dual-engine testing in specs and environment variable docs. Fully documented in-memory sliding-window vs. real Redis cluster operational boundaries. |

---

## 3. Detailed Remediation Evidence

### ADV-01: CORS Header Preservation on Rate-Limited Responses
- **Root Cause**: In `backend/main.py`, `CORSMiddleware` was added before `RateLimitingMiddleware`. Under Starlette's `reversed(self.user_middleware)` execution order, `RateLimitingMiddleware` wrapped `CORSMiddleware`, returning HTTP 429 and 503 before `CORSMiddleware` could process the response.
- **Fix Applied**: In `backend/main.py`, `RateLimitingMiddleware` is mounted first, and `CORSMiddleware` is mounted second. Starlette executes `CORSMiddleware` outermost.
- **Verification Evidence**: Automated test `test_21_cors_headers_preserved_on_rate_limit_429` passes. Verified that allowed origin `http://localhost:3000` receives `Access-Control-Allow-Origin: http://localhost:3000` on HTTP 429, while disallowed origin `http://evil-attacker.com` is stripped.

### ADV-02: IP Anti-Spoofing & Edge Header Verification
- **Root Cause**: `get_trusted_client_ip()` trusted `CF-Connecting-IP` and `X-Real-IP` if `request.client.host` was in `10.0.0.0/8`. Render routes internal traffic through `10.x.x.x`, allowing attackers to forge arbitrary client IPs.
- **Fix Applied**:
  - `RATE_LIMIT_TRUST_CLOUDFLARE_HEADERS` added to `backend/config.py` (default: `False`).
  - `CF-Connecting-IP` is only accepted if explicitly enabled.
  - Removed blind evaluation of `X-Real-IP`.
  - `X-Forwarded-For` is parsed strictly right-to-left, extracting the rightmost untrusted IP.
  - Added IPv4-mapped IPv6 normalization (`::ffff:x.x.x.x` -> `x.x.x.x`).
- **Verification Evidence**: Automated tests `test_22_ip_spoofing_cf_connecting_ip_and_x_real_ip_rejected` and `test_23_ipv4_mapped_ipv6_normalized` pass.

### ADV-03: Tenant-Wide AI Quota Enforcement
- **Root Cause**: `backend/routers/auth.py` issued access tokens without `org_id` in claims. As a result, the rate limiter defaulted `effective_org = actor_id`, allowing multi-user enterprise tenants to bypass the 100 req/min tenant quota.
- **Fix Applied**: Updated all 6 token issuance points in `backend/routers/auth.py`:
  - Verify registration OTP (line 390)
  - Verify login OTP (line 562)
  - Local registration (line 940)
  - Local login (line 1071)
  - Standard login (line 1144)
  - Invitation accept (line 1366)
  Each now passes `additional_claims={"org_id": str(user.org_id)} if getattr(user, "org_id", None) else None`.
- **Verification Evidence**: Automated test `test_25_tenant_wide_ai_quota_enforced_across_multiple_users` verifies that multiple distinct users within the same organization consume the shared tenant quota and are collectively bounded by the tenant limit.

### ADV-04: Unified Authentication Scope
- **Root Cause**: Rate limit keys used `f"auth_{path.replace('/', '_')}"`, generating separate keys `auth_auth_login` and `auth_auth_local-login`, permitting 10 total brute-force attempts instead of 5.
- **Fix Applied**: In `backend/core/rate_limiter.py`, mapped both `auth/login` and `auth/local-login` to canonical scope `auth_login`.
- **Verification Evidence**: Automated test `test_24_unified_login_scope_prevents_dual_endpoint_brute_force` sends 3 attempts to `/auth/login` and 2 attempts to `/auth/local-login`. The 6th attempt on either endpoint fails with HTTP 429.

### ADV-05: Machine Agent Authentication Protection
- **Root Cause**: `runtime/auth` was omitted from `AUTH_CANONICAL_PREFIXES`, falling through to public IP rate limits (60 req/min fail-open).
- **Fix Applied**: Added `MACHINE_AUTH_CANONICAL_PREFIXES = ("runtime/auth",)`. Configured `RATE_LIMIT_MACHINE_AUTH_LIMIT = 30` and enforced `fail_policy="closed"` on Redis outage.
- **Verification Evidence**: Automated test `test_26_machine_auth_rate_limiting_and_fail_closed` verifies that `/api/v1/runtime/auth` enforces the 30 req/min limit and fails closed with HTTP 503 if Redis becomes unreachable.

### ADV-06: Redis Cluster Hash Tag Colocation
- **Root Cause**: The Lua script executes `INCR key .. ':seq'`. Without Redis hash tags `{...}`, `key` and `key:seq` hash to different slots on a Redis Cluster, throwing `CROSSSLOT` exceptions.
- **Fix Applied**: Updated `_make_key` to format keys as `f"{{rl:{dimension}:{safe_hash}:{scope}:{window}}}"`. In Redis Cluster, CRC16 hashing is performed only on the substring inside `{...}`, guaranteeing colocation. SHA-256 truncation was increased from 16 to 32 hex chars (128-bit entropy).
- **Verification Evidence**: Automated test `test_27_redis_cluster_hash_tag_compatibility` verifies that both keys share identical hash tag substrings.

### ADV-07: Supabase Auth JWT Verification
- **Root Cause**: `extract_caller_identity()` only checked `settings.SECRET_KEY`, causing Supabase Auth JWTs (signed with `SUPABASE_JWT_SECRET`) to fail decoding and be downgraded to anonymous public traffic.
- **Fix Applied**: Added secondary verification step using `settings.SUPABASE_JWT_SECRET` with HS256 algorithm. Extracted `sub` and `org_id` from payload, `app_metadata`, or `user_metadata`.
- **Verification Evidence**: Automated test `test_28_supabase_jwt_verification_and_org_extraction` verifies that tokens signed with `SUPABASE_JWT_SECRET` are correctly recognized as `JWT` callers with appropriate `org_id`.

### ADV-08: Dual-Engine Testing Documentation
- **Root Cause**: Lack of formal operational boundaries between `MemorySlidingWindowEngine` and live Redis clusters.
- **Fix Applied**: Fully documented in `docs/security/AGENTGUARD_GLOBAL_RATE_LIMITING_IMPLEMENTATION_SPEC.md` and `docs/deployment/AGENTGUARD_STAGING_ENVIRONMENT_VARIABLES.md`. Local unit tests use the in-memory engine, while staging and production rely on real Redis clusters with identical atomic Lua logic.

---

## 4. Codebase Files Modified

| File Path | Description of Changes | Lines Affected |
|:---|:---|:---|
| `backend/main.py` | Inverted middleware registration: `RateLimitingMiddleware` mounted before `CORSMiddleware` so CORS wraps all 429/503 responses. | 76–90 |
| `backend/config.py` | Added `RATE_LIMIT_MACHINE_AUTH_LIMIT` (30) and `RATE_LIMIT_TRUST_CLOUDFLARE_HEADERS` (False). | 114–115 |
| `backend/routers/auth.py` | Added `additional_claims={"org_id": str(user.org_id)}` across all 6 token issuance points. | 390–396, 566–572, 940–946, 1071–1077, 1144–1150, 1366–1372 |
| `backend/core/rate_limiter.py` | Implemented cluster hash tags `{rl:...}`, unified `auth_login` scope, machine auth category, strict anti-spoofing IP resolution, and Supabase JWT decoding. | 100–108, 182–245, 402–408, 521–548, 585–630 |
| `backend/tests/test_global_rate_limiting.py` | Added 8 comprehensive adversarial test cases (`test_21` through `test_28`). | 490–698 |
| `docs/deployment/AGENTGUARD_STAGING_ENVIRONMENT_VARIABLES.md` | Documented staging environment variables for machine auth limits and Cloudflare header trust flags. | 120–131 |
| `docs/security/AGENTGUARD_GLOBAL_RATE_LIMITING_IMPLEMENTATION_SPEC.md` | Updated architecture specification and added Section 11 documenting adversarial audit remediations. | 249–285 |

---

## 5. Verification & Test Execution Results

All automated test suites executed with 100% passing results:

```
======================================================================
1. Rate Limiting Suite (backend/tests/test_global_rate_limiting.py)
   28 passed in 4.71s
   Covers: Sliding window, boundary burst, multi-instance concurrency,
   anti-spoofing, CORS preservation, unified login scope, AI tenant
   quotas, machine auth fail-closed, Redis cluster hash tags, Supabase JWTs.

2. Authentication, OTP & IAM Suites
   backend/tests/test_authentication_and_otp_flows.py
   backend/tests/test_websocket_auth.py
   backend/tests/test_iam_direct.py
   38 passed in 13.14s

3. Tenant Isolation, Runtime Security & SSRF Suites
   backend/tests/test_tenant_isolation_and_security_audit.py
   backend/tests/test_tenant_security_penetration.py
   backend/tests/test_runtime_security_invariants.py
   backend/tests/test_tool_proxy_suite.py
   backend/tests/test_ssrf_dns_rebinding_suite.py
   64 passed in 35.87s

4. Hardening & Infrastructure Suites
   backend/tests/test_phase6f_production_hardening.py
   backend/tests/test_phase6d_infrastructure.py
   64 passed in 40.35s

5. Frontend Linter (npm --prefix frontend run lint)
   ✔ No ESLint warnings or errors
======================================================================
TOTAL: 194 automated security and regression tests PASSED. 0 failed.
```

---

## 6. Staging Release Gate Verdict

Based on the independent adversarial review, the remediation of findings ADV-01 through ADV-08, and the complete passage of all 194 automated regression tests:

### **VERDICT: READY FOR ISOLATED STAGING DEPLOYMENT**

The global distributed rate-limiting system (`AG-SEC-02`) is hardened, cryptographically verified, and cluster-compatible. AGENTGUARD is approved to proceed to the isolated staging provisioning phase according to `docs/deployment/AGENTGUARD_STAGING_INFRASTRUCTURE_PLAN.md`.
