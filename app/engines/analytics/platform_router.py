"""Platform Analytics Router — enterprise endpoints.

Prefix: /v1/admin/analytics
Tags: Platform Analytics
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_super_admin
from app.dependencies.db import get_db
from app.engines.analytics.platform_service import PlatformAnalyticsService
from app.schemas.base import ok

_svc = PlatformAnalyticsService()

platform_analytics_router = APIRouter(
    prefix="/v1/admin/analytics",
    tags=["Platform Analytics"],
    dependencies=[Depends(require_super_admin)],
)


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ── Platform Summary ──────────────────────────────────────────────────────────

@platform_analytics_router.get("/platform/summary")
async def get_platform_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    vertical: str | None = Query(None),
):
    data = await _svc.get_platform_summary(
        db, date_from=date_from, date_to=date_to,
        vertical=vertical,
    )
    return ok(data, _rid(request))


# ── Platform Trends ───────────────────────────────────────────────────────────

@platform_analytics_router.get("/platform/trends")
async def get_platform_trends(
    request: Request,
    db: AsyncSession = Depends(get_db),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    vertical: str | None = Query(None),
    granularity: str = Query("daily"),
):
    data = await _svc.get_platform_trends(
        db, date_from=date_from, date_to=date_to,
        vertical=vertical, granularity=granularity,
    )
    return ok(data, _rid(request))


# ── Operational Alerts ────────────────────────────────────────────────────────

@platform_analytics_router.get("/operational-alerts")
async def get_operational_alerts(
    request: Request,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
):
    data = await _svc.get_operational_alerts(db, limit=limit)
    return ok(data, _rid(request))


@platform_analytics_router.post("/operational-alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    data = await _svc.resolve_alert(db, alert_id)
    return ok(data, _rid(request))


@platform_analytics_router.post("/operational-alerts/{alert_id}/ignore")
async def ignore_alert(
    alert_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    data = await _svc.ignore_alert(db, alert_id)
    return ok(data, _rid(request))


# ── Categories ────────────────────────────────────────────────────────────────

@platform_analytics_router.get("/categories/performance")
async def get_category_performance(
    request: Request,
    db: AsyncSession = Depends(get_db),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    vertical: str | None = Query(None),
):
    data = await _svc.get_category_performance(
        db, date_from=date_from, date_to=date_to, vertical=vertical,
    )
    return ok(data, _rid(request))


# ── Providers ─────────────────────────────────────────────────────────────────

@platform_analytics_router.get("/providers/performance")
async def get_provider_performance(
    request: Request,
    db: AsyncSession = Depends(get_db),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    vertical: str | None = Query(None),
    sort_by: str = Query("completed_jobs"),
    limit: int = Query(50, ge=1, le=200),
    health_band: str | None = Query(None),
):
    data = await _svc.get_provider_performance(
        db, date_from=date_from, date_to=date_to,
        vertical=vertical, sort_by=sort_by, health_band=health_band, limit=limit,
    )
    return ok(data, _rid(request))


# ── Finance ───────────────────────────────────────────────────────────────────

@platform_analytics_router.get("/finance/summary")
async def get_finance_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    vertical: str | None = Query(None),
):
    data = await _svc.get_finance_summary(
        db, date_from=date_from, date_to=date_to, vertical=vertical,
    )
    return ok(data, _rid(request))


@platform_analytics_router.get("/finance/by-vertical")
async def get_finance_by_vertical(
    request: Request,
    db: AsyncSession = Depends(get_db),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
):
    data = await _svc.get_finance_by_vertical(db, date_from=date_from, date_to=date_to)
    return ok(data, _rid(request))


# ── Quality ───────────────────────────────────────────────────────────────────

@platform_analytics_router.get("/quality/summary")
async def get_quality_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    vertical: str | None = Query(None),
):
    data = await _svc.get_quality_summary(
        db, date_from=date_from, date_to=date_to, vertical=vertical,
    )
    return ok(data, _rid(request))


# ── Complaints ────────────────────────────────────────────────────────────────

@platform_analytics_router.get("/complaints/summary")
async def get_complaints_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    vertical: str | None = Query(None),
):
    data = await _svc.get_complaints_summary(
        db, date_from=date_from, date_to=date_to, vertical=vertical,
    )
    return ok(data, _rid(request))


@platform_analytics_router.get("/complaints/breakdown")
async def get_complaints_breakdown(
    request: Request,
    db: AsyncSession = Depends(get_db),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    vertical: str | None = Query(None),
):
    data = await _svc.get_complaints_breakdown(
        db, date_from=date_from, date_to=date_to, vertical=vertical,
    )
    return ok(data, _rid(request))


# ── Geography ─────────────────────────────────────────────────────────────────

@platform_analytics_router.get("/geography/summary")
async def get_geography_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    vertical: str | None = Query(None),
    city: str | None = Query(None),
    state: str | None = Query(None),
):
    data = await _svc.get_geography_summary(
        db, date_from=date_from, date_to=date_to, vertical=vertical,
        city=city, state=state,
    )
    return ok(data, _rid(request))


# ── Customers ─────────────────────────────────────────────────────────────────

@platform_analytics_router.get("/customers/summary")
async def get_customer_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    vertical: str | None = Query(None),
):
    data = await _svc.get_customer_summary(
        db, date_from=date_from, date_to=date_to, vertical=vertical,
    )
    return ok(data, _rid(request))

