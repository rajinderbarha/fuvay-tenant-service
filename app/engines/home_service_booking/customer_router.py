"""Sprint 16 — Customer Home Service Booking Draft API.

10 endpoints at /v1/customer/home-services/booking-drafts/*.
Auth: customer JWT (Bearer token) required on all endpoints.
"""
from __future__ import annotations
import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
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

# Category-scoped, not draft-scoped -- a customer calls this BEFORE any
# draft exists, so it lives under its own path rather than
# /booking-drafts/{draft_id}/... (see get_assistant_bootstrap).
assistant_bootstrap_router = APIRouter(
    prefix="/v1/customer/home-services",
    tags=["Customer Home Service Booking Drafts"],
)


def _svc(r: Request, db: AsyncSession = Depends(get_db)) -> HomeServiceChatbotBookingService:
    return HomeServiceChatbotBookingService(db=db, request_id=getattr(r.state, "request_id", "—"))


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ── GET /assistant-bootstrap — backend-first Booking Assistant bootstrap ─────
@assistant_bootstrap_router.get(
    "/assistant-bootstrap",
    response_model=ApiResponse[dict],
    summary="Backend-first Booking Assistant bootstrap (no DeepSeek call)",
    description=(
        "Returns the category, real zipcode-serviceable offerings, and the "
        "customer's own resumable draft (if any) for the Booking Assistant's "
        "first screen -- entirely backend-authoritative, never a DeepSeek call."
    ),
)
async def get_assistant_bootstrap(
    r: Request,
    category_slug: str = Query(...),
    zipcode: Optional[str] = Query(None),
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    user: UserContext = Depends(get_current_user),
):
    customer_id = uuid.UUID(user.user_id)
    result = await svc.get_assistant_bootstrap(customer_id=customer_id, category_slug=category_slug, zipcode=zipcode)
    return ok(result, _rid(r), "home_service_booking")


# ── POST /assistant-bootstrap/interpret — constrained offering selection ────
def _oi_svc(db: AsyncSession = Depends(get_db)):
    from app.engines.home_service_booking.offering_interpretation_service import OfferingInterpretationService
    return OfferingInterpretationService(db=db)


@assistant_bootstrap_router.post(
    "/assistant-bootstrap/interpret",
    response_model=ApiResponse[dict],
    summary="Interpret a customer's free-text message against the real serviceable offering list",
)
async def interpret_assistant_bootstrap_text(
    r: Request,
    oi=Depends(_oi_svc),
    user: UserContext = Depends(get_current_user),
):
    body = await r.json()
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="text is required.")
    result = await oi.interpret(
        category_slug=body["category_slug"], zipcode=body.get("zipcode"),
        text=text, session_id=body.get("session_id"),
    )
    return ok(result, _rid(r), "home_service_booking")


# ── POST /assistant-bootstrap/select-issue — canonical issue selection ──────
@assistant_bootstrap_router.post(
    "/assistant-bootstrap/select-issue",
    response_model=ApiResponse[dict],
    summary="Select a real, zipcode-serviceable AC issue and start/resolve its canonical draft",
)
async def select_assistant_bootstrap_issue(
    r: Request,
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    body = await r.json()
    customer_id = uuid.UUID(user.user_id)
    result = await svc.select_issue(
        customer_id=customer_id,
        ai_session_id=uuid.UUID(body["ai_session_id"]) if body.get("ai_session_id") else None,
        category_slug=body["category_slug"], zipcode=body.get("zipcode"),
        issue_id=body["issue_id"],
        additional_issue_ids=body.get("additional_issue_ids"),
    )
    # Real bug fixed here: this endpoint returns the FIRST question of the
    # flow, but presentation was only wired into get_question_flow and
    # submit_answer -- so after choosing Hindi/Punjabi the very first
    # question still came back in English (confirmed live). Present it here
    # too, using the same validated, fail-closed path.
    from app.engines.home_service_booking.question_presentation_service import present_envelope
    result["envelope"] = await present_envelope(
        db, result.get("envelope"), body.get("language"),
        session_id=body.get("ai_session_id"), request_id=_rid(r),
    )
    return ok(result, _rid(r), "home_service_booking")


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


# ── GET /by-session/{ai_session_id}  — Resolve draft by AI session ───────────
# Registered BEFORE /{draft_id} -- FastAPI matches routes in registration
# order, and "by-session" would otherwise be swallowed by {draft_id} (as a
# non-UUID string) and 422, or -- as found live -- never matched at all,
# falling through to a raw 404 because this route never existed.
@router.get(
    "/by-session/{ai_session_id}",
    response_model=ApiResponse[Optional[dict]],
    summary="Resolve a customer's own draft by AI session id",
    responses={200: {"description": "Draft details, or null if none exists yet"}},
)
async def get_booking_draft_by_ai_session(
    ai_session_id: uuid.UUID,
    r: Request,
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    user: UserContext = Depends(get_current_user),
):
    customer_id = uuid.UUID(user.user_id)
    result = await svc.get_booking_draft_by_ai_session(ai_session_id=ai_session_id, customer_id=customer_id)
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


# ── GET /{draft_id}/available-slots ───────────────────────────────────────────
@router.get(
    "/{draft_id}/available-slots",
    response_model=ApiResponse[dict],
    summary="Real, capacity-checked slots the assigned provider can offer",
    description=(
        "Lists every slot the provider genuinely has room for, earliest first -- "
        "lets the customer choose instead of only seeing the single system-picked slot."
    ),
)
async def get_available_slots(
    draft_id: uuid.UUID,
    r: Request,
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    user: UserContext = Depends(get_current_user),
):
    customer_id = uuid.UUID(user.user_id)
    result = await svc.list_available_slots(draft_id=draft_id, customer_id=customer_id)
    return ok(result, _rid(r), "home_service_booking")


# ── POST /{draft_id}/select-slot ──────────────────────────────────────────────
@router.post(
    "/{draft_id}/select-slot",
    response_model=ApiResponse[dict],
    summary="Customer picks which offered slot to book",
    responses={422: {"description": "Slot no longer has capacity, or no provider assigned yet"}},
)
async def select_slot(
    draft_id: uuid.UUID,
    body: dict,
    r: Request,
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    user: UserContext = Depends(get_current_user),
):
    date_iso = body.get("date")
    time_window = body.get("time_window")
    if not date_iso or not time_window:
        raise HTTPException(status_code=422, detail="date and time_window are required.")
    customer_id = uuid.UUID(user.user_id)
    try:
        result = await svc.select_promised_slot(
            draft_id=draft_id, customer_id=customer_id, date_iso=date_iso, time_window=time_window,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
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


# ── GET /{draft_id}/question-flow — deterministic question envelope ──────────
# NEVER wired to an HTTP route until now (migration 220 / Phase 3 built the
# whole QuestionFlowService but no router imported it) -- the mobile app's
# getQuestionFlow/submitQuestionFlowAnswer calls 404'd unconditionally, for
# every draft, for every customer, since the feature was written. This is
# why the assistant never showed a question or option card.
def _qf_svc(db: AsyncSession = Depends(get_db)):
    from app.engines.home_service_booking.question_flow_service import QuestionFlowService
    return QuestionFlowService(db=db)


@router.get(
    "/{draft_id}/question-flow",
    response_model=ApiResponse[dict],
    summary="Get the current deterministic question for a draft",
)
async def get_question_flow(
    draft_id: uuid.UUID,
    r: Request,
    language: str | None = None,
    session_id: str | None = None,
    qf=Depends(_qf_svc),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """`language` presents the SAME canonical question in the customer's
    chosen conversation language (CUSTOMER-ASSISTANT-UX-04 Part 3). Only
    display text/labels change -- question id, option ids, order, type,
    required state and progress are always the backend's own, and any
    invalid DeepSeek presentation fails closed to the canonical wording.
    Omitting it returns the authored English envelope unchanged."""
    from app.engines.home_service_booking.question_presentation_service import present_envelope
    customer_id = uuid.UUID(user.user_id)
    result = await qf.get_current_question(draft_id=draft_id, customer_id=customer_id)
    result = await present_envelope(
        db, result, language, session_id=session_id, request_id=_rid(r),
    )
    return ok(result, _rid(r), "home_service_booking")


@router.post(
    "/{draft_id}/question-flow/answer",
    response_model=ApiResponse[dict],
    summary="Submit an answer to the current deterministic question",
)
async def submit_question_flow_answer(
    draft_id: uuid.UUID,
    r: Request,
    qf=Depends(_qf_svc),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    body = await r.json()
    customer_id = uuid.UUID(user.user_id)
    result = await qf.submit_answer(
        draft_id=draft_id,
        customer_id=customer_id,
        question_id=body["question_id"],
        option_id=body.get("option_id"),
        value=body.get("value"),
        expected_version=body.get("expected_version"),
    )
    # The NEXT question comes back in the same response -- present it in
    # the same conversation language, so the customer never sees one
    # question translated and the next one in English.
    from app.engines.home_service_booking.question_presentation_service import present_envelope
    result = await present_envelope(
        db, result, body.get("language"), session_id=body.get("session_id"), request_id=_rid(r),
    )
    return ok(result, _rid(r), "home_service_booking")


# ── POST /{draft_id}/question-flow/interpret — free-text interpretation ──────
# The ONLY place DeepSeek is consulted while a canonical question is
# active -- never for a tap (that goes straight to the endpoint above).
# See question_interpretation_service.py's module docstring for the full
# backend-first-with-DeepSeek-on-demand contract.
def _qi_svc(db: AsyncSession = Depends(get_db)):
    from app.engines.home_service_booking.question_interpretation_service import QuestionInterpretationService
    return QuestionInterpretationService(db=db)


@router.post(
    "/{draft_id}/question-flow/interpret",
    response_model=ApiResponse[dict],
    summary="Interpret a customer's free-text message against the current deterministic question",
)
async def interpret_question_flow_text(
    draft_id: uuid.UUID,
    r: Request,
    qi=Depends(_qi_svc),
    user: UserContext = Depends(get_current_user),
):
    body = await r.json()
    customer_id = uuid.UUID(user.user_id)
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="text is required.")
    result = await qi.interpret(
        draft_id=draft_id, customer_id=customer_id, text=text,
        session_id=body.get("session_id"),
    )
    return ok(result, _rid(r), "home_service_booking")


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


# ── DELETE /{draft_id}/photos ─────────────────────────────────────────────────
@router.delete(
    "/{draft_id}/photos",
    response_model=ApiResponse[dict],
    summary="Detach a photo from the booking draft",
    description=(
        "Removes the photo URL from the draft. The underlying media asset is "
        "left to the media engine's own retention rules."
    ),
)
async def remove_photo(
    draft_id: uuid.UUID,
    r: Request,
    svc: HomeServiceChatbotBookingService = Depends(_svc),
    user: UserContext = Depends(get_current_user),
):
    body        = await r.json() if r.headers.get("content-length", "0") != "0" else {}
    customer_id = uuid.UUID(user.user_id)
    result = await svc.remove_photo(
        draft_id=draft_id,
        customer_id=customer_id,
        photo_url=body["photo_url"],
    )
    return ok(result, _rid(r), "home_service_booking")
