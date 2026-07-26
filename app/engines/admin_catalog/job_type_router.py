"""Admin Job Type CRUD + Blueprint Impact -- router.

Backs the approved Admin Catalog page's "Add Job Type" action and the
right-panel "Version & impact" / "Impact Report". Writes are super-admin only.
"""
import uuid

from fastapi import APIRouter, Depends, Query, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.admin_catalog.job_type_service import JobTypeService
from app.engines.admin_catalog.blueprint_impact_service import BlueprintImpactService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/catalog/job-types", tags=["Admin Catalog Job Types"])
impact_router = APIRouter(prefix="/v1/admin/catalog/blueprint-impact", tags=["Admin Catalog Blueprint Impact"])
draft_router = APIRouter(prefix="/v1/admin/catalog/blueprint", tags=["Admin Catalog Blueprint Draft"])
ENGINE_ID = "admin_catalog"


def _svc(db: AsyncSession = Depends(get_db), u: UserContext = Depends(get_current_user)) -> JobTypeService:
    return JobTypeService(db=db, actor_id=uuid.UUID(u.user_id) if u.user_id else None)


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("", response_model=ApiResponse[dict], summary="List job types")
async def list_job_types(r: Request, include_inactive: bool = Query(False),
                          u: UserContext = Depends(get_current_user),
                          s: JobTypeService = Depends(_svc)):
    data = await s.list_job_types(include_inactive)
    return ok({"items": data, "total": len(data)}, _rid(r), ENGINE_ID)


@router.post("", response_model=ApiResponse[dict], status_code=201, summary="Create a job type")
async def create_job_type(r: Request, payload: dict = Body(...),
                           u: UserContext = Depends(require_super_admin),
                           s: JobTypeService = Depends(_svc)):
    return ok(await s.create_job_type(payload), _rid(r), ENGINE_ID)


@router.put("/{job_type_id}", response_model=ApiResponse[dict], summary="Update a job type")
async def update_job_type(job_type_id: uuid.UUID, r: Request, payload: dict = Body(...),
                           u: UserContext = Depends(require_super_admin),
                           s: JobTypeService = Depends(_svc)):
    return ok(await s.update_job_type(job_type_id, payload), _rid(r), ENGINE_ID)


@impact_router.get("", response_model=ApiResponse[dict],
                   summary="Structured impact report of the most recent blueprint publish for a master service")
async def get_impact_report(r: Request, master_service_id: uuid.UUID = Query(...),
                            u: UserContext = Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)):
    return ok(await BlueprintImpactService(db).get_impact_report(master_service_id), _rid(r), ENGINE_ID)


@draft_router.get("/draft-status", response_model=ApiResponse[dict],
                  summary="Pending (unpublished) structural changes for a master service -- the real 'Draft changes · N' count")
async def get_draft_status(r: Request, master_service_id: uuid.UUID = Query(...),
                           u: UserContext = Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)):
    return ok(await BlueprintImpactService(db).get_draft_status(master_service_id), _rid(r), ENGINE_ID)


@draft_router.post("/publish", response_model=ApiResponse[dict],
                   summary="Publish pending structural changes as a new blueprint version")
async def publish_draft(r: Request, payload: dict = Body(...),
                        u: UserContext = Depends(require_super_admin),
                        db: AsyncSession = Depends(get_db)):
    master_service_id = uuid.UUID(payload["master_service_id"])
    actor_id = uuid.UUID(u.user_id) if u.user_id else None
    return ok(await BlueprintImpactService(db).publish_draft(master_service_id, actor_id), _rid(r), ENGINE_ID)
