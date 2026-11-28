# AGENTGUARD — Security Executive Summary

**Date**: November 28, 2026  
**Audience**: Founders, Engineering Leadership, Prospective Enterprise Customers, Security Reviewers  
**Auditor**: Independent Pre-Production Security Review Team  
**Evaluated Git Baseline**: Commit `5e8523e1acf5d96c31b570330f5cbca1f942bf92` (`main`)  
**Overall Release Classification**: **CONDITIONAL GO** (Approved for Staging Deployment; Production Held Pending Staging Verification)

---

## 1. Overall Security Posture

AGENTGUARD is an enterprise-grade AI-agent runtime governance, security, and monitoring platform. It acts as an authoritative control plane that intercepts, evaluates, and controls the actions of autonomous AI agents before they interact with internal databases, APIs, or third-party tools.

An exhaustive, independent code-level security audit was conducted across the entire codebase (40 API routers, 12 backend services, 10 security engines, database migrations, deployment configurations, and Next.js frontend).

### High-Level Summary:
- **Zero Critical Vulnerabilities**: No authentication bypasses, no cross-tenant data leaks, no remote code execution outside sandboxes, and no prompt injection leakage vulnerabilities exist in the codebase.
- **Architectural Strengths**:
  1. **Non-Bypassable 12-Stage Governance**: Every AI agent action must pass through pre-flight identity, passport, budget, circuit breaker, policy, and prompt-injection checks before obtaining a single-use execution gate token.
  2. **SSRF & DNS Rebinding Immunity**: The forward tool execution proxy employs connection IP pinning (`PinningTransport`) that physically prevents DNS rebinding (TOCTOU) attacks at the TCP socket layer.
  3. **Strict Machine / Human Identity Boundary**: Machine agents (`AGENT`) cannot authenticate to human REST endpoints, and human users cannot assume machine credentials.
  4. **Cryptographic Protection of Credentials**: All API keys, agent credentials, and OTP challenges are HMAC-hashed or encrypted at rest using AES-256-GCM authenticated encryption.
- **Remaining Prerequisites Before Production**:
  1. The defense-in-depth PostgreSQL Row Level Security (RLS) migration is fully designed and tested in isolated suites, but must be applied and verified on a live Supabase staging database.
  2. Global API rate limiting needs to be added across general REST endpoints.
  3. Outbound email domain verification must be provisioned in the production mail provider.

---

## 2. Release Classification

### Official Verdict: **CONDITIONAL GO**

| Target Environment | Status | Criteria / Rationale |
|---|---|---|
| **Isolated Staging** | **GO** | All application security controls, tenant isolation, auth, and runtime governance verified. Safe for staging provisioning, internal red-teaming, and UAT. |
| **Public Beta / Production** | **HELD (PENDING PREREQUISITES)** | Requires live staging verification of database RLS, global API rate limiting, and verified email sender domains. |

---

## 3. Findings Summary by Severity

| Severity Level | Count | Summary of Issues |
|---|---|---|
| **CRITICAL** | **0** | No critical vulnerabilities discovered in the audited scope. |
| **HIGH** | **1** | `AG-SEC-01`: Proposed PostgreSQL RLS migration unapplied to live database (mitigated at application layer). |
| **MEDIUM** | **1** | `AG-SEC-02`: Absence of global distributed rate limiting on general REST endpoints (OTP endpoints are rate-limited). |
| **LOW** | **2** | `AG-SEC-03`: Default Resend email sender domain restricted to sandbox; `AG-SEC-04`: Client-side JWT storage in browser localStorage. |
| **INFORMATIONAL** | **2** | `AG-SEC-05`: Plan migration from `python-jose` to `PyJWT`; `AG-SEC-06`: Production Redis deployment requirement. |

---

## 4. Verified Security Controls

The following security controls have been directly verified against actual source code and automated tests:

1. **Authentication & Session Lifecycle**:
   - Cryptographically secure 6-digit OTPs using CSPRNG (`secrets.randbelow`).
   - HMAC-SHA256 hashed OTP storage (zero plaintext OTPs in database).
   - Maximum 5 verification attempts per OTP challenge before automatic destruction.
   - 120-second resend cooldown per email and purpose.
   - Account enumeration protection across registration, login, and password recovery.
   - Instant revocation of all active user sessions upon password reset.
   - Strict separation of WebSocket tickets, machine tokens, and human user tokens.

2. **Enterprise IAM & Authorization**:
   - 11 hierarchical human roles (`USER` up to `SUPER_ADMIN`) and 1 machine role (`AGENT`).
   - Privilege escalation prevention: users cannot assign roles at or above their own rank.
   - Self-role modification prevention: users cannot alter their own roles.
   - Platform super-admin endpoints (`/platform/*`) strictly require verified `SUPER_ADMIN` authorization.

3. **Multi-Tenant Isolation**:
   - Application-layer tenant filtering (`org_id`) enforced across all API routers and database queries.
   - Fail-closed cross-tenant access denial (HTTP 403 Forbidden).
   - Parent-child tenant scoping across approvals, webhook deliveries, and policy rules.

4. **AI-Agent Runtime Governance**:
   - 12-stage pre-flight authorization kernel.
   - FinOps budget enforcement (daily limits and monthly caps).
   - Dynamic circuit breaker engine that trips on consecutive failure spikes.
   - Prompt injection and jailbreak detection refusing high-threat payloads.
   - Single-use execution gate tokens (`gate_<uuid>`) with 300-second TTL.
   - Atomic SQL update preventing concurrent gate-token replay attacks.

5. **Tool Proxy & SSRF Defense**:
   - Complete blacklist of RFC 1918 private IPs, loopback, link-local, and cloud metadata (`169.254.169.254`, `100.100.100.200`).
   - Noncanonical numeric IP decoding (octal, hex, decimal, BSD style).
   - Connection IP pinning (`PinningTransport`) that prevents DNS rebinding (TOCTOU).
   - Automatic HTTP redirect following strictly blocked (`follow_redirects=False`).

6. **Webhooks & Asynchronous Tasks**:
   - HMAC-SHA256 signature verification over `timestamp.payload`.
   - Webhook secrets encrypted at rest via AES-256-GCM.
   - Asynchronous worker dispatch with bounded retries (3 attempts) and dead-letter queueing.
   - Automated retention purging tasks for expired sessions, capability tokens, and audit logs.

---

## 5. Unverified Controls & Staging Dependencies

The following controls could not be verified in this local audit due to non-destructive change control rules:
1. **Live PostgreSQL Row Level Security (RLS)**:
   - The proposed RLS script (`20261125010000_idempotent_defense_in_depth_rls.sql`) has been verified via design review and offline tests, but has **not** been executed against the live Supabase staging database.
   - Requires spinning up a staging PostgreSQL database to run the live RLS verification suite (`test_postgresql_rls_validation.py`).
2. **Outbound Real Email Delivery**:
   - Delivery was verified through mocks and status inspections; actual delivery to live enterprise mailboxes (Google Workspace, Microsoft 365) requires a provisioned staging domain.
3. **Multi-Instance Distributed Celery / Redis Performance**:
   - Local tests ran in synchronous/eager test mode; live distributed task execution across multiple Render workers requires live staging Redis.

---

## 6. Main Residual Risks

1. **Reliance on Application-Layer Isolation**: Until PostgreSQL RLS is applied to the live database, tenant isolation is maintained solely by the FastAPI/SQLAlchemy application code. While application code is verified and 34 tenant isolation tests pass, applying RLS is critical for defense-in-depth against direct database query vulnerabilities.
2. **Denial of Service via Un-Rate-Limited Endpoints**: Without global API rate limiting, a compromised user token could trigger high request volumes against expensive endpoints (e.g. report generation, AI analysis).

---

## 7. Recommended Next Actions

1. **Step 1 (Immediate)**: Authorize deployment of AGENTGUARD to an isolated **Staging Environment** (Render staging + Supabase staging database + staging Redis).
2. **Step 2 (Staging Setup)**: Follow `docs/security/SECURITY_MIGRATION_RUNBOOK.md` to execute the defense-in-depth RLS migration in the staging database.
3. **Step 3 (RLS Verification)**: Run the live RLS test suite (`test_postgresql_rls_validation.py`) against the staging database.
4. **Step 4 (Rate Limiting)**: Add global Redis-backed rate limiting middleware to FastAPI before production deployment.
5. **Step 5 (Email Provisioning)**: Configure and verify a custom sending domain in Brevo or Resend.
6. **Step 6 (Production Promotion)**: Following successful completion of Steps 1–5, upgrade release gate classification to **GO** for production release.
