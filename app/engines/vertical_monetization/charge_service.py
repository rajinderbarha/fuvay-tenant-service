"""VERTICAL-MONETIZATION: customer platform-fee charge lifecycle.

A charge is created (server-side, never client-supplied) at the point the
chargeable service amount becomes known -- booking confirmation for
fixed/range services, or current-quote customer-approval for repair
services. It is idempotent per source record (one charge per booking, one
per approved quote version) so re-running the triggering event never
double-charges. Payment collection reuses the existing, already-integrated
Razorpay payment engine (app.engines.payment) rather than inventing a new
gateway integration.
"""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.vertical_catalog.models import Vertical
from app.engines.vertical_monetization.calculation_service import (
    calculate_customer_platform_fee, get_current_policy, to_minor,
)
from app.engines.vertical_monetization.models import CustomerPlatformFeeCharge
from app.exceptions import ServiceOSException

log = logging.getLogger(__name__)


async def _get_vertical_id(db: AsyncSession, key: str) -> uuid.UUID | None:
    v = (await db.execute(select(Vertical).where(Vertical.key == key))).scalar_one_or_none()
    return v.id if v else None


async def _existing_charge(db: AsyncSession, idempotency_key: str) -> CustomerPlatformFeeCharge | None:
    return (await db.execute(select(CustomerPlatformFeeCharge).where(
        CustomerPlatformFeeCharge.idempotency_key == idempotency_key))).scalar_one_or_none()


async def create_charge_for_booking(
    db: AsyncSession, *, vertical_key: str, booking_id: uuid.UUID, tenant_id: uuid.UUID | None,
    customer_id: uuid.UUID | None, service_amount_major: Decimal, source_event: str,
) -> CustomerPlatformFeeCharge | None:
    """Fixed/price-range services: charge computed and snapshotted at
    booking confirmation, before the customer's final confirmation screen.
    Returns None (no charge row) only when no vertical/policy resolves --
    NONE-model policies still get a zero-fee charge row so the snapshot
    trail is complete."""
    vertical_id = await _get_vertical_id(db, vertical_key)
    if not vertical_id:
        return None
    idem = f"booking:{booking_id}"
    existing = await _existing_charge(db, idem)
    if existing:
        return existing

    policy = await get_current_policy(db, vertical_id)
    result = calculate_customer_platform_fee(
        policy=policy, service_subtotal_minor=to_minor(service_amount_major),
        calculation_basis="booking_price_snapshot",
    )
    charge = CustomerPlatformFeeCharge(
        idempotency_key=idem, vertical_id=vertical_id, tenant_id=tenant_id, customer_id=customer_id,
        booking_id=booking_id, policy_id=uuid.UUID(result["policy_id"]) if result["policy_id"] else None,
        policy_version=result["policy_version"], calculation_basis="booking_price_snapshot",
        service_subtotal_minor=to_minor(service_amount_major),
        chargeable_subtotal_minor=to_minor(result["chargeable_subtotal"]),
        fee_amount_minor=result["fee_amount_minor"],
        total_payable_minor=result["total_payable_minor"],
        currency=result["currency"],
        collection_stage=result["collection_stage"] or "before_booking_confirmation",
        status="NOT_REQUIRED" if result["fee_amount_minor"] == 0 else "PENDING",
        calculation_breakdown=result["calculation_breakdown"],
        source_event=source_event,
    )
    db.add(charge)
    await db.flush()
    return charge


async def create_charge_for_quote(
    db: AsyncSession, *, vertical_key: str, quote_id: uuid.UUID, quote_version: int, is_current: bool,
    job_id: uuid.UUID, tenant_id: uuid.UUID | None, customer_id: uuid.UUID | None,
    customer_payable_amount: Decimal, source_event: str,
) -> CustomerPlatformFeeCharge | None:
    """Repair/inspection services: charge computed only from the CURRENT
    approved quote version. A superseded quote can never create or
    authorize a charge (non-negotiable rule)."""
    if not is_current:
        raise ServiceOSException("PAYMENT_CONTEXT_UNRESOLVED",
                                 "Cannot charge a platform fee against a superseded quote.",
                                 status_code=409)
    vertical_id = await _get_vertical_id(db, vertical_key)
    if not vertical_id:
        return None
    idem = f"quote:{quote_id}:v{quote_version}"
    existing = await _existing_charge(db, idem)
    if existing:
        return existing

    policy = await get_current_policy(db, vertical_id)
    result = calculate_customer_platform_fee(
        policy=policy, service_subtotal_minor=to_minor(customer_payable_amount),
        calculation_basis="approved_quote",
    )
    charge = CustomerPlatformFeeCharge(
        idempotency_key=idem, vertical_id=vertical_id, tenant_id=tenant_id, customer_id=customer_id,
        job_id=job_id, quote_id=quote_id, quote_version=quote_version,
        policy_id=uuid.UUID(result["policy_id"]) if result["policy_id"] else None,
        policy_version=result["policy_version"], calculation_basis="approved_quote",
        service_subtotal_minor=to_minor(customer_payable_amount),
        chargeable_subtotal_minor=to_minor(result["chargeable_subtotal"]),
        fee_amount_minor=result["fee_amount_minor"],
        total_payable_minor=result["total_payable_minor"],
        currency=result["currency"],
        collection_stage=result["collection_stage"] or "after_estimate_approval",
        status="NOT_REQUIRED" if result["fee_amount_minor"] == 0 else "PENDING",
        calculation_breakdown=result["calculation_breakdown"],
        source_event=source_event,
    )
    db.add(charge)
    await db.flush()
    return charge


async def create_payment_order_for_charge(
    db: AsyncSession, *, charge_id: uuid.UUID, customer_id: uuid.UUID,
) -> dict:
    from app.engines.payment.service import PaymentService
    from app.engines.payment.constants import PaymentType

    charge = await db.get(CustomerPlatformFeeCharge, charge_id)
    if not charge:
        raise ServiceOSException("NOT_FOUND", "Charge not found", status_code=404)
    if charge.customer_id and charge.customer_id != customer_id:
        raise ServiceOSException("PERMISSION_DENIED", "This charge does not belong to you.", status_code=403)
    if charge.status == "PAID":
        raise ServiceOSException("PAYMENT_ALREADY_COMPLETED", "This platform fee has already been paid.", status_code=409)
    if charge.status == "NOT_REQUIRED":
        raise ServiceOSException("VALIDATION_ERROR", "No platform fee is due for this charge.", status_code=422)

    if not charge.tenant_id:
        raise ServiceOSException("PAYMENT_CONTEXT_UNRESOLVED",
                                 "This charge has no resolved tenant context yet.", status_code=409)

    pay_svc = PaymentService(db=db)
    order = await pay_svc.create_payment_order(
        tenant_id=charge.tenant_id,  # record-routing only -- CUSTOMER_PLATFORM_FEE is never split with this tenant
        booking_id=str(charge.booking_id or charge.job_id or charge.id),
        customer_id=customer_id,
        amount=Decimal(charge.fee_amount_minor) / 100,
        payment_type=PaymentType.CUSTOMER_PLATFORM_FEE,
        gateway="razorpay",
        extra_notes={"charge_id": str(charge.id)},
    )
    order["charge_id"] = str(charge.id)
    return order


async def assert_customer_platform_fee_paid_if_required(db: AsyncSession, job) -> None:
    """Backend-controlled payment gate for work start. Only blocks when a
    charge exists AND its policy's collection_stage is
    'before_work_start' AND it is not yet PAID/NOT_REQUIRED/WAIVED. If no
    charge/policy exists for this job (vertical unconfigured or a fixed
    booking whose fee is collected at a different stage), this is a no-op
    -- never a new blocker for existing, working flows."""
    charge = (await db.execute(select(CustomerPlatformFeeCharge).where(
        CustomerPlatformFeeCharge.job_id == job.id,
    ).order_by(CustomerPlatformFeeCharge.created_at.desc()))).scalars().first()
    if not charge:
        return
    if charge.collection_stage != "before_work_start":
        return
    if charge.status in ("PAID", "NOT_REQUIRED", "WAIVED"):
        return
    if charge.status == "FAILED":
        raise ServiceOSException("CUSTOMER_PLATFORM_FEE_PAYMENT_FAILED",
                                 "The customer's platform fee payment failed. Work cannot start.",
                                 status_code=402)
    raise ServiceOSException("CUSTOMER_PLATFORM_FEE_REQUIRED",
                             "The customer must pay the Fuvay platform fee before work can start.",
                             status_code=402)
