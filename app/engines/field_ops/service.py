"""Field Ops Engine — FieldOpsService. 23-status lifecycle with atomic close pipeline."""
from __future__ import annotations
import secrets, uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import structlog
from sqlalchemy import select, update, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.engines.field_ops.constants import (
    JS, ALLOWED_TRANSITIONS, TERMINAL_STATUSES, LOCKED_STATUSES,
    DEFAULT_STATUS_SLA_HOURS, REDIS_JOB_TOKEN,
    JobType, JOB_TYPES, get_allowed_transitions as _resolve_transitions,
)
import random
from app.engines.field_ops.models import (
    Job, JobStatusHistory, JobNote, JobMedia, JobQuote, JobChecklistItem,
)
from app.exceptions import ServiceOSException, NotFoundException
from app.redis_client import get_redis, cache_set
from app.schemas.base import encode_cursor, decode_cursor

logger = structlog.get_logger("fieldops.service")
utcnow = lambda: datetime.now(timezone.utc)


class FieldOpsService:
    def __init__(self, db: AsyncSession, request_id: str = "—",
                 actor_id: uuid.UUID | None = None, actor_role: str | None = None,
                 actor_tenant_id: uuid.UUID | None = None):
        self.db = db; self.redis = get_redis()
        self.request_id = request_id; self.actor_id = actor_id; self.actor_role = actor_role
        self.actor_tenant_id = actor_tenant_id  # Step 6: tenant_owner isolation

    def _generate_job_number(self) -> str:
        import random
        return f"JOB-{utcnow().strftime('%Y%m')}-{random.randint(10000,99999)}"

    def _assert_assigned(self, job: Job) -> None:
        """Staff may only read/act on jobs assigned to them. 404 (not 403) so a
        staff member can't use this to confirm another job_id exists."""
        if self.actor_role in ("staff", "technician") and job.assigned_staff_id != self.actor_id:
            raise NotFoundException("Job", str(job.id))

    def _assert_can_access_job(self, job: Job) -> None:
        """Step 6: full isolation — staff (own assigned), tenant_owner (own
        tenant), customer (own job). 404 hides existence, same as bookings."""
        self._assert_assigned(job)
        if self.actor_role == "tenant_owner":
            if self.actor_tenant_id is None or job.tenant_id != self.actor_tenant_id:
                raise NotFoundException("Job", str(job.id))
        elif self.actor_role == "customer":
            if job.customer_id != self.actor_id:
                raise NotFoundException("Job", str(job.id))

    def _update_sla(self, job: Job) -> None:
        """Step 6: recompute minutes_in_status / sla_breached / sla_breach_level
        on read. on_time < sla_minutes; then at_risk (0-30 over), overdue (30-60
        over), critical (60+ over). Defensive against mocked/partial jobs in tests."""
        try:
            if not isinstance(job.sla_minutes, (int, float)) or job.sla_minutes <= 0:
                return
            if job.status in TERMINAL_STATUSES:
                return
            started = job.current_status_started_at or job.updated_at or job.created_at
            if not isinstance(started, datetime):
                return
            elapsed = int((utcnow() - started).total_seconds() / 60)
            job.minutes_in_status = elapsed
            overdue = elapsed - job.sla_minutes
            if overdue <= 0:
                job.sla_breached = False; job.sla_breach_level = "on_time"
            elif overdue <= 30:
                job.sla_breached = True; job.sla_breach_level = "at_risk"
            elif overdue <= 60:
                job.sla_breached = True; job.sla_breach_level = "overdue"
            else:
                job.sla_breached = True; job.sla_breach_level = "critical"
        except Exception:
            return

    def _business_filtered_transitions(self, job: Job) -> list[str]:
        """Step 7: narrows the raw job_type transition graph by per-job
        business state — quote_required (repair) / checklist_required
        (service) gate work_started / work_complete respectively."""
        allowed = list(_resolve_transitions(job.job_type, job.status))
        try:
            if (job.job_type == JobType.REPAIR and JS.WORK_STARTED in allowed
                    and job.quote_required is True and job.status != JS.QUOTE_APPROVED):
                allowed = [a for a in allowed if a != JS.WORK_STARTED]
            if (job.job_type == JobType.SERVICE and JS.WORK_COMPLETE in allowed
                    and job.checklist_required is True and job.status != JS.CHECKLIST_COMPLETE):
                allowed = [a for a in allowed if a != JS.WORK_COMPLETE]
        except Exception:
            pass
        return allowed

    async def _assert_tenant_customer_relationship(self, tenant_id: uuid.UUID,
                                                     customer_id: uuid.UUID) -> None:
        """Slice 2F-14G (tightens Slice 2F-14F's interim policy): NOT every
        historical Booking/Job row is trustworthy relationship evidence.

        Booking: BookingService.create_booking lets a tenant_owner supply an
        arbitrary client-side customer_id with no existence/ownership check at
        all (unlike this service's own create_job, which validates against the
        User table) -- a malicious tenant_owner could otherwise "self-mint"
        qualifying evidence for an unrelated real customer by creating a
        throwaway Booking naming them. A Booking only qualifies once it has
        reached a status that is UNREACHABLE from the initial
        draft/pending/pending_confirmation states except by first passing
        through BS.CONFIRMED (confirmed, scheduled, dispatching, in_progress,
        completed, converted_to_job -- see BOOKING_TRANSITIONS in
        app/engines/booking/constants.py). draft/pending/pending_confirmation/
        rejected/expired/cancelled/voided do not qualify -- cancelled/voided
        are excluded too because BOOKING_TRANSITIONS allows reaching them from
        a NON-confirmed state as well, so current status alone cannot prove
        the booking was ever confirmed.

        Job: a "generic" standalone Job (booking_id and parent_job_id both
        null) carries no field distinguishing a hardened, post-Slice-2F-14C
        standalone creation (itself only ever created because qualifying
        evidence already existed at that time) from an arbitrary pre-hardening
        row. No deployment marker/timestamp is invented to tell them apart
        (out of scope) -- generic Job rows are excluded from evidence
        entirely; only Job rows with a non-null booking_id or parent_job_id
        qualify, since those are structurally derived from an already-
        validated Booking or parent Job and carry their trust forward.

        Read-only; raises a single, uniform, privacy-safe error whether the
        customer is completely unrelated to any tenant, known only to a
        DIFFERENT one, or has only non-qualifying low-trust records -- never
        discloses which case applies or any other tenant's identity."""
        from app.engines.booking.models import Booking, BookingStatusHistory
        from app.engines.booking.constants import BS
        QUALIFYING_BOOKING_STATUSES = (
            BS.CONFIRMED, BS.SCHEDULED, BS.DISPATCHING, BS.IN_PROGRESS,
            BS.COMPLETED, BS.CONVERTED_TO_JOB,
        )
        # Slice 2F-15A: a qualifying-status Booking is no longer sufficient by
        # itself -- it must additionally be CUSTOMER-originated. Provider-
        # created Bookings (Slice 2F-15's own "assisted booking" mode) can now
        # only ever be created when an independent qualifying relationship
        # already existed (enforced in BookingService.create_booking) -- so a
        # provider-created Booking is never the FIRST piece of evidence, and
        # excluding it from being direct evidence here does not break any
        # legitimate chain (the earlier evidence that justified its creation
        # remains independently queryable). This also closes legacy risk:
        # pre-fix provider-created Bookings with no genuine customer
        # participation can no longer qualify by status alone. The creation
        # actor's role is read from BookingStatusHistory's creation row
        # (from_status IS NULL, changed_by_role) -- an existing, unmodified
        # field written unconditionally by create_booking, not a new column.
        # Slice 2F-15C: role equality alone ("changed_by_role == customer") is
        # not sufficient -- it must also be established that the ACTOR who
        # performed the creation event IS this Booking's own customer, not
        # merely "a" customer. Binds changed_by (the acting user's ID)
        # explicitly to Booking.customer_id, closing the theoretical gap
        # where a differently-derived creation path could otherwise let one
        # customer's creation event qualify for another customer's Booking.
        br = await self.db.execute(
            select(Booking.id)
            .join(BookingStatusHistory, BookingStatusHistory.booking_id == Booking.id)
            .where(
                Booking.tenant_id == tenant_id, Booking.customer_id == customer_id,
                Booking.status.in_(QUALIFYING_BOOKING_STATUSES),
                BookingStatusHistory.from_status.is_(None),
                BookingStatusHistory.changed_by_role == "customer",
                BookingStatusHistory.changed_by == Booking.customer_id,
            ).limit(1))
        if br.scalar_one_or_none():
            return
        jr = await self.db.execute(select(Job.id).where(
            Job.tenant_id == tenant_id, Job.customer_id == customer_id,
            or_(Job.booking_id.isnot(None), Job.parent_job_id.isnot(None))).limit(1))
        if jr.scalar_one_or_none():
            return
        raise ServiceOSException("CUSTOMER_TENANT_RELATIONSHIP_REQUIRED",
            "This customer has no existing relationship with your tenant. "
            "A Job can only be manually created for a customer who already has "
            "a booking or prior job with your tenant.", status_code=422)

    async def _get_job_for_assignment(self, job_id: uuid.UUID) -> Job:
        """Step 6: tenant_owner/super_admin lookup used by assign_staff. 404
        for cross-tenant access — explicit JOB_NOT_FOUND code per spec."""
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job:
            raise ServiceOSException("JOB_NOT_FOUND", f"Job '{job_id}' not found.", status_code=404)
        if self.actor_role == "tenant_owner":
            if self.actor_tenant_id is None or job.tenant_id != self.actor_tenant_id:
                raise ServiceOSException("JOB_NOT_FOUND", f"Job '{job_id}' not found.", status_code=404)
        return job

    async def _get_job_for_staff_action(self, job_id: uuid.UUID) -> Job:
        """Step 6: staff accept/reject — explicit 403 (not 404) per spec's
        STAFF_NOT_ASSIGNED_TO_JOB error code."""
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job:
            raise ServiceOSException("JOB_NOT_FOUND", f"Job '{job_id}' not found.", status_code=404)
        if job.assigned_staff_id != self.actor_id:
            raise ServiceOSException("STAFF_NOT_ASSIGNED_TO_JOB",
                "This job is not assigned to you.", status_code=403)
        return job

    def _job_dict(self, j: Job, include_timeline: bool = False) -> dict:
        self._update_sla(j)
        return {
            "job_id": str(j.id), "job_number": j.job_number,
            "tenant_id": str(j.tenant_id), "status": j.status,
            "job_type": j.job_type, "parent_job_id": str(j.parent_job_id) if j.parent_job_id else None,
            "title": j.title, "description": j.description,
            "service_type_id": j.service_type_id, "service_category": j.service_category,
            "booking_id": j.booking_id,
            "source": j.source,
            "assigned_staff_id": str(j.assigned_staff_id) if j.assigned_staff_id else None,
            "customer_id": str(j.customer_id) if j.customer_id else None,
            # Serviceability fields (Step 5)
            "address_id": str(j.address_id) if j.address_id else None,
            "service_id": str(j.service_id) if j.service_id else None,
            "city": j.city,
            "zipcode": j.zipcode,
            "matched_service_area_id": str(j.matched_service_area_id) if j.matched_service_area_id else None,
            "matched_service_area_service_id": str(j.matched_service_area_service_id) if j.matched_service_area_service_id else None,
            "coverage_match_level": j.coverage_match_level,
            "estimated_price": float(j.estimated_price) if j.estimated_price else None,
            "sla_minutes": j.sla_minutes,
            "address": j.address, "pincode": j.pincode,
            "scheduled_at": j.scheduled_at.isoformat() if j.scheduled_at else None,
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            "quoted_price": float(j.quoted_price) if j.quoted_price else None,
            "final_price": float(j.final_price) if j.final_price else None,
            # Customer Service Credit breakdown (migration 093) — the authoritative
            # figures for what the technician should actually collect on-site.
            "customer_credit_applied": float(j.credit_applied or 0),
            "payable_to_provider": float(j.payable_amount) if j.payable_amount is not None else (
                float(j.quoted_price) if j.quoted_price else None),
            "payment_collection_mode": "customer_pays_provider_directly",
            "platform_payment_collected": False,
            # record_payment() enforces amount == payable_amount (PAYMENT_AMOUNT_MISMATCH
            # otherwise), so once paid_at is set the amount collected is always the
            # payable-to-provider figure — safe to derive without an extra join here.
            "payment_recorded": j.payment_id is not None,
            "amount_collected": (float(j.payable_amount) if j.payable_amount is not None else
                                  (float(j.quoted_price) if j.quoted_price else None)) if j.paid_at else None,
            "commission_deducted": j.commission_deducted,
            "commission_amount": float(j.commission_amount) if j.commission_amount else None,
            "sla_breach": j.sla_breach, "customer_rating": j.customer_rating,
            "findings": j.findings, "recommendation": j.recommendation,
            "checklist": j.checklist, "duration_estimate_minutes": j.duration_estimate_minutes,
            "tags": j.tags, "created_at": j.created_at.isoformat() if j.created_at else None,
            "allowed_transitions": self._business_filtered_transitions(j),
            # Step 7 — job-type-specific routing
            "quote_required": j.quote_required, "quote_id": str(j.quote_id) if j.quote_id else None,
            "pre_approval_limit": float(j.pre_approval_limit) if j.pre_approval_limit is not None else None,
            "assessment_findings": j.assessment_findings, "recommended_work": j.recommended_work,
            "estimated_parts": j.estimated_parts,
            "assessment_completed_at": j.assessment_completed_at.isoformat() if j.assessment_completed_at else None,
            "quote_sent_at": j.quote_sent_at.isoformat() if j.quote_sent_at else None,
            "quote_approved_at": j.quote_approved_at.isoformat() if j.quote_approved_at else None,
            "quote_rejected_at": j.quote_rejected_at.isoformat() if j.quote_rejected_at else None,
            "quote_rejection_reason": j.quote_rejection_reason,
            "checklist_required": j.checklist_required,
            "checklist_started_at": j.checklist_started_at.isoformat() if j.checklist_started_at else None,
            "checklist_completed_at": j.checklist_completed_at.isoformat() if j.checklist_completed_at else None,
            "converted_from_consultation": j.converted_from_consultation,
            # Step 6 — assignment + staff lifecycle
            "assigned_at": j.assigned_at.isoformat() if j.assigned_at else None,
            "assigned_by_user_id": str(j.assigned_by_user_id) if j.assigned_by_user_id else None,
            "accepted_at": j.accepted_at.isoformat() if j.accepted_at else None,
            "rejected_at": j.rejected_at.isoformat() if j.rejected_at else None,
            "staff_rejection_reason": j.staff_rejection_reason,
            "en_route_at": j.en_route_at.isoformat() if j.en_route_at else None,
            "arrived_at": j.arrived_at.isoformat() if j.arrived_at else None,
            "work_started_at": j.work_started_at.isoformat() if j.work_started_at else None,
            "work_completed_at": j.work_completed_at.isoformat() if j.work_completed_at else None,
            "cancelled_at": j.cancelled_at.isoformat() if j.cancelled_at else None,
            "cancellation_reason": j.cancellation_reason,
            "status_updated_at": j.status_updated_at.isoformat() if j.status_updated_at else None,
            "minutes_in_status": j.minutes_in_status,
            "sla_breached": j.sla_breached,
            "sla_breach_level": j.sla_breach_level,
            "closing_notes": j.closing_notes,
        }

    async def _write_history(self, job: Job, from_status: str | None, to_status: str,
                               reason: str | None, lat: float | None, lng: float | None):
        self.db.add(JobStatusHistory(
            job_id=job.id, tenant_id=job.tenant_id,
            from_status=from_status, to_status=to_status,
            changed_by=self.actor_id, changed_by_role=self.actor_role,
            reason=reason, lat=lat, lng=lng,
        ))

    async def _publish(self, event_type: str, tenant_id: str, job_id: str, payload: dict):
        try:
            from app.core.events import get_event_bus
            bus = get_event_bus()
            await bus.publish_raw(event_type=event_type, engine_id="field_ops",
                tenant_id=tenant_id, entity_type="job", entity_id=job_id,
                payload=payload, actor_id=str(self.actor_id) if self.actor_id else None)
        except Exception as e:
            logger.warning("fieldops.event_failed", error=str(e))

    # ── Job CRUD (3 methods) ──────────────────────────────────────────────────
    async def create_job(self, tenant_id: uuid.UUID, data: dict) -> dict:
        # Slice 2F-14B: tenant_id was previously taken from the request body
        # as-is for every persona -- a tenant_owner/staff/technician caller
        # could create a Job under a DIFFERENT tenant_id simply by putting one
        # in the request. Tenant-scoped personas are now always pinned to
        # their own principal tenant, the same pattern already established in
        # list_jobs. super_admin (and the internal-only
        # _spawn_repair_from_consultation caller, which passes actor_role
        # unrelated to the acting user) may still pass an explicit tenant_id.
        if self.actor_role in ("tenant_owner", "staff", "technician") and self.actor_tenant_id is not None:
            tenant_id = self.actor_tenant_id
        if data.get("job_type") and data["job_type"] not in JOB_TYPES:
            raise ServiceOSException("INVALID_JOB_TYPE",
                f"Invalid job_type '{data['job_type']}'.", status_code=422,
                context={"valid_types": JOB_TYPES})

        # Slice 2F-14C: every tenant-owned linked-record identifier accepted
        # by this route is now ownership-validated against the (already
        # server-pinned) tenant_id -- a database FK existing is not
        # sufficient; a valid record belonging to a DIFFERENT tenant must
        # still be rejected. Reuses existing services/models only, no new
        # cross-pipeline adapter.
        catalog_item = None
        if data.get("service_type_id"):
            from app.engines.service_catalog.service import ServiceCatalogService
            catalog_item = await ServiceCatalogService(self.db).get_by_service_type_id(
                tenant_id, data["service_type_id"])
            if not catalog_item:
                raise ServiceOSException("FOREIGN_SERVICE_TYPE",
                    f"service_type_id '{data['service_type_id']}' does not belong to this tenant.",
                    status_code=422)
            if not catalog_item.is_active:
                raise ServiceOSException("INACTIVE_SERVICE_TYPE",
                    f"service_type_id '{data['service_type_id']}' is not active.", status_code=422)
        # Slice 2F-14E: booking_id and parent_job_id are each independently
        # cross-checked/duplicate-guarded (below) but no safe combined
        # semantics for supplying BOTH at once have ever been established
        # anywhere in this codebase (neither field defers to the other for
        # customer/service/duplicate authority when both are present) --
        # per the mission's explicit fallback, simultaneous use is rejected
        # before persistence rather than silently picking an undocumented
        # precedence.
        if data.get("booking_id") and data.get("parent_job_id"):
            raise ServiceOSException("AMBIGUOUS_JOB_SOURCE",
                "booking_id and parent_job_id cannot both be supplied.", status_code=422)

        parent = None
        if data.get("parent_job_id"):
            pr = await self.db.execute(select(Job).where(Job.id == uuid.UUID(data["parent_job_id"])))
            parent = pr.scalar_one_or_none()
            if not parent or parent.tenant_id != tenant_id:
                raise ServiceOSException("FOREIGN_PARENT_JOB",
                    f"parent_job_id '{data['parent_job_id']}' does not belong to this tenant.",
                    status_code=422)
            # Slice 2F-14D: parent_job_id is customer-authoritative -- a repair/
            # follow-up Job cannot be linked to a parent belonging to a
            # DIFFERENT customer than the one explicitly requested. Service
            # type is intentionally NOT cross-checked here: convert_to_repair's
            # own established behavior (repair_service_id or job.service_type_id)
            # already treats a differing repair service as legitimate policy,
            # not a defect.
            if data.get("customer_id") and str(parent.customer_id) != str(data["customer_id"]):
                raise ServiceOSException("CUSTOMER_PARENT_JOB_MISMATCH",
                    "customer_id does not match parent_job_id's customer.", status_code=422)
            # Slice 2F-14E: where create_job with a CONSULTATION parent + REPAIR
            # job_type is semantically equivalent to convert_to_repair's own
            # dedicated capability, the identical source-state prerequisite
            # (QUOTE_APPROVED) is now enforced -- mirroring, not inventing,
            # convert_to_repair's established policy. No status gate is
            # imposed on other parent/child job_type combinations, since no
            # established policy exists for those (would be inventing a
            # broader rule than evidenced).
            if parent.job_type == JobType.CONSULTATION and data.get("job_type") == JobType.REPAIR:
                if parent.status != JS.QUOTE_APPROVED:
                    raise ServiceOSException("CONSULTATION_CONVERSION_NOT_ALLOWED",
                        f"Consultation must be in 'quote_approved' status. Current: {parent.status}",
                        status_code=422)
                # Mirrors convert_to_repair's/spawn_repair's own existing
                # duplicate-repair guard -- without this, a caller with
                # create_job's own mutation-scope-aware permission could
                # bypass that established uniqueness rule simply by posting a
                # REPAIR job directly with parent_job_id set to a consultation
                # that already has one.
                er = await self.db.execute(select(Job).where(
                    Job.parent_job_id == parent.id, Job.job_type == JobType.REPAIR))
                if er.scalar_one_or_none():
                    raise ServiceOSException("CONSULTATION_ALREADY_CONVERTED",
                        "A repair job already exists for this consultation.", status_code=409)
        booking = None
        if data.get("booking_id"):
            from app.engines.booking.models import Booking
            try:
                booking_uuid = uuid.UUID(str(data["booking_id"]))
            except ValueError:
                raise ServiceOSException("FOREIGN_BOOKING",
                    "booking_id is not a valid identifier.", status_code=422)
            br = await self.db.execute(select(Booking).where(Booking.id == booking_uuid))
            booking = br.scalar_one_or_none()
            if not booking or booking.tenant_id != tenant_id:
                raise ServiceOSException("FOREIGN_BOOKING",
                    f"booking_id '{data['booking_id']}' does not belong to this tenant.",
                    status_code=422)
            # Slice 2F-14D: booking_id is customer- and service-authoritative --
            # a Job cannot claim a booking reference while showing a DIFFERENT
            # customer or service than that booking actually has (this would
            # otherwise silently mislead any downstream consumer -- billing,
            # notifications, audit -- that trusts job.booking_id to correlate
            # with the real booking). The canonical, atomic booking-conversion
            # pipeline remains Booking.convert_to_job (unmodified, out of
            # scope) -- this only closes the same-tenant cross-field
            # consistency gap on field_ops.router's own separate, generic
            # create_job endpoint.
            if data.get("customer_id") and str(booking.customer_id) != str(data["customer_id"]):
                raise ServiceOSException("CUSTOMER_BOOKING_MISMATCH",
                    "customer_id does not match booking_id's customer.", status_code=422)
            if data.get("service_type_id") and booking.service_type_id != data["service_type_id"]:
                raise ServiceOSException("SERVICE_BOOKING_MISMATCH",
                    "service_type_id does not match booking_id's service type.", status_code=422)
            # Slice 2F-14E: booking_id's customer/service cross-check and
            # duplicate-conversion guard (both already established) make this
            # field an AUTHORITATIVE_LINEAGE_REFERENCE, not merely
            # informational -- so the same source-state prerequisite
            # Booking.convert_to_job already enforces (BS.CONFIRMED) is now
            # enforced here too, closing the gap where create_job's own
            # separate endpoint could reference a draft/pending/cancelled/
            # rejected/expired/voided booking that convert_to_job itself would
            # never have accepted. Reuses the existing BS constant; no new
            # eligibility rule is invented.
            from app.engines.booking.constants import BS
            if booking.status != BS.CONFIRMED:
                raise ServiceOSException("BOOKING_INVALID_STATUS_TRANSITION",
                    f"Only confirmed bookings can be referenced by a job. Current: {booking.status}",
                    status_code=422)
            # Mirrors Booking.convert_to_job's own existing duplicate-conversion
            # guard (b.converted_job_id / existing-Job-by-booking_id checks) --
            # without this, create_job's own separate endpoint could create a
            # second Job referencing a booking that already has one.
            if booking.converted_job_id:
                raise ServiceOSException("JOB_ALREADY_EXISTS_FOR_BOOKING",
                    "A job already exists for this booking.", status_code=409)
            existing_r = await self.db.execute(select(Job).where(Job.booking_id == str(booking_uuid)))
            if existing_r.scalar_one_or_none():
                raise ServiceOSException("JOB_ALREADY_EXISTS_FOR_BOOKING",
                    "A job already exists for this booking.", status_code=409)
            # Slice 2F-15A: directly supplying booking_id to create_job must
            # not bypass the identical provenance protection
            # Booking.convert_to_job now enforces -- a provider-created
            # Booking (including a legacy, pre-fix one) requires INDEPENDENT
            # prior relationship evidence (excluding this same booking)
            # before it may be used to create a Job here.
            # Slice 2F-15C: creator_role alone is not sufficient -- the actor
            # who performed the creation event must also BE this booking's
            # own customer (changed_by == booking.customer_id), not merely
            # someone holding the "customer" role. Filtered directly in SQL
            # (not read-then-compare in Python) so the query shape --
            # scalar_one_or_none() returning a match-or-None -- stays
            # consistent with every other provenance check in this file.
            from app.engines.booking.models import BookingStatusHistory as _BSH
            creator_r = await self.db.execute(select(_BSH.id).where(
                _BSH.booking_id == booking.id, _BSH.from_status.is_(None),
                _BSH.changed_by_role == "customer", _BSH.changed_by == booking.customer_id,
            ).limit(1))
            creator_is_customer_originated = creator_r.scalar_one_or_none() is not None
            if not creator_is_customer_originated:
                from app.engines.booking.models import Booking as _Booking
                QUALIFYING_BOOKING_STATUSES = (
                    BS.CONFIRMED, BS.SCHEDULED, BS.DISPATCHING, BS.IN_PROGRESS,
                    BS.COMPLETED, BS.CONVERTED_TO_JOB,
                )
                indep_br = await self.db.execute(
                    select(_Booking.id)
                    .join(_BSH, _BSH.booking_id == _Booking.id)
                    .where(
                        _Booking.tenant_id == tenant_id, _Booking.customer_id == booking.customer_id,
                        _Booking.id != booking.id,
                        _Booking.status.in_(QUALIFYING_BOOKING_STATUSES),
                        _BSH.from_status.is_(None), _BSH.changed_by_role == "customer",
                        _BSH.changed_by == _Booking.customer_id,
                    ).limit(1))
                has_independent = indep_br.scalar_one_or_none() is not None
                if not has_independent:
                    indep_jr = await self.db.execute(select(Job.id).where(
                        Job.tenant_id == tenant_id, Job.customer_id == booking.customer_id,
                        Job.booking_id != str(booking.id),
                        or_(Job.booking_id.isnot(None), Job.parent_job_id.isnot(None)),
                    ).limit(1))
                    has_independent = indep_jr.scalar_one_or_none() is not None
                if not has_independent:
                    raise ServiceOSException("CUSTOMER_TENANT_RELATIONSHIP_REQUIRED",
                        "This booking cannot be used to create a job without "
                        "independent, established relationship evidence for "
                        "this customer.", status_code=422)
        if data.get("customer_id"):
            from app.engines.auth.models import User
            customer_uuid = uuid.UUID(data["customer_id"])
            cr = await self.db.execute(select(User).where(User.id == customer_uuid))
            customer_user = cr.scalar_one_or_none()
            if not customer_user or customer_user.role != "customer":
                raise ServiceOSException("FOREIGN_CUSTOMER",
                    f"customer_id '{data['customer_id']}' is not a valid customer account.",
                    status_code=422)
            # Slice 2F-14F: a deleted/deactivated customer account cannot be
            # newly associated with a Job -- mirrors the existing
            # staff.is_active check pattern already used by
            # Booking.convert_to_job for staff assignment.
            if not customer_user.is_active or customer_user.deleted_at is not None:
                raise ServiceOSException("FOREIGN_CUSTOMER",
                    f"customer_id '{data['customer_id']}' is not a valid customer account.",
                    status_code=422)
            # Slice 2F-14F (ratified product decision): a tenant mutation
            # permission grants authority over the tenant's own operations --
            # it does not automatically grant authority over every customer
            # identity on the platform. Booking-referenced and parent-Job-
            # derived creation already prove the tenant/customer relationship
            # intrinsically (the Booking/parent Job itself IS the evidence,
            # already tenant-owned and customer-cross-checked above) -- no
            # extra query is needed for those. Standalone manual creation
            # (neither booking_id nor parent_job_id supplied) requires an
            # existing same-tenant Booking or Job for this customer; a
            # completely unrelated global customer, or one known only to a
            # DIFFERENT tenant, is rejected with the same safe, uniform error
            # regardless of which case applies (never discloses whether the
            # customer is known to another tenant).
            if not data.get("booking_id") and not data.get("parent_job_id"):
                await self._assert_tenant_customer_relationship(tenant_id, customer_uuid)

        job = Job(
            tenant_id=tenant_id, job_number=self._generate_job_number(),
            title=data["title"], description=data.get("description"),
            service_type_id=data["service_type_id"],
            service_category=data.get("service_category", "general"),
            job_type=data.get("job_type", JobType.REPAIR),
            parent_job_id=uuid.UUID(data["parent_job_id"]) if data.get("parent_job_id") else None,
            findings=data.get("findings"), recommendation=data.get("recommendation"),
            checklist=data.get("checklist", []),
            duration_estimate_minutes=data.get("duration_estimate_minutes"),
            booking_id=data.get("booking_id"),
            customer_id=uuid.UUID(data["customer_id"]) if data.get("customer_id") else None,
            address=data.get("address", {}), pincode=data.get("pincode"),
            latitude=data.get("latitude"), longitude=data.get("longitude"),
            scheduled_at=datetime.fromisoformat(data["scheduled_at"]) if data.get("scheduled_at") else None,
            quoted_price=Decimal(str(data["quoted_price"])) if data.get("quoted_price") else None,
            tags=data.get("tags", []),
        )
        # If job_type was not explicitly provided, auto-detect from service catalog.
        # This ensures direct job creation (outside booking flow) respects the
        # tenant's catalog definitions for checklist, duration, and pricing model.
        if not data.get("job_type") and data.get("service_type_id"):
            try:
                cat = catalog_item
                if cat and cat.is_active:
                    job.job_type = cat.service_type
                    if not data.get("duration_estimate_minutes") and cat.estimated_duration_minutes:
                        job.duration_estimate_minutes = cat.estimated_duration_minutes
                    if not data.get("checklist") and cat.checklist_template:
                        job.checklist = [{"step": s, "completed": False} for s in cat.checklist_template]
                    if not data.get("quoted_price") and cat.pricing_model == "fixed" and cat.base_price:
                        job.quoted_price = Decimal(str(cat.base_price))
            except Exception as e:
                logger.warning("fieldops.catalog_lookup_failed", error=str(e))

        self.db.add(job); await self.db.flush()
        await self._write_history(job, None, JS.DRAFT, "Job created", None, None)
        try:
            from app.core.usage_quota import adjust_usage
            await adjust_usage(self.db, tenant_id, "current_active_jobs", 1)
        except Exception as e:
            logger.warning("fieldops.job_usage_increment_failed", error=str(e))
        # Cache customer token for public tracking
        try:
            await self.redis.setex(REDIS_JOB_TOKEN.format(token=job.customer_token),
                                    86400 * 30, str(job.id))
        except Exception:
            pass
        await self._publish("job.created", str(tenant_id), str(job.id),
                            {"job_number": job.job_number, "status": JS.DRAFT})
        return self._job_dict(job)

    async def get_job(self, job_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job: raise NotFoundException("Job", str(job_id))
        self._assert_can_access_job(job)
        return self._job_dict(job)

    async def list_jobs(self, tenant_id: uuid.UUID, status: str | None,
                         staff_id: uuid.UUID | None, limit: int, cursor: str | None,
                         job_type: str | None = None, service_id: uuid.UUID | None = None,
                         city: str | None = None, zipcode: str | None = None,
                         scheduled_from: str | None = None, scheduled_to: str | None = None,
                         search: str | None = None) -> dict:
        # Staff can only ever see their own jobs — override regardless of what was requested.
        if self.actor_role in ("staff", "technician"):
            staff_id = self.actor_id
        # tenant_owner and staff/technician are always scoped to their own tenant —
        # the tenant_id query param is ignored for both (previously only tenant_owner
        # was scoped this way, leaving a technician free to pass an arbitrary
        # tenant_id and query another tenant's jobs table).
        if self.actor_role in ("tenant_owner", "staff", "technician") and self.actor_tenant_id is not None:
            tenant_id = self.actor_tenant_id
        q = select(Job).where(Job.tenant_id == tenant_id).order_by(Job.created_at.desc())
        if self.actor_role == "customer":
            q = q.where(Job.customer_id == self.actor_id)
        if status:     q = q.where(Job.status == status)
        if staff_id:   q = q.where(Job.assigned_staff_id == staff_id)
        if job_type:   q = q.where(Job.job_type == job_type)
        if service_id: q = q.where(Job.service_id == service_id)
        if city:       q = q.where(Job.city == city)
        if zipcode:    q = q.where(Job.zipcode == zipcode)
        if scheduled_from:
            try: q = q.where(Job.scheduled_at >= datetime.fromisoformat(scheduled_from))
            except Exception: pass
        if scheduled_to:
            try: q = q.where(Job.scheduled_at <= datetime.fromisoformat(scheduled_to))
            except Exception: pass
        if search:     q = q.where(Job.title.ilike(f"%{search}%"))
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(Job.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        jobs = r.scalars().all()
        has_next = len(jobs) > limit; jobs = jobs[:limit]
        nc = encode_cursor({"created_at": jobs[-1].created_at.isoformat()}) if has_next and jobs else None
        return {"jobs": [self._job_dict(j) for j in jobs], "has_next": has_next, "next_cursor": nc}

    # ── Step 6: Job Assignment + Staff Status Lifecycle ──────────────────────
    async def assign_staff(self, job_id: uuid.UUID, staff_id: uuid.UUID,
                            notes: str | None = None) -> dict:
        """Tenant owner assigns (or reassigns) a job to an active staff member
        of their own tenant. Atomic: validates staff, sets status=assigned,
        writes history."""
        job = await self._get_job_for_assignment(job_id)
        if job.status not in (JS.PENDING_ASSIGNMENT, JS.ASSIGNED, JS.REJECTED_BY_STAFF):
            raise ServiceOSException("JOB_NOT_ASSIGNABLE",
                f"Job in status '{job.status}' cannot be assigned.", status_code=422,
                context={"current_status": job.status})

        from app.engines.auth.models import User
        sr = await self.db.execute(select(User).where(User.id == staff_id))
        staff = sr.scalar_one_or_none()
        if not staff or staff.role not in ("staff", "technician"):
            raise ServiceOSException("STAFF_NOT_FOUND", f"Staff '{staff_id}' not found.", status_code=404)
        if staff.tenant_id != job.tenant_id:
            raise ServiceOSException("CROSS_TENANT_ASSIGNMENT_BLOCKED",
                "Staff belongs to a different tenant.", status_code=403)
        if not staff.is_active:
            raise ServiceOSException("STAFF_INACTIVE", "Staff member is inactive.", status_code=422)

        from_status = job.status
        job.assigned_staff_id = staff.id
        job.assigned_at = utcnow()
        job.assigned_by_user_id = self.actor_id
        job.staff_rejection_reason = None
        job.status = JS.ASSIGNED
        job.status_updated_at = utcnow()
        job.current_status_started_at = utcnow()
        await self._write_history(job, from_status, JS.ASSIGNED, notes or "Assigned to staff", None, None)
        await self._publish("job.assigned", str(job.tenant_id), str(job.id), {"staff_id": str(staff.id)})
        return {"job_id": str(job.id), "status": job.status, "assigned_staff_id": str(staff.id),
                "assigned_staff_name": staff.full_name, "message": "Job assigned successfully"}

    async def accept_job(self, job_id: uuid.UUID, notes: str | None = None) -> dict:
        """Assigned staff accepts the job."""
        job = await self._get_job_for_staff_action(job_id)
        if job.status != JS.ASSIGNED:
            raise ServiceOSException("INVALID_JOB_STATUS_TRANSITION",
                f"Job must be 'assigned' to accept it. Current status: {job.status}", status_code=422,
                context={"current_status": job.status})
        from_status = job.status
        job.status = JS.ACCEPTED
        job.accepted_at = utcnow()
        job.status_updated_at = utcnow()
        job.current_status_started_at = utcnow()
        await self._write_history(job, from_status, JS.ACCEPTED, notes or "Staff accepted job", None, None)
        await self._publish("job.accepted", str(job.tenant_id), str(job.id), {})
        return self._job_dict(job)

    async def reject_assignment(self, job_id: uuid.UUID, reason: str) -> dict:
        """Assigned staff rejects the job — tenant must reassign."""
        if not reason or not reason.strip():
            raise ServiceOSException("JOB_REJECTION_REASON_REQUIRED",
                "A rejection reason is required.", status_code=422)
        job = await self._get_job_for_staff_action(job_id)
        if job.status != JS.ASSIGNED:
            raise ServiceOSException("INVALID_JOB_STATUS_TRANSITION",
                f"Job must be 'assigned' to reject it. Current status: {job.status}", status_code=422,
                context={"current_status": job.status})
        from_status = job.status
        job.status = JS.REJECTED_BY_STAFF
        job.rejected_at = utcnow()
        job.staff_rejection_reason = reason.strip()
        job.status_updated_at = utcnow()
        job.current_status_started_at = utcnow()
        await self._write_history(job, from_status, JS.REJECTED_BY_STAFF, reason.strip(), None, None)
        await self._publish("job.rejected_by_staff", str(job.tenant_id), str(job.id),
                            {"reason": reason.strip()})
        return self._job_dict(job)

    async def get_valid_next_statuses(self, job_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job: raise ServiceOSException("JOB_NOT_FOUND", f"Job '{job_id}' not found.", status_code=404)
        self._assert_can_access_job(job)
        allowed = self._business_filtered_transitions(job)
        return {"job_id": str(job_id), "current_status": job.status, "job_type": job.job_type,
                "valid_next_statuses": allowed}

    async def get_job_history(self, job_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job: raise ServiceOSException("JOB_NOT_FOUND", f"Job '{job_id}' not found.", status_code=404)
        self._assert_can_access_job(job)
        hr = await self.db.execute(select(JobStatusHistory).where(
            JobStatusHistory.job_id == job_id).order_by(JobStatusHistory.created_at))
        history = hr.scalars().all()
        return {"job_id": str(job_id), "history": [
            {"old_status": h.from_status, "new_status": h.to_status,
             "actor_role": h.changed_by_role, "notes": h.reason,
             "created_at": h.created_at.isoformat()} for h in history]}

    # ── Step 6: Customer job tracking ─────────────────────────────────────────
    async def list_customer_jobs(self, customer_id: uuid.UUID, limit: int, cursor: str | None) -> dict:
        q = select(Job).where(Job.customer_id == customer_id).order_by(Job.created_at.desc())
        if cursor:
            try:
                c = decode_cursor(cursor)
                q = q.where(Job.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass
        q = q.limit(limit + 1)
        r = await self.db.execute(q)
        jobs = r.scalars().all()
        has_next = len(jobs) > limit; jobs = jobs[:limit]
        nc = encode_cursor({"created_at": jobs[-1].created_at.isoformat()}) if has_next and jobs else None
        return {"jobs": [self._job_dict(j) for j in jobs], "has_next": has_next, "next_cursor": nc}

    async def get_customer_job(self, job_id: uuid.UUID, customer_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job or job.customer_id != customer_id:
            raise NotFoundException("Job", str(job_id))
        return self._job_dict(job)

    async def get_customer_job_progress(self, job_id: uuid.UUID, customer_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job or job.customer_id != customer_id:
            raise NotFoundException("Job", str(job_id))
        self._update_sla(job)
        staff_summary = None
        if job.assigned_staff_id:
            from app.engines.auth.models import User
            sr = await self.db.execute(select(User).where(User.id == job.assigned_staff_id))
            staff = sr.scalar_one_or_none()
            if staff:
                staff_summary = {"name": staff.full_name, "phone": staff.phone}
        return {
            "job_id": str(job.id), "booking_id": job.booking_id, "status": job.status,
            "progress_steps": _resolve_transitions(job.job_type, job.status),
            "assigned_staff": staff_summary,
            "scheduled_at": job.scheduled_at.isoformat() if job.scheduled_at else None,
            "city": job.city, "zipcode": job.zipcode, "service_name": job.service_type_id,
            "estimated_price": float(job.estimated_price) if job.estimated_price else None,
            "sla_minutes": job.sla_minutes, "minutes_in_status": job.minutes_in_status,
            "sla_breached": job.sla_breached, "sla_breach_level": job.sla_breach_level,
        }

    # ── Status Transition (core method) ──────────────────────────────────────
    async def update_status(self, job_id: uuid.UUID, to_status: str,
                             reason: str | None, lat: float | None, lng: float | None,
                             emergency_assessment: bool = False) -> dict:
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job: raise NotFoundException("Job", str(job_id))
        self._assert_assigned(job)
        if (self.actor_role == "tenant_owner" and self.actor_tenant_id is not None
                and job.tenant_id != self.actor_tenant_id):
            raise NotFoundException("Job", str(job_id))

        if job.status in TERMINAL_STATUSES:
            raise ServiceOSException("CONFLICT",
                f"Job is in terminal status '{job.status}' and cannot be transitioned.",
                context={"current_status": job.status, "terminal": True})

        # Step 7: job-type-specific business guards (explicit error codes,
        # checked before the generic graph lookup below).
        if job.job_type == JobType.CONSULTATION and to_status == JS.WORK_STARTED:
            raise ServiceOSException("WORK_NOT_ALLOWED_FOR_CONSULTATION",
                "Consultation jobs never start physical work.", status_code=422)
        if (job.job_type == JobType.SERVICE and to_status == JS.ASSESSMENT_STARTED
                and not emergency_assessment):
            raise ServiceOSException("ASSESSMENT_NOT_ALLOWED_FOR_SERVICE",
                "Service jobs skip assessment by default. Pass emergency_assessment=true to override.",
                status_code=422)
        if (job.job_type == JobType.REPAIR and to_status == JS.WORK_STARTED
                and job.quote_required is True and job.status != JS.QUOTE_APPROVED):
            raise ServiceOSException("QUOTE_REQUIRED_BEFORE_WORK",
                "This repair requires an approved quote before work can start.", status_code=422,
                context={"current_status": job.status})
        if (job.job_type == JobType.SERVICE and to_status == JS.WORK_COMPLETE
                and job.checklist_required is True and job.status != JS.CHECKLIST_COMPLETE):
            raise ServiceOSException("CHECKLIST_REQUIRED_BEFORE_WORK_COMPLETE",
                "This service job requires checklist completion before work_complete.", status_code=422,
                context={"current_status": job.status})

        allowed = _resolve_transitions(job.job_type, job.status)
        if (job.job_type == JobType.SERVICE and to_status == JS.ASSESSMENT_STARTED
                and emergency_assessment and job.status == JS.ARRIVED):
            allowed = list(allowed) + [JS.ASSESSMENT_STARTED]  # Step 7: emergency override
        if to_status not in allowed:
            raise ServiceOSException("INVALID_TRANSITION",
                f"Transition from '{job.status}' to '{to_status}' is not allowed.",
                resolution=f"Allowed transitions from '{job.status}': {allowed}",
                context={"from_status": job.status, "to_status": to_status,
                         "allowed_transitions": allowed})

        if (to_status == JS.WORK_COMPLETE and job.job_type == JobType.SERVICE
                and job.checklist and not all(item.get("completed") for item in job.checklist)):
            raise ServiceOSException("CHECKLIST_INCOMPLETE",
                "All checklist items must be completed before finishing a service job.",
                context={"incomplete": [i["step"] for i in job.checklist if not i.get("completed")]})

        from_status = job.status
        job.status = to_status
        job.status_updated_at = utcnow()
        job.current_status_started_at = utcnow()

        if to_status == JS.WORK_STARTED and not job.started_at:
            job.started_at = utcnow()
            job.work_started_at = job.work_started_at or utcnow()
        if to_status == JS.WORK_COMPLETE:
            job.completed_at = utcnow()
            job.work_completed_at = utcnow()
        if to_status == JS.EN_ROUTE:
            job.en_route_at = utcnow()
        if to_status == JS.ARRIVED:
            job.arrived_at = utcnow()
        if to_status == JS.CANCELLED:
            job.cancelled_at = utcnow()
            job.cancellation_reason = reason

        if to_status in TERMINAL_STATUSES:
            try:
                from app.core.usage_quota import adjust_usage
                await adjust_usage(self.db, job.tenant_id, "current_active_jobs", -1)
            except Exception as e:
                logger.warning("fieldops.job_usage_decrement_failed", error=str(e))

        if to_status == JS.INVOICE_GENERATED:
            try:
                from app.engines.document.service import DocumentService
                amount = job.final_price or job.quoted_price or Decimal("0")
                # Phase 2A Slice 2F-35: generate_document now requires trusted
                # tenant context; this internal system-triggered invoice
                # generation is explicitly trusted for the job's own tenant.
                await DocumentService(self.db, actor_id=self.actor_id,
                                       actor_tenant_id=job.tenant_id).generate_document(
                    job.tenant_id, "invoice", entity_type="job", entity_id=str(job.id),
                    customer_id=job.customer_id,
                    variables={"job_number": job.job_number, "title": job.title,
                               "amount": str(amount), "service_type": job.service_type_id})
            except Exception as e:
                logger.warning("fieldops.invoice_generation_failed", job_id=str(job_id), error=str(e))

        await self._write_history(job, from_status, to_status, reason, lat, lng)
        await self._publish("job.status_changed", str(job.tenant_id), str(job_id),
                            {"from": from_status, "to": to_status, "job_number": job.job_number})

        # SLA breach detection
        if to_status in DEFAULT_STATUS_SLA_HOURS:
            sla_hours = DEFAULT_STATUS_SLA_HOURS[to_status]
            try:
                await self.redis.setex(
                    f"serviceos:fo:sla:{job_id}:{to_status}",
                    int(sla_hours * 3600) + 300, "1")
            except Exception:
                pass

        logger.info("fieldops.status_changed", job_id=str(job_id),
                    from_status=from_status, to_status=to_status)
        return self._job_dict(job)

    # ── Universal Service Phase Logic (Phase 7) ──────────────────────────────
    async def submit_findings(self, job_id: uuid.UUID, findings: str,
                               recommendation: str | None) -> dict:
        """Technician records what they found during assessment. Used by both
        repair (optional) and consultation (mandatory) job types."""
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job: raise NotFoundException("Job", str(job_id))
        self._assert_assigned(job)
        if job.status not in (JS.ASSESSMENT_STARTED, JS.ASSESSMENT_COMPLETE):
            raise ServiceOSException("CONFLICT",
                f"Findings can only be submitted during assessment. Current status: {job.status}")
        job.findings = findings
        job.recommendation = recommendation
        if job.status == JS.ASSESSMENT_STARTED:
            await self._write_history(job, job.status, JS.ASSESSMENT_COMPLETE,
                                       "Findings submitted", None, None)
            job.status = JS.ASSESSMENT_COMPLETE
        return self._job_dict(job)

    async def update_checklist(self, job_id: uuid.UUID, items: list[dict]) -> dict:
        """Maintenance/service jobs: technician marks checklist steps complete.
        Each item: {"step": str, "completed": bool}."""
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job: raise NotFoundException("Job", str(job_id))
        self._assert_assigned(job)
        job.checklist = items
        return self._job_dict(job)

    # ── Step 7: Assessment workflow (repair / consultation) ──────────────────
    async def start_assessment(self, job_id: uuid.UUID) -> dict:
        job = await self._get_job_for_staff_action(job_id)
        if job.job_type not in (JobType.REPAIR, JobType.CONSULTATION):
            raise ServiceOSException("ASSESSMENT_NOT_ALLOWED_FOR_SERVICE",
                "Service jobs do not require assessment by default.", status_code=422,
                context={"job_type": job.job_type})
        if job.status != JS.ARRIVED:
            raise ServiceOSException("INVALID_JOB_STATUS_TRANSITION",
                f"Assessment can only start from 'arrived'. Current status: {job.status}",
                status_code=422, context={"current_status": job.status})
        from_status = job.status
        job.status = JS.ASSESSMENT_STARTED
        job.status_updated_at = utcnow()
        job.current_status_started_at = utcnow()
        await self._write_history(job, from_status, JS.ASSESSMENT_STARTED, "Assessment started", None, None)
        await self._publish("job.assessment_started", str(job.tenant_id), str(job.id), {})
        return self._job_dict(job)

    async def complete_assessment(self, job_id: uuid.UUID, findings: str,
                                   recommended_work: str | None = None,
                                   estimated_parts: list[dict] | None = None,
                                   labour_estimate: Decimal | None = None,
                                   parts_estimate: Decimal | None = None,
                                   quote_required: bool = False) -> dict:
        job = await self._get_job_for_staff_action(job_id)
        if job.status != JS.ASSESSMENT_STARTED:
            raise ServiceOSException("ASSESSMENT_NOT_STARTED",
                f"Assessment must be started before it can be completed. Current status: {job.status}",
                status_code=422, context={"current_status": job.status})
        if not findings or not findings.strip():
            raise ServiceOSException("ASSESSMENT_FINDINGS_REQUIRED",
                "Assessment findings are required.", status_code=422)
        if job.job_type in (JobType.REPAIR, JobType.CONSULTATION) and not (recommended_work or "").strip():
            raise ServiceOSException("ASSESSMENT_FINDINGS_REQUIRED",
                "recommended_work is required for repair/consultation jobs.", status_code=422)

        job.assessment_findings = findings.strip()
        job.recommended_work = (recommended_work or "").strip() or None
        job.estimated_parts = estimated_parts or []
        job.assessment_completed_at = utcnow()
        # Mirror into the legacy findings/recommendation fields so the existing
        # spawn-repair-on-quote-approval path (Phase 7) keeps working unchanged.
        job.findings = job.assessment_findings
        job.recommendation = job.recommended_work

        from_status = job.status
        job.status = JS.ASSESSMENT_COMPLETE
        job.status_updated_at = utcnow()
        job.current_status_started_at = utcnow()

        if job.job_type == JobType.REPAIR:
            job.quote_required = bool(quote_required)
            total_estimate = (labour_estimate or Decimal("0")) + (parts_estimate or Decimal("0"))
            if (job.quote_required and job.pre_approval_limit is not None
                    and total_estimate <= job.pre_approval_limit):
                job.quote_required = False  # auto-approved — under the pre-approval limit

        await self._write_history(job, from_status, JS.ASSESSMENT_COMPLETE,
                                   "Assessment completed", None, None)
        await self._publish("job.assessment_completed", str(job.tenant_id), str(job.id), {})
        return self._job_dict(job)

    # ── Step 7: Job Quotes (richer line-item quotes) ──────────────────────────
    def _generate_quote_number(self) -> str:
        return f"QT-{utcnow().strftime('%Y%m')}-{random.randint(10000,99999)}"

    def _job_quote_dict(self, q: JobQuote) -> dict:
        return {
            "quote_id": str(q.id), "job_id": str(q.job_id), "tenant_id": str(q.tenant_id),
            "customer_id": str(q.customer_id) if q.customer_id else None,
            "quote_number": q.quote_number, "quote_type": q.quote_type,
            "findings": q.findings_snapshot, "recommended_work": q.recommended_work,
            "labour_amount": float(q.labour_amount), "parts_amount": float(q.parts_amount),
            "visit_fee": float(q.visit_fee), "discount_amount": float(q.discount_amount),
            "tax_amount": float(q.tax_amount),
            "total_amount": float(q.total_amount) if q.total_amount is not None else None,
            "pre_approval_limit": float(q.pre_approval_limit) if q.pre_approval_limit is not None else None,
            "requires_customer_approval": q.requires_customer_approval,
            "status": q.status,
            "sent_at": q.sent_at.isoformat() if q.sent_at else None,
            "approved_at": q.approved_at.isoformat() if q.approved_at else None,
            "rejected_at": q.rejected_at.isoformat() if q.rejected_at else None,
            "rejection_reason": q.rejection_reason,
            "expires_at": q.expires_at.isoformat() if q.expires_at else None,
            "is_expired": bool(q.expires_at and q.status == "sent" and utcnow() > q.expires_at),
            "created_at": q.created_at.isoformat() if q.created_at else None,
        }

    async def _get_job_for_quote_management(self, job_id: uuid.UUID) -> Job:
        """Staff (own assigned job) or tenant_owner (own tenant) may manage
        (create/send) a provider quote. Slice 2F-14B: this previously never
        denied actor_role == "customer" at all -- none of the staff/technician
        or tenant_owner branches fire for a customer actor, so a customer
        could create or send a provider-authored quote on ANY job (quote
        administration is a provider-only capability; customers only ever
        *respond* to a quote via respond_to_quote/approve_job_quote/
        reject_job_quote)."""
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job:
            raise ServiceOSException("JOB_NOT_FOUND", f"Job '{job_id}' not found.", status_code=404)
        if self.actor_role == "customer":
            raise ServiceOSException("QUOTE_ACCESS_DENIED",
                "Customers cannot administer provider quotes.", status_code=403)
        if self.actor_role in ("staff", "technician") and job.assigned_staff_id != self.actor_id:
            raise ServiceOSException("STAFF_NOT_ASSIGNED_TO_JOB",
                "This job is not assigned to you.", status_code=403)
        if (self.actor_role == "tenant_owner" and self.actor_tenant_id is not None
                and job.tenant_id != self.actor_tenant_id):
            raise ServiceOSException("JOB_NOT_FOUND", f"Job '{job_id}' not found.", status_code=404)
        return job

    async def create_job_quote(self, job_id: uuid.UUID, data: dict) -> dict:
        job = await self._get_job_for_quote_management(job_id)
        if job.status != JS.ASSESSMENT_COMPLETE:
            raise ServiceOSException("ASSESSMENT_NOT_STARTED",
                "A quote can only be created after assessment is complete.", status_code=422,
                context={"current_status": job.status})

        amounts = {
            "labour_amount": Decimal(str(data.get("labour_amount", 0))),
            "parts_amount": Decimal(str(data.get("parts_amount", 0))),
            "visit_fee": Decimal(str(data.get("visit_fee", 0))),
            "discount_amount": Decimal(str(data.get("discount_amount", 0))),
            "tax_amount": Decimal(str(data.get("tax_amount", 0))),
        }
        for name, amt in amounts.items():
            if amt < 0:
                raise ServiceOSException("INVALID_QUOTE_AMOUNT", f"{name} cannot be negative.", status_code=422)
        total = (amounts["labour_amount"] + amounts["parts_amount"] + amounts["visit_fee"]
                 + amounts["tax_amount"] - amounts["discount_amount"])
        if total < 0:
            raise ServiceOSException("INVALID_QUOTE_AMOUNT", "total_amount cannot be negative.", status_code=422)
        if not (data.get("recommended_work") or job.recommended_work):
            raise ServiceOSException("ASSESSMENT_FINDINGS_REQUIRED",
                "recommended_work is required to create a quote.", status_code=422)

        quote = JobQuote(
            job_id=job.id, tenant_id=job.tenant_id, customer_id=job.customer_id,
            amount=total, quote_number=self._generate_quote_number(),
            quote_type=("consultation_recommendation" if job.job_type == JobType.CONSULTATION
                        else "repair_quote"),
            findings_snapshot=job.assessment_findings or job.findings,
            recommendation_snapshot=job.recommended_work or job.recommendation,
            recommended_work=data.get("recommended_work") or job.recommended_work,
            status="draft", created_by=self.actor_id, created_by_staff_id=self.actor_id,
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            pre_approval_limit=job.pre_approval_limit, total_amount=total,
            **amounts,
        )
        self.db.add(quote)
        await self.db.flush()
        return self._job_quote_dict(quote)

    async def list_job_quotes(self, job_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(JobQuote).where(JobQuote.job_id == job_id)
                                   .order_by(JobQuote.created_at.desc()))
        quotes = r.scalars().all()
        return {"job_id": str(job_id), "quotes": [self._job_quote_dict(q) for q in quotes]}

    async def get_job_quote(self, job_id: uuid.UUID, quote_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(JobQuote).where(JobQuote.id == quote_id))
        quote = r.scalar_one_or_none()
        if not quote or quote.job_id != job_id:
            raise ServiceOSException("QUOTE_NOT_FOUND", f"Quote '{quote_id}' not found.", status_code=404)
        return self._job_quote_dict(quote)

    async def send_job_quote(self, job_id: uuid.UUID, quote_id: uuid.UUID) -> dict:
        job = await self._get_job_for_quote_management(job_id)
        qr = await self.db.execute(select(JobQuote).where(JobQuote.id == quote_id))
        quote = qr.scalar_one_or_none()
        if not quote or quote.job_id != job.id:
            raise ServiceOSException("QUOTE_NOT_FOUND", f"Quote '{quote_id}' not found.", status_code=404)
        if quote.status in ("sent", "approved", "rejected"):
            raise ServiceOSException("QUOTE_ALREADY_SENT", f"Quote already {quote.status}.", status_code=409)

        er = await self.db.execute(select(JobQuote).where(
            JobQuote.job_id == job.id, JobQuote.status == "sent"))
        if er.scalars().all():
            raise ServiceOSException("QUOTE_ALREADY_SENT",
                "Another quote is already sent and pending for this job.", status_code=409)

        allowed = _resolve_transitions(job.job_type, job.status)
        if JS.QUOTE_SENT not in allowed:
            raise ServiceOSException("INVALID_JOB_STATUS_TRANSITION",
                f"Cannot send a quote from job status '{job.status}'.", status_code=422,
                context={"current_status": job.status})

        quote.status = "sent"; quote.sent_at = utcnow()
        from_status = job.status
        job.status = JS.QUOTE_SENT
        job.quote_id = quote.id
        job.quote_sent_at = utcnow()
        job.status_updated_at = utcnow()
        job.current_status_started_at = utcnow()
        await self._write_history(job, from_status, JS.QUOTE_SENT,
                                   f"Quote {quote.quote_number} sent", None, None)
        await self._publish("job.quote_sent", str(job.tenant_id), str(job.id),
                            {"quote_id": str(quote.id), "total_amount": float(quote.total_amount or 0)})
        return self._job_quote_dict(quote)

    async def _get_quote_for_customer(self, job_id: uuid.UUID, quote_id: uuid.UUID,
                                       customer_id: uuid.UUID) -> tuple[Job, JobQuote]:
        jr = await self.db.execute(select(Job).where(Job.id == job_id))
        job = jr.scalar_one_or_none()
        if not job or job.customer_id != customer_id:
            raise ServiceOSException("JOB_NOT_FOUND", f"Job '{job_id}' not found.", status_code=404)
        qr = await self.db.execute(select(JobQuote).where(JobQuote.id == quote_id))
        quote = qr.scalar_one_or_none()
        if not quote or quote.job_id != job.id:
            raise ServiceOSException("QUOTE_NOT_FOUND", f"Quote '{quote_id}' not found.", status_code=404)
        if quote.customer_id != customer_id:
            raise ServiceOSException("QUOTE_ACCESS_DENIED",
                "This quote does not belong to you.", status_code=403)
        return job, quote

    async def approve_job_quote(self, job_id: uuid.UUID, quote_id: uuid.UUID,
                                 customer_id: uuid.UUID) -> dict:
        job, quote = await self._get_quote_for_customer(job_id, quote_id, customer_id)
        if quote.status == "approved":
            raise ServiceOSException("QUOTE_ALREADY_APPROVED", "Quote already approved.", status_code=409)
        if quote.status == "rejected":
            raise ServiceOSException("QUOTE_ALREADY_REJECTED", "Quote already rejected.", status_code=409)
        if quote.status != "sent":
            raise ServiceOSException("QUOTE_APPROVAL_REQUIRED",
                "Quote must be sent before it can be approved.", status_code=422)
        if quote.expires_at and utcnow() > quote.expires_at:
            quote.status = "expired"
            raise ServiceOSException("QUOTE_EXPIRED",
                "This quote has expired and can no longer be approved.", status_code=409)

        allowed = _resolve_transitions(job.job_type, job.status)
        if JS.QUOTE_APPROVED not in allowed:
            raise ServiceOSException("INVALID_JOB_STATUS_TRANSITION",
                f"Job is not awaiting a quote response. Current status: {job.status}", status_code=422)

        quote.status = "approved"; quote.approved_at = utcnow(); quote.approved_by_customer_id = customer_id
        from_status = job.status
        job.status = JS.QUOTE_APPROVED
        job.quote_approved_at = utcnow()
        job.status_updated_at = utcnow()
        job.current_status_started_at = utcnow()
        await self._write_history(job, from_status, JS.QUOTE_APPROVED, "Customer approved quote", None, None)
        await self._publish("job.quote_approved", str(job.tenant_id), str(job.id), {"quote_id": str(quote.id)})
        return self._job_quote_dict(quote)

    async def reject_job_quote(self, job_id: uuid.UUID, quote_id: uuid.UUID,
                                customer_id: uuid.UUID, reason: str | None = None) -> dict:
        if not reason or not reason.strip():
            raise ServiceOSException("QUOTE_REJECTION_REASON_REQUIRED",
                "A rejection reason is required.", status_code=422)
        job, quote = await self._get_quote_for_customer(job_id, quote_id, customer_id)
        if quote.status == "approved":
            raise ServiceOSException("QUOTE_ALREADY_APPROVED", "Quote already approved.", status_code=409)
        if quote.status == "rejected":
            raise ServiceOSException("QUOTE_ALREADY_REJECTED", "Quote already rejected.", status_code=409)
        if quote.status != "sent":
            raise ServiceOSException("QUOTE_APPROVAL_REQUIRED",
                "Quote must be sent before it can be rejected.", status_code=422)
        if quote.expires_at and utcnow() > quote.expires_at:
            quote.status = "expired"
            raise ServiceOSException("QUOTE_EXPIRED",
                "This quote has expired and can no longer be rejected.", status_code=409)

        allowed = _resolve_transitions(job.job_type, job.status)
        if JS.QUOTE_REJECTED not in allowed:
            raise ServiceOSException("INVALID_JOB_STATUS_TRANSITION",
                f"Job is not awaiting a quote response. Current status: {job.status}", status_code=422)

        quote.status = "rejected"; quote.rejected_at = utcnow(); quote.rejection_reason = reason
        from_status = job.status
        job.status = JS.QUOTE_REJECTED
        job.quote_rejected_at = utcnow()
        job.quote_rejection_reason = reason
        job.status_updated_at = utcnow()
        job.current_status_started_at = utcnow()
        await self._write_history(job, from_status, JS.QUOTE_REJECTED,
                                   reason or "Customer rejected quote", None, None)
        await self._publish("job.quote_rejected", str(job.tenant_id), str(job.id), {"quote_id": str(quote.id)})
        return self._job_quote_dict(quote)

    # ── Step 8: Customer-facing quote list/detail/approve/reject ─────────────
    def _quote_effective_status(self, q: JobQuote) -> str:
        """Read-only expiry check — doesn't mutate the row; approve/reject
        still persist the 'expired' transition the moment it's attempted."""
        if q.status == "sent" and q.expires_at and utcnow() > q.expires_at:
            return "expired"
        return q.status

    async def list_customer_quotes(self, customer_id: uuid.UUID, status: str | None = None,
                                    job_id: uuid.UUID | None = None, quote_type: str | None = None,
                                    created_from: str | None = None, created_to: str | None = None) -> dict:
        q = select(JobQuote, Job).join(Job, Job.id == JobQuote.job_id).where(
            JobQuote.customer_id == customer_id).order_by(JobQuote.created_at.desc())
        if job_id:     q = q.where(JobQuote.job_id == job_id)
        if quote_type: q = q.where(JobQuote.quote_type == quote_type)
        if created_from:
            try: q = q.where(JobQuote.created_at >= datetime.fromisoformat(created_from))
            except Exception: pass
        if created_to:
            try: q = q.where(JobQuote.created_at <= datetime.fromisoformat(created_to))
            except Exception: pass
        rows = (await self.db.execute(q)).all()
        quotes = []
        for quote, job in rows:
            eff_status = self._quote_effective_status(quote)
            if status and eff_status != status:
                continue
            quotes.append({
                "quote_id": str(quote.id), "quote_number": quote.quote_number,
                "job_id": str(job.id), "job_number": job.job_number,
                "service_name": job.service_type_id, "job_type": job.job_type,
                "status": eff_status,
                "findings": quote.findings_snapshot, "recommended_work": quote.recommended_work,
                "total_amount": float(quote.total_amount) if quote.total_amount is not None else None,
                "expires_at": quote.expires_at.isoformat() if quote.expires_at else None,
                "sent_at": quote.sent_at.isoformat() if quote.sent_at else None,
            })
        return {"quotes": quotes}

    async def get_customer_quote_detail(self, customer_id: uuid.UUID, quote_id: uuid.UUID) -> dict:
        qr = await self.db.execute(select(JobQuote).where(JobQuote.id == quote_id))
        quote = qr.scalar_one_or_none()
        if not quote or quote.customer_id != customer_id:
            raise ServiceOSException("QUOTE_NOT_FOUND", f"Quote '{quote_id}' not found.", status_code=404)
        jr = await self.db.execute(select(Job).where(Job.id == quote.job_id))
        job = jr.scalar_one_or_none()
        if not job:
            raise ServiceOSException("JOB_NOT_FOUND", f"Job '{quote.job_id}' not found.", status_code=404)

        tenant_info = None
        try:
            from app.engines.tenant_engine.models import Tenant
            tr = await self.db.execute(select(Tenant).where(Tenant.id == job.tenant_id))
            tenant = tr.scalar_one_or_none()
            if tenant:
                tenant_info = {"tenant_id": str(tenant.id), "name": tenant.tenant_name,
                                "phone": getattr(tenant, "owner_phone", None), "rating": None}
        except Exception:
            pass

        staff_info = None
        if job.assigned_staff_id:
            from app.engines.auth.models import User
            sr = await self.db.execute(select(User).where(User.id == job.assigned_staff_id))
            staff = sr.scalar_one_or_none()
            if staff:
                staff_info = {"staff_id": str(staff.id), "name": staff.full_name}

        eff_status = self._quote_effective_status(quote)
        return {
            "quote_id": str(quote.id), "quote_number": quote.quote_number,
            "job_id": str(job.id), "job_number": job.job_number, "booking_id": job.booking_id,
            "service_name": job.service_type_id, "job_type": job.job_type,
            "tenant": tenant_info, "staff": staff_info,
            "assessment": {
                "findings": quote.findings_snapshot or job.assessment_findings,
                "recommended_work": quote.recommended_work or job.recommended_work,
                "estimated_parts": job.estimated_parts,
            },
            "price_breakdown": {
                "labour_amount": float(quote.labour_amount), "parts_amount": float(quote.parts_amount),
                "visit_fee": float(quote.visit_fee), "discount_amount": float(quote.discount_amount),
                "tax_amount": float(quote.tax_amount),
                "total_amount": float(quote.total_amount) if quote.total_amount is not None else None,
            },
            "status": eff_status,
            "can_approve": eff_status == "sent",
            "can_reject": eff_status == "sent",
            "expires_at": quote.expires_at.isoformat() if quote.expires_at else None,
            "message": ("This quote has expired." if eff_status == "expired"
                        else "Please approve this quote to continue the job." if eff_status == "sent"
                        else None),
        }

    async def approve_customer_quote(self, quote_id: uuid.UUID, customer_id: uuid.UUID,
                                      customer_note: str | None = None) -> dict:
        qr = await self.db.execute(select(JobQuote).where(JobQuote.id == quote_id))
        quote = qr.scalar_one_or_none()
        if not quote or quote.customer_id != customer_id:
            raise ServiceOSException("QUOTE_NOT_FOUND", f"Quote '{quote_id}' not found.", status_code=404)
        await self.approve_job_quote(quote.job_id, quote_id, customer_id)
        jr = await self.db.execute(select(Job).where(Job.id == quote.job_id))
        job = jr.scalar_one_or_none()
        return {"quote_id": str(quote_id), "quote_status": "approved", "job_id": str(quote.job_id),
                "job_status": job.status if job else JS.QUOTE_APPROVED,
                "valid_next_statuses": self._business_filtered_transitions(job) if job else [],
                "message": "Quote approved successfully"}

    async def reject_customer_quote(self, quote_id: uuid.UUID, customer_id: uuid.UUID,
                                     reason: str | None = None) -> dict:
        qr = await self.db.execute(select(JobQuote).where(JobQuote.id == quote_id))
        quote = qr.scalar_one_or_none()
        if not quote or quote.customer_id != customer_id:
            raise ServiceOSException("QUOTE_NOT_FOUND", f"Quote '{quote_id}' not found.", status_code=404)
        await self.reject_job_quote(quote.job_id, quote_id, customer_id, reason)
        jr = await self.db.execute(select(Job).where(Job.id == quote.job_id))
        job = jr.scalar_one_or_none()
        return {"quote_id": str(quote_id), "quote_status": "rejected", "job_id": str(quote.job_id),
                "job_status": job.status if job else JS.QUOTE_REJECTED,
                "message": "Quote rejected successfully"}

    # ── Step 7: Consultation -> Repair conversion ──────────────────────────────
    async def convert_to_repair(self, job_id: uuid.UUID, repair_service_id: str | None = None,
                                 scheduled_at: str | None = None, assignment_mode: str = "manual",
                                 assigned_staff_id: uuid.UUID | str | None = None,
                                 notes: str | None = None) -> dict:
        job = await self._get_job_for_assignment(job_id)
        if job.job_type != JobType.CONSULTATION:
            raise ServiceOSException("CONSULTATION_CONVERSION_NOT_ALLOWED",
                "Only consultation jobs can be converted to repair.", status_code=422,
                context={"job_type": job.job_type})
        if job.status == JS.CONVERTED_TO_REPAIR:
            raise ServiceOSException("CONSULTATION_ALREADY_CONVERTED",
                "This consultation has already been converted to a repair job.", status_code=409)
        if job.status != JS.QUOTE_APPROVED:
            raise ServiceOSException("CONSULTATION_CONVERSION_NOT_ALLOWED",
                f"Consultation must be in 'quote_approved' status. Current: {job.status}", status_code=422)

        er = await self.db.execute(select(Job).where(
            Job.parent_job_id == job.id, Job.job_type == JobType.REPAIR))
        if er.scalar_one_or_none():
            raise ServiceOSException("CONSULTATION_ALREADY_CONVERTED",
                "A repair job already exists for this consultation.", status_code=409)

        staff_uuid = None
        if assigned_staff_id:
            staff_uuid = (assigned_staff_id if isinstance(assigned_staff_id, uuid.UUID)
                          else uuid.UUID(str(assigned_staff_id)))

        repair_job = Job(
            tenant_id=job.tenant_id, job_number=self._generate_job_number(),
            title=f"Repair: {job.title}", description=job.description,
            service_type_id=repair_service_id or job.service_type_id,
            service_category=job.service_category, job_type=JobType.REPAIR,
            parent_job_id=job.id, customer_id=job.customer_id,
            address=job.address, pincode=job.pincode, city=job.city, zipcode=job.zipcode,
            address_id=job.address_id, service_id=job.service_id,
            matched_service_area_id=job.matched_service_area_id,
            matched_service_area_service_id=job.matched_service_area_service_id,
            coverage_match_level=job.coverage_match_level,
            assessment_findings=job.assessment_findings, recommended_work=job.recommended_work,
            estimated_parts=job.estimated_parts,
            findings=job.assessment_findings or job.findings,
            recommendation=job.recommended_work or job.recommendation,
            scheduled_at=datetime.fromisoformat(scheduled_at) if scheduled_at else None,
            converted_from_consultation=True,
            status=JS.PENDING_ASSIGNMENT,
        )
        if staff_uuid:
            repair_job.assigned_staff_id = staff_uuid
            repair_job.status = JS.ASSIGNED
            repair_job.assigned_at = utcnow()
            repair_job.assigned_by_user_id = self.actor_id
        self.db.add(repair_job)
        await self.db.flush()
        await self._write_history(repair_job, None, repair_job.status,
                                   notes or "Created from consultation conversion", None, None)

        from_status = job.status
        job.status = JS.CONVERTED_TO_REPAIR
        job.status_updated_at = utcnow()
        job.current_status_started_at = utcnow()
        await self._write_history(job, from_status, JS.CONVERTED_TO_REPAIR,
                                   notes or "Converted to repair job", None, None)
        await self._publish("job.converted_to_repair", str(job.tenant_id), str(job.id),
                            {"repair_job_id": str(repair_job.id)})
        return {
            "consultation_job_id": str(job.id),
            "repair_job_id": str(repair_job.id),
            "repair_job_status": repair_job.status,
            "parent_job_id": str(job.id),
            "message": "Consultation converted to repair job successfully",
        }

    # ── Step 7: Service checklist foundation (reuses Job.checklist JSONB —
    # see TODO below for the normalized service_checklist_* tables) ───────────
    # TODO(Step 8+): promote to service_checklist_templates/items + job_checklist_items
    # if per-tenant reusable templates are needed; current foundation is
    # functionally complete for "service job requires checklist" gating.
    async def get_job_checklist(self, job_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job: raise ServiceOSException("JOB_NOT_FOUND", f"Job '{job_id}' not found.", status_code=404)
        self._assert_can_access_job(job)
        return {"job_id": str(job_id), "checklist_required": job.checklist_required,
                "checklist_started_at": job.checklist_started_at.isoformat() if job.checklist_started_at else None,
                "checklist_completed_at": job.checklist_completed_at.isoformat() if job.checklist_completed_at else None,
                "items": job.checklist}

    async def start_checklist(self, job_id: uuid.UUID) -> dict:
        job = await self._get_job_for_staff_action(job_id)
        if job.job_type != JobType.SERVICE:
            raise ServiceOSException("INVALID_JOB_TYPE",
                "Checklist is only used for service jobs.", status_code=422,
                context={"job_type": job.job_type})
        allowed = _resolve_transitions(job.job_type, job.status)
        if JS.CHECKLIST_STARTED not in allowed:
            raise ServiceOSException("INVALID_JOB_STATUS_TRANSITION",
                f"Checklist cannot be started from status '{job.status}'.", status_code=422,
                context={"current_status": job.status})
        from_status = job.status
        job.status = JS.CHECKLIST_STARTED
        job.checklist_started_at = utcnow()
        job.status_updated_at = utcnow()
        job.current_status_started_at = utcnow()
        await self._write_history(job, from_status, JS.CHECKLIST_STARTED, "Checklist started", None, None)
        return self._job_dict(job)

    async def complete_checklist(self, job_id: uuid.UUID) -> dict:
        job = await self._get_job_for_staff_action(job_id)
        if job.status != JS.CHECKLIST_STARTED:
            raise ServiceOSException("INVALID_JOB_STATUS_TRANSITION",
                f"Checklist must be started before completing. Current status: {job.status}",
                status_code=422, context={"current_status": job.status})
        if job.checklist and not all(item.get("completed") for item in job.checklist
                                       if item.get("is_required", True)):
            raise ServiceOSException("CHECKLIST_NOT_COMPLETE",
                "All required checklist items must be completed.", status_code=422,
                context={"incomplete": [i.get("step") for i in job.checklist
                                        if i.get("is_required", True) and not i.get("completed")]})
        from_status = job.status
        job.status = JS.CHECKLIST_COMPLETE
        job.checklist_completed_at = utcnow()
        job.status_updated_at = utcnow()
        job.current_status_started_at = utcnow()
        await self._write_history(job, from_status, JS.CHECKLIST_COMPLETE, "Checklist completed", None, None)
        return self._job_dict(job)

    # ── Step 8: Normalized job checklist execution (job_checklist_items) ─────
    def _job_checklist_item_dict(self, i: JobChecklistItem) -> dict:
        return {
            "item_id": str(i.id), "title": i.title, "description": i.description,
            "sort_order": i.sort_order, "is_required": i.is_required,
            "requires_photo": i.requires_photo, "requires_note": i.requires_note,
            "is_completed": i.is_completed,
            "completed_by_staff_id": str(i.completed_by_staff_id) if i.completed_by_staff_id else None,
            "completed_at": i.completed_at.isoformat() if i.completed_at else None,
            "notes": i.notes, "photo_urls": i.photo_urls,
        }

    async def _provision_job_checklist_items(self, job: Job) -> list[JobChecklistItem]:
        """Best-effort lazy provisioning from the tenant's active template for
        this service — called on checklist start. Proceeds with an empty
        checklist if no template exists rather than blocking the staff."""
        from app.engines.field_ops.models import ServiceChecklistTemplate, ServiceChecklistItem
        tr = await self.db.execute(select(ServiceChecklistTemplate).where(
            ServiceChecklistTemplate.tenant_id == job.tenant_id,
            ServiceChecklistTemplate.service_id == job.service_id,
            ServiceChecklistTemplate.is_active.is_(True),
            ServiceChecklistTemplate.deleted_at.is_(None)))
        template = tr.scalar_one_or_none()
        if not template:
            return []
        ir = await self.db.execute(select(ServiceChecklistItem).where(
            ServiceChecklistItem.template_id == template.id,
            ServiceChecklistItem.is_active.is_(True),
            ServiceChecklistItem.deleted_at.is_(None)).order_by(ServiceChecklistItem.sort_order))
        template_items = ir.scalars().all()
        created = []
        for ti in template_items:
            jci = JobChecklistItem(
                job_id=job.id, tenant_id=job.tenant_id, template_item_id=ti.id,
                title=ti.title, description=ti.description, sort_order=ti.sort_order,
                is_required=ti.is_required, requires_photo=ti.requires_photo,
                requires_note=ti.requires_note,
            )
            self.db.add(jci)
            created.append(jci)
        if created:
            job.checklist_required = True
        return created

    async def get_job_checklist_items(self, job_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job: raise ServiceOSException("JOB_NOT_FOUND", f"Job '{job_id}' not found.", status_code=404)
        self._assert_can_access_job(job)
        ir = await self.db.execute(select(JobChecklistItem).where(
            JobChecklistItem.job_id == job_id).order_by(JobChecklistItem.sort_order))
        items = ir.scalars().all()
        required = [i for i in items if i.is_required]
        completed = [i for i in items if i.is_completed]
        completed_required = [i for i in required if i.is_completed]
        checklist_status = ("not_started" if job.status not in (JS.CHECKLIST_STARTED, JS.CHECKLIST_COMPLETE)
                             else "in_progress" if job.status == JS.CHECKLIST_STARTED else "complete")
        return {
            "job_id": str(job_id), "job_type": job.job_type,
            "checklist_required": job.checklist_required, "checklist_status": checklist_status,
            "total_items": len(items), "completed_items": len(completed),
            "required_items": len(required), "completed_required_items": len(completed_required),
            "can_complete_checklist": len(completed_required) == len(required),
            "items": [self._job_checklist_item_dict(i) for i in items],
        }

    async def start_job_checklist(self, job_id: uuid.UUID) -> dict:
        job = await self._get_job_for_staff_action(job_id)
        if job.job_type != JobType.SERVICE and job.checklist_required is not True:
            raise ServiceOSException("CHECKLIST_NOT_ALLOWED_FOR_JOB_TYPE",
                "Checklist is only used for service jobs.", status_code=422,
                context={"job_type": job.job_type})
        allowed = _resolve_transitions(job.job_type, job.status)
        if JS.CHECKLIST_STARTED not in allowed:
            raise ServiceOSException("INVALID_JOB_STATUS_TRANSITION",
                f"Checklist cannot be started from status '{job.status}'.", status_code=422,
                context={"current_status": job.status})

        existing = await self.db.execute(select(JobChecklistItem).where(JobChecklistItem.job_id == job.id))
        if not existing.scalars().first():
            await self._provision_job_checklist_items(job)

        from_status = job.status
        job.status = JS.CHECKLIST_STARTED
        job.checklist_started_at = utcnow()
        job.status_updated_at = utcnow()
        job.current_status_started_at = utcnow()
        await self._write_history(job, from_status, JS.CHECKLIST_STARTED, "Checklist started", None, None)
        return await self.get_job_checklist_items(job.id)

    async def update_job_checklist_item(self, job_id: uuid.UUID, item_id: uuid.UUID,
                                         is_completed: bool, notes: str | None = None,
                                         photo_urls: list[str] | None = None) -> dict:
        job = await self._get_job_for_staff_action(job_id)
        ir = await self.db.execute(select(JobChecklistItem).where(JobChecklistItem.id == item_id))
        item = ir.scalar_one_or_none()
        if not item or item.job_id != job.id:
            raise ServiceOSException("CHECKLIST_ITEM_NOT_FOUND",
                f"Checklist item '{item_id}' not found.", status_code=404)
        # Slice 2F-14: this method previously had NO status guard at all --
        # a technician could mutate an item after complete_job_checklist had
        # already moved the job to CHECKLIST_COMPLETE (or the job had moved
        # further, e.g. WORK_COMPLETE), silently un-doing a required item on
        # an already-finalized checklist with no re-validation of the
        # completion gate. Item mutation is only meaningful while the
        # checklist is actively being worked (CHECKLIST_STARTED) --
        # complete_job_checklist itself requires this same status before it
        # will finalize, so this mirrors the existing, established gate
        # rather than inventing a new one.
        if job.status != JS.CHECKLIST_STARTED:
            raise ServiceOSException("CHECKLIST_NOT_ACTIVE",
                f"Checklist items can only be changed while the checklist is "
                f"in progress. Current job status: {job.status}", status_code=422,
                context={"current_status": job.status})
        if is_completed:
            if item.requires_note and not (notes or "").strip():
                raise ServiceOSException("CHECKLIST_ITEM_NOTE_REQUIRED",
                    "This checklist item requires a note.", status_code=422)
            if item.requires_photo and not (photo_urls or []):
                raise ServiceOSException("CHECKLIST_ITEM_PHOTO_REQUIRED",
                    "This checklist item requires at least one photo.", status_code=422)
            item.is_completed = True
            item.completed_by_staff_id = self.actor_id
            item.completed_at = utcnow()
        else:
            item.is_completed = False
            item.completed_by_staff_id = None
            item.completed_at = None
        if notes is not None:
            item.notes = notes
        if photo_urls is not None:
            item.photo_urls = photo_urls
        return self._job_checklist_item_dict(item)

    async def complete_job_checklist(self, job_id: uuid.UUID) -> dict:
        job = await self._get_job_for_staff_action(job_id)
        if job.status != JS.CHECKLIST_STARTED:
            raise ServiceOSException("INVALID_JOB_STATUS_TRANSITION",
                f"Checklist must be started before completing. Current status: {job.status}",
                status_code=422, context={"current_status": job.status})
        ir = await self.db.execute(select(JobChecklistItem).where(JobChecklistItem.job_id == job.id))
        items = ir.scalars().all()
        incomplete_required = [i for i in items if i.is_required and not i.is_completed]
        if incomplete_required:
            raise ServiceOSException("CHECKLIST_NOT_COMPLETE",
                "All required checklist items must be completed.", status_code=422,
                context={"incomplete": [i.title for i in incomplete_required]})
        from_status = job.status
        job.status = JS.CHECKLIST_COMPLETE
        job.checklist_completed_at = utcnow()
        job.status_updated_at = utcnow()
        job.current_status_started_at = utcnow()
        await self._write_history(job, from_status, JS.CHECKLIST_COMPLETE, "Checklist completed", None, None)
        return await self.get_job_checklist_items(job.id)

    async def get_customer_checklist_summary(self, job_id: uuid.UUID, customer_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job or job.customer_id != customer_id:
            raise ServiceOSException("JOB_NOT_FOUND", f"Job '{job_id}' not found.", status_code=404)
        ir = await self.db.execute(select(JobChecklistItem).where(
            JobChecklistItem.job_id == job_id).order_by(JobChecklistItem.sort_order))
        items = ir.scalars().all()
        required = [i for i in items if i.is_required]
        completed_required = [i for i in required if i.is_completed]
        return {
            "job_id": str(job_id), "checklist_required": job.checklist_required,
            "checklist_completed_at": job.checklist_completed_at.isoformat() if job.checklist_completed_at else None,
            "completed_required_items": len(completed_required), "required_items": len(required),
            "items": [{"title": i.title, "is_completed": i.is_completed,
                       "notes": i.notes, "photo_urls": i.photo_urls,
                       "completed_at": i.completed_at.isoformat() if i.completed_at else None}
                      for i in items],
        }

    def _quote_dict(self, q: JobQuote) -> dict:
        return {
            "quote_id": str(q.id), "job_id": str(q.job_id), "tenant_id": str(q.tenant_id),
            "customer_id": str(q.customer_id) if q.customer_id else None,
            "amount": float(q.amount), "parts": q.parts,
            "labour_estimate": float(q.labour_estimate) if q.labour_estimate is not None else None,
            "findings": q.findings_snapshot, "recommendation": q.recommendation_snapshot,
            "notes": q.notes, "status": q.status,
            "expires_at": q.expires_at.isoformat() if q.expires_at else None,
            "is_expired": bool(q.expires_at and q.status == "pending" and utcnow() > q.expires_at),
            "responded_at": q.responded_at.isoformat() if q.responded_at else None,
            "created_at": q.created_at.isoformat(),
        }

    async def create_quote(self, job_id: uuid.UUID, amount: Decimal,
                            parts: list[dict], labour_estimate: Decimal | None,
                            notes: str | None, expiry_days: int = 7) -> dict:
        """Staff/tenant sends a price quote after assessment. Repair: optional
        ('quote if needed'). Consultation: this IS the deliverable."""
        # Slice 2F-14B: previously loaded the job with NO ownership check at
        # all -- any authenticated user could create a price quote on any
        # job in any tenant. Reuses the same helper already used by
        # create_job_quote/send_job_quote for the identical JobQuote model.
        job = await self._get_job_for_quote_management(job_id)

        allowed = _resolve_transitions(job.job_type, job.status)
        if JS.QUOTE_PENDING not in allowed:
            raise ServiceOSException("INVALID_TRANSITION",
                f"Cannot send a quote from status '{job.status}' for job_type '{job.job_type}'.",
                context={"allowed_transitions": allowed})

        quote = JobQuote(
            job_id=job.id, tenant_id=job.tenant_id, customer_id=job.customer_id,
            amount=amount, parts=parts, labour_estimate=labour_estimate, notes=notes,
            findings_snapshot=job.findings, recommendation_snapshot=job.recommendation,
            created_by=self.actor_id, expires_at=utcnow() + timedelta(days=expiry_days),
        )
        self.db.add(quote)
        await self._write_history(job, job.status, JS.QUOTE_PENDING, "Quote sent", None, None)
        job.status = JS.QUOTE_PENDING
        await self.db.flush()
        await self._publish("job.quote_sent", str(job.tenant_id), str(job.id),
                            {"quote_id": str(quote.id), "amount": float(amount)})
        return {**self._quote_dict(quote), **self._job_dict(job)}

    async def list_quotes_by_job(self, job_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(JobQuote).where(JobQuote.job_id == job_id)
                                   .order_by(JobQuote.created_at.desc()))
        quotes = r.scalars().all()
        return {"job_id": str(job_id), "quotes": [self._quote_dict(q) for q in quotes]}

    async def respond_to_quote(self, quote_id: uuid.UUID, customer_id: uuid.UUID,
                                approved: bool) -> dict:
        """Only the job's own customer may approve/reject — same 404-not-403
        ownership pattern used for bookings/reviews."""
        r = await self.db.execute(select(JobQuote).where(JobQuote.id == quote_id))
        quote = r.scalar_one_or_none()
        if not quote: raise NotFoundException("JobQuote", str(quote_id))
        if quote.customer_id != customer_id:
            raise NotFoundException("JobQuote", str(quote_id))
        if quote.status != "pending":
            raise ServiceOSException("CONFLICT", f"Quote already {quote.status}.")
        if quote.expires_at and utcnow() > quote.expires_at:
            quote.status = "expired"
            raise ServiceOSException("QUOTE_EXPIRED",
                "This quote has expired and can no longer be approved or rejected.",
                resolution="Ask the business to send a new quote.")

        jr = await self.db.execute(select(Job).where(Job.id == quote.job_id))
        job = jr.scalar_one_or_none()
        if not job: raise NotFoundException("Job", str(quote.job_id))

        quote.status = "approved" if approved else "rejected"
        quote.responded_at = utcnow()

        to_status = JS.QUOTE_APPROVED if approved else JS.QUOTE_REJECTED
        allowed = _resolve_transitions(job.job_type, job.status)
        if to_status not in allowed:
            raise ServiceOSException("INVALID_TRANSITION",
                f"Job is not awaiting a quote response. Current status: {job.status}")
        await self._write_history(job, job.status, to_status,
                                   f"Customer {'approved' if approved else 'rejected'} quote",
                                   None, None)
        job.status = to_status

        spawned_job = None
        if approved and job.job_type == JobType.CONSULTATION:
            spawned_job = await self._spawn_repair_from_consultation(job, quote)

        await self._publish("job.quote_responded", str(job.tenant_id), str(job.id),
                            {"quote_id": str(quote.id), "approved": approved})
        result = {"approved": approved, **self._quote_dict(quote), **self._job_dict(job)}
        if spawned_job:
            result["spawned_job"] = spawned_job
        return result

    async def spawn_repair_from_consultation(self, consultation_job_id: uuid.UUID) -> dict:
        """Staff-triggered manual spawn of a repair from a consultation job.
        Automatically uses the most recent approved quote price if one exists."""
        # Slice 2F-14B: previously loaded the job with NO ownership check at
        # all -- any tenant_owner holding TENANT_UPDATE could spawn a repair
        # from a DIFFERENT tenant's consultation. Reuses the same
        # tenant_owner-own-tenant/super_admin helper already used by
        # convert_to_repair. Also previously had no duplicate-repair guard
        # (unlike convert_to_repair, which checks for an existing repair job
        # on the same parent) -- repeated calls could create unlimited
        # duplicate repair jobs. Both fixed here, mirroring convert_to_repair's
        # existing pattern exactly rather than inventing a new one.
        job = await self._get_job_for_assignment(consultation_job_id)
        if job.job_type != JobType.CONSULTATION:
            raise ServiceOSException("INVALID_JOB_TYPE",
                "Only consultation jobs can spawn repair jobs.",
                context={"job_type": job.job_type, "job_id": str(consultation_job_id)})
        er = await self.db.execute(select(Job).where(
            Job.parent_job_id == job.id, Job.job_type == JobType.REPAIR))
        if er.scalar_one_or_none():
            raise ServiceOSException("CONSULTATION_ALREADY_CONVERTED",
                "A repair job already exists for this consultation.", status_code=409)
        qr = await self.db.execute(
            select(JobQuote).where(JobQuote.job_id == consultation_job_id,
                                   JobQuote.status == "approved")
            .order_by(JobQuote.created_at.desc()).limit(1))
        quote = qr.scalar_one_or_none()
        return await self._spawn_repair_from_consultation(job, quote)

    async def _spawn_repair_from_consultation(self, consultation_job: Job, quote: JobQuote | None) -> dict:
        """Approving a consultation's quote creates a brand-new repair job that
        inherits the consultation's findings, recommendation, and quoted price.
        The consultation job itself is untouched here — it still bills its own
        consult fee via the normal sign-off → invoice → close pipeline."""
        new_job = await self.create_job(consultation_job.tenant_id, {
            "title": f"Repair: {consultation_job.title}",
            "service_type_id": consultation_job.service_type_id,
            "service_category": consultation_job.service_category,
            "job_type": JobType.REPAIR,
            "parent_job_id": str(consultation_job.id),
            "findings": consultation_job.findings,
            "recommendation": consultation_job.recommendation,
            "customer_id": str(consultation_job.customer_id) if consultation_job.customer_id else None,
            "address": consultation_job.address, "pincode": consultation_job.pincode,
            "quoted_price": str(quote.amount) if quote else None,
        })
        logger.info("fieldops.repair_spawned_from_consultation",
                    consultation_job_id=str(consultation_job.id), repair_job_id=new_job["job_id"])
        return new_job

    async def get_allowed_transitions(self, job_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job: raise NotFoundException("Job", str(job_id))
        allowed = _resolve_transitions(job.job_type, job.status)
        return {"job_id": str(job_id), "current_status": job.status,
                "allowed_transitions": allowed,
                "is_terminal": job.status in TERMINAL_STATUSES,
                "transition_descriptions": {t: f"Move job from {job.status} → {t}" for t in allowed}}

    # ── Atomic Close Pipeline ─────────────────────────────────────────────────
    async def close_job(self, job_id: uuid.UUID, final_price: Decimal) -> dict:
        """
        ATOMIC PIPELINE: invoice_generated → closed
        1. Validate transition
        2. Deduct commission from Platform Commerce
        3. Confirm credit reservation
        4. Update staff performance signal
        5. Mark job closed
        6. Publish events
        All in one transaction — if commission fails, job stays at invoice_generated.
        """
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job: raise NotFoundException("Job", str(job_id))

        if job.status != JS.INVOICE_GENERATED:
            raise ServiceOSException("INVALID_TRANSITION",
                f"Job must be in invoice_generated to close. Current: {job.status}",
                context={"allowed_transitions": _resolve_transitions(job.job_type, job.status)})

        if job.commission_deducted:
            raise ServiceOSException("CONFLICT", "Commission already deducted for this job.")

        # Step 1: Deduct commission (most critical — if this fails, nothing else proceeds)
        commission_amount = Decimal("0.00")
        try:
            from app.engines.platform_commerce.service import CommerceService
            commerce = CommerceService(self.db, actor_id=self.actor_id)
            result = await commerce.deduct_commission(
                tenant_id=job.tenant_id, job_id=str(job_id),
                job_value=final_price or job.quoted_price or Decimal("0"),
                description=f"Commission: {job.job_number}")
            commission_amount = Decimal(str(result.get("commission_amount", 0)))
        except ServiceOSException as e:
            if "COMMISSION_WALLET_EMPTY" in str(e.error_code):
                raise ServiceOSException("COMMISSION_WALLET_EMPTY",
                    "Tenant wallet has insufficient credits to close this job.",
                    resolution="Tenant must purchase credits before closing.",
                    context={"job_id": str(job_id)})
            raise

        # Step 2: Update job state
        job.status = JS.CLOSED
        job.final_price = final_price
        job.closed_at = utcnow()
        job.commission_deducted = True
        job.commission_amount = commission_amount
        try:
            from app.core.usage_quota import adjust_usage
            await adjust_usage(self.db, job.tenant_id, "current_active_jobs", -1)
        except Exception as e:
            logger.warning("fieldops.job_usage_decrement_failed", error=str(e))

        # Step 3: Confirm credit reservation if exists
        if job.booking_id:
            try:
                from app.engines.platform_commerce.service import CommerceService
                commerce = CommerceService(self.db, actor_id=self.actor_id)
                await commerce.confirm_reservation(str(job.booking_id), job.tenant_id)
            except Exception as e:
                logger.warning("fieldops.reservation_confirm_failed", error=str(e))

        # Step 4: Update staff performance signal
        if job.assigned_staff_id:
            try:
                from app.engines.data_science.service import DSService
                ds = DSService(self.db, actor_id=self.actor_id)
                await ds.update_staff_signal(job.assigned_staff_id, job.tenant_id,
                                              "job_completion_rate", 95.0)
                # Update active job count in Geo
                from app.engines.geo.models import StaffLocation
                loc_r = await self.db.execute(select(StaffLocation).where(
                    StaffLocation.staff_id == job.assigned_staff_id,
                    StaffLocation.tenant_id == job.tenant_id))
                loc = loc_r.scalar_one_or_none()
                if loc:
                    loc.active_job_count = max(0, loc.active_job_count - 1)
            except Exception as e:
                logger.warning("fieldops.staff_signal_failed", error=str(e))

        await self._write_history(job, JS.INVOICE_GENERATED, JS.CLOSED,
                                   f"Closed — commission ₹{commission_amount} deducted", None, None)
        await self._publish("job.closed", str(job.tenant_id), str(job_id),
                            {"job_number": job.job_number, "final_price": float(final_price),
                             "commission": float(commission_amount)})

        # Auto-create review request for customer
        if job.customer_id:
            try:
                from app.engines.review.service import ReviewService
                # Slice 2F-25A: pass the Job's own tenant as the service's actor
                # tenant and mark this a trusted internal caller. Slice 2F-25
                # added tenant pinning to `create_review_request`, and this
                # call site supplied no tenant context at all -- so every job
                # close silently failed to create its review request
                # (TENANT_ACCESS_DENIED, swallowed by the except below). The
                # Job row is the authoritative source of both tenant and
                # customer, which is exactly what the pinning wants.
                await ReviewService(self.db, actor_id=self.actor_id,
                                    actor_role="system",
                                    actor_tenant_id=job.tenant_id).create_review_request(
                    job.job_number, job.tenant_id, job.customer_id, job.assigned_staff_id,
                    trusted_internal=True)
            except Exception as e:
                logger.warning("fieldops.review_request_failed", error=str(e))

        logger.info("fieldops.job_closed", job_id=str(job_id),
                    commission=float(commission_amount))
        return {**self._job_dict(job), "commission_amount": float(commission_amount)}

    # ── Job Timeline (1 method) ───────────────────────────────────────────────
    async def get_job_timeline(self, job_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(JobStatusHistory).where(
            JobStatusHistory.job_id == job_id).order_by(JobStatusHistory.created_at))
        history = r.scalars().all()
        return {"job_id": str(job_id),
                "timeline": [{"from_status": h.from_status, "to_status": h.to_status,
                               "changed_by_role": h.changed_by_role, "reason": h.reason,
                               "occurred_at": h.created_at.isoformat()} for h in history]}

    # ── Notes (2 methods) ─────────────────────────────────────────────────────
    async def add_note(self, job_id: uuid.UUID,
                        content: str, note_type: str, is_internal: bool) -> dict:
        # Slice 2F-14A: tenant_id was previously a client-supplied query param,
        # trusted as-is with no job/tenant ownership check at all -- any
        # authenticated user could write a note onto any job under any tenant_id
        # they chose. tenant_id is now always derived from the job row itself,
        # and the same object-ownership check used for job reads (tenant_owner
        # own-tenant, assigned staff/technician, customer own-job) is enforced
        # before writing. Notes are a staff/tenant-facing capability -- a
        # customer has no documented "add a note to my own job" capability
        # anywhere in this engine, so customers are explicitly denied here
        # rather than silently allowed through the same access check that
        # otherwise permits customer reads.
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job: raise NotFoundException("Job", str(job_id))
        self._assert_can_access_job(job)
        if self.actor_role == "customer":
            raise ServiceOSException("NOTE_ACCESS_DENIED",
                "Customers cannot add notes to a job.", status_code=403)
        note = JobNote(job_id=job_id, tenant_id=job.tenant_id, author_id=self.actor_id,
            author_role=self.actor_role, content=content, note_type=note_type,
            status_at=job.status, is_internal=is_internal)
        self.db.add(note); await self.db.flush()
        return {"note_id": str(note.id), "content": content, "note_type": note_type,
                "is_internal": is_internal, "created_at": note.created_at.isoformat()}

    async def list_notes(self, job_id: uuid.UUID) -> dict:
        # Slice 2F-14A: previously read every note for any job_id with zero
        # tenant/assignment/customer ownership check and no is_internal
        # filtering -- any authenticated user (including an unrelated customer
        # or a staff member from a different tenant) could read every
        # provider-internal note on any job. Now enforces the same
        # object-ownership check as job reads, and hides is_internal=True
        # notes from customers (the only persona this engine ever intends
        # provider-internal notes to be hidden from).
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job: raise NotFoundException("Job", str(job_id))
        self._assert_can_access_job(job)
        r2 = await self.db.execute(select(JobNote).where(JobNote.job_id == job_id)
            .order_by(JobNote.created_at))
        notes = r2.scalars().all()
        if self.actor_role == "customer":
            notes = [n for n in notes if not n.is_internal]
        return {"job_id": str(job_id), "notes": [
            {"note_id": str(n.id), "content": n.content, "note_type": n.note_type,
             "author_role": n.author_role, "status_at": n.status_at,
             "is_internal": n.is_internal, "created_at": n.created_at.isoformat()}
            for n in notes]}

    # ── Media (2 methods) ─────────────────────────────────────────────────────
    async def add_media(self, job_id: uuid.UUID,
                         media_id: uuid.UUID | None, media_type: str,
                         caption: str | None, storage_key: str | None) -> dict:
        # Slice 2F-14A: same class of defect as add_note -- tenant_id was a
        # client-supplied query param with no job/tenant ownership check.
        # tenant_id is now always derived from the job row; the same
        # object-ownership check used for job reads is enforced before
        # attaching media, and customers are denied (no documented
        # "customer attaches media to their own job" capability exists here;
        # this does not build new upload/signature infrastructure -- it only
        # closes the ownership gap on the existing storage_key-reference field).
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job: raise NotFoundException("Job", str(job_id))
        self._assert_can_access_job(job)
        if self.actor_role == "customer":
            raise ServiceOSException("MEDIA_ACCESS_DENIED",
                "Customers cannot attach media to a job.", status_code=403)
        m = JobMedia(job_id=job_id, tenant_id=job.tenant_id, media_id=media_id,
            uploaded_by=self.actor_id, status_at=job.status,
            media_type=media_type, caption=caption, storage_key=storage_key)
        self.db.add(m); await self.db.flush()
        return {"media_id": str(m.id), "job_id": str(job_id), "media_type": media_type,
                "status_at": job.status, "created_at": m.created_at.isoformat()}

    async def list_media(self, job_id: uuid.UUID) -> dict:
        # Slice 2F-14A: previously read every media row for any job_id with
        # zero ownership check at all. Now enforces the same job-access check
        # as list_notes. NOTE: JobMedia has no is_internal-equivalent column
        # (unlike JobNote), so there is no existing internal/customer-visible
        # split to enforce at the row level -- any actor who can access the
        # job at all sees all of its media. This is documented as a product
        # decision (see product-decisions-required.md), not silently assumed;
        # no new column/migration was added to invent that distinction.
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job: raise NotFoundException("Job", str(job_id))
        self._assert_can_access_job(job)
        r2 = await self.db.execute(select(JobMedia).where(JobMedia.job_id == job_id)
            .order_by(JobMedia.created_at))
        items = r2.scalars().all()
        return {"job_id": str(job_id), "media": [
            {"media_id": str(m.id), "media_type": m.media_type, "caption": m.caption,
             "status_at": m.status_at, "storage_key": m.storage_key,
             "created_at": m.created_at.isoformat()} for m in items]}

    # ── Customer public tracking ──────────────────────────────────────────────
    async def get_job_by_token(self, token: str) -> dict:
        try:
            job_id = await self.redis.get(REDIS_JOB_TOKEN.format(token=token))
            if not job_id: raise NotFoundException("Job", "token")
            job_uuid = uuid.UUID(job_id.decode() if isinstance(job_id, bytes) else job_id)
        except NotFoundException:
            raise
        except Exception:
            raise NotFoundException("Job", "token")
        r = await self.db.execute(select(Job).where(Job.id == job_uuid))
        job = r.scalar_one_or_none()
        if not job: raise NotFoundException("Job", "token")
        return {
            "job_number": job.job_number, "status": job.status,
            "title": job.title, "scheduled_at": job.scheduled_at.isoformat() if job.scheduled_at else None,
            "staff_assigned": job.assigned_staff_id is not None,
            "allowed_transitions": [],  # never exposed to customers
        }

    # ── SLA & Counts (3 methods) ──────────────────────────────────────────────
    async def get_sla_status(self, job_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(Job).where(Job.id == job_id))
        job = r.scalar_one_or_none()
        if not job: raise NotFoundException("Job", str(job_id))
        sla_hours = DEFAULT_STATUS_SLA_HOURS.get(job.status)
        breach = job.sla_breach
        return {"job_id": str(job_id), "current_status": job.status,
                "sla_hours": sla_hours, "sla_breach": breach}

    async def list_jobs_admin(self, tenant_id: uuid.UUID | None, status: str | None,
                               limit: int, cursor: str | None,
                               q: str | None = None,
                               job_type: str | None = None,
                               sla_status: str | None = None,
                               unassigned: bool = False,
                               date_from: str | None = None,
                               date_to: str | None = None,
                               sort_by: str = "created_at",
                               sort_dir: str = "desc",
                               page: int = 1,
                               page_size: int = 50,
                               ) -> dict:
        """Platform-wide job queue for Super Admin — optionally filtered to one tenant."""
        from app.engines.tenant_engine.models import Tenant
        from app.engines.auth.models import User as AuthUser
        from sqlalchemy.orm import aliased
        CustomerUser = aliased(AuthUser)
        StaffUser    = aliased(AuthUser)

        stmt = (
            select(Job, Tenant.tenant_name,
                   CustomerUser.full_name.label("customer_name"),
                   StaffUser.full_name.label("staff_name"))
            .join(Tenant, Tenant.id == Job.tenant_id)
            .outerjoin(CustomerUser, CustomerUser.id == Job.customer_id)
            .outerjoin(StaffUser,    StaffUser.id    == Job.assigned_staff_id)
        )

        if tenant_id:  stmt = stmt.where(Job.tenant_id == tenant_id)
        if status:     stmt = stmt.where(Job.status == status)
        if job_type:   stmt = stmt.where(Job.job_type == job_type)
        if unassigned: stmt = stmt.where(Job.assigned_staff_id.is_(None))
        if sla_status == "breached":
            stmt = stmt.where(Job.sla_breached.is_(True))
        elif sla_status == "at_risk":
            stmt = stmt.where(Job.sla_breach.is_(True), Job.sla_breached.is_(False))
        if date_from:
            try: stmt = stmt.where(Job.created_at >= datetime.fromisoformat(date_from))
            except Exception: pass
        if date_to:
            try: stmt = stmt.where(Job.created_at <= datetime.fromisoformat(date_to))
            except Exception: pass
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                Job.job_number.ilike(like) |
                CustomerUser.full_name.ilike(like) |
                Tenant.tenant_name.ilike(like) |
                Job.city.ilike(like)
            )
        if cursor:
            try:
                c = decode_cursor(cursor)
                stmt = stmt.where(Job.created_at < datetime.fromisoformat(c["created_at"]))
            except Exception: pass

        sort_col = {
            "created_at": Job.created_at,
            "scheduled_at": Job.scheduled_at,
            "status_updated_at": Job.status_updated_at,
            "minutes_in_status": Job.minutes_in_status,
        }.get(sort_by, Job.created_at)
        stmt = stmt.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())

        if not cursor:
            stmt = stmt.offset((page - 1) * page_size).limit(page_size + 1)
        else:
            stmt = stmt.limit(limit + 1)

        rows = (await self.db.execute(stmt)).all()
        fetch_limit = page_size if not cursor else limit
        has_next = len(rows) > fetch_limit
        rows = rows[:fetch_limit]

        jobs_out = []
        for job, tenant_name, customer_name, staff_name in rows:
            d = self._job_dict(job)
            d["tenant_name"]   = tenant_name
            d["customer_name"] = customer_name
            d["staff_name"]    = staff_name
            d["assigned_staff"] = staff_name
            jobs_out.append(d)

        nc = encode_cursor({"created_at": rows[-1][0].created_at.isoformat()}) if has_next and rows and cursor else None
        return {"jobs": jobs_out, "has_next": has_next, "next_cursor": nc,
                "page": page, "page_size": fetch_limit, "total_in_page": len(jobs_out)}

    async def get_ops_summary(self, tenant_id: uuid.UUID | None = None) -> dict:
        """Platform-wide summary counts for the Operations Board."""
        from sqlalchemy import case
        now = utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        active_non_terminal = [
            JS.PENDING_ASSIGNMENT, JS.ASSIGNED, JS.REJECTED_BY_STAFF,
            JS.ACCEPTED, JS.EN_ROUTE, JS.ARRIVED,
            JS.ASSESSMENT_STARTED, JS.ASSESSMENT_COMPLETE,
            JS.QUOTE_PENDING, JS.QUOTE_APPROVED,
            JS.WORK_STARTED, JS.PARTS_REQUIRED, JS.PARTS_ORDERED,
            JS.PARTS_RECEIVED, JS.WORK_RESUMED, JS.WORK_COMPLETE,
            JS.CHECKLIST_STARTED, JS.CHECKLIST_COMPLETE,
            JS.QUALITY_CHECK, JS.QUALITY_FAILED, JS.REWORK_REQUIRED,
            JS.REWORK_COMPLETE, JS.PENDING_SIGN_OFF, JS.SIGNED_OFF,
            JS.INVOICE_GENERATED, JS.PAYMENT_PENDING, JS.PAID,
        ]

        base = select(
            func.count(Job.id).label("total"),
            func.sum(case((Job.status == JS.WORK_STARTED, 1), else_=0)).label("in_progress"),
            func.sum(case((Job.sla_breached.is_(True), 1), else_=0)).label("sla_breached"),
            func.sum(case((
                Job.assigned_staff_id.is_(None) & Job.status.in_(active_non_terminal), 1
            ), else_=0)).label("unassigned"),
            func.sum(case((Job.status == JS.REWORK_REQUIRED, 1), else_=0)).label("rework"),
            func.sum(case((
                Job.completed_at >= today_start, 1
            ), else_=0)).label("completed_today"),
        ).where(Job.status.not_in([JS.DRAFT, JS.VOIDED]))

        if tenant_id:
            base = base.where(Job.tenant_id == tenant_id)

        row = (await self.db.execute(base)).one()

        def _i(v): return int(v or 0)

        return {
            "total_active":    _i(row.total),
            "in_progress":     _i(row.in_progress),
            "sla_breached":    _i(row.sla_breached),
            "unassigned":      _i(row.unassigned),
            "rework_required": _i(row.rework),
            "completed_today": _i(row.completed_today),
        }

    async def get_sla_alerts(self, tenant_id: uuid.UUID | None = None, limit: int = 200) -> list[dict]:
        from app.engines.tenant_engine.models import Tenant
        limit = min(limit, 500)
        q = select(Job, Tenant.tenant_name).join(Tenant, Tenant.id == Job.tenant_id).where(
            Job.sla_breach.is_(True)).order_by(Job.updated_at.asc()).limit(limit)
        if tenant_id: q = q.where(Job.tenant_id == tenant_id)
        rows = (await self.db.execute(q)).all()
        alerts = []
        for job, tenant_name in rows:
            sla_hours = DEFAULT_STATUS_SLA_HOURS.get(job.status, 0)
            minutes_overdue = max(0, int((utcnow() - job.updated_at).total_seconds() / 60 - sla_hours * 60))
            severity = "critical" if minutes_overdue > 60 else "high" if minutes_overdue > 30 else "medium"
            alerts.append({"job_id": str(job.id), "job_number": job.job_number,
                            "tenant_name": tenant_name, "status": job.status,
                            "minutes_overdue": minutes_overdue, "severity": severity})
        return alerts

    async def get_job_counts_by_status(self, tenant_id: uuid.UUID) -> dict:
        r = await self.db.execute(select(Job.status, func.count(Job.id)).where(
            Job.tenant_id == tenant_id).group_by(Job.status))
        rows = r.all()
        return {"tenant_id": str(tenant_id), "counts": {row[0]: row[1] for row in rows},
                "total": sum(row[1] for row in rows)}

    async def get_staff_earnings(self, staff_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
        """Self-service earnings summary for a technician — derived straight from
        their completed jobs. Not a payout ledger (none exists yet); a tenant
        runs its own payroll, this just shows job value handled."""
        if self.actor_role in ("staff", "technician") and self.actor_id != staff_id:
            raise NotFoundException("StaffEarnings", str(staff_id))

        month_start = utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        base = (
            select(Job)
            .where(Job.tenant_id == tenant_id,
                   Job.assigned_staff_id == staff_id,
                   Job.status == JS.CLOSED)
            .order_by(Job.completed_at.desc())
            .limit(1000)
        )
        rows = (await self.db.execute(base)).scalars().all()

        def _value(j: Job) -> Decimal:
            return j.final_price or j.quoted_price or Decimal("0")

        total_jobs = len(rows)
        total_value = sum((_value(j) for j in rows), Decimal("0"))
        this_month = [j for j in rows if j.completed_at and j.completed_at >= month_start]
        ratings = [j.customer_rating for j in rows if j.customer_rating is not None]

        return {
            "staff_id": str(staff_id), "tenant_id": str(tenant_id),
            "jobs_completed_total": total_jobs,
            "job_value_total": float(total_value),
            "jobs_completed_this_month": len(this_month),
            "job_value_this_month": float(sum((_value(j) for j in this_month), Decimal("0"))),
            "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
        }

    # ── Void job ──────────────────────────────────────────────────────────────
    async def void_job(self, job_id: uuid.UUID, reason: str) -> dict:
        # Slice 2F-14A: this method previously loaded the job by ID with no
        # tenant-ownership check at all -- any tenant_owner holding the
        # platform-wide TENANT_UPDATE permission could void a job belonging to
        # a DIFFERENT tenant. _get_job_for_assignment is the existing
        # tenant_owner-own-tenant/super_admin-platform-wide helper already used
        # by assign_staff/convert_to_repair -- reused here rather than inventing
        # a new ownership check.
        job = await self._get_job_for_assignment(job_id)
        if job.status in TERMINAL_STATUSES:
            raise ServiceOSException("CONFLICT", f"Job already in terminal status: {job.status}")
        if job.status in LOCKED_STATUSES:
            raise ServiceOSException("CONFLICT",
                f"Job is in {job.status} — cannot void while work is in progress.")
        from_status = job.status
        job.status = JS.VOIDED
        try:
            from app.core.usage_quota import adjust_usage
            await adjust_usage(self.db, job.tenant_id, "current_active_jobs", -1)
        except Exception as e:
            logger.warning("fieldops.job_usage_decrement_failed", error=str(e))
        await self._write_history(job, from_status, JS.VOIDED, f"Voided: {reason}", None, None)
        return self._job_dict(job)
