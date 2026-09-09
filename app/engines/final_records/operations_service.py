"""HOME-SERVICES-OPERATIONS: Unified Bookings & Jobs workspace — read
projection only. Canonical pipeline exclusively:

    home_service_booking_drafts -> service_bookings -> service_jobs
                                                      -> service_job_quotes

Deliberately excludes the legacy `bookings`/`field_ops.jobs` pipeline (the
existing /admin/bookings page) — confirmed via audit to be a disconnected,
non-canonical pipeline with no FK relationship to service_bookings/
service_jobs. Merging it here would violate the "no disconnected generic
bookings" / "no legacy Field Ops jobs" rules. That legacy page is untouched.

Dedup rule (no second status machine, no duplicate rows):
  - A confirmed HomeServiceBookingDraft always gets a ServiceBooking +
    ServiceJob created together, atomically, in the same transaction
    (FinalCreationService.finalize) — there is no real-world window in this
    codebase where a ServiceBooking exists without its ServiceJob. So:
      * work_type=JOB rows  = every ServiceJob (each already has exactly one
        parent ServiceBooking via the non-nullable booking_id FK).
      * work_type=REQUEST rows = HomeServiceBookingDraft rows still in a
        non-terminal, pre-confirmation status. The instant a draft is
        confirmed it disappears from this set and its ServiceJob appears —
        never both at once, by construction (idempotency lock in
        FinalCreationService prevents double-conversion).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Numeric, String, and_, case, cast, false as sa_false, func, literal, or_, select, union_all
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.final_records.models import ServiceBooking, ServiceJob
from app.engines.final_records.sla_summary import attach_sla, DEFAULT_SLA_MINUTES
from app.engines.home_service_booking.models import HomeServiceBookingDraft
from app.engines.quote_checklist.models import ServiceJobQuote

# ── Draft (pre-confirmation) statuses shown as work — matches
#    home_service_booking/constants.py exactly, nothing invented. ───────────
DRAFT_ACTIVE_STATUSES = {
    "draft", "collecting_details", "serviceability_checked",
    "price_estimated", "provider_matched", "ready_for_confirmation",
}
# Only customer-reviewed, booking-ready intent is an operational request.
# Earlier lifecycle states are private resume data for the customer/chatbot;
# exposing them made a postcode check or abandoned conversation look like a
# real unconfirmed booking to administrators.
DRAFT_OPERATIONAL_REQUEST_STATUSES = {"ready_for_confirmation"}
DRAFT_MATCHING_STATUSES = {"provider_matched"}
# Terminal-but-unsuccessful drafts surfaced as Exceptions rather than
# silently vanishing — an admin should still see a request that failed
# before ever becoming a booking. "confirmed" drafts are never shown here;
# their ServiceJob is the operational record from that point on.
DRAFT_EXCEPTION_STATUSES = {"failed", "expired"}

# ── ServiceJob.status -> UI stage, grounded in app/engines/execution/constants.py
#    (JS_* / JOB_TRANSITIONS) — the ONLY real canonical status vocabulary
#    found for service_jobs. No second status machine: this is a read-only
#    projection, the source column is untouched. ────────────────────────────
JOB_STAGE_MAP: dict[str, str] = {
    "pending_assignment":        "UNASSIGNED",
    "assigned":                  "ASSIGNED",
    "accepted":                  "ASSIGNED",
    "scheduled":                 "SCHEDULED",
    "on_the_way":                "ON_THE_WAY",
    "reached_site":              "ON_THE_WAY",
    "inspection_started":        "INSPECTION",
    "inspection_done":           "AWAITING_ESTIMATE",
    "quote_required":            "AWAITING_ESTIMATE",
    "service_started":           "IN_PROGRESS",
    "work_done":                 "WORK_DONE",
    "customer_not_available":    "AT_RISK",
    "cancelled":                 "CLOSED",
    "failed":                    "CLOSED",
    "closed_estimate_declined":  "CLOSED",
    "completed":                 "COMPLETED",
    "force_closed":              "CLOSED",
    "voided":                    "CLOSED",
}
# Stages that represent genuinely finished work (spec §7: closed_estimate_declined is NOT completed)
COMPLETED_STAGES = {"COMPLETED"}
# Canonical quote statuses that mean "sent, waiting on the customer" —
# matches app/engines/quote_checklist/constants.py exactly.
QUOTE_AWAITING_APPROVAL_STATUSES = {"sent_to_customer", "revision_requested"}

# ── Stage -> source statuses (the inverse of JOB_STAGE_MAP) ─────────────────
# A UI stage is a pure function of `service_jobs.status` (plus, for one stage,
# the current quote), so any stage filter can be expressed as a plain
# `status IN (...)` predicate. That matters enormously: `CASE ... END = 'X'` is
# not sargable, so filtering on the CASE forces a sequential scan of the whole
# table, while `status IN (...)` uses ix_sj_ops_status_created_id. Measured at
# 200k jobs: seq scan ~900ms vs bitmap index scan ~10ms, and the gap widens
# linearly with table size.
#
# The CASE is still applied on top — it is what distinguishes AWAITING_ESTIMATE
# from AWAITING_APPROVAL — but only after the index has narrowed the scan.
STAGE_TO_JOB_STATUSES: dict[str, set[str]] = {}
for _status, _stage in JOB_STAGE_MAP.items():
    STAGE_TO_JOB_STATUSES.setdefault(_stage, set()).add(_status)
# AWAITING_APPROVAL has no status of its own: it is a reclassification of the
# two statuses that otherwise mean AWAITING_ESTIMATE, decided by the quote.
STAGE_TO_JOB_STATUSES["AWAITING_APPROVAL"] = {"inspection_done", "quote_required"}
_MAPPED_JOB_STATUSES = frozenset(JOB_STAGE_MAP)


def job_status_prefilter(stages: set[str]) -> tuple[bool, frozenset[str]]:
    """An indexable status predicate for a set of UI stages.

    Returns (positive, statuses):
      * (True, S)  -> `status IN S` selects a superset of the wanted rows.
      * (False, S) -> `status NOT IN S` does, which is what UNKNOWN requires:
        UNKNOWN means "a status this projection has never heard of", so it can
        only be expressed by excluding the ones it has.
    Either way the CASE still runs afterwards, so the result stays exact — this
    only stops the database reading rows that cannot possibly qualify.
    """
    if "UNKNOWN" in stages:
        excluded: set[str] = set()
        for stage, statuses in STAGE_TO_JOB_STATUSES.items():
            if stage not in stages:
                excluded |= statuses
        # A status that also feeds a wanted stage must not be excluded.
        for stage in stages:
            excluded -= STAGE_TO_JOB_STATUSES.get(stage, set())
        return False, frozenset(excluded)
    wanted: set[str] = set()
    for stage in stages:
        wanted |= STAGE_TO_JOB_STATUSES.get(stage, set())
    return True, frozenset(wanted)


# Drafts are already constrained to the active/exception status sets by the
# base filter, so a draft stage always maps to a positive status set.
STAGE_TO_DRAFT_STATUSES: dict[str, set[str]] = {
    "REQUEST": set(DRAFT_ACTIVE_STATUSES),
    "MATCHING": set(DRAFT_MATCHING_STATUSES),
    # A matched-but-stale draft is reclassified AT_RISK, so provider_matched
    # can reach this stage too.
    "AT_RISK": set(DRAFT_EXCEPTION_STATUSES) | set(DRAFT_MATCHING_STATUSES),
}


def draft_status_prefilter(stages: set[str]) -> frozenset[str] | None:
    """`None` means "cannot narrow" (an UNKNOWN draft status is possible)."""
    if "UNKNOWN" in stages:
        return None
    wanted: set[str] = set()
    for stage in stages:
        wanted |= STAGE_TO_DRAFT_STATUSES.get(stage, set())
    return frozenset(wanted)


STAGE_TO_TAB = {
    # Requests
    "REQUEST": "requests", "MATCHING": "requests",
    # Active jobs (assigned through in-progress, excludes completed/terminal)
    "UNASSIGNED": "active", "ASSIGNED": "active", "SCHEDULED": "active",
    "ON_THE_WAY": "active", "INSPECTION": "active", "AWAITING_ESTIMATE": "active",
    "AWAITING_APPROVAL": "active", "READY_TO_START": "active", "IN_PROGRESS": "active",
    "WORK_DONE": "active",
    "COMPLETED": "completed",
    "AT_RISK": "exceptions", "CLOSED": "exceptions",
    "UNKNOWN": "exceptions",
}


# List-total cache window. `fresh` is deliberately LONGER than the key's TTL so
# that any value still in Redis is always inside the fresh window: that makes the
# stale-while-revalidate branch unreachable for counts, which matters because a
# count closure captures the request's database session and must never be re-run
# in the background after that request — and after that session has closed.
# The summary has no such constraint; it opens its own session and does refresh
# in the background.
_COUNT_TTL_SECONDS = 30
_COUNT_FRESH_SECONDS = 45


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _mask_phone(phone: str | None) -> str | None:
    """Restricted customer contact visibility (spec §20/§5): last 4 digits only."""
    if not phone or len(phone) < 4:
        return None
    return f"•••• {phone[-4:]}"


def map_job_stage(status: str, current_quote_status: str | None) -> tuple[str, bool]:
    """Returns (stage, is_unknown). A quote sent to the customer overrides
    AWAITING_ESTIMATE -> AWAITING_APPROVAL regardless of raw job status,
    since the estimate-approval gate (Phase 2A) is the operationally
    meaningful signal, not the job's own status string."""
    if status not in JOB_STAGE_MAP:
        return "UNKNOWN", True
    stage = JOB_STAGE_MAP[status]
    if stage == "AWAITING_ESTIMATE" and current_quote_status in QUOTE_AWAITING_APPROVAL_STATUSES:
        return "AWAITING_APPROVAL", False
    return stage, False


def map_draft_stage(status: str) -> tuple[str, bool]:
    if status in DRAFT_MATCHING_STATUSES:
        return "MATCHING", False
    if status in DRAFT_ACTIVE_STATUSES:
        return "REQUEST", False
    if status in DRAFT_EXCEPTION_STATUSES:
        return "AT_RISK", False
    return "UNKNOWN", True


async def _batch_lookup(db: AsyncSession, model, ids: set[uuid.UUID]) -> dict[uuid.UUID, Any]:
    if not ids:
        return {}
    rows = (await db.execute(select(model).where(model.id.in_(ids)))).scalars().all()
    return {r.id: r for r in rows}


def _amount_summary(booking: ServiceBooking | None, quote: ServiceJobQuote | None) -> dict:
    """Trusted backend-computed summary only — never an admin catalog price
    (non-negotiable rule). Prefers the current approved-or-pending quote
    total; falls back to the booking's price_snapshot (provider/tenant-set,
    captured at confirmation)."""
    if quote is not None:
        return {
            "source": "quote", "quote_status": quote.status, "version": quote.version_number,
            "total_amount": str(quote.total_amount), "currency": quote.currency,
        }
    snap = (booking.price_snapshot or {}) if booking else {}
    if snap:
        return {"source": "booking_price_snapshot", **{k: snap[k] for k in
                ("visit_fee", "min_price", "max_price", "estimated_total") if k in snap}}
    return {"source": "none"}


async def list_operations(
    db: AsyncSession, *,
    view: str = "confirmed",
    search: str | None = None,
    tenant_id: uuid.UUID | None = None,
    technician_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    stage: str | None = None,
    assignment: str | None = None,
    city: str | None = None,
    state: str | None = None,
    district: str | None = None,
    zipcode: str | None = None,
    amount_min: Decimal | None = None,
    amount_max: Decimal | None = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 25,
) -> dict:
    """Single server-side paginated read projection. Jobs and eligible
    drafts are queried, stage-mapped, and merged in Python only for the
    current page's worth of rows (bounded), never the full table — the
    UNION-like merge happens via two small ORDER BY created_at DESC queries
    limited to page window candidates, not a full in-browser merge."""
    # Jobs: paginate/filter/sort in SQL directly (server-side, bounded).
    job_filters = []
    if tenant_id: job_filters.append(ServiceJob.tenant_id == tenant_id)
    if technician_id: job_filters.append(ServiceJob.assigned_staff_id == technician_id)
    if customer_id: job_filters.append(ServiceJob.customer_id == customer_id)
    if city: job_filters.append(func.lower(ServiceJob.city) == city.strip().lower())
    if state: job_filters.append(func.lower(ServiceJob.address_snapshot["state"].astext) == state.strip().lower())
    if district: job_filters.append(func.lower(ServiceJob.address_snapshot["district"].astext) == district.strip().lower())
    if zipcode: job_filters.append(ServiceJob.zipcode == zipcode.strip())
    if date_from: job_filters.append(ServiceJob.created_at >= date_from)
    if date_to: job_filters.append(ServiceJob.created_at <= date_to)
    if assignment == "unassigned": job_filters.append(ServiceJob.assignment_status == "unassigned")
    elif assignment == "assigned": job_filters.append(ServiceJob.assignment_status.in_(["assigned", "accepted"]))

    draft_filters = [HomeServiceBookingDraft.status.in_(DRAFT_ACTIVE_STATUSES | DRAFT_EXCEPTION_STATUSES)]
    if view == "requests":
        draft_filters.extend([
            HomeServiceBookingDraft.status.in_(DRAFT_OPERATIONAL_REQUEST_STATUSES),
            HomeServiceBookingDraft.serviceability_status == "serviceable",
            HomeServiceBookingDraft.selected_tenant_id.isnot(None),
            HomeServiceBookingDraft.zipcode.isnot(None),
        ])
    if customer_id: draft_filters.append(HomeServiceBookingDraft.customer_id == customer_id)
    if city: draft_filters.append(func.lower(HomeServiceBookingDraft.city) == city.strip().lower())
    if state: draft_filters.append(func.lower(HomeServiceBookingDraft.address_snapshot["state"].astext) == state.strip().lower())
    if district: draft_filters.append(func.lower(HomeServiceBookingDraft.address_snapshot["district"].astext) == district.strip().lower())
    if zipcode: draft_filters.append(HomeServiceBookingDraft.zipcode == zipcode.strip())
    if date_from: draft_filters.append(HomeServiceBookingDraft.created_at >= date_from)
    if date_to: draft_filters.append(HomeServiceBookingDraft.created_at <= date_to)
    if tenant_id: draft_filters.append(HomeServiceBookingDraft.selected_tenant_id == tenant_id)
    # Drafts have no technician/assignment concept yet -- excluded by those filters.
    if assignment == "unassigned":
        draft_filters.append(HomeServiceBookingDraft.selected_tenant_id.is_(None))
    if technician_id or assignment == "assigned":
        draft_filters.append(sa_false())  # short-circuits to zero rows, not silently ignored

    jobs = []
    drafts = []

    # Batch lookups — bounded, no N+1 (mirrors sla_summary.py's pattern).
    from app.engines.tenant_engine.models import Tenant
    from app.engines.auth.models import User
    from app.engines.admin_catalog.models import MasterService, JobTypeDefinition

    current_quote_status = (
        select(ServiceJobQuote.status)
        .where(ServiceJobQuote.job_id == ServiceJob.id, ServiceJobQuote.is_current.is_(True))
        .order_by(ServiceJobQuote.version_number.desc()).limit(1)
        .correlate(ServiceJob).scalar_subquery()
    )
    current_quote_total = (
        select(ServiceJobQuote.total_amount)
        .where(ServiceJobQuote.job_id == ServiceJob.id, ServiceJobQuote.is_current.is_(True))
        .order_by(ServiceJobQuote.version_number.desc()).limit(1)
        .correlate(ServiceJob).scalar_subquery()
    )
    booking_amount = func.coalesce(
        current_quote_total,
        cast(ServiceBooking.price_snapshot["customer_total"].astext, Numeric),
        cast(ServiceBooking.price_snapshot["estimated_total"].astext, Numeric),
        cast(ServiceBooking.price_snapshot["standard_price"].astext, Numeric),
        cast(ServiceBooking.price_snapshot["visit_fee"].astext, Numeric),
    )
    draft_amount = func.coalesce(
        cast(HomeServiceBookingDraft.price_snapshot["customer_total"].astext, Numeric),
        cast(HomeServiceBookingDraft.price_snapshot["estimated_total"].astext, Numeric),
        cast(HomeServiceBookingDraft.price_snapshot["standard_price"].astext, Numeric),
        cast(HomeServiceBookingDraft.price_snapshot["visit_fee"].astext, Numeric),
    )
    if amount_min is not None:
        job_filters.append(booking_amount >= amount_min)
        draft_filters.append(draft_amount >= amount_min)
    if amount_max is not None:
        job_filters.append(booking_amount <= amount_max)
        draft_filters.append(draft_amount <= amount_max)
    job_stage = case(
        (and_(ServiceJob.status.in_(["inspection_done", "quote_required"]),
              current_quote_status.in_(QUOTE_AWAITING_APPROVAL_STATUSES)),
         literal("AWAITING_APPROVAL")),
        *[(ServiceJob.status == status, literal(mapped)) for status, mapped in JOB_STAGE_MAP.items()],
        else_=literal("UNKNOWN"),
    )
    delayed_match_cutoff = _now() - timedelta(minutes=DEFAULT_SLA_MINUTES * 0.25)
    draft_stage = case(
        (and_(HomeServiceBookingDraft.status == "provider_matched",
              HomeServiceBookingDraft.created_at < delayed_match_cutoff), literal("AT_RISK")),
        (HomeServiceBookingDraft.status == "provider_matched", literal("MATCHING")),
        (HomeServiceBookingDraft.status.in_(DRAFT_ACTIVE_STATUSES), literal("REQUEST")),
        (HomeServiceBookingDraft.status.in_(DRAFT_EXCEPTION_STATUSES), literal("AT_RISK")),
        else_=literal("UNKNOWN"),
    )

    # Stage/view filters are applied as an indexable `status IN (...)` prefilter
    # AND the exact CASE. The prefilter is what the planner can use; the CASE is
    # what keeps the answer exact. Applying only the CASE (as this did) meant
    # every stage-filtered view sequentially scanned service_jobs.
    def _narrow(stages: set[str]) -> None:
        positive, statuses = job_status_prefilter(stages)
        if positive:
            job_filters.append(ServiceJob.status.in_(statuses) if statuses else sa_false())
        elif statuses:
            job_filters.append(ServiceJob.status.notin_(statuses))
        draft_statuses = draft_status_prefilter(stages)
        if draft_statuses is not None:
            draft_filters.append(
                HomeServiceBookingDraft.status.in_(draft_statuses) if draft_statuses else sa_false())

    if stage:
        _narrow({stage})
        job_filters.append(job_stage == stage)
        draft_filters.append(draft_stage == stage)
    elif view == "confirmed":
        # A booking only exists after FinalCreationService has atomically
        # created its ServiceBooking + ServiceJob.  Pre-confirmation chat/app
        # drafts are useful in the explicit Requests view, but must not leak
        # into the default Bookings & Jobs feed and look like real work.
        draft_filters.append(sa_false())
    elif view != "all":
        view_stages = {
            "requests": {"REQUEST", "MATCHING"},
            "active": {key for key, tab in STAGE_TO_TAB.items() if tab == "active"},
            "approval": {"AWAITING_APPROVAL"},
            "exceptions": {"AT_RISK", "CLOSED", "UNKNOWN"},
            "completed": {"COMPLETED"},
        }.get(view)
        if view_stages is not None:
            _narrow(view_stages)
            job_filters.append(job_stage.in_(view_stages))
            draft_filters.append(draft_stage.in_(view_stages))
            if view == "exceptions":
                # Failed/expired pre-confirmation attempts are not job
                # exceptions. They remain historical draft data and must not
                # make this operational tab look like confirmed work failed.
                draft_filters.append(sa_false())

    job_candidates = (
        select(literal("JOB").label("work_type"), ServiceJob.id.label("record_id"),
               ServiceJob.created_at.label("created_at"),
               ServiceJob.updated_at.label("updated_at"),
               cast(ServiceJob.scheduled_date, DateTime).label("scheduled_date"),
               booking_amount.label("amount"))
        .outerjoin(ServiceBooking, ServiceBooking.id == ServiceJob.booking_id)
        .where(*job_filters)
    )
    draft_candidates = (
        select(literal("REQUEST").label("work_type"), HomeServiceBookingDraft.id.label("record_id"),
               HomeServiceBookingDraft.created_at.label("created_at"),
               HomeServiceBookingDraft.updated_at.label("updated_at"),
               cast(HomeServiceBookingDraft.preferred_date, DateTime).label("scheduled_date"),
               draft_amount.label("amount"))
        .where(*draft_filters)
    )
    if search:
        job_customer = aliased(User)
        job_tenant = aliased(Tenant)
        draft_customer = aliased(User)
        draft_tenant = aliased(Tenant)
        pattern = f"%{search.strip().lower()}%"
        job_candidates = (
            job_candidates
            .outerjoin(job_customer, job_customer.id == ServiceJob.customer_id)
            .outerjoin(job_tenant, job_tenant.id == ServiceJob.tenant_id)
            .where(or_(
            func.lower(ServiceJob.job_number).like(pattern), func.lower(ServiceBooking.booking_number).like(pattern),
            func.lower(job_customer.full_name).like(pattern), func.lower(job_tenant.business_name).like(pattern),
            ))
        )
        request_number = func.concat(
            "REQ-", func.upper(func.substr(cast(HomeServiceBookingDraft.id, String), 1, 8)))
        draft_candidates = (
            draft_candidates
            .outerjoin(draft_customer, draft_customer.id == HomeServiceBookingDraft.customer_id)
            .outerjoin(draft_tenant, draft_tenant.id == HomeServiceBookingDraft.selected_tenant_id)
            .where(or_(
            func.lower(request_number).like(pattern), func.lower(HomeServiceBookingDraft.customer_name).like(pattern),
            func.lower(draft_customer.full_name).like(pattern), func.lower(draft_tenant.business_name).like(pattern),
            ))
        )

    candidates = union_all(job_candidates, draft_candidates).subquery()

    # `total` exists only to render "1–25 of N" and the page count, but costs a
    # full count over the filtered union — on the default unfiltered view that
    # is every job in the system, paid again on every page-turn even though the
    # number cannot have changed meaningfully between clicks. Cached briefly and
    # keyed by the exact filter combination; the page window below is always
    # read live, so rows are never stale, only the total is.
    from app.engines.final_records.operations_cache import count_key, get_or_compute

    async def _count() -> int:
        return int(await db.scalar(select(func.count()).select_from(candidates)) or 0)

    total, _freshness, _at = await get_or_compute(
        count_key({"view": view, "search": search, "stage": stage, "assignment": assignment,
                   "tenant_id": tenant_id, "technician_id": technician_id,
                   "customer_id": customer_id, "city": city, "state": state,
                   "district": district, "zipcode": zipcode,
                   "amount_min": amount_min, "amount_max": amount_max,
                   "date_from": date_from, "date_to": date_to}),
        _count, fresh_seconds=_COUNT_FRESH_SECONDS, ttl_seconds=_COUNT_TTL_SECONDS,
    )
    total = int(total or 0)
    sort_columns = {
        "created_at": candidates.c.created_at,
        "updated_at": candidates.c.updated_at,
        "scheduled_date": candidates.c.scheduled_date,
        "amount": candidates.c.amount,
    }
    sort_column = sort_columns.get(sort_by, candidates.c.created_at)
    sort_expression = sort_column.asc().nulls_last() if sort_dir == "asc" else sort_column.desc().nulls_last()
    selected = (await db.execute(
        select(candidates.c.work_type, candidates.c.record_id, candidates.c.created_at)
        .order_by(sort_expression, candidates.c.record_id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).all()
    selected_job_ids = [row.record_id for row in selected if row.work_type == "JOB"]
    selected_draft_ids = [row.record_id for row in selected if row.work_type == "REQUEST"]
    jobs = (await db.execute(select(ServiceJob).where(ServiceJob.id.in_(selected_job_ids)))).scalars().all() if selected_job_ids else []
    drafts = (await db.execute(select(HomeServiceBookingDraft).where(HomeServiceBookingDraft.id.in_(selected_draft_ids)))).scalars().all() if selected_draft_ids else []

    booking_ids = {j.booking_id for j in jobs}
    bookings_by_id = await _batch_lookup(db, ServiceBooking, booking_ids)

    current_quotes = (await db.execute(
        select(ServiceJobQuote).where(ServiceJobQuote.job_id.in_([j.id for j in jobs]),
                                      ServiceJobQuote.is_current == True)  # noqa: E712
    )).scalars().all() if jobs else []
    quote_by_job = {q.job_id: q for q in current_quotes}

    tenant_ids = {j.tenant_id for j in jobs if j.tenant_id} | {d.selected_tenant_id for d in drafts if d.selected_tenant_id}
    tenants_by_id = await _batch_lookup(db, Tenant, tenant_ids)

    user_ids = ({j.customer_id for j in jobs if j.customer_id} | {j.assigned_staff_id for j in jobs if j.assigned_staff_id}
                | {d.customer_id for d in drafts if d.customer_id})
    users_by_id = await _batch_lookup(db, User, user_ids)

    offering_ids = {j.offering_id for j in jobs} | {d.offering_id for d in drafts}
    services_by_id = await _batch_lookup(db, MasterService, offering_ids)

    job_type_ids = {j.job_type_id for j in jobs if j.job_type_id} | {d.job_type_id for d in drafts if d.job_type_id}
    job_types_by_id = await _batch_lookup(db, JobTypeDefinition, job_type_ids)

    sla_map = await attach_sla(db, jobs)

    unknown_statuses: set[str] = set()
    rows: list[dict] = []

    for j in jobs:
        quote = quote_by_job.get(j.id)
        current_stage, is_unknown = map_job_stage(j.status, quote.status if quote else None)
        if is_unknown:
            unknown_statuses.add(f"service_jobs.status={j.status}")
        booking = bookings_by_id.get(j.booking_id)
        customer = users_by_id.get(j.customer_id) if j.customer_id else None
        technician = users_by_id.get(j.assigned_staff_id) if j.assigned_staff_id else None
        tenant = tenants_by_id.get(j.tenant_id) if j.tenant_id else None
        service = services_by_id.get(j.offering_id)
        job_type = job_types_by_id.get(j.job_type_id) if j.job_type_id else None
        sla = sla_map.get(str(j.id)) or {}

        rows.append({
            "work_id": j.job_number, "work_type": "JOB",
            "draft_id": str(booking.draft_id) if booking and booking.draft_id else None,
            "booking_id": str(j.booking_id), "job_id": str(j.id),
            "booking_number": booking.booking_number if booking else None,
            "customer_id": str(j.customer_id) if j.customer_id else None,
            "customer_name": customer.full_name if customer else (booking.customer_name if booking else None),
            "customer_contact_summary": _mask_phone(customer.phone if customer else (booking.customer_phone if booking else None)),
            "master_service": service.service_name if service else None,
            "job_type": job_type.label if job_type else None,
            "tenant_id": str(j.tenant_id) if j.tenant_id else None,
            "tenant_name": tenant.business_name if tenant else None,
            "technician_id": str(j.assigned_staff_id) if j.assigned_staff_id else None,
            "technician_name": technician.full_name if technician else None,
            "current_stage": current_stage, "canonical_status": j.status,
            "assignment_status": j.assignment_status,
            "schedule": {"date": j.scheduled_date.isoformat() if j.scheduled_date else None,
                         "window": j.scheduled_time_window},
            "sla_state": sla.get("sla_status", "NOT_APPLICABLE"), "sla_deadline": sla.get("next_deadline"),
            "amount_summary": _amount_summary(booking, quote),
            "location_summary": f"{j.city or '—'}" + (f" · {j.zipcode}" if j.zipcode else ""),
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "updated_at": j.updated_at.isoformat() if j.updated_at else None,
            "available_actions": _job_actions(j, quote),
        })

    for d in drafts:
        current_stage, is_unknown = map_draft_stage(d.status)
        if is_unknown:
            unknown_statuses.add(f"home_service_booking_drafts.status={d.status}")
        # Provider-match-delayed exception: still matching after 15 min.
        if current_stage == "MATCHING" and d.created_at:
            created = d.created_at if d.created_at.tzinfo else d.created_at.replace(tzinfo=timezone.utc)
            if (_now() - created) > timedelta(minutes=DEFAULT_SLA_MINUTES * 0.25 or 15):
                current_stage = "AT_RISK"
        customer = users_by_id.get(d.customer_id) if d.customer_id else None
        tenant = tenants_by_id.get(d.selected_tenant_id) if d.selected_tenant_id else None
        service = services_by_id.get(d.offering_id)
        job_type = job_types_by_id.get(d.job_type_id) if d.job_type_id else None

        rows.append({
            "work_id": f"REQ-{str(d.id)[:8].upper()}", "work_type": "REQUEST",
            "draft_id": str(d.id),
            "booking_id": None, "job_id": None, "booking_number": None,
            "customer_id": str(d.customer_id) if d.customer_id else None,
            "customer_name": customer.full_name if customer else d.customer_name,
            "customer_contact_summary": _mask_phone(customer.phone if customer else d.customer_phone),
            "master_service": service.service_name if service else None,
            "job_type": job_type.label if job_type else None,
            "tenant_id": str(d.selected_tenant_id) if d.selected_tenant_id else None,
            "tenant_name": tenant.business_name if tenant else None,
            "technician_id": None, "technician_name": None,
            "current_stage": current_stage, "canonical_status": d.status,
            "assignment_status": "unassigned" if not d.selected_tenant_id else "matched",
            "schedule": {"date": d.preferred_date.isoformat() if d.preferred_date else None,
                         "window": d.preferred_time_window},
            "sla_state": "NOT_APPLICABLE", "sla_deadline": None,
            "amount_summary": ({"source": "draft_price_snapshot", **{
                k: d.price_snapshot[k] for k in
                ("visit_fee", "min_price", "max_price", "estimated_total", "customer_total", "display_price", "note")
                if k in d.price_snapshot
            }} if d.price_snapshot else {"source": "none"}),
            "location_summary": f"{d.city or '—'}" + (f" · {d.zipcode}" if d.zipcode else ""),
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None,
            "available_actions": ["view_details"],
        })

    # ── Search (server-side, applied post-projection since it spans two
    #    source tables + joined names — bounded by the 2000-row candidate
    #    window above, never the full table). ───────────────────────────────
    jobs_by_id = {row["job_id"]: row for row in rows if row["work_type"] == "JOB"}
    requests_by_id = {row["work_id"]: row for row in rows if row["work_type"] == "REQUEST"}
    page_rows = []
    for selected_row in selected:
        if selected_row.work_type == "JOB":
            row = jobs_by_id.get(str(selected_row.record_id))
        else:
            row = requests_by_id.get(f"REQ-{str(selected_row.record_id)[:8].upper()}")
        if row is not None:
            page_rows.append(row)

    return {
        "records": page_rows,
        "pagination": {"page": page, "page_size": page_size, "total": total,
                       "total_pages": max(1, -(-total // page_size))},
        "unknown_statuses": sorted(unknown_statuses),
        "last_updated_at": _now().isoformat(),
    }


def _job_actions(job: ServiceJob, quote: ServiceJobQuote | None) -> list[str]:
    actions = ["view_details"]
    if job.assignment_status == "unassigned":
        actions.append("assign_tenant")
    elif job.tenant_id:
        actions.append("contact_tenant")
    if job.customer_id:
        actions.append("view_customer")
    if quote is not None:
        actions.append("view_estimate")
    actions.append("view_status_history")
    return actions


async def compute_metrics(db: AsyncSession, *, tenant_id: uuid.UUID | None = None) -> dict:
    """The six KPI tiles. Independent of pagination.

    These load on every single view of the page, so their cost is the page's
    floor. They used to be five `count(*) FILTER (<20-branch CASE over a
    correlated subquery>)` aggregates with no WHERE clause at all — a full
    sequential scan of service_jobs, evaluating the CASE per row, per page view.
    Measured at 200k jobs that was ~1.9s, and it grows linearly: a million jobs
    would put the page's floor near ten seconds.

    Four of the five buckets are pure functions of `status`, so they come from a
    single GROUP BY that Postgres satisfies with one aggregate over ~15 distinct
    values and bucket in Python. Only the two that genuinely need more — the
    quote-dependent approval count and the age-dependent overdue count — get
    their own query, and both are restricted to an indexable status set first.
    """
    job_filters = [ServiceJob.tenant_id == tenant_id] if tenant_id else []
    draft_filters = [
        HomeServiceBookingDraft.status.in_(DRAFT_OPERATIONAL_REQUEST_STATUSES),
        HomeServiceBookingDraft.serviceability_status == "serviceable",
        HomeServiceBookingDraft.selected_tenant_id.isnot(None),
        HomeServiceBookingDraft.zipcode.isnot(None),
    ]
    if tenant_id: draft_filters.append(HomeServiceBookingDraft.selected_tenant_id == tenant_id)

    active_stages = {key for key, tab in STAGE_TO_TAB.items() if tab == "active"}
    active_statuses = {s for s in JOB_STAGE_MAP if JOB_STAGE_MAP[s] in active_stages}
    open_statuses = {status for status, mapped in JOB_STAGE_MAP.items()
                     if mapped not in {"COMPLETED", "CLOSED"}}
    at_risk_statuses = STAGE_TO_JOB_STATUSES.get("AT_RISK", set())

    # 1. One pass, grouped by status. Everything derivable from status alone.
    status_rows = (await db.execute(
        select(ServiceJob.status, func.count(ServiceJob.id))
        .where(*job_filters).group_by(ServiceJob.status)
    )).all()
    by_status = {row[0]: int(row[1] or 0) for row in status_rows}

    active = sum(n for s, n in by_status.items() if s in active_statuses)
    unassigned = sum(n for s, n in by_status.items() if JOB_STAGE_MAP.get(s) == "UNASSIGNED")
    in_progress = sum(n for s, n in by_status.items() if JOB_STAGE_MAP.get(s) == "IN_PROGRESS")
    # AT_RISK stage, plus every row whose status this projection cannot map at
    # all — an unmapped status is an operational unknown and must be surfaced,
    # which is why it is counted here rather than silently dropped.
    flagged = sum(n for s, n in by_status.items()
                  if s in at_risk_statuses or s not in _MAPPED_JOB_STATUSES)

    # 2. AWAITING_APPROVAL needs the current quote, so it keeps the correlated
    #    subquery — but only over the two statuses that can ever qualify, which
    #    turns a full scan into an index range scan.
    current_quote_status = (
        select(ServiceJobQuote.status)
        .where(ServiceJobQuote.job_id == ServiceJob.id, ServiceJobQuote.is_current.is_(True))
        .order_by(ServiceJobQuote.version_number.desc()).limit(1)
        .correlate(ServiceJob).scalar_subquery()
    )
    awaiting_approval = int(await db.scalar(
        select(func.count(ServiceJob.id)).where(
            *job_filters,
            ServiceJob.status.in_(["inspection_done", "quote_required"]),
            current_quote_status.in_(QUOTE_AWAITING_APPROVAL_STATUSES),
        )
    ) or 0)

    # 3. Overdue-but-open needs created_at. Excluding the statuses already
    #    counted in `flagged` keeps this a disjoint set, so the two add without
    #    double-counting — the previous version expressed this as one OR, which
    #    is why it could not be split off the full scan.
    overdue_cutoff = _now() - timedelta(minutes=DEFAULT_SLA_MINUTES)
    overdue_statuses = open_statuses - at_risk_statuses
    overdue = int(await db.scalar(
        select(func.count(ServiceJob.id)).where(
            *job_filters,
            ServiceJob.status.in_(overdue_statuses),
            ServiceJob.created_at < overdue_cutoff,
        )
    ) or 0) if overdue_statuses else 0

    draft_counts = (await db.execute(
        select(func.count(HomeServiceBookingDraft.id).label("total"))
        .where(*draft_filters)
    )).one()
    drafts_count = int(draft_counts.total or 0)

    return {
        # Draft attempts are reported separately below. Counting them as
        # active work made an unfinished Instagram conversation look like a
        # confirmed booking in the headline KPI.
        "active": active,
        "new_requests": drafts_count,
        "unassigned": unassigned,
        "in_progress": in_progress,
        "awaiting_approval": awaiting_approval,
        "at_risk": flagged + overdue,
    }


async def compute_metrics_cached(db: AsyncSession, *, tenant_id: uuid.UUID | None = None,
                                 refresh: bool = False) -> dict:
    """`compute_metrics` behind a stale-while-revalidate cache.

    Counting every job is irreducible work, so the cache exists to stop it
    happening on every page view rather than to make it cheaper. Numbers up to a
    minute old are fine for a KPI strip — and the response carries `freshness`
    and `computed_at` so the UI can say how old they are instead of implying
    they are live.

    The background refresh needs a session that outlives this request, so it
    opens its own rather than borrowing `db`.
    """
    from app.database import get_session_factory
    from app.engines.final_records.operations_cache import get_or_compute, summary_key

    async def _compute() -> dict:
        async with get_session_factory()() as bg_db:
            return await compute_metrics(bg_db, tenant_id=tenant_id)

    data, freshness, computed_at = await get_or_compute(
        summary_key(tenant_id), _compute, force=refresh)
    return {**data, "freshness": freshness, "computed_at": computed_at}
