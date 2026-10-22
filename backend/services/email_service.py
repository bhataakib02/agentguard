"""
Phase 6D & Final Auth: Email Provider Abstraction for AgentGuard
Handles transactional email delivery (invitations, report attachments, OTP challenges, approval escalations)
supporting Resend REST API, SMTP, and Mock providers with strict credential protection and truthful status.
"""

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


class EmailService:
    def __init__(self):
        self.sent_emails_mock: List[Dict[str, Any]] = []

    def is_resend_configured(self) -> bool:
        """Returns True if RESEND_API_KEY is provisioned."""
        return bool(getattr(settings, "RESEND_API_KEY", None))

    def is_smtp_configured(self) -> bool:
        """Returns True if SMTP_HOST and SMTP_PORT are provisioned."""
        return bool(settings.SMTP_HOST and settings.SMTP_PORT)

    def is_configured(self) -> bool:
        """Returns True only if an email provider is explicitly configured."""
        if settings.EMAIL_PROVIDER == "MOCK":
            return True
        if settings.EMAIL_PROVIDER == "RESEND":
            return self.is_resend_configured()
        if settings.EMAIL_PROVIDER == "SMTP":
            return self.is_smtp_configured()
        # Fallback detection if EMAIL_PROVIDER is unset/NONE
        return self.is_resend_configured() or self.is_smtp_configured()

    def get_status(self) -> Dict[str, Any]:
        """
        Truthfully returns email provider configuration state without exposing passwords or API keys.
        """
        configured = self.is_configured()
        provider_name = settings.EMAIL_PROVIDER

        if provider_name == "NONE" or not provider_name:
            if self.is_resend_configured():
                provider_name = "RESEND"
            elif self.is_smtp_configured():
                provider_name = "SMTP"
            else:
                provider_name = "NONE"

        resend_active = self.is_resend_configured()
        resend_from = getattr(settings, "RESEND_FROM_EMAIL", "onboarding@resend.dev") if resend_active else None

        return {
            "configured": configured,
            "provider": provider_name if configured else "NONE",
            "status": "HEALTHY" if configured else "NOT_CONFIGURED",
            "resend_configured": resend_active,
            "resend_from_email": resend_from,
            "smtp_configured": self.is_smtp_configured(),
            "smtp_host": settings.SMTP_HOST if settings.SMTP_HOST else None,
            "smtp_port": settings.SMTP_PORT if settings.SMTP_HOST else None,
            "from_email": resend_from if (provider_name == "RESEND" or resend_active) else settings.SMTP_FROM_EMAIL,
            "tls_enabled": settings.SMTP_USE_TLS
        }

    def _send_resend(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends an email using Resend REST API (https://api.resend.com/emails) via standard urllib.
        Never logs or exposes the RESEND_API_KEY.
        """
        resend_key = getattr(settings, "RESEND_API_KEY", "").strip()
        if not resend_key:
            return {
                "status": "EMAIL_PROVIDER_NOT_CONFIGURED",
                "delivered": False,
                "provider": "RESEND",
                "recipient": to_email,
                "error": "RESEND_API_KEY is not configured"
            }

        url = "https://api.resend.com/emails"
        from_addr = getattr(settings, "RESEND_FROM_EMAIL", "").strip() or "AgentGuard <onboarding@resend.dev>"
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
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_bytes = resp.read()
                try:
                    resp_data = json.loads(resp_bytes.decode("utf-8"))
                except Exception:
                    resp_data = {}
                logger.info(f"[EmailService] Successfully sent Resend email to {to_email}")
                return {
                    "status": "EMAIL_SENT",
                    "delivered": True,
                    "provider": "RESEND",
                    "recipient": to_email,
                    "id": resp_data.get("id")
                }
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.error(f"[EmailService] Resend API error for {to_email}: HTTP {e.code}")
            return {
                "status": "EMAIL_DELIVERY_FAILED",
                "delivered": False,
                "provider": "RESEND",
                "error": f"Resend HTTP {e.code}: {err_body}",
                "recipient": to_email
            }
        except Exception as e:
            logger.error(f"[EmailService] Resend network error for {to_email}: {type(e).__name__}")
            return {
                "status": "EMAIL_DELIVERY_FAILED",
                "delivered": False,
                "provider": "RESEND",
                "error": f"{type(e).__name__}: {str(e)}",
                "recipient": to_email
            }

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Sends an email via the configured provider (MOCK, RESEND, or SMTP).
        If no provider is configured, returns truthful EMAIL_PROVIDER_NOT_CONFIGURED state.
        """
        if not to_email:
            return {
                "status": "ERROR",
                "delivered": False,
                "error": "Recipient email address is required"
            }

        # 1. Unconfigured Check
        if not self.is_configured():
            logger.info(
                f"[EmailService] Email not sent to {to_email}: provider is NOT_CONFIGURED."
            )
            return {
                "status": "EMAIL_PROVIDER_NOT_CONFIGURED",
                "delivered": False,
                "provider": "NONE",
                "recipient": to_email,
                "message": "Email delivery skipped because no Resend or SMTP provider is configured."
            }

        # 2. Mock Provider for Unit Tests / Local Testing
        if settings.EMAIL_PROVIDER == "MOCK":
            record = {
                "to_email": to_email,
                "subject": subject,
                "body_text": body_text,
                "has_html": bool(body_html),
                "attachment_count": len(attachments or [])
            }
            self.sent_emails_mock.append(record)
            logger.info(f"[MockEmailProvider] Mock delivered email to {to_email}: '{subject}'")
            return {
                "status": "EMAIL_SENT",
                "delivered": True,
                "provider": "MOCK",
                "recipient": to_email
            }

        # 3. Resend Provider
        if settings.EMAIL_PROVIDER == "RESEND" or (self.is_resend_configured() and settings.EMAIL_PROVIDER != "SMTP"):
            return self._send_resend(to_email, subject, body_text, body_html)

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

            logger.info(f"[EmailService] Successfully sent SMTP email to {to_email}")
            return {
                "status": "EMAIL_SENT",
                "delivered": True,
                "provider": "SMTP",
                "recipient": to_email
            }

        except Exception as e:
            logger.error(f"[EmailService] Failed to send SMTP email to {to_email}: {type(e).__name__}")
            return {
                "status": "EMAIL_DELIVERY_FAILED",
                "delivered": False,
                "provider": "SMTP",
                "error": f"{type(e).__name__}: {str(e)}",
                "recipient": to_email
            }

    def send_otp_email(
        self,
        to_email: str,
        otp_code: str,
        purpose: str
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
        body_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f6f8fa; padding: 24px; color: #1f2328;">
  <div style="max-width: 520px; margin: 0 auto; background: #ffffff; border: 1px solid #d0d7de; border-radius: 8px; padding: 32px;">
    <div style="margin-bottom: 24px;">
      <h2 style="color: #2E9D50; margin: 0; font-size: 20px;">🛡️ AGENTGUARD</h2>
      <p style="color: #656d76; font-size: 13px; margin: 4px 0 0 0;">Runtime Control Plane for Autonomous AI</p>
    </div>
    <h3 style="margin-top: 0; font-size: 18px; color: #1f2328;">{title}</h3>
    <p style="font-size: 14px; line-height: 1.5; color: #333333;">
      Please use the following 6-digit passcode to {action_text}:
    </p>
    <div style="background: #f6f8fa; border: 1px solid #d0d7de; border-radius: 6px; padding: 16px; text-align: center; margin: 24px 0;">
      <span style="font-family: monospace; font-size: 32px; letter-spacing: 8px; font-weight: bold; color: #1f2328;">{otp_code}</span>
    </div>
    <p style="font-size: 13px; color: #656d76; margin-bottom: 8px;">
      ⏱️ This code expires in <strong>10 minutes</strong> and can only be used once.
    </p>
    <p style="font-size: 12px; color: #8c959f; margin-top: 24px; border-top: 1px solid #d0d7de; padding-top: 16px;">
      Security Notice: If you did not request this verification code, please ignore this email. Never share your verification passcode with anyone.
    </p>
  </div>
</body>
</html>"""
        return self.send_email(
            to_email=to_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html
        )


email_service = EmailService()
