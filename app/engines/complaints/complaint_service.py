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
    STATUS_RESOLVED, STATUS_CANCELLED, STATUS_CLOSED,
    STATUS_SETTLED,
    ALLOWED_TRANSITIONS, ALLOWED_TRANSITIONS_EXT, FINAL_STATUSES,
    RESOLVED_OR_FINAL_STATUSES, PROVIDER_ACTION_TIMED_STATUSES, CUSTOMER_TURN_STATUSES,
    PROVIDER_RESOLUTION_TYPES, ERR_RESOLUTION_TYPE_NOT_ALLOWED, ERR_RESOLUTION_AMOUNT_REQUIRED,
    MONETARY_REMEDIES, ERR_SETTLEMENT_MONETARY_NOT_ALLOWED, RES_CANCELLED,
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
from app.exceptions import ServiceOSException

DEFAULT_PROVIDER_RESPONSE_HOURS = 24
DEFAULT_RESOLUTION_HOURS = 72
SAFETY_RESPONSE_HOURS = 1
SAFETY_RESOLUTION_HOURS = 24
DEFAULT_SLA_WARNING_HOURS = 4
# How long past a deadline a breach becomes an escalation.
SLA_ESCALATION_GRACE_HOURS = 24


def _policy_hours(policy, key: str, default: int) -> int:
    """An hours value from a policy row or its dict form, else the default.

    Only a real positive integer counts: the policy columns are NOT NULL, but
    test doubles and hand-built rows can carry anything.
    """
    value = policy.get(key) if isinstance(policy, dict) else getattr(policy, key, None)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return default
    return value


def _as_uuid(value):
    """A UUID or None -- never an arbitrary object inside a SQL comparison."""
    return value if isinstance(value, uuid.UUID) else None


def _as_aware(value):
    if not isinstance(value, datetime):
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


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
        internal_refund_request: bool = False,
        internal_payment_dispute: bool = False,
        created_by_actor_type: str = ACTOR_CUSTOMER,
        created_by_actor_user_id: uuid.UUID | None = None,
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
        # The dedicated refund endpoint creates a provider-owned case as its
        # backing record. It is not a selectable "Report an issue" category;
        # only that internal path may bypass the three public type choices.
        if internal_refund_request and complaint_type != "refund_request":
            raise ValueError(ERR_COMPLAINT_NOT_ELIGIBLE)
        if internal_payment_dispute and complaint_type != "payment_issue":
            raise ValueError(ERR_COMPLAINT_NOT_ELIGIBLE)
        eligibility = await self._eligibility.check_eligible(
            db, customer_id, record_type, record_id,
            # Dedicated refund/payment workflows still pass the canonical
            # ownership, work-started and filing-window checks, but their
            # issue types do not appear in the generic complaint picker.
            complaint_type=None if (internal_refund_request or internal_payment_dispute)
            else complaint_type,
            category_id=category_id,
        )
        if not eligibility["eligible"]:
            raise ValueError(eligibility["reason_code"] or ERR_COMPLAINT_NOT_ELIGIBLE)

        if tenant_id is None:
            tenant_id = await self._resolve_tenant_for_record(db, record_type, record_id)
        is_safety_concern = complaint_type == "safety_concern"
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
            priority             = "critical" if is_safety_concern else "normal",
            severity             = "critical" if is_safety_concern else "medium",
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

        # SLA deadlines. These came from hardcoded 24h, and the admin policy's
        # `default_provider_response_hours`, `default_resolution_hours` and
        # `require_provider_response` were stored but never read. The resolved
        # policy arrives with the eligibility verdict, so no second lookup.
        policy = eligibility.get("policy")
        now = datetime.now(timezone.utc)
        response_required = not (isinstance(policy, dict) and policy.get("require_provider_response") is False)
        # No first-response clock when the provider opened the case (a payment
        # dispute they raised), or when the case is only the backing record of
        # a refund request -- that request carries its own response deadline
        # and penalty, and the complaint clock charged the provider twice for
        # one unanswered refund.
        if created_by_actor_type == ACTOR_PROVIDER or internal_refund_request:
            response_required = False
        if response_required:
            response_hours = (SAFETY_RESPONSE_HOURS if is_safety_concern else
                              _policy_hours(policy, "default_provider_response_hours",
                                            DEFAULT_PROVIDER_RESPONSE_HOURS))
            complaint.tenant_first_response_due_at = now + timedelta(hours=response_hours)
        resolution_hours = _policy_hours(policy, "default_resolution_hours", DEFAULT_RESOLUTION_HOURS)
        if is_safety_concern:
            resolution_hours = min(resolution_hours, SAFETY_RESOLUTION_HOURS)
        complaint.provider_action_due_at = now + timedelta(hours=resolution_hours)
        complaint.sla_status = SLA_ON_TIME

        db.add(complaint)
        await db.flush()
        creator_type = ACTOR_PROVIDER if created_by_actor_type == ACTOR_PROVIDER else ACTOR_CUSTOMER
        creator_id = created_by_actor_user_id or customer_id
        await self._log_event(
            db, complaint.id, tenant_id, creator_type, creator_id,
            EVT_COMPLAINT_CREATED, None, STATUS_OPEN, None, None,
            request_id=request_id,
        )
        # bug #42: tell the provider a customer has raised a complaint about their
        # job — otherwise they never know they need to respond.
        try:
            from app.engines.complaints.notifications import (
                notify_customer_complaint, notify_provider_complaint,
            )
            if creator_type == ACTOR_PROVIDER:
                await notify_customer_complaint(
                    db, complaint,
                    notification_type="complaint.payment_dispute_opened",
                    title=f"Payment review opened — {complaint.complaint_number}",
                    body="Your provider opened a payment discrepancy for this job. Review the case details.",
                    severity="warning",
                )
            else:
                await notify_provider_complaint(
                    db, complaint,
                    notification_type="complaint.filed",
                    title=f"New complaint — {complaint.complaint_number}",
                    body=(complaint.title or complaint.complaint_type.replace("_", " ")).strip()
                         + " — please respond.",
                    severity="critical" if is_safety_concern else "warning",
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
        complaint.provider_response_required = True
        try:
            from app.engines.complaints.notifications import notify_provider_complaint
            await notify_provider_complaint(
                db, complaint,
                notification_type="complaint.customer_message",
                title=f"Customer update — {complaint.complaint_number}",
                body=message_text.strip()[:240], severity="info",
            )
        except Exception:
            pass
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
        resolution_type = getattr(resolution, "resolution_type", None)
        target_status = {
            "rework": STATUS_REWORK_APPROVED,
            "refund": STATUS_REFUND_APPROVED,
        }.get(resolution_type, STATUS_RESOLVED)
        if target_status not in ALLOWED_TRANSITIONS_EXT.get(complaint.status, set()):
            raise ValueError(f"{ERR_COMPLAINT_INVALID_TRANSITION}: {complaint.status} → {target_status}")
        # Only the offer that is still open can be accepted. An expired or
        # superseded offer would otherwise re-run its remedy.
        if getattr(resolution, "status", RES_PROPOSED) != RES_PROPOSED:
            raise ValueError(f"{ERR_COMPLAINT_INVALID_TRANSITION}: resolution is {resolution.status}")

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
        if resolution_type == "refund":
            # Accepting a refund offer used to resolve the case on the spot, so
            # the provider's promise of money never became a refund anyone had
            # to pay. It now creates an approved refund for the offered amount;
            # recording the repayment is what resolves the case.
            from app.engines.complaints.refund_service import RefundRequestService
            await RefundRequestService().create_accepted_offer_refund(
                db, complaint, resolution, request_id=request_id,
            )
            await self._transition(db, complaint, STATUS_REFUND_APPROVED, ACTOR_CUSTOMER, customer_id,
                                   reason="Customer accepted the refund offer", request_id=request_id)
        elif resolution_type == "rework":
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
        try:
            from app.engines.complaints.notifications import notify_provider_complaint
            next_step = {
                "refund": " Record the repayment in Refunds & Warranty to resolve the case.",
                "rework": " Schedule and complete the rework visit in Refunds & Warranty.",
            }.get(resolution_type, "")
            await notify_provider_complaint(
                db, complaint,
                notification_type="complaint.resolution_accepted",
                title=f"Resolution accepted — {complaint.complaint_number}",
                body="The customer accepted the proposed resolution." + next_step,
                severity="success",
            )
        except Exception:
            pass
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
        complaint.provider_response_required = True
        try:
            from app.engines.complaints.notifications import notify_provider_complaint
            await notify_provider_complaint(
                db, complaint,
                notification_type="complaint.resolution_rejected",
                title=f"Resolution rejected — {complaint.complaint_number}",
                body=reason.strip()[:240], severity="warning",
            )
        except Exception:
            pass
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
        # Resolved and settled cases are not open. They were counted as open
        # because only closed/cancelled/rejected were excluded -- and since
        # nothing ever wrote `closed`, every resolved case stayed "open".
        open_rows = [c for c in rows if c.status not in RESOLVED_OR_FINAL_STATUSES]
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
                            else CustomerComplaint.status.notin_(RESOLVED_OR_FINAL_STATUSES))
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
        # Stop the first-response SLA as soon as the provider genuinely replies.
        # The case can remain unresolved (and still affect quality health), but
        # it must not later be charged as if no response was sent.
        await self.check_and_update_sla(db, complaint, request_id=request_id)
        complaint.provider_responded_at = datetime.now(timezone.utc)
        complaint.provider_response_required = False
        await db.flush()
        await self._log_event(db, complaint_id, tenant_id, ACTOR_PROVIDER, actor_user_id,
                              EVT_PROVIDER_RESPONDED, None, None, None, None, request_id=request_id)
        try:
            from app.engines.complaints.notifications import (
                notify_customer_complaint, notify_customer_complaint_channel,
            )
            await notify_customer_complaint(
                db, complaint,
                notification_type="complaint.provider_response",
                title=f"Provider replied — {complaint.complaint_number}",
                body=message_text.strip()[:240], severity="info",
            )
            await notify_customer_complaint_channel(
                db, complaint,
                text=(f"Update on complaint {complaint.complaint_number}:\n\n"
                      f"{message_text.strip()}\n\nSend /complaint to view or reply."),
            )
        except Exception:
            pass
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
        amount=None,
    ) -> ComplaintResolution:
        complaint = await self.provider_get_complaint(db, tenant_id, complaint_id)
        offer_amount = await self._validate_offer(db, complaint, resolution_type, amount)
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
            amount                 = offer_amount,
        )
        db.add(resolution)
        # A proposal is a response. Without this, a provider who went straight
        # to offering a remedy still read as "never responded" and was charged
        # the first-response penalty on a case they had answered.
        if complaint.provider_responded_at is None:
            complaint.provider_responded_at = datetime.now(timezone.utc)
        complaint.provider_response_required = False
        await db.flush()
        await self._log_event(db, complaint_id, tenant_id, ACTOR_PROVIDER, actor_user_id,
                              EVT_RESOLUTION_PROPOSED, None, None, None,
                              {"type": resolution_type,
                               **({"amount": str(offer_amount)} if offer_amount is not None else {})},
                              request_id=request_id)
        # bug #42: the customer must be told a resolution is awaiting their
        # accept/reject — otherwise the complaint sits in resolution_proposed
        # forever with nobody aware it is the customer's move.
        try:
            from app.engines.complaints.notifications import (
                notify_customer_complaint, notify_customer_complaint_channel,
            )
            from app.engines.messaging_gateway.constants import PICK_COMPLAINT, PICKER_SEP
            offered = resolution_type.replace('_', ' ')
            if offer_amount is not None:
                offered = f"{offered} of ₹{offer_amount}"
            await notify_customer_complaint(
                db, complaint,
                notification_type="complaint.resolution_offered",
                title=f"A resolution was offered — {complaint.complaint_number}",
                body=f"The provider offered: {offered}. "
                     "Open the complaint to accept or reject it.",
                severity="info",
            )
            await notify_customer_complaint_channel(
                db, complaint,
                text=(f"Resolution offered for complaint {complaint.complaint_number}:\n\n"
                      f"{resolution_type.replace('_', ' ').title()}\n"
                      f"{description.strip()}"),
                rows=[
                    {
                        "id": PICKER_SEP.join((
                            PICK_COMPLAINT, "accept", str(complaint.id), str(resolution.id),
                        )),
                        "title": "Accept resolution",
                    },
                    {
                        "id": PICKER_SEP.join((
                            PICK_COMPLAINT, "reject", str(complaint.id), str(resolution.id),
                        )),
                        "title": "Reject resolution",
                    },
                ],
                section_title="Complaint resolution",
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
    @staticmethod
    def running_provider_deadline(complaint) -> tuple[datetime | None, str | None]:
        """The provider deadline currently running on `complaint`, if any.

        Two clocks, one at a time. Until the provider first replies or
        proposes, the first-response deadline runs. After that, the resolution
        deadline runs for as long as the case is the provider's move. While it
        waits on the customer, or once it is resolved, no provider clock runs.

        Before the resolution clock existed, a single reply stopped all
        measurement: the case could then sit unresolved forever.
        """
        if complaint.status in RESOLVED_OR_FINAL_STATUSES:
            return None, None
        if complaint.provider_responded_at is None:
            first_due = _as_aware(complaint.tenant_first_response_due_at)
            if first_due is not None:
                return first_due, "first_response"
        if complaint.status in PROVIDER_ACTION_TIMED_STATUSES:
            action_due = _as_aware(getattr(complaint, "provider_action_due_at", None))
            if action_due is not None:
                return action_due, "resolution"
        return None, None

    async def check_and_update_sla(
        self, db: AsyncSession, complaint: CustomerComplaint, request_id: str = "—",
        *, warning_hours: int | None = None,
    ) -> CustomerComplaint:
        """Recompute sla_status against the running provider deadline. Does not commit.

        `sla_status` describes whether the provider is late NOW. A breach is
        not erased from history -- its event and penalty stay -- but a case
        that has moved on to the customer, or into a fresh provider turn, no
        longer reads as breached in the provider's queue.
        """
        due, clock = self.running_provider_deadline(complaint)
        # Historical/imported rows (and a few thin API projections) can carry
        # no concrete deadline; that is "not scheduled", never a breach.
        if due is None:
            return complaint
        warn = (warning_hours if isinstance(warning_hours, int) and warning_hours > 0
                else DEFAULT_SLA_WARNING_HOURS)

        now = datetime.now(timezone.utc)
        old_sla = complaint.sla_status
        if now > due + timedelta(hours=SLA_ESCALATION_GRACE_HOURS):
            complaint.sla_status = SLA_ESCALATED
        elif now > due:
            complaint.sla_status = SLA_BREACHED
        elif now > due - timedelta(hours=warn):
            complaint.sla_status = SLA_AT_RISK
        else:
            complaint.sla_status = SLA_ON_TIME

        if old_sla != complaint.sla_status and complaint.sla_status in (SLA_BREACHED, SLA_ESCALATED):
            await self._log_event(
                db, complaint.id, complaint.tenant_id, ACTOR_SYSTEM, None,
                EVT_SLA_BREACHED, None, None,
                {"sla_status": old_sla},
                {"sla_status": complaint.sla_status, "clock": clock, "due_at": due.isoformat()},
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
                CustomerComplaint.status.notin_(list(RESOLVED_OR_FINAL_STATUSES)),
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
        # A settlement pays credit points or nothing. `_execute_settlement_payout`
        # already refuses to move money for these types, so a "full refund"
        # settlement accepted by both parties settled the case and paid the
        # customer nothing. Refuse it up front; money goes through a refund.
        if (proposal_type or "").lower() in MONETARY_REMEDIES:
            raise ServiceOSException(
                ERR_SETTLEMENT_MONETARY_NOT_ALLOWED,
                "A settlement can offer credit points or a non-monetary remedy. "
                "Offer a refund resolution to return money.",
                status_code=422,
            )
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
                # bug #30b: complaint.status was never advanced, so a fully
                # dual-accepted settlement left the complaint 'open' forever.
                await self._settle(db, complaint, ACTOR_CUSTOMER, customer_id, request_id)
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
                # MODULE-L5-02 bug #30b: complaint.status was never advanced on
                # dual acceptance, so a settlement accepted by BOTH parties left
                # the complaint sitting at 'open' in every queue forever.
                await self._settle(db, complaint, ACTOR_PROVIDER, actor_user_id, request_id)
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

    # ── Status side effects ───────────────────────────────────────────────────
    async def enter_status(self, db: AsyncSession, complaint, new_status: str) -> None:
        """Everything that must happen when a complaint enters `new_status`.

        Called from `_transition` and from the refund/rework services, which
        write the complaint status themselves. Keeping it in one place is what
        keeps the clocks honest: the resolution deadline restarts whenever the
        case comes back to the provider and stops while it waits on the
        customer, and `resolved_at`/`closed_at` are stamped however the case
        got there (accepting a resolution never stamped `resolved_at`, so those
        cases were missing from "Resolved this month").
        """
        now = datetime.now(timezone.utc)
        if new_status in PROVIDER_ACTION_TIMED_STATUSES:
            policy = await self._eligibility.get_complaint_policy(
                db, _as_uuid(complaint.category_id), _as_uuid(complaint.tenant_id),
            )
            hours = _policy_hours(policy, "default_resolution_hours", DEFAULT_RESOLUTION_HOURS)
            complaint.provider_action_due_at = now + timedelta(hours=hours)
            if complaint.provider_responded_at is not None:
                complaint.sla_status = SLA_ON_TIME
        else:
            complaint.provider_action_due_at = None
            if new_status in CUSTOMER_TURN_STATUSES and complaint.provider_responded_at is not None:
                complaint.sla_status = SLA_ON_TIME
        if new_status in (STATUS_RESOLVED, STATUS_SETTLED) and complaint.resolved_at is None:
            complaint.resolved_at = now
        if new_status in FINAL_STATUSES and complaint.closed_at is None:
            complaint.closed_at = now

    async def _settle(self, db: AsyncSession, complaint, actor_type: str, actor_user_id,
                      request_id: str) -> None:
        """Move a dual-accepted settlement's case to `settled`, once."""
        if complaint.status in RESOLVED_OR_FINAL_STATUSES:
            # The case already reached an outcome; the agreement is still
            # honoured by the payout, but the status is not rewound.
            return
        old_status = complaint.status
        complaint.status = STATUS_SETTLED
        await self.enter_status(db, complaint, STATUS_SETTLED)
        await self._log_event(
            db, complaint.id, complaint.tenant_id, actor_type, actor_user_id,
            EVT_STATUS_CHANGED, old_status, STATUS_SETTLED, None, None,
            reason="Settlement accepted by both parties", request_id=request_id,
        )

    async def _validate_offer(self, db: AsyncSession, complaint, resolution_type: str, amount):
        """Refuse an offer the engine cannot carry out. Returns the refund amount.

        `offer-resolution` accepted any string, and the workspace offered
        "partial_refund" and "credit", which nothing modelled -- accepting them
        resolved the case with no remedy. The policy's `allow_rework` and
        `allow_refund_request` switches were stored but never read.
        """
        if resolution_type not in PROVIDER_RESOLUTION_TYPES:
            raise ServiceOSException(
                ERR_RESOLUTION_TYPE_NOT_ALLOWED,
                f"'{resolution_type}' is not a resolution that can be offered.",
                status_code=422,
            )
        policy = await self._eligibility.get_complaint_policy(
            db, _as_uuid(complaint.category_id), _as_uuid(complaint.tenant_id),
        )
        if resolution_type == "rework" and policy is not None and policy.allow_rework is False:
            raise ServiceOSException(ERR_RESOLUTION_TYPE_NOT_ALLOWED,
                                     "Free rework is not offered for this service.", status_code=422)
        if resolution_type != "refund":
            return None
        if policy is not None and policy.allow_refund_request is False:
            raise ServiceOSException(ERR_RESOLUTION_TYPE_NOT_ALLOWED,
                                     "Refunds are not offered for this service.", status_code=422)
        from decimal import Decimal, InvalidOperation
        try:
            value = Decimal(str(amount)) if amount is not None else None
        except (InvalidOperation, ValueError):
            value = None
        if value is None or not value.is_finite() or value <= 0:
            raise ServiceOSException(ERR_RESOLUTION_AMOUNT_REQUIRED,
                                     "Enter the refund amount you are offering.", status_code=422)
        from app.engines.complaints.refund_service import RefundRequestService
        ceiling = await RefundRequestService().eligible_refund_amount(db, complaint)
        if ceiling is not None and value > ceiling:
            raise ServiceOSException(
                "REFUND_AMOUNT_INVALID",
                f"A refund cannot exceed the invoice total of ₹{ceiling}.",
                status_code=422, context={"maximum_eligible_amount": float(ceiling)},
            )
        return value.quantize(Decimal("0.01"))

    # ── Scheduler operations (app/jobs/complaint_sla.py) ─────────────────────
    async def pending_resolution(self, db: AsyncSession, complaint_id) -> ComplaintResolution | None:
        """The offer currently waiting on the customer, if any."""
        rows = await self.list_resolutions(db, complaint_id)
        pending = [r for r in rows if r.status == RES_PROPOSED]
        return pending[-1] if pending else None

    async def remind_customer_to_respond(self, db: AsyncSession, complaint, *, expires_at: datetime,
                                         request_id: str = "job:complaint_sla") -> None:
        """One nudge while a proposed resolution waits on the customer."""
        await self._log_event(
            db, complaint.id, complaint.tenant_id, ACTOR_SYSTEM, None,
            "customer_response_reminder", None, None, None,
            {"expires_at": expires_at.isoformat()}, request_id=request_id,
        )
        try:
            from app.engines.complaints.notifications import (
                notify_customer_complaint, notify_customer_complaint_channel,
            )
            when = expires_at.strftime("%d %b")
            body = (f"Your provider proposed a resolution for {complaint.complaint_number}. "
                    f"Please accept or reject it by {when}, or the case will be closed as resolved.")
            await notify_customer_complaint(
                db, complaint, notification_type="complaint.resolution_reminder",
                title=f"Waiting for your answer — {complaint.complaint_number}",
                body=body, severity="warning",
            )
            await notify_customer_complaint_channel(db, complaint, text=body)
        except Exception:
            pass

    async def expire_unanswered_resolution(self, db: AsyncSession, complaint,
                                           request_id: str = "job:complaint_sla") -> bool:
        """Resolve a case whose proposed resolution the customer never answered.

        Without this a customer who went quiet held the case open forever --
        the provider cannot offer again while one offer is pending, so they had
        no move either. The offer is withdrawn (it can no longer be accepted)
        and the case resolves; the customer can still message until it closes.
        """
        if complaint.status not in CUSTOMER_TURN_STATUSES:
            return False
        from app.engines.complaints.constants import CUSTOMER_RESPONSE_EXPIRY_HOURS
        for resolution in await self.list_resolutions(db, complaint.id):
            if resolution.status == RES_PROPOSED:
                resolution.status = RES_CANCELLED
        await self._transition(
            db, complaint, STATUS_RESOLVED, ACTOR_SYSTEM, None,
            reason=(f"No customer response to the proposed resolution within "
                    f"{CUSTOMER_RESPONSE_EXPIRY_HOURS // 24} days"),
            request_id=request_id,
        )
        try:
            from app.engines.complaints.notifications import (
                notify_customer_complaint, notify_provider_complaint,
            )
            await notify_customer_complaint(
                db, complaint, notification_type="complaint.resolution_expired",
                title=f"Complaint resolved — {complaint.complaint_number}",
                body="We did not hear back about the proposed resolution, so this case is now resolved.",
            )
            await notify_provider_complaint(
                db, complaint, notification_type="complaint.resolution_expired",
                title=f"Complaint resolved — {complaint.complaint_number}",
                body="The customer did not answer your proposed resolution in time. The case is resolved.",
            )
        except Exception:
            pass
        return True

    async def close_resolved(self, db: AsyncSession, complaint,
                             request_id: str = "job:complaint_sla") -> bool:
        """Close a case that reached an outcome. Nothing ever wrote `closed`."""
        from app.engines.complaints.constants import STATUS_REFUND_RECORDED
        if complaint.status == STATUS_REFUND_RECORDED:
            # Recording a refund advances straight to resolved; a row left in
            # refund_recorded predates that and would otherwise never move.
            await self._transition(db, complaint, STATUS_RESOLVED, ACTOR_SYSTEM, None,
                                   reason="Refund recorded", request_id=request_id)
        if complaint.status not in (STATUS_RESOLVED, STATUS_SETTLED):
            return False
        await self._transition(db, complaint, STATUS_CLOSED, ACTOR_SYSTEM, None,
                               reason="Closed automatically after resolution", request_id=request_id)
        return True

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
        await self.enter_status(db, complaint, new_status)
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
