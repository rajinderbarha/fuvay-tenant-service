"""Backend-owned timers for every long-running Home Services job stage.

The client never decides when a stage became late.  Each transition snapshots
the applicable limit into the execution event, so a later policy or provider
schedule change cannot silently move the deadline of a job already in flight.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text

from app.engines.execution.models import ServiceJobExecutionEvent


DEFAULT_STAGE_LIMIT_MINUTES: dict[str, int] = {
    "on_the_way": 30,
    "reached_site": 45,
    "inspection_started": 120,
    "inspection_done": 120,
    "quote_required": 2880,
    "service_started": 480,
    "work_done": 1440,
    "customer_not_available": 240,
}

WAITING_ON: dict[str, str] = {
    "quote_required": "customer",
    "customer_not_available": "customer",
}


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _bounded_minutes(raw, default: int) -> int:
    try:
        return min(10080, max(1, int(raw)))
    except (TypeError, ValueError):
        return default


async def _stage_rule(db, job, status: str) -> tuple[int, str]:
    default = DEFAULT_STAGE_LIMIT_MINUTES[status]
    if status == "on_the_way":
        configured = (await db.execute(text(
            "SELECT buffer_minutes_between_jobs FROM tenant_booking_window_settings "
            "WHERE tenant_id=:tenant_id"
        ), {"tenant_id": str(job.tenant_id)})).scalar()
        # Zero is useful as a slot-spacing value, but not as a journey timer.
        # Give an explicitly zero-buffer provider a small operational window.
        return _bounded_minutes(configured if configured not in (None, 0) else default, default), "provider_travel_buffer"

    from app.engines.vertical_monetization.runtime_operations import (
        get_home_services_operations_policy,
    )
    policy = await get_home_services_operations_policy(db)
    overrides = getattr(policy, "job_stall_limit_minutes", None) or {}
    return _bounded_minutes(overrides.get(status), default), "platform_policy"


async def build_stage_timer_snapshot(
    db, job, status: str, *, entered_at: datetime | None = None,
) -> dict | None:
    """Create the immutable timer stored beside a real status transition."""
    if status not in DEFAULT_STAGE_LIMIT_MINUTES:
        return None
    entered = _aware(entered_at or datetime.now(timezone.utc))
    limit, source = await _stage_rule(db, job, status)
    deadline = entered + timedelta(minutes=limit)
    warning = entered + timedelta(minutes=max(1, round(limit * 0.75)))
    critical = deadline + timedelta(minutes=limit)
    return {
        "status": status,
        "entered_at": entered.isoformat(),
        "warning_at": warning.isoformat(),
        "deadline_at": deadline.isoformat(),
        "critical_at": critical.isoformat(),
        "limit_minutes": limit,
        "waiting_on": WAITING_ON.get(status, "provider"),
        "source": source,
    }


def _parse_datetime(value) -> datetime | None:
    if isinstance(value, datetime):
        return _aware(value)
    if isinstance(value, str):
        try:
            return _aware(datetime.fromisoformat(value.replace("Z", "+00:00")))
        except ValueError:
            return None
    return None


async def describe_stage_timer(db, job, *, now: datetime | None = None) -> dict:
    """Return a client-safe live timer derived from the latest transition."""
    server_now = _aware(now or datetime.now(timezone.utc))
    if job.status not in DEFAULT_STAGE_LIMIT_MINUTES:
        return {"active": False, "status": job.status, "state": "inactive",
                "server_time": server_now.isoformat()}

    event = (await db.execute(
        select(ServiceJobExecutionEvent).where(
            ServiceJobExecutionEvent.job_id == job.id,
            ServiceJobExecutionEvent.new_status == job.status,
            ServiceJobExecutionEvent.old_status != ServiceJobExecutionEvent.new_status,
        ).order_by(ServiceJobExecutionEvent.created_at.desc()).limit(1)
    )).scalars().first()
    stored = ((event.event_metadata or {}).get("stage_timer") if event else None) or {}
    entered = _parse_datetime(stored.get("entered_at"))
    if entered is None:
        entered = _aware(
            (event.created_at if event and event.created_at else None)
            or getattr(job, "updated_at", None)
            or getattr(job, "created_at", None)
            or server_now
        )
    limit, source = await _stage_rule(db, job, job.status)
    limit = _bounded_minutes(stored.get("limit_minutes"), limit)
    deadline = _parse_datetime(stored.get("deadline_at")) or entered + timedelta(minutes=limit)
    warning = _parse_datetime(stored.get("warning_at")) or entered + timedelta(minutes=max(1, round(limit * .75)))
    critical = _parse_datetime(stored.get("critical_at")) or deadline + timedelta(minutes=limit)
    if server_now >= critical:
        state = "critical"
    elif server_now >= deadline:
        state = "breached"
    elif server_now >= warning:
        state = "warning"
    else:
        state = "on_track"
    remaining = max(0, int((deadline - server_now).total_seconds()))
    overdue = max(0, int((server_now - deadline).total_seconds()))
    return {
        "active": True,
        "status": job.status,
        "state": state,
        "entered_at": entered.isoformat(),
        "warning_at": warning.isoformat(),
        "deadline_at": deadline.isoformat(),
        "critical_at": critical.isoformat(),
        "limit_minutes": limit,
        "remaining_seconds": remaining,
        "overdue_seconds": overdue,
        "waiting_on": stored.get("waiting_on") or WAITING_ON.get(job.status, "provider"),
        "source": stored.get("source") or source,
        "requires_provider_intervention": state in {"breached", "critical"},
        "server_time": server_now.isoformat(),
    }
