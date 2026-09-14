"""Canonical missed-arrival SLA summary for ``service_jobs``.

The financial worker and every operational queue read the same slot-based
``sla_due_at``. A former creation-time calculation could label tomorrow's job
overdue today even though financial enforcement correctly waited for its slot.
"""
from __future__ import annotations
from datetime import datetime, timezone

from sqlalchemy import select, func, or_, and_, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_SLA_MINUTES = 60
AT_RISK_MINUTES = 60
TERMINAL_STATUSES = {
    "completed", "cancelled", "failed", "closed_estimate_declined",
    "force_closed", "voided",
}
ARRIVAL_SATISFIED_STATUSES = {
    "reached_site", "customer_not_available", "inspection_started",
    "inspection_done", "service_started", "in_progress", "work_done",
    "awaiting_estimate_approval", "awaiting_payment", "payment_pending",
}


def sla_filter_condition(job_model, status: str):
    """Build the same stamped-slot SLA rule as ``attach_sla``."""
    one_minute = literal_column("INTERVAL '1 minute'")
    deadline = job_model.sla_due_at
    risk_start = deadline - AT_RISK_MINUTES * one_minute
    open_job = and_(
        job_model.status.notin_(TERMINAL_STATUSES | ARRIVAL_SATISFIED_STATUSES),
        job_model.arrival_verified_at.is_(None),
        job_model.sla_stopped_at.is_(None),
        deadline.is_not(None),
    )
    normalized = status.upper()
    if normalized in {"ATTENTION", "NEEDS_ATTENTION"}:
        # Operational queues include work approaching its deadline and work
        # that has already crossed it.  Exposing the union as one predicate
        # keeps KPI counts and their drill-down results identical.
        return and_(open_job, func.now() >= risk_start)
    if normalized == "BREACHED":
        return and_(open_job, func.now() > deadline)
    if normalized == "AT_RISK":
        return and_(open_job, func.now() >= risk_start, func.now() <= deadline)
    if normalized == "ON_TRACK":
        return and_(open_job, func.now() < risk_start)
    raise ValueError("INVALID_SLA_STATUS")


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def resolve_sla_minutes_for_jobs(db: AsyncSession, jobs: list) -> dict[str, int]:
    """Returns {job_id_str: sla_minutes} for a batch of jobs -- at most 2
    queries total regardless of how many jobs are passed."""
    from app.engines.admin_catalog.models import PricingTier, TierLocation

    zipcodes = {j.zipcode for j in jobs if j.zipcode}
    cities = {j.city for j in jobs if j.city}
    if not zipcodes and not cities:
        return {str(j.id): DEFAULT_SLA_MINUTES for j in jobs}

    # Built as a list because a bare Python `False` cannot be the LEFT operand
    # of `|` against a SQLAlchemy expression — `False | <clause>` raises
    # TypeError, which meant every batch of jobs that had cities but no
    # zipcodes (zipcode is nullable) crashed this call with a 500. Collecting
    # the clauses that actually apply and OR-ing them keeps both one-sided
    # cases working.
    location_match = []
    if zipcodes:
        location_match.append(TierLocation.zipcode.in_(zipcodes))
    if cities:
        location_match.append(TierLocation.city.in_(cities))

    locs = (await db.execute(
        select(TierLocation).where(
            TierLocation.is_active.is_(True),
            or_(*location_match),
        )
    )).scalars().all()
    if not locs:
        return {str(j.id): DEFAULT_SLA_MINUTES for j in jobs}

    tier_ids = {loc.tier_id for loc in locs}
    tiers = (await db.execute(select(PricingTier).where(PricingTier.id.in_(tier_ids)))).scalars().all()
    tier_by_id = {t.id: t for t in tiers}

    by_zip = {loc.zipcode: tier_by_id.get(loc.tier_id) for loc in locs if loc.zipcode}
    by_city = {loc.city: tier_by_id.get(loc.tier_id) for loc in locs if loc.city}

    result: dict[str, int] = {}
    for j in jobs:
        tier = by_zip.get(j.zipcode) or by_city.get(j.city)
        result[str(j.id)] = tier.default_sla_minutes if tier else DEFAULT_SLA_MINUTES
    return result


def compute_sla(job, sla_minutes: int = DEFAULT_SLA_MINUTES) -> dict:
    """Project the missed-arrival deadline stamped from the booked slot.

    ``sla_minutes`` remains in the signature for older callers, but pricing
    tiers no longer decide whether a technician arrived on time.
    """
    source = "missed_arrival_slot"
    status = str(job.status or "").lower()
    if (status in TERMINAL_STATUSES | ARRIVAL_SATISFIED_STATUSES
            or getattr(job, "arrival_verified_at", None)
            or getattr(job, "sla_stopped_at", None)):
        return {"sla_status": "NOT_APPLICABLE", "next_deadline": None,
                "minutes_remaining": None, "minutes_overdue": None,
                "breach_stage": None, "source_policy": source}

    deadline = getattr(job, "sla_due_at", None)
    if deadline is None:
        from app.engines.weather.slots import slot_end
        deadline = slot_end(
            getattr(job, "scheduled_date", None),
            getattr(job, "scheduled_time_window", None),
        )
    if deadline is None:
        return {"sla_status": "NOT_APPLICABLE", "next_deadline": None,
                "minutes_remaining": None, "minutes_overdue": None,
                "breach_stage": None, "source_policy": None}
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    now = _now()
    delta_minutes = (deadline - now).total_seconds() / 60

    if delta_minutes < 0:
        return {"sla_status": "BREACHED", "next_deadline": deadline.isoformat(),
                "minutes_remaining": None, "minutes_overdue": round(-delta_minutes),
                "breach_stage": "OVERDUE", "source_policy": source}
    sla_status = "AT_RISK" if delta_minutes <= AT_RISK_MINUTES else "ON_TRACK"
    return {"sla_status": sla_status, "next_deadline": deadline.isoformat(),
            "minutes_remaining": round(delta_minutes), "minutes_overdue": None,
            "breach_stage": None, "source_policy": source}


async def attach_sla(db: AsyncSession, jobs: list) -> dict[str, dict]:
    """Returns {job_id_str: sla_dict} for a batch of jobs."""
    return {str(job.id): compute_sla(job) for job in jobs}


async def compute_summary(db: AsyncSession, *, tenant_id=None, status: str | None = None,
                           date_from: datetime | None = None, date_to: datetime | None = None) -> dict:
    """Real operational summary against service_jobs only -- no /v1/jobs
    dependency, reconciles with list-endpoint filter semantics."""
    from app.engines.final_records.models import ServiceJob

    filters = []
    if tenant_id: filters.append(ServiceJob.tenant_id == tenant_id)
    if status: filters.append(ServiceJob.status == status)
    if date_from: filters.append(ServiceJob.created_at >= date_from)
    if date_to: filters.append(ServiceJob.created_at <= date_to)

    q = select(ServiceJob.status, func.count(ServiceJob.id)).group_by(ServiceJob.status)
    for f in filters: q = q.where(f)
    rows = (await db.execute(q)).all()
    by_status = {status_val: count for status_val, count in rows}

    total = sum(by_status.values())
    unassigned = by_status.get("new", 0) + by_status.get("pending_assignment", 0)
    assigned = by_status.get("assigned", 0)
    in_progress = by_status.get("in_progress", 0)
    completed = by_status.get("completed", 0)
    force_closed = by_status.get("force_closed", 0)
    voided = by_status.get("voided", 0)

    # SLA breach/at-risk counts require per-job computation, but bounded to
    # non-terminal jobs only (not the whole table) to avoid loading everything.
    open_q = select(ServiceJob).where(ServiceJob.status.notin_(TERMINAL_STATUSES))
    for f in filters: open_q = open_q.where(f)
    open_jobs = (await db.execute(open_q.limit(2000))).scalars().all()
    sla_map = await attach_sla(db, open_jobs)
    at_risk = sum(1 for v in sla_map.values() if v["sla_status"] == "AT_RISK")
    breached = sum(1 for v in sla_map.values() if v["sla_status"] == "BREACHED")

    return {
        "total": total, "unassigned": unassigned, "assigned": assigned,
        "in_progress": in_progress, "completed": completed,
        "force_closed": force_closed, "voided": voided,
        "at_risk": at_risk, "breached": breached,
        "delayed": breached,  # alias per mission's "Delayed" terminology
        "completion_exceptions": force_closed + voided,
    }
