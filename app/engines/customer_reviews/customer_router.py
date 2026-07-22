"""Sprint 24 — Customer Review endpoints."""
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user, require_customer
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.engines.customer_reviews.review_service import ReviewService
from app.engines.customer_reviews.eligibility_service import ReviewEligibilityService

customer_review_router = APIRouter(prefix="/v1/customer/reviews", tags=["customer-reviews"])

_svc = ReviewService()
_elig = ReviewEligibilityService()


class CustomerFlagRequest(BaseModel):
    """Slice 2F-24 — strict body for a customer flagging a review.

    The previous untyped body read `body["tenant_id"]` and passed it to the
    service as the flag's tenant, i.e. the client chose the tenant a
    moderation record was attributed to (CLIENT_TENANT_TRUSTED). `tenant_id`
    is no longer accepted at all: `extra="forbid"` rejects it explicitly
    rather than ignoring it, and the flag's tenant is now taken from the
    review itself. No actor or status field is accepted either.
    """
    model_config = ConfigDict(extra="forbid")
    reason_code: Literal["spam", "fake", "offensive", "irrelevant", "other"] = "other"
    reason_text: str | None = Field(default=None, max_length=2000)


@customer_review_router.get("/eligibility")
async def check_eligibility(
    record_type: str,
    record_id: str,
    r: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    rid = getattr(r.state, "request_id", "—")
    result = await _elig.check_eligible(db, user.user_id, record_type, uuid.UUID(record_id))
    return ok(result, rid, "review.eligibility.checked")


@customer_review_router.post("")
async def submit_review(
    body: dict,
    r: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    rid = getattr(r.state, "request_id", "—")
    try:
        review = await _svc.submit_review(
            db,
            customer_id     = user.user_id,
            tenant_id       = uuid.UUID(str(body["tenant_id"])),
            record_type     = body["record_type"],
            record_id       = uuid.UUID(str(body["record_id"])),
            overall_rating  = int(body["overall_rating"]),
            provider_rating = body.get("provider_rating"),
            staff_rating    = body.get("staff_rating"),
            communication_rating = body.get("communication_rating"),
            punctuality_rating   = body.get("punctuality_rating"),
            quality_rating  = body.get("quality_rating"),
            value_rating    = body.get("value_rating"),
            review_title    = body.get("review_title"),
            review_text     = body.get("review_text"),
            review_tags     = body.get("review_tags"),
            media_urls      = body.get("media_urls"),
            request_id      = rid,
        )
    except ValueError as exc:
        # MODULE-L5-02 bug #19: the service raises bare ValueErrors for domain
        # rejections (not eligible / already reviewed / record not found / invalid
        # rating); they were leaking as 500s. Map to the error code + a 4xx.
        code = str(exc)
        status = 404 if code == "RECORD_NOT_FOUND" else 422
        raise ServiceOSException(code, code.replace("_", " ").title(), status_code=status)
    return ok(review.to_dict(), rid, "review.submitted")


@customer_review_router.get("")
async def list_my_reviews(
    r: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "—")
    reviews = await _svc.list_reviews(db, customer_id=user.user_id)
    return ok([rv.to_dict() for rv in reviews], rid, "review.list")


@customer_review_router.get("/{review_id}")
async def get_my_review(
    review_id: str,
    r: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    rid = getattr(r.state, "request_id", "—")
    # Slice 2F-24: the route is named `get_my_review` but was an unscoped
    # primary-key read -- any authenticated principal could read any review in
    # any tenant. Now scoped to the caller's own reviews, matching the route's
    # own contract and the `list_my_reviews` sibling directly above.
    review = await _svc.get_review(db, uuid.UUID(review_id), customer_id=user.user_id)
    return ok(review.to_dict(), rid, "review.fetched")


@customer_review_router.patch("/{review_id}")
async def edit_review(
    review_id: str,
    body: dict,
    r: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    rid = getattr(r.state, "request_id", "—")
    review = await _svc.edit_review(db, uuid.UUID(review_id), user.user_id, body, request_id=rid)
    return ok(review.to_dict(), rid, "review.edited")


@customer_review_router.post("/{review_id}/flag")
async def flag_review(
    review_id: str,
    body: CustomerFlagRequest,
    r: Request,
    user=Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    # Slice 2F-24 — same-record alternate to the provider flag route.
    #
    # Before: `tenant_id` came from the request body, so a customer chose the
    # tenant its moderation record was attributed to, and the service applied
    # no ownership check at all -- any authenticated principal could flag any
    # review in any tenant through this path too.
    #
    # After: the customer may flag only its OWN review (scoped by
    # `customer_id` from the principal), and the flag's tenant is derived from
    # the review. Whether a customer should be able to flag someone else's
    # review is a product question, deliberately NOT invented here -- see
    # customer-flag-authority.md. Self-scoping is the established, provable
    # relationship in this model (`CustomerReview.customer_id` is NOT NULL).
    import uuid
    rid = getattr(r.state, "request_id", "—")
    flag = await _svc.flag_review(
        db,
        review_id          = uuid.UUID(review_id),
        flagged_by_user_id = user.user_id,
        # Server-set: this is the customer surface.
        flagged_by_type    = "customer",
        reason_code        = body.reason_code,
        reason_text        = body.reason_text,
        # Tenant authority is NEVER taken from the client; the scoped lookup
        # resolves the review by customer ownership and the flag inherits the
        # review's own tenant.
        tenant_id          = None,
        customer_id        = user.user_id,
        request_id         = rid,
    )
    return ok(flag.to_dict(), rid, "review.flagged")
