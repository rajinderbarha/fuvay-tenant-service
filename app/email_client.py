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
