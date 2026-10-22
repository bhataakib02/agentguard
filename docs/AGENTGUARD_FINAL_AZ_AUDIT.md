# AGENTGUARD — FINAL A–Z COMPREHENSIVE APPLICATION AUDIT REPORT

**Audit Date:** October 22, 2026  
**Audited Repository:** `D:\AGENTGUARD`  
**Git Repository Origin:** `https://github.com/bhataakib02/agentguard.git`  
**Git Commit SHA / HEAD:** `1ece1ec53ceff2ff07dc8f0522904fcc482cc6b1`  
**Branch:** `main` (clean working tree, 0 modified files, 0 untracked files)  
**Lead Security & Code Quality Auditor:** Antigravity AI Senior Security & Architecture Specialist  

---

## 1. Executive Summary

A comprehensive, evidence-based, A–Z technical audit of the complete AGENTGUARD codebase was conducted across its backend services, database schema, frontend web application, SDKs, background workers, security policies, and deployment infrastructure.

AGENTGUARD is an enterprise-grade AI runtime security control plane designed to intercept, authorize, sandbox, and monitor autonomous AI agents. The application implements an advanced 12-stage runtime authorization kernel, cryptographic Ed25519 agent passports, AES-256-GCM secret encryption at rest, connection-pinned SSRF defenses with DNS rebinding protection, single-use WebSocket authentication tickets, and an isolated sandbox execution pipeline.

### High-Level Summary of Findings
1. **Critical Architectural Strengths:**
   - The core runtime authorization path (`runtime_authorization_service.py` and `tool_proxy_service.py`) demonstrates rigorous defenses against execution token replay, tool hijacking, parameter tampering, and cloud-metadata SSRF.
   - Machine agent identities (`AuthenticatedAgent`) are strictly separated from human user sessions; machine tokens cannot authenticate human administrative REST endpoints.
   - Sensitive at-rest secrets (API keys, webhooks, BYOK keys) utilize SHA-256 hashing or AES-256-GCM encryption with keyring rotation fallback.
   - The backend test suite passed with 100% success rate (639 passed, 0 failed, 1 warning, 116.11s duration).
   - The Next.js production build succeeded with 0 errors, prerendering all 59 static application routes.
   - The TypeScript SDK test suite passed with 5/5 tests verified.

2. **Identified Security & Functional Defects:**
   - **SEC-01 (High):** Missing role-based authorization checks in `policies.py`, `tools.py`, `capabilities.py`, `red_team.py`, `agents.py (create/update)`, and `billing.py (simulate-payment)`. Any authenticated organization member with baseline role `USER`, `VIEWER`, or `ANALYST` can create/delete governance policies, register or redirect tool endpoints, issue high-value capability tokens, launch red-team attacks, modify agent budgets, or trigger artificial subscription upgrades.
   - **SEC-02 (High):** Secondary Outbound SSRF & DNS Rebinding risk in background workers (`webhook_tasks.py` and `siem_tasks.py`). Unlike `tool_proxy_service.py`, asynchronous webhook delivery and SIEM forwarder tasks rely on `requests.post()` after a pre-flight DNS validation check. This leaves them vulnerable to Time-Of-Check to Time-Of-Use (TOCTOU) DNS rebinding and automatic HTTP redirect following.
   - **SEC-03 (Medium):** Missing state machine transition check in `POST /approvals/{id}/act`. Approval requests can be resolved multiple times, flipping decisions or generating new gate tokens without checking if `status == "PENDING"`.
   - **SEC-04 (Low):** Global tenant leakage in `/organization/dashboard`: line 77 queries `db.query(models.ApprovalRequest).count()` without filtering by `target_org_id`, disclosing global system approval volumes to tenant administrators.
   - **UI-01 (Medium):** Dead buttons and placeholder alerts:
     - `frontend/src/app/page.tsx`: Enterprise demo request form triggers a browser `alert()` without sending backend API requests or persisting contact details.
     - `frontend/src/app/platform/page.tsx`: Dashboard export button triggers `alert("Exporting Platform Control Center Overview report...")` without executing an actual export.
     - `frontend/src/app/platform/governance/page.tsx`: Inspect button triggers a browser `alert()` with raw text rather than opening a dedicated modal or navigation view.

---

## 2. Exact Repository State and Verification Metadata

| Attribute | Verified Value |
|---|---|
| **Local Working Directory** | `D:\AGENTGUARD` |
| **Git Commit HEAD** | `1ece1ec53ceff2ff07dc8f0522904fcc482cc6b1` |
| **Branch** | `main` (tracking `origin/main`) |
| **Remote Origin** | `https://github.com/bhataakib02/agentguard.git` |
| **Working Tree Status** | Clean (0 modified, 0 staged, 0 untracked files) |
| **Python Environment** | Python 3.10.11 (AMD64) |
| **Node.js Environment** | v22.22.0 / npm 10.9.4 |
| **Database Engines Supported** | PostgreSQL (Supabase) in production; SQLite in local development |
| **Operating System** | Microsoft Windows |

---

## 3. Architecture & Feature Inventory

### 3.1 Backend Architecture
- **Framework:** FastAPI with Uvicorn ASGI server.
- **ORM / Database:** SQLAlchemy 2.0 with connection pooling (`DB_POOL_SIZE=10`, `DB_MAX_OVERFLOW=20`).
- **Domain Routers (39 mounted modules):**
  `admin`, `agent_network`, `agents`, `ai`, `analytics`, `approvals`, `assistant`, `audit`, `auth`, `behavior`, `billing`, `capabilities`, `decisions`, `developers`, `digital_twin`, `economics`, `iam`, `impact`, `integrations`, `notifications`, `optimization`, `organization`, `permissions`, `platform`, `policies`, `profile`, `provenance`, `red_team`, `reports`, `risk`, `runtime`, `security`, `settings`, `simulation`, `system`, `telemetry`, `tools`, `trust`, `webhooks`.
- **Core Security Modules:**
  - `backend/core/deps.py`: User and machine agent resolution, API key authentication, permission dependencies.
  - `backend/core/permissions.py`: Authoritative enterprise RBAC role matrix (11 human roles + machine `AGENT`).
  - `backend/core/security.py`: Password hashing (bcrypt), JWT generation, AES-256-GCM encryption with HKDF key derivation.
  - `backend/core/supabase_admin.py`: Supabase Admin API client.
- **Asynchronous Processing:** Celery worker with Redis broker (`REDIS_URL`, fallback to eager mode in local tests).
- **Tool Proxy Gateway:** `backend/services/tool_proxy_service.py` with custom `PinningTransport` and `PinningNetworkBackend` for DNS rebinding and SSRF mitigation.

### 3.2 Frontend Architecture
- **Framework:** Next.js 14.2.15 (App Router) with React 18.3.1.
- **Routing Structure:**
  - `(auth)`: Login, Register, Forgot Password, Verify OTP.
  - `(app)`: 25 distinct workspace management routes.
  - `platform`: 20 cross-tenant platform control plane routes for `SUPER_ADMIN`.
  - Public marketing landing page (`/`), 403 Forbidden page (`/403`), and 404 handler (`not-found.tsx`).
- **State & Identity:** `useAuth.tsx` context wrapper integrating Supabase Auth client and backend `/auth/me` authoritative sync.
- **WebSocket Streaming:** `RobustWebSocketClient` with single-use ticket exchange (`POST /auth/ws-ticket`), automatic reconnect with exponential backoff, and 15-second heartbeat ping/pong.

### 3.3 SDKs
- **Python SDK:** `agentguard` (1.0.0) with LangChain callback handler (`langchain_handler.py`) and CrewAI middleware (`crewai_middleware.py`).
- **TypeScript SDK:** `@agentguard/sdk` (1.0.0) with full API client surface, typed schemas, and custom error classes.

---

## 4. Route & Coverage Statistics

### 4.1 Route & Surface Metrics

| Component | Count | Verification Status |
|---|---|---|
| **Backend API Routers** | 39 files | All registered under `/api` and `/api/v1` |
| **Backend API Endpoints** | 164 endpoints | 164 statically audited; 152 covered in test suites |
| **Frontend Static/App Pages** | 59 routes | 59 compiled and prerendered successfully |
| **Backend Test Modules** | 50 files | 639 collected and executed |
| **Database Tables (Models)** | 42 tables | Defined in `backend/models.py` |

### 4.2 Coverage Summary
- **Backend Tests:** 639 / 639 passed (100% passing rate).
- **TypeScript SDK Tests:** 5 / 5 passed (100% passing rate).
- **Frontend Production Build:** 59 / 59 static routes generated.
- **Frontend Linting:** 0 errors, 7 non-blocking warnings.

---

## 5. Security Audit: Authentication, IAM & Access Control

### 5.1 Authentication and Identity Findings
- **Machine vs. Human Token Separation (VERIFIED):**
  `backend/core/deps.py` (lines 250–261) strictly inspects JWT claims. Tokens with `tok_type in ("machine", "ws_ticket")`, `agent_id`, `ticket_id`, or `credential_id` are rejected if presented to human user endpoints. Conversely, `get_current_machine_agent` only accepts machine credentials.
- **Session Revocation (VERIFIED):**
  `POST /auth/logout` sets `models.Session.revoked = True`. Subsequent requests using that token are rejected in `get_current_user` (line 300).
- **WebSocket Single-Use Tickets (VERIFIED):**
  `POST /auth/ws-ticket` generates a 60-second single-use ticket stored in Redis/memory. `main.py` (lines 173–197) rejects query-string bearer tokens and enforces single-use consumption.
- **Account Status Enforced (VERIFIED):**
  Suspended or inactive users (`status != "ACTIVE"`) are denied access in `get_current_user` (line 316) with HTTP 403.

### 5.2 Enterprise IAM & Permission Matrix Audit

The application defines an authoritative role hierarchy in `backend/core/permissions.py`:
- `SUPER_ADMIN` (Level 9): Cross-tenant platform administrator.
- `ADMIN` (Level 8): Organization administrator.
- `DEVELOPER` (Level 7)
- `MANAGER` (Level 6)
- `SECURITY_OFFICER` / `SECURITY_ANALYST` (Level 5)
- `OPERATOR` (Level 4)
- `ANALYST` (Level 3)
- `AUDITOR` / `VIEWER` (Level 2)
- `USER` (Level 1): Baseline registered member.
- `AGENT`: Machine identity.

#### Critical IAM Gaps Discovered
1. **Unprotected Policy Mutation (`backend/routers/policies.py`):**
   - Endpoints `POST /policies`, `PATCH /policies/{policy_id}`, `DELETE /policies/{policy_id}`, `POST /policies/{policy_id}/toggle`, `POST /policies/{policy_id}/rules`, `PATCH /policies/{policy_id}/rules/{rule_id}`, and `DELETE /policies/{policy_id}/rules/{rule_id}` depend only on `current_user: models.User = Depends(get_current_user)`.
   - **Impact:** Any user with `USER`, `VIEWER`, or `AUDITOR` role can disable security policies, delete rules, or create permissive rules within their organization.
2. **Unprotected Tool Management (`backend/routers/tools.py`):**
   - `POST /tools`, `PUT /tools/{tool_id}`, `DELETE /tools/{tool_id}` use `Depends(get_current_user)` with no role restriction.
   - **Impact:** Any member can change a tool's destination endpoint to point to an arbitrary external URL.
3. **Unprotected Capability Issuance (`backend/routers/capabilities.py`):**
   - `POST /capabilities/issue` and `POST /capabilities/revoke/{token_code}` use `Depends(get_current_user)` without checking `ADMIN` or `MANAGER` role.
   - **Impact:** Any user can issue a capability token granting an agent arbitrary spend limits.
4. **Unprotected Red-Team Execution (`backend/routers/red_team.py`):**
   - `POST /red-team/run` and `POST /red-team/fuzz` do not check `PERM_SECURITY_VIEW` or `SECURITY_OFFICER` role.
5. **Unprotected Payment Simulation (`backend/routers/billing.py`):**
   - `POST /billing/simulate-payment` only requires `Depends(get_current_user)`. Any authenticated user can upgrade their organization's plan and extend license validity by 30 days.

---

## 6. Agent Runtime, Policy Engine & Execution Boundary

### 6.1 12-Stage Runtime Kernel Evaluation Path
1. **Tenant Isolation:** Verifies calling agent/user organization match.
2. **Agent Lifecycle:** Blocks `SUSPENDED` or `CIRCUIT_BREAK` agents.
3. **Passport Crypto:** Ed25519 digital signature verified against root key.
4. **Permissions Check:** Verifies agent permission assignments in DB.
5. **Capability Token Check:** Validates capability name, scope, expiration, and amount limit.
6. **Financial Budget Check:** Validates action amount against agent daily and monthly limits.
7. **Circuit Breaker Check:** Rejects actions if breaker state is `TRIPPED` or `SUSPENDED`.
8. **Policy Engine Evaluation:** Evaluates condition expressions via AST engine (`ALLOW`, `REVIEW`, `REFUSE`).
9. **Decision Persistence:** Decision recorded with snapshot of authorized tool endpoint and parameters.
10. **Gate Token Generation:** If `ALLOW`, issues cryptographically random single-use token (`gate_<hex>`) with 300s TTL.
11. **Human Escalation:** If `REVIEW`, creates `ApprovalRequest` and halts forward execution.
12. **Telemetry & Audit:** Logs execution intent and risk score.

### 6.2 Forward Execution Tool Proxy (`backend/services/tool_proxy_service.py`)
- **Atomic Gate Token Consumption:** Uses atomic SQL update (`UPDATE decisions SET gate_token_used = True WHERE gate_token_used = False AND id = :id`). Replays immediately return HTTP 400 `GATE_TOKEN_REPLAYED`.
- **Endpoint Snapshot Binding:** Verifies that `tool_record.endpoint == decision.authorized_endpoint`. If the endpoint changed between authorization and execution, execution is aborted.
- **Parameter Tamper Protection:** Canonical JSON serialization check ensures executed parameters match authorized parameters.
- **Caller Override Rejection:** Any caller-provided `override_endpoint` is unconditionally rejected.

---

## 7. SSRF & Outbound Network Security Audit

### 7.1 Primary Tool Proxy (`tool_proxy_service.py`)
The tool proxy implements comprehensive SSRF protections:
- **Port Allowlist:** Standard web ports `80, 443, 8000, 8080, 8443` allowed; other ports rejected.
- **Embedded Credentials:** URLs containing `@` or userinfo are rejected.
- **Cloud Metadata & Reserved Blocks:** Explicitly blocks AWS/GCP/Azure metadata IPs (`169.254.169.254`, `100.100.100.200`, `metadata.google.internal`), RFC1918 private ranges, CGNAT, loopback, link-local, multicast, documentation ranges, and IPv4-mapped IPv6.
- **Connection Pinning:** `PinningTransport` uses a custom `httpcore.SyncBackend` (`PinningNetworkBackend`) that forces the TCP socket to connect strictly to `pinned_ip` while preserving the original hostname for TLS SNI and HTTP `Host` header.
- **Redirects:** Automatic redirects are disabled (`follow_redirects=False`) to prevent 3xx redirects to internal addresses.

### 7.2 Advisory Findings Revalidation
- **F-1 (Private Transport Attributes):**
  `PinningTransport` accesses `self._pool._ssl_context` from `httpcore.ConnectionPool`. In `httpcore>=1.0.0`, `_ssl_context` is a private attribute.
  *Assessment:* Operational risk. Future minor version upgrades of `httpcore` or `httpx` could break connection pooling initialization. Recommend pinning `httpcore` in `requirements.txt` or creating a dedicated SSL context.
- **F-2 (Mutable Environment Settings):**
  `ToolProxyService` reads `getattr(settings, "ENVIRONMENT", "production")` dynamically.
  *Assessment:* In production deployments where environment variables are fixed in container runtimes, this is secure. However, in test processes where `settings.ENVIRONMENT` is monkeypatched, test hooks could leak. Verified that `set_mock_client`, `set_mock_transport`, and `set_dns_resolver` raise `RuntimeError` if environment is `production`.
- **F-3 (Synthetic DNS Fallback):**
  In non-production test environments with mock clients, `.internal`, `.test`, or `api.example.com` domains fall back to synthetic IP `93.184.215.14`.
  *Assessment:* Strictly guarded by `if not is_production`. Does not execute in production.

### 7.3 Discovered Secondary SSRF Risk (SEC-02)
- **Location:** `backend/tasks/webhook_tasks.py` (line 126) and `backend/tasks/siem_tasks.py` (line 155).
- **Mechanism:** Both tasks validate the target URL using `validate_webhook_url()`, which performs a DNS resolution check. However, they immediately execute `requests.post(endpoint.url, ...)` using Python's `requests` library.
- **Vulnerability:**
  1. `requests.post()` performs a second, unpinned DNS lookup, enabling DNS rebinding (TOCTOU).
  2. `requests.post()` automatically follows HTTP 3xx redirects by default. If a webhook or SIEM destination responds with a redirect to `http://169.254.169.254/computeMetadata/v1/`, `requests` will follow it and leak headers/credentials.

---

## 8. Billing, Webhooks & External Integrations

### 8.1 Stripe & Razorpay Webhook Security
- **Stripe Webhook (`backend/routers/billing.py`):**
  - Uses `hmac.new(..., hashlib.sha256)` with timestamp parsing (`t=..., v1=...`).
  - Reads raw body via `await request.body()`.
  - Fails closed in production or when `STRIPE_WEBHOOK_SECRET` is set. Rejects missing headers or invalid signatures.
  - Idempotency verified via `_is_event_already_processed()` against `AuditLog` records.
- **Razorpay Webhook (`backend/routers/billing.py`):**
  - Validates `X-Razorpay-Signature` against HMAC-SHA256 of raw request body.
  - Fails closed when configured or mandatory.
- **Missing RBAC on Sandbox Payment Simulation:**
  - `POST /billing/simulate-payment` lacks role checks. Any member can upgrade the organization's plan tier and extend license validity.

---

## 9. Comprehensive Frontend & UI/UX Audit

### 9.1 Route Inventory & Verification Results
All 59 routes were built and validated via `next build`:

| Route Category | Routes Verified | Status |
|---|---|---|
| **Public / Auth** | `/`, `/login`, `/register`, `/forgot-password`, `/verify-otp`, `/403`, `/_not-found` | Prerendered, responsive |
| **Workspace (App)** | `/dashboard`, `/activity`, `/agents`, `/agents/passport`, `/analytics`, `/approvals`, `/assistant`, `/audit`, `/capabilities`, `/decisions`, `/digital-twin`, `/economics`, `/iam`, `/iam/role-history`, `/notifications`, `/organization`, `/permissions`, `/policies`, `/profile`, `/provenance`, `/red-team`, `/reports`, `/reports/history`, `/reports/scheduled`, `/risk`, `/runtime`, `/runtime/telemetry`, `/settings`, `/simulation` | Prerendered, authorized |
| **Platform Admin** | `/platform`, `/platform/agents`, `/platform/analytics`, `/platform/api`, `/platform/audit`, `/platform/billing`, `/platform/decisions`, `/platform/governance`, `/platform/health`, `/platform/integrations`, `/platform/licenses`, `/platform/organizations`, `/platform/profile`, `/platform/reports`, `/platform/risk`, `/platform/security`, `/platform/settings`, `/platform/system`, `/platform/system-health`, `/platform/users` | Prerendered, SUPER_ADMIN edge protected |

### 9.2 Dead Controls & Functional Discrepancies
1. **Landing Page Enterprise Demo Form (`frontend/src/app/page.tsx:794`):**
   Submitting the demo modal executes:
   ```typescript
   onSubmit={(e) => {
     e.preventDefault();
     alert("Thank you! Your enterprise demo request has been received. Our team will contact you shortly.");
     setDemoModalOpen(false);
   }}
   ```
   No network request is dispatched, and no lead data is persisted.
2. **Platform Dashboard Export Button (`frontend/src/app/platform/page.tsx:150`):**
   `handleExportDashboard` executes `alert("Exporting Platform Control Center Overview report...");` without generating or downloading a report file.
3. **Platform Governance Policy Inspect (`frontend/src/app/platform/governance/page.tsx:151`):**
   Inspect button renders a browser alert dialog showing plain text rather than an inspection view or drawer.

---

## 10. Database, Concurrency & Data Integrity

### 10.1 Multi-Tenancy & Isolation
- Queries across agents, decisions, telemetry, audit logs, and webhooks consistently filter on `org_id == current_user.org_id`.
- Foreign keys cascade correctly on tenant removal (`cascade="all, delete-orphan"` on child relations).
- Database migrations define PostgreSQL Row-Level Security (RLS) policies in `backend/migrations/rls_tenant_policies.sql`.

### 10.2 Discovered Isolation Gaps
- **Organization Dashboard Pending Approvals Count (`backend/routers/organization.py:77`):**
  `pending_approvals = db.query(models.ApprovalRequest).count()` counts all approvals across all tenants.
  *Fix:* Change to `db.query(models.ApprovalRequest).join(models.Agent).filter(models.Agent.org_id == target_org_id).count()`.

---

## 11. Test Commands and Actual Results

### 11.1 Backend Test Execution
- **Command:** `pytest -q`
- **Working Directory:** `D:\AGENTGUARD\backend`
- **Exit Code:** `0`
- **Total Tests Collected:** 639
- **Passed:** 639
- **Failed:** 0
- **Skipped:** 0
- **Warnings:** 1 (`RequestsDependencyWarning: urllib3 (2.6.2) or chardet (7.4.3)/charset_normalizer (3.4.4) doesn't match a supported version!`)
- **Duration:** 116.11 seconds

### 11.2 TypeScript SDK Test Execution
- **Command:** `npm test`
- **Working Directory:** `D:\AGENTGUARD\sdks\typescript`
- **Exit Code:** `0`
- **Tests Executed:** 5 / 5 passed
- **Duration:** 1.8 seconds

### 11.3 Frontend Production Lint Execution
- **Command:** `npm run lint`
- **Working Directory:** `D:\AGENTGUARD\frontend`
- **Exit Code:** `0`
- **Errors:** 0
- **Warnings:** 7 (3 React Hook exhaustive-deps, 4 Next.js unoptimized `<img>` tags)
- **Duration:** 28.5 seconds

### 11.4 Frontend Production Build Execution
- **Command:** `npm run build`
- **Working Directory:** `D:\AGENTGUARD\frontend`
- **Exit Code:** `0`
- **Pages Prerendered:** 59 / 59 static routes
- **First Load JS (shared):** 87.3 kB
- **Middleware Size:** 27 kB
- **Duration:** 42.1 seconds

---

## 12. Complete Ranked Findings Matrix

| Finding ID | Severity | Category | Affected File(s) & Lines | Title & Summary | Confidence | Blocks Prod? |
|---|---|---|---|---|---|---|
| **SEC-01** | **High** | RBAC / Authorization | `routers/policies.py:81,159,213,243`<br>`routers/tools.py:20,113,158`<br>`routers/capabilities.py:23,70`<br>`routers/red_team.py:21,92`<br>`routers/agents.py:19,161`<br>`routers/billing.py:358` | Missing Route-Level RBAC on Sensitive Mutations | CONFIRMED | **YES** |
| **SEC-02** | **High** | SSRF / Network | `tasks/webhook_tasks.py:126`<br>`tasks/siem_tasks.py:155` | Secondary SSRF & DNS Rebinding in Async Workers | CONFIRMED | **YES** |
| **SEC-03** | **Medium** | Business Logic | `routers/approvals.py:39-76` | Approval Request Replay & Missing State Check | CODE-CONFIRMED | **YES** |
| **SEC-04** | **Low** | Tenant Isolation | `routers/organization.py:77` | Global Approval Count Disclosure in Dashboard | CONFIRMED | NO |
| **SEC-05** | **Low** | Architecture / Dependencies | `services/tool_proxy_service.py:165` | Private `_ssl_context` Access in `PinningTransport` (F-1) | CODE-CONFIRMED | NO |
| **UI-01** | **Medium** | Functional / UI | `app/page.tsx:794`<br>`app/platform/page.tsx:150`<br>`app/platform/governance/page.tsx:151` | Dead Buttons & Placeholder Alert Handlers | CONFIRMED | NO |
| **UI-02** | **Low** | Performance / Lint | `organization/page.tsx:162`<br>`components/ui/DashboardHeader.tsx:66` | Raw `<img>` Elements Instead of Next.js `<Image />` | CONFIRMED | NO |

---

## 13. Detailed Finding Descriptions

### SEC-01: Missing Route-Level RBAC on Sensitive Mutations
- **Severity:** High
- **Category:** Broken Object Level / Functional Access Control
- **File References:**
  - `backend/routers/policies.py` (lines 81, 159, 213, 243, 263, 298, 339)
  - `backend/routers/tools.py` (lines 20, 113, 158)
  - `backend/routers/capabilities.py` (lines 23, 70)
  - `backend/routers/red_team.py` (lines 21, 92)
  - `backend/routers/agents.py` (lines 19, 161)
  - `backend/routers/billing.py` (line 358)
- **Preconditions & Impact:**
  An authenticated attacker with a low-privilege role (`USER`, `VIEWER`, `AUDITOR`) can invoke policy, tool, capability, agent budget, and billing mutation endpoints directly via REST API calls. They can disable critical runtime policies, redirect tool endpoints, issue capability tokens with high limits, or upgrade subscription plans.
- **Reproduction Method:**
  Issue a `POST /api/v1/policies` request using a Bearer token belonging to a `VIEWER` or `USER` account. The server returns HTTP 201 Created and persists the policy.
- **Recommended Fix:**
  Add `require_permission(PERM_POLICY_CREATE)`, `require_permission(PERM_POLICY_UPDATE)`, `require_permission(PERM_POLICY_DELETE)` to `policies.py`; require `ADMIN` or `SECURITY_OFFICER` for tool registration and capability issuance; and restrict `billing/simulate-payment` to `ADMIN` or `SUPER_ADMIN`.
- **Blocks Production:** YES.

### SEC-02: Secondary SSRF & DNS Rebinding in Asynchronous Workers
- **Severity:** High
- **Category:** Server-Side Request Forgery (SSRF) / TOCTOU
- **File References:**
  - `backend/tasks/webhook_tasks.py` (line 126)
  - `backend/tasks/siem_tasks.py` (line 155)
- **Preconditions & Impact:**
  An organization administrator registers an outbound webhook URL pointing to a domain with a low DNS TTL under attacker control. When the worker validates the URL, DNS returns a benign public IP. When `requests.post()` connects moments later, DNS returns `169.254.169.254`. Furthermore, `requests.post()` automatically follows 3xx redirects to internal addresses.
- **Reproduction Method:**
  Register a webhook endpoint pointing to an HTTP server returning a `302 Found` redirect with `Location: http://169.254.169.254/latest/meta-data/`. Trigger an event and observe that `requests.post()` follows the redirect.
- **Recommended Fix:**
  Route outbound webhook and SIEM requests through `tool_proxy_service.py`'s `PinningTransport` or use `requests.post(..., allow_redirects=False)` with socket connection pinning.
- **Blocks Production:** YES.

### SEC-03: Approval Request Replay & Missing State Check
- **Severity:** Medium
- **Category:** Business Logic & State Integrity
- **File References:** `backend/routers/approvals.py` (lines 39–76)
- **Preconditions & Impact:**
  `act_on_approval` does not check `if app_req.status != "PENDING"`. A manager or admin can repeatedly submit approval/rejection requests for already resolved or expired approvals. Additionally, approving an approval immediately sets `dec.execution_status = "EXECUTED"` before the agent or proxy actually executes the action with the gate token.
- **Reproduction Method:**
  Submit `POST /api/v1/approvals/{id}/act` with `{"action": "APPROVE"}` twice on the same approval ID. Both requests succeed with HTTP 200.
- **Recommended Fix:**
  Add `if app_req.status != "PENDING": raise HTTPException(status_code=400, detail="Approval request has already been resolved or expired")`. Set decision status to `APPROVED_PENDING_EXECUTION` rather than `EXECUTED`.
- **Blocks Production:** YES.

### SEC-04: Global Approval Count Disclosure in Dashboard
- **Severity:** Low
- **Category:** Multi-Tenant Information Disclosure
- **File References:** `backend/routers/organization.py` (line 77)
- **Preconditions & Impact:**
  Line 77 executes `pending_approvals = db.query(models.ApprovalRequest).count()`. Any tenant administrator calling `GET /organization/dashboard` sees the global sum of all pending approvals across every tenant on the platform.
- **Recommended Fix:**
  Change line 77 to:
  ```python
  pending_approvals = db.query(models.ApprovalRequest).join(models.Agent).filter(models.Agent.org_id == target_org_id, models.ApprovalRequest.status == "PENDING").count()
  ```
- **Blocks Production:** NO.

### UI-01: Dead Buttons & Placeholder Alert Handlers
- **Severity:** Medium
- **Category:** Functional / UI Completeness
- **File References:**
  - `frontend/src/app/page.tsx` (line 794)
  - `frontend/src/app/platform/page.tsx` (line 150)
  - `frontend/src/app/platform/governance/page.tsx` (line 151)
- **Preconditions & Impact:**
  Prospective enterprise users submitting demo requests receive a browser alert without their inquiry reaching the sales or support team. Platform administrators clicking "Export Report" or "Inspect" on governance policies encounter browser alert dialogs rather than file downloads or detail views.
- **Recommended Fix:**
  Wire the landing demo form to a backend lead intake endpoint (or email webhook). Implement report export streaming in `handleExportDashboard`. Replace the policy inspect alert with an inspection modal.
- **Blocks Production:** NO (marketing/UX defect).

---

## 14. Prioritized Remediation Plan

### Phase 1: Critical Security Remediations (Immediate — Blocks Release)
1. **Enforce RBAC Dependencies:**
   - In `backend/routers/policies.py`, apply `require_permission(PERM_POLICY_CREATE)`, `PERM_POLICY_UPDATE`, `PERM_POLICY_DELETE`.
   - In `backend/routers/tools.py`, apply `require_permission(PERM_AGENT_UPDATE)` or `require_admin`.
   - In `backend/routers/capabilities.py`, apply `require_role(["ADMIN", "MANAGER", "SECURITY_OFFICER"])`.
   - In `backend/routers/agents.py`, apply `require_permission(PERM_AGENT_CREATE)` to `create_agent` and `PERM_AGENT_UPDATE` to `update_agent`.
   - In `backend/routers/billing.py`, restrict `simulate-payment` to `require_admin`.
2. **Harden Outbound Webhook & SIEM Workers against SSRF:**
   - Update `tasks/webhook_tasks.py` and `tasks/siem_tasks.py` to disable automatic redirects (`allow_redirects=False`).
   - Use pre-resolved IP connection pinning or dispatch via `ToolProxyService`'s pinning transport.
3. **Approval State Machine Hardening:**
   - Enforce `app_req.status == "PENDING"` before resolving approvals in `approvals.py`.
   - Transition decisions to `APPROVED` / `CLAIMABLE`, reserving `EXECUTED` for when the proxy consumes the gate token.

### Phase 2: Tenant Isolation & Operational Fixes (Pre-Production Polish)
1. **Scope Organization Dashboard Approvals:**
   - Join `models.Agent` and filter by `target_org_id` in `backend/routers/organization.py:77`.
2. **Wire Frontend Demo & Export Handlers:**
   - Connect `frontend/src/app/page.tsx` demo modal to a backend endpoint.
   - Connect platform overview export button to `GET /api/v1/reports/export/pdf`.
3. **Dependency Pinning:**
   - Pin `httpcore==1.0.5` and `httpx==0.27.0` in `backend/requirements.txt` to guard against breaking changes to private transport attributes.

---

## 15. Production Readiness Checklist

| Readiness Criteria | Status | Notes |
|---|---|---|
| **Cryptographic Agent Passports** | **PASSED** | Ed25519 signing, verification, and rotation verified. |
| **Runtime Gate Token Replay Protection** | **PASSED** | Single-use atomic consumption; 300s TTL enforced. |
| **Tool Proxy SSRF Defense & Pinning** | **PASSED** | Socket connection pinning and cloud metadata blocking verified. |
| **Human / Machine Token Separation** | **PASSED** | Machine tokens cannot access human user endpoints. |
| **At-Rest Secret Encryption** | **PASSED** | AES-256-GCM encryption with keyring migration fallback. |
| **Payment Gateway Webhook Signatures** | **PASSED** | Stripe and Razorpay HMAC verification verified. |
| **Tenant Database Isolation** | **CONDITIONAL** | Dashboard pending approvals count leaks cross-tenant volume. |
| **Route-Level RBAC Enforcement** | **FAILED** | Missing permission checks on policies, tools, and capabilities. |
| **Worker Outbound SSRF Hardening** | **FAILED** | Webhook & SIEM workers vulnerable to redirect / TOCTOU SSRF. |
| **Frontend Static Compilation** | **PASSED** | 59/59 routes prerendered without compilation errors. |
| **Automated Test Suite** | **PASSED** | 639/639 tests passed with 0 failures. |

---

## 16. Final Release Verdicts

### Domain-Specific Verdicts
- **Security Verdict:** **CONDITIONALLY READY** (Critical controls in runtime kernel and tool proxy are excellent; route-level RBAC and worker SSRF must be patched prior to public deployment).
- **Functional Correctness Verdict:** **READY** (Core governance, evaluation, decisions, audit logs, and passports are fully implemented).
- **UI/UX Completeness Verdict:** **CONDITIONALLY READY** (59 static routes functional; demo form and platform export button require backend wiring).
- **Reliability & Data Integrity Verdict:** **READY** (Atomic gate token consumption, database transactions, and rollback behavior verified).
- **Test Coverage Verdict:** **READY** (639 backend tests, 5 TypeScript SDK tests passing; 100% pass rate).
- **Production Readiness Verdict:** **NOT READY** (Blocked by SEC-01 and SEC-02).

### OVERALL SYSTEM VERDICT

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║     OVERALL VERDICT: NOT READY FOR CONTROLLED PRODUCTION USE              ║
║     STATUS: CONDITIONALLY READY FOR ISOLATED STAGING                     ║
║                                                                           ║
║  The AGENTGUARD runtime core, tool proxy, passport cryptography, and     ║
║  test suites demonstrate exceptional engineering rigor. However, the      ║
║  application cannot be released to production until the missing          ║
║  route-level RBAC checks (SEC-01), worker outbound SSRF risks (SEC-02),   ║
║  and approval state machine transition logic (SEC-03) are remediated.     ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
```
