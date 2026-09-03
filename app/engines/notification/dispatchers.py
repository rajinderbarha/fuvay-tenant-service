"""Notification Engine — per-channel dispatch.
sms/email channels send via Twilio/SMTP when rec.data carries a phone/email
and credentials are configured; otherwise falls back to log-only (dev mode).
"""
import structlog
from app.twilio_client import send_sms as twilio_send_sms
from app.email_client import send_email as smtp_send_email

logger = structlog.get_logger("notification.dispatch")


async def dispatch_in_app(rec) -> None:
    logger.info("notification.dispatch.in_app",
                notification_id=str(rec.id), recipient_id=str(rec.recipient_id),
                title=rec.title, body=rec.body[:80])


async def dispatch_push(rec) -> None:
    logger.info("notification.dispatch.push",
                notification_id=str(rec.id), recipient_id=str(rec.recipient_id),
                title=rec.title)


async def dispatch_sms(rec) -> None:
    phone = (rec.data or {}).get("phone")
    sent = await twilio_send_sms(phone, rec.body[:160]) if phone else False
    logger.info("notification.dispatch.sms",
                notification_id=str(rec.id), recipient_id=str(rec.recipient_id),
                body=rec.body[:160], sent=sent)


async def dispatch_email(rec) -> None:
    email = (rec.data or {}).get("email")
    sent = await smtp_send_email(email, rec.title or "Fuvay Notification", rec.body) if email else False
    logger.info("notification.dispatch.email",
                notification_id=str(rec.id), recipient_id=str(rec.recipient_id),
                title=rec.title, sent=sent)


_DISPATCH_MAP = {
    "in_app": dispatch_in_app,
    "push":   dispatch_push,
    "sms":    dispatch_sms,
    "email":  dispatch_email,
}


async def dispatch(channel: str, rec) -> None:
    fn = _DISPATCH_MAP.get(channel)
    if fn:
        await fn(rec)
    else:
        logger.warning("notification.dispatch.unknown_channel", channel=channel)
