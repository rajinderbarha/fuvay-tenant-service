"""Dispatch Engine — Router (10 endpoints)."""
import uuid
import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import P, require_permission
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.dispatch.service import DispatchService
from app.schemas.base import ApiResponse, ok

logger = structlog.get_logger("dispatch.router")
router = APIRouter(prefix="/v1/dispatch", tags=["Dispatch Engine"])
ENGINE_ID = "dispatch"

def _svc(r: Request, db: AsyncSession = Depends(get_db),
          u: UserContext = Depends(get_current_user)) -> DispatchService:
    return DispatchService(db=db, request_id=getattr(r.state,"request_id","—"),
                            actor_id=uuid.UUID(u.user_id) if u.user_id else None, actor_role=u.role)
def _rid(r): return getattr(r.state,"request_id","—")

@router.get("/meta", tags=["Engine Registry"])
async def engine_meta() -> dict:
    return {"engine_id": ENGINE_ID, "name": "Dispatch Engine", "version": "8.0.0",
            "endpoint_count": 10, "status": "active",
            "modes": ["manual","auto_assign","broadcast"],
            "capabilities": ["scoring","auto_assignment","broadcast","escalation",
                             "audit_trail","idempotent_dispatch"]}

@router.post("/jobs/{job_id}/dispatch", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[dict])
async def dispatch_job(job_id: str, r: Request,
                        u: UserContext = Depends(require_permission(P.TENANT_UPDATE)),
                        s: DispatchService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.dispatch_job(job_id, uuid.UUID(body["tenant_id"]),
              body.get("mode","auto_assign"),
              uuid.UUID(body["staff_id"]) if body.get("staff_id") else None,
              body.get("job_lat"), body.get("job_lng"),
              body.get("service_type_id","general")), _rid(r), ENGINE_ID)

@router.get("/jobs/{job_id}", response_model=ApiResponse[dict])
async def get_dispatch(job_id: str, r: Request,
                        u: UserContext = Depends(get_current_user),
                        s: DispatchService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_dispatch_record(job_id), _rid(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/records", response_model=ApiResponse[dict])
async def list_records(tenant_id: uuid.UUID, r: Request,
                        limit: int = Query(50,ge=1,le=200),
                        cursor: str | None = Query(None),
                        u: UserContext = Depends(get_current_user),
                        s: DispatchService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_dispatch_records(tenant_id, limit, cursor), _rid(r), ENGINE_ID)

@router.post("/jobs/{job_id}/accept", response_model=ApiResponse[dict])
async def accept_job(job_id: str, r: Request,
                      u: UserContext = Depends(get_current_user),
                      s: DispatchService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.accept_job(job_id, uuid.UUID(body["staff_id"])), _rid(r), ENGINE_ID)

@router.post("/jobs/{job_id}/reject", response_model=ApiResponse[dict])
async def reject_job(job_id: str, r: Request,
                      u: UserContext = Depends(get_current_user),
                      s: DispatchService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.reject_job(job_id, uuid.UUID(body["staff_id"]), body.get("reason")), _rid(r), ENGINE_ID)

@router.post("/jobs/{job_id}/reassign", response_model=ApiResponse[dict])
async def reassign(job_id: str, r: Request,
                    u: UserContext = Depends(require_permission(P.TENANT_UPDATE)),
                    s: DispatchService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.reassign_job(job_id, uuid.UUID(body["new_staff_id"]), body.get("reason","")), _rid(r), ENGINE_ID)

@router.get("/tenants/{tenant_id}/queue", response_model=ApiResponse[dict])
async def dispatch_queue(tenant_id: uuid.UUID, r: Request,
                          u: UserContext = Depends(get_current_user),
                          s: DispatchService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_dispatch_queue(tenant_id), _rid(r), ENGINE_ID)

@router.get("/jobs/{job_id}/scoring", response_model=ApiResponse[dict])
async def scoring_breakdown(job_id: str, r: Request,
                             u: UserContext = Depends(get_current_user),
                             s: DispatchService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_scoring_breakdown(job_id), _rid(r), ENGINE_ID)
