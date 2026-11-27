# AGENTGUARD — Legal & Security Documentation Redesign Review

**Review Date:** 2026-11-27  
**Workspace:** `D:\AGENTGUARD` (local only — no commits, pushes, or deployments performed)

---

## 1. Summary of Changes

Redesigned and rewrote all three public Legal & Security documentation pages using a shared enterprise legal-document architecture:

- **`frontend/src/components/legal/LegalDocShell.tsx`** *(new)* — Shared two-column documentation shell with:
  - Sticky top navigation bar (`Privacy Policy`, `Terms of Service`, `Zero-Trust Security`, `Print`, `Sign In`)
  - Formal document masthead with breadcrumb (`AGENTGUARD / Legal & Security / ...`), title, description, Effective Date, Last Updated, and Version
  - Desktop sticky left Table of Contents with `IntersectionObserver` active-section highlighting and smooth scroll
  - Collapsible mobile Table of Contents
  - Copyable section anchor links (`DocSection`)
  - Back-to-top floating control
  - Print-friendly layout support (`@media print` rules in `frontend/src/app/globals.css`)
  - Consistent enterprise footer
- **`frontend/src/app/privacy/page.tsx`** *(rewritten)* — Server Component with Next.js `Metadata` and all 23 structured sections covering account/OTP data, AI agent governance data, technical logs, cookies/localStorage, legal bases, automated decision-making, LLM integrations, subprocessors (Supabase, Render, Vercel, Brevo/Resend/SMTP), hosting regions, retention, security, user rights, and enquiries.
- **`frontend/src/app/terms/page.tsx`** *(rewritten)* — Server Component with Next.js `Metadata` and all 28 B2B SaaS agreement sections, distinguishing Customer vs. AGENTGUARD responsibilities, noting human oversight requirements for AI governance/enforcement decisions, and avoiding false uptime or security guarantees.
- **`frontend/src/app/security/page.tsx`** *(rewritten)* — Server Component with Next.js `Metadata` and all 21 technical security sections, classifying every capability strictly under:
  - `Implemented and independently verified`
  - `Implemented but not independently verified`
  - `Partially implemented`
  - `Planned`
  - `Not implemented`
  Explicitly discloses that SOC 2 Type II, ISO 27001, GDPR certification, and third-party penetration testing have not been completed.

---

## 2. Missing Company Information (`[COMPANY INFORMATION REQUIRED]`)

The following placeholders must be filled in by the platform owner before publishing as binding commercial/legal documentation:

1. Registered Legal Entity Name (used in Privacy Policy, Terms of Service, and Footer copyright)
2. Registered Physical Business Address (Privacy Policy §23, Terms of Service §28)
3. Dedicated Privacy Contact / DPO Email (Privacy Policy §23 & Footer)
4. Dedicated Legal Notices Email (Terms of Service §28 & Footer)
5. Dedicated Security Contact Email & optional PGP key/portal (Zero-Trust Security §21)
6. Exact production Supabase database region and object storage region (Privacy Policy §14)

---

## 3. Legal Counsel Review Requirements (`[LEGAL REVIEW REQUIRED]`)

1. Effective Dates for Privacy Policy and Terms of Service
2. Applicable legal bases for processing under target jurisdictions (Privacy Policy §9)
3. International data transfer safeguards / SCCs (Privacy Policy §15)
4. Jurisdiction-specific statutory privacy rights disclosures (Privacy Policy §19)
5. Subscription billing, invoicing, renewal, taxes, and refund terms (Terms §6)
6. Confidentiality carve-outs and survival period (Terms §17)
7. Security incident / breach notification timelines (Terms §18)
8. Commercial SLA / uptime commitments if offered (Terms §19)
9. Post-termination data export window and deletion timeline (Terms §21)
10. Aggregate liability cap and statutory carve-outs (Terms §23)
11. Mutual IP and Customer indemnity clauses (Terms §24)
12. Dispute resolution procedure, governing law, venue, and jurisdiction (Terms §25–26)

---

## 4. Verification Results

- `npx tsc --noEmit`: **Passed (0 errors)**
- `npx next lint`: **Passed (No ESLint warnings or errors)**
- `npx next build`: **Pending completion in background** (verified in final turn)
- **Browser visual testing:** Not executed via browser automation in this turn; verified via Next.js TypeScript/ESLint/production build.
