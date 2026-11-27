"""
Phase 6D & Final Auth: Email Provider Abstraction for AgentGuard
Handles transactional email delivery (invitations, report attachments, OTP challenges, approval escalations)
supporting Resend REST API, SMTP, and Mock providers with strict credential protection and truthful status.
"""

import datetime
import re
import time
import uuid
import smtplib
import ssl
import json
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Optional, Dict, Any, List
import logging
from config import settings

logger = logging.getLogger("agentguard.email_service")

EMAIL_REGEX = re.compile(r"^[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+$")


def _extract_email_address(sender: str) -> str:
    """Extracts bare email address from 'Display Name <addr@domain>' or 'addr@domain'."""
    if not sender:
        return ""
    match = re.search(r"<([^>]+)>", sender)
    return (match.group(1) if match else sender).strip()


def _utc_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class EmailService:
    def __init__(self):
        self.sent_emails_mock: List[Dict[str, Any]] = []

    def is_brevo_configured(self) -> bool:
        """Returns True if BREVO_API_KEY is provisioned."""
        return bool(getattr(settings, "BREVO_API_KEY", "").strip())

    def is_resend_configured(self) -> bool:
        """Returns True if RESEND_API_KEY is provisioned."""
        return bool(getattr(settings, "RESEND_API_KEY", "").strip())

    def is_smtp_configured(self) -> bool:
        """Returns True if SMTP_HOST and SMTP_PORT are provisioned."""
        return bool(settings.SMTP_HOST and settings.SMTP_PORT)

    def is_configured(self) -> bool:
        """Returns True only if an email provider is explicitly configured."""
        if settings.EMAIL_PROVIDER in ("NONE", "DISABLED"):
            return False
        if settings.EMAIL_PROVIDER == "MOCK":
            return True
        if settings.EMAIL_PROVIDER == "BREVO":
            return self.is_brevo_configured()
        if settings.EMAIL_PROVIDER == "RESEND":
            return self.is_resend_configured()
        if settings.EMAIL_PROVIDER == "SMTP":
            return self.is_smtp_configured()
        # Fallback detection if EMAIL_PROVIDER is unset
        if not settings.EMAIL_PROVIDER:
            return self.is_brevo_configured() or self.is_resend_configured() or self.is_smtp_configured()
        return False

    def get_status(self) -> Dict[str, Any]:
        """
        Truthfully returns email provider configuration state without exposing passwords or API keys.
        """
        configured = self.is_configured()
        provider_name = settings.EMAIL_PROVIDER

        if provider_name in ("NONE", "DISABLED") or not provider_name:
            if not configured:
                provider_name = "NONE"
            elif self.is_brevo_configured():
                provider_name = "BREVO"
            elif self.is_resend_configured():
                provider_name = "RESEND"
            elif self.is_smtp_configured():
                provider_name = "SMTP"
            else:
                provider_name = "NONE"

        brevo_from = getattr(settings, "BREVO_FROM_EMAIL", "").strip() or None if self.is_brevo_configured() else None
        brevo_name = getattr(settings, "BREVO_FROM_NAME", "AGENTGUARD") if self.is_brevo_configured() else None
        resend_from = getattr(settings, "RESEND_FROM_EMAIL", "onboarding@resend.dev") if self.is_resend_configured() else None
        sandbox_mode = bool(provider_name == "RESEND" and resend_from and "onboarding@resend.dev" in resend_from.lower())

        active_from = settings.SMTP_FROM_EMAIL
        if provider_name == "BREVO":
            active_from = brevo_from
        elif provider_name == "RESEND":
            active_from = resend_from

        return {
            "configured": configured,
            "provider": provider_name if configured else "NONE",
            "status": "HEALTHY" if configured else "NOT_CONFIGURED",
            "brevo_configured": self.is_brevo_configured(),
            "brevo_from_email": brevo_from,
            "brevo_from_name": brevo_name,
            "resend_configured": self.is_resend_configured(),
            "resend_from_email": resend_from,
            "resend_sandbox_mode": sandbox_mode,
            "smtp_configured": self.is_smtp_configured(),
            "smtp_host": settings.SMTP_HOST if settings.SMTP_HOST else None,
            "smtp_port": settings.SMTP_PORT if settings.SMTP_HOST else None,
            "from_email": active_from,
            "tls_enabled": settings.SMTP_USE_TLS
        }

    @staticmethod
    def _classify_brevo_http_error(status_code: int, raw_body: str) -> Dict[str, str]:
        """Parses and sanitizes a Brevo HTTP error response into structured error_code and message."""
        parsed_code = ""
        parsed_msg = ""
        try:
            err_json = json.loads(raw_body)
            if isinstance(err_json, dict):
                parsed_code = str(err_json.get("code", "")).strip()
                parsed_msg = str(err_json.get("message", "")).strip()
        except Exception:
            parsed_msg = raw_body[:300].strip()

        combined = f"{parsed_code} {parsed_msg}".lower()
        if status_code == 401 or "unauthorized" in combined or "api-key" in combined or "key not found" in combined:
            return {
                "error_code": "INVALID_API_KEY",
                "sanitized_message": parsed_msg or "Brevo API key was rejected (HTTP 401)."
            }
        if status_code in (400, 403, 422) and (
            "unverified" in combined or "not verified" in combined or "not validated" in combined or "verify" in combined
        ):
            return {
                "error_code": "UNVERIFIED_SENDER",
                "sanitized_message": parsed_msg or "Brevo sender email or domain is not verified."
            }
        if status_code in (400, 403, 422) and (
            "recipient" in combined or "blacklisted" in combined or "blocked" in combined or "invalid email" in combined
        ):
            return {
                "error_code": "RECIPIENT_REJECTED",
                "sanitized_message": parsed_msg or "Recipient email address was rejected by Brevo."
            }
        if status_code in (400, 422) and ("sender" in combined or "from" in combined):
            return {
                "error_code": "INVALID_SENDER",
                "sanitized_message": parsed_msg or "Brevo sender email address is invalid."
            }
        if status_code == 429:
            return {
                "error_code": "BREVO_RATE_LIMITED",
                "sanitized_message": parsed_msg or "Brevo API rate limit exceeded."
            }
        if 500 <= status_code < 600:
            return {
                "error_code": "BREVO_5XX",
                "sanitized_message": parsed_msg or f"Brevo server error (HTTP {status_code})."
            }
        return {
            "error_code": parsed_code.upper() or f"BREVO_{status_code}",
            "sanitized_message": parsed_msg or f"Brevo API rejected request with HTTP {status_code}."
        }

    def _send_brevo(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        correlation_id: Optional[str] = None,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.3
    ) -> Dict[str, Any]:
        """
        Sends a transactional email using Brevo REST API (POST https://api.brevo.com/v3/smtp/email).
        - Enforces request timeout (10s).
        - Retries ONLY on transient failures (HTTP 5xx or network/timeout errors) to avoid duplicate emails.
        - Never retries on deterministic 4xx rejections or malformed 2xx responses.
        - Never logs or exposes BREVO_API_KEY, api-key headers, passwords, or OTP codes.
        """
        corr_id = correlation_id or uuid.uuid4().hex[:12]
        ts = _utc_iso()
        brevo_key = getattr(settings, "BREVO_API_KEY", "").strip()
        if not brevo_key:
            logger.warning(
                f"[EmailService] corr_id={corr_id} ts={ts} provider=BREVO stage=PROVIDER_NOT_CONFIGURED "
                f"error_code=MISSING_API_KEY recipient={to_email}"
            )
            return {
                "status": "EMAIL_PROVIDER_NOT_CONFIGURED",
                "delivery_stage": "PROVIDER_NOT_CONFIGURED",
                "accepted": False,
                "delivered": False,
                "delivery_confirmed": False,
                "provider": "BREVO",
                "recipient": to_email,
                "error_code": "MISSING_API_KEY",
                "error": "BREVO_API_KEY is not configured",
                "http_status": None,
                "correlation_id": corr_id,
                "timestamp": ts,
            }

        raw_from = getattr(settings, "BREVO_FROM_EMAIL", "").strip()
        bare_from = _extract_email_address(raw_from)
        if not bare_from or not EMAIL_REGEX.match(bare_from):
            logger.error(
                f"[EmailService] corr_id={corr_id} ts={ts} provider=BREVO stage=REJECTED_BY_PROVIDER "
                f"error_code=INVALID_SENDER recipient={to_email}"
            )
            return {
                "status": "EMAIL_DELIVERY_FAILED",
                "delivery_stage": "REJECTED_BY_PROVIDER",
                "accepted": False,
                "delivered": False,
                "delivery_confirmed": False,
                "provider": "BREVO",
                "recipient": to_email,
                "error_code": "INVALID_SENDER",
                "error": "BREVO_FROM_EMAIL is missing or not a valid email address.",
                "http_status": None,
                "correlation_id": corr_id,
                "timestamp": ts,
            }

        from_name = getattr(settings, "BREVO_FROM_NAME", "AGENTGUARD").strip() or "AGENTGUARD"
        url = "https://api.brevo.com/v3/smtp/email"
        payload: Dict[str, Any] = {
            "sender": {"name": from_name, "email": bare_from},
            "to": [{"email": to_email}],
            "subject": subject,
            "textContent": body_text,
            "htmlContent": body_html or f"<pre>{body_text}</pre>",
        }

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "api-key": brevo_key,
            "Content-Type": "application/json",
            "accept": "application/json",
            "User-Agent": "AgentGuard-Backend/1.0",
        }

        last_result: Optional[Dict[str, Any]] = None
        for attempt in range(max_retries + 1):
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            attempt_ts = _utc_iso()
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    http_status = getattr(resp, "status", 201)
                    resp_bytes = resp.read()
                    try:
                        resp_data = json.loads(resp_bytes.decode("utf-8"))
                    except Exception:
                        resp_data = None

                    message_id = resp_data.get("messageId") if isinstance(resp_data, dict) else None
                    if not isinstance(resp_data, dict) or not message_id or not isinstance(message_id, str):
                        logger.error(
                            f"[EmailService] corr_id={corr_id} ts={attempt_ts} provider=BREVO "
                            f"stage=DELIVERY_UNCONFIRMED http_status={http_status} "
                            f"error_code=MALFORMED_RESPONSE recipient={to_email} attempt={attempt + 1}"
                        )
                        return {
                            "status": "EMAIL_DELIVERY_FAILED",
                            "delivery_stage": "DELIVERY_UNCONFIRMED",
                            "accepted": False,
                            "delivered": False,
                            "delivery_confirmed": False,
                            "provider": "BREVO",
                            "recipient": to_email,
                            "error_code": "MALFORMED_RESPONSE",
                            "error": "Brevo returned a malformed or incomplete response without messageId.",
                            "http_status": http_status,
                            "correlation_id": corr_id,
                            "timestamp": attempt_ts,
                        }

                    logger.info(
                        f"[EmailService] corr_id={corr_id} ts={attempt_ts} provider=BREVO "
                        f"stage=ACCEPTED_BY_PROVIDER http_status={http_status} brevo_message_id={message_id} "
                        f"recipient={to_email} attempt={attempt + 1}"
                    )
                    return {
                        "status": "EMAIL_SENT",
                        "delivery_stage": "ACCEPTED_BY_PROVIDER",
                        "accepted": True,
                        "delivered": True,
                        "delivery_confirmed": False,
                        "provider": "BREVO",
                        "recipient": to_email,
                        "id": message_id,
                        "http_status": http_status,
                        "correlation_id": corr_id,
                        "timestamp": attempt_ts,
                    }
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                classified = self._classify_brevo_http_error(e.code, err_body)
                is_transient = e.code >= 500
                stage = "TRANSIENT_FAILURE" if is_transient else "REJECTED_BY_PROVIDER"
                logger.error(
                    f"[EmailService] corr_id={corr_id} ts={attempt_ts} provider=BREVO stage={stage} "
                    f"http_status={e.code} error_code={classified['error_code']} "
                    f"message={classified['sanitized_message']!r} recipient={to_email} attempt={attempt + 1}"
                )
                last_result = {
                    "status": "EMAIL_DELIVERY_FAILED",
                    "delivery_stage": stage,
                    "accepted": False,
                    "delivered": False,
                    "delivery_confirmed": False,
                    "provider": "BREVO",
                    "error_code": classified["error_code"],
                    "error": classified["sanitized_message"],
                    "http_status": e.code,
                    "recipient": to_email,
                    "correlation_id": corr_id,
                    "timestamp": attempt_ts,
                }
                if not is_transient:
                    return last_result
            except (TimeoutError, urllib.error.URLError) as e:
                is_timeout = isinstance(e, TimeoutError) or (
                    isinstance(e, urllib.error.URLError) and isinstance(getattr(e, "reason", None), TimeoutError)
                ) or "timed out" in str(e).lower()
                err_code = "NETWORK_TIMEOUT" if is_timeout else "NETWORK_ERROR"
                logger.error(
                    f"[EmailService] corr_id={corr_id} ts={attempt_ts} provider=BREVO stage=TRANSIENT_FAILURE "
                    f"error_code={err_code} error_type={type(e).__name__} recipient={to_email} attempt={attempt + 1}"
                )
                last_result = {
                    "status": "EMAIL_DELIVERY_FAILED",
                    "delivery_stage": "TRANSIENT_FAILURE",
                    "accepted": False,
                    "delivered": False,
                    "delivery_confirmed": False,
                    "provider": "BREVO",
                    "error_code": err_code,
                    "error": f"{type(e).__name__}: {str(e)}",
                    "http_status": None,
                    "recipient": to_email,
                    "correlation_id": corr_id,
                    "timestamp": attempt_ts,
                }
            except Exception as e:
                logger.error(
                    f"[EmailService] corr_id={corr_id} ts={attempt_ts} provider=BREVO stage=TRANSIENT_FAILURE "
                    f"error_code=NETWORK_ERROR error_type={type(e).__name__} recipient={to_email} attempt={attempt + 1}"
                )
                last_result = {
                    "status": "EMAIL_DELIVERY_FAILED",
                    "delivery_stage": "TRANSIENT_FAILURE",
                    "accepted": False,
                    "delivered": False,
                    "delivery_confirmed": False,
                    "provider": "BREVO",
                    "error_code": "NETWORK_ERROR",
                    "error": f"{type(e).__name__}: {str(e)}",
                    "http_status": None,
                    "recipient": to_email,
                    "correlation_id": corr_id,
                    "timestamp": attempt_ts,
                }

            if attempt < max_retries and retry_backoff_seconds > 0:
                time.sleep(retry_backoff_seconds * (attempt + 1))

        return last_result or {
            "status": "EMAIL_DELIVERY_FAILED",
            "delivery_stage": "TRANSIENT_FAILURE",
            "accepted": False,
            "delivered": False,
            "delivery_confirmed": False,
            "provider": "BREVO",
            "error_code": "NETWORK_ERROR",
            "error": "Brevo delivery failed after retries",
            "http_status": None,
            "recipient": to_email,
            "correlation_id": corr_id,
            "timestamp": ts,
        }

    @staticmethod
    def _classify_resend_http_error(status_code: int, raw_body: str) -> Dict[str, str]:
        """Parses and sanitizes a Resend HTTP error response into structured error_code and message."""
        parsed_name = ""
        parsed_msg = ""
        try:
            err_json = json.loads(raw_body)
            if isinstance(err_json, dict):
                parsed_name = str(err_json.get("name", "")).strip()
                parsed_msg = str(err_json.get("message", "")).strip()
        except Exception:
            parsed_msg = raw_body[:300].strip()

        msg_lower = parsed_msg.lower()
        if status_code == 401 or "api key" in msg_lower or "unauthorized" in msg_lower:
            return {
                "error_code": "INVALID_API_KEY",
                "sanitized_message": parsed_msg or "Resend API key was rejected (HTTP 401)."
            }
        if status_code == 403 and ("only send testing emails to your own email" in msg_lower or "resend.dev" in msg_lower):
            return {
                "error_code": "RECIPIENT_RESTRICTED",
                "sanitized_message": parsed_msg or "Resend sandbox sender (onboarding@resend.dev) can only deliver to the Resend account owner."
            }
        if status_code in (403, 422) and ("verify" in msg_lower and "domain" in msg_lower):
            return {
                "error_code": "UNVERIFIED_SENDER_DOMAIN",
                "sanitized_message": parsed_msg or "Sender domain is not verified in Resend."
            }
        if status_code == 422 and ("from" in msg_lower or "sender" in msg_lower):
            return {
                "error_code": "INVALID_SENDER",
                "sanitized_message": parsed_msg or "Sender email address is invalid."
            }
        if status_code == 429:
            return {
                "error_code": "RESEND_RATE_LIMITED",
                "sanitized_message": parsed_msg or "Resend API rate limit exceeded."
            }
        if 500 <= status_code < 600:
            return {
                "error_code": "RESEND_5XX",
                "sanitized_message": parsed_msg or f"Resend server error (HTTP {status_code})."
            }
        return {
            "error_code": parsed_name.upper() or f"RESEND_{status_code}",
            "sanitized_message": parsed_msg or f"Resend API rejected request with HTTP {status_code}."
        }

    def _send_resend(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        correlation_id: Optional[str] = None,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.3
    ) -> Dict[str, Any]:
        """
        Sends an email using Resend REST API (https://api.resend.com/emails) via standard urllib.
        - Enforces request timeout (10s).
        - Retries ONLY on transient failures (HTTP 5xx or network/timeout errors) to avoid duplicate emails.
        - Never retries on deterministic 4xx rejections (401, 403, 422).
        - Never logs or exposes RESEND_API_KEY or OTP codes.
        """
        corr_id = correlation_id or uuid.uuid4().hex[:12]
        ts = _utc_iso()
        resend_key = getattr(settings, "RESEND_API_KEY", "").strip()
        if not resend_key:
            logger.warning(
                f"[EmailService] corr_id={corr_id} ts={ts} provider=RESEND stage=PROVIDER_NOT_CONFIGURED "
                f"error_code=MISSING_API_KEY recipient={to_email}"
            )
            return {
                "status": "EMAIL_PROVIDER_NOT_CONFIGURED",
                "delivery_stage": "PROVIDER_NOT_CONFIGURED",
                "accepted": False,
                "delivered": False,
                "delivery_confirmed": False,
                "provider": "RESEND",
                "recipient": to_email,
                "error_code": "MISSING_API_KEY",
                "error": "RESEND_API_KEY is not configured",
                "http_status": None,
                "correlation_id": corr_id,
                "timestamp": ts,
            }

        from_addr = getattr(settings, "RESEND_FROM_EMAIL", "").strip() or "AgentGuard <onboarding@resend.dev>"
        bare_from = _extract_email_address(from_addr)
        if not EMAIL_REGEX.match(bare_from):
            logger.error(
                f"[EmailService] corr_id={corr_id} ts={ts} provider=RESEND stage=REJECTED_BY_PROVIDER "
                f"error_code=INVALID_SENDER recipient={to_email}"
            )
            return {
                "status": "EMAIL_DELIVERY_FAILED",
                "delivery_stage": "REJECTED_BY_PROVIDER",
                "accepted": False,
                "delivered": False,
                "delivery_confirmed": False,
                "provider": "RESEND",
                "recipient": to_email,
                "error_code": "INVALID_SENDER",
                "error": "RESEND_FROM_EMAIL is not a valid email address format.",
                "http_status": None,
                "correlation_id": corr_id,
                "timestamp": ts,
            }

        url = "https://api.resend.com/emails"
        payload: Dict[str, Any] = {
            "from": from_addr,
            "to": [to_email],
            "subject": subject,
            "text": body_text,
        }
        if body_html:
            payload["html"] = body_html

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {resend_key}",
            "Content-Type": "application/json",
            "User-Agent": "AgentGuard-Backend/1.0"
        }

        last_result: Optional[Dict[str, Any]] = None
        for attempt in range(max_retries + 1):
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            attempt_ts = _utc_iso()
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    http_status = getattr(resp, "status", 200)
                    resp_bytes = resp.read()
                    try:
                        resp_data = json.loads(resp_bytes.decode("utf-8"))
                    except Exception:
                        resp_data = {}
                    email_id = resp_data.get("id")
                    logger.info(
                        f"[EmailService] corr_id={corr_id} ts={attempt_ts} provider=RESEND "
                        f"stage=ACCEPTED_BY_PROVIDER http_status={http_status} resend_id={email_id} "
                        f"recipient={to_email} attempt={attempt + 1}"
                    )
                    return {
                        "status": "EMAIL_SENT",
                        "delivery_stage": "ACCEPTED_BY_PROVIDER",
                        "accepted": True,
                        "delivered": True,
                        "delivery_confirmed": False,
                        "provider": "RESEND",
                        "recipient": to_email,
                        "id": email_id,
                        "http_status": http_status,
                        "correlation_id": corr_id,
                        "timestamp": attempt_ts,
                    }
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                classified = self._classify_resend_http_error(e.code, err_body)
                is_transient = e.code >= 500
                stage = "TRANSIENT_FAILURE" if is_transient else "REJECTED_BY_PROVIDER"
                logger.error(
                    f"[EmailService] corr_id={corr_id} ts={attempt_ts} provider=RESEND stage={stage} "
                    f"http_status={e.code} error_code={classified['error_code']} "
                    f"message={classified['sanitized_message']!r} recipient={to_email} attempt={attempt + 1}"
                )
                last_result = {
                    "status": "EMAIL_DELIVERY_FAILED",
                    "delivery_stage": stage,
                    "accepted": False,
                    "delivered": False,
                    "delivery_confirmed": False,
                    "provider": "RESEND",
                    "error_code": classified["error_code"],
                    "error": classified["sanitized_message"],
                    "http_status": e.code,
                    "recipient": to_email,
                    "correlation_id": corr_id,
                    "timestamp": attempt_ts,
                }
                if not is_transient:
                    # Do NOT retry deterministic 4xx rejections
                    return last_result
            except (TimeoutError, urllib.error.URLError) as e:
                is_timeout = isinstance(e, TimeoutError) or (
                    isinstance(e, urllib.error.URLError) and isinstance(getattr(e, "reason", None), TimeoutError)
                ) or "timed out" in str(e).lower()
                err_code = "NETWORK_TIMEOUT" if is_timeout else "NETWORK_ERROR"
                logger.error(
                    f"[EmailService] corr_id={corr_id} ts={attempt_ts} provider=RESEND stage=TRANSIENT_FAILURE "
                    f"error_code={err_code} error_type={type(e).__name__} recipient={to_email} attempt={attempt + 1}"
                )
                last_result = {
                    "status": "EMAIL_DELIVERY_FAILED",
                    "delivery_stage": "TRANSIENT_FAILURE",
                    "accepted": False,
                    "delivered": False,
                    "delivery_confirmed": False,
                    "provider": "RESEND",
                    "error_code": err_code,
                    "error": f"{type(e).__name__}: {str(e)}",
                    "http_status": None,
                    "recipient": to_email,
                    "correlation_id": corr_id,
                    "timestamp": attempt_ts,
                }
            except Exception as e:
                logger.error(
                    f"[EmailService] corr_id={corr_id} ts={attempt_ts} provider=RESEND stage=TRANSIENT_FAILURE "
                    f"error_code=NETWORK_ERROR error_type={type(e).__name__} recipient={to_email} attempt={attempt + 1}"
                )
                last_result = {
                    "status": "EMAIL_DELIVERY_FAILED",
                    "delivery_stage": "TRANSIENT_FAILURE",
                    "accepted": False,
                    "delivered": False,
                    "delivery_confirmed": False,
                    "provider": "RESEND",
                    "error_code": "NETWORK_ERROR",
                    "error": f"{type(e).__name__}: {str(e)}",
                    "http_status": None,
                    "recipient": to_email,
                    "correlation_id": corr_id,
                    "timestamp": attempt_ts,
                }

            if attempt < max_retries and retry_backoff_seconds > 0:
                time.sleep(retry_backoff_seconds * (attempt + 1))

        return last_result or {
            "status": "EMAIL_DELIVERY_FAILED",
            "delivery_stage": "TRANSIENT_FAILURE",
            "accepted": False,
            "delivered": False,
            "delivery_confirmed": False,
            "provider": "RESEND",
            "error_code": "NETWORK_ERROR",
            "error": "Resend delivery failed after retries",
            "http_status": None,
            "recipient": to_email,
            "correlation_id": corr_id,
            "timestamp": ts,
        }

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends an email via the configured provider (MOCK, RESEND, or SMTP).
        If no provider is configured, returns truthful EMAIL_PROVIDER_NOT_CONFIGURED state.
        """
        corr_id = correlation_id or uuid.uuid4().hex[:12]
        ts = _utc_iso()

        if not to_email:
            return {
                "status": "ERROR",
                "delivery_stage": "REJECTED_BY_PROVIDER",
                "accepted": False,
                "delivered": False,
                "delivery_confirmed": False,
                "error_code": "MISSING_RECIPIENT",
                "error": "Recipient email address is required",
                "correlation_id": corr_id,
                "timestamp": ts,
            }

        # 1. Unconfigured Check
        if not self.is_configured():
            logger.info(
                f"[EmailService] corr_id={corr_id} ts={ts} stage=PROVIDER_NOT_CONFIGURED "
                f"provider={settings.EMAIL_PROVIDER} recipient={to_email}"
            )
            return {
                "status": "EMAIL_PROVIDER_NOT_CONFIGURED",
                "delivery_stage": "PROVIDER_NOT_CONFIGURED",
                "accepted": False,
                "delivered": False,
                "delivery_confirmed": False,
                "provider": "NONE",
                "recipient": to_email,
                "error_code": "PROVIDER_DISABLED" if settings.EMAIL_PROVIDER in ("NONE", "DISABLED") else "MISSING_CREDENTIALS",
                "message": "Email delivery skipped because no Resend or SMTP provider is configured.",
                "correlation_id": corr_id,
                "timestamp": ts,
            }

        # 2. Mock Provider for Unit Tests / Local Testing
        if settings.EMAIL_PROVIDER == "MOCK":
            record = {
                "to_email": to_email,
                "subject": subject,
                "body_text": body_text,
                "has_html": bool(body_html),
                "attachment_count": len(attachments or []),
                "correlation_id": corr_id,
            }
            self.sent_emails_mock.append(record)
            logger.info(f"[MockEmailProvider] corr_id={corr_id} Mock delivered email to {to_email}: '{subject}'")
            return {
                "status": "EMAIL_SENT",
                "delivery_stage": "MOCK_SENT",
                "accepted": True,
                "delivered": True,
                "delivery_confirmed": True,
                "provider": "MOCK",
                "recipient": to_email,
                "correlation_id": corr_id,
                "timestamp": ts,
            }

        # 3. Brevo Provider
        if settings.EMAIL_PROVIDER == "BREVO" or (not settings.EMAIL_PROVIDER and self.is_brevo_configured()):
            return self._send_brevo(to_email, subject, body_text, body_html, correlation_id=corr_id)

        # 4. Resend Provider
        if settings.EMAIL_PROVIDER == "RESEND" or (not settings.EMAIL_PROVIDER and self.is_resend_configured()):
            return self._send_resend(to_email, subject, body_text, body_html, correlation_id=corr_id)

        # 4. Live SMTP Provider
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_FROM_EMAIL
            msg["To"] = to_email

            part1 = MIMEText(body_text, "plain")
            msg.attach(part1)

            if body_html:
                part2 = MIMEText(body_html, "html")
                msg.attach(part2)

            if attachments:
                for att in attachments:
                    filename = att.get("filename", "attachment.bin")
                    content = att.get("content", b"")
                    part = MIMEApplication(content)
                    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
                    msg.attach(part)

            if settings.SMTP_USE_TLS:
                context = ssl.create_default_context()
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                    server.starttls(context=context)
                    if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                    server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())
            else:
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                    if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                    server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())

            logger.info(f"[EmailService] corr_id={corr_id} ts={ts} provider=SMTP stage=ACCEPTED_BY_PROVIDER recipient={to_email}")
            return {
                "status": "EMAIL_SENT",
                "delivery_stage": "ACCEPTED_BY_PROVIDER",
                "accepted": True,
                "delivered": True,
                "delivery_confirmed": False,
                "provider": "SMTP",
                "recipient": to_email,
                "correlation_id": corr_id,
                "timestamp": ts,
            }

        except Exception as e:
            logger.error(f"[EmailService] corr_id={corr_id} ts={ts} provider=SMTP stage=TRANSIENT_FAILURE error_type={type(e).__name__} recipient={to_email}")
            return {
                "status": "EMAIL_DELIVERY_FAILED",
                "delivery_stage": "TRANSIENT_FAILURE",
                "accepted": False,
                "delivered": False,
                "delivery_confirmed": False,
                "provider": "SMTP",
                "error_code": "SMTP_ERROR",
                "error": f"{type(e).__name__}: {str(e)}",
                "recipient": to_email,
                "correlation_id": corr_id,
                "timestamp": ts,
            }

    def send_otp_email(
        self,
        to_email: str,
        otp_code: str,
        purpose: str,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends a branded, security-focused OTP email with 10-minute validity notice.
        The OTP code is passed in memory only to the email generator and NEVER logged.
        """
        purpose_titles = {
            "REGISTRATION": ("Verify Your Email Address", "complete your AgentGuard registration"),
            "PASSWORDLESS_LOGIN": ("Your One-Time Sign-In Passcode", "sign in to your AgentGuard account"),
            "PASSWORD_RESET": ("Your Password Reset Passcode", "reset your AgentGuard password"),
        }
        title, action_text = purpose_titles.get(purpose, ("Verification Code", "authenticate with AgentGuard"))
        subject = f"AgentGuard - {title}"

        body_text = f"""Hello,

Your 6-digit AgentGuard one-time passcode is:

    {otp_code}

Use this passcode to {action_text}.
This code is valid for exactly 10 minutes and can only be used once.

Security notice: If you did not initiate this request, please disregard this email. Never share your passcode.
"""
        digit_tiles = "".join(
            f'<td style="padding: 0 4px;">'
            f'<div style="width: 42px; height: 52px; line-height: 52px; text-align: center; '
            f'background-color: #FFFFFF; border: 1.5px solid #B7E4C7; border-radius: 10px; '
            f'font-family: \'SFMono-Regular\', Consolas, \'Liberation Mono\', Menlo, monospace; '
            f'font-size: 26px; font-weight: 800; color: #1F1F1F; '
            f'box-shadow: 0 2px 6px rgba(46, 157, 80, 0.08);">{ch}</div>'
            f'</td>'
            for ch in str(otp_code).strip()
        )
        body_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #EEF0EC; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1F1F1F; -webkit-font-smoothing: antialiased;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #EEF0EC; padding: 36px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width: 560px; background-color: #FFFFFF; border: 1px solid #E2E4DF; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(15, 23, 20, 0.08);">
          <!-- Dark Obsidian-Emerald Brand Header -->
          <tr>
            <td style="padding: 26px 32px; background: linear-gradient(135deg, #0E1713 0%, #162820 100%); border-bottom: 3px solid #2E9D50;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td align="left" style="vertical-align: middle;">
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                      <tr>
                        <td style="vertical-align: middle; padding-right: 14px;">
                          <div style="width: 44px; height: 44px; border-radius: 11px; background-color: #173B25; border: 1px solid #2E9D50; text-align: center; line-height: 44px;">
                            <img src="https://agentguard-beta-ten.vercel.app/logo.png" alt="AGENTGUARD Logo" width="30" height="30" style="display: inline-block; vertical-align: middle; width: 30px; height: 30px; object-fit: contain; border: 0;" />
                          </div>
                        </td>
                        <td style="vertical-align: middle;">
                          <div style="font-size: 19px; font-weight: 800; letter-spacing: 0.01em; color: #FFFFFF; line-height: 1.2;">
                            AGENT<span style="color: #4ADE80;">GUARD</span>
                          </div>
                          <div style="font-size: 10px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #94B8A3; margin-top: 4px;">
                            Runtime Control Plane
                          </div>
                        </td>
                      </tr>
                    </table>
                  </td>
                  <td align="right" style="vertical-align: middle;">
                    <span style="display: inline-block; padding: 5px 11px; background-color: rgba(46, 157, 80, 0.18); border: 1px solid rgba(74, 222, 128, 0.4); border-radius: 999px; font-size: 10px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #4ADE80;">
                      Zero-Trust Auth
                    </span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Main Body -->
          <tr>
            <td style="padding: 34px 32px 28px 32px;">
              <div style="font-size: 11px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #2E9D50; margin-bottom: 8px;">
                Identity Verification
              </div>
              <h1 style="margin: 0 0 12px 0; font-size: 24px; font-weight: 800; letter-spacing: -0.02em; color: #111827; line-height: 1.25;">
                {title}
              </h1>
              <p style="margin: 0 0 26px 0; font-size: 14px; line-height: 1.65; color: #4B5563;">
                Enter the 6-digit verification passcode below to {action_text}. For your protection, this code is cryptographically bound to your request.
              </p>

              <!-- Segmented OTP Container -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 0 0 24px 0;">
                <tr>
                  <td align="center" style="background-color: #F4FBF6; border: 1px solid #C6ECD3; border-radius: 14px; padding: 24px 12px;">
                    <div style="font-size: 10px; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: #237A3C; margin-bottom: 14px;">
                      One-Time Passcode
                    </div>
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center">
                      <tr>
                        {digit_tiles}
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <!-- 2-Column Metadata Cards -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 0 0 24px 0;">
                <tr>
                  <td width="49%" style="background-color: #FCFCFA; border: 1px solid #E8E8E4; border-radius: 10px; padding: 12px 14px; vertical-align: top;">
                    <div style="font-size: 10px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #6B7280; margin-bottom: 3px;">
                      Expires In
                    </div>
                    <div style="font-size: 13px; font-weight: 700; color: #1F1F1F;">
                      10 Minutes
                    </div>
                  </td>
                  <td width="2%">&nbsp;</td>
                  <td width="49%" style="background-color: #FCFCFA; border: 1px solid #E8E8E4; border-radius: 10px; padding: 12px 14px; vertical-align: top;">
                    <div style="font-size: 10px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #6B7280; margin-bottom: 3px;">
                      Policy
                    </div>
                    <div style="font-size: 13px; font-weight: 700; color: #1F1F1F;">
                      Single-Use Only
                    </div>
                  </td>
                </tr>
              </table>

              <!-- Security Callout -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td style="background-color: #F9FAFB; border-left: 3px solid #2E9D50; border-radius: 0 8px 8px 0; padding: 12px 16px; font-size: 12px; line-height: 1.6; color: #6B7280;">
                    <strong style="color: #1F1F1F;">Security Notice:</strong> If you did not initiate this request, you can safely ignore this email. Never share your verification code &mdash; AGENTGUARD will never ask for it.
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 18px 32px; background-color: #FCFCFA; border-top: 1px solid #E8E8E4; text-align: center;">
              <p style="margin: 0 0 4px 0; font-size: 11px; font-weight: 700; color: #4B5563;">
                AGENTGUARD &middot; Enterprise AI Agent Governance
              </p>
              <p style="margin: 0; font-size: 10px; color: #9CA3AF;">
                Automated security message &middot; Please do not reply directly to this email.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
        return self.send_email(
            to_email=to_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            correlation_id=correlation_id
        )


email_service = EmailService()
