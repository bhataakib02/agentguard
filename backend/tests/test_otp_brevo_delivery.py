"""
Comprehensive Automated Tests for Brevo Transactional Email & OTP Delivery
===========================================================================
Uses mocked urllib.request.urlopen responses so ZERO real emails are sent.
"""

import io
import json
import logging
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
from core import security
import models
from services.email_service import email_service
from services.otp_service import PURPOSE_REGISTRATION

client = TestClient(app)


def _mock_http_response(status_code: int, raw_body: bytes):
    resp = unittest.mock.MagicMock()
    resp.status = status_code
    resp.read.return_value = raw_body
    resp.__enter__ = unittest.mock.MagicMock(return_value=resp)
    resp.__exit__ = unittest.mock.MagicMock(return_value=False)
    return resp


def _mock_json_response(status_code: int, payload: dict):
    return _mock_http_response(status_code, json.dumps(payload).encode("utf-8"))


def _mock_http_error(status_code: int, payload: dict):
    raw = json.dumps(payload).encode("utf-8")
    return urllib.error.HTTPError(
        url="https://api.brevo.com/v3/smtp/email",
        code=status_code,
        msg="Error",
        hdrs=None,
        fp=io.BytesIO(raw),
    )


class _LogCaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(self.format(record))


class TestOtpBrevoDelivery(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.orig_provider = settings.EMAIL_PROVIDER
        self.orig_brevo_key = settings.BREVO_API_KEY
        self.orig_brevo_from = settings.BREVO_FROM_EMAIL
        self.orig_brevo_name = settings.BREVO_FROM_NAME
        self.orig_resend_key = settings.RESEND_API_KEY
        self.orig_resend_from = settings.RESEND_FROM_EMAIL

        settings.EMAIL_PROVIDER = "BREVO"
        settings.BREVO_API_KEY = "xkeysib-test-mock-key-never-logged"
        settings.BREVO_FROM_EMAIL = "noreply@verified-agentguard.example"
        settings.BREVO_FROM_NAME = "AGENTGUARD"

    def tearDown(self):
        settings.EMAIL_PROVIDER = self.orig_provider
        settings.BREVO_API_KEY = self.orig_brevo_key
        settings.BREVO_FROM_EMAIL = self.orig_brevo_from
        settings.BREVO_FROM_NAME = self.orig_brevo_name
        settings.RESEND_API_KEY = self.orig_resend_key
        settings.RESEND_FROM_EMAIL = self.orig_resend_from
        self.db.close()

    def _new_email(self) -> str:
        return f"brevo_{uuid.uuid4().hex[:8]}@example.com"

    def _create_active_user(self, email: str):
        org = models.Organization(name=f"Org {uuid.uuid4().hex[:6]}")
        self.db.add(org)
        self.db.flush()
        user = models.User(
            org_id=org.id,
            email=email,
            password_hash=security.get_password_hash("Password123!"),
            full_name="Active Brevo User",
            role="USER",
            status="ACTIVE",
        )
        self.db.add(user)
        self.db.commit()
        return user

    def test_01_successful_brevo_api_response(self):
        email = self._new_email()
        captured_req = {}

        def fake_urlopen(req, timeout=10):
            captured_req["url"] = req.full_url
            captured_req["headers"] = dict(req.header_items())
            captured_req["body"] = json.loads(req.data.decode("utf-8"))
            captured_req["timeout"] = timeout
            return _mock_json_response(201, {"messageId": "<brevo-msg-001@smtp-relay.mailin.fr>"})

        with unittest.mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            res = email_service.send_email(email, "Test Subject", "Plain text", "<p>HTML</p>", correlation_id="corr-01")

        self.assertTrue(res["accepted"])
        self.assertEqual(res["provider"], "BREVO")
        self.assertEqual(res["delivery_stage"], "ACCEPTED_BY_PROVIDER")
        self.assertFalse(res["delivery_confirmed"])
        self.assertEqual(res["id"], "<brevo-msg-001@smtp-relay.mailin.fr>")
        self.assertEqual(res["http_status"], 201)
        self.assertEqual(res["correlation_id"], "corr-01")
        self.assertEqual(captured_req["url"], "https://api.brevo.com/v3/smtp/email")
        self.assertEqual(captured_req["body"]["sender"], {"name": "AGENTGUARD", "email": "noreply@verified-agentguard.example"})
        self.assertEqual(captured_req["body"]["to"], [{"email": email}])
        self.assertEqual(captured_req["timeout"], 10)

    def test_02_missing_api_key_returns_503(self):
        email = self._new_email()
        settings.BREVO_API_KEY = ""
        resp = client.post(
            "/api/auth/register/request-otp",
            json={"full_name": "No Key", "email": email, "password": "Password123!"},
        )
        self.assertEqual(resp.status_code, 503)
        self.assertIn("Email provider configuration is missing", resp.json()["detail"])

    def test_03_invalid_api_key_returns_502_no_retry(self):
        email = self._new_email()
        err = _mock_http_error(401, {"code": "unauthorized", "message": "Key not found"})
        with unittest.mock.patch("urllib.request.urlopen", side_effect=err) as mock_open:
            resp = client.post(
                "/api/auth/register/request-otp",
                json={"full_name": "Bad Key", "email": email, "password": "Password123!"},
            )
        self.assertEqual(resp.status_code, 502)
        self.assertIn("API key was rejected", resp.json()["detail"])
        self.assertEqual(mock_open.call_count, 1)

    def test_04_invalid_sender_rejected_without_network_call(self):
        email = self._new_email()
        settings.BREVO_FROM_EMAIL = "invalid-sender-email"
        with unittest.mock.patch("urllib.request.urlopen") as mock_open:
            resp = client.post(
                "/api/auth/register/request-otp",
                json={"full_name": "Bad Sender", "email": email, "password": "Password123!"},
            )
        self.assertEqual(resp.status_code, 502)
        self.assertIn("sender email address is invalid", resp.json()["detail"].lower())
        mock_open.assert_not_called()

    def test_05_unverified_sender_returns_502_no_retry(self):
        email = self._new_email()
        err = _mock_http_error(400, {"code": "invalid_parameter", "message": "Sender email is not verified in Brevo."})
        with unittest.mock.patch("urllib.request.urlopen", side_effect=err) as mock_open:
            resp = client.post(
                "/api/auth/register/request-otp",
                json={"full_name": "Unverified", "email": email, "password": "Password123!"},
            )
        self.assertEqual(resp.status_code, 502)
        self.assertIn("Sender address or domain is not verified", resp.json()["detail"])
        self.assertEqual(mock_open.call_count, 1)

    def test_06_recipient_rejection_returns_502_no_retry(self):
        email = self._new_email()
        err = _mock_http_error(400, {"code": "invalid_parameter", "message": "Recipient email is blacklisted."})
        with unittest.mock.patch("urllib.request.urlopen", side_effect=err) as mock_open:
            resp = client.post(
                "/api/auth/register/request-otp",
                json={"full_name": "Rejected", "email": email, "password": "Password123!"},
            )
        self.assertEqual(resp.status_code, 502)
        self.assertIn("Recipient address was rejected", resp.json()["detail"])
        self.assertEqual(mock_open.call_count, 1)

    def test_07_brevo_http_4xx_no_retry(self):
        email = self._new_email()
        err = _mock_http_error(422, {"code": "bad_request", "message": "Malformed payload"})
        with unittest.mock.patch("urllib.request.urlopen", side_effect=err) as mock_open:
            resp = client.post(
                "/api/auth/register/request-otp",
                json={"full_name": "HTTP 4xx", "email": email, "password": "Password123!"},
            )
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(mock_open.call_count, 1)

    def test_08_brevo_http_5xx_retries_and_returns_502(self):
        email = self._new_email()
        err = _mock_http_error(503, {"message": "Service Unavailable"})
        with unittest.mock.patch("time.sleep"):
            with unittest.mock.patch("urllib.request.urlopen", side_effect=err) as mock_open:
                resp = client.post(
                    "/api/auth/register/request-otp",
                    json={"full_name": "HTTP 5xx", "email": email, "password": "Password123!"},
                )
        self.assertEqual(resp.status_code, 502)
        self.assertIn("Email delivery could not be confirmed", resp.json()["detail"])
        self.assertEqual(mock_open.call_count, 3)

    def test_09_network_timeout_returns_502_without_provider_fallback(self):
        email = self._new_email()
        settings.RESEND_API_KEY = "re_should_never_be_called"
        with unittest.mock.patch("time.sleep"):
            with unittest.mock.patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")) as mock_open:
                with unittest.mock.patch.object(email_service, "_send_resend") as mock_resend:
                    resp = client.post(
                        "/api/auth/register/request-otp",
                        json={"full_name": "Timeout", "email": email, "password": "Password123!"},
                    )
        self.assertEqual(resp.status_code, 502)
        self.assertEqual(mock_open.call_count, 3)
        mock_resend.assert_not_called()

    def test_10_malformed_api_response_handled_safely_no_retry(self):
        email = self._new_email()
        with unittest.mock.patch(
            "urllib.request.urlopen",
            return_value=_mock_http_response(201, b"not-valid-json"),
        ) as mock_open:
            resp = client.post(
                "/api/auth/register/request-otp",
                json={"full_name": "Malformed", "email": email, "password": "Password123!"},
            )
        self.assertEqual(resp.status_code, 502)
        self.assertIn("unexpected response", resp.json()["detail"].lower())
        self.assertEqual(mock_open.call_count, 1)

    def test_11_provider_disabled_returns_503(self):
        email = self._new_email()
        settings.EMAIL_PROVIDER = "NONE"
        resp = client.post(
            "/api/auth/register/request-otp",
            json={"full_name": "Disabled", "email": email, "password": "Password123!"},
        )
        self.assertEqual(resp.status_code, 503)
        self.assertIn("Email provider configuration is missing", resp.json()["detail"])

    def test_12_registration_otp_uses_brevo(self):
        email = self._new_email()
        with unittest.mock.patch(
            "urllib.request.urlopen",
            return_value=_mock_json_response(201, {"messageId": "<reg-brevo-1>"}),
        ) as mock_open:
            resp = client.post(
                "/api/auth/register/request-otp",
                json={"full_name": "Reg Brevo", "email": email, "password": "Password123!"},
            )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["delivery_status"], "ACCEPTED_FOR_SENDING")
        self.assertEqual(data["provider_message_id"], "<reg-brevo-1>")
        self.assertEqual(mock_open.call_args[0][0].full_url, "https://api.brevo.com/v3/smtp/email")

    def test_13_password_reset_otp_uses_brevo(self):
        email = self._new_email()
        self._create_active_user(email)
        with unittest.mock.patch(
            "urllib.request.urlopen",
            return_value=_mock_json_response(201, {"messageId": "<reset-brevo-1>"}),
        ) as mock_open:
            resp = client.post("/api/auth/forgot-password/request-otp", json={"email": email})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["provider_message_id"], "<reset-brevo-1>")
        self.assertEqual(mock_open.call_args[0][0].full_url, "https://api.brevo.com/v3/smtp/email")

    def test_14_passwordless_login_otp_uses_brevo(self):
        email = self._new_email()
        self._create_active_user(email)
        with unittest.mock.patch(
            "urllib.request.urlopen",
            return_value=_mock_json_response(201, {"messageId": "<login-brevo-1>"}),
        ) as mock_open:
            resp = client.post("/api/auth/login/request-otp", json={"email": email})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["provider_message_id"], "<login-brevo-1>")
        self.assertEqual(mock_open.call_args[0][0].full_url, "https://api.brevo.com/v3/smtp/email")

    def test_15_existing_resend_integration_still_works(self):
        email = self._new_email()
        settings.EMAIL_PROVIDER = "RESEND"
        settings.RESEND_API_KEY = "re_test_mock_key"
        settings.RESEND_FROM_EMAIL = "AgentGuard <noreply@verified-domain.example>"
        with unittest.mock.patch(
            "urllib.request.urlopen",
            return_value=_mock_json_response(200, {"id": "re_ok_123"}),
        ) as mock_open:
            resp = client.post(
                "/api/auth/register/request-otp",
                json={"full_name": "Resend Still Works", "email": email, "password": "Password123!"},
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["provider_message_id"], "re_ok_123")
        self.assertEqual(mock_open.call_args[0][0].full_url, "https://api.resend.com/emails")

    def test_16_no_otp_or_secret_appears_in_logs(self):
        email = self._new_email()
        otp_secret = "948271"
        handler = _LogCaptureHandler()
        email_logger = logging.getLogger("agentguard.email_service")
        email_logger.addHandler(handler)
        email_logger.setLevel(logging.INFO)
        try:
            with unittest.mock.patch(
                "urllib.request.urlopen",
                return_value=_mock_json_response(201, {"messageId": "<log-check-1>"}),
            ):
                email_service.send_otp_email(email, otp_secret, PURPOSE_REGISTRATION, correlation_id="corr-log")
        finally:
            email_logger.removeHandler(handler)

        joined = "\n".join(handler.messages)
        self.assertNotIn(otp_secret, joined)
        self.assertNotIn(settings.BREVO_API_KEY, joined)
        self.assertIn("corr-log", joined)

    def test_17_no_duplicate_dispatch_on_transient_retry_success(self):
        email = self._new_email()
        side_effects = [
            _mock_http_error(502, {"message": "Bad Gateway"}),
            _mock_json_response(201, {"messageId": "<brevo-retry-ok>"}),
        ]
        with unittest.mock.patch("time.sleep"):
            with unittest.mock.patch("urllib.request.urlopen", side_effect=side_effects) as mock_open:
                resp = client.post(
                    "/api/auth/register/request-otp",
                    json={"full_name": "Retry Safe", "email": email, "password": "Password123!"},
                )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["provider_message_id"], "<brevo-retry-ok>")
        self.assertEqual(mock_open.call_count, 2)

    def test_18_failed_email_delivery_preserves_otp_challenge(self):
        email = self._new_email()
        captured = {}
        orig_send = email_service.send_otp_email

        def capture_and_fail(to_email, otp_code, purpose, correlation_id=None):
            captured["otp"] = otp_code
            return orig_send(to_email, otp_code, purpose, correlation_id=correlation_id)

        with unittest.mock.patch("time.sleep"):
            with unittest.mock.patch.object(email_service, "send_otp_email", side_effect=capture_and_fail):
                with unittest.mock.patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
                    req_resp = client.post(
                        "/api/auth/register/request-otp",
                        json={"full_name": "Preserved OTP", "email": email, "password": "Password123!"},
                    )
        self.assertEqual(req_resp.status_code, 502)

        verify_resp = client.post(
            "/api/auth/register/verify-otp",
            json={"email": email, "otp": captured["otp"]},
        )
        self.assertEqual(verify_resp.status_code, 200)
        self.assertIn("access_token", verify_resp.json())


if __name__ == "__main__":
    unittest.main()
