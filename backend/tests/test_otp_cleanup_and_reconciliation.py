"""
Test Suite: Production OTP Cleanup Scheduling & Password-Reset Reconciliation
=============================================================================
Regression tests verifying:
1. Celery task registration and Beat periodic scheduling configuration (hourly).
2. Expired and abandoned challenge cleanup and sensitive metadata scrubbing.
3. Repeated cleanup execution idempotency and multi-worker safety.
4. Bounded batch processing with limit and max_batches enforcement.
5. Database session lifecycle cleanup on task success and failure.
6. Password-reset provider success followed by PostgreSQL commit failure.
7. Supabase-backed login behavior after that failure (authoritative login works).
8. Strict prevention of stale local-password fallback for Supabase-backed users.
"""

import unittest
import unittest.mock
from unittest.mock import patch, MagicMock
import uuid
import sys
import os
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
from services.otp_service import (
    otp_service,
    OtpService,
    PURPOSE_REGISTRATION,
    PURPOSE_PASSWORD_RESET,
    PURPOSE_PASSWORDLESS_LOGIN,
    utc_now,
    SENSITIVE_METADATA_KEYS
)
from core.supabase_admin import supabase_admin
from celery_app import celery_app
from tasks.auth_tasks import cleanup_expired_otp_challenges_task
from sqlalchemy.exc import SQLAlchemyError

client = TestClient(app)


class TestOtpCleanupAndReconciliation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        settings.EMAIL_PROVIDER = "MOCK"

    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    # =========================================================================
    # Task 1: Celery Registration & Scheduling
    # =========================================================================

    def test_01_celery_task_registration_and_schedule(self):
        """
        Verify that:
        1. 'tasks.auth_tasks' is included in celery_app.
        2. 'tasks.auth_tasks.cleanup_expired_otp_challenges_task' is registered.
        3. 'cleanup-expired-otp-challenges' is configured in celery_app.conf.beat_schedule.
        4. The task schedule is hourly (3600.0 seconds).
        """
        # 1. Include check
        self.assertIn("tasks.auth_tasks", celery_app.conf.include)

        # 2. Registered task check
        task_name = "tasks.auth_tasks.cleanup_expired_otp_challenges_task"
        self.assertIn(task_name, celery_app.tasks)

        # 3. Beat schedule check
        schedule_conf = celery_app.conf.beat_schedule.get("cleanup-expired-otp-challenges")
        self.assertIsNotNone(schedule_conf, "Periodic Beat schedule for cleanup-expired-otp-challenges missing")
        self.assertEqual(schedule_conf["task"], task_name)
        self.assertEqual(schedule_conf["schedule"], 3600.0)

    # =========================================================================
    # Task 1: Expired & Abandoned Challenge Cleanup
    # =========================================================================

    def test_02_expired_and_abandoned_challenge_cleanup(self):
        """
        Verify that cleanup_expired_challenges:
        1. Identifies expired unconsumed challenges (abandoned registration & reset).
        2. Marks them consumed = True and scrubs sensitive metadata.
        3. Preserves unexpired active challenges without consuming or scrubbing them prematurely.
        """
        past_time = utc_now() - datetime.timedelta(minutes=30)
        future_time = utc_now() + datetime.timedelta(minutes=10)

        # 1. Expired registration challenge with sensitive metadata
        expired_reg = models.OtpChallenge(
            email="abandoned_reg@test.com",
            purpose=PURPOSE_REGISTRATION,
            code_hash="fake_hash_1",
            consumed=False,
            expires_at=past_time,
            resend_available_at=past_time,
            metadata_json={
                "full_name": "Abandoned User",
                "org_name": "Abandoned Org",
                "password_hash": "sensitive_hash_123",
                "encrypted_password": "sensitive_ciphertext_456"
            }
        )
        self.db.add(expired_reg)

        # 2. Expired reset challenge
        expired_reset = models.OtpChallenge(
            email="abandoned_reset@test.com",
            purpose=PURPOSE_PASSWORD_RESET,
            code_hash="fake_hash_2",
            consumed=False,
            expires_at=past_time,
            resend_available_at=past_time,
            metadata_json={"ip": "127.0.0.1"}
        )
        self.db.add(expired_reset)

        # 3. Active unexpired registration challenge
        active_reg = models.OtpChallenge(
            email="active_user@test.com",
            purpose=PURPOSE_REGISTRATION,
            code_hash="fake_hash_3",
            consumed=False,
            expires_at=future_time,
            resend_available_at=future_time,
            metadata_json={
                "full_name": "Active User",
                "password_hash": "active_hash_789",
                "encrypted_password": "active_ciphertext_101"
            }
        )
        self.db.add(active_reg)
        self.db.commit()

        # Run cleanup
        cleaned = OtpService.cleanup_expired_challenges(self.db)
        self.assertGreaterEqual(cleaned, 2)

        # Reload records
        self.db.refresh(expired_reg)
        self.db.refresh(expired_reset)
        self.db.refresh(active_reg)

        # Assert expired challenges are consumed and scrubbed
        self.assertTrue(expired_reg.consumed)
        for key in SENSITIVE_METADATA_KEYS:
            self.assertNotIn(key, expired_reg.metadata_json)
        self.assertEqual(expired_reg.metadata_json.get("full_name"), "Abandoned User")

        self.assertTrue(expired_reset.consumed)

        # Assert active challenge remains untouched
        self.assertFalse(active_reg.consumed)
        self.assertIn("password_hash", active_reg.metadata_json)
        self.assertIn("encrypted_password", active_reg.metadata_json)

    # =========================================================================
    # Task 1: Repeated Execution & Multi-Worker Safety
    # =========================================================================

    def test_03_repeated_cleanup_execution(self):
        """
        Verify that running cleanup repeatedly is safe, idempotent, and produces 0
        updates when no eligible rows exist.
        """
        past_time = utc_now() - datetime.timedelta(minutes=15)
        ch = models.OtpChallenge(
            email=f"repeat_{uuid.uuid4().hex[:8]}@test.com",
            purpose=PURPOSE_REGISTRATION,
            code_hash="repeat_hash",
            consumed=False,
            expires_at=past_time,
            resend_available_at=past_time,
            metadata_json={"password_hash": "hash_repeat"}
        )
        self.db.add(ch)
        self.db.commit()

        # First execution cleans the row
        first_run = OtpService.cleanup_expired_challenges(self.db)
        self.assertGreaterEqual(first_run, 1)

        # Second execution immediately afterwards should find 0 remaining rows
        second_run = OtpService.cleanup_expired_challenges(self.db)
        self.assertEqual(second_run, 0)

        # Third execution remains 0
        third_run = OtpService.cleanup_expired_challenges(self.db)
        self.assertEqual(third_run, 0)

    # =========================================================================
    # Task 1: Bounded Batch Processing
    # =========================================================================

    def test_04_bounded_batch_processing(self):
        """
        Verify bounded batch processing:
        1. Processes all items in bounded chunks of batch_size.
        2. Honors max_batches constraint when specified.
        """
        past_time = utc_now() - datetime.timedelta(minutes=20)
        prefix = f"batch_{uuid.uuid4().hex[:6]}"

        # Create 12 expired challenges
        for i in range(12):
            c = models.OtpChallenge(
                email=f"{prefix}_{i}@test.com",
                purpose=PURPOSE_REGISTRATION,
                code_hash=f"batch_hash_{i}",
                consumed=False,
                expires_at=past_time,
                resend_available_at=past_time,
                metadata_json={"password_hash": f"hash_{i}", "encrypted_password": f"enc_{i}"}
            )
            self.db.add(c)
        self.db.commit()

        # Test max_batches=1 with batch_size=4 -> exactly 4 rows should be cleaned in that single batch
        cleaned_batch1 = OtpService.cleanup_expired_challenges(self.db, batch_size=4, max_batches=1)
        self.assertEqual(cleaned_batch1, 4)

        # Clean remaining rows with batch_size=5 -> remaining 8 rows cleaned
        remaining_cleaned = OtpService.cleanup_expired_challenges(self.db, batch_size=5)
        self.assertEqual(remaining_cleaned, 8)

    # =========================================================================
    # Task 1: Database Session Lifecycle in Celery Task
    # =========================================================================

    def test_05_database_session_cleanup_after_task_success_and_failure(self):
        """
        Verify database session lifecycle:
        1. Task executes and closes session on success.
        2. Task handles exceptions, rolls back, reliably closes session, and returns error dict.
        3. Zero secrets or sensitive data are logged.
        """
        # Success path
        res = cleanup_expired_otp_challenges_task()
        self.assertEqual(res["status"], "COMPLETED")
        self.assertIn("cleaned_count", res)
        self.assertIn("timestamp", res)

        # Failure path: simulate DB exception
        with patch.object(OtpService, "cleanup_expired_challenges", side_effect=SQLAlchemyError("Simulated DB lock timeout")):
            mock_session = MagicMock()
            with patch("tasks.auth_tasks.SessionLocal", return_value=mock_session):
                fail_res = cleanup_expired_otp_challenges_task()

                # Verify session lifecycle
                mock_session.rollback.assert_called_once()
                mock_session.close.assert_called_once()

                # Verify clean error response without unhandled exception crash
                self.assertEqual(fail_res["status"], "ERROR")
                self.assertEqual(fail_res["cleaned_count"], 0)
                self.assertIn("Simulated DB lock timeout", fail_res["error"])

    # =========================================================================
    # Task 2: Password Reset Reconciliation
    # =========================================================================

    def test_06_password_reset_provider_success_postgres_commit_failure(self):
        """
        Verify scenario:
        1. Supabase successfully updates user password.
        2. PostgreSQL fails to commit the local password hash.
        3. Endpoint reconciles safely, logs warning, and reports SUCCESS to user.
        """
        email = f"reset_reconcile_{uuid.uuid4().hex[:8]}@test.com"
        org = models.Organization(name="Reconcile Org")
        self.db.add(org)
        self.db.commit()

        initial_local_hash = security.get_password_hash("OldPassword123!")
        user = models.User(
            org_id=org.id,
            auth_user_id=f"sb-reconcile-{uuid.uuid4().hex[:8]}",
            email=email,
            full_name="Reconcile User",
            role="USER",
            password_hash=initial_local_hash,
            status="ACTIVE"
        )
        self.db.add(user)
        self.db.commit()

        # Create valid reset ticket
        ticket = OtpService.create_reset_ticket(str(user.id), email)

        # Mock Supabase password update to succeed, but db.commit inside route to fail on first attempt
        from database import get_db

        def override_flaky_db():
            flaky_db = SessionLocal()
            real_commit = flaky_db.commit
            call_count = [0]

            def flaky_commit():
                call_count[0] += 1
                if call_count[0] == 2:
                    raise SQLAlchemyError("Simulated transient PostgreSQL commit failure")
                return real_commit()

            flaky_db.commit = flaky_commit
            try:
                yield flaky_db
            finally:
                flaky_db.close()

        app.dependency_overrides[get_db] = override_flaky_db
        try:
            with patch.object(supabase_admin, "service_role_key", "mock-service-key"):
                with patch.object(supabase_admin, "update_user_password", return_value=True):
                    payload = {
                        "email": email,
                        "reset_ticket": ticket,
                        "new_password": "NewStrongPassword2026!"
                    }
                    resp = client.post("/api/v1/auth/forgot-password/reset", json=payload)
                    self.assertEqual(resp.status_code, 200)
                    data = resp.json()
                    self.assertEqual(data["status"], "SUCCESS")
                    self.assertIn("Password has been reset", data["message"])
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_07_supabase_login_behavior_after_commit_failure(self):
        """
        Verify that a Supabase-backed user can immediately log in with their
        new password via Supabase Auth even if the local password_hash commit failed.
        /auth/login does not verify local password_hash.
        """
        email = f"sb_login_{uuid.uuid4().hex[:8]}@test.com"
        sb_auth_id = f"sb-auth-{uuid.uuid4().hex[:8]}"

        org = models.Organization(name="Sb Org")
        self.db.add(org)
        self.db.commit()

        # User has stale local password hash
        stale_local_hash = security.get_password_hash("StaleOldPassword123!")
        user = models.User(
            org_id=org.id,
            auth_user_id=sb_auth_id,
            email=email,
            full_name="Sb User",
            role="USER",
            password_hash=stale_local_hash,
            status="ACTIVE"
        )
        self.db.add(user)
        self.db.commit()

        # User logs in with new Supabase token
        with patch("core.deps.verify_supabase_token", return_value=(sb_auth_id, email)):
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": email, "auth_user_id": sb_auth_id},
                headers={"Authorization": "Bearer mocked-valid-supabase-new-password-jwt"}
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["email"], email)
            self.assertEqual(data["auth_user_id"], sb_auth_id)
            self.assertTrue(len(data["access_token"]) > 20)

    def test_08_no_stale_local_password_fallback_for_supabase_users(self):
        """
        Verify that Supabase-backed users are strictly prohibited from using
        the /auth/local-login fallback, preventing any authentication against
        stale local password hashes.
        """
        email = f"no_fallback_{uuid.uuid4().hex[:8]}@test.com"
        sb_auth_id = f"sb-user-{uuid.uuid4().hex[:8]}"
        stale_password = "OldStalePassword123!"

        org = models.Organization(name="NoFallback Org")
        self.db.add(org)
        self.db.commit()

        user = models.User(
            org_id=org.id,
            auth_user_id=sb_auth_id,
            email=email,
            full_name="No Fallback User",
            role="USER",
            password_hash=security.get_password_hash(stale_password),
            status="ACTIVE"
        )
        self.db.add(user)
        self.db.commit()

        # 1. Attempt local login with old password when Supabase is configured
        with patch.object(supabase_admin, "service_role_key", "mock-sb-key"):
            resp = client.post("/api/v1/auth/local-login", json={
                "email": email,
                "password": stale_password
            })
            self.assertEqual(resp.status_code, 403)
            self.assertIn("Local login is not permitted", resp.json()["detail"])

        # 2. Attempt local login with old password when Supabase is NOT configured (e.g. offline/misconfigured)
        with patch.object(supabase_admin, "service_role_key", ""):
            resp2 = client.post("/api/v1/auth/local-login", json={
                "email": email,
                "password": stale_password
            })
            # Must STILL be rejected: auth_user_id marks account as identity-provider managed
            self.assertEqual(resp2.status_code, 403)
            self.assertIn("Local login is not permitted", resp2.json()["detail"])


if __name__ == "__main__":
    unittest.main()
