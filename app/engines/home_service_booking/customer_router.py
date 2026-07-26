"""Sprint 16 — Customer Home Service Booking Draft API.

10 endpoints at /v1/customer/home-services/booking-drafts/*.
Auth: customer JWT (Bearer token) required on all endpoints.
"""
from __future__ import annotations
import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, UserContext
from app.dependencies.db import get_db
from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
from app.schemas.base import ApiResponse, ok

logger = structlog.get_logger("home_service.customer_router")

router = APIRouter(
    prefix="/v1/customer/home-services/booking-drafts",
    tags=["Customer Home Service Booking Drafts"],
)


def _svc(r: Request, db: AsyncSession = Depends(get_db)) -> HomeServiceChatbotBookingService:
    return HomeServiceChatbotBookingService(db=db, request_id=getattr(r.state, "request_id", "—"))


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ── POST /  — Start draft ─────────────────────────────────────────────────────
@router.post(
    "",
    response_model=ApiResponse[dict],
    summary="Start a Home Service booking draft",
    description=(
        "Creates a new booking draft for a Home Service offering. "
        "Required fields are driven by the offering catalog, not hardcoded. "
        "Optionally links to an existing AI conversation session."
    ),
    responses={
        200: {"description": "Draft created"},
        422: {"description": "Invalid category or offering slug"},
    },
)
async def start_booking_draft(
    r: Request,
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    user: UserContext = Depends(get_current_user),
):
    body           = await r.json() if r.headers.get("content-length", "0") != "0" else {}
    customer_id    = uuid.UUID(user.user_id)
    ai_session_id  = uuid.UUID(body["ai_session_id"]) if body.get("ai_session_id") else None
    result = await svc.start_booking_draft(
        customer_id=customer_id,
        ai_session_id=ai_session_id,
        category_slug=body["category_slug"],
        offering_slug=body["offering_slug"],
    )
    return ok(result, _rid(r), "home_service_booking")


# ── GET /{draft_id}  — Get draft ──────────────────────────────────────────────
@router.get(
    "/{draft_id}",
    response_model=ApiResponse[dict],
    summary="Get a booking draft",
    responses={
        200: {"description": "Draft details"},
        403: {"description": "Access denied"},
        404: {"description": "Draft not found"},
    },
)
async def get_booking_draft(
    draft_id: uuid.UUID,
    r: Request,
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    user: UserContext = Depends(get_current_user),
):
    customer_id = uuid.UUID(user.user_id)
    result = await svc.get_booking_draft(draft_id=draft_id, customer_id=customer_id)
    return ok(result, _rid(r), "home_service_booking")


# ── PUT /{draft_id}  — Update draft fields ────────────────────────────────────
@router.put(
    "/{draft_id}",
    response_model=ApiResponse[dict],
    summary="Update booking draft fields",
    description=(
        "Update one or more fields (issue, address, type, brand, date). "
        "Backend validates all fields. Frontend price fields are ignored."
    ),
)
async def update_draft_fields(
    draft_id: uuid.UUID,
    r: Request,
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    user: UserContext = Depends(get_current_user),
):
    body        = await r.json() if r.headers.get("content-length", "0") != "0" else {}
    customer_id = uuid.UUID(user.user_id)
    result = await svc.update_draft_fields(
        draft_id=draft_id, customer_id=customer_id, payload=body
    )
    return ok(result, _rid(r), "home_service_booking")


# ── POST /{draft_id}/serviceability-check ─────────────────────────────────────
@router.post(
    "/{draft_id}/serviceability-check",
    response_model=ApiResponse[dict],
    summary="Check service availability for draft address",
    description="Runs real serviceability check against provider service areas. City must be set first.",
)
async def check_serviceability(
    draft_id: uuid.UUID,
    r: Request,
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    user: UserContext = Depends(get_current_user),
):
    customer_id = uuid.UUID(user.user_id)
    result = await svc.check_serviceability(draft_id=draft_id, customer_id=customer_id)
    return ok(result, _rid(r), "home_service_booking")


# ── POST /{draft_id}/price-estimate ──────────────────────────────────────────
@router.post(
    "/{draft_id}/price-estimate",
    response_model=ApiResponse[dict],
    summary="Resolve price estimate for this booking",
    description=(
        "Backend resolves price from offering catalog + city-tier pricing. "
        "Frontend price is NEVER trusted. DeepSeek price is NEVER used."
    ),
)
async def resolve_price_estimate(
    draft_id: uuid.UUID,
    r: Request,
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    user: UserContext = Depends(get_current_user),
):
    customer_id = uuid.UUID(user.user_id)
    result = await svc.resolve_price_estimate(draft_id=draft_id, customer_id=customer_id)
    return ok(result, _rid(r), "home_service_booking")


# ── POST /{draft_id}/match-and-price ─────────────────────────────────────────
@router.post(
    "/{draft_id}/match-and-price",
    response_model=ApiResponse[dict],
    summary="Backend selects the single best provider, then computes its price options",
    description=(
        "Provider-First Matching + Customer Price Choice: the backend runs the full "
        "eligibility gate (bookable, coverage, technician, availability, pricing, "
        "package, credits, deposit) over every candidate, scores them, and selects "
        "exactly ONE provider — the customer never sees or picks from a list. "
        "Returns that provider's public info, its Low/Mid/High price options "
        "(fee-inclusive floor), and a separate, non-authoritative area price "
        "comparison. Internal scoring is never included unless the caller has "
        "debug/admin permission."
    ),
)
async def match_and_price(
    draft_id: uuid.UUID,
    r: Request,
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    user: UserContext = Depends(get_current_user),
):
    customer_id = uuid.UUID(user.user_id)
    draft = await svc.get_booking_draft(draft_id=draft_id, customer_id=customer_id)
    result = await svc.match_provider_and_price(
        category_id=uuid.UUID(draft["category_id"]),
        master_service_id=uuid.UUID(draft["offering_id"]),
        city=draft["city"], zipcode=draft.get("zipcode"),
        offering_type_id=uuid.UUID(draft["offering_type_id"]) if draft.get("offering_type_id") else None,
        brand_id=uuid.UUID(draft["brand_id"]) if draft.get("brand_id") else None,
        job_type_id=uuid.UUID(draft["job_type_id"]) if draft.get("job_type_id") else None,
        draft_id=draft_id, customer_id=customer_id,
        reveal_internal_score=False,
    )
    return ok(result, _rid(r), "home_service_booking")


# ── POST /{draft_id}/confirm-price-choice ─────────────────────────────────────
@router.post(
    "/{draft_id}/confirm-price-choice",
    response_model=ApiResponse[dict],
    summary="Customer chooses Low / Mid / High for the already-selected provider",
    description=(
        "Customer submits only a tier name ('low' | 'mid' | 'high') — never a raw "
        "amount and never a provider. The backend resolves the exact stored "
        "price_options value for that tier and stores it as the booking's "
        "customer_offer, along with the selected-provider snapshot."
    ),
)
async def confirm_price_choice(
    draft_id: uuid.UUID,
    r: Request,
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    user: UserContext = Depends(get_current_user),
):
    body        = await r.json() if r.headers.get("content-length", "0") != "0" else {}
    customer_id = uuid.UUID(user.user_id)
    result = await svc.confirm_price_choice(
        draft_id=draft_id, price_tier=body["price_tier"], customer_id=customer_id
    )
    return ok(result, _rid(r), "home_service_booking")


# ── POST /{draft_id}/match-providers  [DEPRECATED — list-based manual selection] ─
# Superseded by POST /{draft_id}/match-and-price (Provider-First Matching fix).
# Kept only for backward compatibility with any existing caller of the old
# list-and-manually-choose flow; do not build new customer UI against this.
@router.post(
    "/{draft_id}/match-providers",
    response_model=ApiResponse[dict],
    summary="[DEPRECATED] Find bookable providers for this booking (list-based)",
    description=(
        "DEPRECATED — superseded by /match-and-price, which selects a single "
        "provider server-side instead of returning a list for manual customer "
        "choice. Queries real provider service areas. Only bookable active "
        "providers returned. Sorted by coverage quality (zipcode > city) then "
        "health score."
    ),
)
async def find_bookable_providers(
    draft_id: uuid.UUID,
    r: Request,
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    user: UserContext = Depends(get_current_user),
):
    customer_id = uuid.UUID(user.user_id)
    result = await svc.find_bookable_providers(draft_id=draft_id, customer_id=customer_id)
    return ok(result, _rid(r), "home_service_booking")


# ── POST /{draft_id}/select-provider  [DEPRECATED — manual customer selection] ──
# Superseded by POST /{draft_id}/match-and-price, which the backend selects
# automatically. Do not call this from new customer UI.
@router.post(
    "/{draft_id}/select-provider",
    response_model=ApiResponse[dict],
    summary="[DEPRECATED] Manually select a specific provider from matched options",
    description="DEPRECATED — superseded by /match-and-price (Provider-First Matching fix).",
)
async def select_provider(
    draft_id: uuid.UUID,
    r: Request,
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    user: UserContext = Depends(get_current_user),
):
    body         = await r.json() if r.headers.get("content-length", "0") != "0" else {}
    customer_id  = uuid.UUID(user.user_id)
    result = await svc.select_provider(
        draft_id=draft_id, provider_ref=body["provider_ref"], customer_id=customer_id
    )
    return ok(result, _rid(r), "home_service_booking")


# ── POST /{draft_id}/summary ──────────────────────────────────────────────────
@router.post(
    "/{draft_id}/summary",
    response_model=ApiResponse[dict],
    summary="Build booking summary card",
    description="Generates the full booking summary shown to customer before confirmation.",
)
async def build_booking_summary(
    draft_id: uuid.UUID,
    r: Request,
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    user: UserContext = Depends(get_current_user),
):
    customer_id = uuid.UUID(user.user_id)
    result = await svc.build_booking_summary(draft_id=draft_id, customer_id=customer_id)
    return ok(result, _rid(r), "home_service_booking")


# ── POST /{draft_id}/confirm ──────────────────────────────────────────────────
@router.post(
    "/{draft_id}/confirm",
    summary="Confirm booking — creates ServiceBooking + ServiceJob",
    description=(
        "Validates draft, creates a ServiceBooking and ServiceJob, marks draft confirmed. "
        "Idempotent: retrying returns the existing booking number."
    ),
    responses={
        200: {"description": "Booking and job created"},
        422: {"description": "Draft not ready for confirmation"},
    },
)
async def confirm_draft(
    draft_id: uuid.UUID,
    r: Request,
    db: AsyncSession = Depends(get_db),
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    user: UserContext = Depends(get_current_user),
):
    from app.engines.final_records.creation_service import HomeServiceFinalCreationService
    customer_id     = uuid.UUID(user.user_id)
    idempotency_key = r.headers.get("idempotency-key")
    request_id      = getattr(r.state, "request_id", None)

    # HS7 fix: mark_ready_for_confirmation was previously never called from
    # any router, so this endpoint always failed with ERR_DRAFT_NOT_READY.
    # Also re-validates the selected provider is still bookable right now.
    # Skipped when the draft is already confirmed so that an idempotent
    # retry (same idempotency-key) falls through to finalize()'s own
    # duplicate-confirmation handling instead of hitting the terminal-status
    # guard inside mark_ready_for_confirmation.
    existing_draft = await svc.get_booking_draft(draft_id=draft_id, customer_id=customer_id)
    if existing_draft.get("status") != "confirmed":
        await svc.mark_ready_for_confirmation(draft_id=draft_id, customer_id=customer_id)

    final_svc = HomeServiceFinalCreationService(db=db)
    result = await final_svc.finalize(
        draft_id        = draft_id,
        customer_id     = customer_id,
        idempotency_key = idempotency_key,
        request_id      = request_id,
    )
    await db.commit()
    return ok(result, request_id or "—", "home_service_booking")


# ── POST /{draft_id}/cancel ───────────────────────────────────────────────────
@router.post(
    "/{draft_id}/cancel",
    response_model=ApiResponse[dict],
    summary="Cancel a booking draft",
)
async def cancel_draft(
    draft_id: uuid.UUID,
    r: Request,
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    user: UserContext = Depends(get_current_user),
):
    body        = await r.json() if r.headers.get("content-length", "0") != "0" else {}
    customer_id = uuid.UUID(user.user_id)
    result = await svc.cancel_draft(
        draft_id=draft_id, customer_id=customer_id, reason=body.get("reason")
    )
    return ok(result, _rid(r), "home_service_booking")


# ── POST /{draft_id}/photos ───────────────────────────────────────────────────
@router.post(
    "/{draft_id}/photos",
    response_model=ApiResponse[dict],
    summary="Add a photo URL to the booking draft",
    description=(
        "After uploading via /v1/media/upload, pass the URL here to attach to draft. "
        "Allowed types: jpg, png, webp. Max 5 photos."
    ),
)
async def add_photo(
    draft_id: uuid.UUID,
    r: Request,
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    user: UserContext = Depends(get_current_user),
):
    body        = await r.json() if r.headers.get("content-length", "0") != "0" else {}
    customer_id = uuid.UUID(user.user_id)
    result = await svc.add_photo(
        draft_id=draft_id,
        customer_id=customer_id,
        photo_url=body["photo_url"],
        content_type=body.get("content_type", "image/jpeg"),
    )
    return ok(result, _rid(r), "home_service_booking")
