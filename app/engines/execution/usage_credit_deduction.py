"""HS9 — Completed Job Deduction + Usage Credit Ledger.

Deduction model (2026-08-05, explicit user request): a single Home
Services-wide PERCENTAGE_COMMISSION, set in Home Services Finance >
Monetization ("provider_percentage" on the current published
VerticalMonetizationPolicy), applied to the price the tenant actually
collected from the customer for that job (`job.completion_data
.collected_amount`) — never an internal catalog price. This replaced the
old per-service flat "Provider Completion Charge Config" table
(ServicePricingRule.completed_job_deduction_credits), which is kept as a
fallback ONLY for the (now unreachable-from-the-UI) case where no
PERCENTAGE_COMMISSION policy is published, so historical/manually-set
rows don't silently start charging 0.

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


async def resolve_completed_job_deduction_credits(
    db: AsyncSession,
    master_service_id: uuid.UUID,
    offering_type_id: uuid.UUID | None,
    brand_id: uuid.UUID | None,
) -> tuple[Decimal, uuid.UUID | None]:
    """Legacy per-service flat-credit lookup. Mirrors the specificity
    ranking used by HS6's bargain-rule resolution — service+type+brand (3)
    > service+type (2) > service-only (1). A rule scoped to a *different*
    type/brand than requested is never eligible (score -1), preventing
    the ticket's explicit "Window AC LG deduction used for Split AC LG"
    failure mode. Only reached today when no PERCENTAGE_COMMISSION policy
    is published for Home Services — see `resolve_commission_credits`."""
    from app.engines.admin_catalog.models import ServicePricingRule

    rows = (await db.execute(
        select(ServicePricingRule).where(
            ServicePricingRule.master_service_id == master_service_id,
            ServicePricingRule.is_active.is_(True),
        )
    )).scalars().all()

    def _specificity(rule) -> int:
        has_type = offering_type_id is not None and rule.service_type_id == offering_type_id
        has_brand = brand_id is not None and rule.brand_id == brand_id
        if rule.service_type_id is not None and rule.service_type_id != offering_type_id:
            return -1
        if rule.brand_id is not None and rule.brand_id != brand_id:
            return -1
        if has_type and has_brand:
            return 3
        if has_type:
            return 2
        if rule.service_type_id is None and rule.brand_id is None:
            return 1
        return -1

    eligible = [r for r in rows if _specificity(r) >= 0]
    eligible.sort(key=lambda r: (_specificity(r), r.created_at), reverse=True)
    if not eligible:
        return Decimal("0"), None
    best = eligible[0]
    return Decimal(str(best.completed_job_deduction_credits or 0)), best.id


async def resolve_commission_credits(
    db: AsyncSession,
    *,
    job_price: Decimal | None,
    category_id: uuid.UUID | None,
    master_service_id: uuid.UUID,
    offering_type_id: uuid.UUID | None,
    brand_id: uuid.UUID | None,
    job_type_id: uuid.UUID | None = None,
) -> tuple[Decimal, str | None]:
    """Returns (credits, deduction_source_label). Each Home Services
    category carries its own commission rate (`ServiceCategory
    .commission_pct`, edited per-category in the Monetization tab) —
    PERCENTAGE_COMMISSION must be published on the Home Services vertical's
    Monetization policy for this to be live at all, but the actual rate
    applied is the job's own category's rate, falling back to the policy's
    vertical-wide `provider_percentage` only if that category hasn't set
    its own. Falls back further to the legacy per-service flat-credit
    table (see module docstring) if no PERCENTAGE_COMMISSION policy is
    published for Home Services at all."""
    from app.engines.vertical_catalog.models import Vertical
    from app.engines.vertical_monetization.models import (
        MonetizationJobTypeRule,
        VerticalMonetizationPolicy,
    )
    from app.engines.admin_catalog.models import ServiceCategory

    vertical = (await db.execute(
        select(Vertical).where(Vertical.key == _HS_KEY)
    )).scalar_one_or_none()
    policy = None
    if vertical:
        policy = (await db.execute(
            select(VerticalMonetizationPolicy).where(
                VerticalMonetizationPolicy.vertical_id == vertical.id,
                VerticalMonetizationPolicy.is_current.is_(True),
            )
        )).scalar_one_or_none()

    if policy is not None and policy.provider_model == "COMPLETION_CREDITS":
        if job_type_id is not None:
            override = (await db.execute(
                select(MonetizationJobTypeRule).where(
                    MonetizationJobTypeRule.policy_id == policy.id,
                    MonetizationJobTypeRule.job_type_id == job_type_id,
                    MonetizationJobTypeRule.status == "active",
                )
            )).scalar_one_or_none()
            if override is not None:
                source = f"monetization_job_type_rule:{override.id}"
                if not override.provider_charge_enabled:
                    return Decimal("0"), source
                if override.provider_charge_credit_units is not None:
                    return Decimal(str(override.provider_charge_credit_units)), source

        return Decimal(str(policy.provider_credit_units or 0)), f"monetization_policy:{policy.id}"

    if (
        policy is not None
        and policy.provider_model == "PERCENTAGE_COMMISSION"
        and job_price is not None
        and job_price > 0
    ):
        pct = None
        source = None
        if category_id is not None:
            category = await db.get(ServiceCategory, category_id)
            if category is not None and category.commission_pct is not None:
                pct = Decimal(str(category.commission_pct))
                source = f"category_commission:{category_id}"
        if pct is None and policy.provider_percentage is not None:
            pct = Decimal(str(policy.provider_percentage))
            source = f"monetization_policy:{policy.id}"
        if pct is not None:
            credits = (job_price * pct / Decimal("100")).quantize(Decimal("0.01"))
            return credits, source

    # A current policy using NONE/SUBSCRIPTION/etc. explicitly means this
    # usage-credit wallet must not be charged. Do not silently resurrect an
    # older service-pricing rule underneath a published policy.
    if policy is not None:
        return Decimal("0"), f"monetization_policy:{policy.id}"

    legacy_credits, pricing_rule_id = await resolve_completed_job_deduction_credits(
        db, master_service_id, offering_type_id, brand_id,
    )
    return legacy_credits, (str(pricing_rule_id) if pricing_rule_id else None)


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
