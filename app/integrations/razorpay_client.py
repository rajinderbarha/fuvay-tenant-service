"""
Razorpay integration — thin REST wrapper.
Razorpay's order/payment API is plain HTTP Basic Auth, so we call it directly
via httpx instead of pulling in the official SDK as a dependency.

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

from app.config import get_settings

logger = structlog.get_logger("integrations.razorpay")

RAZORPAY_API_BASE = "https://api.razorpay.com/v1"


class RazorpayError(Exception):
    pass


def is_configured() -> bool:
    s = get_settings()
    return bool(s.RAZORPAY_KEY_ID and s.RAZORPAY_KEY_SECRET)


async def create_order(amount_rupees: Decimal | float, receipt: str,
                        notes: dict | None = None) -> dict:
    """
    Create a Razorpay order. amount_rupees is in rupees; Razorpay expects paise (int).
    If no keys are configured, falls back to a local placeholder order so dev/test
    environments without credentials keep working end-to-end.
    """
    s = get_settings()
    amount_paise = int(round(float(amount_rupees) * 100))

    if not is_configured():
        logger.warning("razorpay.not_configured_using_placeholder", receipt=receipt)
        return {"id": f"order_local_{uuid.uuid4().hex[:16]}", "amount": amount_paise,
                "currency": "INR", "status": "created", "receipt": receipt}

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{RAZORPAY_API_BASE}/orders",
                auth=(s.RAZORPAY_KEY_ID, s.RAZORPAY_KEY_SECRET),
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


async def get_order_payments(order_id: str) -> list[dict]:
    """Fetch payments for an order directly from Razorpay.

    Used to reconcile the uncommon but real case where Checkout captures a
    payment and then fails/closes before its browser handler reaches us.
    This call is authenticated with the server secret; no client-reported
    status is trusted.
    """
    s = get_settings()
    if not is_configured():
        return []
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                f"{RAZORPAY_API_BASE}/orders/{order_id}/payments",
                auth=(s.RAZORPAY_KEY_ID, s.RAZORPAY_KEY_SECRET),
            )
        except httpx.HTTPError as exc:
            logger.error("razorpay.order_payments_network_error", order_id=order_id, error=str(exc))
            raise RazorpayError(f"Could not reconcile Razorpay order: {exc}") from exc
    if resp.status_code >= 400:
        logger.error("razorpay.order_payments_failed", order_id=order_id,
                     status=resp.status_code, body=resp.text)
        raise RazorpayError(f"Razorpay reconciliation failed ({resp.status_code}).")
    return list(resp.json().get("items") or [])


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """
    HMAC-SHA256("{order_id}|{payment_id}") keyed with RAZORPAY_KEY_SECRET, per Razorpay docs.
    Skipped when not fully configured (same condition as create_order) so dev/test
    environments using order_local_* placeholder orders keep working end-to-end.
    """
    s = get_settings()
    if not is_configured():
        logger.warning("razorpay.verify_skipped_not_configured")
        return True
    if not order_id or not payment_id or not signature:
        return False
    payload = f"{order_id}|{payment_id}".encode()
    expected = hmac.new(s.RAZORPAY_KEY_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    """Verify the X-Razorpay-Signature header on server-to-server webhook calls."""
    s = get_settings()
    secret = s.RAZORPAY_WEBHOOK_SECRET
    if not secret:
        return True  # webhook secret not configured — skip (dev only)
    if not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
