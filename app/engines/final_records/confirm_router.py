"""Sprint 19 — Customer Confirmation Endpoints.

POST /v1/customer/confirm/home-service-booking/{draft_id}
POST /v1/customer/confirm/coaching-appointment/{draft_id}
POST /v1/customer/confirm/real-estate-lead/{draft_id}

These endpoints convert confirmed chatbot drafts into final records.
Each call is idempotent — duplicate submissions return the same result.
"""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.schemas.base import ApiResponse, ok
from app.engines.final_records.constants import (
    ERR_DRAFT_NOT_FOUND, ERR_DRAFT_NOT_READY, ERR_ACCESS_DENIED,
    ERR_DUPLICATE_CONFIRMATION,
    ERR_SLOT_HOLD_MISSING, ERR_SLOT_HOLD_EXPIRED, ERR_SLOT_HOLD_ALREADY_CONVERTED,
)
from app.engines.final_records.creation_service import (
    HomeServiceFinalCreationService,
    CoachingFinalCreationService,
    RealEstateFinalCreationService,
)

router = APIRouter(
    prefix="/v1/customer/confirm",
    tags=["Customer Final Confirmation"],
)

_RID = lambda r: getattr(r.state, "request_id", "—")


class ConfirmRequest(BaseModel):
    customer_confirmation: bool = True


def _error_code(exc: ValueError) -> str:
    return str(exc)


# ── POST /confirm/home-service-booking/{draft_id} ────────────────────────────

@router.post(
    "/home-service-booking/{draft_id}",
    summary="Confirm home service booking draft → creates ServiceBooking + ServiceJob",
    response_model=ApiResponse,
)
async def confirm_home_service_booking(
    draft_id:        uuid.UUID,
    body:            ConfirmRequest,
    r:               Request,
    user:            UserContext  = Depends(get_current_user),
    db:              AsyncSession = Depends(get_db),
    idempotency_key: str | None  = Header(None, alias="Idempotency-Key"),
):
    customer_id = uuid.UUID(user.user_id)
    svc = HomeServiceFinalCreationService(db)
    try:
        result = await svc.finalize(
            draft_id        = draft_id,
            customer_id     = customer_id,
            idempotency_key = idempotency_key,
            request_id      = _RID(r),
        )
        await db.commit()
    except ValueError as exc:
        code = _error_code(exc)
        return ok({
            "success": False,
            "error": {"code": code, "message": _user_message(code)},
        }, _RID(r), "final_records")

    return ok({
        "record_type":    "booking",
        "booking_id":     result["booking_id"],
        "booking_number": result["booking_number"],
        "job_id":         result.get("job_id"),
        "job_number":     result.get("job_number"),
        "status":         result.get("status", "pending_assignment"),
        "idempotent":     result.get("idempotent", False),
        "message":        "Your booking is confirmed." if not result.get("idempotent") else "Already confirmed.",
    }, _RID(r), "final_records")


# ── POST /confirm/coaching-appointment/{draft_id} ───────────────────────────

@router.post(
    "/coaching-appointment/{draft_id}",
    summary="Confirm coaching appointment draft → creates CoachingAppointment",
    response_model=ApiResponse,
)
async def confirm_coaching_appointment(
    draft_id:        uuid.UUID,
    body:            ConfirmRequest,
    r:               Request,
    user:            UserContext  = Depends(get_current_user),
    db:              AsyncSession = Depends(get_db),
    idempotency_key: str | None  = Header(None, alias="Idempotency-Key"),
):
    customer_id = uuid.UUID(user.user_id)
    svc = CoachingFinalCreationService(db)
    try:
        result = await svc.finalize(
            draft_id        = draft_id,
            customer_id     = customer_id,
            idempotency_key = idempotency_key,
            request_id      = _RID(r),
        )
        await db.commit()
    except ValueError as exc:
        code = _error_code(exc)
        return ok({
            "success": False,
            "error": {"code": code, "message": _user_message(code)},
        }, _RID(r), "final_records")

    return ok({
        "record_type":        "appointment",
        "appointment_id":     result["appointment_id"],
        "appointment_number": result["appointment_number"],
        "status":             result.get("status", "confirmed"),
        "idempotent":         result.get("idempotent", False),
        "message":            "Your appointment is confirmed." if not result.get("idempotent") else "Already confirmed.",
    }, _RID(r), "final_records")


# ── POST /confirm/real-estate-lead/{draft_id} ────────────────────────────────

@router.post(
    "/real-estate-lead/{draft_id}",
    summary="Confirm real estate lead draft → creates RealEstateLead",
    response_model=ApiResponse,
)
async def confirm_real_estate_lead(
    draft_id:        uuid.UUID,
    body:            ConfirmRequest,
    r:               Request,
    user:            UserContext  = Depends(get_current_user),
    db:              AsyncSession = Depends(get_db),
    idempotency_key: str | None  = Header(None, alias="Idempotency-Key"),
):
    customer_id = uuid.UUID(user.user_id)
    svc = RealEstateFinalCreationService(db)
    try:
        result = await svc.finalize(
            draft_id        = draft_id,
            customer_id     = customer_id,
            idempotency_key = idempotency_key,
            request_id      = _RID(r),
        )
        await db.commit()
    except ValueError as exc:
        code = _error_code(exc)
        return ok({
            "success": False,
            "error": {"code": code, "message": _user_message(code)},
        }, _RID(r), "final_records")

    return ok({
        "record_type": "lead",
        "lead_id":     result["lead_id"],
        "lead_number": result["lead_number"],
        "status":      result.get("status", "new"),
        "idempotent":  result.get("idempotent", False),
        "message":     "Your inquiry has been submitted." if not result.get("idempotent") else "Already submitted.",
    }, _RID(r), "final_records")


# ── Error message map ─────────────────────────────────────────────────────────

_MESSAGES = {
    ERR_DRAFT_NOT_FOUND:              "Draft not found.",
    ERR_DRAFT_NOT_READY:              "Draft is not ready for confirmation. Please complete all required steps.",
    ERR_ACCESS_DENIED:                "Access denied.",
    ERR_DUPLICATE_CONFIRMATION:       "Already confirmed.",
    ERR_SLOT_HOLD_MISSING:            "Your slot reservation has expired or is missing. Please select a new slot.",
    ERR_SLOT_HOLD_EXPIRED:            "Your slot reservation has expired. Please select a new slot and try again.",
    ERR_SLOT_HOLD_ALREADY_CONVERTED:  "This slot is already booked.",
}


def _user_message(code: str) -> str:
    return _MESSAGES.get(code, "Confirmation failed. Please try again.")
