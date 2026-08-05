"""VERTICAL-MONETIZATION: the ONE canonical customer platform-fee
calculation service. The frontend, DeepSeek and the customer app must never
compute this fee themselves — they only render this service's output.

Money handling: all amounts are integer MINOR currency units (paise for
INR) internally. Decimal is used only at the input/output boundary to avoid
float rounding errors; every intermediate calculation is integer arithmetic.

Rounding rule (deterministic, documented): percentage-of-amount results are
rounded HALF_UP to the nearest whole minor unit (paise) — i.e. a computed
fee of 12.5 paise rounds to 13 paise. This matches standard payment-gateway
minor-unit rounding (Razorpay itself only accepts integer paise) and is
applied exactly once, on the final fee amount, never on intermediate
percentages.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.vertical_monetization.models import VerticalMonetizationPolicy


def to_minor(amount: Decimal | str | float | int, currency: str = "INR") -> int:
    """Rupees (or other major unit) -> integer minor units, HALF_UP."""
    d = amount if isinstance(amount, Decimal) else Decimal(str(amount))
    return int((d * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def to_major(minor: int) -> str:
    return str((Decimal(minor) / 100).quantize(Decimal("0.01")))


async def get_current_policy(db: AsyncSession, vertical_id: uuid.UUID) -> VerticalMonetizationPolicy | None:
    return (await db.execute(
        select(VerticalMonetizationPolicy).where(
            VerticalMonetizationPolicy.vertical_id == vertical_id,
            VerticalMonetizationPolicy.is_current == True,  # noqa: E712
        )
    )).scalar_one_or_none()


def _pct_of(amount_minor: int, pct: Decimal) -> int:
    raw = (Decimal(amount_minor) * pct / Decimal("100"))
    return int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calculate_customer_platform_fee(
    *,
    policy: VerticalMonetizationPolicy | None,
    service_subtotal_minor: int,
    tax_on_service_minor: int = 0,
    discount_minor: int = 0,
    credit_minor: int = 0,
    calculation_basis: str,
    currency: str = "INR",
) -> dict[str, Any]:
    """Pure, deterministic. No DB access, no side effects — safe to call for
    a preview or a real charge with identical results given identical
    inputs. `service_subtotal_minor` must already exclude taxes, tips,
    refundable security deposits, provider parts reimbursement and
    non-chargeable discounts per the fee-basis default (callers are
    responsible for passing the correct chargeable base)."""
    now = datetime.now(timezone.utc).isoformat()

    if policy is None or policy.customer_fee_model == "NONE":
        return {
            "service_subtotal": to_major(service_subtotal_minor),
            "chargeable_subtotal": to_major(service_subtotal_minor),
            "customer_platform_fee": "0.00",
            "tax_on_platform_fee": "0.00",
            "discount_on_platform_fee": to_major(discount_minor),
            "credits_applied": to_major(credit_minor),
            "total_payable": to_major(max(0, service_subtotal_minor - discount_minor - credit_minor)),
            "currency": currency,
            "policy_id": str(policy.id) if policy else None,
            "policy_version": policy.version_number if policy else None,
            "calculation_timestamp": now,
            "calculation_breakdown": {"model": "NONE", "reason": "No customer monetization policy configured for this vertical."},
            "collection_stage": policy.collection_stage if policy else None,
            "refundability_status": "not_applicable",
            "fee_amount_minor": 0,
            "total_payable_minor": max(0, service_subtotal_minor - discount_minor - credit_minor),
        }

    chargeable = max(0, service_subtotal_minor)
    model = policy.customer_fee_model

    if model == "FIXED":
        fee_minor = policy.customer_fee_fixed_amount_minor or 0
        breakdown = {"model": "FIXED", "fixed_amount_minor": fee_minor}
    elif model == "PERCENTAGE":
        pct = policy.customer_fee_percentage or Decimal("0")
        fee_minor = _pct_of(chargeable, pct)
        breakdown = {"model": "PERCENTAGE", "percentage": str(pct), "base_minor": chargeable, "rounding": "HALF_UP to nearest paise"}
    elif model == "PERCENTAGE_WITH_MIN_MAX":
        pct = policy.customer_fee_percentage or Decimal("0")
        raw_fee = _pct_of(chargeable, pct)
        fee_minor = raw_fee
        clamped = None
        if policy.customer_fee_min_minor is not None and fee_minor < policy.customer_fee_min_minor:
            fee_minor = policy.customer_fee_min_minor
            clamped = "min"
        if policy.customer_fee_max_minor is not None and fee_minor > policy.customer_fee_max_minor:
            fee_minor = policy.customer_fee_max_minor
            clamped = "max"
        breakdown = {"model": "PERCENTAGE_WITH_MIN_MAX", "percentage": str(pct), "raw_fee_minor": raw_fee,
                    "min_minor": policy.customer_fee_min_minor, "max_minor": policy.customer_fee_max_minor,
                    "clamped": clamped}
    else:
        fee_minor = 0
        breakdown = {"model": model, "note": "unrecognized model, fee=0 (fail safe, not fail open)"}

    fee_after_discount = max(0, fee_minor - discount_minor)
    tax_on_fee_minor = 0  # No tax-on-platform-fee rule configured in this deployment yet; explicit 0, not omitted.
    total_payable_minor = max(0, service_subtotal_minor + fee_after_discount + tax_on_fee_minor - credit_minor)

    return {
        "service_subtotal": to_major(service_subtotal_minor),
        "chargeable_subtotal": to_major(chargeable),
        "customer_platform_fee": to_major(fee_after_discount),
        "tax_on_platform_fee": to_major(tax_on_fee_minor),
        "discount_on_platform_fee": to_major(discount_minor),
        "credits_applied": to_major(credit_minor),
        "total_payable": to_major(total_payable_minor),
        "currency": currency,
        "policy_id": str(policy.id) if getattr(policy, "id", None) else None,
        "policy_version": policy.version_number,
        "calculation_timestamp": now,
        "calculation_breakdown": breakdown,
        "collection_stage": policy.collection_stage,
        "refundability_status": policy.customer_fee_refund_policy,
        "fee_amount_minor": fee_after_discount,
        "total_payable_minor": total_payable_minor,
    }
