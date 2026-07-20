"""Sprint 24 — Provider Review endpoints."""
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_tenant_owner_mutation
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.customer_reviews.review_service import ReviewService
from app.engines.customer_reviews.aggregation_service import RatingAggregationService

provider_review_router = APIRouter(prefix="/v1/provider/reviews", tags=["provider-reviews"])

_svc  = ReviewService()
_agg  = RatingAggregationService()


class ProviderReplyRequest(BaseModel):
    """Slice 2F-24 — strict body for the official provider reply.

    Was an untyped `dict`. `extra="forbid"` rejects any attempt to supply
    actor, tenant, provider or status fields rather than silently ignoring
    them, so the request contract cannot be misread as accepting authority the
    server does not honour. Actor identity and tenant come from the JWT.
    """
    model_config = ConfigDict(extra="forbid")
    reply_text: str = Field(min_length=1, max_length=5000)


class ReviewFlagRequest(BaseModel):
    """Slice 2F-24 — strict body for provider flagging.

    `reason_code` is validated against the canonical FLAG_REASONS set here
    rather than silently coerced to "other" deep in the service, so a caller
    learns its reason was invalid. No tenant, actor or status field is
    accepted.
    """
    model_config = ConfigDict(extra="forbid")
    reason_code: Literal["spam", "fake", "offensive", "irrelevant", "other"] = "other"
    reason_text: str | None = Field(default=None, max_length=2000)


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
    # Slice 2F-24: was an unscoped primary-key read -- any authenticated
    # principal could fetch any review in any tenant, including pending,
    # hidden, rejected and deleted reviews together with their moderation and
    # rejection reasons. Now scoped to the caller's own tenant, so a foreign
    # review id is indistinguishable from a missing one.
    review = await _svc.get_review(db, uuid.UUID(review_id), tenant_id=user.tenant_id)
    return ok(review.to_dict(), rid, "provider.review.fetched")


@provider_review_router.post("/{review_id}/reply")
async def submit_reply(
    review_id: str,
    body: ProviderReplyRequest,
    r: Request,
    user=Depends(require_tenant_owner_mutation),
    db: AsyncSession = Depends(get_db),
):
    # Slice 2F-24: was `Depends(get_current_user)`, so ANY authenticated
    # principal -- including a `customer` of this tenant -- could post the
    # official provider reply. The service hardcodes ACTOR_PROVIDER on the
    # resulting event, so a customer's text was attributed to the business in
    # the audit trail. Now restricted to the canonical provider-side persona
    # with mutation-capable access scope.
    import uuid
    rid = getattr(r.state, "request_id", "—")
    reply = await _svc.submit_reply(
        db,
        review_id          = uuid.UUID(review_id),
        tenant_id          = user.tenant_id,
        replied_by_user_id = user.user_id,
        reply_text         = body.reply_text,
        request_id         = rid,
    )
    return ok(reply.to_dict(), rid, "provider.reply.submitted")


@provider_review_router.post("/{review_id}/flag")
async def flag_review(
    review_id: str,
    body: ReviewFlagRequest,
    r: Request,
    user=Depends(require_tenant_owner_mutation),
    db: AsyncSession = Depends(get_db),
):
    # Slice 2F-24: this was the most serious defect in the module. The route
    # was bare-authenticated AND the service performed no ownership check at
    # all (primary-key-only lookup), so any authenticated principal could set
    # `status = flagged` on any review in any tenant. Ownership is now proven
    # inside the service by the central scoped lookup, using the JWT tenant.
    import uuid
    rid = getattr(r.state, "request_id", "—")
    flag = await _svc.flag_review(
        db,
        review_id          = uuid.UUID(review_id),
        flagged_by_user_id = user.user_id,
        # Server-set, never client-supplied: this route is the provider surface.
        flagged_by_type    = "provider",
        reason_code        = body.reason_code,
        reason_text        = body.reason_text,
        tenant_id          = user.tenant_id,
        request_id         = rid,
    )
    return ok(flag.to_dict(), rid, "provider.review.flagged")
