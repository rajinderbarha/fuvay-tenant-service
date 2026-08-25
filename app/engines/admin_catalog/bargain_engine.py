"""Bargain Engine — Customer Range + Platform Fee Floor.

Corrects the prior bargain model, which evaluated customer counter-offers
against a flat, admin-set `floor_amount` with no relationship to a
customer-facing price range or the platform fee. The correct model has three
price layers:

    1. Admin Platform Range   (admin_min_price / admin_max_price / admin_base_price)
    2. Customer Display Range (customer_min_price / customer_max_price)
    3. Final Bargain Floor    (customer_min_price + platform fee)

bargain_floor = customer_min_price * (1 + platform_fee_percent / 100)
                                    + platform_fee_fixed_amount

(percent and fixed fee are both supported and additive — a rule normally
configures one or the other, but the formula composes cleanly either way).

Base price is a *pricing fallback only* (used when no type/brand/issue/option
pricing exists) — it must never be used as the bargain floor. This module
never reads base_price for floor computation, by construction.

Pure, DB-free functions — directly unit-testable without touching the ORM.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

Decision = Literal["accepted", "rejected", "provider_approval_required"]


class BargainValidationError(Exception):
    """Raised when the admin range / customer range / platform fee configuration
    itself is invalid — distinct from a customer offer being rejected."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _d(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _round2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def validate_price_range_config(
    admin_min_price,
    admin_max_price,
    customer_min_price,
    customer_max_price,
    platform_fee_percent=0,
    platform_fee_fixed_amount=0,
) -> None:
    """Validates the *configuration* (rules 1-5, 6-7 partially) — raises
    BargainValidationError on the first violation found. Does not depend on
    any specific customer_offer."""
    admin_min = _d(admin_min_price) if admin_min_price is not None else None
    admin_max = _d(admin_max_price) if admin_max_price is not None else None
    customer_min = _d(customer_min_price)
    customer_max = _d(customer_max_price)
    fee_pct = _d(platform_fee_percent or 0)
    fee_fixed = _d(platform_fee_fixed_amount or 0)

    if admin_min is not None and admin_max is not None and admin_min > admin_max:
        raise BargainValidationError(
            "ADMIN_RANGE_INVALID", "admin_min_price must be <= admin_max_price.")

    if admin_min is not None and customer_min < admin_min:
        raise BargainValidationError(
            "CUSTOMER_MIN_BELOW_ADMIN_MIN",
            "customer_min_price must be >= admin_min_price.")

    if admin_max is not None and customer_max > admin_max:
        raise BargainValidationError(
            "CUSTOMER_MAX_ABOVE_ADMIN_MAX",
            "customer_max_price must be <= admin_max_price.")

    if customer_min > customer_max:
        raise BargainValidationError(
            "CUSTOMER_RANGE_INVALID", "customer_min_price must be <= customer_max_price.")

    if fee_pct < 0:
        raise BargainValidationError(
            "PLATFORM_FEE_INVALID", "platform_fee_percent must be >= 0.")

    if fee_fixed < 0:
        raise BargainValidationError(
            "PLATFORM_FEE_INVALID", "platform_fee_fixed_amount must be >= 0.")

    floor = compute_bargain_floor(customer_min, fee_pct, fee_fixed)

    if floor < customer_min:
        # Not reachable given the formula (fee >= 0), but kept as an explicit
        # invariant check per the ticket's validation rule 6.
        raise BargainValidationError(
            "BARGAIN_FLOOR_INVALID", "bargain_floor must be >= customer_min_price.")

    if floor > customer_max:
        raise BargainValidationError(
            "CUSTOMER_RANGE_TOO_NARROW",
            "Customer range is too narrow after platform fee. "
            "Increase max price or reduce min price.")


def compute_bargain_floor(customer_min_price, platform_fee_percent=0, platform_fee_fixed_amount=0) -> Decimal:
    """bargain_floor = customer_min_price * (1 + platform_fee_percent / 100) + platform_fee_fixed_amount"""
    customer_min = _d(customer_min_price)
    fee_pct = _d(platform_fee_percent or 0)
    fee_fixed = _d(platform_fee_fixed_amount or 0)
    floor = customer_min * (Decimal("1") + fee_pct / Decimal("100")) + fee_fixed
    return _round2(floor)


def evaluate_customer_bargain(
    *,
    service_name: str | None,
    admin_min_price,
    admin_max_price,
    admin_base_price=None,
    customer_min_price,
    customer_max_price,
    platform_fee_percent=0,
    platform_fee_fixed_amount=0,
    customer_offer=None,
    currency: str = "INR",
    provider_approval_required: bool = False,
) -> dict:
    """Full evaluation: validates the range/fee configuration, computes the
    bargain floor, and (if customer_offer is given) decides accept/reject.

    Raises BargainValidationError if the configuration itself is invalid
    (admin range, customer range, or fee makes the floor exceed customer_max).
    Callers should catch this and surface it as a 422 with the error message.
    """
    validate_price_range_config(
        admin_min_price, admin_max_price, customer_min_price, customer_max_price,
        platform_fee_percent, platform_fee_fixed_amount,
    )

    customer_min = _d(customer_min_price)
    customer_max = _d(customer_max_price)
    fee_pct = _d(platform_fee_percent or 0)
    fee_fixed = _d(platform_fee_fixed_amount or 0)

    bargain_floor = compute_bargain_floor(customer_min, fee_pct, fee_fixed)
    platform_fee_amount = _round2(bargain_floor - customer_min)

    result = {
        "service_name": service_name,
        "currency": currency,
        "admin_min_price": float(_d(admin_min_price)) if admin_min_price is not None else None,
        "admin_max_price": float(_d(admin_max_price)) if admin_max_price is not None else None,
        "admin_base_price": float(_d(admin_base_price)) if admin_base_price is not None else None,
        "customer_min_price": float(customer_min),
        "customer_max_price": float(customer_max),
        "platform_fee_percent": float(fee_pct),
        "platform_fee_amount": float(platform_fee_amount),
        "bargain_floor": float(bargain_floor),
        "allowed_offer_min": float(bargain_floor),
        "allowed_offer_max": float(customer_max),
        "payment_mode": "customer_pays_provider_directly",
    }

    if customer_offer is None:
        result["customer_offer"] = None
        result["decision"] = None
        result["reason"] = None
        return result

    offer = _d(customer_offer)
    result["customer_offer"] = float(offer)

    if offer < bargain_floor:
        result["decision"] = "rejected"
        result["reason"] = "Offer is below the minimum allowed price after platform fee."
    elif offer > customer_max:
        result["decision"] = "rejected"
        result["reason"] = "Offer is above selected customer range."
    elif provider_approval_required:
        result["decision"] = "provider_approval_required"
        result["reason"] = "Offer meets bargain floor — pending provider approval."
    else:
        result["decision"] = "accepted"
        result["reason"] = "Offer is within the allowed bargain range."

    return result
