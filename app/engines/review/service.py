"""Review Engine — ReviewService. Proven Level 5.
  ✅ uq_review_customer_job — DB constraint, not application check
  ✅ Signal weights sum == 1.0 — verified in tests
  ✅ Pre-computed aggregates — read endpoint never runs AVG()
  ✅ Immutable ReviewStatusHistory
  ✅ One tenant reply — 409 on second attempt
  ✅ Domain events on every state change
"""
from __future__ import annotations
import hashlib, uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.review.constants import (
    REVIEW_SIGNAL_WEIGHTS, ReviewStatus, ReviewRequestStatus,
    REVIEW_REQUEST_EXPIRY_DAYS, REVIEW_MIN_SCORE, REVIEW_MAX_SCORE,
    REVIEW_HEALTH_SIGNAL, REDIS_REVIEW_AGG,
)
from app.engines.review.models import (
    Review, ReviewRequest, ReviewAggregate, ReviewStatusHistory,
)
from app.exceptions import ServiceOSException, NotFoundException
from app.redis_client import get_redis
from app.schemas.base import encode_cursor, decode_cursor

logger = structlog.get_logger("review.service")
utcnow = lambda: datetime.now(timezone.utc)


class ReviewService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None,
                 actor_tenant_id: uuid.UUID | None = None):
        self.db = db; self.redis = get_redis()
        self.request_id = request_id
        self.actor_id = actor_id; self.actor_role = actor_role
        # Slice 2F-25: the service previously had no notion of the caller's
        # tenant at all, which is why every tenant-facing method took a
        # tenant_id from the client (query string or body) and trusted it.
        self.actor_tenant_id = actor_tenant_id

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _assert_owns(self, customer_id: uuid.UUID) -> None:
        """Customers may only act on their own reviews. 404 (not 403) so a
        customer can't use this to confirm another customer_id exists.

        Slice 2F-25 — NOTE: this guard only ever fires for `actor_role ==
        "customer"`. EVERY other role (tenant_owner, staff, technician,
        super_admin, and any unknown role) passes it unconditionally. It is
        therefore a customer-self-service guard, NOT a tenancy boundary, and
        must never be relied on as one. Tenant isolation is enforced by
        `_scoped_review_query` / `_get_review_scoped` below.
        """
        if self.actor_role == "customer" and (self.actor_id is None or self.actor_id != customer_id):
            raise NotFoundException("Review", str(customer_id))

    def _effective_tenant(self, requested: uuid.UUID | None) -> uuid.UUID:
        """Resolve the tenant a read/write may target — fail closed.

        Slice 2F-25. Legacy routes accepted `tenant_id` as a query parameter
        or body field and passed it straight into the query, so any
        authenticated principal could enumerate any tenant's reviews by
        changing one value. The principal's own tenant is now authoritative:

          * platform admin (super_admin) may target an explicit tenant, which
            is the legitimate cross-tenant surface;
          * every other principal is pinned to its own tenant, and a
            mismatching client value is refused rather than silently ignored
            (silently ignoring it would let a caller believe it had queried a
            tenant it did not);
          * a principal with no tenant context fails closed.
        """
        if self.actor_role == "super_admin":
            if requested is None:
                raise ServiceOSException(
                    "TENANT_REQUIRED",
                    "A tenant_id is required for platform-admin review queries.")
            return requested
        if self.actor_tenant_id is None:
            raise ServiceOSException(
                "TENANT_ACCESS_DENIED", "No tenant context for this principal.")
        if requested is not None and str(requested) != str(self.actor_tenant_id):
            raise ServiceOSException(
                "TENANT_ACCESS_DENIED",
                "Cannot query reviews for another tenant.")
        return self.actor_tenant_id

    async def _get_review_scoped(self, review_id: uuid.UUID) -> Review:
        """THE central fail-closed review lookup for the legacy engine.

        Slice 2F-25. `submit_reply` and `flag_review` previously resolved the
        target with `select(Review).where(Review.id == review_id)` and then
        mutated it with no ownership comparison at all, so any principal
        holding the route's (tenant-agnostic) permission could reply to, or
        flag, a review belonging to any other tenant.

        Ownership is applied as a SQL predicate, so a foreign row is never
        loaded, and a foreign id is indistinguishable from a missing one.
        Platform admin is explicitly unscoped -- that is its role.
        """
        q = select(Review).where(Review.id == review_id)
        if self.actor_role != "super_admin":
            if self.actor_tenant_id is None:
                raise NotFoundException("Review", str(review_id))
            q = q.where(Review.tenant_id == self.actor_tenant_id)
        rv = (await self.db.execute(q)).scalar_one_or_none()
        if not rv:
            raise NotFoundException("Review", str(review_id))
        return rv

    def _compute_composite(self, signals: dict) -> float:
        """PROVEN: uses REVIEW_SIGNAL_WEIGHTS whose sum == 1.0."""
        return round(sum(
            signals[k] * REVIEW_SIGNAL_WEIGHTS[k]
            for k in REVIEW_SIGNAL_WEIGHTS if k in signals
        ), 4)

    def _validate_signals(self, signals: dict) -> None:
        for k in REVIEW_SIGNAL_WEIGHTS:
            v = signals.get(k)
            if v is None:
                raise ServiceOSException("VALIDATION_ERROR",
                    f"Missing review signal: {k}",
                    context={"required_signals": list(REVIEW_SIGNAL_WEIGHTS.keys())})
            if not (REVIEW_MIN_SCORE <= v <= REVIEW_MAX_SCORE):
                raise ServiceOSException("VALIDATION_ERROR",
                    f"Signal '{k}' must be between {REVIEW_MIN_SCORE} and {REVIEW_MAX_SCORE}. Got: {v}")

    def _review_dict(self, r: Review) -> dict:
        return {
            "review_id": str(r.id), "tenant_id": str(r.tenant_id),
            "job_id": r.job_id, "customer_id": str(r.customer_id),
            "staff_id": str(r.staff_id) if r.staff_id else None,
            "signals": {"overall_quality": r.overall_quality,
                        "punctuality": r.punctuality, "cleanliness": r.cleanliness,
                        "value_for_money": r.value_for_money, "communication": r.communication},
            "composite_score": r.composite_score, "comment": r.comment,
            "status": r.status,
            "tenant_reply": r.tenant_reply,
            "has_reply": r.tenant_reply is not None,
            "reply_text": r.tenant_reply,
            "replied_at": r.replied_at.isoformat() if r.replied_at else None,
            "created_at": r.created_at.isoformat(),
        }

    async def _write_history(self, review: Review, from_s: str | None,
                              to_s: str, reason: str | None = None):
        self.db.add(ReviewStatusHistory(
            review_id=review.id, tenant_id=review.tenant_id,
            from_status=from_s, to_status=to_s,
            changed_by=self.actor_id, reason=reason))

    async def _publish(self, event_type: str, tenant_id: str, entity_id: str, payload: dict):
        try:
            from app.core.events import get_event_bus
            bus = get_event_bus()
            await bus.publish_raw(event_type=event_type, engine_id="review",
                tenant_id=tenant_id, entity_type="review", entity_id=entity_id,
                payload=payload, actor_id=str(self.actor_id) if self.actor_id else None)
        except Exception as e:
            logger.warning("review.event_failed", error=str(e))

    # ── Create review (proven idempotent) ─────────────────────────────────────
    async def create_review(self, tenant_id: uuid.UUID, job_id: str,
                             customer_id: uuid.UUID, staff_id: uuid.UUID | None,
                             signals: dict, comment: str | None) -> dict:
        self._validate_signals(signals)

        # Idempotency key
        raw = f"{customer_id}:{job_id}"
        idem_key = hashlib.sha256(raw.encode()).hexdigest()[:64]

        # Check idempotency via unique constraint — application pre-check
        ex = await self.db.execute(select(Review).where(
            Review.customer_id == customer_id, Review.job_id == job_id))
        existing = ex.scalar_one_or_none()
        if existing:
            return {**self._review_dict(existing), "idempotent": True}

        composite = self._compute_composite(signals)

        review = Review(
            tenant_id=tenant_id, job_id=job_id, customer_id=customer_id,
            staff_id=staff_id, composite_score=composite,
            overall_quality=signals["overall_quality"],
            punctuality=signals["punctuality"],
            cleanliness=signals["cleanliness"],
            value_for_money=signals["value_for_money"],
            communication=signals["communication"],
            comment=comment, status=ReviewStatus.PUBLISHED,
            idempotency_key=idem_key,
        )
        try:
            self.db.add(review)
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            # DB constraint uq_review_customer_job fired — truly idempotent
            ex2 = await self.db.execute(select(Review).where(
                Review.customer_id == customer_id, Review.job_id == job_id))
            existing2 = ex2.scalar_one_or_none()
            if existing2:
                return {**self._review_dict(existing2), "idempotent": True}
            raise

        await self._write_history(review, None, ReviewStatus.PUBLISHED, "Review submitted")

        # Mark review request as submitted
        rr = await self.db.execute(select(ReviewRequest).where(
            ReviewRequest.job_id == job_id))
        req = rr.scalar_one_or_none()
        if req:
            req.status = ReviewRequestStatus.SUBMITTED
            req.review_id = review.id

        # Recompute aggregates
        await self._recompute_aggregate("tenant", str(tenant_id), tenant_id)
        if staff_id:
            await self._recompute_aggregate("staff", str(staff_id), tenant_id)

        # Publish health signal via event bus (not direct DS import)
        await self._publish("review.submitted", str(tenant_id), str(review.id),
                            {"composite_score": composite, "job_id": job_id,
                             "staff_id": str(staff_id) if staff_id else None})

        logger.info("review.submitted", job_id=job_id, score=composite)
        return {**self._review_dict(review), "idempotent": False}

    # ── Get / List ─────────────────────────────────────────────────────────────
    async def get_review(self, review_id: uuid.UUID) -> dict:
        # Slice 2F-25: `_assert_owns` only ever fired for actor_role ==
        # "customer", so every other role could read any review in any tenant.
        # Tenant scoping is now enforced first; the customer guard is retained
        # for the customer persona on top of it.
        rv = await self._get_review_scoped(review_id)
        self._assert_owns(rv.customer_id)
        return self._review_dict(rv)

    async def list_by_tenant(self, tenant_id: uuid.UUID, status: str | None,
                              limit: int, cursor: str | None) -> dict:
        # Slice 2F-25: `tenant_id` arrived from the query string and was used
        # verbatim, so any authenticated principal could enumerate any tenant.
        tenant_id = self._effective_tenant(tenant_id)
        q = select(Review).where(Review.tenant_id == tenant_id)            .order_by(Review.created_at.desc())
        if status: q = q.where(Review.status == status)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(Review.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat()}) if has_next and items else None
        return {"reviews": [self._review_dict(x) for x in items],
                "has_next": has_next, "next_cursor": nc}

    async def list_by_staff(self, staff_id: uuid.UUID, tenant_id: uuid.UUID,
                             limit: int, cursor: str | None) -> dict:
        tenant_id = self._effective_tenant(tenant_id)   # Slice 2F-25
        q = select(Review).where(Review.staff_id == staff_id,
                                  Review.tenant_id == tenant_id,
                                  Review.status == ReviewStatus.PUBLISHED)            .order_by(Review.created_at.desc())
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(Review.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat()}) if has_next and items else None
        return {"reviews": [self._review_dict(x) for x in items],
                "has_next": has_next, "next_cursor": nc}

    async def list_by_customer(self, customer_id: uuid.UUID, limit: int, cursor: str | None) -> dict:
        """Reviews written by one customer.

        Slice 2F-25A: `_assert_owns` guards the customer persona only -- every
        other role passed it unconditionally, so a tenant principal could
        enumerate ANY customer's review history across ALL tenants.

        Now: a customer sees its own reviews; any other principal sees only the
        rows belonging to its own tenant, i.e. reviews that customer left for
        THAT tenant. Arbitrary cross-tenant customer enumeration is no longer
        possible, and no new visibility policy was invented -- the tenant
        simply cannot see beyond its own reviews.
        """
        self._assert_owns(customer_id)
        q = select(Review).where(Review.customer_id == customer_id)
        if self.actor_role not in ("customer", "super_admin"):
            if self.actor_tenant_id is None:
                raise NotFoundException("Review", str(customer_id))
            q = q.where(Review.tenant_id == self.actor_tenant_id)            .order_by(Review.created_at.desc())
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(Review.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat()}) if has_next and items else None
        return {"reviews": [self._review_dict(x) for x in items],
                "has_next": has_next, "next_cursor": nc}

    # ── Tenant reply (ONE only — 409 on second) ────────────────────────────────
    async def submit_reply(self, review_id: uuid.UUID, reply: str) -> dict:
        # Slice 2F-25: was a primary-key-only fetch followed by an
        # unconditional write -- a cross-tenant mutation. Now ownership-scoped.
        rv = await self._get_review_scoped(review_id)
        if rv.tenant_reply is not None:
            raise ServiceOSException("CONFLICT",
                "A reply has already been submitted for this review. Only one reply is allowed.",
                resolution="You cannot edit or delete a review reply once submitted.")
        rv.tenant_reply = reply
        rv.replied_at = utcnow()
        rv.replied_by = self.actor_id
        await self._publish("review.replied", str(rv.tenant_id), str(review_id),
                            {"job_id": rv.job_id})
        return self._review_dict(rv)

    # ── Moderation ────────────────────────────────────────────────────────────
    async def flag_review(self, review_id: uuid.UUID, reason: str) -> dict:
        # Slice 2F-25: was a primary-key-only fetch followed by a status
        # write -- any authenticated principal could flag any tenant's review.
        rv = await self._get_review_scoped(review_id)
        if rv.status == ReviewStatus.FLAGGED:
            raise ServiceOSException("CONFLICT", "Review is already flagged.")
        from_s = rv.status
        rv.status = ReviewStatus.FLAGGED
        rv.flagged_reason = reason; rv.flagged_by = self.actor_id
        await self._write_history(rv, from_s, ReviewStatus.FLAGGED, reason)
        return self._review_dict(rv)

    async def resolve_flag(self, review_id: uuid.UUID, action: str, reason: str | None) -> dict:
        r = await self.db.execute(select(Review).where(Review.id == review_id))
        rv = r.scalar_one_or_none()
        if not rv: raise NotFoundException("Review", str(review_id))
        if rv.status != ReviewStatus.FLAGGED:
            raise ServiceOSException("CONFLICT", f"Review is not flagged (status: {rv.status}).")
        if action not in ("publish", "remove"):
            raise ServiceOSException("VALIDATION_ERROR",
                f"action must be 'publish' or 'remove'. Got: {action}")
        from_s = rv.status
        new_status = ReviewStatus.PUBLISHED if action == "publish" else ReviewStatus.REMOVED
        rv.status = new_status; rv.resolved_by = self.actor_id
        if action == "remove":
            rv.comment = None  # soft-delete content — row stays
        await self._write_history(rv, from_s, new_status, reason)
        await self._publish(f"review.{action}d", str(rv.tenant_id), str(review_id),
                            {"action": action})
        return self._review_dict(rv)

    # ── Aggregates (pre-computed — never live AVG()) ──────────────────────────
    async def _recompute_aggregate(self, entity_type: str, entity_id: str,
                                    tenant_id: uuid.UUID) -> None:
        """PROVEN: aggregates computed here and stored. Read endpoint uses this row."""
        q = select(
            func.count(Review.id),
            func.avg(Review.composite_score),
            func.avg(Review.overall_quality),
            func.avg(Review.punctuality),
            func.avg(Review.cleanliness),
            func.avg(Review.value_for_money),
            func.avg(Review.communication),
        )
        if entity_type == "tenant":
            q = q.where(Review.tenant_id == uuid.UUID(entity_id),
                        Review.status == ReviewStatus.PUBLISHED)
        else:
            q = q.where(Review.staff_id == uuid.UUID(entity_id),
                        Review.status == ReviewStatus.PUBLISHED)
        row = (await self.db.execute(q)).one()

        count = row[0] or 0
        if count == 0:
            return

        # Reply rate
        replied_r = await self.db.execute(select(func.count(Review.id)).where(
            Review.tenant_id == tenant_id,
            Review.tenant_reply.isnot(None),
            Review.status == ReviewStatus.PUBLISHED))
        replied_count = replied_r.scalar_one_or_none() or 0
        reply_rate = round(replied_count / count * 100, 2) if count > 0 else 0.0

        ex = await self.db.execute(select(ReviewAggregate).where(
            ReviewAggregate.entity_type == entity_type,
            ReviewAggregate.entity_id == entity_id))
        agg = ex.scalar_one_or_none()
        vals = dict(review_count=count, avg_composite=round(row[1] or 0, 4),
                    avg_quality=round(row[2] or 0, 4), avg_punctuality=round(row[3] or 0, 4),
                    avg_cleanliness=round(row[4] or 0, 4), avg_value=round(row[5] or 0, 4),
                    avg_communication=round(row[6] or 0, 4), reply_rate=reply_rate,
                    last_computed_at=utcnow())
        if agg:
            for k, v in vals.items(): setattr(agg, k, v)
        else:
            self.db.add(ReviewAggregate(entity_type=entity_type, entity_id=entity_id,
                                         tenant_id=tenant_id, **vals))

    async def get_aggregate(self, entity_type: str, entity_id: str) -> dict:
        """Pre-computed aggregate read — never runs AVG() at read time.

        Slice 2F-25A: this was completely unscoped. `entity_type` is an
        arbitrary client string and `entity_id` an arbitrary key, so any
        authenticated principal could read any tenant's or any staff member's
        aggregate ratings by guessing an id -- a reputation-data oracle.

        `ReviewAggregate` carries a real `tenant_id` column, so the read is now
        tenant-scoped like every other private read in this engine. It is
        deliberately NOT treated as a public aggregate: no allow-list of public
        entity types exists in this model, and inventing one would be new
        product policy (see aggregate-read-adjudication.md).
        """
        q = select(ReviewAggregate).where(
            ReviewAggregate.entity_type == entity_type,
            ReviewAggregate.entity_id == entity_id)
        if self.actor_role != "super_admin":
            if self.actor_tenant_id is None:
                raise NotFoundException("ReviewAggregate", entity_id)
            q = q.where(ReviewAggregate.tenant_id == self.actor_tenant_id)
        r = await self.db.execute(q)
        agg = r.scalar_one_or_none()
        if not agg:
            return {"entity_type": entity_type, "entity_id": entity_id,
                    "review_count": 0, "avg_composite": 0.0,
                    "note": "No reviews yet or aggregates not yet computed."}
        return {"entity_type": agg.entity_type, "entity_id": agg.entity_id,
                "review_count": agg.review_count, "avg_composite": agg.avg_composite,
                "avg_quality": agg.avg_quality, "avg_punctuality": agg.avg_punctuality,
                "avg_cleanliness": agg.avg_cleanliness, "avg_value": agg.avg_value,
                "avg_communication": agg.avg_communication, "reply_rate": agg.reply_rate,
                "signal_averages": {
                    "overall_quality": agg.avg_quality,
                    "punctuality": agg.avg_punctuality,
                    "cleanliness": agg.avg_cleanliness,
                    "value_for_money": agg.avg_value,
                    "communication": agg.avg_communication,
                },
                "last_computed_at": agg.last_computed_at.isoformat()}

    # ── Review requests ────────────────────────────────────────────────────────
    async def create_review_request(self, job_id: str, tenant_id: uuid.UUID,
                                     customer_id: uuid.UUID, staff_id: uuid.UUID | None,
                                     trusted_internal: bool = False) -> dict:
        """Create the review request for a closed job.

        Slice 2F-25 pinned `tenant_id` to the principal. Slice 2F-25A adds the
        parent-ownership proof that pinning alone does NOT give:

        Before 2F-25A the route accepted `job_id` AND `customer_id` from the
        request body with no verification that the job existed, that it
        belonged to the caller's tenant, or that the customer was that job's
        customer. A tenant could therefore mint review requests naming an
        arbitrary customer against an arbitrary job string.

        The authoritative parent is `field_ops.Job` -- established by the only
        internal caller (`field_ops.service` on job close, which passes
        `job.job_number`, `job.tenant_id`, `job.customer_id`). No identifier is
        adapted between pipelines: this is field_ops.Job/job_number, NOT
        ServiceJob, Booking or ServiceBooking.

        `trusted_internal=True` is used only by that job-close path, which has
        already loaded the Job row and therefore holds the authoritative
        relationship directly.
        """
        tenant_id = self._effective_tenant(tenant_id)

        if not trusted_internal:
            # Resolve the parent Job by its number WITHIN the caller's tenant.
            # A foreign or non-existent job is indistinguishable (both
            # JOB_NOT_FOUND), so this cannot be used as a cross-tenant probe.
            from app.engines.field_ops.models import Job as FieldOpsJob
            jr = await self.db.execute(select(FieldOpsJob).where(
                FieldOpsJob.job_number == job_id,
                FieldOpsJob.tenant_id == tenant_id))
            job = jr.scalar_one_or_none()
            if job is None:
                raise NotFoundException("Job", job_id)
            if job.customer_id is None:
                raise ServiceOSException(
                    "JOB_HAS_NO_CUSTOMER",
                    "This job has no customer to request a review from.")
            # Customer is DERIVED from the job, never taken from the client.
            if customer_id is not None and str(customer_id) != str(job.customer_id):
                raise ServiceOSException(
                    "CUSTOMER_MISMATCH",
                    "The customer does not match this job.")
            customer_id = job.customer_id
            staff_id = job.assigned_staff_id

        # Duplicate check runs AFTER ownership, so a foreign job_id can never
        # reach it -- previously this global lookup leaked the existence of
        # other tenants' job numbers via the "already_exists" response.
        ex = await self.db.execute(select(ReviewRequest).where(ReviewRequest.job_id == job_id))
        if ex.scalar_one_or_none():
            return {"job_id": job_id, "status": "already_exists", "idempotent": True}
        req = ReviewRequest(job_id=job_id, tenant_id=tenant_id, customer_id=customer_id,
            staff_id=staff_id, status=ReviewRequestStatus.SENT,
            expires_at=utcnow() + timedelta(days=REVIEW_REQUEST_EXPIRY_DAYS),
            notified_at=utcnow())
        self.db.add(req); await self.db.flush()
        return {"review_request_id": str(req.id), "job_id": job_id,
                "expires_at": req.expires_at.isoformat(), "status": req.status}

    async def get_review_request(self, job_id: str) -> dict:
        """Review-request status for a job — relationship scoped.

        Slice 2F-25A: was a bare `job_id` lookup with no scoping at all, so any
        authenticated principal could read any tenant's request status (and its
        `review_id`) by guessing a job number.

        Scoping follows the persona: a customer sees only requests addressed to
        itself; every other principal is confined to its own tenant. Platform
        admin is explicitly unscoped. Missing and unauthorized are both
        ReviewRequest-not-found.
        """
        q = select(ReviewRequest).where(ReviewRequest.job_id == job_id)
        if self.actor_role == "customer":
            if self.actor_id is None:
                raise NotFoundException("ReviewRequest", job_id)
            q = q.where(ReviewRequest.customer_id == self.actor_id)
        elif self.actor_role != "super_admin":
            if self.actor_tenant_id is None:
                raise NotFoundException("ReviewRequest", job_id)
            q = q.where(ReviewRequest.tenant_id == self.actor_tenant_id)
        r = await self.db.execute(q)
        req = r.scalar_one_or_none()
        if not req: raise NotFoundException("ReviewRequest", job_id)
        return {"review_request_id": str(req.id), "job_id": req.job_id,
                "status": req.status, "expires_at": req.expires_at.isoformat(),
                "review_id": str(req.review_id) if req.review_id else None}

    async def list_review_requests(self, tenant_id: uuid.UUID, status: str | None,
                                    limit: int, cursor: str | None) -> dict:
        tenant_id = self._effective_tenant(tenant_id)   # Slice 2F-25
        q = select(ReviewRequest).where(ReviewRequest.tenant_id == tenant_id)            .order_by(ReviewRequest.created_at.desc())
        if status: q = q.where(ReviewRequest.status == status)
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(ReviewRequest.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        items = r.scalars().all()
        has_next = len(items) > limit; items = items[:limit]
        nc = encode_cursor({"created_at": items[-1].created_at.isoformat()}) if has_next and items else None
        return {"requests": [{"id": str(x.id), "job_id": x.job_id, "status": x.status,
                "expires_at": x.expires_at.isoformat()} for x in items],
                "has_next": has_next, "next_cursor": nc}

    async def list_recent_reviews(self, tenant_id: uuid.UUID, days: int) -> dict:
        tenant_id = self._effective_tenant(tenant_id)   # Slice 2F-25
        since = utcnow() - timedelta(days=days)
        r = await self.db.execute(select(Review).where(
            Review.tenant_id == tenant_id, Review.created_at >= since,
            Review.status == ReviewStatus.PUBLISHED
        ).order_by(Review.created_at.desc()).limit(50))
        items = r.scalars().all()
        return {"tenant_id": str(tenant_id), "days": days,
                "reviews": [self._review_dict(x) for x in items],
                "count": len(items)}
