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
            VerticalMonetizationPolicy.status == "published",
        )
    )).scalar_one_or_none()


async def get_current_policy_by_vertical_key(
    db: AsyncSession, vertical_key: str,
) -> VerticalMonetizationPolicy | None:
    """Canonical cross-system policy lookup by business vertical.

    Each vertical owns one published monetization policy. Runtime callers
    use this helper instead of reading service-category finance fields, so a
    Home Services policy can never leak into Coaching/Food and vice versa.
    """
    from app.engines.vertical_catalog.models import Vertical
    return (await db.execute(
        select(VerticalMonetizationPolicy)
        .join(Vertical, Vertical.id == VerticalMonetizationPolicy.vertical_id)
        .where(
            Vertical.key == vertical_key,
            VerticalMonetizationPolicy.is_current.is_(True),
            VerticalMonetizationPolicy.status == "published",
        )
    )).scalar_one_or_none()


async def get_active_job_type_rule(
    db: AsyncSession,
    policy_id: uuid.UUID,
    job_type_id: uuid.UUID | None,
):
    """Return the active override for this exact policy version and Job Type."""
    if job_type_id is None:
        return None
    from app.engines.vertical_monetization.models import MonetizationJobTypeRule
    return (await db.execute(
        select(MonetizationJobTypeRule).where(
            MonetizationJobTypeRule.policy_id == policy_id,
            MonetizationJobTypeRule.job_type_id == job_type_id,
            MonetizationJobTypeRule.status == "active",
        )
    )).scalar_one_or_none()


def _pct_of(amount_minor: int, pct: Decimal) -> int:
    raw = (Decimal(amount_minor) * pct / Decimal("100"))
    return int(raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calculate_provider_completion_credits(
    *,
    policy: VerticalMonetizationPolicy | None,
    service_amount: Decimal | str | float | int,
    provider_charge_enabled: bool = True,
    credit_units_override: Decimal | str | float | int | None = None,
    charge_model_override: str | None = None,
) -> dict[str, Any]:
    """Canonical provider-side completion charge in usage-credit units.

    Home Services credits are rupee-equivalent units. Percentage charges are
    calculated from the provider's service value only (never the customer
    platform fee), while fixed-credit rules can be overridden per Job Type.
    Optional provider min/max values are stored in minor currency units and
    clamp percentage commission deterministically.
    """
    amount = Decimal(str(service_amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if policy is None or not provider_charge_enabled or policy.provider_model == "NONE":
        return {
            "provider_model": policy.provider_model if policy else "NONE",
            "provider_charge_credit_units": "0.00",
            "provider_charge_note": "No provider-side completion charge.",
            "provider_charge_breakdown": {"reason": "disabled_or_not_configured"},
        }

    model = "COMPLETION_CREDITS" if charge_model_override == "FIXED_CREDITS" else policy.provider_model
    units = Decimal("0")
    breakdown: dict[str, Any] = {
        "model": model, "policy_model": policy.provider_model,
        "job_type_model_override": charge_model_override,
        "service_amount": str(amount),
    }
    if model == "PERCENTAGE_COMMISSION":
        pct = Decimal(str(policy.provider_percentage or 0))
        units = amount * pct / Decimal("100")
        raw_units = units
        minimum = (Decimal(str(policy.provider_min_charge_minor)) / Decimal("100")) if policy.provider_min_charge_minor is not None else None
        maximum = (Decimal(str(policy.provider_max_charge_minor)) / Decimal("100")) if policy.provider_max_charge_minor is not None else None
        clamped = None
        if minimum is not None and units < minimum:
            units, clamped = minimum, "min"
        if maximum is not None and units > maximum:
            units, clamped = maximum, "max"
        breakdown.update({"percentage": str(pct), "raw_credit_units": str(raw_units),
                          "minimum_credit_units": str(minimum) if minimum is not None else None,
                          "maximum_credit_units": str(maximum) if maximum is not None else None,
                          "clamped": clamped})
        note = f"{pct.normalize()}% of provider service value"
    elif model == "COMPLETION_CREDITS":
        configured = credit_units_override if credit_units_override is not None else policy.provider_credit_units
        units = Decimal(str(configured or 0))
        breakdown.update({"credit_units_override": str(credit_units_override) if credit_units_override is not None else None})
        note = "Fixed usage credits per eligible completed job"
    elif model == "FIXED_COMPLETION_CHARGE":
        units = Decimal(str(policy.provider_fixed_amount_minor or 0)) / Decimal("100")
        note = "Fixed completion amount converted to usage credits"
    else:
        note = f"{model} is not a completion-credit runtime model"

    units = max(Decimal("0"), units).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {
        "provider_model": model,
        "provider_charge_credit_units": str(units),
        "provider_charge_note": note,
        "provider_charge_breakdown": breakdown,
    }


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
