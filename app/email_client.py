"""Email client — SMTP send via stdlib smtplib (Gmail App Password compatible)."""
import asyncio
import smtplib
from email.mime.text import MIMEText
import structlog
from app.config import get_settings

logger = structlog.get_logger("email_client")


def _send_sync(to_email: str, subject: str, body: str) -> bool:
    settings = get_settings()
    if not (settings.EMAIL_USERNAME and settings.EMAIL_PASSWORD):
        logger.info("email.send.skipped_no_credentials", to=to_email)
        return False
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_USERNAME
    msg["To"] = to_email
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
            server.sendmail(settings.EMAIL_USERNAME, [to_email], msg.as_string())
        logger.info("email.send.sent", to=to_email)
        return True
    except Exception as e:
        logger.error("email.send.exception", error=str(e), to=to_email)
        return False


async def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send an email via SMTP. Returns True on success, False otherwise (never raises)."""
    return await asyncio.to_thread(_send_sync, to_email, subject, body)


def is_email_configured() -> bool:
    """Whether outbound email can actually be sent.

    Read BEFORE offering an email-code sign-in: a code the customer will never receive
    is worse than not offering the option, because they wait for it.
    """
    settings = get_settings()
    return bool(settings.EMAIL_USERNAME and settings.EMAIL_PASSWORD)


async def send_login_code_email(to_email: str, code: str, expires_minutes: int) -> bool:
    """The sign-in code. Deliberately plain: no links, nothing to click.

    A login email with a clickable link is the exact shape of a phishing message, and
    teaching customers to click one trains them into the attack.
    """
    subject = "Your Fuvay sign-in code"
    body = (
        f"Your Fuvay sign-in code is {code}\n\n"
        f"It expires in {expires_minutes} minutes and can be used once.\n\n"
        "If you did not try to sign in, you can ignore this email -- nobody can use "
        "this code without it.\n"
    )
    return await send_email(to_email, subject, body)


async def send_password_reset_email(
    to: str, full_name: str | None, reset_token: str, expires_hours: int,
) -> bool:
    """The admin-initiated password reset.

    This function did not exist. `AuthService.admin_send_password_reset` imported it
    inside a `try` whose `except Exception` logged a warning, so every admin-triggered
    reset email since that code was written raised ImportError, was swallowed, and
    recorded `email_sent: False` in the audit trail while the admin was told the reset
    had been sent. The token itself was real -- it simply never reached anyone.

    Plain text and no link, for the same reason as the sign-in code: a message that
    trains customers to click through to a password form is the shape of the attack it
    is trying to prevent.
    """
    greeting = f"Hi {full_name}," if full_name else "Hi,"
    subject = "Reset your Fuvay password"
    body = (
        f"{greeting}\n\n"
        "An administrator started a password reset for your Fuvay account.\n\n"
        f"Your reset code is {reset_token}\n\n"
        f"It expires in {expires_hours} hours.\n\n"
        "If you were not expecting this, contact your administrator -- this code alone "
        "cannot change anything without being entered in the app.\n"
    )
    return await send_email(to, subject, body)
