"""Sprint 24 — Customer Review endpoints."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.exceptions import ServiceOSException
from app.engines.customer_reviews.review_service import ReviewService
from app.engines.customer_reviews.eligibility_service import ReviewEligibilityService

customer_review_router = APIRouter(prefix="/v1/customer/reviews", tags=["customer-reviews"])

_svc = ReviewService()
_elig = ReviewEligibilityService()


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
    review = await _svc.get_review(db, uuid.UUID(review_id))
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
    body: dict,
    r: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    rid = getattr(r.state, "request_id", "—")
    flag = await _svc.flag_review(
        db,
        review_id          = uuid.UUID(review_id),
        flagged_by_user_id = user.user_id,
        flagged_by_type    = "customer",
        reason_code        = body.get("reason_code", "other"),
        reason_text        = body.get("reason_text"),
        tenant_id          = uuid.UUID(str(body["tenant_id"])) if body.get("tenant_id") else None,
        request_id         = rid,
    )
    return ok(flag.to_dict(), rid, "review.flagged")
