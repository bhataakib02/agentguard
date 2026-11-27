# AGENTGUARD — Final Application-Wide Dummy Data Inventory & Classification

**Audit Date**: 2026-11-27  
**Coverage**: All routes in `frontend/src/app/(app)/*`, `frontend/src/app/platform/*`, `frontend/src/app/(auth)/*`, `frontend/src/app/page.tsx`, shared UI components (`DashboardHeader.tsx`), and all FastAPI routers in `backend/routers/*`.

---

## 1. Classification Key

1. **Genuine Production Data**: Derived from live SQLAlchemy/PostgreSQL queries or environment introspection.
2. **Explicit Demo / Sample Data**: Clearly scoped marketing visuals, sandbox/dry-run simulation presets, or explicit sandbox endpoints.
3. **Test Fixture**: Isolated unit/integration test data or test-mode mocks gated against `ENVIRONMENT == "production"`.
4. **Placeholder or Dummy Implementation**: Hardcoded UI values, fake deltas, fallback static dates/numbers, or unbacked actions on live authenticated routes (**FIXED** in this audit).
5. **Unused Code**: Dead/broken internal route links or unreferenced UI artifacts (**FIXED** where user-facing).

---

## 2. Category (4) & (5) Findings Remediated During This Audit

| File | Original Finding | Classification | Fix Applied |
|---|---|---|---|
| `frontend/src/app/platform/page.tsx` | Hardcoded KPI fallbacks (`?? 5`, `?? 40`, `?? 25`, `?? 12`, `?? 3`), hardcoded `1` Expiring License, hardcoded `1,248` Audit Events, hardcoded `78%` Usage, fake `vs last 30 days` deltas, static `May 4..Jun 3` SVG paths, static `5 (100%)` Org Donut, static `4 (80%)` / `1 (20%)` License Health, static `1`/`3`/`24`/`7`/`2` Security Overview, `"2026-08-31"` expiry fallback, `alert("Exporting...")` placeholder button. | **4 (Placeholder/Dummy)** | Bound every KPI & panel to live `/platform/overview`, `/analytics/overview`, and `/analytics/time-series`; replaced `alert` with real PDF download from `/reports/export/pdf?type=executive`. |
| `frontend/src/app/platform/risk/page.tsx` | Hardcoded `38.4 / 100`, `2` High Risk Agents, `?? 7` Critical Factors, `98.2%` / `↑ 0.5% vs 30d` Safety Compliance Rate, index-hardcoded org scores (`idx === 0 ? 42 : idx === 1 ? 68 : 25 : 18`). | **4 (Placeholder/Dummy)** | Computed live from `/platform/security`, `/platform/agents`, and `/analytics/overview`; shows `N/A` / `0` when empty. |
| `frontend/src/app/platform/security/page.tsx` | Fabricated deltas (`↓ 1 vs last 30d`, `↓ 2 vs last 30d`, `↑ 8 vs last 30d`), static `LOW RISK PROFILE`, hardcoded `0.032 (Low)`. | **4 (Placeholder/Dummy)** | Removed fake deltas; bound Risk Score & Profile tier directly to live `riskScore`. |
| `frontend/src/app/platform/health/page.tsx` | Error fallback `"OPERATIONAL"` when `healthData` missing, `<CheckCircle />` always rendered even for `DEGRADED`/`DOWN`, hardcoded `"Just now"` timestamp. | **4 (Placeholder/Dummy)** | Defaults to `"UNAVAILABLE"` when API fails; status-aware icons; displays formatted `srv.last_checked`. |
| `frontend/src/app/platform/layout.tsx` | Hardcoded `"Last Login: Sep 1, 2026 10:24 AM"`, unread count lacked `/notifications/unread-count` sync/polling, fixed `w-64` sidebar overlapped left edge of `<footer>` (`SUPER_ADMIN` clipped), bright native scrollbar & inactive icon styling in nav. | **4 (Placeholder/Dummy)** | Removed hardcoded date; synced `/notifications/unread-count` with 60s poll; added `lg:pl-[280px]` to footer and slim dark scrollbar + active icon highlights. |
| `frontend/src/app/platform/profile/page.tsx` | Hardcoded `"Enforced (Hardware/TOTP)"`, `"sa-00000-00000-00000"`, `"Sep 1, 2026 10:24 AM"`, `"Aug 1, 2026"`. | **4 (Placeholder/Dummy)** | Bound to `profile.id`, `profile.mfa_enabled`, `profile.last_login_at`, and `profile.created_at` with truthful fallbacks. |
| `frontend/src/app/platform/settings/page.tsx` & `backend/routers/platform.py` | Unbacked `Save Settings` toast (`Platform configuration updated successfully!`), hardcoded green `ACTIVE` notification badges, `platform.py:get_platform_settings` ignored Resend/`email_service`. | **4 (Placeholder/Dummy)** | Connected `get_platform_settings` to `email_service.is_configured()`, rendered truthful `CONFIGURED`/`NOT_CONFIGURED` badges, replaced fake Save button with explicit read-only backend sync view. |
| `frontend/src/app/platform/billing/page.tsx` | Fallback `"2026-08-31"` on license expiry column. | **4 (Placeholder/Dummy)** | Changed fallback to `"No expiry"`. |
| `frontend/src/app/platform/governance/page.tsx` | Fallback `p.rules_count ?? 3`, `"2026-08-15"`, `"2026-09-02"`. | **4 (Placeholder/Dummy)** | Changed fallbacks to `0` and `"—"`. |
| `frontend/src/app/platform/organizations/page.tsx` | Fallback `"Aug 31, 2026"` on `created_at`. | **4 (Placeholder/Dummy)** | Changed fallback to `"—"`. |
| `frontend/src/app/(app)/profile/page.tsx` | Fallback `"31 Aug 2026"` on `created_at`. | **4 (Placeholder/Dummy)** | Changed fallback to `"—"`. |
| `frontend/src/app/(app)/settings/page.tsx` | Local notification toggles had no backend persistence disclosure. | **4 (Placeholder/Dummy)** | Labeled toggles explicitly as local session display preferences (all org alerts remain persisted). |
| `frontend/src/app/(app)/dashboard/page.tsx` | Button linked to nonexistent `/agents/create` route; active agent counter filtered `status === "ACTIVE"` while agents default to `"NORMAL"`. | **5 / 4 (Broken Route & Filter Bug)** | Pointed button to `/agents`; matched `a.status === "NORMAL" \|\| a.status === "ACTIVE"`. |

---

## 3. Verified Non-Placeholder Components (Categories 1, 2, 3)

### Category 1 — Genuine Production Data (Verified Clean)
- **Analytics & Economics**: `(app)/analytics/page.tsx`, `platform/analytics/page.tsx`, `(app)/economics/page.tsx`, `backend/routers/analytics.py`, `backend/routers/economics.py` (all SQL counts/averages/sums).
- **Decisions, Approvals, Policies, Provenance, IAM, Audit, Agents, Risk**: `(app)/decisions/page.tsx`, `platform/decisions/page.tsx`, `(app)/approvals/page.tsx`, `(app)/policies/page.tsx`, `(app)/provenance/page.tsx`, `(app)/iam/page.tsx`, `(app)/iam/role-history/page.tsx`, `(app)/audit/page.tsx`, `platform/audit/page.tsx`, `(app)/agents/*`, `(app)/risk/page.tsx`, `backend/routers/risk.py`.
- **Integrations, Billing, Reports, Assistant**: `platform/integrations/page.tsx`, `backend/routers/integrations.py`, `backend/routers/billing.py`, `(app)/reports/*`, `platform/reports/page.tsx`, `(app)/assistant/page.tsx`.
- **Note**: `(app)/agent-network/page.tsx` computes node risk metrics dynamically from DB agents/decisions, and computes SVG node positions deterministically from agent list index/radius (layout geometry, not synthetic operational data).

### Category 2 — Explicit Demo / Sample Data (Preserved Intentionally)
- `frontend/src/app/page.tsx` (lines ~440+): Public marketing landing page illustrative product preview mockup on unauthenticated route `/`.
- `backend/routers/billing.py` (`SimulatePaymentRequest` / sandbox checkout mode): Explicitly separated `SANDBOX` mode vs `LIVE` Stripe/Razorpay gateways via `_get_gateway_status()`.
- `(app)/simulation/page.tsx`, `(app)/red-team/page.tsx`, `(app)/digital-twin/page.tsx`: Interactive scenario/stress-test simulators executing real backend policy/PACE evaluations against scenario inputs.

### Category 3 — Test Fixtures & Test-Mode Mocks (Preserved Intentionally)
- `backend/services/email_service.py`: `EMAIL_PROVIDER == "MOCK"` in-memory sink used only in automated tests (`test_09`, etc.).
- `backend/services/tool_proxy_service.py` & `backend/services/sandbox_service.py`: Deterministic test workers guarded away from production paths (`ENVIRONMENT == "production"` startup checks in `backend/config.py`).
- `backend/tests/*`: Isolated SQLite and PostgreSQL test fixtures.
