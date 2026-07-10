"""Sprint 17 — Customer Coaching Appointment Draft API (11 endpoints)."""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ApiResponse, ok
from app.engines.coaching_appointment.service import CoachingAppointmentFlowService

router = APIRouter(
    prefix="/v1/customer/coaching/appointment-drafts",
    tags=["Customer Coaching Appointment Drafts"],
)


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ── 1. Start draft ────────────────────────────────────────────────────────────
@router.post("", response_model=ApiResponse)
async def start_appointment_draft(
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    body = await r.json()
    customer_id   = uuid.UUID(user.user_id)
    ai_session_id = uuid.UUID(body["ai_session_id"]) if body.get("ai_session_id") else None
    svc    = CoachingAppointmentFlowService(db, _rid(r))
    result = await svc.start_appointment_draft(
        customer_id=customer_id,
        ai_session_id=ai_session_id,
        category_slug=body.get("category_slug", "coaching-center"),
        offering_slug=body["offering_slug"],
    )
    return ok(result, _rid(r), "coaching_appointment")


# ── 2. Get draft ──────────────────────────────────────────────────────────────
@router.get("/{draft_id}", response_model=ApiResponse)
async def get_appointment_draft(
    draft_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    customer_id = uuid.UUID(user.user_id)
    svc    = CoachingAppointmentFlowService(db, _rid(r))
    result = await svc.get_appointment_draft(draft_id, customer_id)
    return ok(result, _rid(r), "coaching_appointment")


# ── 3. Update draft fields ────────────────────────────────────────────────────
@router.put("/{draft_id}", response_model=ApiResponse)
async def update_draft_fields(
    draft_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    body        = await r.json()
    customer_id = uuid.UUID(user.user_id)
    svc    = CoachingAppointmentFlowService(db, _rid(r))
    result = await svc.update_draft_fields(draft_id, customer_id, body)
    return ok(result, _rid(r), "coaching_appointment")


# ── 4. Find bookable centers ──────────────────────────────────────────────────
@router.post("/{draft_id}/find-centers", response_model=ApiResponse)
async def find_bookable_centers(
    draft_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    customer_id = uuid.UUID(user.user_id)
    svc    = CoachingAppointmentFlowService(db, _rid(r))
    result = await svc.find_bookable_centers(draft_id, customer_id)
    return ok(result, _rid(r), "coaching_appointment")


# ── 5. Available slots ────────────────────────────────────────────────────────
@router.post("/{draft_id}/available-slots", response_model=ApiResponse)
async def get_available_slots(
    draft_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    body        = await r.json()
    customer_id = uuid.UUID(user.user_id)
    tenant_id   = uuid.UUID(body["tenant_id"]) if body.get("tenant_id") else None
    svc    = CoachingAppointmentFlowService(db, _rid(r))
    result = await svc.load_available_slots(
        draft_id=draft_id,
        customer_id=customer_id,
        tenant_id=tenant_id,
        date_str=body.get("date"),
    )
    return ok(result, _rid(r), "coaching_appointment")


# ── 6. Next available slots ───────────────────────────────────────────────────
@router.post("/{draft_id}/next-available-slots", response_model=ApiResponse)
async def find_next_available_slots(
    draft_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    body         = await r.json()
    customer_id  = uuid.UUID(user.user_id)
    svc     = CoachingAppointmentFlowService(db, _rid(r))
    result  = await svc.find_next_available_slots(
        draft_id=draft_id,
        customer_id=customer_id,
        search_days=int(body.get("search_days", 14)),
        preferred_date=body.get("preferred_date"),
    )
    return ok(result, _rid(r), "coaching_appointment")


# ── 7. Select slot ────────────────────────────────────────────────────────────
@router.post("/{draft_id}/select-slot", response_model=ApiResponse)
async def select_slot(
    draft_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    body        = await r.json()
    customer_id = uuid.UUID(user.user_id)
    svc    = CoachingAppointmentFlowService(db, _rid(r))
    result = await svc.select_slot(
        draft_id=draft_id,
        customer_id=customer_id,
        tenant_id=uuid.UUID(body["tenant_id"]),
        slot_date=body["slot_date"],
        start_time=body["start_time"],
        end_time=body["end_time"],
        mode=body.get("mode"),
        staff_member_id=uuid.UUID(body["staff_member_id"]) if body.get("staff_member_id") else None,
    )
    return ok(result, _rid(r), "coaching_appointment")


# ── 8. Fee estimate ───────────────────────────────────────────────────────────
@router.post("/{draft_id}/fee-estimate", response_model=ApiResponse)
async def get_fee_estimate(
    draft_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    customer_id = uuid.UUID(user.user_id)
    svc    = CoachingAppointmentFlowService(db, _rid(r))
    result = await svc.resolve_appointment_fee(draft_id, customer_id)
    return ok(result, _rid(r), "coaching_appointment")


# ── 9. Appointment summary ────────────────────────────────────────────────────
@router.post("/{draft_id}/summary", response_model=ApiResponse)
async def get_appointment_summary(
    draft_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    customer_id = uuid.UUID(user.user_id)
    svc    = CoachingAppointmentFlowService(db, _rid(r))
    result = await svc.build_appointment_summary(draft_id, customer_id)
    return ok(result, _rid(r), "coaching_appointment")


# ── 10. Confirm ───────────────────────────────────────────────────────────────
@router.post("/{draft_id}/confirm", response_model=ApiResponse,
             summary="Confirm appointment — creates CoachingAppointment record")
async def confirm_draft(
    draft_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.engines.final_records.creation_service import CoachingFinalCreationService
    customer_id     = uuid.UUID(user.user_id)
    idempotency_key = r.headers.get("idempotency-key")
    request_id      = _rid(r)
    svc = CoachingFinalCreationService(db=db)
    result = await svc.finalize(
        draft_id        = draft_id,
        customer_id     = customer_id,
        idempotency_key = idempotency_key,
        request_id      = request_id,
    )
    await db.commit()
    return ok(result, request_id, "coaching_appointment")


# ── 11. Cancel ────────────────────────────────────────────────────────────────
@router.post("/{draft_id}/cancel", response_model=ApiResponse)
async def cancel_draft(
    draft_id: uuid.UUID,
    r: Request,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    body        = await r.json()
    customer_id = uuid.UUID(user.user_id)
    svc    = CoachingAppointmentFlowService(db, _rid(r))
    result = await svc.cancel_draft(draft_id, customer_id, reason=body.get("reason"))
    return ok(result, _rid(r), "coaching_appointment")
