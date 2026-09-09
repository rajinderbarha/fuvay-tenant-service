"""Home Services operational dashboard aggregation.

Single read-only projection over canonical, already-proven data sources
(service_jobs, provider_team_members/team_readiness_service, tenant_services,
customer_complaints, customer_reviews, service_invoices, tenant_billing) --
never a second, drifting copy of job/staff/finance state. Every query is
tenant-scoped; Home Services scope is structural because service_jobs is the
Home-Services-only final-record table (Coaching/Real Estate use separate
tables), matching the isolation argument already established in
finance_hub.home_services_finance_service.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Presentation-group mapping over the real execution.constants job-status
# machine -- never a second set of database statuses.
# "New" and "Awaiting assignment" both map from the same raw status
# (pending_assignment) in this codebase's execution model -- there is no
# separate "just created, not yet due for assignment" status, so a single
# real bucket is used for both to avoid inventing a distinction the backend
# cannot support.
_PIPELINE_GROUPS = [
    ("awaiting_assignment", "Awaiting assignment", {"pending_assignment"}),
    ("scheduled", "Scheduled", {"assigned", "accepted", "scheduled"}),
    ("on_the_way", "On the way", {"on_the_way"}),
    ("inspection", "Inspection", {"reached_site", "inspection_started", "inspection_done"}),
    ("estimate_approval", "Estimate approval", {"quote_required"}),
    ("in_progress", "In progress", {"service_started"}),
    ("work_done", "Work done", {"work_done"}),
    ("completed", "Completed", {"completed"}),
    ("cancelled", "Cancelled", {"cancelled", "failed", "closed_estimate_declined"}),
]
_STATUS_TO_GROUP = {s: key for key, _, statuses in _PIPELINE_GROUPS for s in statuses}


async def _safe(coro, module_key: str, errors: list[str]) -> dict | list | None:
    try:
        return await coro
    except Exception as exc:  # noqa: BLE001 -- module-level isolation is the point
        errors.append(module_key)
        return None


async def _attention_queue(
    db: AsyncSession,
    tid: uuid.UUID,
    service_coverage: list[dict] | None = None,
) -> list[dict]:
    items: list[dict] = []

    unassigned = (await db.execute(text(
        "SELECT count(*), min(created_at) FROM service_jobs "
        "WHERE tenant_id=:tid AND status='pending_assignment'"
    ), {"tid": str(tid)})).fetchone()
    if unassigned and unassigned[0]:
        items.append({
            "key": "UNASSIGNED_JOBS", "label": "Unassigned jobs", "count": int(unassigned[0]),
            "severity": "warning", "oldest_age_hours": _age_hours(unassigned[1]),
            "destination": "/home-services/bookings-jobs?stage=new&assignment=unassigned",
        })

    quote_pending = (await db.execute(text(
        "SELECT count(*), min(created_at) FROM service_jobs "
        "WHERE tenant_id=:tid AND status='quote_required'"
    ), {"tid": str(tid)})).fetchone()
    if quote_pending and quote_pending[0]:
        items.append({
            "key": "ESTIMATES_AWAITING_APPROVAL", "label": "Estimates awaiting approval",
            "count": int(quote_pending[0]), "severity": "warning",
            "oldest_age_hours": _age_hours(quote_pending[1]),
            "destination": "/home-services/bookings-jobs?stage=estimate_approval",
        })

    pending_invoices = (await db.execute(text(
        "SELECT count(*), min(created_at) FROM service_invoices "
        "WHERE tenant_id=:tid AND payment_status='pending'"
    ), {"tid": str(tid)})).fetchone()
    if pending_invoices and pending_invoices[0]:
        items.append({
            "key": "PAYMENT_CONFIRMATIONS_PENDING", "label": "Payment confirmations pending",
            "count": int(pending_invoices[0]), "severity": "info",
            "oldest_age_hours": _age_hours(pending_invoices[1]),
            "destination": "/home-services/direct-payments",
        })

    # SLA at risk: a job assigned to a technician who hasn't accepted it
    # within a reasonable window. There is no dedicated SLA-deadline field on
    # service_jobs (unlike customer_complaints, which has real sla_status/
    # tenant_first_response_due_at columns) -- this reuses the same real
    # assignment timestamp every other assignment view already reads
    # (service_jobs.updated_at, set by assign_job() when status becomes
    # 'assigned') rather than inventing a new per-job deadline column. 2
    # hours is a conservative, documented policy constant, not a per-tenant
    # configurable SLA yet.
    sla_at_risk = (await db.execute(text(
        "SELECT count(*), min(sj.updated_at) FROM service_jobs sj "
        "WHERE sj.tenant_id=:tid AND sj.status='assigned' "
        "AND sj.updated_at < now() - interval '2 hours'"
    ), {"tid": str(tid)})).fetchone()
    if sla_at_risk and sla_at_risk[0]:
        items.append({
            "key": "SLA_AT_RISK", "label": "SLA at risk", "count": int(sla_at_risk[0]),
            "severity": "danger", "oldest_age_hours": _age_hours(sla_at_risk[1]),
            "destination": "/home-services/bookings-jobs?sla=AT_RISK",
        })

    open_complaints = (await db.execute(text(
        "SELECT count(*), min(created_at) FROM customer_complaints "
        "WHERE tenant_id=:tid AND status IN ('open','in_progress')"
    ), {"tid": str(tid)})).fetchone()
    if open_complaints and open_complaints[0]:
        items.append({
            "key": "OPEN_COMPLAINTS", "label": "Open complaints", "count": int(open_complaints[0]),
            "severity": "danger", "oldest_age_hours": _age_hours(open_complaints[1]),
            "destination": "/home-services/complaints?status=open",
        })

    if service_coverage is None:
        from app.engines.home_service_assignment.team_readiness_service import compute_service_coverage
        service_coverage = await compute_service_coverage(db, tid)
    gap_count = sum(1 for c in service_coverage if c["ready_technician_count"] == 0)
    if gap_count:
        items.append({
            "key": "SERVICE_COVERAGE_GAPS", "label": "Services with no eligible technician",
            "count": gap_count, "severity": "warning", "oldest_age_hours": None,
            "destination": "/home-services/team",
        })

    from app.engines.usage_credits.constants import DEFAULT_LOW_USAGE_CREDIT_THRESHOLD
    billing = (await db.execute(text(
        "SELECT credit_balance FROM tenant_billing WHERE tenant_id=:tid"
    ), {"tid": str(tid)})).fetchone()
    if billing and billing.credit_balance is not None \
            and float(billing.credit_balance) < float(DEFAULT_LOW_USAGE_CREDIT_THRESHOLD):
        items.append({
            "key": "LOW_USAGE_CREDIT", "label": "Low usage-credit balance", "count": 1,
            "severity": "warning", "oldest_age_hours": None,
            "destination": "/home-services/finance?tab=usage-credits",
        })

    return items


def _age_hours(ts) -> float | None:
    if not ts:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return round((datetime.now(timezone.utc) - ts).total_seconds() / 3600, 1)


async def _job_pipeline(db: AsyncSession, tid: uuid.UUID) -> list[dict]:
    rows = (await db.execute(text(
        "SELECT status, count(*) FROM service_jobs WHERE tenant_id=:tid GROUP BY status"
    ), {"tid": str(tid)})).fetchall()
    counts = {key: 0 for key, _, _ in _PIPELINE_GROUPS}
    for status, cnt in rows:
        group = _STATUS_TO_GROUP.get(status)
        if group:
            counts[group] += int(cnt)
    return [{"key": key, "label": label, "count": counts[key]} for key, label, _ in _PIPELINE_GROUPS]


async def _todays_jobs(db: AsyncSession, tid: uuid.UUID, limit: int = 20) -> list[dict]:
    rows = (await db.execute(text(
        "SELECT sj.id, sj.job_number, sj.status, sj.scheduled_date, sj.scheduled_time_window, "
        "sj.city, sj.assigned_staff_id, "
        "COALESCE(t.full_name, 'Customer') AS customer_name, "
        "COALESCE(ts.tenant_display_name, ms.service_name, 'Service') AS service_name, "
        "ptm.full_name AS technician_name "
        "FROM service_jobs sj "
        "LEFT JOIN users t ON t.id = sj.customer_id "
        "LEFT JOIN tenant_services ts ON ts.id = sj.offering_id "
        "LEFT JOIN master_services ms ON ms.id = ts.master_service_id "
        "LEFT JOIN provider_team_members ptm ON ptm.id = sj.assigned_staff_id "
        "WHERE sj.tenant_id=:tid AND sj.scheduled_date = CURRENT_DATE "
        "ORDER BY sj.scheduled_time_window NULLS LAST, sj.created_at DESC LIMIT :lim"
    ), {"tid": str(tid), "lim": limit})).fetchall()
    return [{
        "job_id": str(r.id), "job_number": r.job_number, "customer_name": r.customer_name,
        "service_name": r.service_name, "scheduled_time": r.scheduled_time_window,
        "technician_name": r.technician_name, "city": r.city, "status": r.status,
        "pipeline_group": _STATUS_TO_GROUP.get(r.status, r.status),
    } for r in rows]


_JOBS_TAB_GROUPS = [("all", "All", None)] + [(k, l, s) for k, l, s in _PIPELINE_GROUPS]


async def get_jobs_list(
    db: AsyncSession, tid: uuid.UUID, *, group: str | None = None,
    search: str | None = None, limit: int = 20, offset: int = 0,
) -> dict:
    """Bookings & Jobs list -- same resolved-name join pattern as the
    dashboard's Today's Jobs table (customer/service/technician names), just
    without the scheduled_date=today restriction, with pagination and a
    pipeline-group filter. Single source of truth for status->group mapping
    (_STATUS_TO_GROUP) shared with the dashboard so tab counts here can never
    drift from the dashboard's Job Pipeline counts."""
    where = ["sj.tenant_id = :tid"]
    params: dict = {"tid": str(tid)}
    if group and group != "all":
        statuses = next((s for k, _, s in _PIPELINE_GROUPS if k == group), None)
        if statuses:
            where.append("sj.status = ANY(:statuses)")
            params["statuses"] = list(statuses)
    if search:
        where.append("(sj.job_number ILIKE :q OR sj.zipcode ILIKE :q)")
        params["q"] = f"%{search}%"
    where_sql = " AND ".join(where)

    total = (await db.execute(text(f"SELECT count(*) FROM service_jobs sj WHERE {where_sql}"), params)).scalar() or 0

    rows = (await db.execute(text(
        f"SELECT sj.id, sj.job_number, sj.status, sj.assignment_status, sj.scheduled_date, "
        f"sj.scheduled_time_window, sj.city, sj.zipcode, sj.assigned_staff_id, sj.created_at, "
        f"COALESCE(t.full_name, 'Customer') AS customer_name, "
        f"COALESCE(ts.tenant_display_name, ms.service_name, 'Service') AS service_name, "
        f"ptm.full_name AS technician_name, "
        f"si.payment_status AS payment_status "
        f"FROM service_jobs sj "
        f"LEFT JOIN users t ON t.id = sj.customer_id "
        f"LEFT JOIN tenant_services ts ON ts.id = sj.offering_id "
        f"LEFT JOIN master_services ms ON ms.id = ts.master_service_id "
        f"LEFT JOIN provider_team_members ptm ON ptm.id = sj.assigned_staff_id "
        f"LEFT JOIN service_invoices si ON si.job_id = sj.id "
        f"WHERE {where_sql} "
        f"ORDER BY sj.created_at DESC LIMIT :lim OFFSET :off"
    ), {**params, "lim": limit, "off": offset})).fetchall()

    items = [{
        "job_id": str(r.id), "job_number": r.job_number, "status": r.status,
        "pipeline_group": _STATUS_TO_GROUP.get(r.status, r.status),
        "assignment_status": r.assignment_status,
        "customer_name": r.customer_name, "service_name": r.service_name,
        "technician_name": r.technician_name,
        "scheduled_date": r.scheduled_date.isoformat() if r.scheduled_date else None,
        "scheduled_time_window": r.scheduled_time_window,
        "city": r.city, "zipcode": r.zipcode,
        "payment_status": r.payment_status,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]

    tab_rows = (await db.execute(text(
        "SELECT status, count(*) FROM service_jobs WHERE tenant_id=:tid GROUP BY status"
    ), {"tid": str(tid)})).fetchall()
    tab_counts = {key: 0 for key, _, _ in _PIPELINE_GROUPS}
    grand_total = 0
    for status, cnt in tab_rows:
        grand_total += int(cnt)
        g = _STATUS_TO_GROUP.get(status)
        if g:
            tab_counts[g] += int(cnt)
    tabs = [{"key": "all", "label": "All", "count": grand_total}] + \
           [{"key": k, "label": l, "count": tab_counts[k]} for k, l, _ in _PIPELINE_GROUPS]

    return {"items": items, "total": total, "limit": limit, "offset": offset, "tabs": tabs}


async def get_job_detail(db: AsyncSession, tid: uuid.UUID, job_id: uuid.UUID) -> dict | None:
    """Single-job detail for the Bookings & Jobs drawer -- reuses the same
    resolved-name join as the list, plus the real execution-event timeline
    and, when one exists, the real invoice. Every field here is a real
    column; fields the platform has no concept of yet (visit fee, quote
    amount, technician photo/phone) are simply omitted rather than faked."""
    row = (await db.execute(text(
        "SELECT sj.id, sj.job_number, sj.status, sj.assignment_status, sj.scheduled_date, "
        "sj.scheduled_time_window, sj.city, sj.zipcode, sj.address_snapshot, sj.assigned_staff_id, "
        "sj.completion_data, sj.failure_reason, sj.created_at, sj.updated_at, "
        "COALESCE(t.full_name, 'Customer') AS customer_name, t.phone AS customer_phone, "
        "COALESCE(ts.tenant_display_name, ms.service_name, 'Service') AS service_name, "
        "ptm.full_name AS technician_name, ptm.phone AS technician_phone "
        "FROM service_jobs sj "
        "LEFT JOIN users t ON t.id = sj.customer_id "
        "LEFT JOIN tenant_services ts ON ts.id = sj.offering_id "
        "LEFT JOIN master_services ms ON ms.id = ts.master_service_id "
        "LEFT JOIN provider_team_members ptm ON ptm.id = sj.assigned_staff_id "
        "WHERE sj.id = :jid AND sj.tenant_id = :tid"
    ), {"jid": str(job_id), "tid": str(tid)})).fetchone()
    if not row:
        return None

    events = (await db.execute(text(
        "SELECT event_type, old_status, new_status, notes, created_at "
        "FROM service_job_execution_events WHERE job_id=:jid ORDER BY created_at ASC"
    ), {"jid": str(job_id)})).fetchall()

    invoice = (await db.execute(text(
        "SELECT invoice_number, payment_status, total_amount, customer_payable_amount "
        "FROM service_invoices WHERE job_id=:jid LIMIT 1"
    ), {"jid": str(job_id)})).fetchone()

    return {
        "job_id": str(row.id), "job_number": row.job_number, "status": row.status,
        "pipeline_group": _STATUS_TO_GROUP.get(row.status, row.status),
        "assignment_status": row.assignment_status,
        "customer_name": row.customer_name,
        # MASKED CALLING: the customer's raw number is no longer returned here.
        # A number handed over once becomes a permanent private channel and the
        # next job goes off-platform, so calls are bridged by the platform
        # instead -- see masked_calling.router
        # (GET /v1/staff/service-jobs/{job_id}/contact, POST .../call).
        # `customer_phone` is kept as an explicit null rather than dropped, so
        # any existing client reading the key gets a defined absence instead of
        # an undefined that might read as "not loaded yet".
        "customer_phone": None,
        "customer_contact_mode": "platform_masked_call",
        "service_name": row.service_name,
        # The technician's own number stays visible to their own provider --
        # they are that provider's staff, so this is not a cross-party leak.
        "technician_name": row.technician_name, "technician_phone": row.technician_phone,
        "scheduled_date": row.scheduled_date.isoformat() if row.scheduled_date else None,
        "scheduled_time_window": row.scheduled_time_window,
        "city": row.city, "zipcode": row.zipcode, "address_snapshot": row.address_snapshot,
        "completion_data": row.completion_data, "failure_reason": row.failure_reason,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "timeline": [{
            "event_type": e.event_type, "old_status": e.old_status, "new_status": e.new_status,
            "notes": e.notes, "occurred_at": e.created_at.isoformat() if e.created_at else None,
        } for e in events],
        "invoice": {
            "invoice_number": invoice.invoice_number, "payment_status": invoice.payment_status,
            "total_amount": float(invoice.total_amount), "customer_payable_amount": float(invoice.customer_payable_amount),
        } if invoice else None,
    }


async def _customers_quality(db: AsyncSession, tid: uuid.UUID) -> dict:
    active_customers = (await db.execute(text(
        "SELECT count(DISTINCT customer_id) FROM service_jobs WHERE tenant_id=:tid AND customer_id IS NOT NULL"
    ), {"tid": str(tid)})).scalar() or 0
    repeat_customers = (await db.execute(text(
        "SELECT count(*) FROM (SELECT customer_id FROM service_jobs WHERE tenant_id=:tid "
        "AND customer_id IS NOT NULL GROUP BY customer_id HAVING count(*) > 1) x"
    ), {"tid": str(tid)})).scalar() or 0
    open_complaints = (await db.execute(text(
        "SELECT count(*) FROM customer_complaints WHERE tenant_id=:tid AND status IN ('open','in_progress')"
    ), {"tid": str(tid)})).scalar() or 0
    avg_rating = (await db.execute(text(
        "SELECT avg(overall_rating) FROM customer_reviews WHERE tenant_id=:tid AND status='approved'"
    ), {"tid": str(tid)})).scalar()
    return {
        "active_customers": int(active_customers), "repeat_customers": int(repeat_customers),
        "open_complaints": int(open_complaints),
        "average_rating": round(float(avg_rating), 1) if avg_rating is not None else None,
    }


async def _finance_snapshot(db: AsyncSession, tid: uuid.UUID) -> dict:
    invoices = (await db.execute(text(
        "SELECT payment_status, count(*) FROM service_invoices WHERE tenant_id=:tid GROUP BY payment_status"
    ), {"tid": str(tid)})).fetchall()
    inv_counts = {r[0]: int(r[1]) for r in invoices}
    billing = (await db.execute(text(
        "SELECT credit_balance, entitled_seats FROM tenant_billing WHERE tenant_id=:tid"
    ), {"tid": str(tid)})).fetchone()
    deduction = (await db.execute(text(
        "SELECT count(*), COALESCE(sum(abs(credit_delta)), 0) FROM usage_credit_ledger "
        "WHERE tenant_id=:tid AND event_type='completed_job_deduction' AND created_at::date = CURRENT_DATE"
    ), {"tid": str(tid)})).fetchone()
    # Seats come from the live entitlements, not `tenant_billing.entitled_seats`
    # -- that column is a cached projection refreshed by the expiry sweep, so a
    # lapsed plan would keep showing its seats on the dashboard for up to an
    # hour after they had stopped counting anywhere else.
    from app.engines.vertical_catalog.seat_enforcement import get_seat_usage
    seats = await get_seat_usage(db, tid)

    suspended = int((await db.execute(text(
        "SELECT count(*) FROM provider_team_members "
        "WHERE tenant_id = :tid AND deleted_at IS NULL AND credit_suspended_at IS NOT NULL"
    ), {"tid": str(tid)})).scalar() or 0)

    return {
        "direct_payments_pending": inv_counts.get("pending", 0),
        "direct_payments_confirmed": inv_counts.get("collected", 0),
        "usage_credit_balance": float(billing.credit_balance) if billing and billing.credit_balance is not None else None,
        "completion_deductions_today_count": int(deduction[0]) if deduction else 0,
        "completion_deductions_today_amount": float(deduction[1]) if deduction and deduction[1] is not None else 0.0,
        # The security deposit was replaced by purchased technician seats in
        # migration 317 — headcount is bought, not collateralised.
        "entitled_seats": seats["entitled_seats"],
        "used_seats": seats["used_seats"],
        "available_seats": seats["available_seats"],
        "seats_over_limit": seats["over_limit"],
        # Surfaced so a suspended workspace can see WHY its technicians went
        # inactive, instead of finding an empty roster with no explanation.
        "team_suspended_for_credit": suspended,
    }


async def _tenant_bookability(db: AsyncSession, tid: uuid.UUID) -> dict:
    """The SAME tenant-level bookability gate customer discovery and provider
    matching read (provider_visibility_statuses.is_bookable, computed by
    provider_portal._evaluate_provider_bookability) -- not a second,
    dashboard-only calculation. There is no canonical PER-OFFERING
    bookability evaluator in this codebase (is_bookable is tenant-wide), so
    per-offering rows below layer real technician-coverage on top of this
    single tenant-level gate rather than inventing a competing one."""
    row = (await db.execute(text(
        "SELECT is_bookable, bookability_blockers FROM provider_visibility_statuses "
        "WHERE tenant_id=:tid AND category_id IS NULL "
        "ORDER BY created_at DESC, id DESC LIMIT 1"
    ), {"tid": str(tid)})).fetchone()
    if not row:
        return {"is_bookable": False, "blockers": []}
    return {"is_bookable": bool(row.is_bookable), "blockers": row.bookability_blockers or []}


async def _recent_activity(db: AsyncSession, tid: uuid.UUID, limit: int = 8) -> list[dict]:
    rows = (await db.execute(text(
        "SELECT event_type, job_id, created_at FROM service_job_execution_events "
        "WHERE tenant_id=:tid ORDER BY created_at DESC LIMIT :lim"
    ), {"tid": str(tid), "lim": limit})).fetchall()
    return [{"event_type": r.event_type, "job_id": str(r.job_id) if r.job_id else None,
             "occurred_at": r.created_at.isoformat() if r.created_at else None} for r in rows]


def _bookability_row(coverage_row: dict, tenant_bookable: dict | None) -> dict:
    if tenant_bookable is not None and not tenant_bookable["is_bookable"]:
        blockers = tenant_bookable["blockers"]
        reason = blockers[0]["message"] if blockers else "Not yet bookable"
        return {"offering_id": coverage_row["offering_id"], "name": coverage_row["name"],
                "bookable": False, "blocking_reason": reason}
    if coverage_row["ready_technician_count"] == 0:
        return {"offering_id": coverage_row["offering_id"], "name": coverage_row["name"],
                "bookable": False, "blocking_reason": "No available technician"}
    return {"offering_id": coverage_row["offering_id"], "name": coverage_row["name"],
            "bookable": True, "blocking_reason": None}


async def get_dashboard(db: AsyncSession, tid: uuid.UUID) -> dict:
    errors: list[str] = []

    from app.engines.home_service_assignment.team_readiness_service import compute_team_summary, compute_service_coverage
    team_summary = await _safe(compute_team_summary(db, tid), "staff_capacity", errors) or {"counts": {}, "per_member": {}}
    coverage = await _safe(compute_service_coverage(db, tid, team_summary), "service_bookability", errors) or []

    attention = await _safe(_attention_queue(db, tid, coverage), "attention_queue", errors) or []
    pipeline = await _safe(_job_pipeline(db, tid), "job_pipeline", errors) or []
    todays_jobs = await _safe(_todays_jobs(db, tid), "todays_jobs", errors) or []

    customers_quality = await _safe(_customers_quality(db, tid), "customers_quality", errors) or {}
    finance = await _safe(_finance_snapshot(db, tid), "finance_snapshot", errors) or {}
    activity = await _safe(_recent_activity(db, tid), "recent_activity", errors) or []

    tenant_bookable = await _safe(_tenant_bookability(db, tid), "service_bookability", errors)

    ready = team_summary["counts"].get("ready", 0)
    active_members = (await db.execute(text(
        "SELECT count(*) FROM provider_team_members WHERE tenant_id=:tid AND status='active' AND deleted_at IS NULL"
    ), {"tid": str(tid)})).scalar() or 0
    assigned_now = (await db.execute(text(
        "SELECT count(DISTINCT assigned_staff_id) FROM service_jobs WHERE tenant_id=:tid "
        "AND assigned_staff_id IS NOT NULL AND status NOT IN ('completed','cancelled','failed','closed_estimate_declined')"
    ), {"tid": str(tid)})).scalar() or 0

    tenant = (await db.execute(text(
        "SELECT COALESCE(business_name, tenant_name) AS business_name, "
        "tenant_code, city, state, zipcode, logo_url "
        "FROM tenants WHERE id=:tid"
    ), {"tid": str(tid)})).fetchone()
    today_total = (await db.execute(text(
        "SELECT count(*) FROM service_jobs WHERE tenant_id=:tid "
        "AND scheduled_date=CURRENT_DATE"
    ), {"tid": str(tid)})).scalar() or 0
    active_jobs = sum(
        int(item["count"]) for item in pipeline
        if item["key"] not in {"completed", "cancelled"}
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tenant_id": str(tid),
        "vertical": {"key": "home_services"},
        "workspace": {
            "business_name": tenant.business_name if tenant else "Your business",
            "tenant_code": tenant.tenant_code if tenant else None,
            "city": tenant.city if tenant else None,
            "state": tenant.state if tenant else None,
            "zipcode": tenant.zipcode if tenant else None,
            "logo_url": tenant.logo_url if tenant else None,
        },
        "operational_summary": {
            "active_jobs": active_jobs,
            "jobs_today": int(today_total),
            "available_technicians": max(ready - int(assigned_now), 0),
            "attention_items": sum(int(item.get("count", 0)) for item in attention),
        },
        "attention_queue": attention,
        "job_pipeline": pipeline,
        "todays_jobs": todays_jobs,
        "staff_capacity": {
            "ready": ready, "assigned_now": int(assigned_now),
            "available_now": max(ready - int(assigned_now), 0), "total_active": int(active_members),
        },
        "bookability": tenant_bookable or {"is_bookable": False, "blockers": []},
        "service_bookability": [_bookability_row(c, tenant_bookable) for c in coverage],
        "customers_quality": customers_quality,
        "finance_snapshot": finance,
        "recent_activity": activity,
        "available_actions": ["VIEW_ALL_JOBS", "OPEN_DISPATCH", "REFRESH"],
        "failed_modules": errors,
    }
