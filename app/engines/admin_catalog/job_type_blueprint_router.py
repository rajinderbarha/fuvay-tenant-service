"""Job-Type Blueprint admin router (migration 160) -- Job Type as a child
record of a Master Service + its workflow ownership. Writes are super-admin
only.
"""
import uuid

from fastapi import APIRouter, Depends, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.engines.admin_catalog.job_type_blueprint_service import JobTypeBlueprintService
from app.schemas.base import ApiResponse, ok

router = APIRouter(prefix="/v1/admin/master-services", tags=["Admin Master Service Job Types"])
ENGINE_ID = "admin_catalog"


def _svc(db: AsyncSession = Depends(get_db)) -> JobTypeBlueprintService:
    return JobTypeBlueprintService(db=db)


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


@router.get("/{service_id}/job-types", response_model=ApiResponse[dict],
            summary="List job types configured on this master service")
async def list_job_types(service_id: uuid.UUID, r: Request,
                          u: UserContext = Depends(get_current_user),
                          s: JobTypeBlueprintService = Depends(_svc)):
    return ok({"items": await s.list_job_types_for_service(service_id)}, _rid(r), ENGINE_ID)


@router.post("/{service_id}/job-types", response_model=ApiResponse[dict], status_code=201,
             summary="Add a job type to this master service")
async def add_job_type(service_id: uuid.UUID, r: Request, payload: dict = Body(...),
                        u: UserContext = Depends(require_super_admin),
                        s: JobTypeBlueprintService = Depends(_svc)):
    return ok(await s.add_job_type_to_service(service_id, payload), _rid(r), ENGINE_ID)


@router.delete("/{service_id}/job-types/{link_id}", response_model=ApiResponse[dict],
               summary="Remove a job type from this master service")
async def remove_job_type(service_id: uuid.UUID, link_id: uuid.UUID, r: Request,
                          u: UserContext = Depends(require_super_admin),
                          s: JobTypeBlueprintService = Depends(_svc)):
    return ok(await s.remove_job_type_from_service(link_id), _rid(r), ENGINE_ID)


@router.get("/{service_id}/job-types/{job_type_id}/workflow", response_model=ApiResponse[dict],
            summary="Get this job type's workflow blueprint (structure/behavior, no amounts)")
async def get_workflow(service_id: uuid.UUID, job_type_id: uuid.UUID, r: Request,
                       u: UserContext = Depends(get_current_user),
                       s: JobTypeBlueprintService = Depends(_svc)):
    return ok(await s.get_workflow(service_id, job_type_id), _rid(r), ENGINE_ID)


@router.put("/{service_id}/job-types/{job_type_id}/workflow", response_model=ApiResponse[dict],
            summary="Set this job type's workflow blueprint (structure/behavior, no amounts)")
async def set_workflow(service_id: uuid.UUID, job_type_id: uuid.UUID, r: Request,
                       payload: dict = Body(...),
                       u: UserContext = Depends(require_super_admin),
                       s: JobTypeBlueprintService = Depends(_svc)):
    return ok(await s.set_workflow(service_id, job_type_id, payload), _rid(r), ENGINE_ID)
