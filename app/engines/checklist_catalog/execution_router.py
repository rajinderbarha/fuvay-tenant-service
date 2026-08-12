"""Checklist Catalog Engine — job-execution endpoints: staff response
capture/evidence/completion, tenant-admin read access, and a super-admin
authorised waiver endpoint. Templates/mappings authoring lives in
admin_router.py (platform catalog admin only).

Every route filters by the job's own tenant_id from the authenticated
user's context -- runtime checklist data is tenant-isolated the same way
the rest of the execution engine is.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import (
    get_current_user,
    require_customer,
    require_staff_or_technician_only,
    require_super_admin,
)
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.engines.checklist_catalog import service as svc
from app.engines.checklist_catalog import constants as c
from app.engines.checklist_catalog.models import JobChecklistInstance, JobChecklistResponse

staff_router = APIRouter(prefix="/v1/staff/service-jobs", tags=["checklist-catalog-staff"])
tenant_router = APIRouter(prefix="/v1/tenant/service-jobs", tags=["checklist-catalog-tenant"])
customer_router = APIRouter(prefix="/v1/customer/service-jobs", tags=["checklist-catalog-customer"])
admin_router = APIRouter(prefix="/v1/admin/checklist-instances", tags=["checklist-catalog-admin"])


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


async def _get_job(db: AsyncSession, job_id: uuid.UUID, tenant_id: uuid.UUID):
    from app.engines.final_records.models import ServiceJob
    res = await db.execute(select(ServiceJob).where(ServiceJob.id == job_id, ServiceJob.tenant_id == tenant_id))
    job = res.scalars().first()
    if not job:
        raise ServiceOSException("ERR_RECORD_NOT_FOUND", "Job not found.", status_code=404)
    return job


async def _instance_detail(db: AsyncSession, instance: JobChecklistInstance, customer_view: bool = False) -> dict:
    items = await svc._instance_items(db, instance)
    responses = {
        r.checklist_item_id: r for r in (await db.execute(
            select(JobChecklistResponse).where(JobChecklistResponse.job_checklist_instance_id == instance.id)
        )).scalars().all()
    }
    d = instance.to_dict()
    item_list = []
    for item in items:
        if customer_view and not item.customer_visible:
            continue
        idict = item.to_dict()
        resp = responses.get(item.id)
        idict["response"] = resp.to_dict() if resp else None
        item_list.append(idict)
    d["items"] = item_list
    return d


# ── Staff: list applicable instances for a job, resolve on demand ────────

@staff_router.get("/{job_id}/checklists")
async def staff_list_job_checklists(job_id: uuid.UUID, r: Request, user=Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    job = await _get_job(db, job_id, uuid.UUID(str(user.tenant_id)))
    mappings = await svc.get_applicable_mappings(db, job)
    instances = []
    for m in mappings:
        try:
            instance = await svc.ensure_instance(db, job, m)
        except ServiceOSException:
            continue
        instances.append(await _instance_detail(db, instance))
    await db.commit()
    return ok(instances, _rid(r), "staff_list_job_checklists")


async def _get_owned_instance(db: AsyncSession, instance_id: uuid.UUID, tenant_id: uuid.UUID) -> JobChecklistInstance:
    instance = await db.get(JobChecklistInstance, instance_id)
    if instance is None or instance.tenant_id != tenant_id:
        raise ServiceOSException("ERR_RECORD_NOT_FOUND", "Checklist instance not found.", status_code=404)
    return instance


@staff_router.post("/checklist-instances/{instance_id}/responses/{item_id}")
async def staff_save_response(
    instance_id: uuid.UUID, item_id: uuid.UUID, body: dict, r: Request,
    user=Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db),
):
    instance = await _get_owned_instance(db, instance_id, uuid.UUID(str(user.tenant_id)))
    response = await svc.save_response(
        db, instance, item_id, actor_user_id=uuid.UUID(str(user.user_id)), actor_role="TECHNICIAN",
        response_value=body.get("response_value"), evidence=body.get("evidence"),
    )
    await db.commit()
    return ok(response.to_dict(), _rid(r), "staff_save_response")


@staff_router.post("/checklist-instances/{instance_id}/complete")
async def staff_complete_instance(instance_id: uuid.UUID, r: Request, user=Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    instance = await _get_owned_instance(db, instance_id, uuid.UUID(str(user.tenant_id)))
    completed = await svc.complete_instance(db, instance, completed_by=uuid.UUID(str(user.user_id)))
    await db.commit()
    return ok(completed.to_dict(), _rid(r), "staff_complete_instance")


@staff_router.get("/checklist-instances/{instance_id}")
async def staff_get_instance(instance_id: uuid.UUID, r: Request, user=Depends(require_staff_or_technician_only), db: AsyncSession = Depends(get_db)):
    instance = await _get_owned_instance(db, instance_id, uuid.UUID(str(user.tenant_id)))
    return ok(await _instance_detail(db, instance), _rid(r), "staff_get_instance")


# ── Tenant admin: read-only ───────────────────────────────────────────────

@tenant_router.get("/{job_id}/checklists")
async def tenant_list_job_checklists(job_id: uuid.UUID, r: Request, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(JobChecklistInstance).where(
            JobChecklistInstance.job_id == job_id, JobChecklistInstance.tenant_id == uuid.UUID(str(user.tenant_id)),
        )
    )
    instances = res.scalars().all()
    out = [await _instance_detail(db, i) for i in instances]
    return ok(out, _rid(r), "tenant_list_job_checklists")


# ── Customer: only explicitly customer-visible items/evidence ───────────

@customer_router.get("/{job_id}/checklists")
async def customer_list_job_checklists(job_id: uuid.UUID, r: Request, user=Depends(require_customer), db: AsyncSession = Depends(get_db)):
    from app.engines.final_records.models import ServiceJob

    job = (await db.execute(
        select(ServiceJob).where(
            ServiceJob.id == job_id,
            ServiceJob.customer_id == uuid.UUID(str(user.user_id)),
        )
    )).scalar_one_or_none()
    if job is None:
        raise ServiceOSException("ERR_RECORD_NOT_FOUND", "Job not found.", status_code=404)

    res = await db.execute(
        select(JobChecklistInstance).where(
            JobChecklistInstance.job_id == job_id,
            JobChecklistInstance.tenant_id == job.tenant_id,
        )
    )
    instances = res.scalars().all()
    out = [await _instance_detail(db, i, customer_view=True) for i in instances]
    return ok(out, _rid(r), "customer_list_job_checklists")


# ── Platform admin: authorised, audited waiver ────────────────────────────

@admin_router.post("/{instance_id}/waive")
async def admin_waive_instance(instance_id: uuid.UUID, body: dict, r: Request, user=Depends(require_super_admin), db: AsyncSession = Depends(get_db)):
    instance = await db.get(JobChecklistInstance, instance_id)
    if instance is None:
        raise ServiceOSException("ERR_RECORD_NOT_FOUND", "Checklist instance not found.", status_code=404)
    waived = await svc.waive_instance(
        db, instance, waived_by=uuid.UUID(str(user.user_id)), reason=body.get("reason", ""), authorized=True,
    )
    await db.commit()
    return ok(waived.to_dict(), _rid(r), "admin_waive_instance")
