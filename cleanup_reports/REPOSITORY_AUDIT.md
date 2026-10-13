# AGENTGUARD — Exhaustive Repository Audit and Security Baseline

> **Official Evidence-Based Repository Inventory, Architectural Audit & Security Baseline**  
> **Execution Date:** 2026-10-13  
> **Repository:** `https://github.com/bhataakib02/agentguard.git`  
> **Working Tree:** `d:\AGENTGUARD` (Branch: `main`, Clean, Aligned with `origin/main`)  
> **Status:** AUDIT COMPLETE — REMEDIATION IN PROGRESS  

---

## 1. Executive Summary

This exhaustive repository audit provides a comprehensive, evidence-based inventory and architectural evaluation of the AGENTGUARD codebase prior to security remediation. 

The investigation confirms that the core architectural foundations of AGENTGUARD are genuinely implemented, including:
- A 9-level hierarchical human IAM system (`SUPER_ADMIN` down to `USER`) and machine agent identity (`AGENT`).
- A 12-stage runtime authorization kernel with non-bypassable policy evaluation (REFUSE > REVIEW > ALLOW).
- Asymmetric Ed25519 digital signature signing for Agent Passports.
- Single-use execution gate tokens with forward tool execution proxying and SSRF protections.
- An extensive Next.js frontend with 24 tenant workspaces and 19 platform control plane pages.

However, verified critical security vulnerabilities exist that must be remediated immediately:
1. **Unauthenticated WebSocket Broadcast Endpoint (`/ws`):** Accepts connections without authentication, deriving tenant ID and role directly from untrusted query parameters, allowing cross-tenant event leakage and unauthorized platform broadcast access.
2. **Client-Side Privilege Escalation in Frontend Middleware:** Decodes unverified JWT tokens via base64, trusting user-editable `user_metadata.role` and hardcoding a personal email address (`thefreelancer2076@gmail.com`) for `SUPER_ADMIN` access.
3. **Machine JWT Revocation & Status Check Bypass:** `decode_and_verify_machine_jwt` validates token signatures but does not check if an agent has been suspended, if credentials have been revoked, or if the organization is active.
4. **Ephemeral Signing Key Generation in Production:** Process startup silently falls back to `secrets.token_hex(32)` if `SECRET_KEY` is not provided, causing Ed25519 passport root keys to mutate across restarts.
5. **Plaintext Webhook Secret Retention:** Webhook HMAC secrets are stored in plaintext in the database rather than encrypted at rest.
6. **Discrepancy Between Claimed 100% Checklist and Real External Infrastructure:** External sandbox (gVisor/Firecracker), SIEM forwarders, Redis, Celery, and SMTP are implemented with fallback/mock paths but are unconfigured or local by default.

---

## 2. Repository Structure & Component Inventory

### A. Top-Level Directory Layout
- `backend/`: FastAPI application, models, schemas, routers, engines, services, Celery tasks, and tests.
- `frontend/`: Next.js 14 App Router application, Tailwind CSS styles, components, and client libraries.
- `cleanup_reports/`: Audit summaries, deleted database record registers, pre-cleanup snapshot backups.
- `documents/`: Enterprise feature lists, UI design system specifications, and testing matrices.
- `sdks/`: Python SDK (`sdks/python`) and TypeScript SDK (`sdks/typescript`).
- `supabase/`: Migrations (`supabase/migrations/`) and SQL cleanup scripts.
- `scripts/`: Operational audit scripts (`scripts/audit_phase6c.py`).
- `AGENTGUARD_5_ORGANIZATIONS_DATASET/`: Canonical demo datasets for 5 enterprise organizations.
- Configuration & Deployment: `Dockerfile`, `docker-compose.yml`, `render.yaml`, `vercel.json`, `pyrightconfig.json`.

### B. Backend Component Breakdown (Python 3.10+)
- **API Routers (38 modules in `backend/routers/`):**
  - Identity & Access: `auth.py`, `profile.py`, `iam.py`, `permissions.py`, `capabilities.py`.
  - Machine Agents & Runtime: `agents.py`, `runtime.py`, `decisions.py`, `approvals.py`, `tools.py`.
  - Governance & Security: `policies.py`, `security.py`, `risk.py`, `behavior.py`, `trust.py`, `circuit_breaker` (engine).
  - SOC & Intelligence: `audit.py`, `provenance.py`, `red_team.py`, `digital_twin.py`, `ai.py`, `assistant.py`.
  - Platform & Multi-Tenancy: `platform.py`, `organization.py`, `admin.py`, `billing.py`, `reports.py`, `webhooks.py`, `telemetry.py`, `economics.py`, `impact.py`, `optimization.py`, `analytics.py`, `agent_network.py`, `developers.py`, `integrations.py`, `system.py`, `settings.py`, `notifications.py`.
- **Core Security Modules (`backend/core/`):**
  - `deps.py`: Core FastAPI dependencies (`get_current_user`, `get_current_machine_agent`, `require_permission`, `check_org_isolation`).
  - `permissions.py`: 9 human roles, permission constants, role permission matrix, role hierarchy levels.
  - `security.py`: Password hashing (bcrypt) and token helpers.
  - `supabase_admin.py`: Supabase Admin service-role client.
- **Services (`backend/services/`):**
  - `runtime_authorization_service.py`: 12-stage runtime evaluation kernel.
  - `passport_service.py`: Asymmetric Ed25519 digital signature signing and verification.
  - `machine_auth_service.py`: Machine credentials, hashing, rotation, and machine JWT lifecycle.
  - `tool_proxy_service.py`: Execution gate token validation, SSRF filtering, tool dispatch.
  - `sandbox_service.py`: Isolated container execution provider abstraction.
  - `siem_forwarder_service.py`: SIEM log formatting (CEF/JSONL) and batch forwarding.
  - `notification_service.py`: Webhook dispatch, HMAC signatures, in-app notifications.
  - `byok_service.py`: Tenant KMS BYOK abstraction.
  - `storage_service.py`: PDF/Excel report storage (Local vs S3).
  - `email_service.py`: Transactional email delivery (SMTP vs Mock).
  - `runtime_telemetry_service.py`: Token tracking, execution recording, budget accounting.
- **Engines (`backend/engines/`):**
  - `policy_engine.py`, `policy_evaluator.py`, `circuit_breaker.py`, `capability_engine.py`, `intent_engine.py`, `pii_engine.py`, `output_guardrails_engine.py`, `behavior_engine.py`, `risk_engine.py`, `red_team_engine.py`, `digital_twin_engine.py`, `assistant_engine.py`, `model_router.py`, `provenance_engine.py`.
- **Test Suites (`backend/tests/`):**
  - 36 test modules covering auth hardening, runtime security invariants, IAM role matrix, machine agent lifecycle, SIEM export, reports, sandbox, and penetration testing.

### C. Frontend Component Breakdown (Next.js 14)
- **App Router (`frontend/src/app/`):**
  - Public & Auth (`(auth)`): `/login`, `/register`, `/forgot-password`, `/verify-otp`.
  - Tenant Workspace (`(app)`): 24 operational sections including `/dashboard`, `/agents`, `/decisions`, `/policies`, `/approvals`, `/runtime`, `/audit`, `/reports`, `/iam`, `/activity`.
  - Platform Control Plane (`/platform`): 19 super-admin sections for global oversight, cross-tenant telemetry, and license provisioning.
- **Client Utilities (`frontend/src/lib/`):**
  - `api.ts`: Centralized fetch client (`fetchApi`) with automatic token injection and tenant context headers.
  - `useAuth.tsx`: React Auth context with Supabase auth session sync.
  - `permissions.ts`: Frontend role matrix mirrored from backend.
  - `middleware.ts`: Next.js Edge route guard.

---

## 3. Confirmed Findings & Vulnerabilities Ranked by Severity

| ID | Finding | Severity | Component | Root Cause |
|:---|:---|:---|:---|:---|
| **VULN-01** | Unauthenticated WebSocket Endpoint with Arbitrary Role Spoofing | **CRITICAL (P0)** | `backend/main.py`, `backend/ws_manager.py` | `/ws` accepts connections without checking credentials; query parameters `org_id` and `role` are trusted unconditionally. |
| **VULN-02** | Unverified JWT & Client-Side Privilege Escalation in Frontend Middleware | **CRITICAL (P0)** | `frontend/src/middleware.ts` | Edge middleware parses raw JWT via `atob()` without cryptographic verification; trusts `user_metadata.role` and hardcoded email `thefreelancer2076@gmail.com`. |
| **VULN-03** | Suspended Agent & Revoked Machine Credential Execution Bypass | **HIGH (P0/P1)** | `backend/services/machine_auth_service.py` | `decode_and_verify_machine_jwt` does not check `agent.status in ('SUSPENDED', 'CIRCUIT_BREAK')`, revoked credentials, or organization status. |
| **VULN-04** | Ephemeral Random Signing Keys on Startup Invalidates Tokens & Passports | **HIGH (P1)** | `backend/config.py`, `backend/services/passport_service.py` | If `SECRET_KEY` is not provided, config generates a random hex key on each process boot. Passport service derives Ed25519 root keys from `SECRET_KEY`, breaking previously signed passports across restarts. |
| **VULN-05** | Plaintext Webhook Signing Secrets Stored at Rest | **HIGH (P1)** | `backend/routers/webhooks.py`, `backend/models.py` | Webhook raw secret (`whsec_...`) is saved in cleartext in `webhook_endpoints.secret_key` rather than encrypted at rest with AES-GCM. |
| **VULN-06** | Hardcoded Super-Admin Email in Frontend Client Components | **MEDIUM (P1)** | `frontend/src/lib/useAuth.tsx`, `platform/layout.tsx`, `dashboard/page.tsx` | UI checks hardcoded email `thefreelancer2076@gmail.com` to grant client-side Super Admin display privileges instead of relying solely on server-authorized profile data. |
| **VULN-07** | Automatic DDL Migration on App Startup | **MEDIUM (P1)** | `backend/main.py`, `backend/bootstrap.py` | `bootstrap_database()` executes `Base.metadata.create_all()` and `ensure_schema_compatibility()` on every application boot, conflating runtime startup with schema migrations. |
| **VULN-08** | Disassociated Audit Log Historical Attribution Gap | **LOW (P2)** | `cleanup_reports/DELETED_DATABASE_RECORDS.md` | 80 historical audit records have `org_id = NULL` following deletion of synthetic demo organizations. Restoration is constrained by database foreign keys. |
| **VULN-09** | Discrepancy Between 100% Checklist Claims and Infrastructure Reality | **LOW (P2)** | `AGENTGUARD_MASTER_BUILD_CHECKLIST.md` | Checklist claims 100% completion across all milestones without distinguishing between fully configured production integrations and simulated/mock fallbacks (e.g. gVisor, Firecracker, Splunk HEC). |

---

## 4. Architectural Analysis by Domain

### A. Authentication & Tenant Isolation
- **Backend Flow:** Requests hit `core/deps.py` dependencies. `get_current_user` extracts Bearer JWT or API key. Local tokens are decoded with `settings.SECRET_KEY`; Supabase tokens are verified via in-memory cache, local secret, or Supabase Auth API endpoint.
- **Tenant Enforcement:** Application routes enforce `check_org_isolation(current_user, target_org_id)`. `SUPER_ADMIN` can switch context via `X-Organization-Context` header.
- **Vulnerability Found:** WebSocket endpoint `/ws` completely bypassed this flow.

### B. Machine Agent Identity & Execution Kernel
- **Machine Identity:** Agents authenticate via machine JWT (`token_type: "machine"`) or machine key (`ag_agent_...`).
- **Execution Pipeline (12 Stages):**
  1. Tenant Active Check
  2. Agent Status Check
  3. Cryptographic Ed25519 Passport Check
  4. Granted IAM Permissions Check
  5. One-Time Capability Token Check
  6. Prompt Injection & Tool Schema Check
  7. PII Guardrails Check
  8. FinOps Daily Budget Check
  9. Circuit Breaker Gate Check
  10. Behavioral Anomaly Heuristic Check
  11. Policy Engine Evaluation (REFUSE > REVIEW > ALLOW)
  12. Execution Gate Token Generation & Tool Proxy Dispatch

### C. Database & Tenancy Architecture
- 47 tables preserved from the 2026-10-11 cleanup baseline.
- Real production accounts: 10 genuine users, 2 genuine organizations (`Platform Admin Control`, `AgentGuard Enterprise Core`).
- 175 audit records preserved.

### D. External Integrations Status Matrix
| Integration | Implementation File | Status | Notes |
|:---|:---|:---|:---|
| **Supabase Auth** | `backend/core/deps.py`, `supabase_admin.py` | Configured / Operational | Real verification against Supabase API. |
| **PostgreSQL Database** | `backend/database.py` | Configured / Operational | Supabase pooler connection. |
| **Redis Pub/Sub** | `backend/ws_manager.py` | Implemented / Fallback Active | Single-node in-memory delivery when Redis absent. |
| **Celery Tasks** | `backend/celery_app.py` | Implemented / Eager Active | `CELERY_TASK_ALWAYS_EAGER=True` when Redis absent. |
| **Report Storage** | `backend/services/storage_service.py` | Implemented / Local Active | Saves to `storage/reports/` when S3 unconfigured. |
| **Email Delivery** | `backend/services/email_service.py` | Implemented / Mock Active | Returns simulation log when SMTP unconfigured. |
| **SIEM Log Forwarding**| `backend/services/siem_forwarder_service.py` | Implemented / Unconfigured | Formats CEF/JSONL; requires `SIEM_FORWARDER_URL`. |
| **Isolated Sandbox** | `backend/services/sandbox_service.py` | Implemented / Provider Configured | Reports `NOT_CONFIGURED` truthfully unless configured. |

---

## 5. Verification Commands & Test Coverage

- **Backend Pytest Suites:**
  - `python -m pytest backend/tests/test_iam_role_matrix.py` (4/4 passed)
  - `python -m pytest backend/tests/test_runtime_security_invariants.py` (13/13 passed)
- **Frontend Code Quality:**
  - `npm run lint` in `frontend/` (Clean: 0 errors, 4 non-critical `<img>` warnings)

---

## 6. Phase Execution & Remediation Roadmap

- **PHASE 1 (Immediate P0 Focus):**
  - Fix WebSocket authentication in `backend/main.py` and `backend/ws_manager.py` to authenticate via verifiable token, resolve database user profile, enforce tenant boundaries, and allow platform-wide streaming only for genuine `SUPER_ADMIN`.
  - Fix frontend `middleware.ts` to eliminate unverified JWT parsing and remove hardcoded email privilege escalation.
  - Fix machine JWT verification in `machine_auth_service.py` to check agent suspension, credential revocation, and org status.
  - Add comprehensive regression tests for cross-tenant WebSocket rejection, forged tokens, and suspended agents.
- **PHASE 2 (Keys & Startup Safety):**
  - Implement secure key provisioning failing closed in production; eliminate random key generation on boot.
  - Separate database DDL migrations from application startup.
- **PHASE 3 (Data Protection & Webhooks):**
  - Implement AES-GCM encryption-at-rest for webhook secrets.
- **PHASE 4 (Runtime & Tool Security):**
  - Audit all tool execution call sites to verify non-bypassability.
- **PHASE 5 & 6 (Living Checklist & Final Documentation):**
  - Update `AGENTGUARD_MASTER_BUILD_CHECKLIST.md` with truthful status labels.
