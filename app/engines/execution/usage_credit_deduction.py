"""HS9 — Completed Job Deduction + Usage Credit Ledger.

Resolves the deduction credits for a completed Home Services job using
the same specificity hierarchy already certified in HS6 for pricing
(brand+type > type-only > service-only — never fall back to an
unrelated type/brand combination), then applies an idempotent-per-job
deduction against the tenant's existing `tenant_billing.credit_balance`
and writes a `usage_credit_ledger` row.

Usage credits are internal platform credits, not money — never wallet,
payout, or escrow terminology anywhere in this module.
"""
from __future__ import annotations
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

DEDUCTION_EVENT_TYPE = "completed_job_deduction"


async def resolve_completed_job_deduction_credits(
    db: AsyncSession,
    master_service_id: uuid.UUID,
    offering_type_id: uuid.UUID | None,
    brand_id: uuid.UUID | None,
) -> tuple[Decimal, uuid.UUID | None]:
    """Returns (credits, pricing_rule_id). Mirrors the specificity ranking
    used by HS6's bargain-rule resolution — service+type+brand (3) >
    service+type (2) > service-only (1). A rule scoped to a *different*
    type/brand than requested is never eligible (score -1), preventing
    the ticket's explicit "Window AC LG deduction used for Split AC LG"
    failure mode."""
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


async def deduct_for_completed_job(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    booking_id: uuid.UUID,
    master_service_id: uuid.UUID,
    offering_type_id: uuid.UUID | None,
    brand_id: uuid.UUID | None,
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

    credits, pricing_rule_id = await resolve_completed_job_deduction_credits(
        db, master_service_id, offering_type_id, brand_id,
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
        deduction_source=str(pricing_rule_id) if pricing_rule_id else None,
        service_id=master_service_id, service_type_id=offering_type_id, brand_id=brand_id,
        reason=f"Completed Job Deduction for job {job_id}",
        request_id=request_id,
    )
    db.add(ledger)
    await db.flush()
    return {**ledger.to_dict(), "deduction_status": "deducted"}
