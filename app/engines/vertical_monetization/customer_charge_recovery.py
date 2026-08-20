"""HOME-SERVICES-FINANCE: Customer Platform Charge Recovery.

Confirmed payment model: the customer pays the PROVIDER directly (service
amount + the transparently-added platform fee, together). ServiceOS never
collects or holds that money. ServiceOS instead RECOVERS the fee-equivalent
by deducting it from the provider's own usage-credit balance -- a second,
independent ledger entry from the Provider Completion Charge
(`usage_credit_deduction.deduct_for_completed_job`), never combined into
one ambiguous commission record.

Both entries are written from the SAME real completion event
(execution/home_service_service.py's job-completion handler), each
independently idempotent per job_id so one failing can never falsely mark
the other successful.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

RECOVERY_EVENT_TYPE = "customer_platform_charge_recovery"


async def deduct_customer_platform_charge_recovery(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    booking_id: uuid.UUID,
    vertical_key: str,
    chargeable_amount: Decimal,
    snapshotted_fee_amount: Decimal | None = None,
    policy_reference: str | None = None,
    request_id: str | None = None,
) -> dict:
    """Idempotent per (job_id, event_type) -- a second call for the same job
    returns the existing ledger row instead of recovering twice."""
    from app.engines.tenant_engine.models import TenantBilling, UsageCreditLedger
    from app.engines.vertical_catalog.models import Vertical
    from app.engines.vertical_monetization.calculation_service import (
        calculate_customer_platform_fee, get_current_policy, to_minor, to_major,
    )

    existing = (await db.execute(
        select(UsageCreditLedger).where(
            UsageCreditLedger.job_id == job_id,
            UsageCreditLedger.event_type == RECOVERY_EVENT_TYPE,
        )
    )).scalars().first()
    if existing:
        return {**existing.to_dict(), "recovery_status": "already_recovered"}

    vertical = (await db.execute(select(Vertical).where(Vertical.key == vertical_key))).scalar_one_or_none()
    if not vertical:
        return {"recovery_status": "skipped", "reason": "vertical_not_found"}

    result = None
    if snapshotted_fee_amount is None:
        policy = await get_current_policy(db, vertical.id)
        result = calculate_customer_platform_fee(
            policy=policy, service_subtotal_minor=to_minor(chargeable_amount),
            calculation_basis="job_completion_fallback",
        )
        recovery_amount = Decimal(to_major(result["fee_amount_minor"]))
        policy_reference = policy_reference or (
            f"monetization_policy:{result['policy_id']}:v{result['policy_version']}"
        )
    else:
        # Invoice creation already snapshotted the policy-calculated fee.
        # Recover that exact amount even if an admin publishes a new policy
        # before the provider completes the job.
        recovery_amount = Decimal(str(snapshotted_fee_amount)).quantize(Decimal("0.01"))
        policy_reference = policy_reference or "invoice_platform_fee_snapshot"
    if recovery_amount <= 0:
        return {"recovery_status": "not_required", "reason": "no_customer_fee_policy_or_zero_fee"}

    billing = (await db.execute(select(TenantBilling).where(TenantBilling.tenant_id == tenant_id))).scalars().first()
    if not billing:
        billing = TenantBilling(tenant_id=tenant_id, credit_balance=Decimal("0"))
        db.add(billing)
        await db.flush()

    balance_before = Decimal(str(billing.credit_balance))
    balance_after = balance_before - recovery_amount
    billing.credit_balance = balance_after

    ledger = UsageCreditLedger(
        tenant_id=tenant_id, job_id=job_id, booking_id=booking_id,
        event_type=RECOVERY_EVENT_TYPE, credit_delta=-recovery_amount,
        balance_before=balance_before, balance_after=balance_after,
        reason=f"Customer platform charge recovery for job {job_id} ({policy_reference})",
        request_id=request_id,
    )
    db.add(ledger)
    await db.flush()
    return {
        **ledger.to_dict(), "recovery_status": "recovered",
        "fee_amount": str(recovery_amount),
        "policy_reference": policy_reference,
        "policy_version": result["policy_version"] if result is not None else None,
    }
