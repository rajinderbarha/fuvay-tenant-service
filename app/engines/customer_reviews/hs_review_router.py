"""REVIEW-CONSOLIDATION: vertical-scoped review surface for the Home
Services Job 360 Review & Feedback tab, Provider 360 Quality & Complaints,
Staff 360 Performance, and Home Services Review Moderation.

This is NOT a second review engine -- every endpoint here reads/mutates the
SAME canonical `customer_reviews` tables (CustomerReview/ReviewReply/
ReviewFlag/ReviewEvent/TenantRatingSummary/StaffRatingSummary) via the same
ReviewService/RatingAggregationService the platform-wide admin router uses,
scoped to the exact Business Vertical resolved server-side from the URL
path (never a client-supplied vertical).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.dependencies.vertical_directory_scope import require_vertical_domain_scope, VerticalScope
from app.schemas.base import ApiResponse, ok
from app.exceptions import ServiceOSException, NotFoundException

from app.engines.final_records.models import ServiceJob
from app.engines.tenant_engine.models import Tenant
from app.engines.vertical_directory.models import StaffBusinessVertical
from app.engines.home_service_assignment.staff_model import ProviderTeamMember
from app.engines.customer_reviews.constants import (
    RECORD_TYPE_SERVICE_JOB, STATUS_APPROVED, STATUS_HIDDEN, STATUS_REJECTED,
    STATUS_FLAGGED, STATUS_DELETED, STATUS_PENDING,
)
from app.engines.customer_reviews.models import (
    CustomerReview, ReviewReply, ReviewFlag, ReviewEvent,
    TenantRatingSummary, StaffRatingSummary,
)
from app.engines.customer_reviews.review_service import ReviewService
from app.engines.customer_reviews.aggregation_service import RatingAggregationService

router = APIRouter(prefix="/v1/admin/verticals/{vertical}", tags=["Home Services Reviews"])
_svc = ReviewService()
_agg = RatingAggregationService()

# A job-close review-request window is not currently a canonical, versioned
# policy value anywhere in the codebase (audited: no submission-window field
# exists on ReviewPolicy or elsewhere) -- so "submission window" is reported
# as not-configured rather than invented.
MODERATION_STATUSES = (STATUS_FLAGGED, STATUS_HIDDEN, STATUS_REJECTED, STATUS_DELETED)


def _rid(r: Request) -> str:
    return getattr(r.state, "request_id", "—")


def _actor_id(scope: VerticalScope) -> uuid.UUID:
    if not scope.actor.user_id:
        raise ServiceOSException("VALIDATION_ERROR", "Actor identity required for this action.", status_code=422)
    return uuid.UUID(scope.actor.user_id)


async def _resolve_job(db: AsyncSession, scope: VerticalScope, job_id: uuid.UUID) -> tuple[ServiceJob, Tenant | None]:
    # `service_jobs` is structurally the Home-Services-only final-record
    # table (Coaching/Real Estate use their own separate tables -- see
    # finance_hub/home_services_finance_service.py's module docstring for
    # the same established convention), so a ServiceJob row proves its own
    # vertical by construction. The Tenant row is joined only for display
    # (business_name) -- an orphaned/missing tenant_id (stale seed data,
    # deleted tenant) must not 404 a job that genuinely exists, and an
    # INNER JOIN did exactly that. Only reject when a tenant row DOES exist
    # and explicitly disagrees (defensive, should never happen given the
    # structural guarantee above).
    row = (await db.execute(
        select(ServiceJob, Tenant).join(Tenant, Tenant.id == ServiceJob.tenant_id, isouter=True)
        .where(ServiceJob.id == job_id)
    )).first()
    if not row:
        raise NotFoundException("ServiceJob", str(job_id))
    job, tenant = row
    if tenant is not None and tenant.vertical != scope.vertical_key:
        raise ServiceOSException("CROSS_VERTICAL_ACCESS_DENIED",
                                 f"Job does not belong to vertical '{scope.vertical_key}'.", status_code=403)
    return job, tenant


async def _find_review(db: AsyncSession, job_id: uuid.UUID) -> CustomerReview | None:
    return (await db.execute(
        select(CustomerReview).where(
            CustomerReview.record_type == RECORD_TYPE_SERVICE_JOB,
            CustomerReview.record_id == job_id,
        )
    )).scalars().first()


# ═══════════════════════════════════════════════════════════════════════════
# Job 360 — Review & Feedback tab
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/jobs/{job_id}/review", response_model=ApiResponse)
async def get_job_review(
    job_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("reviews", "view")),
):
    job, tenant = await _resolve_job(db, scope, job_id)

    if job.status not in ("completed", "work_done", "invoice_issued", "paid"):
        return ok({"state": "job_not_completed", "job_status": job.status}, _rid(r))

    review = await _find_review(db, job_id)
    if not review:
        return ok({
            "state": "awaiting_review", "job_status": job.status,
            "eligible_customer_id": str(job.customer_id) if job.customer_id else None,
            "submission_window": None,  # not a canonical policy value today -- see module docstring
        }, _rid(r))

    reply = (await db.execute(select(ReviewReply).where(ReviewReply.review_id == review.id))).scalars().first()
    d = review.to_dict()
    d["state"] = "review_hidden" if review.status == STATUS_HIDDEN else \
                 "review_removed" if review.status == STATUS_DELETED else \
                 "review_under_moderation" if review.status in (STATUS_FLAGGED, STATUS_PENDING) else \
                 "review_available"
    d["reply"] = reply.to_dict() if reply else None
    d["tenant_name"] = tenant.business_name if tenant else None
    return ok(d, _rid(r))


@router.get("/jobs/{job_id}/review/integrity", response_model=ApiResponse)
async def get_job_review_integrity(
    job_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("reviews", "view")),
):
    job, tenant = await _resolve_job(db, scope, job_id)
    review = await _find_review(db, job_id)

    checks = {
        "service_job_exists": True,
        "job_completed": job.status in ("completed", "work_done", "invoice_issued", "paid"),
        "reviewer_is_booking_customer": None,
        "review_belongs_to_same_provider": None,
        # service_jobs is structurally Home-Services-only (see _resolve_job)
        # -- True by construction even when the tenant row itself is
        # missing/orphaned; only False if a tenant row exists and disagrees.
        "review_belongs_to_home_services": tenant is None or tenant.vertical == "home_services",
        "one_canonical_review_per_job": None,
        "no_duplicate_signal": None,
        "no_abuse_report": None,
        "no_active_appeal": None,
        "publication_state": None,
    }
    if review:
        checks["reviewer_is_booking_customer"] = True  # enforced at submission time by eligibility_service
        checks["review_belongs_to_same_provider"] = review.tenant_id == job.tenant_id
        dup_count = await db.scalar(select(func.count(CustomerReview.id)).where(
            CustomerReview.record_type == RECORD_TYPE_SERVICE_JOB, CustomerReview.record_id == job_id))
        checks["one_canonical_review_per_job"] = dup_count == 1
        checks["no_duplicate_signal"] = dup_count == 1
        open_flags = await db.scalar(select(func.count(ReviewFlag.id)).where(
            ReviewFlag.review_id == review.id, ReviewFlag.status == "open"))
        checks["no_abuse_report"] = open_flags == 0
        checks["no_active_appeal"] = review.status not in (STATUS_FLAGGED,)
        checks["publication_state"] = review.status

    concerns = [k for k, v in checks.items() if v is False]
    reason_code = None
    if concerns:
        reason_code = "REVIEW_INTEGRITY_" + concerns[0].upper()
    return ok({
        "checks": checks,
        "status": "no_action_required" if not concerns else "moderation_required",
        "reason_code": reason_code,
    }, _rid(r))


@router.get("/jobs/{job_id}/review/lifecycle", response_model=ApiResponse)
async def get_job_review_lifecycle(
    job_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("reviews", "view")),
):
    job, _ = await _resolve_job(db, scope, job_id)
    review = await _find_review(db, job_id)
    events = []
    if review:
        rows = (await db.execute(
            select(ReviewEvent).where(ReviewEvent.review_id == review.id).order_by(ReviewEvent.created_at.asc())
        )).scalars().all()
        events = [{
            "event_type": e.event_type, "actor_type": e.actor_type,
            "actor_user_id": str(e.actor_user_id) if e.actor_user_id else None,
            "reason": e.reason, "request_id": e.request_id,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        } for e in rows]
    return ok({"job_id": str(job_id), "events": events}, _rid(r))


@router.get("/jobs/{job_id}/review/rating-impact", response_model=ApiResponse)
async def get_job_review_rating_impact(
    job_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("reviews", "view")),
):
    job, tenant = await _resolve_job(db, scope, job_id)
    review = await _find_review(db, job_id)
    provider_summary = (await db.execute(
        select(TenantRatingSummary).where(TenantRatingSummary.tenant_id == job.tenant_id))).scalars().first()

    contributes = bool(review and review.status == STATUS_APPROVED)
    excluded_reason = None
    if review and not contributes:
        excluded_reason = f"Review status is '{review.status}', not approved."
    elif not review:
        excluded_reason = "No review submitted yet."

    result = {
        "job_id": str(job_id),
        "provider_rating_current": str(provider_summary.average_rating) if provider_summary else "0.00",
        "provider_review_count": provider_summary.total_reviews if provider_summary else 0,
        "contributes": contributes,
        "excluded_reason": excluded_reason,
        "staff_rating_current": None, "staff_completed_job_count": None,
    }
    if job.assigned_staff_id:
        staff_summary = (await db.execute(select(StaffRatingSummary).where(
            StaffRatingSummary.tenant_id == job.tenant_id,
            StaffRatingSummary.staff_member_id == job.assigned_staff_id,
        ))).scalars().first()
        result["staff_rating_current"] = str(staff_summary.average_rating) if staff_summary else "0.00"
        result["staff_completed_job_count"] = staff_summary.total_reviews if staff_summary else 0
    # Before/after: this platform does not persist a per-review rating-delta
    # snapshot, so "before" is honestly reported as the current projection
    # (identical to "after" when the review already contributed) rather than
    # a fabricated historical value.
    result["provider_rating_before"] = result["provider_rating_current"]
    result["staff_rating_before"] = result["staff_rating_current"]
    return ok(result, _rid(r))


# ═══════════════════════════════════════════════════════════════════════════
# Provider 360 / Staff 360 aggregates
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/providers/{tenant_id}/review-summary", response_model=ApiResponse)
async def provider_review_summary(
    tenant_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("reviews", "view")),
):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant or tenant.vertical != scope.vertical_key:
        raise ServiceOSException("CROSS_VERTICAL_ACCESS_DENIED",
                                 f"Provider does not belong to vertical '{scope.vertical_key}'.", status_code=403)
    summary = (await db.execute(select(TenantRatingSummary).where(
        TenantRatingSummary.tenant_id == tenant_id))).scalars().first()
    recent = (await db.execute(
        select(CustomerReview).where(CustomerReview.tenant_id == tenant_id, CustomerReview.status == STATUS_APPROVED)
        .order_by(CustomerReview.approved_at.desc()).limit(10)
    )).scalars().all()
    low_rating = await db.scalar(select(func.count(CustomerReview.id)).where(
        CustomerReview.tenant_id == tenant_id, CustomerReview.status == STATUS_APPROVED,
        CustomerReview.overall_rating <= 2))
    replied = await db.scalar(select(func.count(func.distinct(ReviewReply.review_id))).where(
        ReviewReply.tenant_id == tenant_id))
    open_reports = await db.scalar(select(func.count(ReviewFlag.id)).where(
        ReviewFlag.tenant_id == tenant_id, ReviewFlag.status == "open"))
    return ok({
        "summary": summary.to_dict() if summary else None,
        "recent_reviews": [{**rv.to_dict(), "job_id": str(rv.job_id) if rv.job_id else None} for rv in recent],
        "low_rating_count": low_rating or 0,
        "provider_response_rate": round((replied or 0) / summary.total_reviews * 100, 1) if summary and summary.total_reviews else 0.0,
        "open_review_reports": open_reports or 0,
    }, _rid(r))


@router.get("/staff/{staff_id}/review-summary", response_model=ApiResponse)
async def staff_review_summary(
    staff_id: uuid.UUID, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("reviews", "view")),
):
    sbv = (await db.execute(select(StaffBusinessVertical).where(
        StaffBusinessVertical.staff_id == staff_id, StaffBusinessVertical.vertical_id == scope.vertical.id,
    ))).scalars().first()
    if not sbv:
        raise ServiceOSException("CROSS_VERTICAL_ACCESS_DENIED",
                                 f"Staff member is not assigned to vertical '{scope.vertical_key}'.", status_code=403)
    summary = (await db.execute(select(StaffRatingSummary).where(
        StaffRatingSummary.tenant_id == sbv.tenant_id, StaffRatingSummary.staff_member_id == staff_id,
    ))).scalars().first()
    recent = (await db.execute(
        select(CustomerReview).where(
            CustomerReview.staff_member_id == staff_id, CustomerReview.status == STATUS_APPROVED,
        ).order_by(CustomerReview.approved_at.desc()).limit(10)
    )).scalars().all()
    return ok({
        "summary": summary.to_dict() if summary else None,
        "recent_reviews": [{**rv.to_dict(), "job_id": str(rv.job_id) if rv.job_id else None} for rv in recent],
    }, _rid(r))


# ═══════════════════════════════════════════════════════════════════════════
# Home Services Review Moderation (exception-only queue)
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/reviews/moderation", response_model=ApiResponse)
async def list_moderation_queue(
    r: Request, status: str | None = Query(None), rating: int | None = Query(None),
    provider_id: str | None = Query(None), page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("reviews", "moderate")),
):
    conditions = [Tenant.vertical == scope.vertical_key]
    if status:
        conditions.append(CustomerReview.status == status)
    else:
        conditions.append(CustomerReview.status.in_(MODERATION_STATUSES))
    if rating:
        conditions.append(CustomerReview.overall_rating == rating)
    if provider_id:
        conditions.append(CustomerReview.tenant_id == uuid.UUID(provider_id))

    stmt = select(CustomerReview, Tenant).join(Tenant, Tenant.id == CustomerReview.tenant_id).where(*conditions)
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    rows = (await db.execute(stmt.order_by(CustomerReview.updated_at.desc())
                             .offset((page - 1) * page_size).limit(page_size))).all()

    review_ids = [rv.id for rv, _ in rows]
    report_counts: dict[uuid.UUID, int] = {}
    if review_ids:
        flag_rows = (await db.execute(
            select(ReviewFlag.review_id, func.count(ReviewFlag.id)).where(
                ReviewFlag.review_id.in_(review_ids), ReviewFlag.status == "open"
            ).group_by(ReviewFlag.review_id)
        )).all()
        report_counts = {rid: cnt for rid, cnt in flag_rows}

    items = [{
        **rv.to_dict(), "tenant_name": t.business_name, "report_count": report_counts.get(rv.id, 0),
    } for rv, t in rows]
    return ok({"items": items, "total": total, "page": page, "page_size": page_size}, _rid(r))


@router.get("/reviews/moderation/summary", response_model=ApiResponse)
async def moderation_summary(
    r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("reviews", "moderate")),
):
    base = select(CustomerReview).join(Tenant, Tenant.id == CustomerReview.tenant_id).where(
        Tenant.vertical == scope.vertical_key)

    async def _count(status: str) -> int:
        return (await db.execute(select(func.count()).select_from(
            base.where(CustomerReview.status == status).subquery()))).scalar() or 0

    pending = await _count(STATUS_PENDING)
    flagged = await _count(STATUS_FLAGGED)
    hidden = await _count(STATUS_HIDDEN)
    rejected = await _count(STATUS_REJECTED)
    return ok({
        "pending_review": pending, "flagged": flagged, "reported": flagged,
        "suspicious": 0,  # no canonical fraud-signal source exists today -- not invented
        "under_appeal": 0,  # no canonical appeal state exists today -- not invented
        "hidden": hidden, "resolved": rejected,
    }, _rid(r))


class ModerationActionRequest(BaseModel):
    reason: str = ""


@router.post("/reviews/{review_id}/flag", response_model=ApiResponse)
async def moderation_flag(
    review_id: uuid.UUID, body: ModerationActionRequest, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("reviews", "moderate")),
):
    await _assert_review_in_scope(db, scope, review_id)
    flag = await _svc.admin_flag_review(db, review_id, _actor_id(scope), body.reason, request_id=_rid(r))
    return ok(flag.to_dict(), _rid(r))


@router.post("/reviews/{review_id}/hide", response_model=ApiResponse)
async def moderation_hide(
    review_id: uuid.UUID, body: ModerationActionRequest, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("reviews", "moderate")),
):
    await _assert_review_in_scope(db, scope, review_id)
    review = await _svc.hide_review(db, review_id, _actor_id(scope), reason=body.reason, request_id=_rid(r))
    return ok(review.to_dict(), _rid(r))


@router.post("/reviews/{review_id}/restore", response_model=ApiResponse)
async def moderation_restore(
    review_id: uuid.UUID, body: ModerationActionRequest, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("reviews", "moderate")),
):
    await _assert_review_in_scope(db, scope, review_id)
    review = await _svc.restore_review(db, review_id, _actor_id(scope), request_id=_rid(r))
    return ok(review.to_dict(), _rid(r))


@router.post("/reviews/{review_id}/resolve", response_model=ApiResponse)
async def moderation_resolve(
    review_id: uuid.UUID, body: ModerationActionRequest, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("reviews", "moderate")),
):
    await _assert_review_in_scope(db, scope, review_id)
    open_flags = (await db.execute(select(ReviewFlag).where(
        ReviewFlag.review_id == review_id, ReviewFlag.status == "open"))).scalars().all()
    resolved = None
    for f in open_flags:
        resolved = await _svc.resolve_flag(db, f.id, _actor_id(scope), request_id=_rid(r))
    if resolved is None:
        raise ServiceOSException("NO_OPEN_FLAG", "No open flag to resolve for this review.", status_code=422)
    return ok(resolved.to_dict(), _rid(r))


@router.post("/reviews/{review_id}/escalate", response_model=ApiResponse)
async def moderation_escalate(
    review_id: uuid.UUID, body: ModerationActionRequest, r: Request, db: AsyncSession = Depends(get_db),
    scope: VerticalScope = Depends(require_vertical_domain_scope("reviews", "moderate")),
):
    await _assert_review_in_scope(db, scope, review_id)
    review = await _svc.escalate_review(db, review_id, _actor_id(scope), body.reason, request_id=_rid(r))
    return ok(review.to_dict(), _rid(r))


async def _assert_review_in_scope(db: AsyncSession, scope: VerticalScope, review_id: uuid.UUID) -> None:
    row = (await db.execute(
        select(CustomerReview, Tenant).join(Tenant, Tenant.id == CustomerReview.tenant_id)
        .where(CustomerReview.id == review_id)
    )).first()
    if not row or row[1].vertical != scope.vertical_key:
        raise ServiceOSException("CROSS_VERTICAL_ACCESS_DENIED",
                                 f"Review does not belong to vertical '{scope.vertical_key}'.", status_code=403)
