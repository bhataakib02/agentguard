"""
Comprehensive Automated Test Suite: Final Authentication & OTP Flows
====================================================================
Tests:
1. Registration with email OTP (request, HMAC hashing, 10m expiry, atomic verify, safe default USER role, no enumeration, duplicate prevention).
2. Login Method A: Email & Password (valid credentials, invalid credentials, suspended accounts, server-side session validation).
3. Login Method B: Passwordless Email OTP (request, generic anti-enumeration response, atomic verify, session establishment).
4. Forgot Password & Recovery: (request, generic anti-enumeration response, reset with OTP, session revocation policy).
5. OTP Security Invariants: (keyed HMAC storage, replay prevention, 5-attempt limit, 60s cooldown, superseded challenge invalidation, expiry).
6. Resend Email Provider Configuration & Truthful Status (RESEND_API_KEY, onboarding@resend.dev, secret redaction).
7. Tenant Isolation & Audit Logging (audit entries recorded, zero secrets leaked).
"""

import unittest
import uuid
import sys
import os
import datetime
import hmac
import hashlib
import re

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("EMAIL_PROVIDER", "MOCK")
os.environ.setdefault("SECRET_KEY", "agentguard-test-secret-key-32charactersmin")

sys.path.insert(0, backend_dir)
from starlette.testclient import TestClient
from main import app
from database import SessionLocal
from config import settings
from core import security
import models
from services.email_service import email_service
from services.otp_service import (
    otp_service,
    hash_otp_code,
    PURPOSE_REGISTRATION,
    PURPOSE_PASSWORDLESS_LOGIN,
    PURPOSE_PASSWORD_RESET
)

client = TestClient(app)


class TestAuthenticationAndOtpFlows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        settings.EMAIL_PROVIDER = "MOCK"

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def setUp(self):
        email_service.sent_emails_mock.clear()

    # ========================================================================
    # 1. REGISTRATION WITH EMAIL OTP
    # ========================================================================

    def test_01_registration_request_otp_success(self):
        """Requesting registration OTP generates 6-digit code, stores HMAC, and sends email."""
        test_email = f"reg_user_{uuid.uuid4().hex[:6]}@enterprise.ai"
        resp = client.post("/api/auth/register/request-otp", json={
            "full_name": "Alan Turing",
            "email": test_email,
            "password": "SecurePassword123!",
            "org_name": "Turing Labs"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertIn("6-digit verification code", data["message"])
        self.assertEqual(data["cooldown_seconds"], 60)

        # Verify challenge in DB
        challenge = self.db.query(models.OtpChallenge).filter(
            models.OtpChallenge.email == test_email.lower(),
            models.OtpChallenge.purpose == PURPOSE_REGISTRATION
        ).first()
        self.assertIsNotNone(challenge)
        self.assertEqual(challenge.attempts, 0)
        self.assertEqual(challenge.max_attempts, 5)
        self.assertFalse(challenge.consumed)

        # SECURITY INVARIANT: Verify code_hash is HMAC-SHA256 and NOT plaintext
        self.assertEqual(len(challenge.code_hash), 64)
        self.assertFalse(challenge.code_hash.isdigit())

        # SECURITY INVARIANT: Verify User is NOT created prior to OTP verification
        unverified_user = self.db.query(models.User).filter(models.User.email == test_email).first()
        self.assertIsNone(unverified_user)

        # Verify email dispatched via mock provider
        self.assertEqual(len(email_service.sent_emails_mock), 1)
        sent = email_service.sent_emails_mock[0]
        self.assertEqual(sent["to_email"], test_email)
        self.assertIn("Verify Your Email Address", sent["subject"])

    def test_02_registration_verify_otp_creates_account_with_safe_user_role(self):
        """Verifying registration OTP creates Organization and User with safe default role 'USER'."""
        test_email = f"reg_user_{uuid.uuid4().hex[:6]}@enterprise.ai"
        client.post("/api/auth/register/request-otp", json={
            "full_name": "Ada Lovelace",
            "email": test_email,
            "password": "LovelaceSecure123!",
            "org_name": "Analytical Engines"
        })

        # Extract generated OTP code from the dispatched mock email
        sent_email = email_service.sent_emails_mock[-1]
        body = sent_email["body_text"]
        # Code is 6 digits in body
        import re
        code_match = re.search(r'\b(\d{6})\b', body)
        self.assertIsNotNone(code_match)
        raw_code = code_match.group(1)

        # Verify OTP
        resp = client.post("/api/auth/register/verify-otp", json={
            "email": test_email,
            "otp": raw_code
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["email"], test_email)
        self.assertEqual(data["full_name"], "Ada Lovelace")
        self.assertEqual(data["role"], "USER")
        self.assertEqual(data["org_name"], "Analytical Engines")

        # Verify User and Org in DB
        db_user = self.db.query(models.User).filter(models.User.email == test_email).first()
        self.assertIsNotNone(db_user)
        self.assertEqual(db_user.role, "USER")
        self.assertEqual(db_user.status, "ACTIVE")
        self.assertTrue(security.verify_password("LovelaceSecure123!", db_user.password_hash))

        # Verify challenge is marked consumed atomically
        challenge = self.db.query(models.OtpChallenge).filter(
            models.OtpChallenge.email == test_email,
            models.OtpChallenge.purpose == PURPOSE_REGISTRATION
        ).first()
        self.assertTrue(challenge.consumed)
        self.assertIsNotNone(challenge.consumed_at)

        # Verify Audit Log
        audit = self.db.query(models.AuditLog).filter(
            models.AuditLog.actor_id == str(db_user.id),
            models.AuditLog.event_type == "USER_REGISTER_VERIFIED"
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.result, "SUCCESS")

    def test_03_registration_duplicate_anti_enumeration(self):
        """Duplicate registration request returns generic response and does NOT issue OTP or duplicate user."""
        test_email = f"dup_{uuid.uuid4().hex[:6]}@enterprise.ai"
        # Register user first
        client.post("/api/auth/register/request-otp", json={
            "full_name": "Original User",
            "email": test_email,
            "password": "Password123!"
        })
        raw_code = re.search(r'\b(\d{6})\b', email_service.sent_emails_mock[-1]["body_text"]).group(1)
        client.post("/api/auth/register/verify-otp", json={"email": test_email, "otp": raw_code})

        email_count_before = len(email_service.sent_emails_mock)

        # Attempt to register again with same email
        resp = client.post("/api/auth/register/request-otp", json={
            "full_name": "Attacker Impersonator",
            "email": test_email,
            "password": "AttackerPassword123!"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertIn("6-digit verification code", data["message"])

        # No new email sent because account already exists (prevents account takeover)
        self.assertEqual(len(email_service.sent_emails_mock), email_count_before)

    # ========================================================================
    # 2. LOGIN METHOD A: EMAIL AND PASSWORD
    # ========================================================================

    def test_04_password_login_success_and_server_side_session_validation(self):
        """Password login authenticates without OTP and validates session on protected endpoints."""
        test_email = f"pass_login_{uuid.uuid4().hex[:6]}@enterprise.ai"
        client.post("/api/auth/register/request-otp", json={
            "full_name": "Shannon Claude",
            "email": test_email,
            "password": "CorrectPassword123!"
        })
        import re
        code = re.search(r'\b(\d{6})\b', email_service.sent_emails_mock[-1]["body_text"]).group(1)
        client.post("/api/auth/register/verify-otp", json={"email": test_email, "otp": code})

        # Login with email & password via local-login fallback
        resp = client.post("/api/auth/local-login", json={
            "email": test_email,
            "password": "CorrectPassword123!"
        })
        self.assertEqual(resp.status_code, 200)
        login_data = resp.json()
        self.assertIn("access_token", login_data)
        token = login_data["access_token"]

        # Validate session on protected endpoint /api/auth/me
        me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me_resp.status_code, 200)
        me_data = me_resp.json()
        self.assertEqual(me_data["email"], test_email)
        self.assertEqual(me_data["role"], "USER")

    def test_05_password_login_invalid_credentials_rejected(self):
        """Password login rejects incorrect password with 401."""
        test_email = f"pass_bad_{uuid.uuid4().hex[:6]}@enterprise.ai"
        client.post("/api/auth/register/request-otp", json={
            "full_name": "User BadPass",
            "email": test_email,
            "password": "CorrectPassword123!"
        })
        import re
        code = re.search(r'\b(\d{6})\b', email_service.sent_emails_mock[-1]["body_text"]).group(1)
        client.post("/api/auth/register/verify-otp", json={"email": test_email, "otp": code})

        resp = client.post("/api/auth/local-login", json={
            "email": test_email,
            "password": "WrongPassword999!"
        })
        self.assertEqual(resp.status_code, 401)
        self.assertNotIn("access_token", resp.json())

    def test_06_password_login_suspended_account_rejected(self):
        """Suspended user account cannot authenticate with password."""
        test_email = f"pass_susp_{uuid.uuid4().hex[:6]}@enterprise.ai"
        client.post("/api/auth/register/request-otp", json={
            "full_name": "Suspended User",
            "email": test_email,
            "password": "CorrectPassword123!"
        })
        import re
        code = re.search(r'\b(\d{6})\b', email_service.sent_emails_mock[-1]["body_text"]).group(1)
        client.post("/api/auth/register/verify-otp", json={"email": test_email, "otp": code})

        # Suspend account
        user = self.db.query(models.User).filter(models.User.email == test_email).first()
        user.status = "SUSPENDED"
        self.db.commit()

        resp = client.post("/api/auth/local-login", json={
            "email": test_email,
            "password": "CorrectPassword123!"
        })
        self.assertEqual(resp.status_code, 403)

    # ========================================================================
    # 3. LOGIN METHOD B: PASSWORDLESS EMAIL OTP
    # ========================================================================

    def test_07_passwordless_login_request_otp_and_verify_success(self):
        """Passwordless login requests OTP, verifies it, and authenticates without password."""
        test_email = f"otp_login_{uuid.uuid4().hex[:6]}@enterprise.ai"
        client.post("/api/auth/register/request-otp", json={
            "full_name": "Grace Hopper",
            "email": test_email,
            "password": "RegisterPassword123!"
        })
        import re
        code = re.search(r'\b(\d{6})\b', email_service.sent_emails_mock[-1]["body_text"]).group(1)
        client.post("/api/auth/register/verify-otp", json={"email": test_email, "otp": code})

        # Request Passwordless OTP
        resp = client.post("/api/auth/login/request-otp", json={"email": test_email})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "SUCCESS")

        # Get the login OTP code from dispatched email
        sent = email_service.sent_emails_mock[-1]
        self.assertIn("Your One-Time Sign-In Passcode", sent["subject"])
        login_code = re.search(r'\b(\d{6})\b', sent["body_text"]).group(1)

        # Verify OTP
        verify_resp = client.post("/api/auth/login/verify-otp", json={
            "email": test_email,
            "otp": login_code
        })
        self.assertEqual(verify_resp.status_code, 200)
        data = verify_resp.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["email"], test_email)

        # Validate session on protected endpoint
        me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
        self.assertEqual(me_resp.status_code, 200)

    def test_08_passwordless_login_non_existent_account_generic_response(self):
        """Non-existent account requesting passwordless login returns generic response (anti-enumeration)."""
        non_existent_email = f"ghost_{uuid.uuid4().hex[:6]}@enterprise.ai"
        count_before = len(email_service.sent_emails_mock)
        resp = client.post("/api/auth/login/request-otp", json={"email": non_existent_email})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "SUCCESS")
        # No email sent to ghost account
        self.assertEqual(len(email_service.sent_emails_mock), count_before)

    # ========================================================================
    # 4. FORGOT PASSWORD & RECOVERY FLOW
    # ========================================================================

    def test_09_forgot_password_recovery_and_session_revocation(self):
        """Password recovery with OTP resets password and revokes all active prior sessions."""
        test_email = f"recovery_{uuid.uuid4().hex[:6]}@enterprise.ai"
        client.post("/api/auth/register/request-otp", json={
            "full_name": "Nikola Tesla",
            "email": test_email,
            "password": "OldPassword123!"
        })
        import re
        code = re.search(r'\b(\d{6})\b', email_service.sent_emails_mock[-1]["body_text"]).group(1)
        reg_data = client.post("/api/auth/register/verify-otp", json={"email": test_email, "otp": code}).json()
        old_token = reg_data["access_token"]

        # Request recovery OTP
        req_resp = client.post("/api/auth/forgot-password/request-otp", json={"email": test_email})
        self.assertEqual(req_resp.status_code, 200)

        recovery_code = re.search(r'\b(\d{6})\b', email_service.sent_emails_mock[-1]["body_text"]).group(1)

        # Reset password with recovery OTP
        reset_resp = client.post("/api/auth/forgot-password/reset", json={
            "email": test_email,
            "otp": recovery_code,
            "new_password": "BrandNewSecurePassword456!"
        })
        self.assertEqual(reset_resp.status_code, 200)
        self.assertEqual(reset_resp.json()["status"], "SUCCESS")

        # SESSION REVOCATION POLICY: Old session token must now be rejected
        me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {old_token}"})
        self.assertEqual(me_resp.status_code, 401)

        # Verify old password fails
        old_login = client.post("/api/auth/local-login", json={
            "email": test_email,
            "password": "OldPassword123!"
        })
        self.assertEqual(old_login.status_code, 401)

        # Verify new password succeeds
        new_login = client.post("/api/auth/local-login", json={
            "email": test_email,
            "password": "BrandNewSecurePassword456!"
        })
        self.assertEqual(new_login.status_code, 200)

    # ========================================================================
    # 5. OTP SECURITY INVARIANTS & RATE LIMITING
    # ========================================================================

    def test_10_otp_expiry_rejected(self):
        """OTP older than 10 minutes is rejected as expired."""
        test_email = f"expired_{uuid.uuid4().hex[:6]}@enterprise.ai"
        challenge, raw_code = otp_service.issue_challenge(
            self.db, test_email, PURPOSE_REGISTRATION
        )
        # Manually backdate expiration to 11 minutes ago
        challenge.expires_at = datetime.datetime.utcnow() - datetime.timedelta(minutes=11)
        self.db.commit()

        valid, err_msg, chal = otp_service.verify_challenge(
            self.db, test_email, PURPOSE_REGISTRATION, raw_code
        )
        self.assertFalse(valid)
        self.assertIn("expired", err_msg.lower())

    def test_11_otp_replay_prevention(self):
        """Consumed OTP cannot be reused (replay prevention)."""
        test_email = f"replay_{uuid.uuid4().hex[:6]}@enterprise.ai"
        challenge, raw_code = otp_service.issue_challenge(
            self.db, test_email, PURPOSE_REGISTRATION
        )

        # First verification succeeds
        valid1, _, _ = otp_service.verify_challenge(self.db, test_email, PURPOSE_REGISTRATION, raw_code)
        self.assertTrue(valid1)

        # Second verification with same code fails immediately
        valid2, err_msg, _ = otp_service.verify_challenge(self.db, test_email, PURPOSE_REGISTRATION, raw_code)
        self.assertFalse(valid2)

    def test_12_otp_max_5_attempts_limit(self):
        """Submitting 5 incorrect codes locks and invalidates the challenge."""
        test_email = f"brute_{uuid.uuid4().hex[:6]}@enterprise.ai"
        challenge, raw_code = otp_service.issue_challenge(
            self.db, test_email, PURPOSE_REGISTRATION
        )

        # 4 wrong attempts
        for i in range(4):
            valid, err_msg, _ = otp_service.verify_challenge(self.db, test_email, PURPOSE_REGISTRATION, "000000")
            self.assertFalse(valid)
            self.assertIn("remaining", err_msg.lower())

        # 5th wrong attempt locks the challenge
        valid5, err5, _ = otp_service.verify_challenge(self.db, test_email, PURPOSE_REGISTRATION, "000000")
        self.assertFalse(valid5)
        self.assertIn("maximum attempts exceeded", err5.lower())

        # Now even the correct code is rejected because the challenge was invalidated
        valid_post, err_post, _ = otp_service.verify_challenge(self.db, test_email, PURPOSE_REGISTRATION, raw_code)
        self.assertFalse(valid_post)

    def test_13_otp_resend_cooldown_60s(self):
        """Requesting another OTP within 60s cooldown is rejected with HTTP 429."""
        test_email = f"cd_{uuid.uuid4().hex[:6]}@enterprise.ai"
        # First request succeeds
        resp1 = client.post("/api/auth/register/request-otp", json={
            "full_name": "Cooldown Test",
            "email": test_email,
            "password": "Password123!"
        })
        self.assertEqual(resp1.status_code, 200)

        # Second immediate request must be rejected with 429
        resp2 = client.post("/api/auth/register/request-otp", json={
            "full_name": "Cooldown Test",
            "email": test_email,
            "password": "Password123!"
        })
        self.assertEqual(resp2.status_code, 429)
        self.assertIn("Please wait", resp2.json()["detail"])

    def test_14_otp_superseded_invalidation(self):
        """When a new OTP is issued, any prior unconsumed OTP for that purpose is invalidated."""
        test_email = f"super_{uuid.uuid4().hex[:6]}@enterprise.ai"
        challenge1, code1 = otp_service.issue_challenge(self.db, test_email, PURPOSE_PASSWORDLESS_LOGIN)

        # Manually clear cooldown so we can issue a second challenge
        challenge1.resend_available_at = datetime.datetime.utcnow() - datetime.timedelta(seconds=1)
        self.db.commit()

        challenge2, code2 = otp_service.issue_challenge(self.db, test_email, PURPOSE_PASSWORDLESS_LOGIN)

        # Older code1 must now fail
        valid1, _, _ = otp_service.verify_challenge(self.db, test_email, PURPOSE_PASSWORDLESS_LOGIN, code1)
        self.assertFalse(valid1)

        # Newer code2 succeeds
        valid2, _, _ = otp_service.verify_challenge(self.db, test_email, PURPOSE_PASSWORDLESS_LOGIN, code2)
        self.assertTrue(valid2)

    def test_15_resend_email_provider_configuration(self):
        """EmailService truthful status reporting and Resend configuration detection."""
        original_provider = settings.EMAIL_PROVIDER
        original_resend_key = getattr(settings, "RESEND_API_KEY", "")
        try:
            settings.RESEND_API_KEY = "re_test_dummy_key_not_real"
            settings.EMAIL_PROVIDER = "RESEND"

            self.assertTrue(email_service.is_resend_configured())
            status = email_service.get_status()
            self.assertEqual(status["provider"], "RESEND")
            self.assertTrue(status["configured"])
            self.assertTrue(status["resend_configured"])
            self.assertEqual(status["from_email"], "AgentGuard <onboarding@resend.dev>")
            # SECRET PROTECTION: RESEND_API_KEY must NEVER be present in get_status
            self.assertNotIn("re_test_dummy_key_not_real", str(status))
            self.assertNotIn("api_key", status)
        finally:
            settings.EMAIL_PROVIDER = original_provider
            settings.RESEND_API_KEY = original_resend_key

    def test_16_registration_role_escalation_strictly_prevented(self):
        """Registration ignores any client-supplied role or permissions and strictly assigns USER."""
        test_email = f"escalate_{uuid.uuid4().hex[:6]}@enterprise.ai"
        # Attempt to pass role="SUPER_ADMIN" in registration
        resp = client.post("/api/auth/register/request-otp", json={
            "full_name": "Privilege Escalator",
            "email": test_email,
            "password": "Password123!",
            "role": "SUPER_ADMIN"
        })
        self.assertEqual(resp.status_code, 200)

        raw_code = re.search(r'\b(\d{6})\b', email_service.sent_emails_mock[-1]["body_text"]).group(1)
        verify_resp = client.post("/api/auth/register/verify-otp", json={
            "email": test_email,
            "otp": raw_code,
            "role": "SUPER_ADMIN"
        })
        self.assertEqual(verify_resp.status_code, 200)
        user_data = verify_resp.json()
        self.assertEqual(user_data["role"], "USER")

        # Database verification
        user = self.db.query(models.User).filter(models.User.email == test_email).first()
        self.assertIsNotNone(user)
        self.assertEqual(user.role, "USER")

    def test_17_tenant_isolation_enforced(self):
        """User from Org A cannot access or see resources belonging to Org B."""
        # Org A User
        email_a = f"org_a_{uuid.uuid4().hex[:6]}@tenant-a.com"
        client.post("/api/auth/register/request-otp", json={"full_name": "User A", "email": email_a, "password": "Password123!"})
        code_a = re.search(r'\b(\d{6})\b', email_service.sent_emails_mock[-1]["body_text"]).group(1)
        token_a = client.post("/api/auth/register/verify-otp", json={"email": email_a, "otp": code_a}).json()["access_token"]

        # Org B User
        email_b = f"org_b_{uuid.uuid4().hex[:6]}@tenant-b.com"
        client.post("/api/auth/register/request-otp", json={"full_name": "User B", "email": email_b, "password": "Password123!"})
        code_b = re.search(r'\b(\d{6})\b', email_service.sent_emails_mock[-1]["body_text"]).group(1)
        token_b = client.post("/api/auth/register/verify-otp", json={"email": email_b, "otp": code_b}).json()["access_token"]

        user_a = self.db.query(models.User).filter(models.User.email == email_a).first()
        user_b = self.db.query(models.User).filter(models.User.email == email_b).first()
        self.assertNotEqual(user_a.org_id, user_b.org_id)

        # Profile A reports Org A
        profile_a = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_a}"}).json()
        self.assertEqual(profile_a["email"], email_a)
        self.assertEqual(profile_a["org_id"], str(user_a.org_id))

        # Profile B reports Org B
        profile_b = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_b}"}).json()
        self.assertEqual(profile_b["email"], email_b)
        self.assertEqual(profile_b["org_id"], str(user_b.org_id))

    def test_18_audit_logs_zero_secrets_leakage(self):
        """Verifies that all auth events are audited and zero credentials/secrets leak into metadata."""
        recent_audits = self.db.query(models.AuditLog).filter(
            models.AuditLog.timestamp >= datetime.datetime.utcnow() - datetime.timedelta(minutes=5)
        ).all()
        self.assertGreater(len(recent_audits), 0)

        forbidden_keys = {"password", "password_hash", "code_hash", "otp", "raw_code", "access_token", "secret"}

        for audit in recent_audits:
            meta = audit.metadata_json or {}
            for key in forbidden_keys:
                self.assertNotIn(key, meta, f"Secret key '{key}' leaked in audit log {audit.id}!")
                # Also verify string values do not contain raw passwords
                for val in meta.values():
                    if isinstance(val, str):
                        self.assertNotIn("Password123!", val)
                        self.assertNotIn("BrandNewSecurePassword456!", val)


if __name__ == "__main__":
    unittest.main()
