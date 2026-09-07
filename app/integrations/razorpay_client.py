"""
Razorpay integration — thin REST wrapper.
Razorpay's order/payment API is plain HTTP Basic Auth, so we call it directly
via httpx instead of pulling in the official SDK as a dependency.

Credentials resolve from the admin-configured, encrypted Razorpay channel
(super admin -> Notification & Provider Settings, same pattern as WhatsApp/
Instagram) when it has been saved, tested and enabled; they fall back to the
static RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET / RAZORPAY_WEBHOOK_SECRET env
vars otherwise, so a server with no admin config keeps working exactly as
before. Every function takes an optional `db` -- pass the request's session
so a live admin-console rotation takes effect immediately, with no restart.

Flow (client-side checkout, "tenant pays"):
  1. Backend calls create_order() -> returns Razorpay order_id + the publishable key_id.
  2. Frontend opens Razorpay Checkout with that order_id/key, user pays.
  3. Razorpay returns razorpay_payment_id + razorpay_signature to the frontend.
  4. Frontend posts those to our confirm endpoint, which calls verify_payment_signature()
     before crediting anything.
"""
from __future__ import annotations

import hashlib
import hmac
import uuid
from decimal import Decimal

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.exceptions import ServiceOSException

logger = structlog.get_logger("integrations.razorpay")

RAZORPAY_API_BASE = "https://api.razorpay.com/v1"


class RazorpayError(Exception):
    pass


async def _resolve_credentials(db: AsyncSession | None) -> tuple[str, str, str]:
    """Return (key_id, key_secret, webhook_secret).

    Prefers the admin-configured channel (only when it is enabled and its
    last connection test passed -- see NotificationChannelConfigService.
    get_active), falling back to the env-var settings.
    """
    s = get_settings()
    key_id, key_secret, webhook_secret = s.RAZORPAY_KEY_ID, s.RAZORPAY_KEY_SECRET, s.RAZORPAY_WEBHOOK_SECRET
    if db is not None:
        try:
            from app.engines.platform_notifications.channel_config_service import channel_config_service
            active = await channel_config_service.get_active(db, "razorpay")
        except Exception:
            logger.warning("razorpay.admin_config_lookup_failed", exc_info=True)
            active = None
        if active:
            config, credentials = active
            key_id = config.get("key_id") or key_id
            key_secret = credentials.get("key_secret") or key_secret
            webhook_secret = credentials.get("webhook_secret") or webhook_secret
    return key_id, key_secret, webhook_secret


async def is_configured(db: AsyncSession | None = None) -> bool:
    key_id, key_secret, _ = await _resolve_credentials(db)
    return bool(key_id and key_secret)


async def get_key_id(db: AsyncSession | None = None) -> str:
    """The publishable key_id handed to the frontend for Checkout."""
    key_id, _, _ = await _resolve_credentials(db)
    return key_id


async def require_configured(db: AsyncSession | None = None) -> None:
    if not await is_configured(db):
        raise ServiceOSException(
            "RAZORPAY_NOT_CONFIGURED",
            "Payment checkout is not configured on this server. Configure the Razorpay test Key ID and Key Secret to make test payments.",
            status_code=503,
        )


async def create_order(amount_rupees: Decimal | float, receipt: str,
                        notes: dict | None = None, db: AsyncSession | None = None) -> dict:
    """
    Create a Razorpay order. amount_rupees is in rupees; Razorpay expects paise (int).
    Test payments require real Razorpay test credentials and a gateway order.
    Never return a placeholder that Checkout cannot open.
    """
    amount_paise = int(round(float(amount_rupees) * 100))

    key_id, key_secret, _ = await _resolve_credentials(db)
    if not (key_id and key_secret):
        await require_configured(db)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{RAZORPAY_API_BASE}/orders",
                auth=(key_id, key_secret),
                json={"amount": amount_paise, "currency": "INR", "receipt": receipt,
                      "notes": notes or {}},
            )
        except httpx.HTTPError as e:
            logger.error("razorpay.order_create_network_error", error=str(e))
            raise RazorpayError(f"Could not reach Razorpay: {e}") from e

    if resp.status_code >= 400:
        logger.error("razorpay.order_create_failed", status=resp.status_code, body=resp.text)
        raise RazorpayError(f"Razorpay order creation failed ({resp.status_code}): {resp.text}")

    order = resp.json()
    logger.info("razorpay.order_created", order_id=order.get("id"), amount_paise=amount_paise)
    return order


async def get_order_payments(order_id: str, db: AsyncSession | None = None) -> list[dict]:
    """Fetch payments for an order directly from Razorpay.

    Used to reconcile the uncommon but real case where Checkout captures a
    payment and then fails/closes before its browser handler reaches us.
    This call is authenticated with the server secret; no client-reported
    status is trusted.
    """
    key_id, key_secret, _ = await _resolve_credentials(db)
    if not (key_id and key_secret):
        return []
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                f"{RAZORPAY_API_BASE}/orders/{order_id}/payments",
                auth=(key_id, key_secret),
            )
        except httpx.HTTPError as exc:
            logger.error("razorpay.order_payments_network_error", order_id=order_id, error=str(exc))
            raise RazorpayError(f"Could not reconcile Razorpay order: {exc}") from exc
    if resp.status_code >= 400:
        logger.error("razorpay.order_payments_failed", order_id=order_id,
                     status=resp.status_code, body=resp.text)
        raise RazorpayError(f"Razorpay reconciliation failed ({resp.status_code}).")
    return list(resp.json().get("items") or [])


async def verify_payment_signature(order_id: str, payment_id: str, signature: str,
                                    db: AsyncSession | None = None) -> bool:
    """
    HMAC-SHA256("{order_id}|{payment_id}") keyed with the key secret, per Razorpay docs.
    Missing credentials never authorize credits, including in development.
    """
    _, key_secret, _ = await _resolve_credentials(db)
    if not key_secret:
        return False
    if order_id.startswith("order_local_"):
        return False
    if not order_id or not payment_id or not signature:
        return False
    payload = f"{order_id}|{payment_id}".encode()
    expected = hmac.new(key_secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def verify_webhook_signature(raw_body: bytes, signature: str,
                                    db: AsyncSession | None = None) -> bool:
    """Verify the X-Razorpay-Signature header on server-to-server webhook calls."""
    _, _, webhook_secret = await _resolve_credentials(db)
    if not webhook_secret:
        return False
    if not signature:
        return False
    expected = hmac.new(webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
