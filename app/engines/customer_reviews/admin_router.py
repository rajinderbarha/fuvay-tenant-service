"""Sprint 24 — Admin Review endpoints (enterprise-upgraded)."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, func, case, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from pydantic import BaseModel, ConfigDict, Field
from app.dependencies.auth import get_current_user, UserContext, require_super_admin
from app.dependencies.db import get_db
from app.schemas.base import ok
from app.engines.customer_reviews.review_service import ReviewService
from app.engines.customer_reviews.aggregation_service import RatingAggregationService
from app.engines.customer_reviews.models import (
    CustomerReview, ReviewFlag, ReviewReply, ReviewEvent,
    TenantRatingSummary, StaffRatingSummary,
)

admin_review_router  = APIRouter(prefix="/v1/admin/reviews",         tags=["admin-reviews"])
admin_flag_router    = APIRouter(prefix="/v1/admin/review-flags",    tags=["admin-reviews"])
admin_reply_router   = APIRouter(prefix="/v1/admin/review-replies",  tags=["admin-reviews"])
admin_policy_router  = APIRouter(prefix="/v1/admin/review-policies", tags=["admin-reviews"])
admin_rating_router  = APIRouter(prefix="/v1/admin/rating-summaries",tags=["admin-reviews"])

_svc = ReviewService()
_agg = RatingAggregationService()

_utcnow = lambda: datetime.now(timezone.utc)


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


# ── Reviews list (platform-wide, enterprise) ───────────────────────────────────
@admin_review_router.get("/summary", summary="Platform-wide review summary cards")
async def reviews_summary(
    r: Request,
    tenant_id: str | None = Query(None),
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    now = _utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    base = select(
        func.count(CustomerReview.id).label("total"),
        func.sum(case((CustomerReview.created_at >= today_start, 1), else_=0)).label("today"),
        func.avg(CustomerReview.overall_rating).label("avg_rating"),
        func.sum(case((CustomerReview.overall_rating <= 2, 1), else_=0)).label("low_rating"),
        func.sum(case((CustomerReview.status == "flagged", 1), else_=0)).label("flagged"),
        func.sum(case((CustomerReview.status == "pending", 1), else_=0)).label("pending_moderation"),
        func.sum(case((CustomerReview.overall_rating == 5, 1), else_=0)).label("five_star"),
        func.sum(case((CustomerReview.overall_rating >= 4, 1), else_=0)).label("positive"),
        func.sum(case((CustomerReview.overall_rating == 3, 1), else_=0)).label("neutral"),
        func.sum(case((CustomerReview.overall_rating <= 2, 1), else_=0)).label("negative"),
    )

    if tenant_id:
        try:
            base = base.where(CustomerReview.tenant_id == uuid.UUID(tenant_id))
        except ValueError:
            pass

    row = (await db.execute(base)).one()

    # count reviews that have a reply
    reply_q = select(func.count(ReviewReply.id.distinct())).where(ReviewReply.status.in_(["approved", "pending"]))
    if tenant_id:
        try:
            reply_q = reply_q.where(ReviewReply.tenant_id == uuid.UUID(tenant_id))
        except ValueError:
            pass
    replied_count = (await db.execute(reply_q)).scalar() or 0

    total = int(row.total or 0)

    return ok({
        "total":              total,
        "today":              int(row.today or 0),
        "avg_rating":         round(float(row.avg_rating), 2) if row.avg_rating else 0.0,
        "low_rating":         int(row.low_rating or 0),
        "flagged":            int(row.flagged or 0),
        "pending_moderation": int(row.pending_moderation or 0),
        "five_star":          int(row.five_star or 0),
        "positive":           int(row.positive or 0),
        "neutral":            int(row.neutral or 0),
        "negative":           int(row.negative or 0),
        "unreplied":          max(0, total - replied_count),
        "replied":            replied_count,
    }, _rid(r), "admin.reviews.summary")


@admin_review_router.get("", summary="Platform-wide review list (enterprise, paginated)")
async def list_reviews(
    r: Request,
    q: str | None = Query(None, description="Search review text / customer / tenant / booking#"),
    tenant_id: str | None = Query(None),
    job_id: str | None = Query(None, description="Filter to the review left for one specific job"),
    rating: int | None = Query(None, ge=1, le=5),
    rating_min: int | None = Query(None, ge=1, le=5),
    rating_max: int | None = Query(None, ge=1, le=5),
    status: str | None = Query(None),
    record_type: str | None = Query(None),
    has_reply: bool | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_dir: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.engines.tenant_engine.models import Tenant
    from app.engines.auth.models import User as AuthUser

    CustomerUser = aliased(AuthUser)

    # Base query: join tenant + customer user + left-join reply
    stmt = (
        select(
            CustomerReview,
            Tenant.tenant_name,
            CustomerUser.full_name.label("customer_name"),
            CustomerUser.phone.label("customer_phone"),
            ReviewReply.reply_text,
            ReviewReply.submitted_at.label("replied_at"),
        )
        .join(Tenant, Tenant.id == CustomerReview.tenant_id)
        .outerjoin(CustomerUser, CustomerUser.id == CustomerReview.customer_id)
        .outerjoin(ReviewReply, ReviewReply.review_id == CustomerReview.id)
    )

    # Filters
    if tenant_id:
        try:
            stmt = stmt.where(CustomerReview.tenant_id == uuid.UUID(tenant_id))
        except ValueError:
            pass
    if job_id:
        try:
            stmt = stmt.where(CustomerReview.job_id == uuid.UUID(job_id))
        except ValueError:
            pass
    if rating:
        stmt = stmt.where(CustomerReview.overall_rating == rating)
    else:
        if rating_min:
            stmt = stmt.where(CustomerReview.overall_rating >= rating_min)
        if rating_max:
            stmt = stmt.where(CustomerReview.overall_rating <= rating_max)
    if status:
        stmt = stmt.where(CustomerReview.status == status)
    if record_type:
        stmt = stmt.where(CustomerReview.record_type == record_type)
    if has_reply is True:
        stmt = stmt.where(ReviewReply.id.is_not(None))
    elif has_reply is False:
        stmt = stmt.where(ReviewReply.id.is_(None))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            CustomerReview.review_text.ilike(like) |
            CustomerReview.review_title.ilike(like) |
            CustomerReview.review_number.ilike(like) |
            CustomerUser.full_name.ilike(like) |
            Tenant.tenant_name.ilike(like)
        )

    # Count total (before pagination)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Sort
    sort_col = {
        "created_at":    CustomerReview.created_at,
        "overall_rating": CustomerReview.overall_rating,
        "submitted_at":  CustomerReview.submitted_at,
        "updated_at":    CustomerReview.updated_at,
    }.get(sort_by, CustomerReview.created_at)
    stmt = stmt.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())

    # Pagination
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).all()

    items = []
    for rev, tenant_name, customer_name, customer_phone, reply_text, replied_at in rows:
        d = rev.to_dict()
        d["tenant_name"]    = tenant_name
        d["customer_name"]  = customer_name
        d["customer_phone"] = customer_phone
        d["has_reply"]      = reply_text is not None
        d["reply_text"]     = reply_text
        d["replied_at"]     = replied_at.isoformat() if replied_at else None
        # Derive sentiment from rating
        rating_val = rev.overall_rating
        if rating_val >= 4:
            d["sentiment"] = "positive"
        elif rating_val == 3:
            d["sentiment"] = "neutral"
        else:
            d["sentiment"] = "negative"
        d["has_media"] = bool(rev.media_urls)
        items.append(d)

    total_pages = max(1, (total + page_size - 1) // page_size)
    return ok({
        "items": items,
        "meta": {
            "page": page, "page_size": page_size,
            "total": total, "total_pages": total_pages,
            "has_next": page < total_pages, "has_previous": page > 1,
        },
    }, _rid(r), "admin.reviews.list")


@admin_review_router.get("/{review_id}", summary="Get review detail")
async def get_review(
    review_id: str,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    # Slice 2F-24: `get_review` now requires a tenant or customer scope and
    # fails closed without one. The platform-admin surface is legitimately
    # cross-tenant (this whole router is `require_super_admin`), so it reads
    # through the explicitly-unscoped internal helper rather than being handed
    # a fake scope. The intent is visible at the call site.
    review = await _svc._get_review(db, uuid.UUID(review_id))
    # Enrich with reply
    reply_res = await db.execute(
        select(ReviewReply).where(ReviewReply.review_id == uuid.UUID(review_id))
    )
    reply = reply_res.scalar_one_or_none()
    d = review.to_dict()
    d["reply"] = reply.to_dict() if reply else None
    return ok(d, _rid(r), "admin.review.fetched")


@admin_review_router.put("/{review_id}")
async def edit_review(
    review_id: str,
    body: dict,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    review = await _svc.admin_edit_review(db, uuid.UUID(review_id), u.user_id, body, request_id=_rid(r))
    return ok(review.to_dict(), _rid(r), "admin.review.edited")


@admin_review_router.post("/{review_id}/approve")
async def approve_review(
    review_id: str,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    review = await _svc.approve_review(db, uuid.UUID(review_id), u.user_id, request_id=_rid(r))
    return ok(review.to_dict(), _rid(r), "admin.review.approved")


@admin_review_router.post("/{review_id}/reject")
async def reject_review(
    review_id: str,
    body: dict,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    review = await _svc.reject_review(
        db, uuid.UUID(review_id), u.user_id,
        reason=body.get("reason", "Policy violation"),
        request_id=_rid(r),
    )
    return ok(review.to_dict(), _rid(r), "admin.review.rejected")


@admin_review_router.post("/{review_id}/hide")
async def hide_review(
    review_id: str,
    body: dict,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    review = await _svc.hide_review(
        db, uuid.UUID(review_id), u.user_id,
        reason=body.get("reason"),
        request_id=_rid(r),
    )
    return ok(review.to_dict(), _rid(r), "admin.review.hidden")


@admin_review_router.delete("/{review_id}")
async def delete_review(
    review_id: str,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    review = await _svc.delete_review(db, uuid.UUID(review_id), u.user_id, request_id=_rid(r))
    return ok(review.to_dict(), _rid(r), "admin.review.deleted")


@admin_review_router.get("/{review_id}/events")
async def get_review_events(
    review_id: str,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    events = await _svc.list_events(db, uuid.UUID(review_id))
    return ok([e.to_dict() for e in events], _rid(r), "admin.review.events")


# ── Flags ──────────────────────────────────────────────────────────────────────
@admin_flag_router.get("")
async def list_flags(
    status: str | None = None,
    r: Request = None,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    flags = await _svc.list_flags(db, status=status)
    return ok([f.to_dict() for f in flags], _rid(r), "admin.flags.list")


@admin_flag_router.post("/{flag_id}/resolve")
async def resolve_flag(
    flag_id: str,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    flag = await _svc.resolve_flag(db, uuid.UUID(flag_id), u.user_id, request_id=_rid(r))
    return ok(flag.to_dict(), _rid(r), "admin.flag.resolved")


# ── Replies ────────────────────────────────────────────────────────────────────
@admin_reply_router.get("")
async def list_replies(
    status: str | None = None,
    r: Request = None,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    q = select(ReviewReply)
    if status:
        q = q.where(ReviewReply.status == status)
    q = q.order_by(ReviewReply.created_at.desc()).limit(100)
    res = await db.execute(q)
    replies = res.scalars().all()
    return ok([rp.to_dict() for rp in replies], _rid(r), "admin.replies.list")


@admin_reply_router.post("/{review_id}/approve")
async def approve_reply(
    review_id: str,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    reply = await _svc.approve_reply(db, uuid.UUID(review_id), u.user_id, request_id=_rid(r))
    return ok(reply.to_dict(), _rid(r), "admin.reply.approved")


@admin_reply_router.post("/{review_id}/reject")
async def reject_reply(
    review_id: str,
    body: dict,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    reply = await _svc.reject_reply(
        db, uuid.UUID(review_id), u.user_id,
        reason=body.get("reason", "Policy violation"),
        request_id=_rid(r),
    )
    return ok(reply.to_dict(), _rid(r), "admin.reply.rejected")


# ── Policies ───────────────────────────────────────────────────────────────────
@admin_policy_router.get("")
async def list_policies(
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    policies = await _svc.list_policies(db)
    return ok([p.to_dict() for p in policies], _rid(r), "admin.policies.list")


class CreateReviewPolicyIn(BaseModel):
    """Strict body for policy creation.

    `policy_key`/`policy_name` are the only NOT NULL columns without a default;
    everything else falls back to the model defaults, which are the safe
    (moderated) settings.
    """
    model_config = ConfigDict(extra="forbid")
    policy_key: str = Field(..., min_length=1, max_length=80)
    policy_name: str = Field(..., min_length=1, max_length=200)
    tenant_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    auto_approve_enabled: bool | None = None
    require_admin_moderation: bool | None = None
    allow_provider_reply: bool | None = None
    require_reply_moderation: bool | None = None
    allow_review_edit: bool | None = None
    edit_window_hours: int | None = Field(None, ge=0, le=8760)
    min_rating: int | None = Field(None, ge=1, le=5)
    max_rating: int | None = Field(None, ge=1, le=5)
    allow_media: bool | None = None
    max_media_count: int | None = Field(None, ge=0, le=50)
    is_active: bool | None = None


@admin_policy_router.post("", status_code=201)
async def create_policy(
    body: CreateReviewPolicyIn,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a review policy.

    Real gap closed: this resource had list/get/patch but no create, and the
    table ships empty -- so there was nothing to patch, `_get_policy` always
    resolved to None, and every submitted review stayed `pending`/private
    forever because auto-approval could not be turned on.
    """
    p = await _svc.create_policy(db, body.model_dump(exclude_none=True))
    return ok(p.to_dict(), _rid(r), "admin.policy.created")


@admin_policy_router.get("/{policy_id}")
async def get_policy(
    policy_id: str,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    p = await _svc.get_policy(db, uuid.UUID(policy_id))
    return ok(p.to_dict(), _rid(r), "admin.policy.fetched")


@admin_policy_router.patch("/{policy_id}")
async def update_policy(
    policy_id: str,
    body: dict,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    p = await _svc.update_policy(db, uuid.UUID(policy_id), body)
    return ok(p.to_dict(), _rid(r), "admin.policy.updated")


# ── Rating Summaries ───────────────────────────────────────────────────────────
@admin_rating_router.get("")
async def list_tenant_summaries(
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(TenantRatingSummary).order_by(TenantRatingSummary.average_rating.desc()))
    summaries = res.scalars().all()
    return ok([s.to_dict() for s in summaries], _rid(r), "admin.rating_summaries.list")


@admin_rating_router.get("/staff")
async def list_staff_summaries(
    tenant_id: str | None = None,
    r: Request = None,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    q = select(StaffRatingSummary)
    if tenant_id:
        q = q.where(StaffRatingSummary.tenant_id == uuid.UUID(tenant_id))
    q = q.order_by(StaffRatingSummary.average_rating.desc())
    res = await db.execute(q)
    summaries = res.scalars().all()
    return ok([s.to_dict() for s in summaries], _rid(r), "admin.staff_summaries.list")


@admin_rating_router.post("/tenant/{tenant_id}/recompute")
async def recompute_tenant_summary(
    tenant_id: str,
    r: Request,
    u: UserContext = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    summary = await _agg.recompute_tenant_summary(db, uuid.UUID(tenant_id))
    await db.commit()
    return ok(summary.to_dict(), _rid(r), "admin.rating_summary.recomputed")
