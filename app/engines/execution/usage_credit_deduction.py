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

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger("execution.usage_credit_deduction")

DEDUCTION_EVENT_TYPE = "completed_job_deduction"
_HS_KEY = "home_services"


#: Marks a resolution that failed only because this is not the lifecycle moment
#: the policy charges at -- distinct from "charged zero", which is a real
#: outcome worth a ledger row.
_EVENT_NOT_REACHED = "event_not_reached"

async def _resolve_commission_charge(
    db: AsyncSession,
    *,
    job_price: Decimal | None,
    category_id: uuid.UUID | None,
    master_service_id: uuid.UUID,
    offering_type_id: uuid.UUID | None,
    brand_id: uuid.UUID | None,
    job_type_id: uuid.UUID | None = None,
    chargeable_event: str = "job_completed",
    tenant_id: uuid.UUID | None = None,
) -> tuple[Decimal, str | None, dict]:
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
            return Decimal("0"), f"monetization_policy:{policy.id}:unsupported_model", {
                "policy_id": str(policy.id), "policy_version": getattr(policy, "version_number", None),
                "reason": "unsupported_provider_model",
            }
        override = None
        if job_type_id is not None:
            override = (await db.execute(
                select(MonetizationJobTypeRule).where(
                    MonetizationJobTypeRule.policy_id == policy.id,
                    MonetizationJobTypeRule.job_type_id == job_type_id,
                    MonetizationJobTypeRule.status == "active",
                )
            )).scalar_one_or_none()
        # WHEN the provider is charged is a policy decision. The policy-level
        # `provider_chargeable_event` used to be stored and validated but never
        # read here, so only a per-job-type override could influence timing --
        # and only by suppressing the charge entirely. The override still wins
        # for its own job type; otherwise the policy answers, defaulting to
        # completion so an unset policy behaves exactly as before.
        configured_event = (
            override.provider_chargeable_event if override is not None
            else (policy.provider_chargeable_event or "job_completed")
        )
        if configured_event != chargeable_event:
            source = (f"monetization_job_type_rule:{override.id}" if override is not None
                      else f"monetization_policy:{policy.id}")
            return Decimal("0"), f"{source}:{_EVENT_NOT_REACHED}", {
                "policy_id": str(policy.id), "policy_version": getattr(policy, "version_number", None),
                "configured_event": configured_event, "attempted_event": chargeable_event,
                "reason": _EVENT_NOT_REACHED,
            }
        health_snapshot = {
            "source": "not_applicable",
            "reason": "health_adjustment_disabled",
            "score": None,
            "band_key": None,
            "adjustment_percentage_points": "0",
        }
        health_adjustment = Decimal("0")
        health_enabled = bool(getattr(policy, "provider_health_adjustment_enabled", False))
        if health_enabled and policy.provider_model == "PERCENTAGE_COMMISSION" and tenant_id is not None:
            from app.engines.trust_quality.provider_health import get_provider_health_snapshot
            health_snapshot = await get_provider_health_snapshot(
                db,
                tenant_id,
                max_age_days=int(getattr(policy, "provider_health_score_max_age_days", 30) or 30),
            )
            adjustments = getattr(policy, "provider_health_adjustments_json", None) or {}
            if health_snapshot["source"] == "canonical":
                try:
                    health_adjustment = max(
                        Decimal("0"),
                        Decimal(str(adjustments.get(health_snapshot["band_key"], 0))),
                    )
                except Exception:
                    # Published policy validation prevents this, but fail safe
                    # to the base rate if old/corrupt data is encountered.
                    health_adjustment = Decimal("0")
                    health_snapshot["reason"] = "invalid_band_adjustment"
            health_snapshot["adjustment_percentage_points"] = str(health_adjustment)
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
            health_adjustment_percentage_points=health_adjustment,
        )
        source = (
            f"monetization_job_type_rule:{override.id}"
            if override is not None else f"monetization_policy:{policy.id}"
        )
        return Decimal(calculated["provider_charge_credit_units"]), source, {
            "policy_id": str(policy.id),
            "policy_version": getattr(policy, "version_number", None),
            "provider_model": calculated["provider_model"],
            "chargeable_event": chargeable_event,
            "job_type_rule_id": str(override.id) if override is not None else None,
            "calculation": calculated["provider_charge_breakdown"],
            "provider_health": health_snapshot,
            "final_credit_units": calculated["provider_charge_credit_units"],
        }

    # No hidden fallback: Home Services Monetization is the sole authority.
    # With no published policy, no provider charge is created.
    return Decimal("0"), None, {"reason": "no_published_policy"}


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
    """Compatibility facade returning the historical two-item tuple.

    Runtime completion uses the richer resolver below so its immutable ledger
    snapshot also records the provider-health decision. That shared resolver
    remains the authority for the ``configured_event`` resolved from
    ``policy.provider_chargeable_event`` and applies
    the backwards-compatible ``or "job_completed"`` default; this facade does
    not reimplement either rule.
    """
    credits, source, _snapshot = await _resolve_commission_charge(
        db,
        job_price=job_price,
        category_id=category_id,
        master_service_id=master_service_id,
        offering_type_id=offering_type_id,
        brand_id=brand_id,
        job_type_id=job_type_id,
        chargeable_event=chargeable_event,
    )
    if source is None and credits == Decimal("0"):
        return Decimal("0"), None
    return credits, source


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

    credits, deduction_source, calculation_snapshot = await _resolve_commission_charge(
        db, job_price=job_price, category_id=category_id,
        master_service_id=master_service_id, offering_type_id=offering_type_id, brand_id=brand_id,
        job_type_id=job_type_id,
        chargeable_event=chargeable_event,
        tenant_id=tenant_id,
    )

    # This lifecycle moment is not the one the policy charges at. Writing a
    # zero ledger row here would be indistinguishable from "evaluated and
    # charged nothing", and the idempotency guard above would then treat the
    # job as already handled -- so the real chargeable event, when it arrived,
    # would deduct nothing at all. Record nothing and let it come round again.
    if deduction_source and deduction_source.endswith(_EVENT_NOT_REACHED):
        return {
            "deduction_status": "not_yet_chargeable",
            "job_id": str(job_id),
            "chargeable_event": chargeable_event,
            "deduction_source": deduction_source,
            "credit_delta": 0,
        }

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
        calculation_snapshot_json=calculation_snapshot,
    )
    db.add(ledger)
    await db.flush()

    # A deduction can be what takes the workspace to zero, so the team state is
    # reconciled here rather than waiting for the next sweep -- otherwise a
    # provider keeps assigning work they can no longer pay commission on.
    try:
        from app.engines.vertical_catalog.seat_enforcement import sync_team_credit_suspension
        await sync_team_credit_suspension(db, tenant_id)
    except Exception as exc:  # noqa: BLE001 -- never undo a real deduction
        logger.warning("team.credit_sync_failed", tenant_id=str(tenant_id), error=str(exc))

    return {**ledger.to_dict(), "deduction_status": "deducted"}


async def attempt_charge_at_event(
    db: AsyncSession,
    *,
    job,
    chargeable_event: str,
    request_id: str | None = None,
) -> dict:
    """Offer a lifecycle moment to the policy and charge if it is the one.

    Called from every point a provider charge could legitimately fall due.
    The policy decides which of them actually charges; the rest resolve to
    `not_yet_chargeable` and write nothing, so the job stays chargeable when
    its configured moment arrives. The deduction is idempotent per job, so a
    job passing several of these moments is still charged exactly once.

    Failures are swallowed deliberately: a finance-side problem must never
    roll back genuine field work. The status is returned for the caller to log.
    """
    from app.engines.final_records.models import ServiceBooking
    from app.engines.home_service_booking.models import HomeServiceBookingDraft

    offering_type_id = brand_id = None
    job_price = None
    if job.booking_id:
        booking = await db.get(ServiceBooking, job.booking_id)
        if booking is not None:
            if booking.draft_id:
                draft = await db.get(HomeServiceBookingDraft, booking.draft_id)
                if draft is not None:
                    offering_type_id = draft.offering_type_id
                    brand_id = draft.brand_id
            # Only a basis for FIXED credit models -- publishing refuses to pair
            # PERCENTAGE_COMMISSION with a pre-completion event precisely
            # because this number is not the final invoiced value.
            snapshot = booking.price_snapshot or {}
            if isinstance(snapshot, dict) and snapshot.get("base_price") is not None:
                job_price = Decimal(str(snapshot["base_price"]))

    try:
        return await deduct_for_completed_job(
            db,
            tenant_id=job.tenant_id,
            job_id=job.id,
            booking_id=job.booking_id,
            master_service_id=job.offering_id,
            offering_type_id=offering_type_id,
            brand_id=brand_id,
            category_id=job.category_id,
            job_type_id=job.job_type_id,
            job_price=job_price,
            request_id=request_id,
            chargeable_event=chargeable_event,
        )
    except Exception as exc:  # noqa: BLE001 -- finance must not undo field work
        logger.warning("provider_charge.attempt_failed", job_id=str(job.id),
                       chargeable_event=chargeable_event, error=str(exc))
        return {"deduction_status": "failed", "error": str(exc)}
