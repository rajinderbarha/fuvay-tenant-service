"""Analytics Engine — Router (10 endpoints)."""
import uuid
from datetime import date
from decimal import Decimal
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.analytics.service import AnalyticsService
from app.schemas.base import ApiResponse, ok

logger = structlog.get_logger("analytics.router")
router = APIRouter(prefix="/v1/analytics", tags=["Analytics Engine"])
ENGINE_ID = "analytics"

def _svc(r: Request, db: AsyncSession = Depends(get_db),
          u: UserContext = Depends(get_current_user)) -> AnalyticsService:
    return AnalyticsService(db=db, request_id=getattr(r.state,"request_id","—"),
                             actor_id=uuid.UUID(u.user_id) if u.user_id else None)
def _rid(r): return getattr(r.state,"request_id","—")

@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID, "name": "Analytics Engine", "version": "5.0.0",
            "endpoint_count": 10, "status": "active",
            "capabilities": ["event_ingestion","platform_kpis","tenant_metrics",
                             "event_stream","daily_rollups","idempotent_ingestion"]}

@router.post("/events/ingest", status_code=status.HTTP_202_ACCEPTED, response_model=ApiResponse[dict])
async def ingest_event(r: Request,
                        u: UserContext = Depends(require_super_admin),
                        s: AnalyticsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    tid = uuid.UUID(body["tenant_id"]) if body.get("tenant_id") else None
    aid = uuid.UUID(body["actor_id"]) if body.get("actor_id") else None
    return ok(await s.ingest_event(body["event_id"], tid, body["event_type"],
              body.get("engine_id","unknown"), body.get("entity_type"),
              body.get("entity_id"), aid, body.get("payload",{}),
              None), _rid(r), ENGINE_ID)

@router.get("/events/stream", response_model=ApiResponse[dict])
async def event_stream(r: Request,
                        tenant_id: uuid.UUID|None = Query(None),
                        event_type: str|None = Query(None),
                        limit: int = Query(50,ge=1,le=200),
                        cursor: str|None = Query(None),
                        u: UserContext = Depends(get_current_user),
                        s: AnalyticsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_event_stream(tenant_id, event_type, limit, cursor), _rid(r), ENGINE_ID)

@router.get("/platform/summary", response_model=ApiResponse[dict])
async def platform_summary(r: Request,
                            u: UserContext = Depends(require_super_admin),
                            s: AnalyticsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_platform_summary(), _rid(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/metrics", response_model=ApiResponse[dict])
async def tenant_metrics(tenant_id: uuid.UUID, r: Request,
                          days: int = Query(30,ge=1,le=365),
                          u: UserContext = Depends(get_current_user),
                          s: AnalyticsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_tenant_metrics(tenant_id, days), _rid(r), ENGINE_ID)

@router.get("/metrics/daily", response_model=ApiResponse[dict])
async def daily_metrics(r: Request,
                         metric_key: str = Query(...),
                         tenant_id: uuid.UUID|None = Query(None),
                         days: int = Query(30,ge=1,le=365),
                         u: UserContext = Depends(get_current_user),
                         s: AnalyticsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_daily_metrics(tenant_id, metric_key, days), _rid(r), ENGINE_ID)

@router.post("/metrics/daily/upsert", response_model=ApiResponse[dict])
async def upsert_daily(r: Request,
                        u: UserContext = Depends(require_super_admin),
                        s: AnalyticsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    tid = uuid.UUID(body["tenant_id"]) if body.get("tenant_id") else None
    mdate = date.fromisoformat(body["metric_date"])
    return ok(await s.upsert_daily_metric(tid, mdate, body["metric_key"],
              Decimal(str(body["value_num"])) if body.get("value_num") else None,
              body.get("value_json")), _rid(r), ENGINE_ID)
