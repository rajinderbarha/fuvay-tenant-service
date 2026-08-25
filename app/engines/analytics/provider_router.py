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
    # Each definition declares `allowed_filters` (category_id, offering_id,
    # staff_member_id, status ...) and the run endpoint validates them, but
    # nothing ever told a client what the VALID VALUES are — so the portal
    # offered no filters at all and every report ran unfiltered over all time.
    # These options come from the tenant's own rows, so a value offered here
    # always matches something.
    filter_options = await _provider_filter_options(db, tenant_id)
    return ok({"definitions": definitions, "recent_runs": runs,
               "filter_options": filter_options},
              _rid(r), "provider.reports.list")


async def _provider_filter_options(db: AsyncSession, tenant_id) -> dict:
    """Selectable values for the id-based report filters, for one tenant."""
    from sqlalchemy import text as _text

    if tenant_id is None:
        return {"offerings": [], "staff": [], "statuses": [], "categories": []}

    tid = {"tid": str(tenant_id)}

    offerings = (await db.execute(_text("""
        SELECT DISTINCT ms.id::text AS id, ms.service_name AS name
          FROM tenant_services ts
          JOIN master_services ms ON ms.id = ts.master_service_id
         WHERE ts.tenant_id = :tid AND ts.is_active = true AND ts.deleted_at IS NULL
         ORDER BY ms.service_name
    """), tid)).fetchall()

    categories = (await db.execute(_text("""
        SELECT DISTINCT sc.id::text AS id, sc.name AS name
          FROM tenant_services ts
          JOIN master_services ms ON ms.id = ts.master_service_id
          JOIN service_categories sc ON sc.id = ms.category_id
         WHERE ts.tenant_id = :tid AND ts.is_active = true AND ts.deleted_at IS NULL
         ORDER BY sc.name
    """), tid)).fetchall()

    staff = (await db.execute(_text("""
        SELECT id::text AS id,
               COALESCE(NULLIF(TRIM(full_name), ''), designation, 'Technician') AS name
          FROM provider_team_members
         WHERE tenant_id = :tid AND status = 'active'
         ORDER BY 2
    """), tid)).fetchall()

    # Built from the statuses this tenant's jobs are actually in, for the same
    # reason: a status nobody has can only ever return an empty report.
    statuses = (await db.execute(_text("""
        SELECT DISTINCT status FROM service_jobs
         WHERE tenant_id = :tid AND status IS NOT NULL ORDER BY status
    """), tid)).fetchall()

    def _lbl(v: str) -> str:
        return v.replace("_", " ").capitalize()

    return {
        "offerings":  [{"value": x.id, "label": x.name} for x in offerings],
        "categories": [{"value": x.id, "label": x.name} for x in categories],
        "staff":      [{"value": x.id, "label": x.name} for x in staff],
        "statuses":   [{"value": x.status, "label": _lbl(x.status)} for x in statuses],
    }


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
