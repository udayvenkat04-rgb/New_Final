"""
Email Service — Phase 20

Manages SMTP configuration, authentication, HTML/Plain-text MIME message creation,
and secure email delivery with development mode support (EMAIL_ENABLED=false).
"""

from __future__ import annotations

import logging
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Tuple

from backend.config import settings

logger = logging.getLogger(__name__)

# Basic RFC 5322 compliant email regex pattern
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class EmailService:
    """Service handling SMTP email composition, authentication, and delivery."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        smtp_from_email: Optional[str] = None,
        email_enabled: Optional[bool] = None,
    ):
        self.smtp_host = smtp_host if smtp_host is not None else getattr(settings, "SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port if smtp_port is not None else getattr(settings, "SMTP_PORT", 587)
        self.smtp_username = smtp_username if smtp_username is not None else getattr(settings, "SMTP_USERNAME", "")
        self.smtp_password = smtp_password if smtp_password is not None else getattr(settings, "SMTP_PASSWORD", "")
        self.smtp_from_email = smtp_from_email if smtp_from_email is not None else getattr(settings, "SMTP_FROM_EMAIL", "alerts@example.com")
        self.email_enabled = email_enabled if email_enabled is not None else getattr(settings, "EMAIL_ENABLED", False)

    def validate_email_address(self, email: str) -> bool:
        """Validates email format using regex."""
        if not email or not isinstance(email, str):
            return False
        return bool(EMAIL_REGEX.match(email.strip()))

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Sends an email message with HTML + Plain text fallback.

        Returns:
            Tuple[bool, str]: (Success boolean, Status/Error message string)
        """
        if not to_email or not self.validate_email_address(to_email):
            logger.warning("Invalid recipient email address format: '%s'", to_email)
            return False, "INVALID_RECIPIENT_EMAIL_FORMAT"

        # Check SMTP configuration when email is enabled
        if self.email_enabled:
            if not self.smtp_host or not self.smtp_username or not self.smtp_password:
                logger.error("SMTP credentials or host not configured in settings.")
                return False, "SMTP_CONFIGURATION_MISSING"

        # Development Mode Check (EMAIL_ENABLED=false)
        if not self.email_enabled:
            logger.info(
                "[EMAIL DEV SIMULATION] EMAIL_ENABLED is False. Email to '%s' simulated successfully. Subject: '%s'",
                to_email,
                subject
            )
            return True, "EMAIL_DISABLED_DEVELOPMENT_MODE"

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = self.smtp_from_email or self.smtp_username
            msg["To"] = to_email.strip()
            msg["Subject"] = subject

            # Attach plain text
            msg.attach(MIMEText(body_text, "plain", "utf-8"))

            # Attach HTML if provided
            if body_html:
                msg.attach(MIMEText(body_html, "html", "utf-8"))

            # Establish SMTP connection with 2s timeout
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=2) as server:
                server.ehlo()
                if self.smtp_port in (587, 25):
                    server.starttls()
                    server.ehlo()

                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.smtp_from_email or self.smtp_username, [to_email.strip()], msg.as_string())

            logger.info("Successfully delivered email to '%s'. Subject: '%s'", to_email, subject)
            return True, "SENT"

        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP Authentication Failed for host '%s'", self.smtp_host)
            return False, "SMTP_AUTHENTICATION_FAILED"
        except (smtplib.SMTPConnectError, TimeoutError, OSError) as conn_err:
            logger.error("SMTP Connection Error to host '%s': %s", self.smtp_host, conn_err)
            return False, f"SMTP_CONNECTION_ERROR: {conn_err}"
        except smtplib.SMTPException as smtp_err:
            logger.error("SMTP Protocol Error: %s", smtp_err)
            return False, f"SMTP_PROTOCOL_ERROR: {smtp_err}"
        except Exception as exc:
            logger.error("Unexpected failure sending email: %s", exc)
            return False, f"EMAIL_SEND_FAILED: {exc}"

    def send_match_confirmation_email(
        self,
        recipient_email: str,
        complainant_name: str,
        case_number: str,
        missing_person_name: str,
        review_date: str
    ) -> Tuple[bool, str]:
        """
        Composes and sends a professional Match Confirmation email to complainant.
        """
        subject = "Missing Person Case — Match Confirmation Update"

        complainant_salutation = complainant_name.strip() if complainant_name else "Valued Complainant"

        body_text = f"""Dear {complainant_salutation},

We are writing to inform you that a potential identification associated with your missing-person case has been thoroughly reviewed and CONFIRMED by an authorized administrator.

CASE DETAILS:
--------------------------------------------------
Case Number: {case_number}
Missing Person: {missing_person_name}
Match Review Decision: CONFIRMED
Review Date: {review_date}

NEXT STEPS:
Please contact the investigating law enforcement authority or system administrator for further verification and instructions.

Regards,
Missing Person Identification System
--------------------------------------------------
Notice: This is an automated official notification from an auditable system.
"""

        body_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 20px; }}
        .card {{ background: #1e293b; border-radius: 12px; padding: 25px; border-left: 5px solid #10b981; max-width: 600px; margin: 0 auto; }}
        h2 {{ color: #10b981; margin-top: 0; }}
        .badge {{ background: #10b981; color: #ffffff; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 14px; }}
        .info-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        .info-table td {{ padding: 8px; border-bottom: 1px solid #334155; }}
        .footer {{ font-size: 12px; color: #94a3b8; margin-top: 20px; border-top: 1px solid #334155; padding-top: 10px; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>🔍 Missing Person Match Confirmed</h2>
        <p>Dear <b>{complainant_salutation}</b>,</p>
        <p>We are writing to inform you that a potential biometric identification associated with your missing-person case has been reviewed and <span class="badge">CONFIRMED</span> by an authorized Administrator.</p>
        
        <table class="info-table">
            <tr><td><b>Case Number:</b></td><td><code>{case_number}</code></td></tr>
            <tr><td><b>Missing Person Name:</b></td><td><b>{missing_person_name}</b></td></tr>
            <tr><td><b>Review Decision:</b></td><td><span class="badge">CONFIRMED</span></td></tr>
            <tr><td><b>Review Date:</b></td><td>{review_date}</td></tr>
        </table>
        
        <p><b>Next Steps:</b> Please contact the investigating law enforcement agency or system administrator for further assistance and official protocol verification.</p>
        
        <div class="footer">
            <p>Missing Person Identification System — Automated Official Notification<br>
            <i>This message was issued following an auditable human match confirmation.</i></p>
        </div>
    </div>
</body>
</html>
"""

        return self.send_email(
            to_email=recipient_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html
        )


# Legacy Function Export for backward compatibility
def send_matching_alert(
    case_name: str,
    sighting_address: str,
    reporter_name: str,
    confidence: float
) -> bool:
    """Legacy helper function forwarding to EmailService."""
    svc = EmailService()
    subject = f"⚠️ CRITICAL: Missing Person Sighting Alert - {case_name}"
    body = (
        f"A new sighting matching '{case_name}' has been reported.\n\n"
        f"Sighting Details:\n"
        f"- Target Case: {case_name}\n"
        f"- Sighting Location: {sighting_address}\n"
        f"- Sighting Reporter: {reporter_name}\n"
        f"- Face Match Confidence: {confidence * 100:.2f}%\n\n"
        f"Please log in to the Officer Dashboard immediately to review."
    )
    to_addr = svc.smtp_from_email or "admin@example.com"
    success, _ = svc.send_email(to_addr, subject, body)
    return success
