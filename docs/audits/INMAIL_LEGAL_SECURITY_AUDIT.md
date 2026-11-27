# AGENTGUARD — Inmail, Legal & Security Pages Audit Report

**Audit Date:** 2026-11-27  
**Workspace:** `D:\AGENTGUARD` (local only — no commits, pushes, or deployments performed)  
**Final Classification:** **READY FOR LOCAL REVIEW**

---

## 1. Files Reviewed

- **Inmail / Notifications:**
  - `backend/routers/notifications.py`
  - `backend/services/notification_service.py`
  - `backend/tasks/notification_tasks.py`
  - `frontend/src/components/ui/DashboardHeader.tsx`
  - `frontend/src/app/(app)/notifications/page.tsx`
  - `frontend/src/app/platform/layout.tsx`
- **Public Pages & Navigation:**
  - `frontend/src/app/page.tsx`
  - `frontend/src/app/(auth)/register/page.tsx`
  - `frontend/src/app/(auth)/login/page.tsx`
  - `frontend/src/app/privacy/page.tsx` *(created)*
  - `frontend/src/app/terms/page.tsx` *(created)*
  - `frontend/src/app/security/page.tsx` *(created)*

---

## 2. Notification & Inmail Findings

- **Backend (`notifications.py`):** All 6 endpoints enforce `get_current_user`, strict `user_id` isolation for non-`SUPER_ADMIN` users, IDOR checks (`403` on cross-user access), bounded pagination (`limit` 1–200), and SQL-level filtering (`unread_only`, `severity`, `type`).
- **Tenant Navbar (`DashboardHeader.tsx`):** Live 60-second polling (`/notifications?limit=15` and `/notifications/unread-count`), proper `active = false` + `clearInterval` cleanup, unread badge, severity colors, click-to-mark-read, mark-all-read, and "View All Notifications →" link to `/notifications`.
- **Platform Super Admin Navbar (`platform/layout.tsx`):** Same 60-second polling gated on `user?.role === "SUPER_ADMIN"`. **Defect fixed:** Added missing `"View All Notifications →"` link at the bottom of the Platform Alerts dropdown.
- **Notification Center (`(app)/notifications/page.tsx`):** Supports `ALL`, `UNREAD`, `CRITICAL`, and `APPROVALS` filters, pagination, mark-one-read, mark-all-read, delete/dismiss, loading and empty states.

---

## 3. Privacy Policy Findings (`/privacy`)

- **Before:** Route `/privacy` did not exist (404); footer text was unlinked `<span>` elements.
- **Fixed:** Created `frontend/src/app/privacy/page.tsx` matching AGENTGUARD's design system (`#FCFCFA` / `#FFFFFF` / `#2E9D50` / `#E8E8E4`).
- **Truthfulness:** Documents only verified data collection (account/auth data, OTP 10-minute expiry, Agent Passports, governance decisions, security incidents, audit logs, session cookies `agentguard_token` and `localStorage` keys) and actual third-party infrastructure (Supabase, Render, Vercel, and optional Resend). Does not invent legal entities, addresses, or certifications.

---

## 4. Terms of Service Findings (`/terms`)

- **Before:** Route `/terms` did not exist (404); footer text was unlinked `<span>` elements.
- **Fixed:** Created `frontend/src/app/terms/page.tsx` tailored specifically to AGENTGUARD as an enterprise AI agent runtime governance platform.
- **Truthfulness:** Covers service description, account/OTP responsibility, authorized use, AI agent governance responsibility, prohibited activities, API usage, third-party infrastructure, availability, IP, termination, liability disclaimers, and `[LEGAL REVIEW REQUIRED]` flags for counsel.

---

## 5. Zero-Trust Security Findings (`/security`)

- **Before:** Route `/security` did not exist (404); footer text was unlinked `<span>` elements.
- **Fixed:** Created `frontend/src/app/security/page.tsx` with interactive expandable sections and explicit 4-tier status badges:
  1. **Implemented & Verified** (JWT + Supabase fallback, OTP verification, session revocation, 9-tier RBAC, `SUPER_ADMIN` isolation, IDOR protection, SQL tenant filtering, parameterized queries, no secrets in health APIs, kill switch, webhook dedupe, internal tests)
  2. **Implemented — Not Independently Verified** (token cache, PostgreSQL RLS migrations, capability tokens, deterministic policy engine, causal provenance, CORS/HTTPS)
  3. **Planned** (TOTP MFA, ABAC, SIEM integration, platform-wide API rate limiting, GDPR DPA)
  4. **Not Implemented** (WAF, automated secret rotation, independent penetration test, SOC 2 Type II, ISO 27001)
- **Compliance honesty:** Explicitly states no SOC 2, ISO 27001, or third-party penetration test has been completed.

---

## 6. Footer & Legal Navigation Findings

- **Fixed in `frontend/src/app/page.tsx`:** Converted all footer `<span>` labels (`Privacy Policy`, `Terms of Service`, `Zero-Trust Security`, and bottom `Privacy` / `Terms` / `Security`) into `<Link>` components pointing to `/privacy`, `/terms`, and `/security`.
- **Fixed in `frontend/src/app/(auth)/register/page.tsx` & `login/page.tsx`:** Added direct links to `/terms`, `/privacy`, and `/security`.

---

## 7. Tests Performed

| Check | Result |
|---|---|
| `pytest tests/test_otp_resend_delivery.py tests/test_authentication_and_otp_flows.py tests/test_notification_alerting_engine.py tests/test_tenant_isolation_and_security_audit.py -v` | **63 passed, 0 failed** (59.67s) |
| `npx tsc --noEmit` | **Passed (0 errors)** |
| `npx next lint` | **Passed (No ESLint warnings or errors)** |
| Browser automation | Not run in this session (API/unit/build verified; browser smoke test recommended locally/staging) |

---

## 8. Remaining Legal & Security Requirements

### Legal Requirements (Owner + Counsel Action Required)
- Registered legal entity name and business address
- Dedicated privacy/DPO and legal contact email addresses
- Governing law, jurisdiction, venue, and dispute resolution clauses
- Formal data retention schedule and post-termination deletion SLA
- Jurisdiction-specific liability caps and GDPR DPA (if serving EU customers)

### Security Evidence Required Before Production Claims
- Independent third-party penetration test
- Live PostgreSQL 17 / Supabase RLS verification (`POSTGRES_RLS_TEST_URL`)
- SOC 2 Type II / ISO 27001 audit (only if pursuing certification)
- Production WAF and automated secret rotation policy
