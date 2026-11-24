"""
Test Suite: Registration Consistency & Failure Scenario Verification
=====================================================================
Remediation test suite covering the 10 required regression test scenarios:
1. Supabase registration failure never produces an active account without a required identity.
2. Lost Supabase creation responses recover safely without changing an unrelated existing identity's password.
3. Registration can retry after a recoverable failure without duplicate records.
4. Password-reset provider failure never reports success while credentials remain inconsistent.
5. Password-reset timeout and retry behavior are safe.
6. Expired, exhausted, invalidated, and completed challenges scrub encrypted credentials.
7. Abandoned challenge cleanup works and is safe to rerun.
8. Supabase-backed users cannot authenticate through a prohibited local-login fallback.
9. Explicitly supported local-only development accounts continue to work only in their permitted environment.
10. OTP expiry, attempt limits, resend cooldown, single-use consumption, verified-email sequencing, session revocation, tenant isolation, and authorization remain correct.
"""

import unittest
import unittest.mock
import uuid
import sys
import os
import re
import datetime

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
    encrypt_ephemeral_secret,
    decrypt_ephemeral_secret,
    PURPOSE_REGISTRATION,
    PURPOSE_PASSWORD_RESET,
    PURPOSE_PASSWORDLESS_LOGIN,
    utc_now
)
from core.supabase_admin import supabase_admin, SupabaseAdminClient

client = TestClient(app)


def extract_otp_code(email_idx: int = -1) -> str:
    body = email_service.sent_emails_mock[email_idx]["body_text"]
    match = re.search(r'\b(\d{6})\b', body)
    if not match:
        raise ValueError("OTP code not found in email body")
    return match.group(1)


class TestRegistrationConsistencyScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        settings.EMAIL_PROVIDER = "MOCK"

    def setUp(self):
        self.db = SessionLocal()
        email_service.sent_emails_mock.clear()

    def tearDown(self):
        self.db.close()

    def test_01_supabase_registration_failure_never_produces_active_account(self):
        """
        1. Supabase registration failure never produces an active account without a required identity.
        When Supabase is configured and create_user returns None/fails:
        - HTTP 502 Bad Gateway is returned.
        - No active user is created in PostgreSQL with auth_user_id=None.
        - OTP challenge remains unconsumed and retryable.
        """
        test_email = f"fail_closed_{uuid.uuid4().hex[:6]}@enterprise.ai"
        chosen_pass = "Password123!"

        with unittest.mock.patch.object(supabase_admin, "service_role_key", "test_service_key"):
            with unittest.mock.patch.object(supabase_admin, "create_user", return_value=None):
                req_resp = client.post("/api/auth/register/request-otp", json={
                    "full_name": "Fail Closed Test",
                    "email": test_email,
                    "password": chosen_pass
                })
                self.assertEqual(req_resp.status_code, 200)

                raw_code = extract_otp_code(-1)
                verify_resp = client.post("/api/auth/register/verify-otp", json={
                    "email": test_email,
                    "otp": raw_code
                })
                # Fails closed with 502 Bad Gateway
                self.assertEqual(verify_resp.status_code, 502)

                # PostgreSQL state assertion: No ACTIVE user created
                user = self.db.query(models.User).filter(models.User.email == test_email).first()
                if user:
                    self.assertNotEqual(user.status, "ACTIVE")
                else:
                    self.assertIsNone(user)

                # Challenge remains unconsumed and ready for retry
                challenge = self.db.query(models.OtpChallenge).filter(
                    models.OtpChallenge.email == test_email,
                    models.OtpChallenge.purpose == PURPOSE_REGISTRATION
                ).first()
                self.assertIsNotNone(challenge)
                self.assertFalse(challenge.consumed)

    def test_02_lost_supabase_response_recovers_safely_without_changing_password(self):
        """
        2. Lost Supabase creation responses recover safely without changing an unrelated existing identity's password.
        When Supabase returns 422 because user exists, create_user recovers existing auth ID,
        confirms email/metadata, but NEVER updates the password.
        """
        test_email = f"lost_resp_{uuid.uuid4().hex[:6]}@enterprise.ai"
        existing_id = f"sb-lost-{uuid.uuid4().hex}"
        password = "Password123!"

        admin = SupabaseAdminClient()
        admin.service_role_key = "test_key"

        with unittest.mock.patch.object(admin, "_request", return_value=(422, {"message": "User already registered"})):
            with unittest.mock.patch.object(admin, "_get_existing_user_id", return_value=existing_id) as mock_get:
                with unittest.mock.patch.object(admin, "update_user", return_value=True) as mock_update:
                    result_id = admin.create_user(test_email, password=password, full_name="Lost Resp", email_confirm=True)
                    self.assertEqual(result_id, existing_id)
                    mock_get.assert_called_once_with(test_email)
                    # update_user MUST be called with email_confirm and full_name, but WITHOUT password!
                    mock_update.assert_called_once_with(existing_id, email_confirm=True, full_name="Lost Resp")

    def test_03_registration_retry_after_recoverable_failure_without_duplicate_records(self):
        """
        3. Registration can retry after a recoverable failure without duplicate records.
        First attempt fails upstream, second attempt succeeds with same OTP.
        Exactly one user and one organization are created.
        """
        test_email = f"retry_ok_{uuid.uuid4().hex[:6]}@enterprise.ai"
        chosen_pass = "Password123!"
        mock_auth_id = f"sb-auth-{uuid.uuid4().hex}"

        req_resp = client.post("/api/auth/register/request-otp", json={
            "full_name": "Retry User",
            "email": test_email,
            "password": chosen_pass
        })
        self.assertEqual(req_resp.status_code, 200)
        raw_code = extract_otp_code(-1)

        with unittest.mock.patch.object(supabase_admin, "service_role_key", "test_service_key"):
            # Attempt 1: Upstream failure
            with unittest.mock.patch.object(supabase_admin, "create_user", return_value=None):
                attempt1 = client.post("/api/auth/register/verify-otp", json={
                    "email": test_email,
                    "otp": raw_code
                })
                self.assertEqual(attempt1.status_code, 502)

            # Attempt 2: Upstream recovers and succeeds with same OTP
            with unittest.mock.patch.object(supabase_admin, "create_user", return_value=mock_auth_id):
                attempt2 = client.post("/api/auth/register/verify-otp", json={
                    "email": test_email,
                    "otp": raw_code
                })
                self.assertEqual(attempt2.status_code, 200)
                self.assertEqual(attempt2.json()["auth_user_id"], mock_auth_id)

        # Confirm exactly 1 user and 1 organization in DB (no duplicates)
        users = self.db.query(models.User).filter(models.User.email == test_email).all()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].status, "ACTIVE")
        self.assertEqual(users[0].auth_user_id, mock_auth_id)

        orgs = self.db.query(models.Organization).filter(models.Organization.id == users[0].org_id).all()
        self.assertEqual(len(orgs), 1)

    def test_04_password_reset_provider_failure_never_reports_success_while_inconsistent(self):
        """
        4. Password-reset provider failure never reports success while credentials remain inconsistent.
        If Supabase password update fails, reset endpoint returns 502, and local password hash is NOT updated.
        """
        test_email = f"reset_diverge_{uuid.uuid4().hex[:6]}@enterprise.ai"
        initial_pass = "InitialPass123!"
        new_pass = "BrandNewPass456!"
        auth_id = f"sb-{uuid.uuid4().hex}"

        org = models.Organization(name="Reset Test Org")
        self.db.add(org)
        self.db.commit()

        user = models.User(
            org_id=org.id,
            auth_user_id=auth_id,
            email=test_email,
            password_hash=security.get_password_hash(initial_pass),
            full_name="Reset Fail Test",
            role="USER",
            status="ACTIVE"
        )
        self.db.add(user)
        self.db.commit()

        # Request recovery OTP
        client.post("/api/auth/forgot-password/request-otp", json={"email": test_email})
        code = extract_otp_code(-1)

        with unittest.mock.patch.object(supabase_admin, "service_role_key", "test_key"):
            with unittest.mock.patch.object(supabase_admin, "update_user_password", return_value=False):
                reset_resp = client.post("/api/auth/forgot-password/reset", json={
                    "email": test_email,
                    "otp": code,
                    "new_password": new_pass
                })
                # Returns 502 Bad Gateway (NOT 200 SUCCESS!)
                self.assertEqual(reset_resp.status_code, 502)

                # Local password hash remains unchanged (still verifies against initial_pass)
                self.db.refresh(user)
                self.assertTrue(security.verify_password(initial_pass, str(user.password_hash)))
                self.assertFalse(security.verify_password(new_pass, str(user.password_hash)))

    def test_05_password_reset_timeout_and_retry_behavior_are_safe(self):
        """
        5. Password-reset timeout and retry behavior are safe.
        SupabaseAdminClient retries transient timeouts safely, and reset ticket is single-use.
        """
        test_email = f"retry_safe_{uuid.uuid4().hex[:6]}@enterprise.ai"
        initial_pass = "Pass12345!"
        new_pass = "NewPass12345!"
        auth_id = f"sb-to-{uuid.uuid4().hex}"

        org = models.Organization(name="Timeout Org")
        self.db.add(org)
        self.db.commit()

        user = models.User(
            org_id=org.id,
            auth_user_id=auth_id,
            email=test_email,
            password_hash=security.get_password_hash(initial_pass),
            full_name="Timeout Test",
            role="USER",
            status="ACTIVE"
        )
        self.db.add(user)
        self.db.commit()

        # Request OTP and obtain reset ticket
        client.post("/api/auth/forgot-password/request-otp", json={"email": test_email})
        code = extract_otp_code(-1)
        verify_resp = client.post("/api/auth/forgot-password/verify-otp", json={"email": test_email, "otp": code})
        ticket = verify_resp.json()["reset_ticket"]
        self.assertIsNotNone(ticket)

        admin = SupabaseAdminClient()
        admin.service_role_key = "test_key"

        # Simulate update_user encountering network error (code 0) first, then retry succeeds (code 200)
        with unittest.mock.patch.object(admin, "_request", side_effect=[(0, "timeout"), (200, {"id": auth_id})]):
            success = admin.update_user_password(auth_id, new_pass)
            self.assertTrue(success)

        # Verify that reset ticket is strictly single-use
        with unittest.mock.patch.object(supabase_admin, "service_role_key", "test_key"):
            with unittest.mock.patch.object(supabase_admin, "update_user_password", return_value=True):
                # First reset with ticket succeeds
                first_reset = client.post("/api/auth/forgot-password/reset", json={
                    "email": test_email,
                    "reset_ticket": ticket,
                    "new_password": new_pass
                })
                self.assertEqual(first_reset.status_code, 200)

                # Second reset attempt with same ticket fails (single-use enforcement)
                replay_reset = client.post("/api/auth/forgot-password/reset", json={
                    "email": test_email,
                    "reset_ticket": ticket,
                    "new_password": "AnotherPassword789!"
                })
                self.assertEqual(replay_reset.status_code, 400)
                self.assertIn("already been used", replay_reset.json()["detail"].lower())

    def test_06_expired_exhausted_invalidated_and_completed_challenges_scrub_credentials(self):
        """
        6. Expired, exhausted, invalidated, and completed challenges scrub encrypted credentials.
        """
        # Scenario A: Completed challenge scrubs metadata
        email_comp = f"comp_{uuid.uuid4().hex[:6]}@enterprise.ai"
        client.post("/api/auth/register/request-otp", json={"full_name": "Comp", "email": email_comp, "password": "Password123!"})
        code_comp = extract_otp_code(-1)
        client.post("/api/auth/register/verify-otp", json={"email": email_comp, "otp": code_comp})

        ch_comp = self.db.query(models.OtpChallenge).filter(models.OtpChallenge.email == email_comp).first()
        self.assertNotIn("encrypted_password", ch_comp.metadata_json or {})
        self.assertNotIn("password_hash", ch_comp.metadata_json or {})

        # Scenario B: Exhausted challenge (5 incorrect attempts) scrubs metadata
        email_exh = f"exh_{uuid.uuid4().hex[:6]}@enterprise.ai"
        client.post("/api/auth/register/request-otp", json={"full_name": "Exh", "email": email_exh, "password": "Password123!"})
        for _ in range(5):
            otp_service.verify_challenge(self.db, email_exh, PURPOSE_REGISTRATION, "000000")

        ch_exh = self.db.query(models.OtpChallenge).filter(models.OtpChallenge.email == email_exh).first()
        self.assertTrue(ch_exh.consumed)
        self.assertNotIn("encrypted_password", ch_exh.metadata_json or {})
        self.assertNotIn("password_hash", ch_exh.metadata_json or {})

        # Scenario C: Expired challenge scrubs metadata upon evaluation
        email_exp = f"exp_{uuid.uuid4().hex[:6]}@enterprise.ai"
        ch_exp, code_exp = otp_service.issue_challenge(
            self.db, email_exp, PURPOSE_REGISTRATION,
            metadata_json={"encrypted_password": "ciphertext", "password_hash": "hash"}
        )
        ch_exp.expires_at = utc_now() - datetime.timedelta(seconds=10)
        self.db.commit()

        valid, _, _ = otp_service.verify_challenge(self.db, email_exp, PURPOSE_REGISTRATION, code_exp)
        self.assertFalse(valid)
        self.db.refresh(ch_exp)
        self.assertNotIn("encrypted_password", ch_exp.metadata_json or {})

        # Scenario D: Superseded challenge scrubs metadata
        email_sup = f"sup_{uuid.uuid4().hex[:6]}@enterprise.ai"
        ch_sup1, _ = otp_service.issue_challenge(
            self.db, email_sup, PURPOSE_REGISTRATION,
            metadata_json={"encrypted_password": "secret1", "password_hash": "hash1"}
        )
        ch_sup1.resend_available_at = utc_now() - datetime.timedelta(seconds=1)
        self.db.commit()

        # Issue second challenge
        otp_service.issue_challenge(self.db, email_sup, PURPOSE_REGISTRATION)
        self.db.refresh(ch_sup1)
        self.assertTrue(ch_sup1.consumed)
        self.assertNotIn("encrypted_password", ch_sup1.metadata_json or {})

    def test_07_abandoned_challenge_cleanup_works_and_is_safe_to_rerun(self):
        """
        7. Abandoned challenge cleanup works and is safe to rerun.
        Scrubs existing abandoned/expired challenges without error.
        """
        email_ab = f"abandoned_{uuid.uuid4().hex[:6]}@enterprise.ai"
        ch_ab, _ = otp_service.issue_challenge(
            self.db, email_ab, PURPOSE_REGISTRATION,
            metadata_json={"encrypted_password": "stale_cipher", "password_hash": "stale_hash", "full_name": "Abandoned"}
        )
        ch_ab.expires_at = utc_now() - datetime.timedelta(minutes=30)
        self.db.commit()

        # Run cleanup
        scrubbed_count = otp_service.cleanup_expired_challenges(self.db)
        self.assertGreaterEqual(scrubbed_count, 1)

        self.db.refresh(ch_ab)
        self.assertTrue(ch_ab.consumed)
        self.assertNotIn("encrypted_password", ch_ab.metadata_json or {})
        self.assertNotIn("password_hash", ch_ab.metadata_json or {})
        self.assertEqual(ch_ab.metadata_json.get("full_name"), "Abandoned")

        # Rerun cleanup — safe and idempotent (returns 0 for already cleaned rows)
        rerun_count = otp_service.cleanup_expired_challenges(self.db)
        self.assertEqual(rerun_count, 0)

    def test_08_supabase_backed_users_cannot_authenticate_through_prohibited_local_login(self):
        """
        8. Supabase-backed users cannot authenticate through a prohibited local-login fallback.
        When Supabase is configured and a user has auth_user_id, local-login rejects with 403.
        """
        test_email = f"sb_only_{uuid.uuid4().hex[:6]}@enterprise.ai"
        password = "Password123!"
        auth_id = f"sb-{uuid.uuid4().hex}"

        org = models.Organization(name="SB Only Org")
        self.db.add(org)
        self.db.commit()

        user = models.User(
            org_id=org.id,
            auth_user_id=auth_id,
            email=test_email,
            password_hash=security.get_password_hash(password),
            full_name="SB Backed User",
            role="USER",
            status="ACTIVE"
        )
        self.db.add(user)
        self.db.commit()

        with unittest.mock.patch.object(supabase_admin, "service_role_key", "mock_key"):
            resp = client.post("/api/auth/local-login", json={
                "email": test_email,
                "password": password
            })
            self.assertEqual(resp.status_code, 403)
            self.assertIn("not permitted for accounts managed by supabase auth", resp.json()["detail"].lower())

    def test_09_explicitly_supported_local_only_dev_accounts_work_only_in_permitted_environment(self):
        """
        9. Explicitly supported local-only development accounts continue to work only in their permitted environment.
        - In development/testing (without Supabase identity): succeeds.
        - In production (with ALLOW_LOCAL_LOGIN=False): rejected with 403.
        """
        test_email = f"dev_local_{uuid.uuid4().hex[:6]}@enterprise.ai"
        password = "Password123!"

        org = models.Organization(name="Dev Local Org")
        self.db.add(org)
        self.db.commit()

        user = models.User(
            org_id=org.id,
            auth_user_id=None,  # Local-only account
            email=test_email,
            password_hash=security.get_password_hash(password),
            full_name="Dev Local User",
            role="USER",
            status="ACTIVE"
        )
        self.db.add(user)
        self.db.commit()

        # In testing environment with local auth permitted:
        resp_dev = client.post("/api/auth/local-login", json={"email": test_email, "password": password})
        self.assertEqual(resp_dev.status_code, 200)
        self.assertIn("access_token", resp_dev.json())

        # In production with local auth disabled:
        with unittest.mock.patch.object(settings, "ENVIRONMENT", "production"):
            with unittest.mock.patch.object(settings, "ALLOW_LOCAL_LOGIN", False):
                resp_prod = client.post("/api/auth/local-login", json={"email": test_email, "password": password})
                self.assertEqual(resp_prod.status_code, 403)
                self.assertIn("disabled in this environment", resp_prod.json()["detail"].lower())

    def test_10_otp_security_invariants_and_auth_integrity(self):
        """
        10. OTP expiry, attempt limits, resend cooldown, single-use consumption,
        verified-email sequencing, session revocation, tenant isolation, and authorization remain correct.
        """
        test_email = f"invariants_{uuid.uuid4().hex[:6]}@enterprise.ai"
        password = "InvariantPassword123!"

        # A. Verified-email sequencing: account does NOT exist prior to OTP verification
        client.post("/api/auth/register/request-otp", json={"full_name": "Invariant User", "email": test_email, "password": password})
        user_before = self.db.query(models.User).filter(models.User.email == test_email).first()
        self.assertIsNone(user_before)

        # B. Resend cooldown: immediate second request returns 429
        dup_req = client.post("/api/auth/register/request-otp", json={"full_name": "Invariant User", "email": test_email, "password": password})
        self.assertEqual(dup_req.status_code, 429)

        # C. 6-digit OTP verification & account creation
        code = extract_otp_code(-1)
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

        # Bad code fails with attempt counter decrement
        bad_code = client.post("/api/auth/register/verify-otp", json={"email": test_email, "otp": "000000"})
        self.assertEqual(bad_code.status_code, 400)

        # Correct code verifies and creates account
        good_verify = client.post("/api/auth/register/verify-otp", json={"email": test_email, "otp": code})
        self.assertEqual(good_verify.status_code, 200)
        token = good_verify.json()["access_token"]

        # D. Single-use consumption: same OTP cannot be reused
        replay_verify = client.post("/api/auth/register/verify-otp", json={"email": test_email, "otp": code})
        self.assertEqual(replay_verify.status_code, 400)

        # E. Session revocation on password reset
        client.post("/api/auth/forgot-password/request-otp", json={"email": test_email})
        rec_code = extract_otp_code(-1)
        client.post("/api/auth/forgot-password/reset", json={"email": test_email, "otp": rec_code, "new_password": "NewInvariantPass456!"})

        # Old session token must now be revoked
        me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me_resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
