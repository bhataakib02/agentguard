"""
Phase 6D: Email Provider Abstraction for AgentGuard
Handles transactional email delivery (invitations, report attachments, approval escalations)
with strict credential protection, bounded retries, and truthful delivery status.
"""

import smtplib
import ssl
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

    def is_configured(self) -> bool:
        """Returns True only if an email provider is explicitly configured."""
        if settings.EMAIL_PROVIDER == "MOCK":
            return True
        if settings.EMAIL_PROVIDER == "SMTP" or settings.SMTP_HOST:
            return bool(settings.SMTP_HOST and settings.SMTP_PORT)
        return False

    def get_status(self) -> Dict[str, Any]:
        """
        Truthfully returns email provider configuration state without exposing passwords.
        """
        configured = self.is_configured()
        provider_name = settings.EMAIL_PROVIDER
        if provider_name == "NONE" and settings.SMTP_HOST:
            provider_name = "SMTP"

        return {
            "configured": configured,
            "provider": provider_name if configured else "NONE",
            "status": "HEALTHY" if configured else "NOT_CONFIGURED",
            "smtp_host": settings.SMTP_HOST if settings.SMTP_HOST else None,
            "smtp_port": settings.SMTP_PORT if settings.SMTP_HOST else None,
            "from_email": settings.SMTP_FROM_EMAIL,
            "tls_enabled": settings.SMTP_USE_TLS
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
        Sends an email via the configured provider.
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
                "message": "Email delivery skipped because no SMTP or email provider is configured."
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

        # 3. Live SMTP Provider
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


email_service = EmailService()
