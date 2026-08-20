"""HS9 — Completed Job Deduction + Usage Credit Ledger.

Deduction model (2026-08-05, explicit user request): a single Home
Services-wide PERCENTAGE_COMMISSION, set in Home Services Finance >
Monetization ("provider_percentage" on the current published
VerticalMonetizationPolicy), applied to the final service value snapshotted
on the job's issued invoice (`service_invoices.total_amount`). Legacy jobs
without an invoice fall back to the collected amount. The customer platform
fee is never part of this basis. This replaces the old per-service flat
"Provider Completion Charge Config". There is deliberately no fallback:
without a published Home Services Monetization policy the charge is zero.
This guarantees one visible configuration authority for every new charge.

Deduction itself is applied against the tenant's existing
`tenant_billing.credit_balance` and writes a `usage_credit_ledger` row,
idempotent per job.

Usage credits are internal platform credits, not money — never wallet,
payout, or escrow terminology anywhere in this module.
"""
from __future__ import annotations
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

DEDUCTION_EVENT_TYPE = "completed_job_deduction"
_HS_KEY = "home_services"


async def resolve_commission_credits(
    db: AsyncSession,
    *,
    job_price: Decimal | None,
    category_id: uuid.UUID | None,
    master_service_id: uuid.UUID,
    offering_type_id: uuid.UUID | None,
    brand_id: uuid.UUID | None,
    job_type_id: uuid.UUID | None = None,
    chargeable_event: str = "job_completed",
) -> tuple[Decimal, str | None]:
    """Returns (credits, deduction_source_label). Each Home Services
    PERCENTAGE_COMMISSION rate comes only from the Home Services vertical's
    published Monetization policy. Service categories do not carry a second
    Home Services finance configuration. No published policy means zero
    charge; hidden pricing-rule values are never used as a fallback."""
    from app.engines.vertical_catalog.models import Vertical
    from app.engines.vertical_monetization.models import (
        MonetizationJobTypeRule,
        VerticalMonetizationPolicy,
    )

    vertical = (await db.execute(
        select(Vertical).where(Vertical.key == _HS_KEY)
    )).scalar_one_or_none()
    policy = None
    if vertical:
        policy = (await db.execute(
            select(VerticalMonetizationPolicy).where(
                VerticalMonetizationPolicy.vertical_id == vertical.id,
                VerticalMonetizationPolicy.is_current.is_(True),
                VerticalMonetizationPolicy.status == "published",
            )
        )).scalar_one_or_none()

    if policy is not None:
        # Defence in depth: publishing already rejects unsupported provider
        # models, but the runtime writer must also fail closed if an old or
        # manually-corrupted policy reaches this path. These are the only
        # three models that produce a Home Services provider charge.
        runtime_model_supported = (
            policy.provider_model == "COMPLETION_CREDITS"
            or policy.provider_model == "PERCENTAGE_COMMISSION"
            or policy.provider_model == "FIXED_COMPLETION_CHARGE"
        )
        if not runtime_model_supported:
            return Decimal("0"), f"monetization_policy:{policy.id}:unsupported_model"
        override = None
        if job_type_id is not None:
            override = (await db.execute(
                select(MonetizationJobTypeRule).where(
                    MonetizationJobTypeRule.policy_id == policy.id,
                    MonetizationJobTypeRule.job_type_id == job_type_id,
                    MonetizationJobTypeRule.status == "active",
                )
            )).scalar_one_or_none()
        if override is not None and override.provider_chargeable_event != chargeable_event:
            return Decimal("0"), f"monetization_job_type_rule:{override.id}:event_not_reached"
        from app.engines.vertical_monetization.calculation_service import calculate_provider_completion_credits
        calculated = calculate_provider_completion_credits(
            policy=policy,
            service_amount=job_price or Decimal("0"),
            provider_charge_enabled=override.provider_charge_enabled if override is not None else True,
            credit_units_override=(
                override.provider_charge_credit_units
                if override is not None and (
                    policy.provider_model == "COMPLETION_CREDITS"
                    or override.provider_charge_model == "FIXED_CREDITS"
                )
                else None
            ),
            charge_model_override=override.provider_charge_model if override is not None else None,
        )
        source = (
            f"monetization_job_type_rule:{override.id}"
            if override is not None else f"monetization_policy:{policy.id}"
        )
        return Decimal(calculated["provider_charge_credit_units"]), source

    # No hidden fallback: Home Services Monetization is the sole authority.
    # With no published policy, no provider charge is created.
    return Decimal("0"), None


async def deduct_for_completed_job(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    booking_id: uuid.UUID,
    master_service_id: uuid.UUID,
    offering_type_id: uuid.UUID | None,
    brand_id: uuid.UUID | None,
    category_id: uuid.UUID | None = None,
    job_type_id: uuid.UUID | None = None,
    job_price: Decimal | None = None,
    request_id: str | None = None,
    chargeable_event: str = "job_completed",
) -> dict:
    """Idempotent per job_id — a second call for the same job returns the
    existing ledger row instead of deducting again (HS9 hard gate: never
    deduct twice for the same job)."""
    from app.engines.tenant_engine.models import TenantBilling, UsageCreditLedger

    existing = (await db.execute(
        select(UsageCreditLedger).where(
            UsageCreditLedger.job_id == job_id,
            UsageCreditLedger.event_type == DEDUCTION_EVENT_TYPE,
        )
    )).scalars().first()
    if existing:
        return {**existing.to_dict(), "deduction_status": "already_deducted"}

    credits, deduction_source = await resolve_commission_credits(
        db, job_price=job_price, category_id=category_id,
        master_service_id=master_service_id, offering_type_id=offering_type_id, brand_id=brand_id,
        job_type_id=job_type_id,
        chargeable_event=chargeable_event,
    )

    billing = (await db.execute(
        select(TenantBilling).where(TenantBilling.tenant_id == tenant_id)
    )).scalars().first()
    if not billing:
        billing = TenantBilling(tenant_id=tenant_id, credit_balance=Decimal("0"))
        db.add(billing)
        await db.flush()

    balance_before = Decimal(str(billing.credit_balance))
    balance_after = balance_before - credits
    # Recommended policy (documented, not blocking): allow completion even
    # if this drives the balance negative — never block a genuine customer
    # job completion over provider credit shortfall. Low/negative balance
    # is simply recorded; restricting future matching on it is a separate,
    # not-yet-implemented concern (see HS9_REMAINING_BLOCKERS.md).
    billing.credit_balance = balance_after

    ledger = UsageCreditLedger(
        tenant_id=tenant_id, job_id=job_id, booking_id=booking_id,
        event_type=DEDUCTION_EVENT_TYPE, credit_delta=-credits,
        balance_before=balance_before, balance_after=balance_after,
        deduction_source=deduction_source,
        service_id=master_service_id, service_type_id=offering_type_id, brand_id=brand_id,
        reason=f"Completed Job Deduction for job {job_id}",
        request_id=request_id,
    )
    db.add(ledger)
    await db.flush()
    return {**ledger.to_dict(), "deduction_status": "deducted"}
