# AGENTGUARD — Registration OTP Delivery Investigation & Fix Report

**Date:** 2026-11-27  
**Workspace:** `D:\AGENTGUARD` (local only — no commits, pushes, deployments, or production secret changes)

---

## 1. Exact Root Cause

Two compounding defects caused recipients not to receive registration OTP emails while the UI reported success:

1. **Sender Domain Restriction (`onboarding@resend.dev`):**
   - `backend/.env` (and `backend/.env.example` / `backend/config.py`) sets `RESEND_FROM_EMAIL='AgentGuard <onboarding@resend.dev>'` with `EMAIL_PROVIDER='RESEND'`.
   - Resend's `onboarding@resend.dev` sandbox sender **only permits delivery to the Resend account owner's own email address**. Any registration attempt by another recipient is rejected by Resend with **HTTP 403 (`validation_error`)** requiring a verified sending domain.
2. **Fire-and-Forget `BackgroundTasks` Swallowed Delivery Failures:**
   - `backend/routers/auth.py` (`register_request_otp`, `login_request_otp`, `forgot_password_request_otp`) used `background_tasks.add_task(email_service.send_otp_email, ...)` and immediately returned HTTP `200 OK` with `status="SUCCESS"` (*"a 6-digit verification code has been sent"*) and recorded `AuditLog(result="DISPATCHED")` **before** Resend was even called.
   - When Resend rejected the request (403 recipient restriction, 401 invalid key, 422 invalid sender, 5xx, timeout, or `EMAIL_PROVIDER=NONE`), the failure happened silently in the background and the frontend falsely displayed a green success banner.
3. **Deployment Config Gap (`render.yaml`):**
   - `render.yaml` did not declare `EMAIL_PROVIDER`, `RESEND_API_KEY`, or `RESEND_FROM_EMAIL` in `envVars`, meaning Render deployments without manual dashboard overrides default to `EMAIL_PROVIDER=NONE`.

---

## 2. Files Modified

- `backend/schemas.py` — Added optional `delivery_status`, `correlation_id`, and `provider_message_id` fields to `OtpActionResponse`.
- `backend/services/email_service.py` — Added `correlation_id`, UTC timestamp, sender email validation, Resend HTTP error classification (`RECIPIENT_RESTRICTED`, `UNVERIFIED_SENDER_DOMAIN`, `INVALID_API_KEY`, `INVALID_SENDER`, `RESEND_5XX`, `NETWORK_TIMEOUT`), bounded retry ONLY on transient 5xx/network errors (never retrying 4xx to prevent duplicate emails), 10s request timeout, and `resend_sandbox_mode` in `get_status()`. Never logs `RESEND_API_KEY` or OTP codes.
- `backend/routers/auth.py` — Added `_dispatch_otp_and_build_response(...)` and replaced background fire-and-forget dispatch in `register_request_otp`, `login_request_otp`, and `forgot_password_request_otp` with synchronous verified dispatch. Preserves the valid OTP challenge in DB even if email delivery fails, and returns HTTP `503` (missing provider config) or `502` (provider rejection / transient failure) with correlation ID.
- `frontend/src/app/(auth)/register/page.tsx` — Added clear UI feedback for accepted-for-sending, unconfirmed delivery (amber warning), missing provider config / sending failed (red error), active resend cooldown countdown synced from 429 responses, OTP expiry errors, and OTP verification success.
- `backend/tests/test_otp_resend_delivery.py` *(new)* — 13 mocked Resend tests covering every failure, retry, cooldown, anti-enumeration, and end-to-end verification scenario without sending real emails.

---

## 3. Whether Resend Accepted / Delivered the Email

- **Did Resend accept the email for arbitrary recipients?** **No** when using `onboarding@resend.dev` (Resend rejects external recipients with HTTP 403).
- **Was the email delivered?** **No** for external recipients under `onboarding@resend.dev`. Even when Resend returns HTTP `200` with an email `id`, that confirms **acceptance for sending** (`delivery_stage="ACCEPTED_BY_PROVIDER"`), not final inbox delivery.
- **Note on Production Render / Resend Logs:** `render` CLI and Resend dashboard API logs were not accessible from this local workspace; no production environment variables or secrets were modified or printed.

---

## 4. Automated Test Results

Command:
```powershell
pytest tests/test_otp_resend_delivery.py tests/test_authentication_and_otp_flows.py tests/test_notification_alerting_engine.py tests/test_tenant_isolation_and_security_audit.py -v --tb=short
```
Result: **63 passed, 0 failed** (59.67s), including all **13/13** new mocked Resend delivery tests (`test_otp_resend_delivery.py`) and all **24/24** existing auth/OTP flow tests (`test_authentication_and_otp_flows.py`).

---

## 5. Exact Environment Configuration Required & Verified Domain

- **Is a verified sending domain required?** **Yes.** To send registration OTP emails to arbitrary user email addresses via Resend, you **must** verify a custom domain in Resend (`resend.com/domains`) and set `RESEND_FROM_EMAIL` to an address on that verified domain (e.g., `AgentGuard <noreply@yourdomain.com>`). `onboarding@resend.dev` cannot deliver to external registration users.
- **Required backend environment variables (Render `agentguard-backend`):**
  - `EMAIL_PROVIDER=RESEND`
  - `RESEND_API_KEY=<your-resend-api-key>`
  - `RESEND_FROM_EMAIL=AgentGuard <noreply@your-verified-domain.com>`

---

## 6. Remaining Blockers for Live Registration OTP Delivery

1. **Verify a sending domain in Resend** and update `RESEND_FROM_EMAIL` in Render production environment variables (and local `.env` if testing against non-owner addresses).
2. **Confirm `EMAIL_PROVIDER=RESEND` and `RESEND_API_KEY` are set in Render** for `agentguard-backend`.
3. **Deploy** the updated backend and frontend after review/commit.
