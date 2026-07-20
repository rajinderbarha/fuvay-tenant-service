"""Sprint 28 — Provider Analytics Router (10 endpoints).

Rules:
- tenant_id comes from token ONLY — never from query params
- Provider cannot access admin analytics endpoints
- Provider cannot see another tenant's data
"""
from __future__ import annotations
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.core.permissions import require_mutation_access_scope
from app.engines.analytics.provider_analytics import ProviderAnalyticsService
from app.engines.analytics.report_service import ReportService
from app.engines.analytics.constants import SCOPE_PROVIDER, ERR_ANALYTICS_ACCESS_DENIED
from app.schemas.base import ok

_svc = ProviderAnalyticsService()
_rpt = ReportService()


def _tid(u: UserContext) -> uuid.UUID:
    """Extract tenant_id from token. Raises if missing."""
    if not u.tenant_id:
        raise ValueError(ERR_ANALYTICS_ACCESS_DENIED)
    return uuid.UUID(u.tenant_id)


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ── Provider Analytics ────────────────────────────────────────────────────────
provider_analytics_router = APIRouter(
    prefix="/v1/provider/analytics",
    tags=["Provider Analytics"],
)


@provider_analytics_router.get(
    "/summary",
    summary="Provider dashboard summary (own tenant only)",
)
async def provider_analytics_summary(
    r: Request,
    date_from: Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    date_to:   Optional[str] = Query(None, description="ISO date YYYY-MM-DD"),
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tid(u)
    data = await _svc.get_provider_dashboard(
        db, tenant_id=tenant_id, date_from=date_from, date_to=date_to,
    )
    return ok(data, _rid(r), "provider.analytics.summary")


@provider_analytics_router.get(
    "/operational-summary",
    summary="Provider operational metrics (jobs, appointments, leads)",
)
async def provider_operational_summary(
    r: Request,
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tid(u)
    data = await _svc.get_provider_dashboard(
        db, tenant_id=tenant_id, date_from=date_from, date_to=date_to,
    )
    return ok(data, _rid(r), "provider.analytics.operational")


@provider_analytics_router.get(
    "/financial-summary",
    tags=["Financial Analytics"],
    summary="Provider financial summary (own invoices, wallet, commission)",
)
async def provider_financial_summary(
    r: Request,
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tid(u)
    data = await _svc.get_provider_financial_summary(
        db, tenant_id=tenant_id, date_from=date_from, date_to=date_to,
    )
    return ok(data, _rid(r), "provider.analytics.financial")


@provider_analytics_router.get(
    "/staff-performance",
    summary="Provider staff/technician performance (own staff only)",
)
async def provider_staff_performance(
    r: Request,
    date_from:       Optional[str] = Query(None),
    date_to:         Optional[str] = Query(None),
    staff_member_id: Optional[str] = Query(None),
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tid(u)
    data = await _svc.get_provider_staff_performance(
        db, tenant_id=tenant_id, date_from=date_from, date_to=date_to,
        staff_member_id=staff_member_id,
    )
    return ok(data, _rid(r), "provider.analytics.staff")


@provider_analytics_router.get(
    "/quality-summary",
    tags=["Quality Analytics"],
    summary="Provider reviews and rating analytics (own reviews only)",
)
async def provider_quality_summary(
    r: Request,
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tid(u)
    data = await _svc.get_provider_quality_summary(
        db, tenant_id=tenant_id, date_from=date_from, date_to=date_to,
    )
    return ok(data, _rid(r), "provider.analytics.quality")


@provider_analytics_router.get(
    "/complaint-summary",
    tags=["Complaint Analytics"],
    summary="Provider complaints/refunds/rework analytics",
)
async def provider_complaint_summary(
    r: Request,
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tid(u)
    data = await _svc.get_provider_complaint_summary(
        db, tenant_id=tenant_id, date_from=date_from, date_to=date_to,
    )
    return ok(data, _rid(r), "provider.analytics.complaints")


@provider_analytics_router.get(
    "/operational-alerts",
    tags=["Operational Alerts"],
    summary="Provider operational alerts (low wallet, open complaints, etc.)",
)
async def provider_operational_alerts(
    r: Request,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tid(u)
    data = await _svc.get_provider_alerts(db, tenant_id=tenant_id)
    return ok(data, _rid(r), "provider.analytics.alerts")


# ── Provider Reports ──────────────────────────────────────────────────────────
provider_reports_router = APIRouter(
    prefix="/v1/provider/reports",
    tags=["Reports"],
)


@provider_reports_router.get(
    "",
    summary="List available provider report definitions and recent runs",
)
async def provider_list_reports(
    r: Request,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    tenant_id = _tid(u)
    definitions = _rpt.list_reports(SCOPE_PROVIDER)
    runs = await _rpt.list_report_runs(db, SCOPE_PROVIDER,
                                        tenant_id=tenant_id, limit=limit, offset=offset)
    return ok({"definitions": definitions, "recent_runs": runs},
              _rid(r), "provider.reports.list")


@provider_reports_router.post(
    "/run",
    summary="Run a provider report (own data only, sync for ≤5000 rows)",
)
async def provider_run_report(
    body: dict,
    r: Request,
    u: UserContext = Depends(require_mutation_access_scope),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tid(u)
    result = await _rpt.run_report(
        db,
        report_key=body.get("report_key", ""),
        scope=SCOPE_PROVIDER,
        requested_by_user_id=uuid.UUID(u.user_id),
        tenant_id=tenant_id,
        filters=body.get("filters", {}),
        export_format=body.get("export_format"),
    )
    return ok(result, _rid(r), "provider.reports.run")


@provider_reports_router.get(
    "/{report_run_id}",
    summary="Get provider report run status and result",
)
async def provider_get_report_run(
    report_run_id: str,
    r: Request,
    u: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tid(u)
    result = await _rpt.get_report_run(
        db, uuid.UUID(report_run_id), SCOPE_PROVIDER, tenant_id=tenant_id,
    )
    return ok(result, _rid(r), "provider.reports.get")
