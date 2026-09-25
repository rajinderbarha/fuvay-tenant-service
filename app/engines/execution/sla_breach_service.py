"""A job that ran out of time, and what it costs.

One sweep, one job at a time:

  1. the provider is charged the admin-set amount when the arrival slot ends;
  2. after the configured close window the provider is charged only the
     remainder of the configured cumulative total and the job is cancelled;
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

After verified arrival, `enforce_stalled_provider_stage` applies the same
two-step financial rule only when a provider-owned stage also exceeds its own
deadline. Customer-owned waits are never charged to the provider.
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
    "pending_assignment", "assigned", "accepted", "scheduled", "on_the_way",
)

# Post-arrival stages where the next move is owned by the technician/provider.
# Customer-owned waits are intentionally absent: a provider is not charged
# because a customer has not approved an estimate or was unavailable.
PROVIDER_PROGRESS_STATUSES = frozenset({
    "reached_site", "inspection_started", "inspection_done",
    "service_started", "work_done",
})

_HS_KEY = "home_services"


async def stage_waiting_on_customer(db: AsyncSession, job) -> bool:
    """Whether a nominally active stage is blocked on a real customer action.

    ``work_done`` starts as provider-owned: the technician must submit proof,
    request handover and declare payment.  Once either customer confirmation
    is genuinely pending, charging the provider for the same elapsed time is
    incorrect.  This query is deliberately based on durable records rather
    than a client-supplied flag.
    """
    if getattr(job, "status", None) != "work_done":
        return False
    result = await db.execute(text(
        "SELECT ("
        " EXISTS (SELECT 1 FROM service_job_completion_proofs p "
        "         WHERE p.job_id=:job_id AND p.status='submitted' "
        "           AND p.handover_status='requested') "
        " OR EXISTS (SELECT 1 FROM service_payment_records r "
        "            WHERE r.job_id=:job_id "
        "              AND r.provider_confirmed_at IS NOT NULL "
        "              AND r.customer_confirmed=false "
        "              AND COALESCE(r.payment_status,'') NOT IN "
        "                  ('dispute_open','disputed','reversed','cancelled'))"
        ")"
    ), {"job_id": str(job.id)})
    return bool(result.scalar())


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
        "       p.sla_penalty_max_days, p.sla_close_after_hours, "
        "       p.sla_total_penalty_amount, "
        "       p.health_suspension_threshold, p.health_suspension_days, "
        "       p.health_reinstatement_score "
        "FROM vertical_monetization_policies p "
        "JOIN verticals v ON v.id = p.vertical_id "
        "WHERE p.is_current = true AND p.status = 'published' AND v.key = :k "
        "LIMIT 1"
    ), {"k": _HS_KEY})).first()


def compute_due_at(scheduled_date: dt.date | None, scheduled_time_window: str | None,
                   breach_hours: int | None) -> dt.datetime | None:
    """When the first missed-arrival charge is due.

    The stored window is local IST wall-clock text.  Reuse the canonical slot
    parser so dashboards and financial enforcement agree on the exact moment.
    A zero-hour grace means the charge is due as soon as the slot ends.
    """
    if scheduled_date is None or breach_hours is None or breach_hours < 0:
        return None
    from app.engines.weather.slots import slot_end
    end = slot_end(scheduled_date, scheduled_time_window)
    return end + dt.timedelta(hours=int(breach_hours)) if end is not None else None


async def stamp_due_at(db: AsyncSession, job_id: uuid.UUID) -> dt.datetime | None:
    """Set the SLA from the promised slot and enroll only now/future actions.

    Migration 355 intentionally leaves old jobs unenrolled. Stamping happens
    on a new assignment or an approved schedule change, which is the safe
    point to start the new daily financial rule.
    """
    policy = await _policy(db)
    if policy is None or policy.sla_breach_hours is None:
        return None
    row = (await db.execute(text(
        "SELECT scheduled_date, scheduled_time_window FROM service_jobs WHERE id = :id"
    ), {"id": str(job_id)})).first()
    if row is None:
        return None
    due = compute_due_at(
        row.scheduled_date, row.scheduled_time_window, policy.sla_breach_hours)
    if due is not None:
        await db.execute(text(
            "UPDATE service_jobs SET sla_due_at = :due, "
            "sla_enforcement_started_at = COALESCE(sla_enforcement_started_at, now()), "
            "sla_next_penalty_at = :due, sla_stopped_at = NULL, updated_at = now() "
            "WHERE id = :id"
        ), {"due": due, "id": str(job_id)})
    return due


async def stop_sla(db: AsyncSession, job_id: uuid.UUID) -> None:
    """Stop future SLA charges once verified field work has begun."""
    await db.execute(text(
        "UPDATE service_jobs SET sla_stopped_at = COALESCE(sla_stopped_at, now()), "
        "sla_due_at = NULL, sla_next_penalty_at = NULL, updated_at = now() "
        "WHERE id = :id"
    ), {"id": str(job_id)})


def final_penalty_top_up(*, charged_so_far: Decimal,
                         total_penalty: Decimal) -> Decimal:
    """Amount still needed to reach the configured cumulative close penalty."""
    return max(Decimal("0"), Decimal(str(total_penalty)) - Decimal(str(charged_so_far)))


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
                          cap: Decimal | None, day_number: int = 1,
                          source: str = "sla_breach") -> Decimal:
    """Withdraw the penalty from the provider ONLY -- nothing reaches the customer.

    Allowed to take a balance negative: a provider already at zero would
    otherwise face no penalty at all, which removes the deterrent exactly where
    it is most needed. `cap` is how far into debt a provider may be driven, so
    repeated breaches cannot spiral into a balance they can never clear.
    """
    idem = f"{source}:{job_id}:day:{day_number}"
    existing = (await db.execute(text(
        "SELECT credit_delta FROM usage_credit_ledger "
        "WHERE tenant_id=:t AND idempotency_key=:k LIMIT 1"
    ), {"t": str(tenant_id), "k": idem})).first()
    if existing is not None:
        return abs(Decimal(str(existing.credit_delta or 0)))

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
        "  balance_before, balance_after, deduction_source, reason, idempotency_key, "
        "  source_type, source_id, reason_code, actor_role) "
        "VALUES (:t, :j, 'sla_breach_penalty', :d, :before, :after, :source, :r, :k, "
        "  'service_job', :source_id, 'sla_breach', 'system')"
    ), {"t": str(tenant_id), "j": str(job_id), "d": float(-charge),
        "before": float(balance), "after": float(after),
        "source": source, "source_id": str(job_id), "k": idem,
        "r": f"SLA breach day {day_number} penalty for job {job_id}"})
    return charge


async def _penalise_and_compensate(db: AsyncSession, *, tenant_id, customer_id,
                                   booking_id, job_id, amount: Decimal,
                                   day_number: int = 1,
                                   source: str = "sla_breach") -> Decimal:
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
        reference_type=("sla_final_close" if source == "sla_final_close"
                        else f"sla_breach_day_{day_number}"),
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
        "WHERE (reference_type LIKE 'sla_breach%' OR reference_type='sla_final_close') "
        "  AND reference_id = :j "
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


async def _reconcile_enforced_deadlines(db: AsyncSession, policy, *, limit: int) -> None:
    """Move enrolled open jobs from the legacy calendar-day clock to slot time.

    This deliberately touches only jobs already enrolled in enforcement.  It
    fixes existing breached rows without retroactively charging unrelated old
    test data.
    """
    rows = (await db.execute(text(
        "SELECT id, scheduled_date, scheduled_time_window, sla_penalty_day_count "
        "FROM service_jobs "
        "WHERE sla_enforcement_started_at IS NOT NULL AND sla_stopped_at IS NULL "
        "  AND arrival_verified_at IS NULL AND status = ANY(:statuses) "
        "ORDER BY scheduled_date NULLS LAST LIMIT :lim "
        "FOR UPDATE SKIP LOCKED"
    ), {"statuses": list(BREACHABLE_STATUSES), "lim": limit})).fetchall()
    close_hours = max(1, min(168, int(policy.sla_close_after_hours or 24)))
    for row in rows:
        first_due = compute_due_at(
            row.scheduled_date, row.scheduled_time_window, policy.sla_breach_hours)
        if first_due is None:
            continue
        next_due = (first_due if int(row.sla_penalty_day_count or 0) == 0
                    else first_due + dt.timedelta(hours=close_hours))
        await db.execute(text(
            "UPDATE service_jobs SET sla_due_at=:first_due, sla_next_penalty_at=:next_due, "
            "updated_at=now() WHERE id=:id"
        ), {"first_due": first_due, "next_due": next_due, "id": str(row.id)})


async def enforce_stalled_provider_stage(
    db: AsyncSession, *, job, entered_at: dt.datetime, stage_limit_minutes: int,
    now: dt.datetime | None = None,
) -> dict:
    """Charge and close a provider-owned stage that stopped progressing.

    The first deadline is the later of the promised slot deadline and the
    stage's own operational limit.  That prevents a long legitimate visit
    from being penalised before its booked window ends, while still ensuring
    that tapping "Reached site" cannot permanently escape the SLA.

    Each stage entry has its own idempotency key. Overlapping workers therefore
    cannot double-charge, and moving to the next stage immediately disarms the
    old entry because its timestamp no longer matches the watchdog candidate.
    """
    if job.status not in PROVIDER_PROGRESS_STATUSES:
        return {"eligible": False, "penalised": False, "closed": False}
    if await stage_waiting_on_customer(db, job):
        return {"eligible": False, "penalised": False, "closed": False,
                "waiting_on": "customer"}

    policy = await _policy(db)
    if policy is None or policy.sla_breach_hours is None:
        return {"eligible": False, "penalised": False, "closed": False}

    current = now or dt.datetime.now(dt.timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=dt.timezone.utc)
    if entered_at.tzinfo is None:
        entered_at = entered_at.replace(tzinfo=dt.timezone.utc)
    slot_due = compute_due_at(
        job.scheduled_date, job.scheduled_time_window, policy.sla_breach_hours,
    )
    if slot_due is None:
        return {"eligible": False, "penalised": False, "closed": False}
    first_due = max(
        slot_due,
        entered_at + dt.timedelta(minutes=max(1, int(stage_limit_minutes))),
    )
    if current < first_due:
        return {"eligible": True, "penalised": False, "closed": False,
                "first_due_at": first_due.isoformat()}

    token = f"{job.status}:{int(entered_at.timestamp())}"
    first_source = f"stage_sla:{token}"
    first_row = (await db.execute(text(
        "SELECT metadata->>'amount' AS amount FROM service_job_execution_events "
        "WHERE job_id=:job_id AND event_type='job_stage_sla_penalty' "
        "AND metadata->>'stage_entry_token'=:token LIMIT 1"
    ), {"job_id": str(job.id), "token": token})).first()

    enabled, override = await _job_type_override(
        db, policy_id=policy.id, job_type_id=job.job_type_id,
    )
    initial_amount = resolve_penalty(
        policy,
        job_value=(Decimal(str(job.job_value or 0)) or None),
        job_type_override=override,
    ) if enabled else Decimal("0")
    cap = (Decimal(str(policy.sla_penalty_debt_cap))
           if policy.sla_penalty_debt_cap is not None else None)
    penalised = False
    first_taken = abs(Decimal(str(first_row.amount or 0))) if first_row else Decimal("0")
    if first_row is None:
        first_taken = await _charge_penalty(
            db, tenant_id=job.tenant_id, job_id=job.id,
            amount=initial_amount, cap=cap, day_number=1, source=first_source,
        )
        penalised = first_taken > 0
        if first_taken > 0:
            await db.execute(text(
                "UPDATE service_jobs SET "
                "sla_breached_at=COALESCE(sla_breached_at, now()), "
                "sla_penalty_charged=COALESCE(sla_penalty_charged,0)+:amount, "
                "updated_at=now() WHERE id=:id"
            ), {"amount": first_taken, "id": str(job.id)})
            if policy.sla_notify_provider:
                await _notify_provider(db, job=job, amount=first_taken, cancelled=False)

        from app.engines.execution.models import ServiceJobExecutionEvent
        db.add(ServiceJobExecutionEvent(
            booking_id=job.booking_id, job_id=job.id, tenant_id=job.tenant_id,
            staff_member_id=job.assigned_staff_id,
            actor_role="platform", event_type="job_stage_sla_penalty",
            old_status=job.status, new_status=job.status,
            notes=(f"Provider-owned stage exceeded its deadline after the slot; "
                   f"Rs.{first_taken:,.2f} deducted."),
            event_metadata={
                "status": job.status, "entered_at": entered_at.isoformat(),
                "first_due_at": first_due.isoformat(), "amount": float(first_taken),
                "waiting_on": "provider", "stage_entry_token": token,
            },
            request_id="job:stage_sla",
        ))

    close_hours = max(1, min(168, int(policy.sla_close_after_hours or 24)))
    final_due = first_due + dt.timedelta(hours=close_hours)
    if current < final_due:
        if penalised:
            from app.engines.tenant_engine.health import refresh_provider_operational_health
            await refresh_provider_operational_health(db, job.tenant_id)
        return {"eligible": True, "penalised": penalised, "closed": False,
                "first_due_at": first_due.isoformat(), "final_due_at": final_due.isoformat()}

    final_source = f"stage_sla_final:{token}"
    final_exists = (await db.execute(text(
        "SELECT 1 FROM service_job_execution_events "
        "WHERE job_id=:job_id AND event_type='job_stage_sla_closed' "
        "AND metadata->>'stage_entry_token'=:token LIMIT 1"
    ), {"job_id": str(job.id), "token": token})).first()
    if final_exists is not None:
        return {"eligible": True, "penalised": penalised, "closed": False,
                "first_due_at": first_due.isoformat(), "final_due_at": final_due.isoformat()}

    top_up = final_penalty_top_up(
        charged_so_far=first_taken,
        total_penalty=Decimal(str(policy.sla_total_penalty_amount or 0)),
    ) if enabled else Decimal("0")
    final_taken = await _charge_penalty(
        db, tenant_id=job.tenant_id, job_id=job.id,
        amount=top_up, cap=cap, day_number=2, source=final_source,
    ) if top_up > 0 else Decimal("0")
    if final_taken > 0:
        await db.execute(text(
            "UPDATE service_jobs SET "
            "sla_penalty_charged=COALESCE(sla_penalty_charged,0)+:amount, "
            "updated_at=now() WHERE id=:id"
        ), {"amount": final_taken, "id": str(job.id)})
        if policy.sla_notify_provider:
            await _notify_provider(
                db, job=job, amount=final_taken,
                cancelled=bool(policy.sla_auto_cancel),
            )

    from app.engines.execution.models import ServiceJobExecutionEvent
    db.add(ServiceJobExecutionEvent(
        booking_id=job.booking_id, job_id=job.id, tenant_id=job.tenant_id,
        staff_member_id=job.assigned_staff_id,
        actor_role="platform", event_type="job_stage_sla_closed",
        old_status=job.status,
        new_status="cancelled" if policy.sla_auto_cancel else job.status,
        notes=(f"No provider action for {close_hours} hours after the stage SLA; "
               f"cumulative target Rs.{Decimal(str(policy.sla_total_penalty_amount or 0)):,.2f}."),
        event_metadata={
            "status": job.status, "entered_at": entered_at.isoformat(),
            "first_due_at": first_due.isoformat(), "final_due_at": final_due.isoformat(),
            "amount": float(final_taken), "waiting_on": "provider",
            "stage_entry_token": token,
        },
        request_id="job:stage_sla",
    ))
    closed = False
    if policy.sla_auto_cancel:
        await _close_breached_job(
            db, job_id=job.id, booking_id=job.booking_id,
            reason=(f"No technician or provider action for {close_hours} hours "
                    f"after the {job.status.replace('_', ' ')} deadline"),
        )
        await _notify_customer(
            db, job=job, compensated=False, amount=first_taken + final_taken,
        )
        closed = True
    if penalised or final_taken > 0 or closed:
        from app.engines.tenant_engine.health import refresh_provider_operational_health
        await refresh_provider_operational_health(db, job.tenant_id)
    return {"eligible": True, "penalised": penalised or final_taken > 0,
            "closed": closed, "first_due_at": first_due.isoformat(),
            "final_due_at": final_due.isoformat()}


async def sweep(db: AsyncSession, *, limit: int = 200) -> dict:
    """Apply the missed-slot charge, then close after the configured window.

    Rows are locked and each ledger movement has a day-specific idempotency
    key, so overlapping schedulers and retries cannot double-charge a day.
    """
    policy = await _policy(db)
    if policy is None:
        return {"breached": 0, "penalised": 0, "compensated": 0,
                "suspended": 0, "reinstated": 0, "cancelled_job_ids": [],
                "reason": "no_published_policy"}

    cap = Decimal(str(policy.sla_penalty_debt_cap)) if policy.sla_penalty_debt_cap is not None else None
    statuses = policy.sla_breachable_statuses or list(BREACHABLE_STATUSES)
    if not isinstance(statuses, list) or not statuses:
        statuses = list(BREACHABLE_STATUSES)
    # Arrival is the success condition for this SLA.  Never let a stale admin
    # policy include post-arrival statuses and charge a technician who arrived.
    statuses = [status for status in statuses if status in BREACHABLE_STATUSES]
    if not statuses:
        statuses = list(BREACHABLE_STATUSES)

    await _reconcile_enforced_deadlines(db, policy, limit=limit)

    due = (await db.execute(text(
        "SELECT j.id, j.tenant_id, j.booking_id, j.customer_id, j.status, j.job_type_id, "
        "       j.job_number, j.assigned_staff_id, "
        "       j.sla_penalty_day_count, COALESCE(j.sla_penalty_charged, 0) AS charged_so_far, "
        "       COALESCE((SELECT i.total_amount FROM service_invoices i "
        "                 WHERE i.job_id=j.id AND i.status<>'cancelled' "
        "                 ORDER BY i.created_at DESC LIMIT 1), 0) AS job_value "
        "FROM service_jobs j "
        "WHERE j.sla_enforcement_started_at IS NOT NULL AND j.sla_stopped_at IS NULL "
        "  AND j.sla_next_penalty_at IS NOT NULL AND j.sla_next_penalty_at <= now() "
        "  AND j.arrival_verified_at IS NULL AND j.status = ANY(:statuses) "
        "ORDER BY j.sla_next_penalty_at LIMIT :lim FOR UPDATE OF j SKIP LOCKED"
    ), {"statuses": statuses, "lim": limit})).fetchall()

    breached = penalised = compensated = 0
    affected_tenants: set = set()
    cancelled_job_ids: list[str] = []
    for job in due:
        previous_stage = int(job.sla_penalty_day_count or 0)
        final_day = previous_stage >= 1
        day_number = 2 if final_day else 1
        breached += 1

        enabled, override = await _job_type_override(
            db, policy_id=policy.id, job_type_id=job.job_type_id)
        initial_penalty = resolve_penalty(
            policy, job_value=Decimal(str(job.job_value or 0)) or None,
            job_type_override=override,
        ) if enabled else Decimal("0")
        penalty = (final_penalty_top_up(
            charged_so_far=Decimal(str(job.charged_so_far or 0)),
            total_penalty=Decimal(str(policy.sla_total_penalty_amount or 0)),
        ) if final_day and enabled else initial_penalty)
        penalty_source = "sla_final_close" if final_day else "sla_breach"

        taken = Decimal("0")
        if penalty > 0:
            if policy.sla_penalty_to_customer and job.customer_id is not None:
                try:
                    taken = await _penalise_and_compensate(
                        db, tenant_id=job.tenant_id, customer_id=job.customer_id,
                        booking_id=job.booking_id, job_id=job.id, amount=penalty,
                        day_number=day_number, source=penalty_source)
                    if taken > 0:
                        compensated += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning("sla_breach.compensation_failed",
                                   job_id=str(job.id), error=str(exc))
                    taken = await _charge_penalty(
                        db, tenant_id=job.tenant_id, job_id=job.id,
                        amount=penalty, cap=cap, day_number=day_number,
                        source=penalty_source)
            else:
                taken = await _charge_penalty(
                    db, tenant_id=job.tenant_id, job_id=job.id,
                    amount=penalty, cap=cap, day_number=day_number,
                    source=penalty_source)
            if taken > 0:
                penalised += 1
                affected_tenants.add(job.tenant_id)

        await db.execute(text(
            "UPDATE service_jobs SET sla_breached_at=COALESCE(sla_breached_at, now()), "
            "sla_penalty_day_count=:day, sla_penalty_charged=:charged, "
            "sla_next_penalty_at=CASE WHEN :final THEN NULL "
            "  ELSE sla_due_at + make_interval(hours => :close_hours) END, "
            "sla_stopped_at=CASE WHEN :final THEN now() ELSE sla_stopped_at END, "
            "updated_at=now() WHERE id=:id"
        ), {"day": day_number, "charged": Decimal(str(job.charged_so_far or 0)) + taken,
            "final": final_day,
            "close_hours": max(1, min(168, int(policy.sla_close_after_hours or 24))),
            "id": str(job.id)})

        if taken > 0 and policy.sla_notify_provider:
            await _notify_provider(db, job=job, amount=taken,
                                   cancelled=bool(final_day and policy.sla_auto_cancel))

        if not final_day:
            # The customer should not keep seeing "on the way" with no
            # explanation after the promised slot is missed. Delivery is
            # best-effort and exactly scoped to the booking's Instagram ID.
            from app.engines.messaging_gateway.booking_updates import send_stage_delay
            await send_stage_delay(
                db, job, stage=job.status, critical=True,
                waiting_on="provider",
            )

        if final_day:
            if policy.sla_auto_cancel:
                close_hours = max(1, min(168, int(policy.sla_close_after_hours or 24)))
                await _close_breached_job(
                    db, job_id=job.id, booking_id=job.booking_id,
                    reason=(f"Technician did not arrive within {close_hours} hours "
                            "of the booked slot"),
                )
                await _notify_customer(db, job=job, compensated=bool(
                    policy.sla_penalty_to_customer
                    and (Decimal(str(job.charged_so_far or 0)) + taken) > 0),
                    amount=Decimal(str(job.charged_so_far or 0)) + taken)
                cancelled_job_ids.append(str(job.id))
                affected_tenants.add(job.tenant_id)

        logger.info("sla_breach.actioned", job_id=str(job.id), tenant_id=str(job.tenant_id),
                    penalty_taken=float(taken), day_number=day_number, final_day=final_day,
                    compensated_customer=bool(policy.sla_penalty_to_customer and taken > 0))

    # Health is a live matching input.  Refresh it before evaluating the
    # suspension threshold so a new breach changes ranking/suspension in this
    # same transaction instead of waiting for an unrelated later refresh.
    if affected_tenants:
        from app.engines.tenant_engine.health import refresh_provider_operational_health
        for tenant_id in affected_tenants:
            await refresh_provider_operational_health(db, tenant_id)

    suspended = await _apply_health_suspensions(db, policy)
    reinstated = await reinstate_due(db, policy)
    return {"breached": breached, "penalised": penalised, "compensated": compensated,
            "suspended": suspended, "reinstated": reinstated,
            "cancelled_job_ids": cancelled_job_ids}


async def settle_no_arrival_close(db: AsyncSession, *, job_id) -> Decimal:
    """Settle a no-arrival cancellation exactly as this engine's close would.

    `travel_timeout` cancels a job whose technician set off and never arrived,
    without waiting for this engine's close window. A cancelled job is outside
    BREACHABLE_STATUSES, so without this the no-show would cost the provider
    nothing -- less than a provider who never tapped "On the way" at all.

    The provider cancellation path also calls this after a breach has already
    been recorded.  Otherwise a provider could cancel after the initial charge
    and avoid the remainder of the configured cumulative close penalty.

    Here the missed-slot charge and the final close collapse into one: the
    provider pays the larger of the two policy amounts, less anything already
    taken, under the same final-close idempotency key, and the clock stops so
    no later sweep can charge the job again. Returns the amount taken now.
    """
    policy = await _policy(db)
    if policy is None:
        return Decimal("0")
    job = (await db.execute(text(
        "SELECT j.id, j.tenant_id, j.booking_id, j.customer_id, j.job_type_id, "
        "       COALESCE(j.sla_penalty_charged, 0) AS charged_so_far, "
        "       COALESCE((SELECT i.total_amount FROM service_invoices i "
        "                 WHERE i.job_id=j.id AND i.status<>'cancelled' "
        "                 ORDER BY i.created_at DESC LIMIT 1), 0) AS job_value "
        "FROM service_jobs j WHERE j.id = :id"
    ), {"id": str(job_id)})).first()
    if job is None:
        return Decimal("0")

    charged = Decimal(str(job.charged_so_far or 0))
    taken = Decimal("0")
    enabled, override = await _job_type_override(
        db, policy_id=policy.id, job_type_id=job.job_type_id)
    if enabled:
        initial = resolve_penalty(
            policy, job_value=Decimal(str(job.job_value or 0)) or None,
            job_type_override=override,
        )
        target = max(initial, Decimal(str(policy.sla_total_penalty_amount or 0)))
        penalty = max(Decimal("0"), target - charged)
        if penalty > 0:
            cap = (Decimal(str(policy.sla_penalty_debt_cap))
                   if policy.sla_penalty_debt_cap is not None else None)
            if policy.sla_penalty_to_customer and job.customer_id is not None:
                try:
                    taken = await _penalise_and_compensate(
                        db, tenant_id=job.tenant_id, customer_id=job.customer_id,
                        booking_id=job.booking_id, job_id=job.id, amount=penalty,
                        day_number=2, source="sla_final_close")
                except Exception as exc:  # noqa: BLE001
                    logger.warning("sla_breach.compensation_failed",
                                   job_id=str(job.id), error=str(exc))
                    taken = await _charge_penalty(
                        db, tenant_id=job.tenant_id, job_id=job.id, amount=penalty,
                        cap=cap, day_number=2, source="sla_final_close")
            else:
                taken = await _charge_penalty(
                    db, tenant_id=job.tenant_id, job_id=job.id, amount=penalty,
                    cap=cap, day_number=2, source="sla_final_close")

    await db.execute(text(
        "UPDATE service_jobs SET sla_breached_at=COALESCE(sla_breached_at, now()), "
        "sla_penalty_day_count=2, sla_penalty_charged=:charged, "
        "sla_next_penalty_at=NULL, sla_stopped_at=now(), updated_at=now() WHERE id=:id"
    ), {"charged": charged + taken, "id": str(job.id)})
    if taken > 0 and policy.sla_notify_provider:
        await _notify_provider(db, job=job, amount=taken, cancelled=True)
    logger.info("sla_breach.no_arrival_settled", job_id=str(job.id),
                tenant_id=str(job.tenant_id), penalty_taken=float(taken))
    return taken


async def _close_breached_job(db: AsyncSession, *, job_id, booking_id,
                              reason: str = "Technician did not arrive within the SLA window") -> None:
    """Close job, booking and current assignment as one transaction."""
    await db.execute(text(
        "UPDATE service_jobs SET status='cancelled', assignment_status='cancelled', "
        "failure_reason=:reason, updated_at=now() WHERE id=:id"
    ), {"id": str(job_id), "reason": reason})
    await db.execute(text(
        "UPDATE service_bookings SET status='cancelled', assignment_status='cancelled', "
        "failure_reason=:reason, updated_at=now() WHERE id=:id"
    ), {"id": str(booking_id), "reason": reason})
    await db.execute(text(
        "UPDATE service_job_assignments SET is_current=false, assignment_status='cancelled', "
        "cancelled_at=now(), notes=:reason, updated_at=now() "
        "WHERE job_id=:id AND is_current=true"
    ), {"id": str(job_id), "reason": reason})


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
