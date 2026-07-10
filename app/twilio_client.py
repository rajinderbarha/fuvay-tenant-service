"""
Twilio client — SMS sending + Verify API (OTP).

Two modes:
  • Plain SMS (send_sms)  — uses Messaging API with TWILIO_PHONE_NUMBER
  • Verify OTP (verify_send / verify_check) — uses Verify API with TWILIO_VERIFY_SERVICE_SID

Use Verify in preference to plain SMS for OTP flows: Twilio handles generation,
delivery, retry, expiry, and rate-limiting natively.
"""
import httpx
import structlog
from app.config import get_settings

logger = structlog.get_logger("twilio_client")

TWILIO_API_BASE    = "https://api.twilio.com/2010-04-01"
TWILIO_VERIFY_BASE = "https://verify.twilio.com/v2"


def _is_sms_configured() -> bool:
    s = get_settings()
    return bool(s.TWILIO_ACCOUNT_SID and s.TWILIO_AUTH_TOKEN and s.TWILIO_PHONE_NUMBER)


def is_verify_configured() -> bool:
    s = get_settings()
    return bool(s.TWILIO_ACCOUNT_SID and s.TWILIO_AUTH_TOKEN and s.TWILIO_VERIFY_SERVICE_SID)


async def send_sms(to_phone: str, body: str) -> bool:
    """Send an SMS via Twilio Messaging API. Returns True on success, False otherwise (never raises)."""
    settings = get_settings()
    if not _is_sms_configured():
        logger.info("twilio.sms.skipped_no_credentials", to=to_phone[:4] + "****")
        return False

    url = f"{TWILIO_API_BASE}/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
                data={"From": settings.TWILIO_PHONE_NUMBER, "To": to_phone, "Body": body},
            )
        if resp.status_code >= 400:
            logger.error("twilio.sms.failed", status=resp.status_code, body=resp.text[:300])
            return False
        logger.info("twilio.sms.sent", to=to_phone[:4] + "****")
        return True
    except Exception as e:
        logger.error("twilio.sms.exception", error=str(e))
        return False


async def verify_send(to_phone: str, channel: str = "sms") -> bool:
    """
    Start a Twilio Verify flow — Twilio generates and delivers the OTP.
    Returns True if the verification was created, False on failure (never raises).
    channel: "sms" | "call" | "whatsapp"
    """
    settings = get_settings()
    if not is_verify_configured():
        logger.info("twilio.verify.skipped_no_service_sid", to=to_phone[:4] + "****")
        return False

    url = f"{TWILIO_VERIFY_BASE}/Services/{settings.TWILIO_VERIFY_SERVICE_SID}/Verifications"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
                data={"To": to_phone, "Channel": channel},
            )
        if resp.status_code >= 400:
            logger.error("twilio.verify.send_failed", status=resp.status_code, body=resp.text[:300])
            return False
        data = resp.json()
        logger.info("twilio.verify.sent", to=to_phone[:4] + "****", status=data.get("status"))
        return True
    except Exception as e:
        logger.error("twilio.verify.send_exception", error=str(e))
        return False


async def verify_check(to_phone: str, code: str) -> bool:
    """
    Check a Twilio Verify OTP. Returns True if approved, False otherwise (never raises).
    Twilio marks the verification as consumed on success so replay is impossible.
    """
    settings = get_settings()
    if not is_verify_configured():
        logger.info("twilio.verify.check_skipped_no_service_sid")
        return False

    url = f"{TWILIO_VERIFY_BASE}/Services/{settings.TWILIO_VERIFY_SERVICE_SID}/VerificationChecks"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
                data={"To": to_phone, "Code": code},
            )
        if resp.status_code == 404:
            # Verification not found (expired or already used)
            logger.warning("twilio.verify.check_not_found", to=to_phone[:4] + "****")
            return False
        if resp.status_code >= 400:
            logger.error("twilio.verify.check_failed", status=resp.status_code, body=resp.text[:300])
            return False
        data = resp.json()
        approved = data.get("status") == "approved"
        logger.info("twilio.verify.check_result", to=to_phone[:4] + "****",
                    status=data.get("status"), approved=approved)
        return approved
    except Exception as e:
        logger.error("twilio.verify.check_exception", error=str(e))
        return False
