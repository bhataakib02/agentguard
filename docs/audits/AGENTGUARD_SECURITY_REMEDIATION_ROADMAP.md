# AGENTGUARD — Security Remediation Roadmap

**Document Reference**: AGENTGUARD-SEC-ROADMAP-2026-11-28  
**Audit Baseline**: Commit `5e8523e1acf5d96c31b570330f5cbca1f942bf92` (`main`)  
**Purpose**: Prescriptive, prioritized engineering roadmap to remediate all security findings discovered during the Pre-Production Security Release Gate audit.

---

## Roadmap Overview

```
┌──────────────────────────────────────────────────────────────┐
│  Phase 1: Critical Blockers (Staging Release Gates)          │
│  - Staging Environment Database Provisioning                 │
│  - Live Staging PostgreSQL Defense-in-Depth RLS Migration    │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  Phase 2: High-Priority Security (Production Release Gates)  │
│  - Global Distributed API Rate Limiting Middleware           │
│  - Production Verified Outbound Email Sender Domain Setup    │
│  - Live Database Catalog Privilege Revocation (TRUNCATE/etc) │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  Phase 3: Medium-Priority Hardening (Enterprise Scaling)     │
│  - Frontend Session Transition to HttpOnly Secure Cookies    │
│  - Modernize JWT Library from python-jose to PyJWT           │
│  - Content Security Policy (CSP) & Header Hardening          │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  Phase 4: Operational Maturity (Day-2 Production Operations) │
│  - SIEM Live Integration & Automated Alerting Rules          │
│  - Secret Rotation Runbooks & Automated Key Roll-Over        │
│  - Automated Staging Security Regression Pipeline in CI/CD   │
└──────────────────────────────────────────────────────────────┘
```

---

## Phase 1 — Critical Blockers (Required for Staging Promotion)

These items must be completed before any deployment beyond local development:

### Item 1.1: Live Staging PostgreSQL RLS Migration Execution
- **Finding ID**: `AG-SEC-01`
- **Priority**: P0 (CRITICAL RELEASE PREREQUISITE)
- **Required Fix**:
  1. Provision a dedicated staging PostgreSQL database (Supabase staging project or isolated PostgreSQL 15+ container).
  2. Execute `docs/proposed_migrations/20261125010000_idempotent_defense_in_depth_rls.sql` against the staging database following `docs/security/SECURITY_MIGRATION_RUNBOOK.md`.
  3. Ensure execution of `20261125010000_idempotent_defense_in_depth_rls_rollback.sql` in a rollback test dry run to guarantee reversibility.
- **Dependencies**: Dedicated staging database connection string (`STAGING_DATABASE_URL`).
- **Acceptance Criteria**:
  - All 50 public schema tables have `ROW LEVEL SECURITY` enabled.
  - Dangerous privileges (`TRUNCATE`, `REFERENCES`, `TRIGGER`) are revoked from `anon` and `authenticated`.
  - Service role bypass policy (`service_role_all`) is verified for backend workers.
  - Authenticated PostgREST client queries without valid `app_metadata.org_id` return 0 rows.
- **Suggested Regression Tests**:
  - Run `POSTGRES_TEST_URL="<staging_url>" pytest backend/tests/test_postgresql_rls_validation.py -v`.
  - All 15 database engine RLS tests must pass with 0 failures.

---

## Phase 2 — High-Priority Security (Required Before Production Release)

These items must be resolved and verified before promoting from Staging to Production:

### Item 2.1: Global Distributed API Rate Limiting Middleware
- **Finding ID**: `AG-SEC-02`
- **Priority**: P1 (HIGH)
- **Required Fix**:
  1. Integrate `slowapi` or custom Redis sliding-window rate limiting middleware in `backend/main.py`.
  2. Define tiered limits:
     - Public Unauthenticated Auth (`/auth/login`, `/auth/local-login`): 10 requests / minute per IP.
     - Authenticated API Endpoints: 120 requests / minute per user/tenant.
     - Expensive Endpoints (`/reports/generate`, `/reports/export/*`, `/ai/*`): 10 requests / minute per tenant.
     - Machine Runtime Execution (`/runtime/action/authorize`, `/tools/execute`): Bound by agent autonomy level and license quota.
  3. Connect middleware to managed Redis (`agentguard-redis`).
- **Dependencies**: Provisioned Redis instance (`REDIS_URL`).
- **Acceptance Criteria**:
  - High-frequency requests exceeding limits receive `429 Too Many Requests` with `Retry-After` header.
  - Rate limits are distributed across multi-instance backend pods via Redis.
  - OTP rate limits remain enforced via `models.OtpChallenge` as an independent defense layer.
- **Suggested Regression Tests**:
  - Add `backend/tests/test_global_rate_limiting.py` asserting HTTP 429 upon bursting 15 consecutive login attempts.

### Item 2.2: Outbound Email Custom Domain Provisioning
- **Finding ID**: `AG-SEC-03`
- **Priority**: P1 (HIGH)
- **Required Fix**:
  1. In Brevo or Resend management console, add and verify corporate DNS records (SPF, DKIM, DMARC) for the production sender domain (e.g. `mail.agentguard.io`).
  2. Set production environment variables in Render:
     ```bash
     EMAIL_PROVIDER=BREVO # or RESEND
     BREVO_API_KEY=<verified-key>
     BREVO_FROM_EMAIL=auth@agentguard.io
     BREVO_FROM_NAME="AgentGuard Security"
     ```
  3. Verify that `/platform/health` reports email status as `Operational` and `sandbox_mode: false`.
- **Dependencies**: Corporate domain DNS access.
- **Acceptance Criteria**:
  - Registration OTPs sent to external email addresses (`@gmail.com`, `@outlook.com`, `@company.com`) deliver within 5 seconds.
  - Zero `RECIPIENT_RESTRICTED` or `UNVERIFIED_SENDER_DOMAIN` errors in `AuditLog`.
- **Suggested Regression Tests**:
  - Execute `test_otp_resend_delivery.py` and `test_otp_brevo_delivery.py` against staging mock targets.

---

## Phase 3 — Medium-Priority Hardening (Planned Security Improvements)

These enhancements should be scheduled in the first post-launch sprint:

### Item 3.1: Frontend Session Transition to HttpOnly, Secure Cookies
- **Finding ID**: `AG-SEC-04`
- **Priority**: P2 (MEDIUM)
- **Required Fix**:
  1. Update `/auth/login`, `/auth/verify-otp`, and `/auth/register` endpoints to return access tokens via `Set-Cookie` header with attributes: `HttpOnly; Secure; SameSite=Strict; Path=/`.
  2. Implement double-submit anti-CSRF token or custom header requirement (`X-Requested-With: AgentGuardClient`) for state-changing endpoints.
  3. Update `frontend/src/middleware.ts` to read cookies strictly from request cookies.
  4. Remove token persistence from `localStorage.getItem("agentguard_token")`.
- **Dependencies**: Backend CORS `allow_credentials=True` (already enabled in `main.py:81`).
- **Acceptance Criteria**:
  - Browser DevTools console cannot access access tokens via `document.cookie` or `localStorage`.
  - Frontend continues to authenticate cleanly across all 59 routes.
- **Suggested Regression Tests**:
  - Run frontend E2E Playwright suite asserting login session creation via cookie headers.

### Item 3.2: Modernize JWT Library from python-jose to PyJWT
- **Finding ID**: `AG-SEC-05`
- **Priority**: P2 (MEDIUM)
- **Required Fix**:
  1. Replace `python-jose[cryptography]` with `PyJWT[crypto]>=2.8.0` in `backend/requirements.txt`.
  2. Refactor `jwt.encode` and `jwt.decode` calls in `core/security.py`, `core/deps.py`, `services/machine_auth_service.py`, and `services/otp_service.py`.
- **Dependencies**: None.
- **Acceptance Criteria**:
  - All existing JWT decoding, audience validation, and expiration checks pass identically.
  - Eliminated unmaintained library dependency.
- **Suggested Regression Tests**:
  - Run `test_authentication_and_otp_flows.py`, `test_machine_identity_suite.py`, and `test_websocket_auth.py`.

---

## Phase 4 — Operational Maturity & Day-2 Procedures

Operational controls required for sustainable enterprise compliance:

### Item 4.1: Automated Security Telemetry & SIEM Live Ingestion
- **Finding ID**: `AG-SEC-06`
- **Priority**: P3 (LOW / OPERATIONAL)
- **Required Fix**:
  1. Provision production Splunk HEC or Datadog Logs endpoint.
  2. Populate `SIEM_FORWARDER_URL` and `SIEM_AUTH_TOKEN` in Render environment.
  3. Verify that `tasks/siem_tasks.py` exports security events (`AUTH_FAILED`, `CIRCUIT_BREAK`, `SSRF_BLOCKED`, `DECISION_BLOCKED`) in real time.
- **Dependencies**: Enterprise SIEM instance.
- **Acceptance Criteria**:
  - Critical incidents appear in SIEM within 30 seconds of occurrence.

### Item 4.2: Automated Staging Security Regression Pipeline in CI/CD
- **Finding ID**: `AG-SEC-07`
- **Priority**: P3 (LOW / OPERATIONAL)
- **Required Fix**:
  1. In `.github/workflows/ci.yml`, add a dedicated security testing job.
  2. Launch a temporary PostgreSQL 16 container with `docker-compose.staging.yml`.
  3. Execute `20261125010000_idempotent_defense_in_depth_rls.sql`.
  4. Run `pytest backend/tests/test_postgresql_rls_validation.py`.
  5. Block PR merges if any RLS policy test fails.
- **Dependencies**: GitHub Actions workflow configuration.
- **Acceptance Criteria**:
  - Automated PR checks validate PostgreSQL RLS defense-in-depth on every pull request.

---

## Summary of Remediation Ownership

| Item | Area | Owner | Target Gate | Estimated Effort |
|---|---|---|---|---|
| **1.1** | Supabase RLS Migration | Database / SecOps | Staging Gate | 1 Day |
| **2.1** | Global API Rate Limiting | Backend Engineering | Production Gate | 2 Days |
| **2.2** | Verified Email Domain | DevOps / Infrastructure | Production Gate | 0.5 Days |
| **3.1** | HttpOnly Cookie Migration | Fullstack Engineering | Beta Hardening | 3 Days |
| **3.2** | PyJWT Library Upgrade | Backend Engineering | Maintenance | 1 Day |
| **4.1** | SIEM Live Forwarding | SecOps / Enterprise Ops | Post-Launch | 2 Days |
| **4.2** | CI/CD RLS Automated Job | DevOps Engineering | Post-Launch | 1 Day |
