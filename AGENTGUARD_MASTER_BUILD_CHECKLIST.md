# AGENTGUARD MASTER BUILD CHECKLIST

> **Living Master Build Checklist & Engineering Roadmap**  
> **Repository:** `d:\AGENTGUARD`  
> **Authoritative Baseline:** Actual Source Code (Git HEAD)  
> **Notice:** This checklist is the single persistent, dependency-aware source of truth for all current and future implementation phases. It supersedes previous plans, audit notes, and speculative documentation.

---

## Project Status

```text
Last Updated: 2026-10-01
Current Phase: Phase 4 — Security Intelligence & AI Guardrails Complete
Current Milestone: Milestone 5 — Developer SDKs & External Integrations
Total Tracked Checkbox Items: 154
Completed: 71
Partial: 27
Foundation: 19
Simulated: 12
Demo: 6
Not Implemented: 19
Blocked: 0
Broken: 0
Overall Completion: 46.1% (71 / 154 genuinely complete items)
```

---

## 0. Repository Baseline

### Backend Architecture
- **Framework:** FastAPI (Python 3.10+) running with ASGI.
- **Entrypoints:** `backend/main.py` mounting 36 domain routers under `/api` and `/api/v1`.
- **Database Layer:** SQLAlchemy 2.0 ORM with PostgreSQL (Supabase pooler) as primary and SQLite as development fallback (`backend/database.py`).
- **Data Models:** Single unified `backend/models.py` (767 lines, 30+ relational entities).
- **Core Security & Auth:** `backend/core/deps.py`, `backend/core/security.py`, `backend/core/permissions.py`, `backend/core/supabase_admin.py`.
- **Asynchronous Execution:** Celery 5.x (`backend/celery_app.py`) backed by Redis (or in-memory eager fallback) with Celery Beat periodic schedules for report generation, approval escalation, and webhook retries.
- **Real-Time Streaming:** In-memory WebSocket manager (`backend/ws_manager.py`) with tenant and role-scoped broadcasting.
- **Reporting Engine:** Native streaming PDF via ReportLab, native multi-tab Excel via OpenPyXL, and CSV generation (`backend/routers/reports.py`).

### Frontend Architecture
- **Framework:** Next.js 14+ (App Router) with React 18 and TypeScript.
- **Styling:** Vanilla Tailwind CSS with custom enterprise design system (`#1F1F1F`, `#666666`, `#8064C8`, `#2E9D50`, `#E53935`).
- **Routing Structure:**
  - `(auth)`: Login, Register, Forgot Password, Reset Password, Invite Acceptance.
  - `(app)`: Tenant workspace covering 24 domains (Agents, Decisions, Policies, Approvals, Runtime, Telemetry, IAM, Security, Red Team, Digital Twin, Reports, Analytics).
  - `platform`: Super-Admin control plane covering multi-tenant management, license provisioning, cross-tenant audit, and system health.
- **State & Auth Management:** Supabase client (`frontend/src/lib/supabase.ts`), `AuthProvider` (`frontend/src/lib/useAuth.tsx`), Edge middleware (`frontend/src/middleware.ts`), and permission matrix (`frontend/src/lib/permissions.ts`).
- **API Client:** `frontend/src/lib/api.ts` with auto-injected JWT, tenant context header (`X-Organization-Context`), and robust reconnecting WebSocket client with ping/pong heartbeat.

### Database Architecture
- **Migrations:** Dual setup:
  - Supabase SQL migrations (`supabase/migrations/20260831000000_agentguard_schema.sql`).
  - Auto-bootstrapping ORM metadata (`Base.metadata.create_all`) via `backend/bootstrap.py` on startup.
- **Multi-Tenancy:** Schema-level tenancy enforced via mandatory foreign keys to `organizations(id)` across users, agents, policies, executions, security incidents, webhooks, and audit logs.
- **Row-Level Isolation:** Application-level tenant scoping in every router; optional PostgreSQL RLS policies in `backend/migrations/rls_tenant_policies.sql`.

### Infrastructure & Deployment
- **Containerization:** `Dockerfile` and `docker-compose.yml` defining `backend`, `celery_worker`, `celery_beat`, `redis`, and `frontend`.
- **Cloud Configurations:** `render.yaml` for backend + worker deployment; `vercel.json` for frontend deployment.
- **External Integrations:** S3/Local object storage abstraction (`storage_service.py`), SMTP/Mock email service (`email_service.py`), Supabase Admin Auth (`supabase_admin.py`).

### Major Source Files
- **Server Startup:** [`backend/main.py`](file:///d:/AGENTGUARD/backend/main.py)
- **Configuration:** [`backend/config.py`](file:///d:/AGENTGUARD/backend/config.py)
- **Database Engine:** [`backend/database.py`](file:///d:/AGENTGUARD/backend/database.py)
- **Relational Models:** [`backend/models.py`](file:///d:/AGENTGUARD/backend/models.py)
- **Schemas:** [`backend/schemas.py`](file:///d:/AGENTGUARD/backend/schemas.py)
- **Dependencies & Auth:** [`backend/core/deps.py`](file:///d:/AGENTGUARD/backend/core/deps.py)
- **RBAC Matrix:** [`backend/core/permissions.py`](file:///d:/AGENTGUARD/backend/core/permissions.py)
- **Supabase Admin:** [`backend/core/supabase_admin.py`](file:///d:/AGENTGUARD/backend/core/supabase_admin.py)
- **Policy Engine:** [`backend/engines/policy_engine.py`](file:///d:/AGENTGUARD/backend/engines/policy_engine.py)
- **Safe Condition Evaluator:** [`backend/engines/policy_evaluator.py`](file:///d:/AGENTGUARD/backend/engines/policy_evaluator.py)
- **Runtime Telemetry Service:** [`backend/services/runtime_telemetry_service.py`](file:///d:/AGENTGUARD/backend/services/runtime_telemetry_service.py)
- **Notification Service:** [`backend/services/notification_service.py`](file:///d:/AGENTGUARD/backend/services/notification_service.py)
- **Storage Service:** [`backend/services/storage_service.py`](file:///d:/AGENTGUARD/backend/services/storage_service.py)
- **Email Service:** [`backend/services/email_service.py`](file:///d:/AGENTGUARD/backend/services/email_service.py)
- **Celery App & Tasks:** [`backend/celery_app.py`](file:///d:/AGENTGUARD/backend/celery_app.py), `backend/tasks/`
- **Frontend Middleware:** [`frontend/src/middleware.ts`](file:///d:/AGENTGUARD/frontend/src/middleware.ts)
- **Frontend API Client:** [`frontend/src/lib/api.ts`](file:///d:/AGENTGUARD/frontend/src/lib/api.ts)
- **Frontend Auth Context:** [`frontend/src/lib/useAuth.tsx`](file:///d:/AGENTGUARD/frontend/src/lib/useAuth.tsx)

---

## PROTECTED / ALREADY BUILT COMPONENTS

*Components that are genuinely implemented, tested, and MUST NOT be rewritten or dismantled during future build phases:*

| Component | Status | Relevant Files | Reason to Preserve |
|---|---|---|---|
| **Human Authentication & Sessions** | COMPLETE | `backend/core/deps.py`, `backend/routers/auth.py`, `backend/core/security.py` | Handles local bcrypt and Supabase JWT verification, active session tracking, and revocation. |
| **Enterprise Human RBAC Matrix** | COMPLETE | `backend/core/permissions.py`, `backend/core/deps.py`, `frontend/src/lib/permissions.ts` | 9-level hierarchical role system (USER through SUPER_ADMIN) with fine-grained permission constants. |
| **Multi-Tenancy & Platform Licensing** | COMPLETE | `backend/routers/platform.py`, `backend/routers/organization.py`, `backend/models.py` | Enforces organization isolation, license quota checks (max users, max agents), plan limits, and super-admin controls. |
| **Database-Driven Policy Engine** | COMPLETE | `backend/engines/policy_engine.py`, `backend/engines/policy_evaluator.py`, `backend/routers/policies.py` | Tenant-scoped policy rules, AST-based safe evaluation without `eval()`, strict conflict resolution (REFUSE > REVIEW > ALLOW). |
| **Human Approval Workflow** | COMPLETE | `backend/routers/approvals.py`, `backend/tasks/escalation_tasks.py` | Role-gated approval resolution, execution status updating, and Celery periodic escalation. |
| **Enterprise Report Generation** | COMPLETE | `backend/routers/reports.py`, `backend/services/storage_service.py` | Real ReportLab PDF and OpenPyXL Excel rendering for 9 enterprise report types with local/S3 storage. |
| **Webhook Infrastructure** | COMPLETE | `backend/routers/webhooks.py`, `backend/services/notification_service.py`, `backend/tasks/webhook_tasks.py` | SSRF-validated endpoints, HMAC-SHA256 signing, async Celery dispatch, retry backoff, and dead-letter queue. |
| **Immutable Audit Logging** | COMPLETE | `backend/routers/audit.py`, `backend/models.py` | Append-only audit logs with HTTP 403 rejection on PUT, PATCH, and DELETE requests. |
| **Runtime Telemetry & Cost Accounting** | COMPLETE | `backend/services/runtime_telemetry_service.py`, `backend/routers/telemetry.py` | Execution tracking, token aggregation, model pricing calculations, budget limits, and risk signal detection. |
| **Security Operations Center (SOC)** | COMPLETE | `backend/routers/security.py`, `backend/models.py` | Incident tracking (OPEN to CLOSED), severity levels, timeline journaling, and agent linkage. |

---

## CURRENT GAPS

### P0 — Core Architecture Blockers (Must build before production agent deployment)
1. **Agent Authentication & Machine Credentials:** AI agents cannot authenticate themselves to AGENTGUARD. No machine token issuance, agent API keys, or machine authentication middleware exists.
2. **Cryptographic Agent Passport:** Passports currently store arbitrary dummy sha256 hashes without asymmetric keypairs, verifiable digital signatures, or runtime passport validation.
3. **Runtime Authorization Enforcement Gate:** Agent actions are evaluated passively via `/decisions/evaluate`, but agent permissions (`models.Permission`) and capability tokens (`models.CapabilityToken`) are completely bypassed during runtime evaluation.
4. **Agent Runtime Gateway API:** No dedicated machine-facing runtime endpoints exist (e.g. `/runtime/v1/auth`, `/runtime/v1/authorize`, `/runtime/v1/execute`, `/runtime/v1/heartbeat`).

### P1 — Important Product Gaps (Essential enterprise control plane features)
1. **Execution Control & Tool Proxy:** AGENTGUARD records decisions as EXECUTED or BLOCKED, but lacks an egress proxy or forward execution gateway that actually invokes downstream APIs or tools.
2. **Structured Intent & Parameter Extraction:** `intent_engine.py` relies on 4 simple regex keywords (`refund`, `transfer`, `delete`, `export`) rather than schema-based function call verification.
3. **AI Output Governance & Guardrails:** No automated PII redaction, prompt injection defense, or hallucination detection on inputs/outputs.
4. **Agent SDKs:** No client SDKs (Python SDK, TypeScript SDK, LangChain/CrewAI middleware) for developers to integrate agents with AGENTGUARD.

### P2 — Advanced Functionality
1. **Dynamic Risk Engine:** Transform the static risk formula into behavioral baselining based on historical execution telemetry and anomaly detection.
2. **Real Red-Team Fuzzing:** Upgrade from the 4 static synthetic scenarios to dynamic automated policy stress testing and jailbreak fuzzing.
3. **AI Admin Assistant LLM Integration:** Connect the keyword-matched assistant engine to a real LLM provider (OpenAI, Anthropic, or Gemini) using the configured provider keys.
4. **Dynamic Model Router:** Turn the static 3-model demo list into a real telemetry-driven router that selects models based on measured latency and pricing.

### P3 — Optional / Enterprise Enhancements
1. **Agent-to-Agent Delegation Protocol:** Enforce trust levels and delegation scopes between parent and child agents in multi-agent networks.
2. **Automated Budget Approval Workflows:** Enable dynamic budget increase requests with managerial approval workflows.
3. **External SIEM Integration:** Forward audit logs and security incidents directly to Splunk, Datadog, or AWS CloudWatch.

---

## PRODUCT CHECKLIST

### 1. Identity & Authentication

- [x] Human registration with duplicate email rejection  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/auth.py` (`register_organization`), `test_auth_suite.py`  
  *What currently works:* Registers user, binds to new organization, sets USER role, returns JWT.  
  *What is missing:* Email verification challenge prior to initial login.  
  *Dependencies:* Database session, `security.py`.  
  *Next action:* Add mandatory email verification requirement when email service is active.

- [x] Human login via Supabase JWT verification  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/auth.py` (`login`), `backend/core/deps.py` (`verify_supabase_token`)  
  *What currently works:* Decodes local JWT secret or authoritatively verifies token against Supabase Auth API with caching.  
  *What is missing:* None for human login.  
  *Dependencies:* Supabase URL/keys or local SECRET_KEY.

- [x] Fallback local password authentication  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/auth.py` (`local_login`), `test_auth_suite.py`  
  *What currently works:* Bcrypt password verification for seeded and offline users.

- [x] Session tracking and revocation  
  *Status:* COMPLETE  
  *Evidence:* `backend/models.py` (`Session`), `backend/routers/auth.py` (`logout`), `backend/core/deps.py`  
  *What currently works:* 24h sessions stored in DB; logout marks session revoked; revoking blocks further requests.

- [x] Cryptographic API key authentication for humans/developers  
  *Status:* COMPLETE  
  *Evidence:* `backend/models.py` (`ApiKey`), `backend/routers/iam.py` (`create_api_key`), `backend/core/deps.py`  
  *What currently works:* `ag_live_` keys generated with 24 bytes entropy, stored as SHA-256 hash, verified in `deps.py`.

- [x] AI Agent machine authentication endpoint  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/runtime.py` (`runtime_machine_auth`), `backend/services/machine_auth_service.py`, `backend/core/deps.py` (`get_current_machine_agent`), `tests/test_machine_identity_suite.py`  
  *What currently works:* POST `/api/runtime/auth` authenticates machine credentials (`ag_agent_...`), validates agent and organization status, and issues short-lived machine JWTs with full claims (`sub`, `agent_code`, `org_id`, `autonomy_level`, `token_type=machine`). Direct header authentication (`X-Agent-Code` + `X-Agent-Key`) is also supported.  
  *Dependencies:* `AgentCredential`, `MachineAuthService`, `deps.py`.

- [x] Agent credential generation & hashing  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/agents.py` (`create_agent_credential`, `rotate_agent_credential`, `revoke_agent_credential`, `list_agent_credentials`), `backend/models.py` (`AgentCredential`), `backend/services/machine_auth_service.py`, `tests/test_machine_identity_suite.py`  
  *What currently works:* Cryptographically secure 256-bit entropy credentials with `ag_agent_` prefix. Plaintext token returned ONLY ONCE upon creation/rotation. Stored strictly as SHA-256 hash. Rotation, revocation, expiration, and audit logging fully implemented and tested.  
  *Dependencies:* `Agent` model, `AgentCredential` model, `machine_auth_service.py`.

- [x] Agent session management & heartbeats  
  *Status:* COMPLETE  
  *Evidence:* `backend/models.py` (`AgentRuntimeSession`), `backend/routers/runtime.py` (`runtime_agent_heartbeat`), `tests/test_machine_identity_suite.py`  
  *What currently works:* Active runtime session tracking (`AgentRuntimeSession`) with JTI linkage and POST `/api/runtime/heartbeat` confirming liveness and updating session expiration.  
  *Dependencies:* `get_current_machine_agent`, `AgentRuntimeSession`.

---

### 2. Organizations & Multi-Tenancy

- [x] Multi-tenant organization isolation in database  
  *Status:* COMPLETE  
  *Evidence:* `backend/models.py`, `backend/core/deps.py` (`check_org_isolation`)  
  *What currently works:* Every core table has foreign key `org_id`; `check_org_isolation()` strictly rejects cross-tenant access.  
  *Dependencies:* PostgreSQL / SQLAlchemy.

- [x] Organization branding & workspace profile  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/organization.py`, `test_organization_branding_suite.py`  
  *What currently works:* Display name, custom domain, logo URL, and org initials.

- [x] User invitations with cryptographic single-use tokens  
  *Status:* COMPLETE  
  *Evidence:* `backend/models.py` (`UserInvitation`), `backend/routers/iam.py`, `backend/routers/auth.py`  
  *What currently works:* SHA-256 hashed invite tokens with expiry; `/auth/invitations/{token}/accept` provisions user.

- [x] Organization license quotas & enforcement  
  *Status:* COMPLETE  
  *Evidence:* `backend/core/deps.py` (`check_license_limit`), `backend/routers/platform.py`  
  *What currently works:* Blocks user and agent creation when tenant hits plan limit (FREE, STARTER, PRO, ENTERPRISE).

- [ ] Per-tenant custom encryption keys (BYOK)  
  *Status:* NOT_IMPLEMENTED  
  *Evidence:* `backend/models.py`  
  *What currently works:* System uses global SECRET_KEY.  
  *What is missing:* Organization-level KMS key configuration.

---

### 3. Human RBAC

- [x] Hierarchical human roles (9 levels)  
  *Status:* COMPLETE  
  *Evidence:* `backend/core/permissions.py` (`ROLE_LEVELS`), `test_iam_role_matrix.py`  
  *What currently works:* `USER (1)` through `SUPER_ADMIN (9)` with role management hierarchy (`can_manage_role`).

- [x] Centralized permission constants & role matrix  
  *Status:* COMPLETE  
  *Evidence:* `backend/core/permissions.py` (`ROLE_PERMISSIONS_MATRIX`), `test_phase5_enterprise_iam.py`  
  *What currently works:* Granular permissions (`AGENT_SUSPEND`, `POLICY_CREATE`, `DECISION_APPROVE`, etc.).

- [x] FastAPI route RBAC dependency enforcement  
  *Status:* COMPLETE  
  *Evidence:* `backend/core/deps.py` (`require_role`, `require_permission`, `require_admin`, `require_super_admin`)  
  *What currently works:* All sensitive endpoints are protected by RBAC dependencies.

- [x] Frontend route & navigation RBAC guard  
  *Status:* COMPLETE  
  *Evidence:* `frontend/src/middleware.ts`, `frontend/src/lib/permissions.ts`  
  *What currently works:* Next.js middleware guards `/platform` for SUPER_ADMIN; page components check permissions.

---

### 4. AI Agent Identity

- [x] Agent registration and profile management  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/agents.py`, `backend/models.py` (`Agent`), `test_identity_relationship_suite.py`  
  *What currently works:* Creates agent with unique code (`AG-xxx`), department, autonomy level, budget, and owner.

- [x] Agent status lifecycle state machine  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/agents.py` (`suspend_agent`, `restore_agent`)  
  *What currently works:* States: `NORMAL`, `WARNING`, `RESTRICTED`, `HUMAN_APPROVAL`, `CIRCUIT_BREAK`, `SUSPENDED`.

- [x] Agent ownership transfer with audit logging  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/agents.py` (`update_agent`), `test_identity_relationship_suite.py`  
  *What currently works:* Reassigns `owner_id` within same tenant; records `AGENT_OWNER_CHANGE` audit log.

- [x] Agent metadata signature & provenance stamping  
  *Status:* COMPLETE  
  *Evidence:* `backend/models.py` (`AgentPassport`), `backend/services/passport_service.py`, `tests/test_machine_identity_suite.py`  
  *What currently works:* Canonical passport payloads (agent identity, version, model, department, purpose, capabilities, validity) signed via platform root Ed25519 asymmetric cryptography. Tamper-evident and verifiable.

---

### 5. Agent Passport

- [x] Agent passport record creation  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/agents.py`, `backend/models.py` (`AgentPassport`), `backend/services/passport_service.py`  
  *What currently works:* Automatically creates and asymmetrically signs an Ed25519 passport row upon agent creation.

- [x] Passport inspection endpoint  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/agents.py` (`get_agent_passport`)  
  *What currently works:* Returns passport, owner name, organization name, permission count, and credential types.

- [x] Cryptographic passport signing (Asymmetric Ed25519/ECDSA)  
  *Status:* COMPLETE  
  *Evidence:* `backend/services/passport_service.py`, `backend/routers/agents.py` (`sign_agent_passport`, `verify_agent_passport`), `frontend/src/app/(app)/agents/passport/page.tsx`, `tests/test_machine_identity_suite.py`  
  *What currently works:* Root Ed25519 keypair loaded from environment or securely derived. `sign_passport()` generates digital signature; `verify_passport()` cryptographically validates signatures, expiration, and agent status. Endpoint GET `/api/agents/{id}/passport/verify` and interactive verification in the frontend UI are live.

- [x] Passport revocation & expiration verification gate  
  *Status:* COMPLETE  
  *Evidence:* `backend/services/runtime_authorization_service.py` (Stage 4), `backend/services/passport_service.py`, `backend/tests/test_runtime_authorization_suite.py`  
  *What currently works:* Runtime authorization kernel strictly verifies digital signature validity, expiration timestamp, and revocation state before evaluating any agent action. Refuses execution with structured `PASSPORT` stage failure reason upon tampered or expired passports.

---

### 6. Agent Permissions

- [x] Agent permission database model  
  *Status:* COMPLETE  
  *Evidence:* `backend/models.py` (`Permission`)  
  *What currently works:* Links agent to `resource_type`, `resource_name`, `action`, `is_allowed`.

- [x] Permission listing & matrix endpoints  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/permissions.py` (`list_permissions`, `get_permission_matrix`)  
  *What currently works:* Returns permissions per agent and tenant matrix.

- [x] Runtime permission enforcement gate  
  *Status:* COMPLETE  
  *Evidence:* `backend/services/runtime_authorization_service.py` (Stage 5), `backend/tests/test_runtime_authorization_suite.py`  
  *What currently works:* Stage 5 pre-flight enforcement verifies granted resource and action permissions for the agent. Supports fine-grained resource and action targeting as well as wildcard permissions (`*:*`). Denied actions immediately produce an audited `PERMISSION_DENIED` refusal.

- [x] Permission grant, update, and revoke API  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/permissions.py`, `backend/routers/agents.py`, `backend/tests/test_runtime_authorization_suite.py`  
  *What currently works:* Full tenant-isolated REST CRUD endpoints: `POST /permissions`, `GET /permissions`, `DELETE /permissions/{id}`, `GET /agents/{id}/permissions`, `POST /agents/{id}/permissions`, `DELETE /agents/{id}/permissions/{permission_id}` with persistent audit logging (`PERMISSION_GRANTED`, `PERMISSION_REVOKED`).

---

### 7. Capability System

- [x] Capability token database schema  
  *Status:* COMPLETE  
  *Evidence:* `backend/models.py` (`CapabilityToken`)  
  *What currently works:* Stores `token_code`, `agent_id`, `capability_name`, `scope`, `amount_limit`, `expires_at`, `status`.

- [x] Capability token issuance & revocation API  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/capabilities.py`, `backend/engines/capability_engine.py`  
  *What currently works:* Issues `tok_...` code with TTL; revokes token; broadcasts WebSocket event.

- [x] Runtime capability token enforcement gate  
  *Status:* COMPLETE  
  *Evidence:* `backend/services/runtime_authorization_service.py` (Stage 6), `backend/engines/capability_engine.py` (`validate_token`), `backend/tests/test_runtime_authorization_suite.py`  
  *What currently works:* Stage 6 pre-flight validation checks token presence, matching agent ownership, validity period/expiration, scope conformance, and amount ceiling before granting execution authorization.

- [x] Single-use token consumption & replay protection  
  *Status:* COMPLETE  
  *Evidence:* `backend/engines/capability_engine.py` (`consume_token`), `backend/services/runtime_authorization_service.py`, `backend/tests/test_runtime_authorization_suite.py`  
  *What currently works:* Consuming token on authorization transitions state from `ACTIVE` to `USED`. Subsequent attempts with the same token are strictly rejected to prevent replay attacks.

---

### 8. Intent & Action Understanding

- [x] Intent extraction engine  
  *Status:* COMPLETE  
  *Evidence:* `backend/engines/intent_engine.py`, `backend/routers/runtime.py` (`POST /api/runtime/validate-intent`), `backend/tests/test_tool_proxy_suite.py`  
  *What currently works:* Unified intent extraction blending structured function call parsing (OpenAI/Anthropic tool call formats, generic formats) with heuristic regex extraction (`REFUND`, `PAYMENT`, `DATA_DELETION`, `DATA_EXPORT`), extraction of entity IDs and financial limits, parameter validation, and prompt injection screening.

- [x] Function call parameter validation & schema matching  
  *Status:* COMPLETE  
  *Evidence:* `backend/engines/intent_engine.py` (`validate_parameters`), `backend/models.py` (`Tool.schema_definition`), `backend/services/runtime_authorization_service.py` (Stage 6.5), `backend/tests/test_tool_proxy_suite.py`  
  *What currently works:* Deep validation of agent tool parameters against target tool JSON Schema / OpenAPI specifications. Enforces required fields, primitive types (`string`, `integer`, `number`, `boolean`, `array`, `object`), numeric ranges (`minimum`, `maximum`), allowed values (`enum`), string boundaries (`minLength`, `maxLength`), and regex pattern matching. Integrated into Stage 6.5 of the runtime kernel to reject invalid payloads prior to authorization.

- [x] Prompt injection & jailbreak detection on agent intents  
  *Status:* COMPLETE  
  *Evidence:* `backend/engines/intent_engine.py` (`detect_prompt_injection`), `backend/services/runtime_authorization_service.py` (Stage 6.5), `backend/tests/test_tool_proxy_suite.py`  
  *What currently works:* Multi-pattern heuristic detection battery analyzing prompt text and tool arguments. Detects instruction override attempts (`ignore previous instructions`, `disregard safety guidelines`), jailbreak/developer modes (`DAN mode`, `developer mode enabled`), prompt delimiter escapes (`---BEGIN SYSTEM PROMPT---`, `<|im_start|>`), roleplay privilege escalations (`pretend you are root / unrestricted`), and system prompt exfiltration probes. Blocks malicious intents in Stage 6.5 of the runtime authorization kernel.

---

### 9. Context Engine

- [x] Context assembly for policy evaluation  
  *Status:* PARTIAL  
  *Evidence:* `backend/engines/policy_engine.py` (lines 59-73)  
  *What currently works:* Constructs dictionary of `amount`, `risk_score`, `action`, `resource`, `agent_status`, `agent_autonomy`, `user_role`.  
  *What is missing:* Environmental context (time-of-day, operating hours compliance, IP origin, cumulative velocity).

- [x] Operating hours & geographic context enforcement  
  *Status:* COMPLETE  
  *Evidence:* `backend/engines/behavior_engine.py` (`is_within_operating_hours`), `backend/models.py` (`BehaviorProfile.normal_operating_hours`), `backend/services/runtime_authorization_service.py` (Stage 8.5), `backend/tests/test_ai_guardrails_suite.py`  
  *What currently works:* Parses agent's configured operating hours window (e.g. `09:00 - 18:00`), evaluates current execution timestamp against active window, flags `OFF_HOURS_ACTIVITY` anomaly deviation if invoked outside hours, and incorporates deviation into runtime risk calculation.

---

### 10. Risk Engine

- [x] Deterministic risk calculation formula  
  *Status:* COMPLETE  
  *Evidence:* `backend/engines/risk_engine.py`, `backend/routers/decisions.py`  
  *What currently works:* Combines identity risk, permission risk, financial risk, behavior risk, and data sensitivity risk into [0, 100] score with levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).

- [x] Risk trend analytics  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/risk.py` (`get_risk_trends`), `test_phase2_policy_engine.py`  
  *What currently works:* Returns daily buckets of high-risk actions, average score, and refused action rates for 7 days.

- [x] Real behavioral anomaly detection for risk scoring  
  *Status:* COMPLETE  
  *Evidence:* `backend/engines/behavior_engine.py` (`evaluate_behavior`), `backend/models.py` (`BehaviorProfile`, `AnomalyEvent`, `RuntimeRiskSignal`), `backend/routers/behavior.py`, `backend/services/runtime_authorization_service.py` (Stage 8.5), `backend/tests/test_ai_guardrails_suite.py`  
  *What currently works:* Real-time statistical anomaly engine comparing live 24h invocation velocity against `BehaviorProfile.avg_daily_actions`, monitoring baseline spending spikes, detecting unauthorized tool invocations (`allowed_tools_json`), recording persistent `AnomalyEvent` records, generating `RuntimeRiskSignal` events, and dynamically feeding the calculated `deviation_score` directly into `risk_engine.calculate_risk(behavior_deviation=...)`.

---

### 11. Policy Engine

- [x] Tenant-isolated database policy management  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/policies.py`, `backend/models.py` (`Policy`, `PolicyRule`), `test_phase2_policy_engine.py`  
  *What currently works:* CRUD for policies and policy rules with priority ordering and status toggles.

- [x] AST-based safe rule condition evaluator  
  *Status:* COMPLETE  
  *Evidence:* `backend/engines/policy_evaluator.py`, `test_phase2_policy_engine.py`  
  *What currently works:* Parses expressions using Python `ast` with strict allowlist (no `eval`); evaluates comparisons, boolean operators, and memberships.

- [x] Deterministic priority & conflict resolution  
  *Status:* COMPLETE  
  *Evidence:* `backend/engines/policy_engine.py` (lines 147-180), `test_phase2_policy_engine.py`  
  *What currently works:* Resolves conflicting rule outputs using strict enterprise precedence: `REFUSE > REVIEW > ALLOW`.

- [x] Hard circuit-breaker guard  
  *Status:* COMPLETE  
  *Evidence:* `backend/engines/policy_engine.py` (lines 43-56)  
  *What currently works:* Automatically REFUSES any action from an agent whose status is `SUSPENDED` or `CIRCUIT_BREAK`.

---

### 12. Approval Engine

- [x] Approval request creation upon REVIEW decision  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/decisions.py` (lines 170-184), `backend/models.py` (`ApprovalRequest`)  
  *What currently works:* Automatically creates `ApprovalRequest` with status `PENDING` when policy evaluates to `REVIEW`.

- [x] Role-gated human resolution (Approve / Reject)  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/approvals.py` (`act_on_approval`), `test_phase2_policy_engine.py`  
  *What currently works:* Restricts resolution to `MANAGER`, `ADMIN`, or `SUPER_ADMIN`; updates decision `execution_status` to `EXECUTED` or `BLOCKED`.

- [x] Real-time WebSocket broadcasting of approval status  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/approvals.py` (lines 71-77), `backend/ws_manager.py`  
  *What currently works:* Broadcasts `APPROVAL_RESOLVED` event over WebSockets to all tenant subscribers.

- [x] Asynchronous escalation of overdue approvals  
  *Status:* COMPLETE  
  *Evidence:* `backend/tasks/escalation_tasks.py`, `backend/celery_app.py`  
  *What currently works:* Celery Beat task identifies approvals pending over 24 hours and flags them.

---

### 13. Runtime Enforcement Kernel

- [x] Decision evaluation pipeline  
  *Status:* PARTIAL  
  *Evidence:* `backend/routers/decisions.py` (`evaluate_decision`)  
  *What currently works:* Coordinates Intent -> Budget Check -> Risk Calculation -> Policy Engine -> Decision Record -> Telemetry -> Audit.  
  *What is missing:* Does not enforce Agent Authentication, Agent Passport, Agent Permissions, or Capability Tokens.

### 13. Runtime Enforcement Kernel

- [x] Decision evaluation pipeline  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/decisions.py` (`evaluate_decision`), `backend/services/runtime_authorization_service.py`  
  *What currently works:* Coordinates Intent -> Budget Check -> Risk Calculation -> Policy Engine -> Decision Record -> Telemetry -> Audit.

- [x] Unified Runtime Gate (Pre-flight interceptor)  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/runtime.py` (`runtime_authorize_action`), `backend/services/runtime_authorization_service.py`, `backend/tests/test_runtime_authorization_suite.py`  
  *What currently works:* Canonical 12-stage non-bypassable pre-flight evaluation: Machine Auth -> Tenant Isolation -> Agent Lifecycle Status -> Cryptographic Passport Verification -> Resource Permission Check -> Dynamic Capability Token Verification -> FinOps Budget Governance -> Circuit Breaker Safety Check -> Policy Rules Evaluation -> Human Approval Escalation -> Decision Provenance -> Immutable Audit Logging.

- [x] Automatic circuit breaker state tripping  
  *Status:* COMPLETE  
  *Evidence:* `backend/engines/circuit_breaker.py`, `backend/routers/runtime.py` (`reset_circuit_breaker`), `backend/tests/test_runtime_authorization_suite.py`  
  *What currently works:* Automatic tripping to `CIRCUIT_BREAK` state when consecutive policy refusals reach threshold (`MAX_CONSECUTIVE_REFUSALS=3`). Blocks all subsequent executions across the runtime kernel. Provides authorized operator reset endpoint `POST /api/runtime/circuit-breakers/{id}/reset` with audit logging and WebSocket notification.

---

### 14. Agent Runtime API

- [x] Standalone agent invocation endpoint (`/runtime/authorize`)  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/runtime.py` (`runtime_authorize_action`), `backend/tests/test_runtime_authorization_suite.py`  
  *What currently works:* Machine-authenticated endpoint accepting machine JWT or `X-Agent-Key` header, validating correlation parameters, executing pre-flight gate, generating single-use execution gate tokens (`gate_...`), and returning structured authorization response.

- [x] Machine capability validation endpoint (`/capabilities/validate`)  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/capabilities.py` (`validate_capability_token_endpoint`), `backend/engines/capability_engine.py`, `backend/tests/test_runtime_authorization_suite.py`  
  *What currently works:* Standalone validation checking token code, agent identity matching, expiration timestamp, scope matching, and amount limits.

- [x] Agent runtime heartbeat & liveness API (`/runtime/heartbeat`)  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/runtime.py` (`runtime_agent_heartbeat`), `backend/models.py` (`AgentRuntimeSession`), `backend/tests/test_machine_identity_suite.py`  
  *What currently works:* POST `/api/runtime/heartbeat` keeps machine runtime session alive, updates session expiration timestamp, and confirms agent status.

---

### 15. Execution Control

- [x] Execution status state management  
  *Status:* COMPLETE  
  *Evidence:* `backend/models.py` (`Decision.execution_status`)  
  *What currently works:* Tracks `EXECUTED`, `BLOCKED`, and `PENDING_APPROVAL`.

- [x] Downstream API / Tool execution gateway  
  *Status:* COMPLETE  
  *Evidence:* `backend/services/tool_proxy_service.py`, `backend/routers/tools.py`, `backend/routers/runtime.py` (`POST /api/runtime/execute`, `POST /api/runtime/invoke`), `backend/tests/test_tool_proxy_suite.py`  
  *What currently works:* Forward tool proxy gateway that securely dispatches approved agent actions to downstream APIs. Enforces single-use gate token validation (`execution_gate_token`), token TTL (300s), agent correlation, strict anti-replay protection (marks `gate_token_used = True`), and comprehensive SSRF defense (blocking loopback `127.0.0.1`, link-local `169.254.x.x`, and cloud metadata `169.254.169.254`). Dispatches HTTP requests with headers and timeout, records execution latency, and records execution telemetry and provenance events.

---

### 16. Telemetry

- [x] Agent execution tracking & metrics  
  *Status:* COMPLETE  
  *Evidence:* `backend/models.py` (`AgentExecution`), `backend/services/runtime_telemetry_service.py` (`record_execution`), `test_phase4_runtime_security.py`  
  *What currently works:* Records execution ID, action, resource, outcome, tokens, cost, provider, latency ms, and timestamp.

- [x] Execution listing and filtering API  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/telemetry.py` (`list_executions`)  
  *What currently works:* Filter by agent, time range (24h, 7d, 30d, 90d), tenant-scoped.

- [x] Automated runtime risk signal detection  
  *Status:* COMPLETE  
  *Evidence:* `backend/services/runtime_telemetry_service.py` (`detect_risk_signals`), `models.py` (`RuntimeRiskSignal`)  
  *What currently works:* Derives signals for repeated refusals, high risk volume, and budget cap exhaustion.

---

### 17. FinOps & Cost Governance

- [x] Configurable model pricing catalog  
  *Status:* COMPLETE  
  *Evidence:* `backend/models.py` (`ModelPricing`), `backend/services/runtime_telemetry_service.py` (`calculate_cost`)  
  *What currently works:* Deterministic cost calculation per 1K input/output tokens based on active provider/model pricing rows.

- [x] Agent & organization budget limits and pre-checks  
  *Status:* COMPLETE  
  *Evidence:* `backend/models.py` (`AgentBudgetConfig`), `backend/services/runtime_telemetry_service.py` (`check_budget_before_execution`)  
  *What currently works:* Pre-check blocks action with REFUSE decision if daily or monthly cost/token limit is exceeded.

- [x] Token & cost analytics endpoints  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/telemetry.py` (`get_token_usage`, `get_cost_analytics`)  
  *What currently works:* Returns aggregated token and dollar spend grouped by provider, model, and day.

- [x] Cost optimization recommendation engine  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/optimization.py`, `test_phase6c_truthfulness.py`  
  *What currently works:* Recommends cheaper models when appropriate; truthfully reports "INSUFFICIENT DATA" when sample size < 5.

---

### 18. Audit & Provenance

- [x] Immutable append-only audit logging  
  *Status:* COMPLETE  
  *Evidence:* `backend/models.py` (`AuditLog`), `backend/routers/audit.py`, `test_phase6f_production_hardening.py`  
  *What currently works:* Logs actor, action, resource, result, metadata; explicitly rejects PUT/PATCH/DELETE with HTTP 403.

- [x] Causal provenance graph reconstruction  
  *Status:* COMPLETE  
  *Evidence:* `backend/engines/provenance_engine.py`, `backend/models.py` (`ProvenanceEvent`), `backend/routers/provenance.py`  
  *What currently works:* Builds causal chain from human initiator to agent, policy rule matched, decision, and outcome.

- [x] Audit log export  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/reports.py` (lines 45-54)  
  *What currently works:* Exportable as CSV, Excel, and PDF via the Report Center.

---

### 19. Security Operations

- [x] Security Incident Management (SOC)  
  *Status:* COMPLETE  
  *Evidence:* `backend/models.py` (`SecurityIncident`), `backend/routers/security.py`, `test_phase6f_production_hardening.py`  
  *What currently works:* Incident creation, severity tracking (CRITICAL to INFO), status workflow (OPEN to CLOSED), timeline journaling.

- [x] Incident resolution & assignment  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/security.py` (`update_incident`)  
  *What currently works:* Assign to security analyst, record resolution notes, record resolved_at timestamp.

---

### 20. Red Team

- [x] Red Team test harness  
  *Status:* SIMULATED  
  *Evidence:* `backend/engines/red_team_engine.py`, `backend/routers/red_team.py`, `backend/models.py` (`SecurityTest`)  
  *What currently works:* Evaluates 4 synthetic adversarial scenarios against the real PolicyEngine; records pass/fail score.  
  *What is missing:* Real penetration testing, live network port scans, or automated external exploit payloads (intentionally simulated to protect production infrastructure).

- [x] Automated adversarial prompt fuzzer  
  *Status:* COMPLETE  
  *Evidence:* `backend/engines/red_team_engine.py` (`fuzz_agent_policy`), `backend/routers/red_team.py` (`POST /api/red-team/fuzz`), `backend/tests/test_ai_guardrails_suite.py`  
  *What currently works:* Dynamic adversarial fuzzing engine supporting parameter mutation techniques (Base64 encoding evasion, Delimiter injection `<|im_start|>`, Roleplay framing, Leetspeak, Instruction override), threshold boundary abuse testing, PII exfiltration fuzzing, automated resilience scoring, and actionable remediation generation.

---

### 21. Digital Twin

- [x] Deterministic scenario stress simulation  
  *Status:* SIMULATED  
  *Evidence:* `backend/engines/digital_twin_engine.py`, `backend/routers/digital_twin.py`, `backend/models.py` (`Simulation`)  
  *What currently works:* Models stress scenarios (volume spikes, latency strain, error injection) grounded in historical execution telemetry baseline.  
  *What is missing:* Dynamic sandboxed agent execution or code containerization.

---

### 22. AI / Model Governance

- [x] AI Model catalog endpoint  
  *Status:* DEMO  
  *Evidence:* `backend/routers/ai.py`, `backend/engines/model_router.py`  
  *What currently works:* Returns hardcoded static list of 3 models (`gpt-4o`, `claude-3-5-sonnet`, `gemini-1.5-pro`).  
  *What is missing:* Database-backed model registry, dynamic benchmark evaluation, provider health checks.  
  *Dependencies:* `models.AiModel` exists in `models.py` but is not queried by `routers/ai.py`.  
  *Next action:* Connect `routers/ai.py` to query `models.AiModel` and `models.ModelPricing` from database.

---

### 23. AI Output Governance

- [x] PII redaction on inputs & outputs  
  *Status:* COMPLETE  
  *Evidence:* `backend/engines/pii_engine.py`, `backend/services/runtime_authorization_service.py` (Stage 6.6), `backend/services/tool_proxy_service.py`, `backend/routers/runtime.py` (`POST /api/runtime/scan-pii`), `backend/tests/test_ai_guardrails_suite.py`  
  *What currently works:* High-precision pattern detection for SSNs (synthetic and standard), payment card numbers (with Luhn checksum validation), emails, phone numbers, API keys / secrets (OpenAI, AWS, AgentGuard, Bearer), JWTs, and IPv4 addresses. Supports multiple remediation modes (`MASK`, `PARTIAL_MASK`, `TOKENIZE`, `BLOCK`). Sanitizes inputs prior to tool proxy dispatch and sanitizes outbound response payloads to prevent data exfiltration. Dedicated `/api/runtime/scan-pii` diagnostics endpoint live.

- [x] Output toxicity & hallucination filter  
  *Status:* COMPLETE  
  *Evidence:* `backend/engines/output_guardrails_engine.py`, `backend/routers/runtime.py` (`POST /api/runtime/scan-output`), `backend/services/tool_proxy_service.py`, `sdks/python/agentguard/client.py` (`scan_output`), `tests/test_output_guardrails_suite.py` (10/10 tests passed)  
  *What currently works:* Evaluates model and tool outputs against multi-vector safety criteria: toxicity, hate speech, threats, harassment, and dangerous instructions (with configurable policy modes: `ALLOW`, `WARN`, `REDACT`, `BLOCK`). Detects factual contradictions, ungrounded numeric values, and speculative certainty markers against reference context. Integrated directly into the Egress Tool Proxy response flow, exposed via machine- and user-authenticated `POST /api/runtime/scan-output` endpoint with persistent audit logging (`OUTPUT_GUARDRAIL_BLOCKED`), and accessible through Python SDK `client.scan_output()`.

---

### 24. AI Admin Assistant

- [x] Assistant query engine  
  *Status:* SIMULATED  
  *Evidence:* `backend/engines/assistant_engine.py`, `backend/routers/assistant.py`  
  *What currently works:* Keyword matching on "suspicious", "blocked", "cost", "compliance" that queries real DB records and returns structured summaries.  
  *What is missing:* Real LLM chat integration with tool-calling capabilities.

---

### 25. Notifications

- [x] In-app notification creation & persistence  
  *Status:* COMPLETE  
  *Evidence:* `backend/models.py` (`Notification`), `backend/services/notification_service.py`  
  *What currently works:* Creates alerts for approval requests, policy refusals, and high-risk flags.

- [x] Notification listing & mark-read API  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/notifications.py`  
  *What currently works:* Lists unread notifications, marks read, tenant-scoped.

- [x] Transactional email delivery service  
  *Status:* COMPLETE  
  *Evidence:* `backend/services/email_service.py`, `test_phase6d_infrastructure.py`  
  *What currently works:* Supports SMTP with TLS, MOCK provider for tests, and truthful "NOT_CONFIGURED" status when credentials are missing.

---

### 26. Webhooks

- [x] Webhook endpoint registration & secret generation  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/webhooks.py`, `backend/models.py` (`WebhookEndpoint`), `test_phase6d_infrastructure.py`  
  *What currently works:* Generates `whsec_...` signing secrets, stores SHA-256 hash, masks secret preview.

- [x] Server-Side Request Forgery (SSRF) protection  
  *Status:* COMPLETE  
  *Evidence:* `backend/services/notification_service.py` (`validate_webhook_url`), `test_phase6d_infrastructure.py`  
  *What currently works:* Blocks loopback (`127.0.0.1`), private RFC1918 IPs, link-local, and cloud metadata (`169.254.169.254`).

- [x] HMAC-SHA256 signature generation  
  *Status:* COMPLETE  
  *Evidence:* `backend/services/notification_service.py`, `test_phase6d_infrastructure.py`  
  *What currently works:* Signs payload with `X-AgentGuard-Signature: sha256=<digest>` and timestamp header.

- [x] Asynchronous Celery dispatch, retry backoff & DLQ  
  *Status:* COMPLETE  
  *Evidence:* `backend/tasks/webhook_tasks.py`, `backend/models.py` (`WebhookDelivery`), `test_phase6d_infrastructure.py`  
  *What currently works:* Dispatches delivery asynchronously; exponential backoff on failure; transitions to `DEAD_LETTER` after 3 retries.

---

### 27. Reporting

- [x] Multi-format report generation (PDF, Excel, CSV)  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/reports.py`, `test_enterprise_report_center_suite.py`  
  *What currently works:* ReportLab PDF and OpenPyXL Excel rendering for 9 enterprise report categories.

- [x] Tenant-isolated report storage abstraction  
  *Status:* COMPLETE  
  *Evidence:* `backend/services/storage_service.py`, `test_phase6d_infrastructure.py`  
  *What currently works:* Local filesystem fallback with tenant subdirectories; S3/MinIO client ready when env vars supplied.

- [x] Report scheduling & automated execution  
  *Status:* COMPLETE  
  *Evidence:* `backend/tasks/report_tasks.py`, `backend/celery_app.py`  
  *What currently works:* Celery Beat periodic task checks scheduled reports every 15 minutes and generates files.

---

### 28. Analytics

- [x] Tenant-isolated analytics aggregation  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/analytics.py` (`get_analytics_overview`), `test_phase3_analytics_reporting.py`  
  *What currently works:* Aggregates total agents, decision volume, refusal rate, approval counts, and high-risk flags from DB.

- [x] Observed governance impact metrics  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/impact.py`, `test_phase6c_truthfulness.py`  
  *What currently works:* Aggregates real prevented financial exposure and refusal rates; never fabricates amounts.

---

### 29. Super Admin / Platform

- [x] Cross-tenant organization management  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/platform.py`, `test_platform_super_admin_license_suite.py`  
  *What currently works:* Create, update, suspend, and deactivate organizations; Super Admin exclusion from regular tenant lists.

- [x] Canonical subscription plan & license provisioning  
  *Status:* COMPLETE  
  *Evidence:* `backend/bootstrap.py` (`CANONICAL_PLANS`), `backend/routers/platform.py`  
  *What currently works:* Plans: FREE, STARTER, PROFESSIONAL, ENTERPRISE; license creation, extension, renewal, and revocation.

- [x] Impersonation & organization context switching  
  *Status:* COMPLETE  
  *Evidence:* `backend/core/deps.py` (`get_effective_org_id`), `frontend/src/lib/api.ts`  
  *What currently works:* Super Admin sends `X-Organization-Context` header to view any tenant workspace.

- [x] Subsystem health inspection  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/system.py` (`get_system_health`), `test_phase6c_truthfulness.py`  
  *What currently works:* Real round-trip DB latency check, Celery broker status, storage status, email status.

---

### 30. Billing

- [x] Canonical license tier definitions  
  *Status:* COMPLETE  
  *Evidence:* `backend/bootstrap.py` (`CANONICAL_PLANS`), `backend/models.py` (`Plan`, `License`)  
  *What currently works:* Monthly price, user quota, agent quota, API key quota, monthly request quota.

- [ ] Payment gateway integration (Stripe / Razorpay)  
  *Status:* NOT_IMPLEMENTED  
  *Evidence:* `backend/routers/integrations.py`  
  *What currently works:* Truthfully reports `NOT_CONFIGURED`.  
  *What is missing:* Stripe webhooks, checkout sessions, automatic license renewal on charge.

---

### 31. External Storage

- [x] Local report storage provider  
  *Status:* COMPLETE  
  *Evidence:* `backend/services/storage_service.py`  
  *What currently works:* Creates tenant directories under `backend/storage/reports/<org_id>/`.

- [x] S3-compatible cloud object storage integration  
  *Status:* COMPLETE  
  *Evidence:* `backend/services/storage_service.py`  
  *What currently works:* Boto3 S3 client initialized when `S3_BUCKET`, `S3_ACCESS_KEY`, and `S3_SECRET_KEY` are provided.

---

### 32. Production Infrastructure

- [x] Docker & Docker Compose setup  
  *Status:* COMPLETE  
  *Evidence:* `Dockerfile`, `backend/Dockerfile`, `docker-compose.yml`  
  *What currently works:* Multi-service stack: backend, worker, beat, redis, frontend.

- [x] Celery background worker & Celery Beat scheduler  
  *Status:* COMPLETE  
  *Evidence:* `backend/celery_app.py`, `backend/tasks/`  
  *What currently works:* 4 task modules, 3 periodic schedules, eager fallback for offline tests.

- [x] Redis connection & health monitoring  
  *Status:* COMPLETE  
  *Evidence:* `backend/celery_app.py` (`inspect_broker_health`), `backend/config.py`  
  *What currently works:* Connects to Redis URL; safely masks password in status outputs.

- [x] Liveness & Readiness health probes  
  *Status:* COMPLETE  
  *Evidence:* `backend/main.py` (`/health/live`, `/health/ready`)  
  *What currently works:* `/health/live` returns 200 ALIVE; `/health/ready` executes `SELECT 1;` and returns 200 or 503.

- [x] Trusted hosts & CORS origin hardening  
  *Status:* COMPLETE  
  *Evidence:* `backend/config.py`, `backend/main.py`  
  *What currently works:* Disallows wildcard `*` in production; restricts CORS to configured origins.

---

### 33. Frontend Completion

- [x] Tenant workspace UI (24 views)  
  *Status:* COMPLETE  
  *Evidence:* `frontend/src/app/(app)/` (dashboard, agents, policies, decisions, approvals, runtime, telemetry, iam, etc.)  
  *What currently works:* All 24 page views render real tables, metrics, and forms calling backend `/api`.

- [x] Super-Admin platform control plane UI  
  *Status:* COMPLETE  
  *Evidence:* `frontend/src/app/platform/`  
  *What currently works:* Multi-tenant org grid, license modal, cross-tenant audit viewer, system health dashboard.

- [x] Real-time WebSocket live updates in UI  
  *Status:* COMPLETE  
  *Evidence:* `frontend/src/lib/api.ts` (`RobustWebSocketClient`), `frontend/src/app/(app)/dashboard/page.tsx`  
  *What currently works:* Reconnecting WebSocket client updates live decision feeds and metrics without page refresh.

---

### 34. API / SDK

- [x] REST API documentation  
  *Status:* COMPLETE  
  *Evidence:* `backend/main.py` (FastAPI Swagger `/docs` and ReDoc `/redoc`), `routers/developers.py`  
  *What currently works:* OpenAPI schema generated for all 36 routers.

- [x] Python Client SDK (`agentguard-python`)  
  *Status:* COMPLETE  
  *Evidence:* `sdks/python/agentguard/` (`client.py`, `langchain_handler.py`, `crewai_middleware.py`, `exceptions.py`), `backend/tests/test_sdk_suite.py` (19/19 passed)  
  *What currently works:* Full-featured SDK client supporting machine authentication (`authenticate()`), direct header authorization (`authorize()`), gate token validation (`gate_...`), egress execution dispatch (`execute()`), atomic unified invocation (`invoke()`), session heartbeats (`heartbeat()`), PII scanning & masking (`scan_pii()`), output toxicity/hallucination scanning (`scan_output()`), LangChain callback handler (`LangChainAgentGuardHandler`), and CrewAI governance middleware (`CrewAIAgentGuardMiddleware`).

- [ ] TypeScript / Node Client SDK (`@agentguard/sdk`)  
  *Status:* PARTIAL  
  *Evidence:* `sdks/typescript/` (`client.ts`, `types.ts`, `errors.ts`)  
  *What currently works:* Client, types, and error structures defined.  
  *What is missing:* Comprehensive automated test suite and npm packaging.

---

### 35. Data Governance

- [x] Immutable audit trail retention  
  *Status:* COMPLETE  
  *Evidence:* `backend/routers/audit.py`  
  *What currently works:* Audit records cannot be modified or deleted.

- [x] Automated data retention & purging worker  
  *Status:* COMPLETE  
  *Evidence:* `backend/tasks/retention_tasks.py` (`purge_expired_data_task`), `backend/tests/test_sdk_suite.py` (`test_data_retention_purging_task`)  
  *What currently works:* Periodic Celery worker task that purges expired runtime sessions, expired capability tokens, stale telemetry metrics, and audit logs beyond retention threshold. Emits immutable `DATA_RETENTION_PURGE` audit logs summarizing purged entities.

---

### 36. Testing

- [x] Automated test suite (398 test cases)  
  *Status:* COMPLETE  
  *Evidence:* `backend/tests/` (29 test suites including `test_sdk_suite.py`, `test_tool_proxy_suite.py`, `test_machine_identity_suite.py`, `test_runtime_authorization_suite.py`, `test_ai_guardrails_suite.py`, `test_output_guardrails_suite.py`), verified via `pytest --collect-only` (398 tests collected)  
  *What currently works:* Auth hardening, policy engine evaluation, multi-tenant isolation, penetration tests, licensing, machine authentication, cryptographic passport verification, runtime authorization kernel, tool proxy gateway, AI guardrails, output safety & hallucination filters, Python SDK client, and retention tasks.

---

### 37. Full System Integration

- [x] End-to-end Human -> Org -> RBAC -> Policy -> Approval -> Telemetry -> Audit flow  
  *Status:* COMPLETE  
  *Evidence:* Verified across `auth.py`, `policies.py`, `decisions.py`, `approvals.py`, `runtime_telemetry_service.py`, `audit.py`.

- [ ] End-to-end Machine Agent -> Auth -> Passport -> Permission -> Capability -> Runtime Gate flow  
  *Status:* NOT_IMPLEMENTED  
  *Evidence:* See Section 1, 4, 5, 6, 7, 13.

---

### 38. Final Product Polish

- [x] Consistent enterprise typography, color tokens, and layout  
  *Status:* COMPLETE  
  *Evidence:* `frontend/src/app/globals.css`, `frontend/tailwind.config.js`  
  *What currently works:* Cohesive dark/light palette, crisp status badges, zero placeholder lorem ipsum.

---

## BUILD DEPENDENCY GRAPH

```mermaid
graph TD
    %% Milestone 1: Agent Machine Identity & Passport
    A[Human Identity & Org Multi-Tenancy] -->|ALREADY COMPLETE| B[Agent Registration Model]
    B -->|ALREADY COMPLETE| C[Agent Status State Machine]
    C --> D[1. Agent Machine Credential Hashing & API]
    D --> E[2. Asymmetric Cryptographic Agent Passport]
    E --> F[3. Machine Agent Authentication Endpoint /runtime/auth]

    %% Milestone 2: Runtime Authorization Kernel
    F --> G[4. Agent Permission Grant/Revoke & Enforcement Gate]
    G --> H[5. Capability Token Pre-Flight Validation Gate]
    H --> I[6. Passport Expiration & Revocation Gate]
    I --> J[7. Unified Runtime Authorization Kernel]

    %% Milestone 3: Intent & Execution Control
    J --> K[8. Structured Intent & Parameter Extraction]
    K --> L[9. Prompt Injection & Jailbreak Defense Guardrail]
    L --> M[10. Egress Tool Execution Proxy Gateway]

    %% Milestone 4: Security Intelligence & Guardrails
    M --> N[11. PII Redaction & Data Exfiltration Filter]
    N --> O[12. Behavioral Anomaly Statistical Velocity Engine]
    O --> P[13. Dynamic Red-Team Policy Fuzzer]

    %% Milestone 5: Developer Ecosystem & SDKs
    P --> Q[14. Python AgentGuard SDK]
    Q --> R[15. TypeScript / LangChain AgentGuard Middleware]
    R --> S[16. Real LLM Provider Integration for Admin Assistant]
```

---

## BUILD MILESTONES

### MILESTONE 1: Machine Agent Identity, Authentication & Cryptographic Passport
- **Goal:** Enable autonomous AI agents to possess genuine machine credentials, authenticate themselves, and present a cryptographically verifiable passport.
- **Dependencies:** Complete Human Auth and Organization models.
- **Deliverables:**
  1. Agent credential generation (`POST /api/agents/{id}/credentials`) and SHA-256 storage.
  2. Asymmetric digital signing service for Agent Passports (Ed25519/ECDSA).
  3. Machine authentication endpoint (`POST /api/runtime/auth`) issuing agent JWTs.
  4. Authentication middleware supporting `X-Agent-Code` and `X-Agent-Key` or Bearer agent tokens.

### MILESTONE 2: Runtime Authorization Kernel & Gateways
- **Goal:** Transform passive policy checks into an active runtime authorization kernel enforcing permissions and capabilities.
- **Dependencies:** Milestone 1.
- **Deliverables:**
  1. Permission grant/revoke API and mandatory permission checking in evaluation pipeline.
  2. Capability token verification gate in evaluation pipeline.
  3. Unified pre-flight authorization endpoint (`POST /api/runtime/authorize`).
  4. Automatic circuit breaker tripping on consecutive policy violations.

### MILESTONE 3: Intent Understanding & Execution Proxy
- **Goal:** Replace primitive regex matching with structured tool call verification and add outbound action dispatching.
- **Dependencies:** Milestone 2.
- **Deliverables:**
  1. Structured function call & JSON schema parameter validator.
  2. Prompt injection and jailbreak detection heuristics.
  3. Outbound execution dispatcher for approved actions.

### MILESTONE 4: AI Guardrails & Security Intelligence
- **Goal:** Implement content safety, PII protection, and dynamic red-teaming.
- **Dependencies:** Milestone 3.
- **Deliverables:**
  1. Input/output PII redaction engine.
  2. Statistical behavioral anomaly engine comparing live velocity to historical baseline.
  3. Automated adversarial policy fuzzing lab.

### MILESTONE 5: Developer SDKs & External Integrations
- **Goal:** Provide first-class developer tooling to seamlessly bind Python and TypeScript agents to AGENTGUARD.
- **Dependencies:** Milestone 4.
- **Deliverables:**
  1. `agentguard` Python client library with LangChain and CrewAI callback handlers.
  2. `@agentguard/sdk` TypeScript package.
  3. Real LLM integration for AI Admin Assistant.

---

## CURRENT NEXT BUILD

### Next Milestone
**MILESTONE 5: Developer Ecosystem & SDKs**

### Next Feature
**Feature 5.1: Python AgentGuard Client SDK & Framework Middleware (LangChain / CrewAI)**

### Why This Comes Next
With Machine Identity (M1), the Runtime Authorization Kernel (M2), Tool Proxy & Intent Parsing (M3), and AI Guardrails & Security Intelligence (M4) fully implemented and tested, the AGENTGUARD platform core is complete. Developers now need high-level SDKs and framework middleware to easily wrap their Python and TypeScript agents with AGENTGUARD governance in just 2 lines of code.

### Dependencies
- `/api/runtime/auth` (M1: complete)
- `/api/runtime/authorize` (M2: complete)
- `/api/runtime/execute` and `/api/runtime/invoke` (M3: complete)
- `/api/runtime/scan-pii` (M4: complete)

### Files Expected To Be Involved
- `sdks/python/agentguard/__init__.py`
- `sdks/python/agentguard/client.py`
- `sdks/python/agentguard/langchain_handler.py`
- `sdks/python/agentguard/crewai_middleware.py`
- `sdks/typescript/src/index.ts`
- `sdks/typescript/src/client.ts`
- `backend/tests/test_sdk_suite.py`

### Definition of Done
1. Python SDK package allows agents to authenticate using API keys, pre-flight check actions, invoke tools safely through AGENTGUARD, and catch governance refusals.
2. LangChain callback handler automatically intercepts tool calls and LLM outputs, reporting tokens and pre-clearing decisions.
3. CrewAI middleware intercepts agent task executions.
4. TypeScript client provides typed API client for Node.js / Next.js agent runtimes.
5. All regression tests pass with 100% green.

---

## LIVING CHECKLIST RULE

This document is the **Living Master Checklist** for AGENTGUARD.

Whenever an implementation phase is completed:
1. Open this file (`AGENTGUARD_MASTER_BUILD_CHECKLIST.md`).
2. Update the specific checkbox items from `[ ]` to `[x]`.
3. Update their status (e.g. `NOT_IMPLEMENTED` $\rightarrow$ `COMPLETE`).
4. Document the exact evidence: files modified, database changes, APIs added, test coverage.
5. Update the summary counters in the **Project Status** header.
6. Record an entry in the **CHECKLIST CHANGE HISTORY** table below.
7. Advance the **CURRENT NEXT BUILD** pointer to the next single priority item.

---

## CHECKLIST CHANGE HISTORY

| Date | Phase / Milestone | Changes Made | Items Completed | Next Target |
|:---|:---|:---|:---|:---|
| 2026-10-01 | Baseline Forensic Audit | Inspected full codebase, verified 299 tests, established baseline status across 38 domains, created persistent living checklist. | 58 items confirmed complete | Feature 1.1: Agent Machine Credential Issuance |
| 2026-10-01 | Milestone 1 — Machine Identity | Implemented agent credentials (generation, SHA-256 hashing, rotation, revocation), Ed25519 asymmetric cryptographic passport signing & verification, machine JWT auth `/api/runtime/auth`, direct headers auth, agent runtime sessions & heartbeats. | 5 items completed | Milestone 2: Runtime Authorization Kernel |
| 2026-10-01 | Milestone 2 — Runtime Authorization Kernel | Implemented permission grant/revoke CRUD & Stage 5 permission enforcement gate, Stage 6 dynamic single-use capability token validation gate, unified pre-flight authorization endpoint `/api/runtime/authorize`, automatic circuit breaker tripping on consecutive refusals with operator reset. | 4 items completed | Milestone 3: Intent & Tool Proxy Gateway |
| 2026-10-01 | Milestone 3 — Tool Proxy & Intent Engine | Implemented structured function call & JSON schema parameter validation, prompt injection & jailbreak detection heuristics, tool registry CRUD `/api/tools`, forward egress tool proxy with SSRF defense (blocking loopback & cloud metadata `169.254.169.254`), single-use execution gate token replay protection, `/api/runtime/execute`, `/api/runtime/invoke`, execution telemetry & provenance logging. | 4 items completed | Milestone 4: AI Guardrails & Security Intelligence |
| 2026-10-01 | Milestone 4 — AI Guardrails & Security Intelligence | Implemented PII & sensitive data redaction engine (`pii_engine.py`) with MASK/PARTIAL_MASK/TOKENIZE/BLOCK modes, Stage 6.6 PII guardrail in runtime kernel, outbound proxy response sanitization, behavioral anomaly engine (`behavior_engine.py`) tracking velocity spikes, operating hours compliance, allowed tools, and baseline spending, Stage 8.5 dynamic risk scoring integration, upgraded red team engine (`red_team_engine.py`) with mutation techniques (Base64, Delimiter, Roleplay, Leetspeak, Instruction override), automated policy fuzzing `/api/red-team/fuzz`, and standalone `/api/runtime/scan-pii` diagnostics. | 4 items completed | Milestone 5: Developer Ecosystem & SDKs |
