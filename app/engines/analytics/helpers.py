"""Sprint 28 — Analytics helpers: response contract, filters, safe query."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta, date
from typing import Any

from app.engines.analytics.constants import (
    ERR_ANALYTICS_INVALID_DATE_RANGE, MAX_DATE_RANGE_DAYS, DEFAULT_DATE_RANGE_DAYS,
)

_utcnow = lambda: datetime.now(timezone.utc)


# ── Standard analytics response ───────────────────────────────────────────────

def analytics_ok(
    summary: dict | None = None,
    series: list | None = None,
    breakdown: list | None = None,
    top_items: list | None = None,
    filters_applied: dict | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    extra: dict | None = None,
) -> dict:
    """Return standardised analytics response envelope."""
    data: dict[str, Any] = {
        "summary":         summary or {},
        "series":          series or [],
        "breakdown":       breakdown or [],
        "top_items":       top_items or [],
        "filters_applied": filters_applied or {},
        "date_range": {
            "from": date_from.isoformat() if date_from else None,
            "to":   date_to.isoformat() if date_to else None,
        },
        "generated_at": _utcnow().isoformat(),
    }
    if extra:
        data.update(extra)
    return {"success": True, "data": data}


def null_metric(reason: str) -> None:
    """Return None for metrics that could not be computed."""
    return None


# ── Date range helpers ────────────────────────────────────────────────────────

def resolve_date_range(
    date_from_str: str | None,
    date_to_str: str | None,
) -> tuple[date, date]:
    """Parse and validate date range. Returns (date_from, date_to)."""
    today = _utcnow().date()

    if date_to_str:
        try:
            dt = date.fromisoformat(date_to_str)
        except ValueError:
            raise ValueError(ERR_ANALYTICS_INVALID_DATE_RANGE)
    else:
        dt = today

    if date_from_str:
        try:
            df = date.fromisoformat(date_from_str)
        except ValueError:
            raise ValueError(ERR_ANALYTICS_INVALID_DATE_RANGE)
    else:
        df = dt - timedelta(days=DEFAULT_DATE_RANGE_DAYS)

    if df > dt:
        raise ValueError(ERR_ANALYTICS_INVALID_DATE_RANGE)

    if (dt - df).days > MAX_DATE_RANGE_DAYS:
        raise ValueError(ERR_ANALYTICS_INVALID_DATE_RANGE)

    return df, dt


def date_range_to_datetimes(df: date, dt: date) -> tuple[datetime, datetime]:
    """Convert date range to UTC datetimes for DB timestamp comparisons."""
    from_dt = datetime(df.year, df.month, df.day, 0, 0, 0, tzinfo=timezone.utc)
    to_dt   = datetime(dt.year, dt.month, dt.day, 23, 59, 59, tzinfo=timezone.utc)
    return from_dt, to_dt


# ── Safe metric wrapper ───────────────────────────────────────────────────────

async def safe_metric(coro, default=None):
    """Await a coroutine; return default if any exception.

    Dashboard cards must not fail because one card fails.
    """
    try:
        return await coro
    except Exception:
        return default
