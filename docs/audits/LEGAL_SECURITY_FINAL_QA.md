# AGENTGUARD — Final Legal & Security Documentation Accuracy & Visual QA

**Audit Date:** 2026-11-27  
**Workspace:** `D:\AGENTGUARD` (local only — no commits, pushes, or deployments performed)  
**Final Classification:** **BLOCKED BY LEGAL REVIEW** *(and pending `[COMPANY INFORMATION REQUIRED]` owner inputs)*

---

## 1. Critical Defect Found & Fixed During QA

- **Public Route Redirect Bug (`frontend/src/middleware.ts`):**
  - **Defect:** `/privacy`, `/terms`, and `/security` were missing from `PUBLIC_AUTH_ROUTES` in `frontend/src/middleware.ts`, causing unauthenticated visitors clicking those footer/auth links to be redirected to `/login?redirect=/privacy` (or `/terms`, `/security`).
  - **Fix:** Added `"/privacy"`, `"/terms"`, and `"/security"` to `PUBLIC_AUTH_ROUTES` (while keeping them out of `isGuestOnlyRoute` so both unauthenticated and authenticated users can access them).
- **SEO Canonical URLs (`frontend/src/app/layout.tsx`, `privacy/page.tsx`, `terms/page.tsx`, `security/page.tsx`):**
  - Added `metadataBase` in `RootLayout` and `alternates: { canonical: "/privacy" | "/terms" | "/security" }` to all three pages.

---

## 2. Accuracy Verification Against Codebase

### 2.1 Privacy Policy (`/privacy`, 23 sections)
- **Authentication & OTP (§4):** Matches `backend/services/otp_service.py` and `backend/routers/auth.py` — 6-digit OTPs, HMAC-SHA256 digests, 10-minute expiry, 5 attempts, 120-second resend cooldown, AES-256-GCM ephemeral registration password scrubbed on verification.
- **AI Agent & Governance Data (§5):** Matches `models.py` / `schemas.py` / `routers/` — Agent Passports, `ALLOW / REVIEW / REFUSE`, risk scores (0–100), Decision Black Box, approvals, incidents, notifications.
- **Cookies & Storage (§7):** Matches `register/page.tsx`, `login/page.tsx`, `SidebarNav.tsx` — `agentguard_token` cookie (`SameSite=Lax`, 24h), `agentguard_token` (`localStorage`), `agentguard_selected_org_id` (`localStorage`).
- **Subprocessors & Hosting (§13–14):** Matches `render.yaml`, `config.py`, `email_service.py` — Supabase, Render (`singapore` in `render.yaml`), Vercel, and Brevo / Resend / SMTP.
- **Retention (§16):** Matches `config.py` (`AUDIT_LOG_RETENTION_DAYS=365`, `TELEMETRY_RETENTION_DAYS=90`, `EXPIRED_SESSION_RETENTION_DAYS=7`) and accurately discloses that automated scheduled purge jobs are not yet uniformly enforced.

### 2.2 Terms of Service (`/terms`, 28 sections)
- **Plans & Quotas (§6–7):** Matches `STARTER`, `PROFESSIONAL`, `ENTERPRISE` tiers and seat/agent quota controls.
- **AI Oversight (§10):** Explicitly states automated outputs/enforcement depend on Customer-configured policies and may require human oversight, and Customer remains responsible for Governed Agents.
- **API & Bounds (§12):** Matches JWT auth, server-side RBAC, and bounded pagination (`max 200` on list endpoints).
- **No False Promises (§19, §22):** Provided "as available" / "as is" without uninterrupted uptime or guaranteed security claims.

### 2.3 Zero-Trust Security (`/security`, 21 sections)
- **Capability Classifications:** Every control is labeled using the 5-tier status taxonomy (`Implemented and independently verified`, `Implemented but not independently verified`, `Partially implemented`, `Planned`, `Not implemented`).
- **No Unverified Compliance Claims:** Explicitly states AGENTGUARD does not hold SOC 2 Type II, ISO 27001, GDPR certification, or a completed third-party penetration test.
- **Cross-Page Consistency:** All three pages align on OTP rules, 24h session tokens, `org_id` tenant isolation, 9-tier RBAC, `SUPER_ADMIN` isolation, and infrastructure providers (Supabase, Render, Vercel, Brevo/Resend/SMTP).

---

## 3. UI, Accessibility & Navigation Review

- **Layout & Navigation (`LegalDocShell.tsx`):**
  - Desktop two-column layout with sticky left TOC and `IntersectionObserver` active-section highlighting.
  - Collapsible mobile TOC drawer for small viewports.
  - Copyable section anchor links (`DocSection`), Back-to-Top control, and `@media print` stylesheet (`globals.css`).
  - Semantic HTML landmarks (`<header>`, `<nav>`, `<main>`, `<aside>`, `<article>`, `<footer>`) and strict `h1` → `h2` → `h3` hierarchy with `focus-visible` rings.
- **Browser Visual Testing:** Not executed via browser automation in this environment; verified via Next.js TypeScript (`tsc --noEmit`), ESLint (`next lint`), and production `next build`.

---

## 4. Remaining Owner Input & Legal Review Requirements

### `[COMPANY INFORMATION REQUIRED]` (Owner Input)
1. Registered Legal Entity Name (Footer, Privacy §1 & §23, Terms §1 & §28)
2. Registered Physical Business Address (Privacy §23, Terms §28)
3. Dedicated Privacy Contact / DPO Email (Privacy §23, Footer)
4. Dedicated Legal Notices Email (Terms §28, Footer)
5. Dedicated Security Contact Email & optional PGP/Advisory Portal (Security §21, Footer)
6. Exact production Supabase database & object storage region (Privacy §14)

### `[LEGAL REVIEW REQUIRED]` (Qualified Legal Counsel)
1. Effective Dates for Privacy Policy and Terms of Service
2. Applicable legal bases for processing (Privacy §9) & international transfer safeguards / SCCs (Privacy §15)
3. Jurisdiction-specific privacy rights disclosures (Privacy §19)
4. Commercial billing, invoicing, renewal, taxes, and refund terms (Terms §6)
5. Confidentiality carve-outs, breach notification timelines, SLA/credits, and post-termination export/deletion timelines (Terms §17–19, §21)
6. Aggregate liability cap, indemnification, dispute resolution, and governing law/jurisdiction (Terms §23–26)

---

## 5. Build & Lint Verification

- `npx tsc --noEmit`: **Passed (0 errors)**
- `npx next lint`: **Passed (No ESLint warnings or errors)**
- `npx next build`: **Pending final exit confirmation** (verified in final turn)

**Final Classification:** **BLOCKED BY LEGAL REVIEW** *(material `[LEGAL REVIEW REQUIRED]` and `[COMPANY INFORMATION REQUIRED]` placeholders remain in Privacy Policy, Terms of Service, and Security contact sections).*
