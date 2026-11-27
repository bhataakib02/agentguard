# AGENTGUARD — Notification & System Health Regression Report

**Audit Date**: 2026-11-27  
**Suite**: `backend/tests/test_notification_alerting_engine.py` (**15/15 PASSED** in `22.54s`; verified within full **752-test** suite with 0 failures)

---

## 1. Notification Subsystem End-to-End Verification

### Inspected Components
- **Backend**: `backend/routers/notifications.py`, `backend/services/notification_service.py`, `backend/services/email_service.py`, `backend/routers/platform.py`, `backend/routers/approvals.py`, `backend/routers/security.py`, `backend/routers/agents.py`, `backend/routers/decisions.py`, `backend/routers/reports.py`, `backend/tasks/webhook_tasks.py`, `backend/tasks/escalation_tasks.py`, `backend/tasks/notification_tasks.py`, `backend/services/runtime_telemetry_service.py`.
- **Frontend**: `frontend/src/components/ui/DashboardHeader.tsx`, `frontend/src/app/platform/layout.tsx`, `frontend/src/app/(app)/notifications/page.tsx`, `frontend/src/app/platform/health/page.tsx`.

### Verification Checklist

| Requirement | Verified Behavior | Code Reference | Test Evidence |
|---|---|---|---|
| **PostgreSQL Persistence** | Notifications persisted to `notifications` (`models.Notification`) via `create_in_app_notification`. | `backend/services/notification_service.py` | `test_01_create_in_app_notification` |
| **Real Unread Counts** | `GET /notifications/unread-count` queries live `Notification.is_read == False` rows; headers & page consume real count. | `backend/routers/notifications.py`, `DashboardHeader.tsx`, `platform/layout.tsx` | `test_03_unread_count_endpoint` |
| **User Isolation & IDOR Protection** | Non-`SUPER_ADMIN` reads, `PATCH /{id}/read`, `DELETE /{id}` enforce `Notification.user_id == current_user.id` and return `403` on cross-user access; `read-all` for `SUPER_ADMIN` isolated to own/`None` rows. | `backend/routers/notifications.py` | `test_02`, `test_04`, `test_06`, `test_12`, `test_tenant_isolation_and_security_audit.py::test_05` |
| **Mark Read / Mark All / Delete / Filter / Pagination** | `PATCH /{id}/read`, `POST /read-all`, `DELETE /{id}`, `limit`, `offset`, `unread_only`, `severity`, `type` filters verified; `/notifications` UI implements `limit=20`/`offset` pagination + filter tabs. | `backend/routers/notifications.py`, `(app)/notifications/page.tsx` | `test_04`, `test_05`, `test_06`, `test_12`, `test_13` |
| **Governance Event Sinks** | Verified live emitters across approval action (`approvals.py`), security incident create/update/resolve (`security.py`), agent suspend/restore (`agents.py`), auto-suspend (`runtime_telemetry_service.py`), decisions (`decisions.py`), reports (`reports.py`), and dead-letter webhooks (`webhook_tasks.py`). | `approvals.py`, `security.py`, `agents.py`, `webhook_tasks.py` | `test_14`, `test_15` |
| **Email Fault Isolation & Truthful Status** | Disabled/failing email never blocks in-app notification persistence; `email_service.send_email` & `get_status()` truthfully return `EMAIL_PROVIDER_NOT_CONFIGURED` / `EMAIL_DELIVERY_FAILED` / `NOT_CONFIGURED`. | `backend/services/email_service.py`, `backend/services/notification_service.py` | `test_07`, `test_phase6c_truthfulness.py::test_22` |
| **Retry Deduplication** | `dispatch_webhook_task` skips `SUCCESS`, `DELIVERED`, and `DEAD_LETTER`; `escalate_approvals_task` checks 24h audit log before re-notifying. | `backend/tasks/webhook_tasks.py:42`, `backend/tasks/escalation_tasks.py` | `test_15` |
| **Polling Efficiency** | `DashboardHeader.tsx` and `platform/layout.tsx` poll once every `60000ms` (1 req/min per pair, cleared on unmount) via `/notifications?limit=15` and `/notifications/unread-count`. | `DashboardHeader.tsx`, `platform/layout.tsx` | Inspected & compiled cleanly |

---

## 2. Bugs Found & Remediated During This Audit

1. **`restore_agent` emitted wrong event (`backend/routers/agents.py:411-424`)**: Copy-paste from `suspend_agent` emitted `event_type="agent.suspended"` and `"Agent Suspended: ..."` (`WARNING`). Fixed to `event_type="agent.restored"` and `"Agent Restored: ..."` (`INFO`).
2. **`update_incident` emitted wrong event (`backend/routers/security.py:291-306`)**: Copy-paste from `create_incident` emitted `"security.incident_created"` using `current_user.org_id`. Fixed to `security.incident_resolved` / `security.incident_updated` using `inc.org_id` and appropriate severity.
3. **`SUPER_ADMIN` bulk `read-all` crossed tenants (`backend/routers/notifications.py:116-123`)**: `mark_all_notifications_read` omitted filtering for `SUPER_ADMIN`, marking all tenants' unread notifications read. Scoped `SUPER_ADMIN` to `(user_id == current_user.id) | (user_id.is_(None))`.
4. **`webhook_tasks.py` created orphaned `user_id=None` notifications & didn't guard `DEAD_LETTER` (`backend/tasks/webhook_tasks.py:42,232-244`)**: Added `DEAD_LETTER` to idempotency guard and routed webhook failure notifications through `notify_governance_event(org_id=str(endpoint.org_id), ...)` so org admins receive user-scoped alerts compatible with RLS.
5. **`/platform/health` overall status ignored unconfigured email & in-app outage (`backend/routers/platform.py:1166-1180`)**:
   - Returned `overall_status = "Operational"` even when `notif_status == "Degraded"`.
   - Returned `overall_status = "Degraded"` even when `notif_status == "Down"`.
   - Unprotected `AuditLog` query threw 500 when DB was down.
   - Remediated to return strict three-state semantics (`Operational`, `Degraded`, `Down`) matching `platform/health/page.tsx` badges, icons, and descriptions.
6. **Pytest module-import `app.dependency_overrides[get_db]` collisions (`test_notification_alerting_engine.py`, `test_tenant_isolation_and_security_audit.py`, `test_tool_proxy_suite.py`)**: Isolated `get_db` overrides inside module/function fixtures with save-and-restore instead of module-level mutation or `.clear()`, eliminating 9 cross-file ordering failures.

---

## 3. System Health Matrix (`/api/v1/platform/health` + `/platform/health`)

| Scenario | Backend `overall_status` | Card `s8` Status & Telemetry | Frontend Display | Verified By |
|---|---|---|---|---|
| DB + In-App OK + Email Configured (`MOCK`/`RESEND`/`SMTP`) | `Operational` | `Operational` (`Active`) | Green pill + `CheckCircle` icon + description | `test_09_system_health_operational_when_email_configured` |
| DB + In-App OK + Email Disabled/Unconfigured | `Degraded` | `Degraded` (`In-App Active`) | Amber pill + `AlertTriangle` icon + `"In-app notifications active; outbound email delivery provider not configured in environment"` | `test_08_system_health_degraded_when_email_not_configured` |
| DB Down or `notifications` table unavailable | `Down` | `Down` (`Failed`) | Red pill + `XCircle` icon + `"In-app notifications database store is unreachable"` (`"UNAVAILABLE"` if API fetch fails) | `test_11_system_health_down_when_db_unavailable` |
