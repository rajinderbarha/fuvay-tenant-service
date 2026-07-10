"""Sprint 28 — Admin Analytics Router (13 endpoints + report endpoints).

Swagger tags: Admin Analytics, Category Analytics, Financial Analytics,
              Quality Analytics, Complaint Analytics, Operational Alerts, Reports
"""
from __future__ import annotations
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.analytics.admin_analytics import AdminAnalyticsService
from app.engines.analytics.report_service import ReportService
from app.engines.analytics.constants import SCOPE_ADMIN
from app.schemas.base import ok

_svc = AdminAnalyticsService()
_rpt = ReportService()


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ── Admin Analytics Summary ───────────────────────────────────────────────────
admin_analytics_router = APIRouter(
    prefix="/v1/admin/analytics",
    tags=["Admin Analytics"],
    dependencies=[Depends(require_super_admin)],
)


@admin_analytics_router.get(
    "/summary",
    summary="Platform admin summary dashboard",
)
async def admin_analytics_summary(
    r: Request,
    date_from:   Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:     Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    category_id: Optional[str] = Query(None),
    tenant_id:   Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    data = await _svc.get_platform_summary(
        db, date_from=date_from, date_to=date_to,
        category_id=category_id, tenant_id=tenant_id,
    )
    return ok(data, _rid(r), "admin.analytics.summary")


@admin_analytics_router.get(
    "/category-performance",
    summary="Category-level performance metrics",
)
async def admin_category_performance(
    r: Request,
    date_from:   Optional[str] = Query(None),
    date_to:     Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    data = await _svc.get_category_performance(
        db, date_from=date_from, date_to=date_to, category_id=category_id,
    )
    return ok(data, _rid(r), "admin.analytics.category_performance")


@admin_analytics_router.get(
    "/categories/{category_id}",
    summary="Category-specific analytics",
)
async def admin_category_detail(
    category_id: str,
    r: Request,
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    data = await _svc.get_category_performance(
        db, date_from=date_from, date_to=date_to, category_id=category_id,
    )
    return ok(data, _rid(r), "admin.analytics.category_detail")


@admin_analytics_router.get(
    "/provider-performance",
    summary="Provider performance across all tenants",
)
async def admin_provider_performance(
    r: Request,
    date_from:   Optional[str] = Query(None),
    date_to:     Optional[str] = Query(None),
    category_id: Optional[str] = Query(None),
    tenant_id:   Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    data = await _svc.get_provider_performance(
        db, date_from=date_from, date_to=date_to,
        category_id=category_id, tenant_id=tenant_id,
    )
    return ok(data, _rid(r), "admin.analytics.provider_performance")


@admin_analytics_router.get(
    "/providers/{tenant_id}",
    summary="Single provider analytics",
)
async def admin_provider_detail(
    tenant_id: str,
    r: Request,
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    data = await _svc.get_provider_performance(
        db, date_from=date_from, date_to=date_to, tenant_id=tenant_id,
    )
    return ok(data, _rid(r), "admin.analytics.provider_detail")


@admin_analytics_router.get(
    "/financial-summary",
    tags=["Financial Analytics"],
    summary="Platform financial summary (invoices, payments, commissions, wallet)",
)
async def admin_financial_summary(
    r: Request,
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    data = await _svc.get_financial_summary(
        db, date_from=date_from, date_to=date_to, tenant_id=tenant_id,
    )
    return ok(data, _rid(r), "admin.analytics.financial")


@admin_analytics_router.get(
    "/quality-summary",
    tags=["Quality Analytics"],
    summary="Review and rating analytics",
)
async def admin_quality_summary(
    r: Request,
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    data = await _svc.get_quality_summary(
        db, date_from=date_from, date_to=date_to, tenant_id=tenant_id,
    )
    return ok(data, _rid(r), "admin.analytics.quality")


@admin_analytics_router.get(
    "/complaint-summary",
    tags=["Complaint Analytics"],
    summary="Complaints, disputes, refunds, rework analytics",
)
async def admin_complaint_summary(
    r: Request,
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    data = await _svc.get_complaint_summary(
        db, date_from=date_from, date_to=date_to, tenant_id=tenant_id,
    )
    return ok(data, _rid(r), "admin.analytics.complaints")


@admin_analytics_router.get(
    "/staff-performance",
    summary="Staff and technician performance analytics",
)
async def admin_staff_performance(
    r: Request,
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    data = await _svc.get_staff_performance(
        db, date_from=date_from, date_to=date_to, tenant_id=tenant_id,
    )
    return ok(data, _rid(r), "admin.analytics.staff")


@admin_analytics_router.get(
    "/operational-alerts",
    tags=["Operational Alerts"],
    summary="Platform-wide operational alerts and anomalies",
)
async def admin_operational_alerts(
    r: Request,
    db: AsyncSession = Depends(get_db),
):
    data = await _svc.get_operational_alerts(db)
    return ok(data, _rid(r), "admin.analytics.alerts")


# ── Admin Reports ─────────────────────────────────────────────────────────────
admin_reports_router = APIRouter(
    prefix="/v1/admin/reports",
    tags=["Reports"],
    dependencies=[Depends(require_super_admin)],
)


@admin_reports_router.get(
    "",
    summary="List available admin report definitions and recent runs",
)
async def admin_list_reports(
    r: Request,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    definitions = _rpt.list_reports(SCOPE_ADMIN)
    runs = await _rpt.list_report_runs(db, SCOPE_ADMIN, tenant_id=None,
                                        limit=limit, offset=offset)
    return ok({"definitions": definitions, "recent_runs": runs},
              _rid(r), "admin.reports.list")


@admin_reports_router.post(
    "/run",
    summary="Run an admin report (sync for ≤5000 rows)",
)
async def admin_run_report(
    body: dict,
    r: Request,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await _rpt.run_report(
        db,
        report_key=body.get("report_key", ""),
        scope=SCOPE_ADMIN,
        requested_by_user_id=uuid.UUID(u.user_id),
        tenant_id=None,
        filters=body.get("filters", {}),
        export_format=body.get("export_format"),
    )
    return ok(result, _rid(r), "admin.reports.run")


@admin_reports_router.get(
    "/{report_run_id}",
    summary="Get report run status and result",
)
async def admin_get_report_run(
    report_run_id: str,
    r: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await _rpt.get_report_run(
        db, uuid.UUID(report_run_id), SCOPE_ADMIN, tenant_id=None,
    )
    return ok(result, _rid(r), "admin.reports.get")
