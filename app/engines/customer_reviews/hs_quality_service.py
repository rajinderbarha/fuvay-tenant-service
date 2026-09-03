"""Home Services Reviews & Service Quality — tenant-facing read aggregation.

Reuses the canonical Sprint 24 review system (customer_reviews, review_replies,
review_flags, review_events, tenant_rating_summaries) end to end -- this
module adds NO new review table and NO new rating calculation. It only joins
those canonical tables to service_jobs/provider_team_members/tenant_services/
master_services/customer_complaints for the job-linked context the Reviews &
Service Quality page needs, and projects real KPIs/trend/distribution from
them.

Mutations (reply, moderation flag) are NOT duplicated here -- the frontend
calls the existing, already-secured
POST /v1/provider/reviews/{id}/reply and POST /v1/provider/reviews/{id}/flag
(app.engines.customer_reviews.provider_router), which already enforce
ownership, tenant scope, and the one-reply-per-review constraint.

Home Services scope is structural: a review only appears here when its
job_id resolves to a real service_jobs row for this tenant (record_type may
be 'booking', but the join is what actually proves Home Services scope --
Coaching/Real Estate reviews have no job_id and are excluded by the INNER
JOIN, never a record_type string match alone).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _parse_boundary(value: str, *, end_of_day: bool = False) -> datetime | None:
    """Turn a `YYYY-MM-DD` or ISO-8601 filter bound into a tz-aware datetime.

    A bare date is expanded to cover the whole day, so `date_to=2026-08-21`
    includes reviews submitted at 18:40 that day instead of stopping at
    midnight. Unparseable input returns None and the bound is dropped rather
    than erroring the whole queue.
    """
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if len(raw) == 10 and end_of_day:  # bare YYYY-MM-DD upper bound
        parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _customer_alias(customer_id: str | None) -> str:
    """Tenant-scoped display alias -- never a name/phone/email. Stable per
    customer (first 4 hex chars of their UUID), matching the reference
    design's "Customer HS-8F42" pattern without inventing a new id scheme."""
    if not customer_id:
        return "Customer"
    return f"Customer {customer_id.replace('-', '')[:4].upper()}"


async def get_reviews_summary(
    db: AsyncSession, tid: uuid.UUID, *,
    rating: int | None = None, rating_max: int | None = None,
    reply_status: str | None = None,
    technician_id: uuid.UUID | None = None, complaint_linked: bool | None = None,
    moderation_status: str | None = None, search: str | None = None,
    date_from: str | None = None, date_to: str | None = None,
    offering_id: uuid.UUID | None = None,
    limit: int = 20, offset: int = 0,
) -> dict:
    where = ["cr.tenant_id = :tid", "sj.id IS NOT NULL", "cr.status != 'deleted'"]
    params: dict = {"tid": str(tid)}

    if rating:
        where.append("cr.overall_rating = :rating")
        params["rating"] = rating
    if rating_max:
        # The "Low ratings" KPI counts overall_rating <= 2, but the only
        # filter available was an EXACT match, so clicking that tile filtered
        # to exactly 2 stars and quietly dropped every 1-star review -- the
        # list never matched the number on the tile it came from.
        where.append("cr.overall_rating <= :rating_max")
        params["rating_max"] = rating_max
    if reply_status == "answered":
        where.append("rr.id IS NOT NULL")
    elif reply_status == "unanswered":
        where.append("rr.id IS NULL")
    if technician_id:
        where.append("cr.staff_member_id = :sid")
        params["sid"] = str(technician_id)
    if offering_id:
        # Maps straight onto the tenant's configured catalog (tenant_services),
        # i.e. the same offerings the Services & Pricing setup page manages.
        where.append("sj.offering_id = :oid")
        params["oid"] = str(offering_id)
    if complaint_linked is True:
        where.append("cc.id IS NOT NULL")
    elif complaint_linked is False:
        where.append("cc.id IS NULL")
    if moderation_status:
        where.append("rf.status = :mstatus")
        params["mstatus"] = moderation_status
    if search:
        where.append("(cr.review_text ILIKE :q OR cr.review_number ILIKE :q OR sj.job_number ILIKE :q)")
        params["q"] = f"%{search}%"
    # The date range NEVER worked. These were bound as plain strings against a
    # timestamptz column, and asyncpg rejects that outright
    # ("expected a datetime.date or datetime.datetime instance, got 'str'").
    # The router's per-module _safe() wrapper caught the DataError and turned
    # it into failed_modules=['reviews'], so supplying any date silently
    # returned an empty list rather than an error -- indistinguishable from
    # "no reviews in that range". Parsing to real datetimes is the fix; an
    # in-SQL CAST does not work, because asyncpg then infers the parameter as
    # timestamptz and still refuses the str.
    if date_from:
        parsed_from = _parse_boundary(date_from)
        if parsed_from:
            where.append("cr.created_at >= :dfrom")
            params["dfrom"] = parsed_from
    if date_to:
        parsed_to = _parse_boundary(date_to, end_of_day=True)
        if parsed_to:
            where.append("cr.created_at <= :dto")
            params["dto"] = parsed_to

    where_sql = " AND ".join(where)
    # Complaint join is pre-deduped to ONE (the most recent) complaint per
    # job via a subquery -- a job can have multiple complaints, and joining
    # customer_complaints directly would fan out rows and break the
    # ORDER BY/LIMIT/OFFSET pagination below (DISTINCT ON at the outer level
    # cannot fix that since it doesn't sort by created_at first).
    base_from = (
        "FROM customer_reviews cr "
        "JOIN service_jobs sj ON sj.id = cr.job_id "
        "LEFT JOIN review_replies rr ON rr.review_id = cr.id "
        "LEFT JOIN provider_team_members ptm ON ptm.id = cr.staff_member_id "
        "LEFT JOIN LATERAL ("
        "  SELECT id, complaint_number, status FROM customer_complaints "
        "  WHERE job_id = sj.id ORDER BY created_at DESC LIMIT 1"
        ") cc ON true "
        "LEFT JOIN review_flags rf ON rf.review_id = cr.id AND rf.status = 'open' "
        "LEFT JOIN tenant_services ts ON ts.id = sj.offering_id "
        "LEFT JOIN master_services ms ON ms.id = ts.master_service_id "
    )

    total = (await db.execute(text(f"SELECT count(*) {base_from} WHERE {where_sql}"), params)).scalar() or 0

    rows = (await db.execute(text(
        f"SELECT cr.id, cr.review_number, cr.customer_id, cr.overall_rating, "
        f"cr.review_text, cr.status AS review_status, cr.created_at, "
        f"sj.id AS job_id, sj.job_number, "
        f"COALESCE(ts.tenant_display_name, ms.service_name, 'Service') AS service_name, "
        f"ptm.full_name AS technician_name, "
        f"rr.id AS reply_id, rr.reply_text, rr.status AS reply_status, "
        f"cc.id AS complaint_id, cc.complaint_number, cc.status AS complaint_status, "
        f"rf.id AS flag_id, rf.status AS flag_status "
        f"{base_from} WHERE {where_sql} "
        f"ORDER BY cr.created_at DESC LIMIT :lim OFFSET :off"
    ), {**params, "lim": limit, "off": offset})).fetchall()

    items = [{
        "review_id": str(r.id), "review_number": r.review_number,
        "customer_alias": _customer_alias(str(r.customer_id)),
        "rating": r.overall_rating, "review_excerpt": (r.review_text or "")[:140],
        "job_id": str(r.job_id), "job_number": r.job_number, "service_name": r.service_name,
        "technician_name": r.technician_name,
        "reply_status": "answered" if r.reply_id else "unanswered",
        # Publication state was selected but never projected, so the queue
        # could not distinguish a review the customer can see from one still
        # awaiting approval -- and with no review_policies row present every
        # review stays 'pending', which made that invisible distinction the
        # normal case rather than the exception.
        "review_status": r.review_status,
        "complaint_linked": r.complaint_id is not None,
        "complaint_number": r.complaint_number,
        "moderation_status": r.flag_status if r.flag_id else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]

    return {"items": items, "total": total, "limit": limit, "offset": offset}


async def get_review_filter_options(db: AsyncSession, tid: uuid.UUID) -> dict:
    """Facet lists for the queue filters.

    Only values that actually occur in this tenant's job-linked reviews are
    returned, so a filter can never be set to something that yields an
    unexplained empty list. Mirrors the `available_filters` shape the team
    directory endpoint already uses.
    """
    techs = (await db.execute(text(
        "SELECT DISTINCT ptm.id, ptm.full_name FROM customer_reviews cr "
        "JOIN service_jobs sj ON sj.id = cr.job_id "
        "JOIN provider_team_members ptm ON ptm.id = cr.staff_member_id "
        "WHERE cr.tenant_id = :tid AND cr.status != 'deleted' "
        "ORDER BY ptm.full_name"
    ), {"tid": str(tid)})).fetchall()

    services = (await db.execute(text(
        "SELECT DISTINCT sj.offering_id AS id, "
        "COALESCE(ts.tenant_display_name, ms.service_name, 'Service') AS name "
        "FROM customer_reviews cr "
        "JOIN service_jobs sj ON sj.id = cr.job_id "
        "LEFT JOIN tenant_services ts ON ts.id = sj.offering_id "
        "LEFT JOIN master_services ms ON ms.id = ts.master_service_id "
        "WHERE cr.tenant_id = :tid AND cr.status != 'deleted' AND sj.offering_id IS NOT NULL "
        "ORDER BY name"
    ), {"tid": str(tid)})).fetchall()

    return {
        "technicians": [{"id": str(t.id), "name": t.full_name} for t in techs],
        "services": [{"id": str(s.id), "name": s.name} for s in services],
        "moderation_statuses": ["open", "reviewed", "dismissed", "actioned"],
    }


async def get_reviews_kpis(db: AsyncSession, tid: uuid.UUID) -> dict:
    """All server-side, real -- never a fabricated zero on partial failure
    (caller wraps each module independently)."""
    row = (await db.execute(text(
        "SELECT count(DISTINCT cr.id) AS total, "
        "avg(cr.overall_rating) AS avg_rating, "
        "count(DISTINCT cr.id) FILTER (WHERE cr.overall_rating <= 2) AS low_ratings, "
        "count(DISTINCT cr.id) FILTER (WHERE rr.id IS NULL) AS unanswered, "
        "count(DISTINCT cr.id) FILTER (WHERE rr.id IS NOT NULL) AS answered, "
        "count(DISTINCT cr.id) FILTER (WHERE rf.id IS NOT NULL) AS flagged "
        "FROM customer_reviews cr "
        "JOIN service_jobs sj ON sj.id = cr.job_id "
        "LEFT JOIN review_replies rr ON rr.review_id = cr.id "
        "LEFT JOIN review_flags rf ON rf.review_id = cr.id AND rf.status = 'open' "
        "WHERE cr.tenant_id = :tid AND cr.status != 'deleted'"
    ), {"tid": str(tid)})).fetchone()

    total = int(row.total or 0)
    answered = int(row.answered or 0)
    eligible = total  # every job-linked review is reply-eligible; no separate eligibility gate exists yet
    response_rate = round((answered / eligible) * 100, 1) if eligible else 0.0

    return {
        "reviews": total,
        "average_rating": round(float(row.avg_rating), 2) if row.avg_rating is not None else None,
        "response_rate": response_rate,
        "low_ratings": int(row.low_ratings or 0),
        "unanswered": int(row.unanswered or 0),
        "flagged": int(row.flagged or 0),
    }


async def get_rating_trend(db: AsyncSession, tid: uuid.UUID, days: int = 30) -> list[dict]:
    rows = (await db.execute(text(
        "SELECT cr.created_at::date AS day, avg(cr.overall_rating) AS avg_rating, count(*) AS review_count "
        "FROM customer_reviews cr JOIN service_jobs sj ON sj.id = cr.job_id "
        "WHERE cr.tenant_id = :tid AND cr.status != 'deleted' "
        "AND cr.created_at >= now() - make_interval(days => :days) "
        "GROUP BY cr.created_at::date ORDER BY day ASC"
    ), {"tid": str(tid), "days": days})).fetchall()
    return [{"date": r.day.isoformat(), "average_rating": round(float(r.avg_rating), 2), "review_count": int(r.review_count)} for r in rows]


async def get_rating_distribution(db: AsyncSession, tid: uuid.UUID) -> list[dict]:
    rows = (await db.execute(text(
        "SELECT cr.overall_rating AS rating, count(*) AS cnt "
        "FROM customer_reviews cr JOIN service_jobs sj ON sj.id = cr.job_id "
        "WHERE cr.tenant_id = :tid AND cr.status != 'deleted' GROUP BY cr.overall_rating"
    ), {"tid": str(tid)})).fetchall()
    counts = {r.rating: int(r.cnt) for r in rows}
    total = sum(counts.values())
    return [{
        "stars": s, "count": counts.get(s, 0),
        "percent": round((counts.get(s, 0) / total) * 100) if total else 0,
    } for s in (5, 4, 3, 2, 1)]


async def get_quality_signals(db: AsyncSession, tid: uuid.UUID) -> dict:
    """Only factual, computable metrics -- no fabricated sentiment/trust
    scores. SLA-met reuses the same 2-hour assignment-acceptance heuristic
    documented in home_services_dashboard_service._attention_queue (the only
    real SLA-adjacent signal in this codebase today); rework/complaint rates
    are computed from real customer_complaints rows."""
    completed = (await db.execute(text(
        "SELECT count(*) FROM service_jobs WHERE tenant_id=:tid AND status='completed'"
    ), {"tid": str(tid)})).scalar() or 0
    if not completed:
        return {"sla_met_percent": None, "rework_rate_percent": None, "complaint_after_completion_percent": None, "sample_size": 0}

    sla_at_risk = (await db.execute(text(
        "SELECT count(*) FROM service_jobs WHERE tenant_id=:tid AND status='assigned' "
        "AND updated_at < now() - interval '2 hours'"
    ), {"tid": str(tid)})).scalar() or 0
    complaints_after_completion = (await db.execute(text(
        "SELECT count(DISTINCT cc.job_id) FROM customer_complaints cc "
        "JOIN service_jobs sj ON sj.id = cc.job_id "
        "WHERE cc.tenant_id=:tid AND sj.status='completed'"
    ), {"tid": str(tid)})).scalar() or 0
    rework = (await db.execute(text(
        "SELECT count(*) FROM customer_complaints WHERE tenant_id=:tid AND complaint_type='service_quality'"
    ), {"tid": str(tid)})).scalar() or 0

    return {
        "sla_met_percent": round(max(0.0, (1 - (sla_at_risk / completed))) * 100, 1),
        "rework_rate_percent": round((rework / completed) * 100, 1),
        "complaint_after_completion_percent": round((complaints_after_completion / completed) * 100, 1),
        "sample_size": completed,
    }


async def get_review_detail(db: AsyncSession, tid: uuid.UUID, review_id: uuid.UUID) -> dict | None:
    row = (await db.execute(text(
        "SELECT cr.id, cr.review_number, cr.customer_id, cr.overall_rating, cr.review_title, "
        "cr.review_text, cr.status AS review_status, cr.created_at, "
        "sj.id AS job_id, sj.job_number, sj.status AS job_status, sj.city, sj.zipcode, "
        "sj.completion_data, sj.category_id, "
        "COALESCE(ts.tenant_display_name, ms.service_name, 'Service') AS service_name, "
        "cr.staff_member_id AS technician_id, ptm.full_name AS technician_name, "
        "rr.id AS reply_id, rr.reply_text, rr.status AS reply_status, rr.created_at AS reply_created_at, "
        "cc.id AS complaint_id, cc.complaint_number, cc.status AS complaint_status, "
        "cc.severity AS complaint_severity, cc.sla_status AS complaint_sla_status, "
        "si.invoice_number, si.payment_status "
        "FROM customer_reviews cr "
        "JOIN service_jobs sj ON sj.id = cr.job_id "
        "LEFT JOIN tenant_services ts ON ts.id = sj.offering_id "
        "LEFT JOIN master_services ms ON ms.id = ts.master_service_id "
        "LEFT JOIN provider_team_members ptm ON ptm.id = cr.staff_member_id "
        "LEFT JOIN review_replies rr ON rr.review_id = cr.id "
        # A job can carry several complaints and several invoices. Joining
        # them directly fanned this query out to multiple rows and the
        # trailing LIMIT 1 then picked an ARBITRARY one -- so the detail panel
        # could show a stale complaint while the list row (which already
        # de-duped via LATERAL) showed the current one. Both sides now agree
        # on "the most recent".
        "LEFT JOIN LATERAL ("
        "  SELECT id, complaint_number, status, severity, sla_status "
        "  FROM customer_complaints WHERE job_id = sj.id ORDER BY created_at DESC LIMIT 1"
        ") cc ON true "
        "LEFT JOIN LATERAL ("
        "  SELECT invoice_number, payment_status FROM service_invoices "
        "  WHERE job_id = sj.id ORDER BY created_at DESC LIMIT 1"
        ") si ON true "
        "WHERE cr.id = :rid AND cr.tenant_id = :tid AND cr.status != 'deleted' "
        "LIMIT 1"
    ), {"rid": str(review_id), "tid": str(tid)})).fetchone()
    if not row:
        return None

    flag = (await db.execute(text(
        "SELECT id, status, reason_code, reason_text, created_at FROM review_flags "
        "WHERE review_id = :rid ORDER BY created_at DESC LIMIT 1"
    ), {"rid": str(review_id)})).fetchone()

    events = (await db.execute(text(
        "SELECT event_type, actor_type, reason, created_at FROM review_events "
        "WHERE review_id = :rid ORDER BY created_at ASC"
    ), {"rid": str(review_id)})).fetchall()

    return {
        "review_id": str(row.id), "review_number": row.review_number,
        "customer_alias": _customer_alias(str(row.customer_id)),
        "rating": row.overall_rating, "title": row.review_title, "review_text": row.review_text,
        "review_status": row.review_status, "created_at": row.created_at.isoformat() if row.created_at else None,
        "job": {
            "job_id": str(row.job_id), "job_number": row.job_number, "status": row.job_status,
            "city": row.city, "zipcode": row.zipcode, "completion_data": row.completion_data,
            "service_name": row.service_name,
        },
        "technician": {"id": str(row.technician_id), "name": row.technician_name} if row.technician_id else None,
        "reply": {
            "reply_id": str(row.reply_id), "reply_text": row.reply_text, "status": row.reply_status,
            "created_at": row.reply_created_at.isoformat() if row.reply_created_at else None,
        } if row.reply_id else None,
        "complaint": {
            "complaint_id": str(row.complaint_id), "complaint_number": row.complaint_number,
            "status": row.complaint_status, "severity": row.complaint_severity,
            "sla_status": row.complaint_sla_status,
        } if row.complaint_id else None,
        "invoice": {"invoice_number": row.invoice_number, "payment_status": row.payment_status} if row.invoice_number else None,
        "moderation": {
            "flag_id": str(flag.id), "status": flag.status, "reason_code": flag.reason_code,
            "reason_text": flag.reason_text, "created_at": flag.created_at.isoformat() if flag.created_at else None,
        } if flag else None,
        "activity": [{
            "event_type": e.event_type, "actor_type": e.actor_type, "reason": e.reason,
            "occurred_at": e.created_at.isoformat() if e.created_at else None,
        } for e in events],
        "available_actions": (["REPLY"] if not row.reply_id else []) + (["REQUEST_MODERATION"] if not flag or flag.status != "open" else []),
    }
