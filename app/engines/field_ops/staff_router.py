"""Field Ops Engine — Staff App Router (Step 6).
Logged-in staff context only — staff can never pass staff_id manually."""
import uuid
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.field_ops.service import FieldOpsService
from app.exceptions import ServiceOSException
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/staff/me/jobs", tags=["Staff Jobs"])
ENGINE_ID = "field_ops"


def _svc(r: Request, db: AsyncSession = Depends(get_db),
         u: UserContext = Depends(get_current_user)) -> FieldOpsService:
    # Deliberately narrower than require_technician (which also allows
    # tenant_owner/super_admin) — this is a staff/technician *self-service* app
    # section, not a tenant-oversight one (tenant_owner already has /v1/jobs for
    # that). The real seeded role is "technician", not "staff"; a bare
    # `u.role != "staff"` check here previously rejected every real account.
    if u.role not in ("staff", "technician"):
        raise ServiceOSException("STAFF_ACCESS_DENIED",
            "This endpoint is for staff/technician accounts only.", status_code=403)
    return FieldOpsService(db=db, request_id=getattr(r.state, "request_id", "—"),
                            actor_id=uuid.UUID(u.user_id) if u.user_id else None,
                            actor_role=u.role,
                            actor_tenant_id=uuid.UUID(u.tenant_id) if u.tenant_id else None)


def _rid(r): return getattr(r.state, "request_id", "—")


@router.get("", summary="Step 6: My assigned jobs", response_model=ApiResponse[dict])
async def my_jobs(r: Request,
                   tenant_id: uuid.UUID = Query(...),
                   job_status: str | None = Query(None, alias="status"),
                   limit: int = Query(50, ge=1, le=200),
                   cursor: str | None = Query(None),
                   s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.list_jobs(tenant_id, job_status, s.actor_id, limit, cursor), _rid(r), ENGINE_ID)


@router.get("/{job_id}", summary="Step 6: My assigned job detail", response_model=ApiResponse[dict])
async def my_job_detail(job_id: uuid.UUID, r: Request,
                         s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_job(job_id), _rid(r), ENGINE_ID)


@router.post("/{job_id}/accept", summary="Step 6: Accept my assigned job", response_model=ApiResponse[dict])
async def accept(job_id: uuid.UUID, r: Request,
                  s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.accept_job(job_id, body.get("notes")), _rid(r), ENGINE_ID)


@router.post("/{job_id}/reject-assignment", summary="Step 6: Reject my assigned job — reason required",
             response_model=ApiResponse[dict])
async def reject(job_id: uuid.UUID, r: Request,
                  s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    return ok(await s.reject_assignment(job_id, body.get("reason")), _rid(r), ENGINE_ID)


@router.put("/{job_id}/status", summary="Step 6: Update status of my assigned job",
            response_model=ApiResponse[dict])
async def update_status(job_id: uuid.UUID, r: Request,
                         s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    data = await s.update_status(job_id, body["to_status"], body.get("reason"),
                                  body.get("latitude"), body.get("longitude"))
    return ok(data, _rid(r), ENGINE_ID)


# ── Step 8: Staff checklist aliases ──────────────────────────────────────────
@router.get("/{job_id}/checklist", summary="Step 8: My assigned job's checklist",
            response_model=ApiResponse[dict])
async def my_job_checklist(job_id: uuid.UUID, r: Request,
                            s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.get_job_checklist_items(job_id), _rid(r), ENGINE_ID)


@router.post("/{job_id}/checklist/start", summary="Step 8: Start my assigned job's checklist",
             response_model=ApiResponse[dict])
async def my_job_checklist_start(job_id: uuid.UUID, r: Request,
                                  s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.start_job_checklist(job_id), _rid(r), ENGINE_ID)


@router.put("/{job_id}/checklist/items/{item_id}",
            summary="Step 8: Mark a checklist item complete/incomplete on my assigned job",
            response_model=ApiResponse[dict])
async def my_job_checklist_item(job_id: uuid.UUID, item_id: uuid.UUID, r: Request,
                                 s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    body = await r.json()
    data = await s.update_job_checklist_item(
        job_id, item_id, body.get("is_completed", True), body.get("notes"), body.get("photo_urls"))
    return ok(data, _rid(r), ENGINE_ID)


@router.post("/{job_id}/checklist/complete", summary="Step 8: Complete my assigned job's checklist",
             response_model=ApiResponse[dict])
async def my_job_checklist_complete(job_id: uuid.UUID, r: Request,
                                     s: FieldOpsService = Depends(_svc)) -> ApiResponse[dict]:
    return ok(await s.complete_job_checklist(job_id), _rid(r), ENGINE_ID)
