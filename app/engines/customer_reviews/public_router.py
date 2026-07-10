"""Sprint 24 — Public Review endpoints (no auth required)."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.customer_reviews.models import (
    CustomerReview, TenantRatingSummary, StaffRatingSummary, ReviewReply,
)
from app.engines.customer_reviews.constants import STATUS_APPROVED, REPLY_APPROVED

public_review_router = APIRouter(prefix="/v1/public/reviews", tags=["public-reviews"])


@public_review_router.get("/tenant/{tenant_id}")
async def list_tenant_reviews(
    tenant_id: str,
    r: Request,
    db: AsyncSession = Depends(get_db),
):
    import uuid
    rid = getattr(r.state, "request_id", "—")
    res = await db.execute(
        select(CustomerReview).where(
            CustomerReview.tenant_id == uuid.UUID(tenant_id),
            CustomerReview.status    == STATUS_APPROVED,
        ).order_by(CustomerReview.approved_at.desc()).limit(50)
    )
    reviews = res.scalars().all()
    return ok([rv.to_public_dict() for rv in reviews], rid, "public.reviews.list")


@public_review_router.get("/tenant/{tenant_id}/summary")
async def get_tenant_rating_summary(
    tenant_id: str,
    r: Request,
    db: AsyncSession = Depends(get_db),
):
    import uuid
    rid = getattr(r.state, "request_id", "—")
    res = await db.execute(
        select(TenantRatingSummary).where(TenantRatingSummary.tenant_id == uuid.UUID(tenant_id))
    )
    summary = res.scalars().first()
    return ok(summary.to_dict() if summary else {}, rid, "public.rating_summary.fetched")


@public_review_router.get("/{review_id}")
async def get_review(
    review_id: str,
    r: Request,
    db: AsyncSession = Depends(get_db),
):
    import uuid
    rid = getattr(r.state, "request_id", "—")
    res = await db.execute(
        select(CustomerReview).where(
            CustomerReview.id     == uuid.UUID(review_id),
            CustomerReview.status == STATUS_APPROVED,
        )
    )
    review = res.scalars().first()
    if not review:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Review not found")
    return ok(review.to_public_dict(), rid, "public.review.fetched")


@public_review_router.get("/{review_id}/reply")
async def get_reply(
    review_id: str,
    r: Request,
    db: AsyncSession = Depends(get_db),
):
    import uuid
    rid = getattr(r.state, "request_id", "—")
    res = await db.execute(
        select(ReviewReply).where(
            ReviewReply.review_id == uuid.UUID(review_id),
            ReviewReply.status    == REPLY_APPROVED,
        )
    )
    reply = res.scalars().first()
    return ok(reply.to_dict() if reply else None, rid, "public.reply.fetched")
