"""Sprint 24 — Provider Review endpoints."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.customer_reviews.review_service import ReviewService
from app.engines.customer_reviews.aggregation_service import RatingAggregationService

provider_review_router = APIRouter(prefix="/v1/provider/reviews", tags=["provider-reviews"])

_svc  = ReviewService()
_agg  = RatingAggregationService()


@provider_review_router.get("")
async def list_my_reviews(
    status: str | None = None,
    r: Request = None,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "—")
    reviews = await _svc.list_reviews(db, tenant_id=user.tenant_id, status=status)
    return ok([rv.to_dict() for rv in reviews], rid, "provider.reviews.list")


@provider_review_router.get("/summary")
async def get_tenant_rating_summary(
    r: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "—")
    from sqlalchemy import select
    from app.engines.customer_reviews.models import TenantRatingSummary
    res = await db.execute(
        select(TenantRatingSummary).where(TenantRatingSummary.tenant_id == user.tenant_id)
    )
    summary = res.scalars().first()
    return ok(summary.to_dict() if summary else {}, rid, "provider.rating_summary.fetched")


@provider_review_router.get("/staff-summary")
async def get_staff_rating_summary(
    r: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rid = getattr(r.state, "request_id", "—")
    from sqlalchemy import select
    from app.engines.customer_reviews.models import StaffRatingSummary
    res = await db.execute(
        select(StaffRatingSummary).where(StaffRatingSummary.tenant_id == user.tenant_id)
    )
    summaries = res.scalars().all()
    return ok([s.to_dict() for s in summaries], rid, "provider.staff_summary.list")


@provider_review_router.get("/{review_id}")
async def get_review(
    review_id: str,
    r: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    rid = getattr(r.state, "request_id", "—")
    review = await _svc.get_review(db, uuid.UUID(review_id))
    return ok(review.to_dict(), rid, "provider.review.fetched")


@provider_review_router.post("/{review_id}/reply")
async def submit_reply(
    review_id: str,
    body: dict,
    r: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid
    rid = getattr(r.state, "request_id", "—")
    reply = await _svc.submit_reply(
        db,
        review_id          = uuid.UUID(review_id),
        tenant_id          = user.tenant_id,
        replied_by_user_id = user.user_id,
        reply_text         = body["reply_text"],
        request_id         = rid,
    )
    return ok(reply.to_dict(), rid, "provider.reply.submitted")


@provider_review_router.post("/{review_id}/flag")
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
        flagged_by_type    = "provider",
        reason_code        = body.get("reason_code", "other"),
        reason_text        = body.get("reason_text"),
        tenant_id          = user.tenant_id,
        request_id         = rid,
    )
    return ok(flag.to_dict(), rid, "provider.review.flagged")
