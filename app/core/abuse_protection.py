"""Public challenge verification and abuse-control helpers."""
from __future__ import annotations

import uuid

import httpx

from app.config import get_settings
from app.exceptions import ServiceOSException

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile(
    token: str | None,
    *,
    remote_ip: str | None,
    expected_action: str,
) -> None:
    """Validate a single-use Turnstile token server-side.

    The check is optional in local/test environments unless explicitly
    enabled, and mandatory/fail-closed in production.
    """
    settings = get_settings()
    if not settings.TURNSTILE_REQUIRED:
        return
    if not token or not settings.TURNSTILE_SECRET_KEY:
        raise ServiceOSException(
            "BOT_CHALLENGE_REQUIRED",
            "Please complete the security check and try again.",
            status_code=400,
        )

    payload = {
        "secret": settings.TURNSTILE_SECRET_KEY,
        "response": token,
        "idempotency_key": str(uuid.uuid4()),
    }
    if remote_ip and remote_ip != "unknown":
        payload["remoteip"] = remote_ip
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(TURNSTILE_VERIFY_URL, data=payload)
            response.raise_for_status()
            result = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ServiceOSException(
            "BOT_CHALLENGE_UNAVAILABLE",
            "The security check is temporarily unavailable.",
            status_code=503,
            resolution="Please wait a moment and try again.",
        ) from exc

    hostname = str(result.get("hostname") or "").lower()
    allowed_hosts = {host.lower() for host in settings.TURNSTILE_ALLOWED_HOSTNAMES}
    action = result.get("action")
    if (
        not result.get("success")
        or action != expected_action
        or (allowed_hosts and hostname not in allowed_hosts)
    ):
        raise ServiceOSException(
            "BOT_CHALLENGE_FAILED",
            "The security check could not be verified. Please try again.",
            status_code=400,
        )
