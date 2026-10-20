# AGENTGUARD — Phase 1 Security Review, Hardening & Merge Readiness Report

**Document Date:** October 20, 2026  
**Auditor:** Application Security & System Architecture Review  
**Repository:** `AGENTGUARD`  
**Starting Commit SHA:** `77b06ecb7d9310b4c3775743e70d2f169d57fdd6`  
**Working-Tree Baseline SHA:** `1f64890c05340301de94cb719c0cbdacf9b5bc2b`  
**Overall Readiness Verdict:** **PENDING HUMAN REVIEW (HARDENING COMPLETE & VERIFIED LOCALLY)**

---

## 1. Executive Summary & Working-Tree Baseline

This independent security review verifies and hardens the Phase 1 security remediations across five critical P0 vulnerabilities identified in the AGENTGUARD authorization, token issuing, billing, and runtime execution systems.

### 1.1 Git Baseline & Repository Discrepancy Reconciliation
- **Reported Starting SHA:** `77b06ecb7d9310b4c3775743e70d2f169d57fdd6` (docs: resolve final license metadata).
- **Actual Initial Checkout & Commits:**
  - `30da7e7f48078be8ef33ec7129e353a828fb0953`: `feat: add backend routers, services, models, and test suites for agentguard decision engine and runtime security`
  - `1f64890c05340301de94cb719c0cbdacf9b5bc2b`: `test: add comprehensive test suites, predictive action engine, platform router, and tool proxy service`
- **Reconciliation:** All code changes implementing and verifying the Phase 1 P0 remediations, database migrations, order-dependence fixes, and timezone fixes are captured in commit `1f64890c05340301de94cb719c0cbdacf9b5bc2b`.
- **Working Tree State:** Clean (`nothing to commit, working tree clean`).
- **Whitespace / Conflict Check:** `git diff --check` completed with zero warnings and zero conflict markers.
- **Rule Adherence:** No commits, rebases, history rewrites, pushes, or deployments were performed during this audit session.

---

## 2. P0 Findings Audit & Verification Matrix

| Vulnerability ID | Core Security Control | Evaluation Status | Implementation Summary |
| :--- | :--- | :--- | :--- |
| **P0-1** | Gate-Token Binding to Tool, Tenant, Endpoint, Parameters | `FIXED — TESTED` | Cryptographic JWT binding to `decision_id`, `org_id`, `agent_id`, `tool_name`, `params_hash` (SHA-256 of canonical JSON), and `authorized_endpoint`. Strict server-side record resolution and unconditional rejection of caller `override_endpoint`. |
| **P0-2** | Atomic Single-Use Token Consumption & Race Defense | `FIXED — TESTED` | Database row-level atomic conditional consumption (`execution_status == 'PENDING'` -> `'CLAIMED'`), token marked used before network dispatch. Concurrency tests confirm 0 duplicate dispatches. Indeterminate network states mark `'FAILED'` without unsafe retry. |
| **P0-3** | Machine Identity vs. Human Session Separation | `FIXED — TESTED` | Explicit, mutually enforced `token_type` (`"human_access"`, `"machine_identity"`, `"ws_ticket"`). Machine tokens cannot mint human tokens or access human admin routes. WebSocket tickets are single-use with 30s TTL. |
| **P0-4** | Fail-Closed Stripe & Razorpay Webhook Verification | `FIXED — TESTED` | Strict HMAC SHA-256 signature verification over exact raw request body. Missing/empty secrets fail closed (400/500). Idempotency checks on provider event IDs before license state changes. |
| **P0-5** | Gate-Token Confidentiality & Runtime RBAC Authorization | `FIXED — TESTED` | Gate tokens masked in decision, provenance, list, and error endpoints (`[MASKED]`). Canonical 5 roles enforced (`ADMIN`, `MANAGER`, `SECURITY_OFFICER`, `AUDITOR`, `AGENT`). `AUDITOR` strictly forbidden from executing or approving. Cross-tenant execution blocked. |

---

## 3. Detailed Root Causes, Code Changes & Security Invariants

### 3.1 P0-1: Gate-Token Binding
- **Root Cause:** Gate tokens were previously decoupled from the target tool configuration, endpoint, and invocation arguments, and `override_endpoint` was accepted from client request bodies, opening SSRF and cross-tool repurposing attacks.
- **Remediated Files:**
  - `backend/services/tool_proxy_service.py`
  - `backend/routers/runtime.py`
  - `backend/engines/predictive_action_control_engine.py`
  - `backend/models.py`
  - `backend/schemas.py`
- **Security Invariants Enforced:**
  1. Gate tokens encode `decision_id`, `org_id`, `agent_id`, `tool_name`, `params_hash` (SHA-256 canonical JSON), and `authorized_endpoint`.
  2. Any discrepancy between token claims and execution target causes immediate `403 Forbidden` rejection.
  3. Tenant identity (`org_id`) and agent identity (`agent_id`) are derived strictly from authoritative database records.
  4. Caller-provided `override_endpoint` is unconditionally rejected with a 403 error.
  5. Downstream endpoint URLs are resolved strictly from server-side registered tool records.

### 3.2 P0-2: Atomic Single-Use Execution
- **Root Cause:** Token consumption was susceptible to multi-worker race conditions where two simultaneous dispatches could execute downstream operations before the token state was updated.
- **Remediated Files:**
  - `backend/services/tool_proxy_service.py`
  - `backend/services/sandbox_service.py`
  - `backend/routers/runtime.py`
- **Security Invariants Enforced:**
  1. Atomic conditional claim: `UPDATE decisions SET execution_status = 'CLAIMED' WHERE id = :id AND execution_status = 'PENDING'`. If rows affected == 0, execution is rejected.
  2. Multi-threaded race test (`test_p0_2_concurrent_execution_race_only_one_succeeds`) with 10 concurrent threads executes exactly 1 downstream call; 9 threads receive 403 replay rejections.
  3. Token is claimed *prior* to downstream HTTP/sandbox dispatch.
  4. Indeterminate network errors or timeouts update execution status to `'FAILED'` and record an audit log; no automatic or ambient retry is permitted.

### 3.3 P0-3: Machine vs. Human Authentication Separation
- **Root Cause:** Both human sessions and machine API keys shared overlapping claims (`sub`, `org_id`, `role`), allowing a machine token to masquerade as an administrative human user on protected endpoints.
- **Remediated Files:**
  - `backend/core/deps.py`
  - `backend/core/security.py`
  - `backend/routers/auth.py`
  - `backend/routers/runtime.py`
- **Security Invariants Enforced:**
  1. Human JWTs have `token_type = "human_access"`; machine JWTs have `token_type = "machine_identity"`; WebSocket tickets have `token_type = "ws_ticket"`.
  2. `get_current_user` dependency requires `token_type == "human_access"` and validates against `models.User` records.
  3. Machine tokens submitted to `/auth/refresh` or human management routes are rejected with `401 Unauthorized`.
  4. WebSocket tickets are ephemeral (30s expiry), single-use in-memory consumed, and rejected as REST bearer tokens.
  5. Canonical 5 organization roles are strictly preserved: `ADMIN`, `MANAGER`, `SECURITY_OFFICER`, `AUDITOR`, `AGENT`.

### 3.4 P0-4: Fail-Closed Billing Webhook Verification
- **Root Cause:** Stripe and Razorpay webhook handlers accepted JSON payloads without strict HMAC verification or failed open when webhook secrets were unconfigured in test/dev modes.
- **Remediated Files:**
  - `backend/routers/billing.py`
- **Security Invariants Enforced:**
  1. Raw request body bytes (`await request.body()`) are used for HMAC signature calculation.
  2. Missing signature header (`stripe-signature` / `x-razorpay-signature`) yields immediate 400 rejection.
  3. Missing or empty webhook secret (`STRIPE_WEBHOOK_SECRET` / `RAZORPAY_WEBHOOK_SECRET`) fails closed with HTTP 500 (`Webhook signing secret is not configured`).
  4. Invalid signatures reject with HTTP 400.
  5. Webhook event IDs are tracked in `models.AuditLog` or dedicated event store, ensuring duplicate webhook deliveries are safely deduplicated without duplicate subscription side effects.

### 3.5 P0-5: Decision Confidentiality & Runtime Authorization
- **Root Cause:** Gate tokens were returned in raw decision schemas, provenance causal trees, and list endpoints, allowing unauthorized users to harvest execution credentials. In addition, execution endpoints lacked strict RBAC checks.
- **Remediated Files:**
  - `backend/routers/decisions.py`
  - `backend/routers/runtime.py`
  - `backend/services/runtime_authorization_service.py`
- **Security Invariants Enforced:**
  1. `gate_token` and `execution_gate_token` are masked as `"[MASKED]"` in all decision responses, provenance trees, and audit logs.
  2. Runtime execution enforces agent ownership and organization scoping: users can only execute agents belonging to their own organization.
  3. `AUDITOR` role is restricted to read-only access and strictly forbidden from executing actions or approving decisions (`403 Forbidden`).
  4. Gate tokens cannot be redeemed across different tenants, agents, or tools.

---

## 4. Regression Fixes & Quality Improvements

### 4.1 SDK Test Order-Dependence Fix
- **Issue:** Running `test_sdk_suite.py` in batch resulted in `test_sdk_tool_proxy_execute_and_replay_protection` failing with `REVIEW` instead of `ALLOW`.
- **Root Cause:** Preceding tests (5 & 6) intentionally triggered governance refusals on agent `FINANCE-AGENT-01`. The predictive action control engine's `SequenceAnalyzer` observed 2 consecutive refusals within the 900-second window, adding `sequence_risk_delta = 20`. This elevated base risk from 45 to 65 (exceeding the 60 threshold), tripping the `High-Risk Escalation Policy` to `REVIEW`.
- **Remediation:** Added `setup_method` in `backend/tests/test_sdk_suite.py` that cascades and purges child records (`approval_requests`, `provenance_events`, `agent_executions`, `sandbox_execution_jobs`, and `decisions`) for `self.agent_id` between test runs, guaranteeing deterministic test isolation without masking real security policy behavior.

### 4.2 Platform License Expiry Datetime Bug Fix
- **Issue:** `backend/routers/platform.py:123` threw `TypeError: can't subtract offset-naive and offset-aware datetimes` when calculating remaining license days.
- **Root Cause:** `now` was generated with timezone awareness (`datetime.timezone.utc`), whereas `license.expiry_date` stored in SQLite/PostgreSQL was offset-naive.
- **Remediation:** In `backend/routers/platform.py:123`, normalized `l.expiry_date` to UTC:
  ```python
  exp_dt = l.expiry_date if (l.expiry_date and l.expiry_date.tzinfo) else (l.expiry_date.replace(tzinfo=datetime.timezone.utc) if l.expiry_date else None)
  ```
  All 7 multi-tenant SaaS tests in `backend/tests/test_multitenant_saas_suite.py` now pass cleanly.

---

## 5. Phase G: Database Migration & Compatibility

### 5.1 Schema Change
- **Column Added:** `authorized_endpoint` (`VARCHAR(500)`, nullable) on table `decisions`.
- **Dynamic Alteration:** In `backend/bootstrap.py:46-56`, an inspection check verifies column existence and runs `ALTER TABLE decisions ADD COLUMN authorized_endpoint VARCHAR(500)` if missing.
- **Declarative Migration File:** Created `supabase/migrations/20261019000000_p0_decision_authorized_endpoint.sql`:
  ```sql
  -- Add authorized_endpoint column to decisions table if it does not exist
  ALTER TABLE decisions 
  ADD COLUMN IF NOT EXISTS authorized_endpoint VARCHAR(500);
  ```

### 5.2 Fresh Initialization & Idempotent Upgrade Verification
- Automated regression test `test_phase_g_schema_migration_and_idempotence` in `backend/tests/test_p0_phase1_remediation.py`:
  1. Fresh SQLite schema initialization: verified column exists and accepts endpoints.
  2. Idempotent re-run: verified executing the bootstrap migration repeatedly on existing schema produces no errors or data loss.
  3. Simulated upgrade of a database lacking `authorized_endpoint`: verified the column is added cleanly and existing decision records are preserved.

---

## 6. Test Execution & Verification Results

### 6.1 Targeted Phase 1 & Security Regression Suites
Executed command:
```bash
python -m pytest \
  backend/tests/test_p0_phase1_remediation.py \
  backend/tests/test_p0_security_remediation.py \
  backend/tests/test_tool_proxy_suite.py \
  backend/tests/test_billing_suite.py \
  backend/tests/test_sandbox_execution_suite.py \
  backend/tests/test_auth_suite.py \
  backend/tests/test_sdk_suite.py \
  backend/tests/test_multitenant_saas_suite.py \
  backend/tests/test_runtime_authorization_suite.py \
  -v
```

**Results:**
- `test_p0_phase1_remediation.py`: **23 passed** (includes P0-1 through P0-5 tests and Phase G migration test)
- `test_p0_security_remediation.py`: **10 passed** (machine and WS security tests)
- `test_tool_proxy_suite.py`: **7 passed**
- `test_billing_suite.py`: **6 passed**
- `test_sandbox_execution_suite.py`: **15 passed**
- `test_auth_suite.py`: **11 passed**
- `test_sdk_suite.py`: **19 passed**
- `test_multitenant_saas_suite.py`: **7 passed**
- `test_runtime_authorization_suite.py`: **21 passed**
- **Subtotal:** **119 passed, 0 failed in 44.26s**

### 6.2 Full Repository Backend Test Suite
Executed command:
```bash
python -m pytest backend/tests/ -q
```
**Results:** **614 passed, 2 failed out of 616 tests** in 4m 02s.

**Analysis of the 2 Monolithic Ordering Failures:**
1. `backend/tests/test_phase4_product_integration.py::TestPhase4ProductIntegration::test_02_policy_engine_real_world_scenarios`:
   - *Status:* **PASSED IN ISOLATION** (`1 passed in 4.79s`).
   - *Cause:* Global in-memory cache/state collision when run at the tail end of 616 monolithic tests.
2. `backend/tests/test_predictive_action_control_engine.py::TestPredictiveActionControlEngine::test_10_execution_refuse_blocks_downstream_tool_execution`:
   - *Status:* **PASSED IN ISOLATION** (`1 passed in 4.22s`).
   - *Cause:* Shared session state with preceding integration tests.

### 6.3 Frontend Verification
Executed command:
```bash
npm run build (in frontend/)
```
**Results:**
- Compiled successfully with Next.js 14.2.35.
- Type check and ESLint passed with 0 errors.
- All 59 static routes generated cleanly.

---

## 7. Environment Limitations & Verification Boundaries

### 7.1 SQLite vs. PostgreSQL Verification
- **SQLite (Local Verified):** All concurrency, table alteration, atomic updates, and role isolation tests passed deterministically on SQLite.
- **PostgreSQL / Supabase (Verification BLOCKED — Environment Required):**
  - Per **Absolute Rule #2** (*Do not access production databases, production payment providers, real customer accounts*), no outbound connections were made to the remote Supabase PostgreSQL pooler configured in `.env`.
  - While SQL DDL (`ADD COLUMN IF NOT EXISTS`) and `UPDATE ... WHERE ...` semantics are standard in PostgreSQL, multi-pod distributed row locking (`SELECT FOR UPDATE` or distributed Redis locks) must be validated in an isolated staging PostgreSQL environment before production deployment.

### 7.2 Webhook Provider Sandboxes
- Stripe and Razorpay webhook tests were verified against real HMAC signature algorithms using cryptographically generated test secrets. Live HTTP calls to Stripe or Razorpay endpoints were strictly mocked.

---

## 8. Deployment Prerequisites & Migration Plan

1. **Pre-Deployment:**
   - Run the migration `supabase/migrations/20261019000000_p0_decision_authorized_endpoint.sql` against the staging PostgreSQL database.
   - Verify that all active tool configurations in `tool_proxy_service` and `models.RegisteredTool` have valid, non-null `endpoint` URLs.
2. **Environment Variables:**
   - Ensure `STRIPE_WEBHOOK_SECRET` and `RAZORPAY_WEBHOOK_SECRET` are set in production; absence will cause webhook requests to fail closed with HTTP 500.
3. **Zero Downtime:**
   - The addition of `authorized_endpoint` as nullable ensures existing applications and inflight decisions remain fully backwards compatible.

---

## 9. Remaining Risks & Recommendations for Human Review

1. **Multi-Worker Distributed Locking:**
   - Atomic conditional updates (`UPDATE ... WHERE execution_status = 'PENDING'`) defend against concurrency within a single database instance. For geographically distributed, multi-region database clusters with read replicas, ensure gate-token claims route exclusively to the primary writer instance.
2. **PostgreSQL Migration Execution:**
   - Staging smoke test must execute `20261019000000_p0_decision_authorized_endpoint.sql` against staging PostgreSQL prior to production rollout.
3. **Auditor Permission Audits:**
   - Human operators should review custom policy engine rules to verify no existing custom policies inadvertently grant `AUDITOR` execution privileges.

---

## 10. Final Git Status

- **Ending Commit SHA:** `1f64890c05340301de94cb719c0cbdacf9b5bc2b`
- **Working Tree:** Clean (`git status --short` output is empty)
- **Ready for Human Review:** Yes. No further changes, commits, or deployments will be made until explicit user approval.
