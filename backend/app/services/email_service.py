import logging
import smtplib
import ssl
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

from ..config import get_settings

logger = logging.getLogger("officepilot.email")

settings = get_settings()

USE_SMTP = bool(settings.smtp_host)


def _safe_redact(value: str, visible_chars: int = 4) -> str:
    if len(value) <= visible_chars:
        return "***"
    return value[:visible_chars] + "****"


def _send_smtp(to_email: str, subject: str, html_body: str, text_body: str | None = None) -> bool:
    if not USE_SMTP:
        logger.warning("email_smtp_not_configured: host=%s", settings.smtp_host)
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        msg["To"] = to_email

        if text_body:
            msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        if settings.smtp_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout, context=context) as server:
                if settings.smtp_username and settings.smtp_password:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(settings.smtp_from_email, to_email, msg.as_string())
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout) as server:
                server.ehlo()
                if settings.smtp_tls:
                    server.starttls()
                    server.ehlo()
                if settings.smtp_username and settings.smtp_password:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(settings.smtp_from_email, to_email, msg.as_string())

        logger.info("email_sent to=%s subject=%s", _safe_redact(to_email), subject)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("email_auth_failed: host=%s", settings.smtp_host)
        return False
    except smtplib.SMTPException as e:
        logger.error("email_smtp_error: %s", str(e))
        return False
    except (socket.gaierror, socket.timeout, ConnectionRefusedError) as e:
        logger.error("email_connection_failed: %s", str(e))
        return False
    except Exception as e:
        logger.error("email_send_failed: %s", str(e))
        return False


def _print_dev_link(to_email: str, link: str, label: str) -> None:
    print("\n" + "=" * 60)
    print(f"  [DEV] {label} for: {to_email}")
    print(f"  [DEV] {link}")
    print("=" * 60 + "\n")
    logger.info("dev_link: to=%s label=%s", to_email, label)


def _rebrand_html(body_html: str) -> str:
    """Rebrand CFOBench email HTML to OfficePilot."""
    return body_html.replace("CFOBench", "OfficePilot").replace("CFObench", "OfficePilot").replace("cfobench.com", "officepilot.ai").replace("support@cfobench.com", "support@officepilot.ai").replace("#3B82F6", "#4ade80").replace("#8B5CF6", "#22d3ee")


def send_verification_email(to_email: str, token: str) -> bool:
    verification_link = f"{settings.frontend_url}/verify-email?token={token}"
    now = datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC")

    text_body = f"""Verify your OfficePilot AI account

Thanks for signing up! Please verify your email address to activate your OfficePilot account.

Click this link to verify: {verification_link}

This link expires in 24 hours. If you didn't create an account, you can safely ignore this email.

---
{settings.smtp_from_name}
Support: support@officepilot.ai"""

    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; background: #1e1e2e; color: #cdd6f4; padding: 40px 20px;">
        <div style="text-align: center; margin-bottom: 32px;">
            <span style="font-size: 28px; font-weight: 700; color: #a6e3a1;">OfficePilot</span>
            <span style="font-size: 28px; font-weight: 300; color: #89b4fa;"> AI</span>
        </div>
        <div style="background: #313244; border-radius: 16px; padding: 32px; border: 1px solid rgba(255,255,255,0.1);">
            <h1 style="font-size: 24px; margin: 0 0 16px 0; color: #cdd6f4;">Verify your email</h1>
            <p style="color: #a6adc8; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
                Thanks for signing up! Please verify your email address to activate your OfficePilot AI account.
            </p>
            <p style="color: #a6adc8; font-size: 14px; line-height: 1.6; margin: 0 0 24px 0;">
                This link expires in 24 hours.
            </p>
            <div style="text-align: center; margin: 32px 0;">
                <a href="{verification_link}"
                   style="display: inline-block; background: linear-gradient(135deg, #4ade80, #22d3ee); color: #1e1e2e; padding: 14px 32px; border-radius: 12px; text-decoration: none; font-weight: 600; font-size: 16px;">
                    Verify Email Address
                </a>
            </div>
            <p style="color: #6B7280; font-size: 14px; line-height: 1.6; margin: 0;">
                If the button doesn't work, copy and paste this link into your browser:<br>
                <a href="{verification_link}" style="color: #4ade80; word-break: break-all;">{verification_link}</a>
            </p>
            <p style="color: #6B7280; font-size: 12px; margin: 24px 0 0 0;">
                If you didn't create an account, you can safely ignore this email.
            </p>
            <p style="color: #6B7280; font-size: 12px; margin: 8px 0 0 0;">
                Need help? Contact <a href="mailto:support@officepilot.ai" style="color: #4ade80;">support@officepilot.ai</a>
            </p>
        </div>
        <p style="text-align: center; color: #4B5563; font-size: 12px; margin-top: 24px;">
            &copy; {datetime.now(timezone.utc).year} {settings.smtp_from_name}. All rights reserved.
        </p>
    </div>
    """

    if USE_SMTP:
        logger.info("sending_verification_email: to=%s", _safe_redact(to_email))
        return _send_smtp(to_email, "Verify your OfficePilot AI account", html_body, text_body)
    else:
        _print_dev_link(to_email, verification_link, "Verification email")
        return True


def send_password_reset_email(to_email: str, token: str) -> bool:
    reset_link = f"{settings.frontend_url}/reset-password?token={token}"

    text_body = f"""Reset your OfficePilot AI password

We received a request to reset your password. Click the link below to set a new one.

{reset_link}

This link expires in 1 hour. If you didn't request this, ignore this email.

---
{settings.smtp_from_name}
Support: support@officepilot.ai"""

    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; background: #1e1e2e; color: #cdd6f4; padding: 40px 20px;">
        <div style="text-align: center; margin-bottom: 32px;">
            <span style="font-size: 28px; font-weight: 700; color: #a6e3a1;">OfficePilot</span>
            <span style="font-size: 28px; font-weight: 300; color: #89b4fa;"> AI</span>
        </div>
        <div style="background: #313244; border-radius: 16px; padding: 32px; border: 1px solid rgba(255,255,255,0.1);">
            <h1 style="font-size: 24px; margin: 0 0 16px 0; color: #cdd6f4;">Reset your password</h1>
            <p style="color: #a6adc8; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
                We received a request to reset your password. Click the button below to set a new one.
            </p>
            <p style="color: #a6adc8; font-size: 14px; line-height: 1.6; margin: 0 0 24px 0;">
                This link expires in 1 hour.
            </p>
            <div style="text-align: center; margin: 32px 0;">
                <a href="{reset_link}"
                   style="display: inline-block; background: linear-gradient(135deg, #4ade80, #22d3ee); color: #1e1e2e; padding: 14px 32px; border-radius: 12px; text-decoration: none; font-weight: 600; font-size: 16px;">
                    Reset Password
                </a>
            </div>
            <p style="color: #6B7280; font-size: 14px; line-height: 1.6; margin: 0;">
                If the button doesn't work, copy and paste this link:<br>
                <a href="{reset_link}" style="color: #4ade80; word-break: break-all;">{reset_link}</a>
            </p>
            <p style="color: #6B7280; font-size: 12px; margin: 24px 0 0 0;">
                If you didn't request this, ignore this email.
            </p>
            <p style="color: #6B7280; font-size: 12px; margin: 8px 0 0 0;">
                Need help? Contact <a href="mailto:support@officepilot.ai" style="color: #4ade80;">support@officepilot.ai</a>
            </p>
        </div>
        <p style="text-align: center; color: #4B5563; font-size: 12px; margin-top: 24px;">
            &copy; {datetime.now(timezone.utc).year} {settings.smtp_from_name}. All rights reserved.
        </p>
    </div>
    """

    if USE_SMTP:
        logger.info("sending_password_reset_email: to=%s", _safe_redact(to_email))
        return _send_smtp(to_email, f"Reset your {settings.smtp_from_name} password", html_body, text_body)
    else:
        _print_dev_link(to_email, reset_link, "Password reset email")
        return True
