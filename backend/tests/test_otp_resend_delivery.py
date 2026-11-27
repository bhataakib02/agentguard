"""
Comprehensive Automated Tests for Registration OTP & Resend Email Delivery
===========================================================================
Uses mocked urllib.request.urlopen responses so ZERO real emails are sent.
"""

import io
import json
import os
import sys
import unittest
import unittest.mock
import urllib.error
import uuid

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("SECRET_KEY", "agentguard-test-secret-key-32charactersmin")

sys.path.insert(0, backend_dir)

from starlette.testclient import TestClient
from main import app
from database import SessionLocal
from config import settings
import models
from services.email_service import email_service
from services.otp_service import PURPOSE_REGISTRATION

client = TestClient(app)


def _mock_http_response(status_code: int, payload: dict):
    resp = unittest.mock.MagicMock()
    resp.status = status_code
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.__enter__ = unittest.mock.MagicMock(return_value=resp)
    resp.__exit__ = unittest.mock.MagicMock(return_value=False)
    return resp


def _mock_http_error(status_code: int, payload: dict):
    raw = json.dumps(payload).encode("utf-8")
    return urllib.error.HTTPError(
        url="https://api.resend.com/emails",
        code=status_code,
        msg="Error",
        hdrs=None,
        fp=io.BytesIO(raw),
    )


class TestOtpResendDelivery(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.orig_provider = settings.EMAIL_PROVIDER
        self.orig_key = settings.RESEND_API_KEY
        self.orig_from = settings.RESEND_FROM_EMAIL
        settings.EMAIL_PROVIDER = "RESEND"
        settings.RESEND_API_KEY = "re_test_mock_key_1234567890"
        settings.RESEND_FROM_EMAIL = "AgentGuard <noreply@verified-domain.example>"

    def tearDown(self):
        settings.EMAIL_PROVIDER = self.orig_provider
        settings.RESEND_API_KEY = self.orig_key
        settings.RESEND_FROM_EMAIL = self.orig_from
        self.db.close()

    def _new_email(self) -> str:
        return f"otp_test_{uuid.uuid4().hex[:8]}@example.com"

    def test_01_resend_success_returns_accepted_and_email_id(self):
        email = self._new_email()
        with unittest.mock.patch(
            "urllib.request.urlopen",
            return_value=_mock_http_response(200, {"id": "re_msg_abc123"}),
        ) as mock_open:
            resp = client.post(
                "/api/auth/register/request-otp",
                json={"full_name": "Resend OK", "email": email, "password": "Password123!"},
            )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["delivery_status"], "ACCEPTED_FOR_SENDING")
        self.assertEqual(data["provider_message_id"], "re_msg_abc123")
        self.assertTrue(data["correlation_id"])
        self.assertEqual(data["cooldown_seconds"], 120)
        self.assertEqual(mock_open.call_count, 1)

    def test_02_missing_api_key_returns_503_and_preserves_otp(self):
        email = self._new_email()
        settings.RESEND_API_KEY = ""
        resp = client.post(
            "/api/auth/register/request-otp",
            json={"full_name": "Missing Key", "email": email, "password": "Password123!"},
        )
        self.assertEqual(resp.status_code, 503)
        self.assertIn("Email provider configuration is missing", resp.json()["detail"])

        challenge = self.db.query(models.OtpChallenge).filter(
            models.OtpChallenge.email == email,
            models.OtpChallenge.purpose == PURPOSE_REGISTRATION,
        ).first()
        self.assertIsNotNone(challenge)
        self.assertFalse(challenge.consumed)

    def test_03_invalid_sender_format_rejected_without_network_call(self):
        email = self._new_email()
        settings.RESEND_FROM_EMAIL = "invalid-sender-without-at-sign"
        with unittest.mock.patch("urllib.request.urlopen") as mock_open:
            resp = client.post(
                "/api/auth/register/request-otp",
                json={"full_name": "Bad Sender", "email": email, "password": "Password123!"},
            )
        self.assertEqual(resp.status_code, 502)
        self.assertIn("Invalid", resp.json()["detail"].title())
        mock_open.assert_not_called()

    def test_04_unverified_sender_domain_403_no_retry(self):
        email = self._new_email()
        err = _mock_http_error(403, {"name": "validation_error", "message": "Please verify a domain first."})
        with unittest.mock.patch("urllib.request.urlopen", side_effect=err) as mock_open:
            resp = client.post(
                "/api/auth/register/request-otp",
                json={"full_name": "Unverified Domain", "email": email, "password": "Password123!"},
            )
        self.assertEqual(resp.status_code, 502)
        self.assertIn("Sender domain is not verified", resp.json()["detail"])
        self.assertEqual(mock_open.call_count, 1)

    def test_05_recipient_restriction_onboarding_resend_dev_no_retry(self):
        email = self._new_email()
        settings.RESEND_FROM_EMAIL = "AgentGuard <onboarding@resend.dev>"
        err = _mock_http_error(
            403,
            {
                "statusCode": 403,
                "name": "validation_error",
                "message": "You can only send testing emails to your own email address. To send emails to other recipients, please verify a domain at resend.com/domains.",
            },
        )
        with unittest.mock.patch("urllib.request.urlopen", side_effect=err) as mock_open:
            resp = client.post(
                "/api/auth/register/request-otp",
                json={"full_name": "Restricted Recipient", "email": email, "password": "Password123!"},
            )
        self.assertEqual(resp.status_code, 502)
        self.assertIn("Sender domain is not verified for external recipients", resp.json()["detail"])
        self.assertEqual(mock_open.call_count, 1)

    def test_06_resend_4xx_invalid_api_key_no_retry(self):
        email = self._new_email()
        err = _mock_http_error(401, {"name": "validation_error", "message": "API key is invalid"})
        with unittest.mock.patch("urllib.request.urlopen", side_effect=err) as mock_open:
            resp = client.post(
                "/api/auth/register/request-otp",
                json={"full_name": "Invalid Key", "email": email, "password": "Password123!"},
            )
        self.assertEqual(resp.status_code, 502)
        self.assertIn("API key was rejected", resp.json()["detail"])
        self.assertEqual(mock_open.call_count, 1)

    def test_07_resend_5xx_retries_and_succeeds_without_duplicate(self):
        email = self._new_email()
        side_effects = [
            _mock_http_error(500, {"message": "Internal Server Error"}),
            _mock_http_response(200, {"id": "re_retry_ok"}),
        ]
        with unittest.mock.patch("time.sleep"):
            with unittest.mock.patch("urllib.request.urlopen", side_effect=side_effects) as mock_open:
                resp = client.post(
                    "/api/auth/register/request-otp",
                    json={"full_name": "Retry OK", "email": email, "password": "Password123!"},
                )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["provider_message_id"], "re_retry_ok")
        self.assertEqual(mock_open.call_count, 2)

    def test_08_network_timeout_retries_then_returns_502_and_preserves_otp(self):
        email = self._new_email()
        with unittest.mock.patch("time.sleep"):
            with unittest.mock.patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")) as mock_open:
                resp = client.post(
                    "/api/auth/register/request-otp",
                    json={"full_name": "Timeout User", "email": email, "password": "Password123!"},
                )
        self.assertEqual(resp.status_code, 502)
        self.assertIn("Email delivery could not be confirmed", resp.json()["detail"])
        self.assertEqual(mock_open.call_count, 3)

        challenge = self.db.query(models.OtpChallenge).filter(
            models.OtpChallenge.email == email,
            models.OtpChallenge.purpose == PURPOSE_REGISTRATION,
        ).first()
        self.assertIsNotNone(challenge)
        self.assertFalse(challenge.consumed)

    def test_09_email_provider_disabled_returns_503(self):
        email = self._new_email()
        settings.EMAIL_PROVIDER = "NONE"
        resp = client.post(
            "/api/auth/register/request-otp",
            json={"full_name": "Disabled Provider", "email": email, "password": "Password123!"},
        )
        self.assertEqual(resp.status_code, 503)
        self.assertIn("Email provider configuration is missing", resp.json()["detail"])

    def test_10_otp_remains_valid_and_verifiable_after_transient_failure(self):
        email = self._new_email()
        captured_code = {}
        orig_send = email_service.send_otp_email

        def capture_and_fail(to_email, otp_code, purpose, correlation_id=None):
            captured_code["otp"] = otp_code
            return orig_send(to_email, otp_code, purpose, correlation_id=correlation_id)

        with unittest.mock.patch("time.sleep"):
            with unittest.mock.patch.object(email_service, "send_otp_email", side_effect=capture_and_fail):
                with unittest.mock.patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
                    req_resp = client.post(
                        "/api/auth/register/request-otp",
                        json={"full_name": "Verify After Fail", "email": email, "password": "Password123!"},
                    )
        self.assertEqual(req_resp.status_code, 502)
        self.assertIn("otp", captured_code)

        # Verify the preserved OTP still works
        verify_resp = client.post(
            "/api/auth/register/verify-otp",
            json={"email": email, "otp": captured_code["otp"]},
        )
        self.assertEqual(verify_resp.status_code, 200)
        self.assertIn("access_token", verify_resp.json())

    def test_11_resend_cooldown_enforced(self):
        email = self._new_email()
        with unittest.mock.patch(
            "urllib.request.urlopen",
            return_value=_mock_http_response(200, {"id": "re_cd_1"}),
        ):
            r1 = client.post(
                "/api/auth/register/request-otp",
                json={"full_name": "Cooldown User", "email": email, "password": "Password123!"},
            )
            r2 = client.post(
                "/api/auth/register/request-otp",
                json={"full_name": "Cooldown User", "email": email, "password": "Password123!"},
            )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 429)
        self.assertIn("wait", r2.json()["detail"].lower())

    def test_12_duplicate_registration_anti_enumeration_no_email_sent(self):
        email = self._new_email()
        captured = {}
        orig_send = email_service.send_otp_email

        def capture_send(to_email, otp_code, purpose, correlation_id=None):
            captured["otp"] = otp_code
            return orig_send(to_email, otp_code, purpose, correlation_id=correlation_id)

        with unittest.mock.patch.object(email_service, "send_otp_email", side_effect=capture_send):
            with unittest.mock.patch(
                "urllib.request.urlopen",
                return_value=_mock_http_response(200, {"id": "re_dup_1"}),
            ):
                client.post(
                    "/api/auth/register/request-otp",
                    json={"full_name": "Dup User", "email": email, "password": "Password123!"},
                )
        v_resp = client.post("/api/auth/register/verify-otp", json={"email": email, "otp": captured["otp"]})
        self.assertEqual(v_resp.status_code, 200)

        with unittest.mock.patch("urllib.request.urlopen") as mock_open:
            dup_resp = client.post(
                "/api/auth/register/request-otp",
                json={"full_name": "Dup User 2", "email": email, "password": "Password123!"},
            )
        self.assertEqual(dup_resp.status_code, 200)
        mock_open.assert_not_called()

    def test_13_otp_verification_after_successful_resend_delivery(self):
        email = self._new_email()
        captured = {}
        orig_send = email_service.send_otp_email

        def capture_send(to_email, otp_code, purpose, correlation_id=None):
            captured["otp"] = otp_code
            return orig_send(to_email, otp_code, purpose, correlation_id=correlation_id)

        with unittest.mock.patch.object(email_service, "send_otp_email", side_effect=capture_send):
            with unittest.mock.patch(
                "urllib.request.urlopen",
                return_value=_mock_http_response(200, {"id": "re_e2e_1"}),
            ):
                req_resp = client.post(
                    "/api/auth/register/request-otp",
                    json={"full_name": "E2E User", "email": email, "password": "Password123!"},
                )
        self.assertEqual(req_resp.status_code, 200)

        verify_resp = client.post(
            "/api/auth/register/verify-otp",
            json={"email": email, "otp": captured["otp"]},
        )
        self.assertEqual(verify_resp.status_code, 200)
        self.assertEqual(verify_resp.json()["email"], email)
        self.assertEqual(verify_resp.json()["role"], "USER")


if __name__ == "__main__":
    unittest.main()
