"""FINAL-L5-05E — Canonical SLA + operational summary for service_jobs.

SLA input inventory (grounded in real, existing config, not invented):
  AVAILABLE / CONFIGURED: PricingTier.default_sla_minutes, resolved per job
    via TierLocation (zipcode overrides city) -- this is a real, admin-
    editable SLA source already used elsewhere in pricing.
  MISSING: service_jobs has no explicit deadline column; MasterWorkflowTemplate
    .max_sla_hours exists but isn't reliably joinable to a specific job
    without a service/category resolution chain not built here -- documented
    limitation, not used.
  DERIVED: sla deadline = job.created_at + resolved_sla_minutes.

Batch-resolves SLA for a page of jobs with a fixed, small number of queries
(no per-row query), per the mission's explicit N+1 requirement.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, func, or_, and_, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_SLA_MINUTES = 60
TERMINAL_STATUSES = {
    "completed", "cancelled", "failed", "closed_estimate_declined",
    "force_closed", "voided",
}


def sla_filter_condition(job_model, status: str):
    """Build the same SLA rule as ``attach_sla`` as a SQL predicate.

    This lets list/count queries apply SLA before pagination. Postcode tier
    wins, then city tier, then the documented 60 minute default.
    """
    from app.engines.admin_catalog.models import PricingTier, TierLocation

    zip_minutes = (
        select(PricingTier.default_sla_minutes)
        .join(TierLocation, TierLocation.tier_id == PricingTier.id)
        .where(
            TierLocation.is_active.is_(True), PricingTier.is_active.is_(True),
            TierLocation.zipcode == job_model.zipcode,
        )
        .order_by(TierLocation.priority.asc()).limit(1)
        .correlate(job_model).scalar_subquery()
    )
    city_minutes = (
        select(PricingTier.default_sla_minutes)
        .join(TierLocation, TierLocation.tier_id == PricingTier.id)
        .where(
            TierLocation.is_active.is_(True), PricingTier.is_active.is_(True),
            TierLocation.city == job_model.city,
        )
        .order_by(TierLocation.priority.asc()).limit(1)
        .correlate(job_model).scalar_subquery()
    )
    minutes = func.coalesce(zip_minutes, city_minutes, DEFAULT_SLA_MINUTES)
    one_minute = literal_column("INTERVAL '1 minute'")
    deadline = job_model.created_at + minutes * one_minute
    risk_start = job_model.created_at + (minutes * 0.8) * one_minute
    open_job = job_model.status.notin_(TERMINAL_STATUSES)
    normalized = status.upper()
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


def compute_sla(job, sla_minutes: int) -> dict:
    if job.status in TERMINAL_STATUSES:
        return {"sla_status": "NOT_APPLICABLE", "next_deadline": None,
                "minutes_remaining": None, "minutes_overdue": None,
                "breach_stage": None, "source_policy": f"tier_default_{sla_minutes}min"}

    created = job.created_at
    if created is None:
        return {"sla_status": "NOT_APPLICABLE", "next_deadline": None,
                "minutes_remaining": None, "minutes_overdue": None,
                "breach_stage": None, "source_policy": None}
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)

    deadline = created + timedelta(minutes=sla_minutes)
    now = _now()
    delta_minutes = (deadline - now).total_seconds() / 60

    if delta_minutes < 0:
        return {"sla_status": "BREACHED", "next_deadline": deadline.isoformat(),
                "minutes_remaining": None, "minutes_overdue": round(-delta_minutes),
                "breach_stage": "OVERDUE", "source_policy": f"tier_default_{sla_minutes}min"}
    at_risk_threshold = sla_minutes * 0.2
    status = "AT_RISK" if delta_minutes <= at_risk_threshold else "ON_TRACK"
    return {"sla_status": status, "next_deadline": deadline.isoformat(),
            "minutes_remaining": round(delta_minutes), "minutes_overdue": None,
            "breach_stage": None, "source_policy": f"tier_default_{sla_minutes}min"}


async def attach_sla(db: AsyncSession, jobs: list) -> dict[str, dict]:
    """Returns {job_id_str: sla_dict} for a batch of jobs."""
    minutes_by_job = await resolve_sla_minutes_for_jobs(db, jobs)
    return {str(j.id): compute_sla(j, minutes_by_job[str(j.id)]) for j in jobs}


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
