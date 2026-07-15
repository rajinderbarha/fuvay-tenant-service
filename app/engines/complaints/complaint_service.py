"""Sprint 25 — Complaint Service (core business logic)."""
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from datetime import timedelta

from app.engines.complaints.constants import (
    STATUS_OPEN, STATUS_AWAITING_PROVIDER, STATUS_AWAITING_CUSTOMER,
    STATUS_UNDER_ADMIN_REVIEW, STATUS_RESOLUTION_PROPOSED, STATUS_REWORK_APPROVED,
    STATUS_REFUND_REQUESTED, STATUS_REFUND_APPROVED, STATUS_REFUND_RECORDED,
    STATUS_REJECTED, STATUS_RESOLVED, STATUS_CLOSED, STATUS_CANCELLED,
    STATUS_TENANT_REVIEW_PENDING, STATUS_TENANT_NO_RESPONSE,
    STATUS_AI_SETTLEMENT_STARTED, STATUS_AI_WAITING_CUSTOMER,
    STATUS_AI_PROPOSAL_SENT, STATUS_AI_SETTLEMENT_ACCEPTED, STATUS_AI_SETTLEMENT_FAILED,
    STATUS_ADMIN_REVIEW_PENDING, STATUS_SETTLEMENT_PROPOSED, STATUS_SETTLED,
    ALLOWED_TRANSITIONS, ALLOWED_TRANSITIONS_EXT, FINAL_STATUSES, VALID_PRIORITIES,
    SLA_ON_TIME, SLA_AT_RISK, SLA_BREACHED, SLA_ESCALATED,
    RES_PROPOSED, RES_CUSTOMER_ACCEPTED, RES_CUSTOMER_REJECTED,
    PROPOSAL_PROPOSED, PROPOSAL_ACCEPTED, PROPOSAL_REJECTED, PROPOSAL_COUNTERED,
    ACTOR_CUSTOMER, ACTOR_PROVIDER, ACTOR_STAFF, ACTOR_ADMIN, ACTOR_SYSTEM, ACTOR_AI,
    VIS_PUBLIC, VIS_ADMIN_ONLY,
    EVT_COMPLAINT_CREATED, EVT_COMPLAINT_ASSIGNED, EVT_PROVIDER_RESPONSE_REQUESTED,
    EVT_PROVIDER_RESPONDED, EVT_CUSTOMER_MESSAGE_ADDED, EVT_ADMIN_MESSAGE_ADDED,
    EVT_EVIDENCE_UPLOADED, EVT_PRIORITY_CHANGED, EVT_STATUS_CHANGED,
    EVT_RESOLUTION_PROPOSED, EVT_RESOLUTION_ACCEPTED, EVT_RESOLUTION_REJECTED,
    EVT_COMPLAINT_REJECTED, EVT_COMPLAINT_RESOLVED, EVT_COMPLAINT_CLOSED,
    EVT_SLA_BREACHED, EVT_SETTLEMENT_PROPOSED, EVT_SETTLEMENT_ACCEPTED,
    EVT_SETTLEMENT_REJECTED, EVT_SETTLEMENT_COUNTERED, EVT_COMPLAINT_SETTLED,
    EVT_SEVERITY_CHANGED, EVT_ADMIN_ESCALATED,
    ERR_COMPLAINT_NOT_FOUND, ERR_COMPLAINT_ACCESS_DENIED, ERR_COMPLAINT_ALREADY_CLOSED,
    ERR_COMPLAINT_INVALID_TRANSITION, ERR_COMPLAINT_REASON_REQUIRED,
    ERR_COMPLAINT_MESSAGE_REQUIRED, ERR_RESOLUTION_NOT_FOUND,
)
from app.engines.complaints.models import (
    CustomerComplaint, ComplaintMessage, ComplaintMedia,
    ComplaintEvent, ComplaintResolution, ComplaintPolicy,
    SettlementProposal, AISettlementSession,
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
        request_id: str = "—",
    ) -> CustomerComplaint:
        # MODULE-L5-02 bug #25: the customer who files a complaint has no tenant
        # (tenant_id is None on customer accounts), so the complaint was persisted
        # with tenant_id = NULL. That made it invisible to the provider whose job
        # it is about — provider_list_complaints filters by tenant_id and
        # provider_get_complaint denies when it does not match — so the entire
        # provider-side complaint flow was dead. Resolve the owning tenant from
        # the linked record when the caller did not supply one.
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

        # SLA deadlines
        now = datetime.now(timezone.utc)
        complaint.tenant_first_response_due_at = now + timedelta(hours=24)
        complaint.ai_escalation_at  = now + timedelta(hours=48)
        complaint.admin_escalation_at = now + timedelta(hours=72)
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
        complaint = await self._get_complaint(db, complaint_id)
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
        await self.get_customer_complaint(db, customer_id, complaint_id)
        resolution = await self._get_resolution(db, resolution_id)
        resolution.status = RES_CUSTOMER_ACCEPTED

        complaint = await self._get_complaint(db, complaint_id)
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
        await self.get_customer_complaint(db, customer_id, complaint_id)
        resolution = await self._get_resolution(db, resolution_id)
        resolution.status = RES_CUSTOMER_REJECTED

        complaint = await self._get_complaint(db, complaint_id)
        await db.flush()
        await self._transition(db, complaint, STATUS_UNDER_ADMIN_REVIEW, ACTOR_CUSTOMER, customer_id,
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
        await self._transition(db, complaint, STATUS_RESOLUTION_PROPOSED, ACTOR_PROVIDER, actor_user_id,
                               request_id=request_id)
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

    async def admin_assign_complaint(
        self,
        db: AsyncSession,
        admin_user_id: uuid.UUID,
        complaint_id: uuid.UUID,
        assignee_id: uuid.UUID,
        request_id: str = "—",
    ) -> CustomerComplaint:
        complaint = await self._get_complaint(db, complaint_id)
        old_assignee = complaint.assigned_admin_user_id
        complaint.assigned_admin_user_id = assignee_id
        await db.flush()
        await self._log_event(db, complaint_id, complaint.tenant_id, ACTOR_ADMIN, admin_user_id,
                              EVT_COMPLAINT_ASSIGNED, None, None,
                              {"assignee_id": str(old_assignee) if old_assignee else None},
                              {"assignee_id": str(assignee_id)}, request_id=request_id)
        await db.commit()
        return complaint

    async def admin_change_priority(
        self,
        db: AsyncSession,
        admin_user_id: uuid.UUID,
        complaint_id: uuid.UUID,
        priority: str,
        reason: str | None = None,
        request_id: str = "—",
    ) -> CustomerComplaint:
        complaint = await self._get_complaint(db, complaint_id)
        old_priority = complaint.priority
        complaint.priority = priority
        await db.flush()
        await self._log_event(db, complaint_id, complaint.tenant_id, ACTOR_ADMIN, admin_user_id,
                              EVT_PRIORITY_CHANGED, None, None,
                              {"priority": old_priority}, {"priority": priority},
                              reason=reason, request_id=request_id)
        await db.commit()
        return complaint

    async def admin_request_provider_response(
        self,
        db: AsyncSession,
        admin_user_id: uuid.UUID,
        complaint_id: uuid.UUID,
        request_id: str = "—",
    ) -> CustomerComplaint:
        complaint = await self._get_complaint(db, complaint_id)
        await self._transition(db, complaint, STATUS_AWAITING_PROVIDER, ACTOR_ADMIN, admin_user_id,
                               request_id=request_id)
        await self._log_event(db, complaint_id, complaint.tenant_id, ACTOR_ADMIN, admin_user_id,
                              EVT_PROVIDER_RESPONSE_REQUESTED, None, None, None, None, request_id=request_id)
        await db.commit()
        return complaint

    async def admin_add_message(
        self,
        db: AsyncSession,
        admin_user_id: uuid.UUID,
        complaint_id: uuid.UUID,
        message_text: str,
        visibility: str = VIS_ADMIN_ONLY,
        request_id: str = "—",
    ) -> ComplaintMessage:
        if not message_text.strip():
            raise ValueError(ERR_COMPLAINT_MESSAGE_REQUIRED)
        complaint = await self._get_complaint(db, complaint_id)
        msg = ComplaintMessage(
            complaint_id   = complaint_id,
            tenant_id      = complaint.tenant_id,
            sender_type    = ACTOR_ADMIN,
            sender_user_id = admin_user_id,
            message_text   = message_text,
            visibility     = visibility,
        )
        db.add(msg)
        await db.flush()
        await self._log_event(db, complaint_id, complaint.tenant_id, ACTOR_ADMIN, admin_user_id,
                              EVT_ADMIN_MESSAGE_ADDED, None, None, None, None, request_id=request_id)
        await db.commit()
        return msg

    async def admin_propose_resolution(
        self,
        db: AsyncSession,
        admin_user_id: uuid.UUID,
        complaint_id: uuid.UUID,
        resolution_type: str,
        description: str,
        customer_visible_notes: str | None = None,
        internal_notes: str | None = None,
        request_id: str = "—",
    ) -> ComplaintResolution:
        complaint = await self._get_complaint(db, complaint_id)
        resolution = ComplaintResolution(
            complaint_id           = complaint_id,
            tenant_id              = complaint.tenant_id,
            resolution_type        = resolution_type,
            status                 = RES_PROPOSED,
            proposed_by_type       = ACTOR_ADMIN,
            proposed_by_user_id    = admin_user_id,
            description            = description,
            customer_visible_notes = customer_visible_notes,
            internal_notes         = internal_notes,
        )
        db.add(resolution)
        await db.flush()
        await self._transition(db, complaint, STATUS_AWAITING_CUSTOMER, ACTOR_ADMIN, admin_user_id,
                               request_id=request_id)
        await self._log_event(db, complaint_id, complaint.tenant_id, ACTOR_ADMIN, admin_user_id,
                              EVT_RESOLUTION_PROPOSED, None, None, None, {"type": resolution_type},
                              request_id=request_id)
        # MODULE-L5-24: it is now the customer's move (accept/reject) — tell them,
        # or the complaint silently waits on someone who doesn't know it's on them.
        from app.engines.complaints.notifications import notify_customer_complaint
        await notify_customer_complaint(
            db, complaint, notification_type="complaint.resolution_proposed",
            title="A resolution was proposed for your complaint",
            body="Your provider or our team proposed a resolution. Review and accept or decline it.")
        await db.commit()
        return resolution

    async def admin_reject_complaint(
        self,
        db: AsyncSession,
        admin_user_id: uuid.UUID,
        complaint_id: uuid.UUID,
        reason: str,
        request_id: str = "—",
    ) -> CustomerComplaint:
        if not reason:
            raise ValueError(ERR_COMPLAINT_REASON_REQUIRED)
        complaint = await self._get_complaint(db, complaint_id)
        await self._transition(db, complaint, STATUS_REJECTED, ACTOR_ADMIN, admin_user_id,
                               reason=reason, request_id=request_id)
        await self._log_event(db, complaint_id, complaint.tenant_id, ACTOR_ADMIN, admin_user_id,
                              EVT_COMPLAINT_REJECTED, None, None, None, {"reason": reason}, request_id=request_id)
        from app.engines.complaints.notifications import notify_customer_complaint
        await notify_customer_complaint(
            db, complaint, notification_type="complaint.rejected",
            title="Your complaint was closed",
            body=f"After review, your complaint was closed: {reason}", severity="warning")
        await db.commit()
        return complaint

    async def admin_resolve_complaint(
        self,
        db: AsyncSession,
        admin_user_id: uuid.UUID,
        complaint_id: uuid.UUID,
        reason: str | None = None,
        request_id: str = "—",
    ) -> CustomerComplaint:
        complaint = await self._get_complaint(db, complaint_id)
        complaint.resolved_at = datetime.now(timezone.utc)
        await db.flush()
        await self._transition(db, complaint, STATUS_RESOLVED, ACTOR_ADMIN, admin_user_id,
                               reason=reason, request_id=request_id)
        await self._log_event(db, complaint_id, complaint.tenant_id, ACTOR_ADMIN, admin_user_id,
                              EVT_COMPLAINT_RESOLVED, None, None, None, None, request_id=request_id)
        from app.engines.complaints.notifications import notify_customer_complaint
        await notify_customer_complaint(
            db, complaint, notification_type="complaint.resolved",
            title="Your complaint has been resolved",
            body="Our team marked your complaint as resolved. Tap to view the details.")
        await db.commit()
        return complaint

    async def close_complaint(
        self,
        db: AsyncSession,
        actor_user_id: uuid.UUID,
        actor_type: str,
        complaint_id: uuid.UUID,
        reason: str | None = None,
        request_id: str = "—",
    ) -> CustomerComplaint:
        complaint = await self._get_complaint(db, complaint_id)
        complaint.closed_at = datetime.now(timezone.utc)
        await db.flush()
        await self._transition(db, complaint, STATUS_CLOSED, actor_type, actor_user_id,
                               reason=reason, request_id=request_id)
        await self._log_event(db, complaint_id, complaint.tenant_id, actor_type, actor_user_id,
                              EVT_COMPLAINT_CLOSED, None, None, None, None, request_id=request_id)
        await db.commit()
        return complaint

    # ── Queries ───────────────────────────────────────────────────────────────
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
        ai_generated: bool = False,
        ai_confidence_score=None,
        request_id: str = "—",
    ) -> SettlementProposal:
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
            ai_generated        = ai_generated,
            ai_confidence_score = ai_confidence_score,
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
        # did NOT make this proposal that it is now awaiting their response. An
        # AI/admin proposal awaits both sides.
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
        proposal = await self._get_settlement_proposal(db, proposal_id)

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
                # Pay the customer in CREDIT POINTS, funded from the PROVIDER's
                # credit wallet and then their security deposit. Never money.
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
        proposal = await self._get_settlement_proposal(db, proposal_id)

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
                # Pay the customer in CREDIT POINTS, funded from the PROVIDER's
                # credit wallet and then their security deposit. Never money.
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

    async def admin_start_ai_settlement(
        self,
        db: AsyncSession,
        admin_user_id: uuid.UUID,
        complaint_id: uuid.UUID,
        request_id: str = "—",
    ) -> AISettlementSession:
        complaint = await self._get_complaint(db, complaint_id)
        from app.engines.complaints.ai_settlement_service import AISettlementService
        ai_svc = AISettlementService()
        session = await ai_svc.start_session(db, complaint, admin_user_id, request_id=request_id)
        complaint.status = STATUS_AI_SETTLEMENT_STARTED
        await db.flush()
        await self._log_event(
            db, complaint_id, complaint.tenant_id, ACTOR_ADMIN, admin_user_id,
            EVT_ADMIN_ESCALATED, None, STATUS_AI_SETTLEMENT_STARTED,
            None, {"session_id": str(session.id)}, request_id=request_id,
        )
        await db.commit()
        return session

    async def admin_finalize_settlement(
        self,
        db: AsyncSession,
        admin_user_id: uuid.UUID,
        complaint_id: uuid.UUID,
        decision: str,
        notes: str | None = None,
        request_id: str = "—",
    ) -> CustomerComplaint:
        complaint = await self._get_complaint(db, complaint_id)
        now = datetime.now(timezone.utc)
        if decision == "settle":
            complaint.status = STATUS_SETTLED
            complaint.settlement_status = PROPOSAL_ACCEPTED
            complaint.resolved_at = now
            evt = EVT_COMPLAINT_SETTLED
        elif decision == "reject":
            complaint.status = STATUS_REJECTED
            evt = EVT_COMPLAINT_REJECTED
        else:
            complaint.status = STATUS_RESOLVED
            evt = EVT_COMPLAINT_RESOLVED

        if notes:
            complaint.internal_admin_notes = notes
        await db.flush()
        await self._log_event(
            db, complaint_id, complaint.tenant_id, ACTOR_ADMIN, admin_user_id,
            evt, None, complaint.status, None, {"decision": decision, "notes": notes},
            request_id=request_id,
        )
        await db.commit()
        return complaint

    async def list_settlement_proposals(
        self, db: AsyncSession, complaint_id: uuid.UUID
    ) -> list[SettlementProposal]:
        r = await db.execute(
            select(SettlementProposal)
            .where(SettlementProposal.complaint_id == complaint_id)
            .order_by(SettlementProposal.created_at)
        )
        return r.scalars().all()

    async def get_ai_session(
        self, db: AsyncSession, complaint_id: uuid.UUID
    ) -> AISettlementSession | None:
        r = await db.execute(
            select(AISettlementSession)
            .where(AISettlementSession.complaint_id == complaint_id)
            .order_by(AISettlementSession.created_at.desc())
        )
        return r.scalars().first()

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
        credits are funded by deducting from the PROVIDER's credit wallet,
        falling back to their security deposit. Remedies that carry no amount
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
        self, db: AsyncSession, proposal_id: uuid.UUID
    ) -> SettlementProposal:
        r = await db.execute(
            select(SettlementProposal).where(SettlementProposal.id == proposal_id)
        )
        p = r.scalars().first()
        if not p:
            raise ValueError("SETTLEMENT_PROPOSAL_NOT_FOUND")
        return p

    async def _get_complaint(self, db: AsyncSession, complaint_id: uuid.UUID) -> CustomerComplaint:
        r = await db.execute(select(CustomerComplaint).where(CustomerComplaint.id == complaint_id))
        c = r.scalars().first()
        if not c:
            raise ValueError(ERR_COMPLAINT_NOT_FOUND)
        return c

    async def _get_resolution(self, db: AsyncSession, resolution_id: uuid.UUID) -> ComplaintResolution:
        r = await db.execute(select(ComplaintResolution).where(ComplaintResolution.id == resolution_id))
        res = r.scalars().first()
        if not res:
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
