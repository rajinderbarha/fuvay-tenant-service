"""Sprint 21 — Home Service execution routers (staff + provider + customer + admin)."""
from __future__ import annotations
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from sqlalchemy import select

from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.schemas.base import ApiResponse, ok
from app.engines.execution.home_service_service import HomeServiceJobExecutionService
from app.exceptions import ServiceOSException

_svc = HomeServiceJobExecutionService()

# ── Staff router ──────────────────────────────────────────────────────────────
staff_router = APIRouter(prefix="/v1/staff/service-jobs", tags=["Sprint21-Staff-HomeService"])


async def _staff_member_id(user, db) -> uuid.UUID:
    """HS8 fix: `UserContext` has no `staff_member_id` field at all — every
    handler in this router called `(await _staff_member_id(user, db))`,
    which evaluated to `uuid.UUID("None")` and raised, making every
    technician status-transition/parts/notes/media endpoint a hard 500
    (confirmed live: POST .../on-the-way). Fixed by resolving the real
    `provider_team_members.id` from the logged-in user's `user_id`, same
    fix as `home_service_assignment/staff_router.py`."""
    from app.engines.home_service_assignment.staff_model import ProviderTeamMember
    res = await db.execute(
        select(ProviderTeamMember.id).where(
            ProviderTeamMember.user_id == uuid.UUID(str(user.user_id))
        )
    )
    row = res.scalars().first()
    if not row:
        raise ServiceOSException("STAFF_MEMBER_NOT_FOUND", "You are not registered as a technician on this account.", status_code=403)
    return row


class AcceptBody(BaseModel):
    pass


class RejectBody(BaseModel):
    reason: str


class ScheduleBody(BaseModel):
    scheduled_date: Optional[str] = None
    scheduled_time_window: Optional[str] = None


class NoteBody(BaseModel):
    note_text: str
    is_customer_visible: bool = False


class MediaBody(BaseModel):
    media_type: str
    file_url: str
    file_name: Optional[str] = None
    caption: Optional[str] = None
    is_customer_visible: bool = False


class CancelBody(BaseModel):
    reason: str


# HS8B — real parts request workflow
class PartsRequestBody(BaseModel):
    part_name: str
    quantity: int
    estimated_cost: float
    reason: str
    photo_ids: Optional[list] = None
    technician_note: Optional[str] = None
    customer_approval_required: bool = False


class PartsRejectBody(BaseModel):
    reason: Optional[str] = None


# HS8B — single validated completion action.
# work_summary/collected_amount are Optional here (not required by
# Pydantic) so a missing value reaches the service layer's explicit
# checks, which raise the ticket's exact required error codes
# (WORK_SUMMARY_REQUIRED / COLLECTED_AMOUNT_REQUIRED) instead of a
# generic Pydantic VALIDATION_ERROR.
class CompleteJobBody(BaseModel):
    work_summary: Optional[str] = None
    collected_amount: Optional[float] = None
    payment_mode: str = "customer_pays_provider_directly"
    before_photo_ids: Optional[list] = None
    after_photo_ids: Optional[list] = None
    completion_photo_ids: Optional[list] = None
    customer_signature_id: Optional[str] = None
    technician_note: Optional[str] = None


@staff_router.post("/{job_id}/accept")
async def staff_accept_job(job_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.accept_job(db, job_id, uuid.UUID(str(user.tenant_id)), (await _staff_member_id(user, db)), uuid.UUID(str(user.user_id)), request_id=rid)
    await db.commit()
    return ok(result, rid, "staff-exec-accept")


@staff_router.post("/{job_id}/reject")
async def staff_reject_job(job_id: uuid.UUID, body: RejectBody, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.reject_job(db, job_id, uuid.UUID(str(user.tenant_id)), (await _staff_member_id(user, db)), uuid.UUID(str(user.user_id)), reason=body.reason, request_id=rid)
    await db.commit()
    return ok(result, rid, "staff-exec-reject")


@staff_router.post("/{job_id}/on-the-way")
async def staff_on_the_way(job_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.mark_on_the_way(db, job_id, uuid.UUID(str(user.tenant_id)), (await _staff_member_id(user, db)), uuid.UUID(str(user.user_id)), request_id=rid)
    await db.commit()
    return ok(result, rid, "staff-exec-on-way")


@staff_router.post("/{job_id}/reached-site")
async def staff_reached_site(job_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.mark_reached_site(db, job_id, uuid.UUID(str(user.tenant_id)), (await _staff_member_id(user, db)), uuid.UUID(str(user.user_id)), request_id=rid)
    await db.commit()
    return ok(result, rid, "staff-exec-reached")


@staff_router.post("/{job_id}/start-inspection")
async def staff_start_inspection(job_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.start_inspection(db, job_id, uuid.UUID(str(user.tenant_id)), (await _staff_member_id(user, db)), uuid.UUID(str(user.user_id)), request_id=rid)
    await db.commit()
    return ok(result, rid, "staff-exec-inspect-start")


@staff_router.post("/{job_id}/complete-inspection")
async def staff_complete_inspection(job_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.complete_inspection(db, job_id, uuid.UUID(str(user.tenant_id)), (await _staff_member_id(user, db)), uuid.UUID(str(user.user_id)), request_id=rid)
    await db.commit()
    return ok(result, rid, "staff-exec-inspect-done")


@staff_router.post("/{job_id}/start-service")
async def staff_start_service(job_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.start_service(db, job_id, uuid.UUID(str(user.tenant_id)), (await _staff_member_id(user, db)), uuid.UUID(str(user.user_id)), request_id=rid)
    await db.commit()
    return ok(result, rid, "staff-exec-service-start")


@staff_router.post("/{job_id}/work-done")
async def staff_work_done(job_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.mark_work_done(db, job_id, uuid.UUID(str(user.tenant_id)), (await _staff_member_id(user, db)), uuid.UUID(str(user.user_id)), request_id=rid)
    await db.commit()
    return ok(result, rid, "staff-exec-work-done")


@staff_router.post("/{job_id}/customer-not-available")
async def staff_customer_not_available(job_id: uuid.UUID, body: NoteBody, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.mark_customer_not_available(db, job_id, uuid.UUID(str(user.tenant_id)), (await _staff_member_id(user, db)), uuid.UUID(str(user.user_id)), notes=body.note_text, request_id=rid)
    await db.commit()
    return ok(result, rid, "staff-exec-not-avail")


@staff_router.post("/{job_id}/quote-required")
async def staff_quote_required(job_id: uuid.UUID, body: NoteBody, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.mark_quote_required(db, job_id, uuid.UUID(str(user.tenant_id)), (await _staff_member_id(user, db)), uuid.UUID(str(user.user_id)), notes=body.note_text, request_id=rid)
    await db.commit()
    return ok(result, rid, "staff-exec-quote-req")


@staff_router.post("/{job_id}/parts-required")
async def staff_parts_required(job_id: uuid.UUID, body: NoteBody, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.mark_parts_required(db, job_id, uuid.UUID(str(user.tenant_id)), (await _staff_member_id(user, db)), uuid.UUID(str(user.user_id)), notes=body.note_text, request_id=rid)
    await db.commit()
    return ok(result, rid, "staff-exec-parts-req")


@staff_router.post("/{job_id}/notes")
async def staff_add_note(job_id: uuid.UUID, body: NoteBody, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    note_type = body.note_text  # type annotation only; determine note type by endpoint
    result = await _svc.add_work_note(db, job_id, uuid.UUID(str(user.tenant_id)), (await _staff_member_id(user, db)), uuid.UUID(str(user.user_id)), note_text=body.note_text, is_customer_visible=body.is_customer_visible, request_id=rid)
    await db.commit()
    return ok(result, rid, "staff-exec-note")


@staff_router.post("/{job_id}/diagnosis-notes")
async def staff_add_diagnosis_note(job_id: uuid.UUID, body: NoteBody, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.add_diagnosis_note(db, job_id, uuid.UUID(str(user.tenant_id)), (await _staff_member_id(user, db)), uuid.UUID(str(user.user_id)), note_text=body.note_text, is_customer_visible=body.is_customer_visible, request_id=rid)
    await db.commit()
    return ok(result, rid, "staff-exec-diag-note")


@staff_router.post("/{job_id}/media")
async def staff_upload_media(job_id: uuid.UUID, body: MediaBody, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.upload_job_media(
        db, job_id, uuid.UUID(str(user.tenant_id)),
        (await _staff_member_id(user, db)), uuid.UUID(str(user.user_id)),
        media_type=body.media_type, file_url=body.file_url,
        file_name=body.file_name, caption=body.caption,
        is_customer_visible=body.is_customer_visible, request_id=rid,
    )
    await db.commit()
    return ok(result, rid, "staff-exec-media")


@staff_router.get("/{job_id}/timeline")
async def staff_get_timeline(job_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.get_job_timeline(db, job_id, uuid.UUID(str(user.tenant_id)))
    return ok(result, rid, "staff-exec-timeline")


# HS8B — real parts request creation
@staff_router.post("/{job_id}/parts-requests")
async def staff_create_parts_request(job_id: uuid.UUID, body: PartsRequestBody, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    staff_id = await _staff_member_id(user, db)
    result = await _svc.create_parts_request(
        db, job_id, uuid.UUID(str(user.tenant_id)), staff_id, uuid.UUID(str(user.user_id)),
        part_name=body.part_name, quantity=body.quantity, estimated_cost=body.estimated_cost,
        reason=body.reason, photo_ids=body.photo_ids, technician_note=body.technician_note,
        customer_approval_required=body.customer_approval_required, request_id=rid,
    )
    await db.commit()
    return ok(result, rid, "staff-exec-parts-create")


@staff_router.get("/{job_id}/parts-requests")
async def staff_list_parts_requests(job_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.list_parts_requests(db, job_id, uuid.UUID(str(user.tenant_id)))
    return ok({"job_id": str(job_id), "parts_requests": result}, rid, "staff-exec-parts-list")


# HS8B — single validated completion action
@staff_router.post("/{job_id}/complete")
async def staff_complete_job(job_id: uuid.UUID, body: CompleteJobBody, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    staff_id = await _staff_member_id(user, db)
    result = await _svc.complete_job(
        db, job_id, uuid.UUID(str(user.tenant_id)), staff_id, uuid.UUID(str(user.user_id)),
        work_summary=body.work_summary, collected_amount=body.collected_amount,
        payment_mode=body.payment_mode, before_photo_ids=body.before_photo_ids,
        after_photo_ids=body.after_photo_ids, completion_photo_ids=body.completion_photo_ids,
        customer_signature_id=body.customer_signature_id, technician_note=body.technician_note,
        request_id=rid,
    )
    await db.commit()
    return ok(result, rid, "staff-exec-complete")


# ── Provider router ───────────────────────────────────────────────────────────
provider_router = APIRouter(prefix="/v1/provider/service-jobs", tags=["Sprint21-Provider-HomeService"])


@provider_router.post("/{job_id}/cancel")
async def provider_cancel_job(job_id: uuid.UUID, body: CancelBody, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.cancel_job(db, job_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(user.user_id)), reason=body.reason, actor_role="provider", request_id=rid)
    await db.commit()
    return ok(result, rid, "provider-exec-cancel")


@provider_router.get("/{job_id}/execution-timeline")
async def provider_get_timeline(job_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.get_job_timeline(db, job_id, uuid.UUID(str(user.tenant_id)))
    return ok(result, rid, "provider-exec-timeline")


@provider_router.get("/{job_id}/notes")
async def provider_get_notes(job_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.get_job_notes(db, job_id, uuid.UUID(str(user.tenant_id)))
    return ok(result, rid, "provider-exec-notes")


@provider_router.get("/{job_id}/media")
async def provider_get_media(job_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.get_job_media(db, job_id, uuid.UUID(str(user.tenant_id)))
    return ok(result, rid, "provider-exec-media")


# HS8B — tenant/business parts request approval
@provider_router.get("/{job_id}/parts-requests")
async def provider_list_parts_requests(job_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.list_parts_requests(db, job_id, uuid.UUID(str(user.tenant_id)))
    return ok({"job_id": str(job_id), "parts_requests": result}, rid, "provider-exec-parts-list")


@provider_router.post("/{job_id}/parts-requests/{parts_request_id}/approve")
async def provider_approve_parts_request(job_id: uuid.UUID, parts_request_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.approve_parts_request(db, parts_request_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(user.user_id)), request_id=rid)
    await db.commit()
    return ok(result, rid, "provider-exec-parts-approve")


@provider_router.post("/{job_id}/parts-requests/{parts_request_id}/reject")
async def provider_reject_parts_request(job_id: uuid.UUID, parts_request_id: uuid.UUID, body: PartsRejectBody, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.reject_parts_request(db, parts_request_id, uuid.UUID(str(user.tenant_id)), uuid.UUID(str(user.user_id)), reason=body.reason, request_id=rid)
    await db.commit()
    return ok(result, rid, "provider-exec-parts-reject")


@provider_router.post("/{job_id}/parts-requests/{parts_request_id}/install")
async def provider_install_parts_request(job_id: uuid.UUID, parts_request_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    result = await _svc.install_parts_request(db, parts_request_id, uuid.UUID(str(user.tenant_id)), request_id=rid)
    await db.commit()
    return ok(result, rid, "provider-exec-parts-install")


# ── Customer tracking router ──────────────────────────────────────────────────
customer_router = APIRouter(prefix="/v1/customer/service-jobs", tags=["Sprint21-Customer-HomeService"])


@customer_router.get("/{job_id}/tracking")
async def customer_job_tracking(job_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    from sqlalchemy import select
    from app.engines.final_records.models import ServiceJob
    res = await db.execute(select(ServiceJob).where(ServiceJob.id == job_id, ServiceJob.customer_id == uuid.UUID(str(user.user_id))))
    job = res.scalars().first()
    if not job:
        from app.engines.execution.constants import ERR_RECORD_NOT_FOUND
        raise ValueError(ERR_RECORD_NOT_FOUND)
    notes = await _svc.get_job_notes(db, job_id, job.tenant_id, customer_only=True)
    media = await _svc.get_job_media(db, job_id, job.tenant_id, customer_only=True)
    timeline = await _svc.get_job_timeline(db, job_id, job.tenant_id)
    return ok({"job": job.to_dict(), "notes": notes, "media": media, "timeline": timeline}, rid, "customer-exec-tracking")


# ── Admin router ──────────────────────────────────────────────────────────────
admin_router = APIRouter(prefix="/v1/admin/service-jobs", tags=["Sprint21-Admin-HomeService"])


@admin_router.get("/{job_id}/execution-timeline")
async def admin_get_timeline(job_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    from sqlalchemy import select
    from app.engines.final_records.models import ServiceJob
    res = await db.execute(select(ServiceJob).where(ServiceJob.id == job_id))
    job = res.scalars().first()
    if not job:
        from app.engines.execution.constants import ERR_RECORD_NOT_FOUND
        raise ValueError(ERR_RECORD_NOT_FOUND)
    result = await _svc.get_job_timeline(db, job_id, job.tenant_id)
    return ok(result, rid, "admin-exec-timeline")


@admin_router.get("/{job_id}/notes")
async def admin_get_notes(job_id: uuid.UUID, r: Request, user=Depends(get_current_user), db=Depends(get_db)):
    rid = getattr(r.state, "request_id", "—")
    from sqlalchemy import select
    from app.engines.final_records.models import ServiceJob
    res = await db.execute(select(ServiceJob).where(ServiceJob.id == job_id))
    job = res.scalars().first()
    if not job:
        from app.engines.execution.constants import ERR_RECORD_NOT_FOUND
        raise ValueError(ERR_RECORD_NOT_FOUND)
    result = await _svc.get_job_notes(db, job_id, job.tenant_id)
    return ok(result, rid, "admin-exec-notes")
