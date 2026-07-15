"""Sprint 24 — Review Service (core business logic)."""
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.engines.customer_reviews.constants import (
    STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_HIDDEN,
    STATUS_DELETED, STATUS_FLAGGED,
    VISIBILITY_PRIVATE, VISIBILITY_PUBLIC, VISIBILITY_HIDDEN,
    REPLY_PENDING, REPLY_APPROVED, REPLY_REJECTED,
    FLAG_STATUS_OPEN, FLAG_STATUS_RESOLVED,
    ACTOR_CUSTOMER, ACTOR_PROVIDER, ACTOR_ADMIN, ACTOR_SYSTEM,
    EVT_REVIEW_SUBMITTED, EVT_REVIEW_EDITED, EVT_REVIEW_APPROVED,
    EVT_REVIEW_REJECTED, EVT_REVIEW_HIDDEN, EVT_REVIEW_DELETED,
    EVT_REPLY_SUBMITTED, EVT_REPLY_APPROVED, EVT_REPLY_REJECTED,
    EVT_FLAG_CREATED, EVT_FLAG_RESOLVED,
    ERR_REVIEW_NOT_FOUND, ERR_REVIEW_ALREADY_EXISTS, ERR_REVIEW_NOT_ELIGIBLE,
    ERR_REVIEW_NOT_EDITABLE, ERR_REVIEW_EDIT_WINDOW_CLOSED,
    ERR_REVIEW_ALREADY_APPROVED, ERR_REVIEW_INVALID_RATING,
    ERR_REPLY_NOT_FOUND, ERR_REPLY_ALREADY_EXISTS,
    ERR_FLAG_NOT_FOUND, ERR_POLICY_NOT_FOUND, ERR_PERMISSION_DENIED,
    VALID_RECORD_TYPES, FLAG_REASONS,
    RECORD_TYPE_SERVICE_BOOKING, RECORD_TYPE_SERVICE_JOB,
    RECORD_TYPE_COACHING_APPOINTMENT, RECORD_TYPE_REAL_ESTATE_LEAD,
)
from app.engines.customer_reviews.models import (
    CustomerReview, ReviewReply, ReviewFlag, ReviewEvent, ReviewPolicy,
)
from app.engines.customer_reviews.eligibility_service import ReviewEligibilityService
from app.engines.customer_reviews.aggregation_service import RatingAggregationService


def _num() -> str:
    import random, string
    return "REV-" + "".join(random.choices(string.digits, k=8))


class ReviewService:

    def __init__(self):
        self._eligibility = ReviewEligibilityService()
        self._aggregation = RatingAggregationService()

    # ── Customer: submit review ────────────────────────────────────────────────
    async def submit_review(
        self,
        db: AsyncSession,
        customer_id: uuid.UUID,
        tenant_id: uuid.UUID,
        record_type: str,
        record_id: uuid.UUID,
        overall_rating: int,
        *,
        provider_rating: int | None = None,
        staff_rating: int | None = None,
        communication_rating: int | None = None,
        punctuality_rating: int | None = None,
        quality_rating: int | None = None,
        value_rating: int | None = None,
        review_title: str | None = None,
        review_text: str | None = None,
        review_tags: list | None = None,
        media_urls: list | None = None,
        request_id: str = "—",
    ) -> CustomerReview:
        if record_type not in VALID_RECORD_TYPES:
            raise ValueError(ERR_REVIEW_NOT_ELIGIBLE)
        if not (1 <= overall_rating <= 5):
            raise ValueError(ERR_REVIEW_INVALID_RATING)

        result = await self._eligibility.check_eligible(db, customer_id, record_type, record_id)
        if not result["eligible"]:
            raise ValueError(ERR_REVIEW_NOT_ELIGIBLE)

        policy = await self._get_policy(db, tenant_id)
        initial_status    = STATUS_APPROVED if (policy and policy.auto_approve_enabled) else STATUS_PENDING
        initial_visibility = VISIBILITY_PUBLIC if initial_status == STATUS_APPROVED else VISIBILITY_PRIVATE

        review = CustomerReview(
            review_number    = _num(),
            customer_id      = customer_id,
            tenant_id        = tenant_id,
            record_type      = record_type,
            record_id        = record_id,
            overall_rating   = overall_rating,
            provider_rating  = provider_rating,
            staff_rating     = staff_rating,
            communication_rating = communication_rating,
            punctuality_rating   = punctuality_rating,
            quality_rating   = quality_rating,
            value_rating     = value_rating,
            review_title     = review_title,
            review_text      = review_text,
            review_tags      = review_tags,
            media_urls       = media_urls,
            status           = initial_status,
            visibility       = initial_visibility,
            submitted_at     = datetime.now(timezone.utc),
        )
        # Stamp record-specific FK
        if record_type == RECORD_TYPE_SERVICE_BOOKING:
            review.booking_id = record_id
        elif record_type == RECORD_TYPE_SERVICE_JOB:
            review.job_id = record_id
        elif record_type == RECORD_TYPE_COACHING_APPOINTMENT:
            review.appointment_id = record_id
        elif record_type == RECORD_TYPE_REAL_ESTATE_LEAD:
            review.lead_id = record_id

        db.add(review)
        await db.flush()
        await self._log_event(db, review.id, tenant_id, ACTOR_CUSTOMER, customer_id,
                              EVT_REVIEW_SUBMITTED, None, {"status": initial_status}, request_id)
        # MODULE-L5-22: tell the provider a review came in (was silent).
        from app.engines.customer_reviews.notifications import notify_provider_new_review
        await notify_provider_new_review(db, review)
        await db.commit()

        if initial_status == STATUS_APPROVED:
            await self._trigger_aggregation(db, review)

        return review

    # ── Customer: edit review ─────────────────────────────────────────────────
    async def edit_review(
        self,
        db: AsyncSession,
        review_id: uuid.UUID,
        customer_id: uuid.UUID,
        updates: dict,
        request_id: str = "—",
    ) -> CustomerReview:
        review = await self._get_review(db, review_id)
        if str(review.customer_id) != str(customer_id):
            raise ValueError(ERR_PERMISSION_DENIED)
        if review.status in (STATUS_DELETED, STATUS_REJECTED):
            raise ValueError(ERR_REVIEW_NOT_EDITABLE)

        policy = await self._get_policy(db, review.tenant_id)
        edit_window_hours = policy.edit_window_hours if policy else 48
        if review.submitted_at:
            age = (datetime.now(timezone.utc) - review.submitted_at.replace(tzinfo=timezone.utc))
            if age > timedelta(hours=edit_window_hours):
                raise ValueError(ERR_REVIEW_EDIT_WINDOW_CLOSED)

        old = {"overall_rating": review.overall_rating, "review_text": review.review_text}
        editable = ["overall_rating","provider_rating","staff_rating","communication_rating",
                    "punctuality_rating","quality_rating","value_rating",
                    "review_title","review_text","review_tags","media_urls"]
        for k in editable:
            if k in updates:
                setattr(review, k, updates[k])

        if "overall_rating" in updates and not (1 <= updates["overall_rating"] <= 5):
            raise ValueError(ERR_REVIEW_INVALID_RATING)

        review.edited_at = datetime.now(timezone.utc)
        review.status    = STATUS_PENDING
        review.visibility = VISIBILITY_PRIVATE
        await db.flush()
        await self._log_event(db, review.id, review.tenant_id, ACTOR_CUSTOMER, customer_id,
                              EVT_REVIEW_EDITED, old, updates, request_id)
        await db.commit()
        return review

    # ── Admin: approve review ─────────────────────────────────────────────────
    async def approve_review(
        self,
        db: AsyncSession,
        review_id: uuid.UUID,
        admin_user_id: uuid.UUID,
        request_id: str = "—",
    ) -> CustomerReview:
        review = await self._get_review(db, review_id)
        if review.status == STATUS_APPROVED:
            raise ValueError(ERR_REVIEW_ALREADY_APPROVED)
        old_status = review.status
        review.status     = STATUS_APPROVED
        review.visibility = VISIBILITY_PUBLIC
        review.approved_at = datetime.now(timezone.utc)
        await db.flush()
        await self._log_event(db, review.id, review.tenant_id, ACTOR_ADMIN, admin_user_id,
                              EVT_REVIEW_APPROVED, {"status": old_status}, {"status": STATUS_APPROVED}, request_id)
        await db.commit()
        await self._trigger_aggregation(db, review)
        return review

    # ── Admin: reject review ──────────────────────────────────────────────────
    async def reject_review(
        self,
        db: AsyncSession,
        review_id: uuid.UUID,
        admin_user_id: uuid.UUID,
        reason: str,
        request_id: str = "—",
    ) -> CustomerReview:
        review = await self._get_review(db, review_id)
        old_status = review.status
        review.status           = STATUS_REJECTED
        review.visibility       = VISIBILITY_HIDDEN
        review.rejection_reason = reason
        review.rejected_at      = datetime.now(timezone.utc)
        await db.flush()
        await self._log_event(db, review.id, review.tenant_id, ACTOR_ADMIN, admin_user_id,
                              EVT_REVIEW_REJECTED, {"status": old_status}, {"status": STATUS_REJECTED, "reason": reason}, request_id)
        await db.commit()
        return review

    # ── Admin: hide review ────────────────────────────────────────────────────
    async def hide_review(
        self,
        db: AsyncSession,
        review_id: uuid.UUID,
        admin_user_id: uuid.UUID,
        reason: str | None = None,
        request_id: str = "—",
    ) -> CustomerReview:
        review = await self._get_review(db, review_id)
        old_status = review.status
        review.status            = STATUS_HIDDEN
        review.visibility        = VISIBILITY_HIDDEN
        review.moderation_reason = reason
        review.hidden_at         = datetime.now(timezone.utc)
        await db.flush()
        await self._log_event(db, review.id, review.tenant_id, ACTOR_ADMIN, admin_user_id,
                              EVT_REVIEW_HIDDEN, {"status": old_status}, {"status": STATUS_HIDDEN}, request_id)
        await db.commit()
        await self._trigger_aggregation(db, review)
        return review

    # ── Admin: delete review ──────────────────────────────────────────────────
    async def delete_review(
        self,
        db: AsyncSession,
        review_id: uuid.UUID,
        admin_user_id: uuid.UUID,
        request_id: str = "—",
    ) -> CustomerReview:
        review = await self._get_review(db, review_id)
        old_status = review.status
        review.status     = STATUS_DELETED
        review.visibility = VISIBILITY_HIDDEN
        await db.flush()
        await self._log_event(db, review.id, review.tenant_id, ACTOR_ADMIN, admin_user_id,
                              EVT_REVIEW_DELETED, {"status": old_status}, {"status": STATUS_DELETED}, request_id)
        await db.commit()
        await self._trigger_aggregation(db, review)
        return review

    # ── Provider: submit reply ────────────────────────────────────────────────
    async def submit_reply(
        self,
        db: AsyncSession,
        review_id: uuid.UUID,
        tenant_id: uuid.UUID,
        replied_by_user_id: uuid.UUID,
        reply_text: str,
        request_id: str = "—",
    ) -> ReviewReply:
        review = await self._get_review(db, review_id)
        if str(review.tenant_id) != str(tenant_id):
            raise ValueError(ERR_PERMISSION_DENIED)

        existing = await db.execute(select(ReviewReply).where(ReviewReply.review_id == review_id))
        if existing.scalars().first():
            raise ValueError(ERR_REPLY_ALREADY_EXISTS)

        policy = await self._get_policy(db, tenant_id)
        require_mod   = policy.require_reply_moderation if policy else True
        initial_status = REPLY_PENDING if require_mod else REPLY_APPROVED

        reply = ReviewReply(
            review_id          = review_id,
            tenant_id          = tenant_id,
            replied_by_user_id = replied_by_user_id,
            reply_text         = reply_text,
            status             = initial_status,
            submitted_at       = datetime.now(timezone.utc),
        )
        db.add(reply)
        await db.flush()
        await self._log_event(db, review_id, tenant_id, ACTOR_PROVIDER, replied_by_user_id,
                              EVT_REPLY_SUBMITTED, None, {"status": initial_status}, request_id)
        # MODULE-L5-22: if the reply is live immediately (no moderation), tell the
        # customer their provider responded. If it needs moderation, the customer
        # is told on approval instead (see approve_reply).
        if initial_status == REPLY_APPROVED:
            from app.engines.customer_reviews.notifications import notify_customer_review_reply
            await notify_customer_review_reply(db, review)
        await db.commit()
        return reply

    # ── Admin: approve/reject reply ───────────────────────────────────────────
    async def approve_reply(
        self,
        db: AsyncSession,
        review_id: uuid.UUID,
        admin_user_id: uuid.UUID,
        request_id: str = "—",
    ) -> ReviewReply:
        reply = await self._get_reply(db, review_id)
        reply.status      = REPLY_APPROVED
        reply.approved_at = datetime.now(timezone.utc)
        await db.flush()
        await self._log_event(db, review_id, reply.tenant_id, ACTOR_ADMIN, admin_user_id,
                              EVT_REPLY_APPROVED, {"status": REPLY_PENDING}, {"status": REPLY_APPROVED}, request_id)
        # MODULE-L5-22: the reply is now live — tell the customer.
        review = await self._get_review(db, review_id)
        from app.engines.customer_reviews.notifications import notify_customer_review_reply
        await notify_customer_review_reply(db, review)
        await db.commit()
        return reply

    async def reject_reply(
        self,
        db: AsyncSession,
        review_id: uuid.UUID,
        admin_user_id: uuid.UUID,
        reason: str,
        request_id: str = "—",
    ) -> ReviewReply:
        reply = await self._get_reply(db, review_id)
        reply.status            = REPLY_REJECTED
        reply.moderation_reason = reason
        await db.flush()
        await self._log_event(db, review_id, reply.tenant_id, ACTOR_ADMIN, admin_user_id,
                              EVT_REPLY_REJECTED, {"status": REPLY_PENDING}, {"status": REPLY_REJECTED, "reason": reason}, request_id)
        await db.commit()
        return reply

    # ── Flag a review ─────────────────────────────────────────────────────────
    async def flag_review(
        self,
        db: AsyncSession,
        review_id: uuid.UUID,
        flagged_by_user_id: uuid.UUID,
        flagged_by_type: str,
        reason_code: str,
        reason_text: str | None = None,
        tenant_id: uuid.UUID | None = None,
        request_id: str = "—",
    ) -> ReviewFlag:
        review = await self._get_review(db, review_id)
        if reason_code not in FLAG_REASONS:
            reason_code = "other"

        flag = ReviewFlag(
            review_id          = review_id,
            tenant_id          = tenant_id,
            flagged_by_user_id = flagged_by_user_id,
            flagged_by_type    = flagged_by_type,
            reason_code        = reason_code,
            reason_text        = reason_text,
            status             = FLAG_STATUS_OPEN,
        )
        db.add(flag)

        if review.status != STATUS_FLAGGED:
            review.status = STATUS_FLAGGED

        await db.flush()
        await self._log_event(db, review_id, review.tenant_id, flagged_by_type, flagged_by_user_id,
                              EVT_FLAG_CREATED, None, {"reason_code": reason_code}, request_id)
        await db.commit()
        return flag

    # ── Admin: resolve flag ───────────────────────────────────────────────────
    async def resolve_flag(
        self,
        db: AsyncSession,
        flag_id: uuid.UUID,
        admin_user_id: uuid.UUID,
        request_id: str = "—",
    ) -> ReviewFlag:
        r = await db.execute(select(ReviewFlag).where(ReviewFlag.id == flag_id))
        flag = r.scalars().first()
        if not flag:
            raise ValueError(ERR_FLAG_NOT_FOUND)
        flag.status = FLAG_STATUS_RESOLVED
        await db.flush()

        review = await self._get_review(db, flag.review_id)
        remaining = await db.execute(
            select(ReviewFlag).where(
                ReviewFlag.review_id == flag.review_id,
                ReviewFlag.status    == FLAG_STATUS_OPEN,
            )
        )
        if not remaining.scalars().first():
            if review.status == STATUS_FLAGGED:
                review.status = STATUS_APPROVED

        await self._log_event(db, flag.review_id, review.tenant_id, ACTOR_ADMIN, admin_user_id,
                              EVT_FLAG_RESOLVED, {"status": FLAG_STATUS_OPEN}, {"status": FLAG_STATUS_RESOLVED}, request_id)
        await db.commit()
        return flag

    # ── Read helpers ──────────────────────────────────────────────────────────
    async def list_reviews(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        status: str | None = None,
        record_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CustomerReview]:
        q = select(CustomerReview)
        if tenant_id:
            q = q.where(CustomerReview.tenant_id == tenant_id)
        if customer_id:
            q = q.where(CustomerReview.customer_id == customer_id)
        if status:
            q = q.where(CustomerReview.status == status)
        if record_type:
            q = q.where(CustomerReview.record_type == record_type)
        q = q.order_by(CustomerReview.created_at.desc()).limit(limit).offset(offset)
        r = await db.execute(q)
        return r.scalars().all()

    async def get_review(self, db: AsyncSession, review_id: uuid.UUID) -> CustomerReview:
        return await self._get_review(db, review_id)

    async def get_reply(self, db: AsyncSession, review_id: uuid.UUID) -> ReviewReply | None:
        r = await db.execute(select(ReviewReply).where(ReviewReply.review_id == review_id))
        return r.scalars().first()

    async def list_flags(
        self,
        db: AsyncSession,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[ReviewFlag]:
        q = select(ReviewFlag)
        if status:
            q = q.where(ReviewFlag.status == status)
        q = q.order_by(ReviewFlag.created_at.desc()).limit(limit)
        r = await db.execute(q)
        return r.scalars().all()

    async def list_policies(self, db: AsyncSession) -> list[ReviewPolicy]:
        r = await db.execute(select(ReviewPolicy).order_by(ReviewPolicy.created_at))
        return r.scalars().all()

    async def get_policy(self, db: AsyncSession, policy_id: uuid.UUID) -> ReviewPolicy:
        r = await db.execute(select(ReviewPolicy).where(ReviewPolicy.id == policy_id))
        p = r.scalars().first()
        if not p:
            raise ValueError(ERR_POLICY_NOT_FOUND)
        return p

    async def update_policy(
        self, db: AsyncSession, policy_id: uuid.UUID, updates: dict
    ) -> ReviewPolicy:
        p = await self.get_policy(db, policy_id)
        allowed = ["auto_approve_enabled","require_admin_moderation","allow_provider_reply",
                   "require_reply_moderation","allow_review_edit","edit_window_hours",
                   "min_rating","max_rating","allow_media","max_media_count","is_active"]
        for k in allowed:
            if k in updates:
                setattr(p, k, updates[k])
        await db.commit()
        return p

    async def list_events(
        self,
        db: AsyncSession,
        review_id: uuid.UUID,
    ) -> list:
        from app.engines.customer_reviews.models import ReviewEvent
        r = await db.execute(
            select(ReviewEvent).where(ReviewEvent.review_id == review_id)
            .order_by(ReviewEvent.created_at)
        )
        return r.scalars().all()

    # ── Internal helpers ──────────────────────────────────────────────────────
    async def _get_review(self, db: AsyncSession, review_id: uuid.UUID) -> CustomerReview:
        r = await db.execute(select(CustomerReview).where(CustomerReview.id == review_id))
        rv = r.scalars().first()
        if not rv:
            raise ValueError(ERR_REVIEW_NOT_FOUND)
        return rv

    async def _get_reply(self, db: AsyncSession, review_id: uuid.UUID) -> ReviewReply:
        r = await db.execute(select(ReviewReply).where(ReviewReply.review_id == review_id))
        rp = r.scalars().first()
        if not rp:
            raise ValueError(ERR_REPLY_NOT_FOUND)
        return rp

    async def _get_policy(self, db: AsyncSession, tenant_id: uuid.UUID) -> ReviewPolicy | None:
        r = await db.execute(
            select(ReviewPolicy).where(
                ReviewPolicy.tenant_id == tenant_id,
                ReviewPolicy.is_active  == True,
            )
        )
        p = r.scalars().first()
        if p:
            return p
        # fall back to default policy
        r2 = await db.execute(
            select(ReviewPolicy).where(
                ReviewPolicy.tenant_id == None,
                ReviewPolicy.policy_key == "default",
                ReviewPolicy.is_active  == True,
            )
        )
        return r2.scalars().first()

    async def _log_event(
        self,
        db: AsyncSession,
        review_id: uuid.UUID,
        tenant_id,
        actor_type: str,
        actor_user_id,
        event_type: str,
        old_value: dict | None,
        new_value: dict | None,
        request_id: str,
    ) -> None:
        from app.engines.customer_reviews.models import ReviewEvent
        ev = ReviewEvent(
            review_id     = review_id,
            tenant_id     = tenant_id,
            actor_type    = actor_type,
            actor_user_id = actor_user_id,
            event_type    = event_type,
            old_value     = old_value,
            new_value     = new_value,
            request_id    = request_id,
        )
        db.add(ev)
        await db.flush()

    async def _trigger_aggregation(self, db: AsyncSession, review: CustomerReview) -> None:
        try:
            await self._aggregation.recompute_tenant_summary(db, review.tenant_id)
            if review.staff_member_id:
                await self._aggregation.recompute_staff_summary(db, review.tenant_id, review.staff_member_id)
            await db.commit()
        except Exception:
            pass
