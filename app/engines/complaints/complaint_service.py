"""Sprint 25 — Complaint Service (core business logic)."""
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func

from datetime import timedelta

from app.engines.complaints.constants import (
    STATUS_OPEN, STATUS_AWAITING_PROVIDER, STATUS_AWAITING_CUSTOMER,
    STATUS_RESOLUTION_PROPOSED, STATUS_REWORK_APPROVED,
    STATUS_REFUND_REQUESTED, STATUS_REFUND_APPROVED, STATUS_REFUND_RECORDED,
    STATUS_RESOLVED, STATUS_CANCELLED,
    STATUS_SETTLED,
    ALLOWED_TRANSITIONS, ALLOWED_TRANSITIONS_EXT, FINAL_STATUSES,
    SLA_ON_TIME, SLA_AT_RISK, SLA_BREACHED, SLA_ESCALATED,
    RES_PROPOSED, RES_CUSTOMER_ACCEPTED, RES_CUSTOMER_REJECTED,
    PROPOSAL_PROPOSED, PROPOSAL_ACCEPTED, PROPOSAL_REJECTED, PROPOSAL_COUNTERED,
    ACTOR_CUSTOMER, ACTOR_PROVIDER, ACTOR_SYSTEM,
    VIS_PUBLIC,
    EVT_COMPLAINT_CREATED, EVT_PROVIDER_RESPONDED, EVT_CUSTOMER_MESSAGE_ADDED,
    EVT_EVIDENCE_UPLOADED, EVT_STATUS_CHANGED,
    EVT_RESOLUTION_PROPOSED, EVT_RESOLUTION_ACCEPTED, EVT_RESOLUTION_REJECTED,
    EVT_SLA_BREACHED, EVT_SETTLEMENT_PROPOSED, EVT_SETTLEMENT_ACCEPTED,
    EVT_SETTLEMENT_REJECTED, EVT_SETTLEMENT_COUNTERED,
    ERR_COMPLAINT_NOT_FOUND, ERR_COMPLAINT_ACCESS_DENIED, ERR_COMPLAINT_ALREADY_CLOSED,
    ERR_COMPLAINT_INVALID_TRANSITION,
    ERR_COMPLAINT_MESSAGE_REQUIRED, ERR_RESOLUTION_NOT_FOUND,
    ERR_COMPLAINT_RECORD_NOT_FOUND, ERR_COMPLAINT_NOT_ELIGIBLE,
)
from app.engines.complaints.models import (
    CustomerComplaint, ComplaintMessage, ComplaintMedia,
    ComplaintEvent, ComplaintResolution, ComplaintPolicy,
    SettlementProposal,
)
from app.engines.complaints.eligibility_service import ComplaintEligibilityService


class ComplaintService:

    def __init__(self):
        self._eligibility = ComplaintEligibilityService()

    # ── Create complaint ───────────────────────────────────────────────────────
    async def _resolve_tenant_for_record(
        self, db: AsyncSession, record_type: str, record_id: uuid.UUID
    ) -> uuid.UUID | None:
        """Resolve the owning tenant of the record a complaint is filed against,
        so provider-scoped queries can see it (bug #25)."""
        from app.engines.complaints.constants import (
            RECORD_SERVICE_BOOKING, RECORD_SERVICE_JOB, RECORD_SERVICE_INVOICE,
        )
        table = {
            RECORD_SERVICE_BOOKING: "service_bookings",
            RECORD_SERVICE_JOB:     "service_jobs",
            RECORD_SERVICE_INVOICE: "service_invoices",
        }.get(record_type)
        if not table:
            return None
        from sqlalchemy import text
        row = await db.execute(
            text(f"SELECT tenant_id FROM {table} WHERE id = :rid"), {"rid": str(record_id)}
        )
        return row.scalar_one_or_none()

    @staticmethod
    async def _link_service_job(db: AsyncSession, complaint, record_type: str, record_id) -> None:
        """Resolve and stamp `job_id` for a complaint filed against a booking.

        The customer app files complaints with record_type="service_booking"
        (see CreateSupportRequestScreen, which hardcodes it), which stamped
        `booking_id` and left `job_id` NULL. Everything the provider needs to
        actually work the case hangs off the job:

          * the queue row's job number and service name (`_job_snapshot`),
          * the Job Context tab,
          * the `service_id` queue filter, which matches on the job's offering,
          * and the Reviews page's complaint join, which links reviews to
            complaints through `job_id` -- so a review could never be shown as
            having a complaint against it.

        The booking -> job link already exists as `service_jobs.booking_id`;
        this just follows it. Best-effort: a complaint must still be filed if
        the booking has no job yet.
        """
        from sqlalchemy import text
        from app.engines.complaints.constants import RECORD_SERVICE_BOOKING
        if record_type != RECORD_SERVICE_BOOKING or complaint.job_id:
            return
        try:
            row = (await db.execute(
                text("SELECT id, offering_id FROM service_jobs WHERE booking_id = :bid "
                     "ORDER BY created_at DESC LIMIT 1"),
                {"bid": str(record_id)},
            )).fetchone()
            if row:
                complaint.job_id = row.id
                # The `service_id` queue filter matches on the complaint's own
                # offering_id, but the customer app never supplies one -- so the
                # filter could not match anything. The complaint's service IS
                # the job's service, so inherit it.
                if not complaint.offering_id:
                    complaint.offering_id = row.offering_id
        except Exception:
            pass

    async def create_complaint(
        self,
        db: AsyncSession,
        customer_id: uuid.UUID,
        category_id: uuid.UUID,
        record_type: str,
        record_id: uuid.UUID,
        complaint_type: str,
        description: str,
        *,
        tenant_id: uuid.UUID | None = None,
        offering_id: uuid.UUID | None = None,
        requested_resolution: str | None = None,
        title: str | None = None,
        commit: bool = True,
        request_id: str = "—",
    ) -> CustomerComplaint:
        # MODULE-L5-02 bug #25: the customer who files a complaint has no tenant
        # (tenant_id is None on customer accounts), so the complaint was persisted
        # with tenant_id = NULL. That made it invisible to the provider whose job
        # it is about — provider_list_complaints filters by tenant_id and
        # provider_get_complaint denies when it does not match — so the entire
        # provider-side complaint flow was dead. Resolve the owning tenant from
        # the linked record when the caller did not supply one.
        # Slice 2F-10A: ComplaintEligibilityService.check_eligible is the
        # canonical creation-eligibility contract, not merely an advisory
        # preflight -- its own record-status table (ELIGIBLE_STATUSES) has
        # real, deliberate product history (see MODULE-L5-02 bug #23's
        # comment in constants.py), and its window/duplicate rules are
        # backed by a real, configurable ComplaintPolicy model, not a
        # stub. Slice 2F-10 wired in only the ownership half of this
        # check directly (duplicating _fetch_record/_customer_owns_record
        # inline); this call now uses the single, shared, canonical
        # assertion for ALL of it -- record existence, ownership, status
        # eligibility, filing window, and duplicate-open-complaint --
        # so `check_eligible` and `create_complaint` can never disagree
        # with each other for the same fixture (see
        # docs/workflow-rearchitecture/phase-02a-slice-02f10a/
        # complaint-eligibility-contract.md). Raises before any
        # CustomerComplaint row is constructed.
        eligibility = await self._eligibility.check_eligible(
            db, customer_id, record_type, record_id,
            complaint_type=complaint_type, category_id=category_id,
        )
        if not eligibility["eligible"]:
            raise ValueError(eligibility["reason_code"] or ERR_COMPLAINT_NOT_ELIGIBLE)

        if tenant_id is None:
            tenant_id = await self._resolve_tenant_for_record(db, record_type, record_id)
        complaint = CustomerComplaint(
            customer_id          = customer_id,
            tenant_id            = tenant_id,
            category_id          = category_id,
            offering_id          = offering_id,
            record_type          = record_type,
            record_id            = record_id,
            complaint_type       = complaint_type,
            requested_resolution = requested_resolution,
            title                = title,
            description          = description,
            status               = STATUS_OPEN,
            priority             = "normal",
        )
        # FK convenience
        from app.engines.complaints.constants import (
            RECORD_SERVICE_BOOKING, RECORD_SERVICE_JOB, RECORD_SERVICE_INVOICE,
            RECORD_COACHING_APPOINTMENT, RECORD_REAL_ESTATE_LEAD, RECORD_CUSTOMER_REVIEW,
        )
        if record_type == RECORD_SERVICE_BOOKING:
            complaint.booking_id = record_id
        elif record_type == RECORD_SERVICE_JOB:
            complaint.job_id = record_id
        elif record_type == RECORD_SERVICE_INVOICE:
            complaint.invoice_id = record_id
        elif record_type == RECORD_COACHING_APPOINTMENT:
            complaint.appointment_id = record_id
        elif record_type == RECORD_REAL_ESTATE_LEAD:
            complaint.lead_id = record_id
        elif record_type == RECORD_CUSTOMER_REVIEW:
            complaint.review_id = record_id

        await self._link_service_job(db, complaint, record_type, record_id)

        # SLA deadlines
        now = datetime.now(timezone.utc)
        complaint.tenant_first_response_due_at = now + timedelta(hours=24)
        complaint.sla_status = SLA_ON_TIME

        db.add(complaint)
        await db.flush()
        await self._log_event(
            db, complaint.id, tenant_id, ACTOR_CUSTOMER, customer_id,
            EVT_COMPLAINT_CREATED, None, STATUS_OPEN, None, None,
            request_id=request_id,
        )
        # bug #42: tell the provider a customer has raised a complaint about their
        # job — otherwise they never know they need to respond.
        try:
            from app.engines.complaints.notifications import notify_provider_complaint
            await notify_provider_complaint(
                db, complaint,
                notification_type="complaint.filed",
                title=f"New complaint — {complaint.complaint_number}",
                body=(complaint.title or complaint.complaint_type.replace("_", " ")).strip()
                     + " — please respond.",
                severity="warning",
            )
        except Exception:
            pass
        if commit:
            await db.commit()
        return complaint

    # ── Customer read ─────────────────────────────────────────────────────────
    async def get_customer_complaint(
        self, db: AsyncSession, customer_id: uuid.UUID, complaint_id: uuid.UUID
    ) -> CustomerComplaint:
        complaint = await self._get_complaint(db, complaint_id)
        if str(complaint.customer_id) != str(customer_id):
            raise ValueError(ERR_COMPLAINT_ACCESS_DENIED)
        return complaint

    async def list_customer_complaints(
        self, db: AsyncSession, customer_id: uuid.UUID, status: str | None = None
    ) -> list[CustomerComplaint]:
        q = select(CustomerComplaint).where(CustomerComplaint.customer_id == customer_id)
        if status:
            q = q.where(CustomerComplaint.status == status)
        q = q.order_by(CustomerComplaint.created_at.desc()).limit(100)
        r = await db.execute(q)
        return r.scalars().all()

    # ── Customer actions ──────────────────────────────────────────────────────
    async def add_customer_message(
        self,
        db: AsyncSession,
        customer_id: uuid.UUID,
        complaint_id: uuid.UUID,
        message_text: str,
        request_id: str = "—",
    ) -> ComplaintMessage:
        if not message_text or not message_text.strip():
            raise ValueError(ERR_COMPLAINT_MESSAGE_REQUIRED)
        complaint = await self.get_customer_complaint(db, customer_id, complaint_id)
        if complaint.status in FINAL_STATUSES:
            raise ValueError(ERR_COMPLAINT_ALREADY_CLOSED)

        msg = ComplaintMessage(
            complaint_id   = complaint_id,
            tenant_id      = complaint.tenant_id,
            sender_type    = ACTOR_CUSTOMER,
            sender_user_id = customer_id,
            message_text   = message_text,
            visibility     = VIS_PUBLIC,
        )
        db.add(msg)
        await db.flush()
        await self._log_event(db, complaint_id, complaint.tenant_id, ACTOR_CUSTOMER, customer_id,
                              EVT_CUSTOMER_MESSAGE_ADDED, None, None, None, None, request_id=request_id)
        await db.commit()
        return msg

    async def upload_complaint_media(
        self,
        db: AsyncSession,
        actor_user_id: uuid.UUID,
        actor_type: str,
        complaint_id: uuid.UUID,
        file_url: str,
        media_type: str = "photo",
        file_name: str | None = None,
        caption: str | None = None,
        visibility: str = VIS_PUBLIC,
        request_id: str = "—",
    ) -> ComplaintMedia:
        # `_get_complaint` loads by primary key with no ownership check, so a
        # caller could attach evidence to any tenant's complaint. Customer
        # callers pass their own id and are scoped the same way
        # `add_customer_message` scopes itself; provider/admin callers keep the
        # unscoped load, matching the rest of this service.
        if actor_type == ACTOR_CUSTOMER:
            complaint = await self.get_customer_complaint(db, actor_user_id, complaint_id)
        else:
            complaint = await self._get_complaint(db, complaint_id)
        if complaint.status in FINAL_STATUSES:
            raise ValueError(ERR_COMPLAINT_ALREADY_CLOSED)
        media = ComplaintMedia(
            complaint_id        = complaint_id,
            uploaded_by_user_id = actor_user_id,
            uploaded_by_type    = actor_type,
            media_type          = media_type,
            file_url            = file_url,
            file_name           = file_name,
            caption             = caption,
            visibility          = visibility,
        )
        db.add(media)
        await db.flush()
        await self._log_event(db, complaint_id, complaint.tenant_id, actor_type, actor_user_id,
                              EVT_EVIDENCE_UPLOADED, None, None, None, {"file_url": file_url}, request_id=request_id)
        await db.commit()
        return media

    async def cancel_customer_complaint(
        self,
        db: AsyncSession,
        customer_id: uuid.UUID,
        complaint_id: uuid.UUID,
        reason: str,
        request_id: str = "—",
    ) -> CustomerComplaint:
        complaint = await self.get_customer_complaint(db, customer_id, complaint_id)
        await self._transition(db, complaint, STATUS_CANCELLED, ACTOR_CUSTOMER, customer_id,
                               reason=reason, request_id=request_id)
        await db.commit()
        return complaint

    async def customer_accept_resolution(
        self,
        db: AsyncSession,
        customer_id: uuid.UUID,
        complaint_id: uuid.UUID,
        resolution_id: uuid.UUID,
        request_id: str = "—",
    ) -> ComplaintResolution:
        complaint = await self.get_customer_complaint(db, customer_id, complaint_id)
        resolution = await self._get_resolution(db, resolution_id, complaint_id=complaint_id)
        # Slice 2F-10: validate the complaint's state transition *before*
        # mutating resolution.status or (for a rework resolution)
        # committing a real ServiceReworkRequest. Previously
        # resolution.status was flushed, and for rework resolutions a
        # ServiceReworkRequest was created AND COMMITTED, before
        # _transition ever checked whether the complaint's current status
        # legally allows resolved/rework_approved -- an illegal-state
        # accept still left a resolution marked accepted (and, for
        # rework, a real rework request row) persisted ahead of the
        # ValueError. Pre-validate using the same ALLOWED_TRANSITIONS_EXT
        # map _transition itself uses, so nothing is created or mutated
        # unless the transition is already known to be legal.
        target_status = (STATUS_REWORK_APPROVED
                          if getattr(resolution, "resolution_type", None) == "rework"
                          else STATUS_RESOLVED)
        if target_status not in ALLOWED_TRANSITIONS_EXT.get(complaint.status, set()):
            raise ValueError(f"{ERR_COMPLAINT_INVALID_TRANSITION}: {complaint.status} → {target_status}")

        resolution.status = RES_CUSTOMER_ACCEPTED
        complaint.customer_accepted_resolution_at = datetime.now(timezone.utc)
        await db.flush()

        # MODULE-L5-02 bug #28: a rework-type resolution must actually spawn a
        # ServiceReworkRequest — create_rework_request_from_complaint had NO
        # caller anywhere, so the entire rework sub-flow (admin approve/assign,
        # provider schedule/start/complete) operated on records that could never
        # exist. When the customer accepts a rework resolution, create the rework
        # request and move the complaint to rework_approved (the provider then
        # runs the rework, whose completion resolves the complaint). All other
        # resolution types resolve the complaint immediately as before.
        if getattr(resolution, "resolution_type", None) == "rework":
            from app.engines.complaints.rework_service import ServiceReworkService
            await ServiceReworkService().create_rework_request_from_complaint(
                db, complaint_id, customer_id, ACTOR_CUSTOMER,
                rework_reason=(resolution.description or "Customer accepted rework resolution"),
                request_id=request_id,
            )
            # the helper committed; re-fetch the complaint before transitioning
            complaint = await self._get_complaint(db, complaint_id)
            await self._transition(db, complaint, STATUS_REWORK_APPROVED, ACTOR_CUSTOMER, customer_id,
                                   reason="Customer accepted rework resolution", request_id=request_id)
        else:
            await self._transition(db, complaint, STATUS_RESOLVED, ACTOR_CUSTOMER, customer_id,
                                   reason="Customer accepted resolution", request_id=request_id)
        await self._log_event(db, complaint_id, complaint.tenant_id, ACTOR_CUSTOMER, customer_id,
                              EVT_RESOLUTION_ACCEPTED, None, None, None, {"resolution_id": str(resolution_id)},
                              request_id=request_id)
        await db.commit()
        return resolution

    async def customer_reject_resolution(
        self,
        db: AsyncSession,
        customer_id: uuid.UUID,
        complaint_id: uuid.UUID,
        resolution_id: uuid.UUID,
        reason: str,
        request_id: str = "—",
    ) -> ComplaintResolution:
        complaint = await self.get_customer_complaint(db, customer_id, complaint_id)
        resolution = await self._get_resolution(db, resolution_id, complaint_id=complaint_id)
        # Slice 2F-10: same ordering fix as customer_accept_resolution --
        # validate the transition before mutating resolution.status.
        if STATUS_AWAITING_PROVIDER not in ALLOWED_TRANSITIONS.get(complaint.status, set()):
            raise ValueError(f"{ERR_COMPLAINT_INVALID_TRANSITION}: {complaint.status} → {STATUS_AWAITING_PROVIDER}")

        resolution.status = RES_CUSTOMER_REJECTED
        await db.flush()
        await self._transition(db, complaint, STATUS_AWAITING_PROVIDER, ACTOR_CUSTOMER, customer_id,
                               reason=reason, request_id=request_id)
        await self._log_event(db, complaint_id, complaint.tenant_id, ACTOR_CUSTOMER, customer_id,
                              EVT_RESOLUTION_REJECTED, None, None, None, {"reason": reason}, request_id=request_id)
        await db.commit()
        return resolution

    # ── Provider actions ──────────────────────────────────────────────────────
    async def provider_list_complaints(
        self, db: AsyncSession, tenant_id: uuid.UUID, status: str | None = None
    ) -> list[CustomerComplaint]:
        q = select(CustomerComplaint).where(CustomerComplaint.tenant_id == tenant_id)
        if status:
            q = q.where(CustomerComplaint.status == status)
        q = q.order_by(CustomerComplaint.created_at.desc()).limit(100)
        r = await db.execute(q)
        return r.scalars().all()

    async def tenant_queue_summary(self, db: AsyncSession, tenant_id: uuid.UUID) -> dict:
        """Real bug fixed here: tenant_router.py's queue endpoint called this
        method (and tenant_list_complaints below) unconditionally on every
        request, but neither was ever implemented on ComplaintService --
        every tenant-facing complaints request 500'd (masked as a CORS
        error in the browser, since the crashed response carries no CORS
        headers). Counts mirror the same FINAL_STATUSES / sla_status /
        severity vocabulary already used elsewhere in this file."""
        base = select(CustomerComplaint).where(CustomerComplaint.tenant_id == tenant_id)
        rows = (await db.execute(base)).scalars().all()
        open_rows = [c for c in rows if c.status not in FINAL_STATUSES]
        # `awaiting_response` and `resolved_this_month` are new. The tenant
        # KPI strip already rendered tiles for both (plus an "SLA breached"
        # tile reading `sla_breached`), but this method returned none of those
        # keys -- so three of the six tiles had always displayed `undefined`.
        # These two are real, cheap counts over rows already loaded; the third
        # was just the frontend using the wrong name for `breached`.
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        def _in_this_month(value) -> bool:
            if not value:
                return False
            stamped = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
            return stamped >= month_start

        return {
            "total": len(rows),
            "open": len(open_rows),
            "at_risk": len([c for c in open_rows if c.sla_status == "at_risk"]),
            "breached": len([c for c in open_rows if c.sla_status == "breached"]),
            "escalated": len([c for c in open_rows if c.sla_status == "escalated"]),
            "critical": len([c for c in open_rows if c.severity == "critical"]),
            "awaiting_response": len([
                c for c in open_rows
                if c.status == STATUS_AWAITING_PROVIDER or c.provider_response_required
            ]),
            "resolved_this_month": len([
                c for c in rows
                if _in_this_month(c.resolved_at) or _in_this_month(c.closed_at)
            ]),
        }

    async def tenant_list_complaints(
        self, db: AsyncSession, tenant_id: uuid.UUID, *,
        search: str | None = None, status: str | None = None, severity: str | None = None,
        sla_status: str | None = None, service_offering_id: uuid.UUID | None = None,
        complaint_type: str | None = None,
        cursor: int = 0, limit: int = 20,
    ) -> tuple[list[CustomerComplaint], int]:
        clauses = [CustomerComplaint.tenant_id == tenant_id]
        if status:
            clauses.append(CustomerComplaint.status == status if status != "open"
                            else CustomerComplaint.status.notin_(FINAL_STATUSES))
        if severity:
            clauses.append(CustomerComplaint.severity == severity)
        if sla_status:
            clauses.append(CustomerComplaint.sla_status == sla_status)
        if service_offering_id:
            clauses.append(CustomerComplaint.offering_id == service_offering_id)
        if complaint_type:
            clauses.append(CustomerComplaint.complaint_type == complaint_type)
        if search:
            like = f"%{search}%"
            # Description was not searchable, so searching for a phrase the
            # customer actually wrote returned nothing unless it happened to be
            # in the (often absent) title.
            clauses.append(or_(
                CustomerComplaint.complaint_number.ilike(like),
                CustomerComplaint.title.ilike(like),
                CustomerComplaint.description.ilike(like),
            ))

        total = (await db.execute(
            select(func.count()).select_from(select(CustomerComplaint).where(*clauses).subquery())
        )).scalar() or 0
        rows = (await db.execute(
            select(CustomerComplaint).where(*clauses)
            .order_by(CustomerComplaint.created_at.desc()).offset(cursor).limit(limit)
        )).scalars().all()
        return list(rows), total

    async def provider_get_complaint(
        self, db: AsyncSession, tenant_id: uuid.UUID, complaint_id: uuid.UUID
    ) -> CustomerComplaint:
        complaint = await self._get_complaint(db, complaint_id)
        if str(complaint.tenant_id) != str(tenant_id):
            raise ValueError(ERR_COMPLAINT_ACCESS_DENIED)
        return complaint

    async def provider_add_response(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        complaint_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        message_text: str,
        request_id: str = "—",
    ) -> ComplaintMessage:
        complaint = await self.provider_get_complaint(db, tenant_id, complaint_id)
        if not message_text.strip():
            raise ValueError(ERR_COMPLAINT_MESSAGE_REQUIRED)
        # Slice 2F-9A: previously had no final-state check at all -- the
        # customer's own analogous add-message method
        # (customer_add_message, line ~190) already guards this exact
        # capability with the identical check; provider_add_response was
        # simply inconsistent with its own sibling method. Mirrors the
        # existing, established pattern -- not a new rule.
        if complaint.status in FINAL_STATUSES:
            raise ValueError(ERR_COMPLAINT_ALREADY_CLOSED)

        msg = ComplaintMessage(
            complaint_id   = complaint_id,
            tenant_id      = tenant_id,
            sender_type    = ACTOR_PROVIDER,
            sender_user_id = actor_user_id,
            message_text   = message_text,
            visibility     = VIS_PUBLIC,
        )
        db.add(msg)
        complaint.provider_responded_at = datetime.now(timezone.utc)
        await db.flush()
        await self._log_event(db, complaint_id, tenant_id, ACTOR_PROVIDER, actor_user_id,
                              EVT_PROVIDER_RESPONDED, None, None, None, None, request_id=request_id)
        await db.commit()
        return msg

    async def provider_offer_resolution(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        complaint_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        resolution_type: str,
        description: str,
        customer_visible_notes: str | None = None,
        request_id: str = "—",
    ) -> ComplaintResolution:
        complaint = await self.provider_get_complaint(db, tenant_id, complaint_id)
        # Slice 2F-9A: validate the state transition *before* creating the
        # resolution record. Previously the record was added/flushed first
        # and the transition legality was only checked afterward -- an
        # illegal-state offer still wrote a ComplaintResolution row to the
        # session ahead of the ValueError. Reordered so no record is
        # created at all when the transition is invalid.
        await self._transition(db, complaint, STATUS_RESOLUTION_PROPOSED, ACTOR_PROVIDER, actor_user_id,
                               request_id=request_id)
        resolution = ComplaintResolution(
            complaint_id           = complaint_id,
            tenant_id              = tenant_id,
            resolution_type        = resolution_type,
            status                 = RES_PROPOSED,
            proposed_by_type       = ACTOR_PROVIDER,
            proposed_by_user_id    = actor_user_id,
            description            = description,
            customer_visible_notes = customer_visible_notes,
        )
        db.add(resolution)
        await db.flush()
        await self._log_event(db, complaint_id, tenant_id, ACTOR_PROVIDER, actor_user_id,
                              EVT_RESOLUTION_PROPOSED, None, None, None, {"type": resolution_type},
                              request_id=request_id)
        # bug #42: the customer must be told a resolution is awaiting their
        # accept/reject — otherwise the complaint sits in resolution_proposed
        # forever with nobody aware it is the customer's move.
        try:
            from app.engines.complaints.notifications import notify_customer_complaint
            await notify_customer_complaint(
                db, complaint,
                notification_type="complaint.resolution_offered",
                title=f"A resolution was offered — {complaint.complaint_number}",
                body=f"The provider offered: {resolution_type.replace('_', ' ')}. "
                     "Open the complaint to accept or reject it.",
                severity="info",
            )
        except Exception:
            pass
        await db.commit()
        return resolution

    # ── Admin actions ─────────────────────────────────────────────────────────
    async def admin_list_complaints(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        status: str | None = None,
        priority: str | None = None,
        record_type: str | None = None,
        limit: int = 100,
    ) -> list[CustomerComplaint]:
        q = select(CustomerComplaint)
        if tenant_id:
            q = q.where(CustomerComplaint.tenant_id == tenant_id)
        if customer_id:
            q = q.where(CustomerComplaint.customer_id == customer_id)
        if status:
            q = q.where(CustomerComplaint.status == status)
        if priority:
            q = q.where(CustomerComplaint.priority == priority)
        if record_type:
            q = q.where(CustomerComplaint.record_type == record_type)
        q = q.order_by(CustomerComplaint.created_at.desc()).limit(limit)
        r = await db.execute(q)
        return r.scalars().all()

    async def get_complaint(self, db: AsyncSession, complaint_id: uuid.UUID) -> CustomerComplaint:
        return await self._get_complaint(db, complaint_id)

    async def list_messages(
        self,
        db: AsyncSession,
        complaint_id: uuid.UUID,
        viewer: str = "admin",
    ) -> list[ComplaintMessage]:
        r = await db.execute(
            select(ComplaintMessage).where(ComplaintMessage.complaint_id == complaint_id)
            .order_by(ComplaintMessage.created_at)
        )
        msgs = r.scalars().all()
        return [m for m in msgs if m.is_visible_to(viewer)]

    async def list_media(
        self,
        db: AsyncSession,
        complaint_id: uuid.UUID,
        viewer: str = "admin",
    ) -> list[ComplaintMedia]:
        r = await db.execute(
            select(ComplaintMedia).where(ComplaintMedia.complaint_id == complaint_id)
            .order_by(ComplaintMedia.created_at)
        )
        media = r.scalars().all()
        if viewer == "admin":
            return media
        return [m for m in media if m.visibility == VIS_PUBLIC]

    async def list_resolutions(
        self, db: AsyncSession, complaint_id: uuid.UUID
    ) -> list[ComplaintResolution]:
        r = await db.execute(
            select(ComplaintResolution).where(ComplaintResolution.complaint_id == complaint_id)
            .order_by(ComplaintResolution.created_at)
        )
        return r.scalars().all()

    async def list_events(
        self, db: AsyncSession, complaint_id: uuid.UUID
    ) -> list[ComplaintEvent]:
        r = await db.execute(
            select(ComplaintEvent).where(ComplaintEvent.complaint_id == complaint_id)
            .order_by(ComplaintEvent.created_at)
        )
        return r.scalars().all()

    async def list_policies(self, db: AsyncSession) -> list[ComplaintPolicy]:
        r = await db.execute(select(ComplaintPolicy).order_by(ComplaintPolicy.created_at))
        return r.scalars().all()

    async def create_policy(self, db: AsyncSession, data: dict) -> ComplaintPolicy:
        # MODULE-L5-02 bug #39: policy_name is NOT NULL, so a create without one
        # blew up with a NotNullViolation -> 500. Default it from the key.
        data = dict(data)
        data.setdefault("policy_key", "default")
        if not data.get("policy_name"):
            data["policy_name"] = str(data["policy_key"]).replace("_", " ").title()
        p = ComplaintPolicy(**{k: v for k, v in data.items() if hasattr(ComplaintPolicy, k)})
        db.add(p)
        await db.commit()
        await db.refresh(p)
        return p

    async def update_policy(self, db: AsyncSession, policy_id: uuid.UUID, data: dict) -> ComplaintPolicy:
        r = await db.execute(select(ComplaintPolicy).where(ComplaintPolicy.id == policy_id))
        p = r.scalars().first()
        if not p:
            from app.engines.complaints.constants import ERR_COMPLAINT_POLICY_NOT_FOUND
            raise ValueError(ERR_COMPLAINT_POLICY_NOT_FOUND)
        for k, v in data.items():
            if hasattr(p, k):
                setattr(p, k, v)
        await db.commit()
        await db.refresh(p)
        return p

    # ── SLA management ────────────────────────────────────────────────────────
    async def check_and_update_sla(
        self, db: AsyncSession, complaint: CustomerComplaint, request_id: str = "—"
    ) -> CustomerComplaint:
        """Recompute sla_status based on now vs. deadline. Does not commit."""
        now = datetime.now(timezone.utc)
        if complaint.status in FINAL_STATUSES:
            return complaint

        due = complaint.tenant_first_response_due_at
        if not due:
            return complaint

        old_sla = complaint.sla_status
        if now > due + timedelta(hours=24):
            complaint.sla_status = SLA_ESCALATED
        elif now > due:
            complaint.sla_status = SLA_BREACHED
        elif now > due - timedelta(hours=4):
            complaint.sla_status = SLA_AT_RISK
        else:
            complaint.sla_status = SLA_ON_TIME

        if old_sla != complaint.sla_status and complaint.sla_status in (SLA_BREACHED, SLA_ESCALATED):
            await self._log_event(
                db, complaint.id, complaint.tenant_id, ACTOR_SYSTEM, None,
                EVT_SLA_BREACHED, None, None,
                {"sla_status": old_sla}, {"sla_status": complaint.sla_status},
                request_id=request_id,
            )
        await db.flush()
        return complaint

    async def get_sla_overdue_complaints(self, db: AsyncSession) -> list[CustomerComplaint]:
        """Return complaints past their tenant_first_response_due_at (for scheduler)."""
        now = datetime.now(timezone.utc)
        from sqlalchemy import and_
        q = (
            select(CustomerComplaint)
            .where(and_(
                CustomerComplaint.tenant_first_response_due_at < now,
                CustomerComplaint.status.notin_(list(FINAL_STATUSES | {STATUS_SETTLED})),
                CustomerComplaint.provider_responded_at.is_(None),
            ))
            .order_by(CustomerComplaint.tenant_first_response_due_at)
            .limit(200)
        )
        r = await db.execute(q)
        return r.scalars().all()

    # ── Settlement proposals ──────────────────────────────────────────────────
    async def create_settlement_proposal(
        self,
        db: AsyncSession,
        complaint_id: uuid.UUID,
        proposed_by: str,
        proposed_by_user_id: uuid.UUID | None,
        proposal_type: str,
        description: str,
        *,
        proposal_amount=None,
        conditions: str | None = None,
        request_id: str = "—",
        tenant_id: uuid.UUID | None = None,
    ) -> SettlementProposal:
        # Slice 2F-9: previously loaded via _get_complaint (no tenant check)
        # -- ANY authenticated user of any tenant could create a settlement
        # proposal on another tenant's complaint. The provider-facing caller
        # now always supplies its own principal tenant_id; a mismatch fails
        # closed with the same access-denied error provider_get_complaint
        # already uses elsewhere in this file.
        if tenant_id is not None:
            complaint = await self.provider_get_complaint(db, tenant_id, complaint_id)
        else:
            complaint = await self._get_complaint(db, complaint_id)
        proposal = SettlementProposal(
            complaint_id        = complaint_id,
            tenant_id           = complaint.tenant_id,
            proposed_by         = proposed_by,
            proposed_by_user_id = proposed_by_user_id,
            proposal_type       = proposal_type,
            description         = description,
            proposal_amount     = proposal_amount,
            conditions          = conditions,
            status              = PROPOSAL_PROPOSED,
        )
        db.add(proposal)
        complaint.settlement_status = PROPOSAL_PROPOSED
        await db.flush()
        await self._log_event(
            db, complaint_id, complaint.tenant_id, proposed_by, proposed_by_user_id,
            EVT_SETTLEMENT_PROPOSED, None, None,
            None, {"type": proposal_type, "amount": str(proposal_amount or "")},
            request_id=request_id,
        )
        # bug #42: a settlement needs BOTH parties to accept, so notify whoever
        # did NOT make this proposal that it is now awaiting their response.
        try:
            from app.engines.complaints.notifications import (
                notify_customer_complaint, notify_provider_complaint,
            )
            title = f"Settlement proposed — {complaint.complaint_number}"
            body = (f"A {proposal_type.replace('_', ' ')} settlement was proposed. "
                    "It only takes effect once both parties accept.")
            if proposed_by != ACTOR_CUSTOMER:
                await notify_customer_complaint(db, complaint,
                    notification_type="complaint.settlement_proposed", title=title, body=body)
            if proposed_by != ACTOR_PROVIDER:
                await notify_provider_complaint(db, complaint,
                    notification_type="complaint.settlement_proposed", title=title, body=body)
        except Exception:
            pass
        await db.commit()
        return proposal

    async def customer_respond_to_settlement(
        self,
        db: AsyncSession,
        customer_id: uuid.UUID,
        complaint_id: uuid.UUID,
        proposal_id: uuid.UUID,
        response: str,
        counter_description: str | None = None,
        request_id: str = "—",
    ) -> SettlementProposal:
        await self.get_customer_complaint(db, customer_id, complaint_id)
        proposal = await self._get_settlement_proposal(db, proposal_id, complaint_id=complaint_id)

        now = datetime.now(timezone.utc)
        proposal.customer_response   = response
        proposal.customer_responded_at = now

        complaint = await self._get_complaint(db, complaint_id)

        if response == "accept":
            # MODULE-L5-02 bug #30a: this used to set proposal.status =
            # PROPOSAL_ACCEPTED *before* _check_dual_acceptance, so a customer
            # accepting ALONE marked the proposal accepted (and stamped
            # settlement_status/resolved_at) without the provider ever agreeing —
            # defeating the whole dual-acceptance guarantee. Let
            # _check_dual_acceptance be the only thing that promotes the status.
            self._check_dual_acceptance(proposal)
            if proposal.status == PROPOSAL_ACCEPTED:
                complaint.settlement_status = PROPOSAL_ACCEPTED
                complaint.resolved_at = now
                # bug #30b: complaint.status was never advanced, so a fully
                # dual-accepted settlement left the complaint 'open' forever.
                complaint.status = STATUS_SETTLED
                # Pay the customer in CREDIT POINTS, funded from the provider's
                # canonical usage-credit balance. Never money.
                await self._execute_settlement_payout(db, complaint, proposal, customer_id)
        elif response == "reject":
            proposal.status = PROPOSAL_REJECTED
            complaint.settlement_status = PROPOSAL_REJECTED
        elif response == "counter" and counter_description:
            proposal.status = PROPOSAL_COUNTERED
            # Create a counter-proposal
            counter = SettlementProposal(
                complaint_id        = complaint_id,
                tenant_id           = complaint.tenant_id,
                proposed_by         = ACTOR_CUSTOMER,
                proposed_by_user_id = customer_id,
                proposal_type       = proposal.proposal_type,
                description         = counter_description,
                status              = PROPOSAL_PROPOSED,
            )
            db.add(counter)

        await db.flush()
        evt = {
            "accept": EVT_SETTLEMENT_ACCEPTED,
            "reject": EVT_SETTLEMENT_REJECTED,
            "counter": EVT_SETTLEMENT_COUNTERED,
        }.get(response, EVT_STATUS_CHANGED)
        await self._log_event(
            db, complaint_id, complaint.tenant_id, ACTOR_CUSTOMER, customer_id,
            evt, None, None, None, {"response": response}, request_id=request_id,
        )
        await db.commit()
        return proposal

    async def tenant_respond_to_settlement(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        complaint_id: uuid.UUID,
        proposal_id: uuid.UUID,
        response: str,
        actor_user_id: uuid.UUID | None = None,
        request_id: str = "—",
    ) -> SettlementProposal:
        await self.provider_get_complaint(db, tenant_id, complaint_id)
        proposal = await self._get_settlement_proposal(db, proposal_id, complaint_id=complaint_id)

        now = datetime.now(timezone.utc)
        proposal.tenant_response   = response
        proposal.tenant_responded_at = now

        complaint = await self._get_complaint(db, complaint_id)

        if response == "accept":
            self._check_dual_acceptance(proposal)
            if proposal.status == PROPOSAL_ACCEPTED:
                complaint.settlement_status = PROPOSAL_ACCEPTED
                complaint.resolved_at = now
                # MODULE-L5-02 bug #30b: complaint.status was never advanced on
                # dual acceptance, so a settlement accepted by BOTH parties left
                # the complaint sitting at 'open' in every queue forever.
                complaint.status = STATUS_SETTLED
                # Pay the customer in credit points funded from the provider's
                # canonical usage-credit balance. Never money.
                await self._execute_settlement_payout(db, complaint, proposal, actor_user_id)
        elif response == "reject":
            proposal.status = PROPOSAL_REJECTED
            complaint.settlement_status = PROPOSAL_REJECTED

        await db.flush()
        evt = EVT_SETTLEMENT_ACCEPTED if response == "accept" else EVT_SETTLEMENT_REJECTED
        await self._log_event(
            db, complaint_id, complaint.tenant_id, ACTOR_PROVIDER, actor_user_id,
            evt, None, None, None, {"response": response}, request_id=request_id,
        )
        await db.commit()
        return proposal

    async def list_settlement_proposals(
        self, db: AsyncSession, complaint_id: uuid.UUID
    ) -> list[SettlementProposal]:
        r = await db.execute(
            select(SettlementProposal)
            .where(SettlementProposal.complaint_id == complaint_id)
            .order_by(SettlementProposal.created_at)
        )
        return r.scalars().all()

    # ── Internal helpers ──────────────────────────────────────────────────────
    def _check_dual_acceptance(self, proposal: SettlementProposal) -> None:
        """Mark proposal accepted only when BOTH parties have accepted."""
        if proposal.customer_response == "accept" and proposal.tenant_response == "accept":
            proposal.status = PROPOSAL_ACCEPTED

    async def _execute_settlement_payout(
        self, db: AsyncSession, complaint: CustomerComplaint,
        proposal: SettlementProposal, actor_id: uuid.UUID | None = None,
    ) -> dict | None:
        """MODULE-L5-02 — pay out a dual-accepted settlement.

        The customer is compensated in CREDIT POINTS, never money, and those
        credits are funded by deducting from the provider's canonical
        usage-credit balance. Remedies that carry no amount
        (rework / callback / apology / no_action) move no value and are skipped.

        Never fatal: a payout problem must not undo the parties' agreement — the
        settlement record carries the shortfall for finance to chase.
        """
        from decimal import Decimal
        from app.engines.complaints.constants import (
            MONETARY_REMEDIES, REMEDY_TO_SETTLEMENT_TYPE, SETTLEMENT_DEDUCTION_STRATEGY,
        )
        from app.engines.customer_credits.service import DisputeSettlementService

        remedy = (proposal.proposal_type or "").lower()
        amount = Decimal(str(proposal.proposal_amount or "0"))

        # Belt and braces: money never leaves this way, whoever proposed it.
        if remedy in MONETARY_REMEDIES:
            return None
        if amount <= Decimal("0"):
            return None  # non-monetary remedy — nothing to move

        svc = DisputeSettlementService(db=db, actor_id=actor_id)
        try:
            settlement = await svc.create_settlement(complaint.id, {
                "settlement_type":    REMEDY_TO_SETTLEMENT_TYPE.get(remedy, "customer_service_credit"),
                "settlement_amount":  float(amount),
                "deduction_strategy": SETTLEMENT_DEDUCTION_STRATEGY,
                "reason":             f"Settlement accepted by both parties — {proposal.proposal_type}",
            })
            sid = uuid.UUID(str(settlement["id"]))
            await svc.approve_settlement(sid)
            result = await svc.execute_settlement(sid)
            # bug #42: tell the customer their compensation has been issued.
            try:
                from app.engines.complaints.notifications import notify_customer_complaint
                await notify_customer_complaint(
                    db, complaint,
                    notification_type="complaint.settlement_paid",
                    title=f"Settlement credited — {complaint.complaint_number}",
                    body=f"{amount} credit points have been added to your account as agreed.",
                    severity="success",
                )
            except Exception:
                pass
            return result
        except Exception as exc:
            db.add(ComplaintEvent(
                complaint_id  = complaint.id,
                tenant_id     = complaint.tenant_id,
                actor_type    = ACTOR_SYSTEM,
                actor_user_id = None,
                event_type    = "settlement_payout_failed",
                reason        = f"Settlement payout failed: {exc}",
            ))
            return None

    async def _get_settlement_proposal(
        self, db: AsyncSession, proposal_id: uuid.UUID,
        complaint_id: uuid.UUID | None = None,
    ) -> SettlementProposal:
        r = await db.execute(
            select(SettlementProposal).where(SettlementProposal.id == proposal_id)
        )
        p = r.scalars().first()
        if not p:
            raise ValueError("SETTLEMENT_PROPOSAL_NOT_FOUND")
        # Slice 2F-9: previously a caller who had already proven ownership of
        # `complaint_id` could still supply an unrelated (or foreign-tenant)
        # `proposal_id` -- tenant_respond_to_settlement can trigger a real
        # usage-credit payout on dual acceptance, so a
        # mismatched proposal could be manipulated against the wrong
        # complaint/tenant/customer. Fail closed the same way a genuinely
        # missing proposal would.
        if complaint_id is not None and str(p.complaint_id) != str(complaint_id):
            raise ValueError("SETTLEMENT_PROPOSAL_NOT_FOUND")
        return p

    async def _get_complaint(self, db: AsyncSession, complaint_id: uuid.UUID) -> CustomerComplaint:
        r = await db.execute(select(CustomerComplaint).where(CustomerComplaint.id == complaint_id))
        c = r.scalars().first()
        if not c:
            raise ValueError(ERR_COMPLAINT_NOT_FOUND)
        return c

    async def _get_resolution(
        self, db: AsyncSession, resolution_id: uuid.UUID,
        complaint_id: uuid.UUID | None = None,
    ) -> ComplaintResolution:
        r = await db.execute(select(ComplaintResolution).where(ComplaintResolution.id == resolution_id))
        res = r.scalars().first()
        if not res:
            raise ValueError(ERR_RESOLUTION_NOT_FOUND)
        # Slice 2F-10: mirrors the identical Slice 2F-9 fix for
        # _get_settlement_proposal -- a caller who already proved ownership
        # of `complaint_id` could still supply an unrelated resolution_id
        # (any other customer's or tenant's), letting them accept/reject a
        # foreign resolution while mutating their own complaint's status.
        # Fail closed the same way a genuinely missing resolution would.
        if complaint_id is not None and str(res.complaint_id) != str(complaint_id):
            raise ValueError(ERR_RESOLUTION_NOT_FOUND)
        return res

    async def _transition(
        self,
        db: AsyncSession,
        complaint: CustomerComplaint,
        new_status: str,
        actor_type: str,
        actor_user_id: uuid.UUID,
        reason: str | None = None,
        request_id: str = "—",
    ) -> None:
        old_status = complaint.status
        allowed = ALLOWED_TRANSITIONS_EXT.get(old_status, set())
        if new_status not in allowed:
            raise ValueError(f"{ERR_COMPLAINT_INVALID_TRANSITION}: {old_status} → {new_status}")
        complaint.status = new_status
        await db.flush()
        await self._log_event(
            db, complaint.id, complaint.tenant_id, actor_type, actor_user_id,
            EVT_STATUS_CHANGED, old_status, new_status, None, None,
            reason=reason, request_id=request_id,
        )

    async def _log_event(
        self,
        db: AsyncSession,
        complaint_id: uuid.UUID,
        tenant_id,
        actor_type: str,
        actor_user_id,
        event_type: str,
        old_status: str | None,
        new_status: str | None,
        old_value: dict | None,
        new_value: dict | None,
        reason: str | None = None,
        request_id: str = "—",
    ) -> None:
        ev = ComplaintEvent(
            complaint_id  = complaint_id,
            tenant_id     = tenant_id,
            actor_type    = actor_type,
            actor_user_id = actor_user_id,
            event_type    = event_type,
            old_status    = old_status,
            new_status    = new_status,
            old_value     = old_value,
            new_value     = new_value,
            reason        = reason,
            request_id    = request_id,
        )
        db.add(ev)
        await db.flush()
