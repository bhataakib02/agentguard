# AGENTGUARD — Notification & Alerting Engine Repair Audit Report

**Audit Date**: 2026-11-25  
**Auditor**: Senior Full-Stack Engineer, Backend Architect & Security Auditor  
**Subsystem**: Notification & Alerting Engine & System Health Subsystem  
**Status**: **VERIFIED & FULLY OPERATIONAL**

---

## 1. Executive Summary

An exhaustive investigation and remediation of AGENTGUARD's Notification & Alerting Engine was conducted. Prior to this remediation, the Notification & Alerting Engine displayed **NOT CONFIGURED** in red on the System Health dashboard (`/platform/health`), despite the presence of operational database-backed in-app notification infrastructure.

Following our investigation:
1. The exact root cause of the incorrect red status was identified in `backend/routers/platform.py`.
2. The notification subsystem was upgraded to an enterprise multi-state health model (`OPERATIONAL`, `DEGRADED`, `NOT CONFIGURED`, `DOWN`) reflecting real database ping latencies and active provider states.
3. In-app notifications were reinforced with pagination, category/severity filtering, individual read toggles, bulk read-all, dismissal/deletion, and real-time unread count badges.
4. The navbar notification bell on both tenant workspace (`DashboardHeader.tsx`) and Platform Control Center (`platform/layout.tsx`) was repaired to display truthful unread badges, timestamps, event categories, and interactive mark-read controls.
5. In-app notifications were integrated into real application lifecycles across approvals, security incidents, agent status changes, and webhook delivery failures.
6. Automated test suite `test_notification_alerting_engine.py` (10/10 tests passing) verified all invariants without any regression across existing suites (59/59 passing).

---

## 2. Root Cause Analysis

### Identified Root Cause
In `backend/routers/platform.py` (lines 1073 and 1086), the notification health check was implemented as:
```python
smtp_configured = bool(os.getenv("SMTP_HOST") or os.getenv("SENDGRID_API_KEY"))
...
{"id": "s8", "name": "Notification & Alerting Engine", "category": "Alerts", "status": "Operational" if smtp_configured else "Not Configured", ...}
```

### Critical Flaws Identified:
1. **Ignored Core In-App Notifications**: The check completely ignored `models.Notification` and `services.notification_service`. In-app governance alerts and incident tracking are the foundational notification layer for AGENTGUARD tenants.
2. **Ignored Resend REST API Gateway**: The application's canonical transactional email abstraction (`services.email_service`) supports Resend (`RESEND_API_KEY`), SMTP, and Mock providers. The health check only inspected `SMTP_HOST` or `SENDGRID_API_KEY`, completely missing Resend API keys.
3. **Binary State Instead of Multi-State Semantics**: The engine forced a binary choice between "Operational" and "Not Configured". When external email was not provisioned, it reported the entire engine as red "Not Configured", even though in-app notifications were 100% active.
4. **Hardcoded Response Latencies**: Subsystem latency was calculated via artificial arithmetic (`latency_ms + 2`), rather than measuring real round-trip execution against the database notification table.

---

## 3. Remediation & Architectural Implementation

### A. Truthful Multi-State Subsystem Health Logic
In `backend/routers/platform.py`, `get_detailed_system_health` now executes a real live query against `models.Notification`, measures actual database execution latency via `time.perf_counter()`, and evaluates provider readiness via `email_service.get_status()`:

- **OPERATIONAL (Green)**: Core in-app notification table is responsive AND outbound email delivery (Resend / SMTP / Mock) is configured and healthy.
- **DEGRADED (Amber)**: Core in-app notifications are responsive, but optional outbound email provider is not provisioned in the environment. Detailed reason truthfully states: `"In-app notifications active; outbound email delivery provider not configured in environment"`.
- **DOWN (Red)**: Database store for notifications is unreachable or throwing errors. Detailed error reason is captured.
- **NOT CONFIGURED (Red)**: Required notification configuration is genuinely missing.

### B. Notification Router Capabilities (`backend/routers/notifications.py`)
- `GET /notifications`: Supports `limit`, `offset`, `unread_only`, `severity`, and `type` query filters. Strictly enforces user-level tenant isolation for non-SUPER_ADMIN users.
- `GET /notifications/unread-count`: Returns real database-backed count `{"unread_count": <int>}` for navbar badge polling.
- `GET /notifications/{id}`: Returns single notification record with ownership checks (403 if accessing another user's alert).
- `PATCH /notifications/{id}/read`: Atomically sets `is_read = True` with ownership verification.
- `POST /notifications/read-all`: Atomically marks all unread notifications for the caller as read.
- `DELETE /notifications/{id}`: Dismisses/deletes notification with ownership checks.

### C. Frontend Navbar Integration
- **`DashboardHeader.tsx`**:
  - Unread badge reflects truthful unread count from `notifications.filter((n) => !n.is_read && !n.read).length`.
  - Dropdown renders severity tags (`CRITICAL`, `HIGH`, `WARNING`, `INFO`), event title, preview message, and relative/local timestamp.
  - "Mark all read" header button calls `POST /notifications/read-all`.
  - Clicking any unread notification calls `PATCH /notifications/${id}/read`.
  - "View All Notifications" footer link navigates directly to `/notifications`.
- **`platform/layout.tsx`**:
  - Badge is hidden when unread count is 0; displays formatted count when unread alerts exist.
  - Interactive dropdown with mark-all-read and click-to-read capabilities.

### D. Full-Featured Notifications Page (`(app)/notifications/page.tsx`)
- Interactive filter tabs: "All", "Unread", "Critical & High", and "Approvals".
- Batch "Mark all as read" button.
- Per-item "Mark read" and "Dismiss" controls.
- Live empty states distinguishing zero unread items from zero total records.

### E. Real Application Event Sinks
In-app notifications are now automatically generated across real platform events:
1. **Approval Requests**: When approvals are generated (`decisions.py`) and when decisions are approved/rejected (`approvals.py`).
2. **Security Incidents**: When incidents are created or resolved (`security.py`).
3. **Agent State Transitions**: When agents are suspended or quarantined (`agents.py`).
4. **Integration Failures**: When webhook dispatch exhausts retry limits and dead-letters (`tasks/webhook_tasks.py`).
5. **Scheduled Reports**: When background reports complete (`reports.py`).

---

## 4. Test Evidence & Verification Matrix

Automated verification suite `backend/tests/test_notification_alerting_engine.py` was executed:

| Test Case | Scenario Verified | Result |
|---|---|---|
| `test_01_create_in_app_notification` | In-app notification creation & persistence in database | **PASS** |
| `test_02_list_notifications_and_user_isolation` | User A cannot view User B notifications (strict isolation) | **PASS** |
| `test_03_unread_count_endpoint` | Database-backed unread count endpoint | **PASS** |
| `test_04_mark_single_notification_read` | Individual mark read & IDOR 403 prevention | **PASS** |
| `test_05_mark_all_notifications_read` | Bulk mark all read updates count to 0 | **PASS** |
| `test_06_delete_notification_and_idor_protection` | Deletion/dismissal with cross-user IDOR protection | **PASS** |
| `test_07_in_app_notifications_work_when_email_disabled` | Full in-app functionality when email provider is disabled | **PASS** |
| `test_08_system_health_degraded_when_email_not_configured` | System Health reports DEGRADED (amber) when email unset | **PASS** |
| `test_09_system_health_operational_when_email_configured` | System Health reports OPERATIONAL (green) when email set | **PASS** |
| `test_10_unauthorized_access_rejected` | Unauthenticated requests rejected with 401 | **PASS** |

**Regression Test Execution**:
- `test_phase6c_truthfulness.py`: 26/26 PASSED
- `test_phase6d_infrastructure.py`: 30/30 PASSED
- `test_webhook_encryption_verification.py`: 3/3 PASSED
- Total: 69/69 PASSED (100% Green).
