"""Sprint 18 — Customer Real Estate Lead Draft API (11 endpoints)."""
from __future__ import annotations
import uuid

from fastapi import APIRouter, Request

from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.schemas.base import ApiResponse, ok

router = APIRouter(
    prefix="/v1/customer/real-estate/lead-drafts",
    tags=["Customer Real Estate Lead Drafts"],
)

_RID = lambda r: getattr(r.state, "request_id", "—")


# ── POST / — Start draft ───────────────────────────────────────────────────────

@router.post(
    "",
    summary="Start a real estate lead draft",
    response_model=ApiResponse,
)
async def start_lead_draft(r: Request):
    """
    Start a new real estate lead draft for Buy/Rent/Sell/Site Visit inquiries.
    Requires customer auth.
    """
    user = await get_current_user(r)
    db   = await anext(get_db())
    try:
        body        = await r.json()
        customer_id = uuid.UUID(user.user_id)
        ai_session_id = uuid.UUID(body["ai_session_id"]) if body.get("ai_session_id") else None

        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        svc    = RealEstateLeadFlowService(db=db)
        result = await svc.start_lead_draft(
            customer_id   = customer_id,
            ai_session_id = ai_session_id,
            category_slug = body.get("category_slug", "real-estate"),
            offering_slug = body.get("offering_slug", ""),
        )
        await db.commit()
        return ok(result, _RID(r), "real_estate_lead")
    except Exception as exc:
        await db.rollback()
        raise


# ── GET /{draft_id} ───────────────────────────────────────────────────────────

@router.get(
    "/{draft_id}",
    summary="Get a real estate lead draft",
    response_model=ApiResponse,
)
async def get_lead_draft(draft_id: uuid.UUID, r: Request):
    user = await get_current_user(r)
    db   = await anext(get_db())
    try:
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        svc    = RealEstateLeadFlowService(db=db)
        result = await svc.get_lead_draft(draft_id, uuid.UUID(user.user_id))
        return ok(result, _RID(r), "real_estate_lead")
    except Exception as exc:
        raise


# ── PUT /{draft_id} — Update fields ──────────────────────────────────────────

@router.put(
    "/{draft_id}",
    summary="Update real estate lead draft fields",
    response_model=ApiResponse,
)
async def update_lead_draft(draft_id: uuid.UUID, r: Request):
    user = await get_current_user(r)
    db   = await anext(get_db())
    try:
        body   = await r.json()
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        svc    = RealEstateLeadFlowService(db=db)
        result = await svc.update_draft_fields(
            draft_id    = draft_id,
            customer_id = uuid.UUID(user.user_id),
            payload     = body,
        )
        await db.commit()
        return ok(result, _RID(r), "real_estate_lead")
    except Exception as exc:
        await db.rollback()
        raise


# ── POST /{draft_id}/check-location ──────────────────────────────────────────

@router.post(
    "/{draft_id}/check-location",
    summary="Check if location has real estate provider coverage",
    response_model=ApiResponse,
)
async def check_location(draft_id: uuid.UUID, r: Request):
    user = await get_current_user(r)
    db   = await anext(get_db())
    try:
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        svc    = RealEstateLeadFlowService(db=db)
        result = await svc.check_location_coverage(draft_id, uuid.UUID(user.user_id))
        await db.commit()
        return ok(result, _RID(r), "real_estate_lead")
    except Exception as exc:
        await db.rollback()
        raise


# ── POST /{draft_id}/find-providers ──────────────────────────────────────────

@router.post(
    "/{draft_id}/find-providers",
    summary="Find eligible real estate providers for the lead",
    response_model=ApiResponse,
)
async def find_providers(draft_id: uuid.UUID, r: Request):
    user = await get_current_user(r)
    db   = await anext(get_db())
    try:
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        svc    = RealEstateLeadFlowService(db=db)
        result = await svc.find_eligible_providers(draft_id, uuid.UUID(user.user_id))
        await db.commit()
        return ok(result, _RID(r), "real_estate_lead")
    except Exception as exc:
        await db.rollback()
        raise


# ── POST /{draft_id}/fallback-options ────────────────────────────────────────

@router.post(
    "/{draft_id}/fallback-options",
    summary="Get fallback/nearby provider options when exact match unavailable",
    response_model=ApiResponse,
)
async def get_fallback_options(draft_id: uuid.UUID, r: Request):
    user = await get_current_user(r)
    db   = await anext(get_db())
    try:
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        svc    = RealEstateLeadFlowService(db=db)
        result = await svc.find_nearby_or_fallback_providers(draft_id, uuid.UUID(user.user_id))
        await db.commit()
        return ok(result, _RID(r), "real_estate_lead")
    except Exception as exc:
        await db.rollback()
        raise


# ── POST /{draft_id}/score ────────────────────────────────────────────────────

@router.post(
    "/{draft_id}/score",
    summary="Calculate lead score based on field completeness",
    response_model=ApiResponse,
)
async def calculate_score(draft_id: uuid.UUID, r: Request):
    user = await get_current_user(r)
    db   = await anext(get_db())
    try:
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        svc    = RealEstateLeadFlowService(db=db)
        result = await svc.calculate_lead_score(draft_id, uuid.UUID(user.user_id))
        await db.commit()
        return ok(result, _RID(r), "real_estate_lead")
    except Exception as exc:
        await db.rollback()
        raise


# ── POST /{draft_id}/summary ──────────────────────────────────────────────────

@router.post(
    "/{draft_id}/summary",
    summary="Build lead summary from collected fields",
    response_model=ApiResponse,
)
async def build_summary(draft_id: uuid.UUID, r: Request):
    user = await get_current_user(r)
    db   = await anext(get_db())
    try:
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        svc    = RealEstateLeadFlowService(db=db)
        result = await svc.build_lead_summary(draft_id, uuid.UUID(user.user_id))
        await db.commit()
        return ok(result, _RID(r), "real_estate_lead")
    except Exception as exc:
        await db.rollback()
        raise


# ── POST /{draft_id}/confirm ──────────────────────────────────────────────────

@router.post(
    "/{draft_id}/confirm",
    summary="Confirm lead draft — creates RealEstateLead record",
    response_model=ApiResponse,
)
async def confirm_draft(draft_id: uuid.UUID, r: Request):
    """Validates draft, creates a RealEstateLead, marks draft confirmed. Idempotent."""
    user = await get_current_user(r)
    db   = await anext(get_db())
    try:
        from app.engines.final_records.creation_service import RealEstateFinalCreationService
        idempotency_key = r.headers.get("idempotency-key")
        request_id      = _RID(r)
        svc    = RealEstateFinalCreationService(db=db)
        result = await svc.finalize(
            draft_id        = draft_id,
            customer_id     = uuid.UUID(user.user_id),
            idempotency_key = idempotency_key,
            request_id      = request_id,
        )
        await db.commit()
        return ok(result, request_id, "real_estate_lead")
    except Exception as exc:
        await db.rollback()
        raise


# ── POST /{draft_id}/cancel ────────────────────────────────────────────────────

@router.post(
    "/{draft_id}/cancel",
    summary="Cancel a real estate lead draft",
    response_model=ApiResponse,
)
async def cancel_draft(draft_id: uuid.UUID, r: Request):
    user = await get_current_user(r)
    db   = await anext(get_db())
    try:
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        svc    = RealEstateLeadFlowService(db=db)
        result = await svc.cancel_draft(draft_id, uuid.UUID(user.user_id))
        await db.commit()
        return ok(result, _RID(r), "real_estate_lead")
    except Exception as exc:
        await db.rollback()
        raise
