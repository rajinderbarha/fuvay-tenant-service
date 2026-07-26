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

from sqlalchemy import select, func, or_, false as sa_false
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
}
# Stages that represent genuinely finished work (spec §7: closed_estimate_declined is NOT completed)
COMPLETED_STAGES = {"COMPLETED"}
# Canonical quote statuses that mean "sent, waiting on the customer" —
# matches app/engines/quote_checklist/constants.py exactly.
QUOTE_AWAITING_APPROVAL_STATUSES = {"sent_to_customer", "revision_requested"}

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
    view: str = "all",
    search: str | None = None,
    tenant_id: uuid.UUID | None = None,
    technician_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    stage: str | None = None,
    assignment: str | None = None,
    city: str | None = None,
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
    if city: job_filters.append(ServiceJob.city == city)
    if date_from: job_filters.append(ServiceJob.created_at >= date_from)
    if date_to: job_filters.append(ServiceJob.created_at <= date_to)
    if assignment == "unassigned": job_filters.append(ServiceJob.assignment_status == "unassigned")
    elif assignment == "assigned": job_filters.append(ServiceJob.assignment_status.in_(["assigned", "accepted"]))

    draft_filters = [HomeServiceBookingDraft.status.in_(DRAFT_ACTIVE_STATUSES | DRAFT_EXCEPTION_STATUSES)]
    if customer_id: draft_filters.append(HomeServiceBookingDraft.customer_id == customer_id)
    if city: draft_filters.append(HomeServiceBookingDraft.city == city)
    if date_from: draft_filters.append(HomeServiceBookingDraft.created_at >= date_from)
    if date_to: draft_filters.append(HomeServiceBookingDraft.created_at <= date_to)
    if tenant_id: draft_filters.append(HomeServiceBookingDraft.selected_tenant_id == tenant_id)
    # Drafts have no technician/assignment concept yet -- excluded by those filters.
    if technician_id or assignment == "assigned":
        draft_filters.append(sa_false())  # short-circuits to zero rows, not silently ignored

    jobs = (await db.execute(
        select(ServiceJob).where(*job_filters).order_by(ServiceJob.created_at.desc()).limit(2000)
    )).scalars().all()
    drafts = (await db.execute(
        select(HomeServiceBookingDraft).where(*draft_filters)
        .order_by(HomeServiceBookingDraft.created_at.desc()).limit(2000)
    )).scalars().all()

    # Batch lookups — bounded, no N+1 (mirrors sla_summary.py's pattern).
    from app.engines.tenant_engine.models import Tenant
    from app.engines.auth.models import User
    from app.engines.admin_catalog.models import MasterService, JobTypeDefinition

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
            "amount_summary": {"source": "none"},
            "location_summary": f"{d.city or '—'}" + (f" · {d.zipcode}" if d.zipcode else ""),
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None,
            "available_actions": ["view_details"],
        })

    # ── Search (server-side, applied post-projection since it spans two
    #    source tables + joined names — bounded by the 2000-row candidate
    #    window above, never the full table). ───────────────────────────────
    if search:
        s = search.strip().lower()
        rows = [r for r in rows if s in (r["work_id"] or "").lower()
                or s in (r["booking_number"] or "").lower()
                or s in (r["customer_name"] or "").lower()
                or s in (r["tenant_name"] or "").lower()]

    if stage:
        rows = [r for r in rows if r["current_stage"] == stage]

    view_key = {"requests": "requests", "active": "active", "approval": "approval",
                "exceptions": "exceptions", "completed": "completed", "all": None}.get(view)
    if view_key == "approval":
        rows = [r for r in rows if r["current_stage"] == "AWAITING_APPROVAL"]
    elif view_key:
        rows = [r for r in rows if STAGE_TO_TAB.get(r["current_stage"]) == view_key]

    rows.sort(key=lambda r: r["created_at"] or "", reverse=True)
    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start:start + page_size]

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
    """Independent of pagination — separate COUNT-style queries, not derived
    from the current page of `list_operations`."""
    job_filters = [ServiceJob.tenant_id == tenant_id] if tenant_id else []
    draft_filters = [HomeServiceBookingDraft.status.in_(DRAFT_ACTIVE_STATUSES)]
    if tenant_id: draft_filters.append(HomeServiceBookingDraft.selected_tenant_id == tenant_id)

    jobs = (await db.execute(select(ServiceJob).where(*job_filters).limit(5000))).scalars().all()
    drafts_count = await db.scalar(select(func.count(HomeServiceBookingDraft.id)).where(*draft_filters)) or 0

    quotes = (await db.execute(
        select(ServiceJobQuote).where(ServiceJobQuote.job_id.in_([j.id for j in jobs]),
                                      ServiceJobQuote.is_current == True)  # noqa: E712
    )).scalars().all() if jobs else []
    quote_status_by_job = {q.job_id: q.status for q in quotes}
    sla_map = await attach_sla(db, jobs)

    active = 0; unassigned = 0; in_progress = 0; awaiting_approval = 0; at_risk = 0
    for j in jobs:
        stage, _ = map_job_stage(j.status, quote_status_by_job.get(j.id))
        if STAGE_TO_TAB.get(stage) == "active":
            active += 1
        if stage == "UNASSIGNED":
            unassigned += 1
        if stage == "IN_PROGRESS":
            in_progress += 1
        if stage == "AWAITING_APPROVAL":
            awaiting_approval += 1
        if stage == "AT_RISK" or sla_map.get(str(j.id), {}).get("sla_status") == "BREACHED":
            at_risk += 1

    return {
        "active": active + drafts_count,
        "new_requests": drafts_count,
        "unassigned": unassigned,
        "in_progress": in_progress,
        "awaiting_approval": awaiting_approval,
        "at_risk": at_risk,
    }
