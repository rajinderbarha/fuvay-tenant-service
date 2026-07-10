"""Platform Command Center Dashboard — Admin Router."""
from __future__ import annotations
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import UserContext
from app.dependencies.db import get_db
from app.core.permissions import P, require_permission
from app.core.audit import record_platform_audit
from app.schemas.base import ok
from app.engines.dashboard_command_center.service import DashboardCommandCenterService

router = APIRouter(prefix="/v1/admin/dashboard", tags=["Platform Command Center"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(require_permission(P.DASHBOARD_READ))) -> DashboardCommandCenterService:
    return DashboardCommandCenterService(
        db=db, actor_id=uuid.UUID(u.user_id) if u.user_id else None,
        actor_role=u.role, request_id=_rid(r))


@router.get("/executive-summary", summary="Executive KPI summary")
async def executive_summary(r: Request, s: DashboardCommandCenterService = Depends(_svc)):
    return ok(await s.get_executive_summary(), _rid(r), "dashboard_command_center")


@router.get("/platform-health", summary="Platform health score")
async def platform_health(r: Request, s: DashboardCommandCenterService = Depends(_svc)):
    return ok(await s.get_platform_health(), _rid(r), "dashboard_command_center")


@router.get("/finance-snapshot", summary="Finance snapshot (platform revenue vs provider direct value)")
async def finance_snapshot(r: Request, date_from: Optional[str] = Query(None), date_to: Optional[str] = Query(None),
                            vertical: Optional[str] = Query(None), db: AsyncSession = Depends(get_db),
                            u: UserContext = Depends(require_permission(P.DASHBOARD_FINANCE_READ))):
    svc = DashboardCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.get_finance_snapshot(date_from, date_to, vertical), _rid(r), "dashboard_command_center")


@router.get("/tenant-lifecycle", summary="Tenant lifecycle snapshot")
async def tenant_lifecycle(r: Request, s: DashboardCommandCenterService = Depends(_svc)):
    return ok(await s.get_tenant_lifecycle(), _rid(r), "dashboard_command_center")


@router.get("/home-services-summary", summary="Home Services vertical summary (shown as its own dashboard section)")
async def home_services_summary(r: Request, s: DashboardCommandCenterService = Depends(_svc)):
    return ok(await s.get_home_services_summary(), _rid(r), "dashboard_command_center")


@router.get("/operations-snapshot", summary="Operations snapshot")
async def operations_snapshot(r: Request, vertical: Optional[str] = Query(None),
                               db: AsyncSession = Depends(get_db),
                               u: UserContext = Depends(require_permission(P.DASHBOARD_OPERATIONS_READ))):
    svc = DashboardCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.get_operations_snapshot(vertical), _rid(r), "dashboard_command_center")


@router.get("/live-operations", summary="Live operations board")
async def live_operations(r: Request, limit: int = Query(30, le=200),
                           db: AsyncSession = Depends(get_db),
                           u: UserContext = Depends(require_permission(P.DASHBOARD_OPERATIONS_READ))):
    svc = DashboardCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.get_live_operations(limit), _rid(r), "dashboard_command_center")


@router.get("/trends", summary="Trend charts")
async def trends(r: Request, date_from: Optional[str] = Query(None), date_to: Optional[str] = Query(None),
                  vertical: Optional[str] = Query(None), s: DashboardCommandCenterService = Depends(_svc)):
    return ok(await s.get_trends(date_from, date_to, vertical), _rid(r), "dashboard_command_center")


@router.get("/action-queue", summary="Pending admin action queue")
async def action_queue(r: Request, limit: int = Query(50, le=500),
                        db: AsyncSession = Depends(get_db),
                        u: UserContext = Depends(require_permission(P.DASHBOARD_ACTION_QUEUE_MANAGE))):
    svc = DashboardCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.get_action_queue(limit), _rid(r), "dashboard_command_center")


@router.post("/action-queue/{action_id}/resolve", summary="Resolve an action queue item")
async def resolve_action(action_id: str, r: Request, db: AsyncSession = Depends(get_db),
                          u: UserContext = Depends(require_permission(P.DASHBOARD_ACTION_QUEUE_MANAGE))):
    body = await r.json() if r.headers.get("content-length") not in (None, "0") else {}
    svc = DashboardCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    result = await svc.resolve_action(action_id, body.get("reason"))
    await record_platform_audit(db, operation="dashboard.action_resolved", engine_id="dashboard_command_center",
                                 entity_id=action_id, actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role)
    return ok(result, _rid(r), "dashboard_command_center")


@router.post("/action-queue/{action_id}/snooze", summary="Snooze an action queue item")
async def snooze_action(action_id: str, r: Request, db: AsyncSession = Depends(get_db),
                         u: UserContext = Depends(require_permission(P.DASHBOARD_ACTION_QUEUE_MANAGE))):
    body = await r.json() if r.headers.get("content-length") not in (None, "0") else {}
    svc = DashboardCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    result = await svc.snooze_action(action_id, body.get("hours", 24))
    await record_platform_audit(db, operation="dashboard.action_snoozed", engine_id="dashboard_command_center",
                                 entity_id=action_id, actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role)
    return ok(result, _rid(r), "dashboard_command_center")


@router.post("/action-queue/{action_id}/assign", summary="Assign an action queue item")
async def assign_action(action_id: str, r: Request, db: AsyncSession = Depends(get_db),
                         u: UserContext = Depends(require_permission(P.DASHBOARD_ACTION_QUEUE_MANAGE))):
    body = await r.json()
    svc = DashboardCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    result = await svc.assign_action(action_id, body["assigned_to_user_id"])
    await record_platform_audit(db, operation="dashboard.action_assigned", engine_id="dashboard_command_center",
                                 entity_id=action_id, actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role)
    return ok(result, _rid(r), "dashboard_command_center")


@router.get("/engine-health", summary="System/engine health panel")
async def engine_health(r: Request, db: AsyncSession = Depends(get_db),
                         u: UserContext = Depends(require_permission(P.DASHBOARD_ENGINE_HEALTH_READ))):
    svc = DashboardCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.get_engine_health(), _rid(r), "dashboard_command_center")


@router.get("/at-risk-tenants", summary="At-risk tenants panel")
async def at_risk_tenants(r: Request, limit: int = Query(50, le=500), s: DashboardCommandCenterService = Depends(_svc)):
    return ok(await s.get_at_risk_tenants(limit), _rid(r), "dashboard_command_center")


@router.get("/compliance-security", summary="Compliance & security panel")
async def compliance_security(r: Request, db: AsyncSession = Depends(get_db),
                               u: UserContext = Depends(require_permission(P.DASHBOARD_SECURITY_READ))):
    svc = DashboardCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.get_compliance_security(), _rid(r), "dashboard_command_center")


@router.get("/trust-quality", summary="Trust & quality snapshot")
async def trust_quality(r: Request, s: DashboardCommandCenterService = Depends(_svc)):
    return ok(await s.get_trust_quality(), _rid(r), "dashboard_command_center")


@router.get("/activity-feed", summary="Live activity feed")
async def activity_feed(r: Request, limit: int = Query(30, le=200),
                         db: AsyncSession = Depends(get_db),
                         u: UserContext = Depends(require_permission(P.DASHBOARD_ACTIVITY_READ))):
    svc = DashboardCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    return ok(await svc.get_activity_feed(limit), _rid(r), "dashboard_command_center")


@router.get("/category-performance", summary="Category performance snapshot")
async def category_performance(r: Request, date_from: Optional[str] = Query(None), date_to: Optional[str] = Query(None),
                                s: DashboardCommandCenterService = Depends(_svc)):
    return ok(await s.get_category_performance(date_from, date_to), _rid(r), "dashboard_command_center")


@router.post("/refresh", summary="Trigger a dashboard refresh (audited)")
async def refresh(r: Request, db: AsyncSession = Depends(get_db),
                   u: UserContext = Depends(require_permission(P.DASHBOARD_READ))):
    await record_platform_audit(db, operation="dashboard.refreshed", engine_id="dashboard_command_center",
                                 actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role)
    return ok({"refreshed": True}, _rid(r), "dashboard_command_center")


@router.post("/export-snapshot", summary="Export a dashboard snapshot (audited)")
async def export_snapshot(r: Request, db: AsyncSession = Depends(get_db),
                           u: UserContext = Depends(require_permission(P.DASHBOARD_EXPORT))):
    svc = DashboardCommandCenterService(db, uuid.UUID(u.user_id) if u.user_id else None, u.role, _rid(r))
    result = await svc.export_snapshot()
    await record_platform_audit(db, operation="dashboard.exported", engine_id="dashboard_command_center",
                                 entity_id=result["snapshot_id"], actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role)
    return ok(result, _rid(r), "dashboard_command_center")
