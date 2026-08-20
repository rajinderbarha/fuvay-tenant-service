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


@router.get("/{service_id}/job-types/{job_type_id}/workflow/step-review",
            response_model=ApiResponse[dict],
            summary="Coherence review of this job type's cross-app step definition")
async def review_workflow_steps(service_id: uuid.UUID, job_type_id: uuid.UUID, r: Request,
                                u: UserContext = Depends(get_current_user),
                                s: JobTypeBlueprintService = Depends(_svc)):
    """Non-fatal review: structural errors are already rejected on save, so this
    reports the judgement calls an admin may knowingly accept while drafting —
    e.g. no step maps to a job status (the sequence can never progress), or an
    app has no step of its own."""
    return ok(await s.review_workflow_steps(service_id, job_type_id), _rid(r), ENGINE_ID)


@router.get("/{service_id}/job-types/{job_type_id}/workflow/step-options",
            response_model=ApiResponse[dict],
            summary="Vocabularies the step builder may offer (canonical, not invented)")
async def workflow_step_options(r: Request, service_id: uuid.UUID, job_type_id: uuid.UUID,
                                u: UserContext = Depends(get_current_user)):
    """The builder must only offer values the API will accept. `job_statuses` is
    derived from the execution engine's own JOB_TRANSITIONS graph, so the picker
    can never drift from what a job can actually be."""
    from app.engines.admin_catalog.workflow_steps import (
        CANONICAL_JOB_STATUSES, OWNER_APPS, OWNER_ROLES,
    )
    return ok({
        "job_statuses": sorted(CANONICAL_JOB_STATUSES),
        "owner_apps": sorted(OWNER_APPS),
        "owner_roles": sorted(OWNER_ROLES),
    }, _rid(r), ENGINE_ID)


@router.put("/{service_id}/job-types/{job_type_id}/workflow", response_model=ApiResponse[dict],
            summary="Set this job type's workflow blueprint (structure/behavior, no amounts)")
async def set_workflow(service_id: uuid.UUID, job_type_id: uuid.UUID, r: Request,
                       payload: dict = Body(...),
                       u: UserContext = Depends(require_super_admin),
                       s: JobTypeBlueprintService = Depends(_svc)):
    return ok(await s.set_workflow(service_id, job_type_id, payload), _rid(r), ENGINE_ID)
