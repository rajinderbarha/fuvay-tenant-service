"""A job that ran out of time, and what it costs.

One sweep, one job at a time:

  1. the customer is released -- the job is cancelled so they can rebook
     immediately, which is the whole point of acting on a breach;
  2. the provider is charged the admin-set penalty;
  3. if the admin chose to, that same amount is issued to the customer as
     service credit, spendable on their next booking;
  4. health takes the hit, and a provider who falls through the threshold is
     suspended until a date.

Every number here is policy, published and audited like a commission rate.
Nothing is hardcoded, because a penalty an operator cannot change or roll back
is a penalty they cannot defend.

The clock runs from the SCHEDULED SLOT. `sla_due_at` is stamped when the job is
scheduled, so a breach is decided by that timestamp and never by when this
sweep happened to run: a late sweep reaches the same outcome as a punctual one.
"""
from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ServiceOSException

logger = structlog.get_logger("execution.sla_breach")

#: Statuses a breach can still act on. A job already finished, cancelled or
#: paid for is nobody's fault any more.
BREACHABLE_STATUSES = (
    "pending_assignment", "assigned", "accepted", "scheduled",
    "on_the_way", "reached_site", "customer_not_available",
)

_HS_KEY = "home_services"


async def _policy(db: AsyncSession):
    """The published Home Services monetization policy, scoped to its vertical.

    `is_current` is unique PER VERTICAL, so an unscoped read could return
    another vertical's penalty.
    """
    return (await db.execute(text(
        "SELECT p.id, p.sla_breach_hours, p.sla_penalty_amount, "
        "       p.sla_penalty_to_customer, p.sla_penalty_debt_cap, "
        "       p.sla_auto_cancel, p.sla_notify_provider, p.sla_penalty_type, "
        "       p.sla_penalty_percentage, p.sla_penalty_min, p.sla_penalty_max, "
        "       p.sla_breachable_statuses, "
        "       p.health_suspension_threshold, p.health_suspension_days, "
        "       p.health_reinstatement_score "
        "FROM vertical_monetization_policies p "
        "JOIN verticals v ON v.id = p.vertical_id "
        "WHERE p.is_current = true AND p.status = 'published' AND v.key = :k "
        "LIMIT 1"
    ), {"k": _HS_KEY})).first()


def compute_due_at(scheduled_date: dt.date | None, breach_hours: int | None) -> dt.datetime | None:
    """When a job scheduled for this date runs out of time.

    Measured from the END of the scheduled day, so "1 day late" means a full
    day after the day the customer was promised -- not from booking creation,
    which would breach a job booked well in advance while nothing is late.
    """
    if scheduled_date is None or not breach_hours or breach_hours <= 0:
        return None
    end_of_day = dt.datetime.combine(
        scheduled_date + dt.timedelta(days=1), dt.time.min, tzinfo=dt.timezone.utc)
    return end_of_day + dt.timedelta(hours=int(breach_hours))


async def stamp_due_at(db: AsyncSession, job_id: uuid.UUID) -> dt.datetime | None:
    """Set `sla_due_at` from the job's scheduled date and the live policy."""
    policy = await _policy(db)
    if policy is None or not policy.sla_breach_hours:
        return None
    row = (await db.execute(text(
        "SELECT scheduled_date FROM service_jobs WHERE id = :id"), {"id": str(job_id)})).first()
    if row is None:
        return None
    due = compute_due_at(row.scheduled_date, policy.sla_breach_hours)
    if due is not None:
        await db.execute(text(
            "UPDATE service_jobs SET sla_due_at = :due, updated_at = now() WHERE id = :id"
        ), {"due": due, "id": str(job_id)})
    return due


def resolve_penalty(policy, *, job_value: Decimal | None,
                    job_type_override: Decimal | None = None) -> Decimal:
    """What this breach costs, before the debt cap.

    A per-job-type override wins outright -- that is the point of setting one.
    Otherwise a percentage is taken of the job's value, so abandoning a large
    job costs more than abandoning a small one, clamped to the configured floor
    and ceiling. With no job value to work from, a percentage cannot be
    computed honestly and the flat amount is used instead.
    """
    if job_type_override is not None:
        return max(Decimal("0"), Decimal(str(job_type_override)))

    flat = Decimal(str(policy.sla_penalty_amount or 0))
    if (policy.sla_penalty_type or "fixed") != "percentage":
        return flat

    pct = Decimal(str(policy.sla_penalty_percentage or 0))
    if job_value is None or job_value <= 0 or pct <= 0:
        return flat

    amount = (Decimal(str(job_value)) * pct / Decimal("100")).quantize(Decimal("0.01"))
    if policy.sla_penalty_min is not None:
        amount = max(amount, Decimal(str(policy.sla_penalty_min)))
    if policy.sla_penalty_max is not None:
        amount = min(amount, Decimal(str(policy.sla_penalty_max)))
    return max(Decimal("0"), amount)


async def _job_type_override(db: AsyncSession, *, policy_id, job_type_id):
    """The per-job-type rule for this policy version, if the admin set one.

    Returns (enabled, amount_override). A disabled rule means this job type is
    never penalised, which is a deliberate choice an admin can make for, say,
    consultations.
    """
    if job_type_id is None:
        return True, None
    row = (await db.execute(text(
        "SELECT sla_penalty_enabled, sla_penalty_amount FROM monetization_job_type_rules "
        "WHERE policy_id = :p AND job_type_id = :j AND status = 'active'"
    ), {"p": str(policy_id), "j": str(job_type_id)})).first()
    if row is None:
        return True, None
    return bool(row.sla_penalty_enabled), row.sla_penalty_amount


async def _charge_penalty(db: AsyncSession, *, tenant_id, job_id, amount: Decimal,
                          cap: Decimal | None) -> Decimal:
    """Withdraw the penalty from the provider ONLY -- nothing reaches the customer.

    Allowed to take a balance negative: a provider already at zero would
    otherwise face no penalty at all, which removes the deterrent exactly where
    it is most needed. `cap` is how far into debt a provider may be driven, so
    repeated breaches cannot spiral into a balance they can never clear.
    """
    balance = Decimal(str((await db.execute(text(
        "SELECT COALESCE(credit_balance, 0) FROM tenant_billing "
        "WHERE tenant_id = :t FOR UPDATE"), {"t": str(tenant_id)})).scalar() or 0))

    charge = amount
    if cap is not None:
        # Never take the balance below -cap. Already past it: take nothing.
        allowed = max(Decimal("0"), balance + cap)
        charge = min(amount, allowed)
    if charge <= 0:
        return Decimal("0")

    after = balance - charge
    await db.execute(text(
        "UPDATE tenant_billing SET credit_balance = :b, updated_at = now() WHERE tenant_id = :t"
    ), {"b": after, "t": str(tenant_id)})
    await db.execute(text(
        "INSERT INTO usage_credit_ledger (tenant_id, job_id, event_type, credit_delta, "
        "  balance_before, balance_after, deduction_source, reason) "
        "VALUES (:t, :j, 'sla_breach_penalty', :d, :before, :after, 'sla_breach', :r)"
    ), {"t": str(tenant_id), "j": str(job_id), "d": float(-charge),
        "before": float(balance), "after": float(after),
        "r": f"SLA breach penalty for job {job_id}"})
    return charge


async def _penalise_and_compensate(db: AsyncSession, *, tenant_id, customer_id,
                                   booking_id, job_id, amount: Decimal) -> Decimal:
    """Take the penalty from the provider AND give it to the customer.

    One call, because `issue_provider_funded_customer_credit` already does both
    halves atomically -- it debits provider credit and issues the customer a
    service credit they can spend at checkout. Calling it alongside
    `_charge_penalty` would deduct the provider twice for one breach.
    """
    if customer_id is None or amount <= 0:
        return Decimal("0")
    from app.engines.customer_credits.service import issue_provider_funded_customer_credit

    result = await issue_provider_funded_customer_credit(
        db,
        tenant_id=tenant_id,
        customer_id=customer_id,
        amount=amount,
        reference_type="sla_breach",
        reference_id=job_id,
        reason=f"Service level breach on job {job_id}",
        actor_id=None,
        actor_role="system",
        booking_id=booking_id,
        job_id=job_id,
    )
    return Decimal(str(result.get("provider_credit_deducted") or 0))


async def _notify_customer(db: AsyncSession, *, job, compensated: bool,
                           amount: Decimal) -> None:
    """Best-effort. A notification failure must never leave a breach unactioned."""
    if job.customer_id is None:
        return
    try:
        from app.engines.platform_notifications.models import InAppNotification
        body = ("We could not complete your booking in time, so it has been cancelled "
                "and you can book again straight away.")
        if compensated and amount > 0:
            body += (f" Rs.{amount:,.2f} has been added to your account as service "
                     f"credit, which will apply to your next booking.")
        db.add(InAppNotification(
            user_id=job.customer_id, tenant_id=job.tenant_id,
            notification_type="booking_cancelled_sla",
            title="Your booking was cancelled",
            body=body,
            action_url="/customer/book", action_label="Book again",
            source_record_type="service_jobs", source_record_id=job.id,
            severity="warning",
        ))
    except Exception as exc:  # noqa: BLE001
        logger.warning("sla_breach.notify_failed", job_id=str(job.id), error=str(exc))


async def _notify_provider(db: AsyncSession, *, job, amount: Decimal,
                           cancelled: bool) -> None:
    """Tell the provider they were charged, and why.

    Finding an unexplained deduction in your balance is how an operator loses
    a provider's trust; a penalty they can see and query is one they can act on.
    """
    try:
        from app.engines.platform_notifications.models import InAppNotification
        owner = (await db.execute(text(
            "SELECT id FROM users WHERE tenant_id = :t AND role = 'tenant_owner' "
            "AND is_active = true LIMIT 1"), {"t": str(job.tenant_id)})).scalar()
        if owner is None:
            return
        body = (f"Rs.{amount:,.2f} was deducted for missing the service window on job "
                f"{job.id}.")
        body += (" The booking was cancelled and the customer can rebook."
                 if cancelled else " The job remains open.")
        db.add(InAppNotification(
            user_id=owner, tenant_id=job.tenant_id,
            notification_type="sla_penalty_charged",
            title="Service level penalty applied",
            body=body,
            action_url="/home-services/finance", action_label="View finance",
            source_record_type="service_jobs", source_record_id=job.id,
            severity="warning",
        ))
    except Exception as exc:  # noqa: BLE001 -- never block the penalty on a notice
        logger.warning("sla_breach.provider_notify_failed", job_id=str(job.id), error=str(exc))


async def waive_penalty(db: AsyncSession, *, job_id: uuid.UUID,
                        actor_id: uuid.UUID | None, reason: str) -> dict:
    """Reverse a penalty charged in error.

    The ledger is append-only and is what an operator has to defend, so nothing
    is edited or deleted: a compensating credit is posted and the job is stamped
    so the same breach cannot be waived twice.

    Customer credit issued from the penalty is revoked only to the extent it is
    STILL UNSPENT. Money the customer has already put toward a booking is
    theirs -- clawing it back would punish them for a provider's failure and a
    platform's mistake.
    """
    job = (await db.execute(text(
        "SELECT id, tenant_id, customer_id, sla_penalty_charged, sla_penalty_waived_at "
        "FROM service_jobs WHERE id = :id FOR UPDATE"), {"id": str(job_id)})).first()
    if job is None:
        raise ServiceOSException("NOT_FOUND", "Job not found.", status_code=404)
    if job.sla_penalty_waived_at is not None:
        raise ServiceOSException("SLA_PENALTY_ALREADY_WAIVED",
                                 "This penalty has already been waived.", status_code=409)
    charged = Decimal(str(job.sla_penalty_charged or 0))
    if charged <= 0:
        raise ServiceOSException("SLA_PENALTY_NOT_CHARGED",
                                 "No penalty was charged for this job.", status_code=409)

    balance = Decimal(str((await db.execute(text(
        "SELECT COALESCE(credit_balance, 0) FROM tenant_billing WHERE tenant_id = :t FOR UPDATE"
    ), {"t": str(job.tenant_id)})).scalar() or 0))
    after = balance + charged
    await db.execute(text(
        "UPDATE tenant_billing SET credit_balance = :b, updated_at = now() WHERE tenant_id = :t"
    ), {"b": after, "t": str(job.tenant_id)})
    await db.execute(text(
        "INSERT INTO usage_credit_ledger (tenant_id, job_id, event_type, credit_delta, "
        "  balance_before, balance_after, deduction_source, reason, created_by) "
        "VALUES (:t, :j, 'sla_penalty_waived', :d, :before, :after, 'sla_waiver', :r, :actor)"
    ), {"t": str(job.tenant_id), "j": str(job.id), "d": float(charged),
        "before": float(balance), "after": float(after),
        "r": f"Penalty waived: {reason}", "actor": str(actor_id) if actor_id else None})

    revoked = Decimal("0")
    if job.customer_id is not None:
        revoked = await _revoke_unspent_customer_credit(db, job_id=job.id)

    await db.execute(text(
        "UPDATE service_jobs SET sla_penalty_waived_at = now(), updated_at = now() "
        "WHERE id = :id"), {"id": str(job.id)})
    logger.info("sla_breach.penalty_waived", job_id=str(job.id),
                refunded=float(charged), customer_credit_revoked=float(revoked))
    return {"job_id": str(job.id), "refunded_to_provider": float(charged),
            "customer_credit_revoked": float(revoked)}


async def _revoke_unspent_customer_credit(db: AsyncSession, *, job_id: uuid.UUID) -> Decimal:
    """Take back only what the customer has not already used."""
    rows = (await db.execute(text(
        "SELECT id, remaining_amount FROM customer_service_credits "
        "WHERE reference_type = 'sla_breach' AND reference_id = :j "
        "  AND status = 'active' FOR UPDATE"), {"j": str(job_id)})).fetchall()
    revoked = Decimal("0")
    for row in rows:
        remaining = Decimal(str(row.remaining_amount or 0))
        if remaining <= 0:
            continue
        await db.execute(text(
            "UPDATE customer_service_credits SET remaining_amount = 0, status = 'revoked', "
            "  updated_at = now() WHERE id = :id"), {"id": str(row.id)})
        revoked += remaining
    return revoked


async def sweep(db: AsyncSession, *, limit: int = 200) -> dict:
    """Act on every job past its SLA, then reinstate anyone whose suspension
    has run out. Safe to run repeatedly and safe to run late."""
    policy = await _policy(db)
    if policy is None:
        return {"breached": 0, "penalised": 0, "compensated": 0,
                "suspended": 0, "reinstated": 0, "reason": "no_published_policy"}

    cap = Decimal(str(policy.sla_penalty_debt_cap)) if policy.sla_penalty_debt_cap is not None else None

    # Which statuses can breach is admin policy, falling back to the code
    # default so an unset policy behaves as before.
    statuses = policy.sla_breachable_statuses or list(BREACHABLE_STATUSES)
    if not isinstance(statuses, list) or not statuses:
        statuses = list(BREACHABLE_STATUSES)

    due = (await db.execute(text(
        "SELECT j.id, j.tenant_id, j.booking_id, j.customer_id, j.status, j.job_type_id, "
        "       COALESCE(i.total_amount, 0) AS job_value "
        "FROM service_jobs j "
        "LEFT JOIN service_invoices i ON i.job_id = j.id "
        "WHERE j.sla_due_at IS NOT NULL AND j.sla_breached_at IS NULL "
        "  AND j.sla_due_at <= now() AND j.status = ANY(:statuses) "
        "ORDER BY j.sla_due_at LIMIT :lim FOR UPDATE OF j SKIP LOCKED"
    ), {"statuses": statuses, "lim": limit})).fetchall()

    breached = penalised = compensated = 0
    for job in due:
        # 1. Release the customer first, if the admin wants breaches to cancel.
        #    Everything after this is about money and none of it should delay
        #    letting them rebook. With auto-cancel off the breach is still
        #    recorded and still costs -- the job simply stays open.
        if policy.sla_auto_cancel:
            await db.execute(text(
                "UPDATE service_jobs SET status = 'cancelled', sla_breached_at = now(), "
                "  updated_at = now() WHERE id = :id"), {"id": str(job.id)})
        else:
            await db.execute(text(
                "UPDATE service_jobs SET sla_breached_at = now(), updated_at = now() "
                "WHERE id = :id"), {"id": str(job.id)})
        breached += 1

        enabled, override = await _job_type_override(
            db, policy_id=policy.id, job_type_id=job.job_type_id)
        penalty = resolve_penalty(
            policy,
            job_value=Decimal(str(job.job_value or 0)) or None,
            job_type_override=override,
        ) if enabled else Decimal("0")

        # 2. The penalty. Exactly ONE of these runs: the compensating path
        #    already debits the provider, so running both would charge twice
        #    for a single breach.
        taken = Decimal("0")
        if penalty > 0:
            if policy.sla_penalty_to_customer and job.customer_id is not None:
                try:
                    taken = await _penalise_and_compensate(
                        db, tenant_id=job.tenant_id, customer_id=job.customer_id,
                        booking_id=job.booking_id, job_id=job.id, amount=penalty)
                    if taken > 0:
                        compensated += 1
                except Exception as exc:  # noqa: BLE001
                    # Compensation failed; still charge the provider, so a
                    # customer-side problem cannot let a breach go unpenalised.
                    logger.warning("sla_breach.compensation_failed",
                                   job_id=str(job.id), error=str(exc))
                    taken = await _charge_penalty(
                        db, tenant_id=job.tenant_id, job_id=job.id,
                        amount=penalty, cap=cap)
            else:
                taken = await _charge_penalty(
                    db, tenant_id=job.tenant_id, job_id=job.id, amount=penalty, cap=cap)
            if taken > 0:
                penalised += 1

        if taken > 0:
            await db.execute(text(
                "UPDATE service_jobs SET sla_penalty_charged = :a WHERE id = :id"
            ), {"a": taken, "id": str(job.id)})
            if policy.sla_notify_provider:
                await _notify_provider(db, job=job, amount=taken,
                                       cancelled=bool(policy.sla_auto_cancel))

        # 3. Tell the customer. Cancelling silently would be worse than a late
        #    job: the point of acting on a breach is that they can rebook, and
        #    they cannot do that if nobody tells them the slot is gone.
        if policy.sla_auto_cancel:
            await _notify_customer(db, job=job, compensated=bool(
                policy.sla_penalty_to_customer and taken > 0), amount=taken)

        logger.info("sla_breach.actioned", job_id=str(job.id), tenant_id=str(job.tenant_id),
                    penalty_taken=float(taken),
                    compensated_customer=bool(policy.sla_penalty_to_customer and taken > 0))

    suspended = await _apply_health_suspensions(db, policy)
    reinstated = await reinstate_due(db, policy)
    return {"breached": breached, "penalised": penalised, "compensated": compensated,
            "suspended": suspended, "reinstated": reinstated}


async def _apply_health_suspensions(db: AsyncSession, policy) -> int:
    """Suspend providers whose health has fallen through the threshold.

    Health is 20% of provider matching, so a falling score already costs a
    provider work. This is the hard stop past the point where ranking alone is
    an adequate answer.
    """
    if policy.health_suspension_threshold is None or not policy.health_suspension_days:
        return 0
    rows = (await db.execute(text(
        "UPDATE tenants SET status = 'suspended', suspended_at = now(), "
        "  suspended_until = now() + make_interval(days => :days), "
        "  suspension_reason = 'health_below_threshold', updated_at = now() "
        "WHERE health_score IS NOT NULL AND health_score < :threshold "
        "  AND status <> 'suspended' "
        "RETURNING id"
    ), {"days": int(policy.health_suspension_days),
        "threshold": float(policy.health_suspension_threshold)})).fetchall()
    for r in rows:
        logger.info("sla_breach.tenant_suspended", tenant_id=str(r[0]),
                    days=int(policy.health_suspension_days))
    return len(rows)


async def reinstate_due(db: AsyncSession, policy=None) -> int:
    """Lift suspensions that have served their time, and rebaseline health.

    Without the rebaseline this is a trap rather than a suspension: health is
    computed from work, a suspended provider does none, so their score is still
    below the threshold on the day they return and they are suspended again
    immediately -- permanently. Reinstating at a score that wins some work lets
    them earn their way back up, or back down, on merit.
    """
    if policy is None:
        policy = await _policy(db)
    if policy is None:
        return 0
    restore_to = policy.health_reinstatement_score

    rows = (await db.execute(text(
        "UPDATE tenants SET status = 'active', suspended_until = NULL, "
        "  suspension_reason = NULL, "
        "  health_score = COALESCE(:restore, health_score), updated_at = now() "
        "WHERE suspended_until IS NOT NULL AND suspended_until <= now() "
        "  AND suspension_reason = 'health_below_threshold' "
        "RETURNING id"
    ), {"restore": float(restore_to) if restore_to is not None else None})).fetchall()
    for r in rows:
        logger.info("sla_breach.tenant_reinstated", tenant_id=str(r[0]),
                    health_restored_to=float(restore_to) if restore_to is not None else None)
    return len(rows)
