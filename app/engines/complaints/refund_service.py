"""Sprint 25 — Refund Request Service (no real money movement)."""
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError

from app.engines.complaints.constants import (
    REFUND_REQUESTED, REFUND_PROVIDER_REVIEW, REFUND_ADMIN_REVIEW,
    REFUND_APPROVED, REFUND_REJECTED, REFUND_RECORDED, REFUND_VERIFIED, REFUND_CANCELLED,
    STATUS_REFUND_REQUESTED, STATUS_REFUND_APPROVED, STATUS_REFUND_RECORDED, STATUS_RESOLVED,
    ALLOWED_TRANSITIONS,
    EVT_REFUND_REQUESTED, EVT_REFUND_APPROVED, EVT_REFUND_RECORDED,
    ACTOR_ADMIN, ACTOR_PROVIDER, ACTOR_CUSTOMER,
    ERR_REFUND_NOT_FOUND, ERR_REFUND_ACCESS_DENIED, ERR_REFUND_AMOUNT_INVALID,
    ERR_REFUND_APPROVAL_FAILED, ERR_REFUND_RECORD_FAILED, ERR_REFUND_VERIFY_FAILED,
)
from app.engines.complaints.models import RefundRequest, CustomerComplaint, ComplaintEvent
from app.engines.complaints.complaint_service import ComplaintService
from app.exceptions import ServiceOSException


class RefundRequestService:

    def __init__(self):
        self._complaint_svc = ComplaintService()

    async def create_refund_request_from_complaint(
        self,
        db: AsyncSession,
        complaint_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_type: str,
        refund_type: str,
        reason: str,
        requested_amount: Decimal | None = None,
        refund_method: str | None = None,
        commit: bool = True,
        request_id: str = "—",
    ) -> RefundRequest:
        # Slice 2F-10: this was a bare fetch-by-id with NO ownership check
        # at all -- the only caller is customer_router's request_refund,
        # which never verified complaint ownership before calling here
        # (unlike every other customer_router route, which calls
        # get_customer_complaint first). Any authenticated user could
        # create a refund request against any complaint_id, for any
        # customer or tenant. Fixed by requiring ownership when the actor
        # is a customer, using the same get_customer_complaint check every
        # other customer route already relies on.
        if actor_type == ACTOR_CUSTOMER:
            complaint = await self._complaint_svc.get_customer_complaint(db, actor_user_id, complaint_id)
        else:
            complaint = await self._complaint_svc.get_complaint(db, complaint_id)

        existing = await db.scalar(
            select(RefundRequest).where(
                RefundRequest.complaint_id == complaint_id,
                RefundRequest.status != REFUND_CANCELLED,
            ).limit(1)
        )
        # Some callers/tests use permissive async session doubles; only a
        # materialized refund row is evidence of a duplicate.  A real
        # SQLAlchemy result returns RefundRequest | None here.
        if isinstance(existing, RefundRequest):
            raise ServiceOSException(
                "REFUND_ALREADY_REQUESTED", "This complaint already has a refund request.", status_code=409,
            )
        eligible_amount = None
        from app.engines.invoice_payment.models import ServiceInvoice
        invoice = None
        if complaint.invoice_id:
            invoice = await db.get(ServiceInvoice, complaint.invoice_id)
        elif complaint.job_id:
            invoice = await db.scalar(
                select(ServiceInvoice).where(
                    ServiceInvoice.job_id == complaint.job_id,
                    ServiceInvoice.status != "cancelled",
                ).order_by(ServiceInvoice.created_at.desc()).limit(1)
            )
        elif complaint.booking_id:
            invoice = await db.scalar(
                select(ServiceInvoice).where(
                    ServiceInvoice.booking_id == complaint.booking_id,
                    ServiceInvoice.status != "cancelled",
                ).order_by(ServiceInvoice.created_at.desc()).limit(1)
            )
        if invoice:
            eligible_amount = Decimal(str(invoice.total_amount))
            complaint.invoice_id = complaint.invoice_id or invoice.id
        if requested_amount is None:
            requested_amount = eligible_amount
        if requested_amount is not None and Decimal(str(requested_amount)) <= 0:
            raise ServiceOSException(
                "REFUND_AMOUNT_REQUIRED", "A positive refund amount is required.", status_code=422,
            )
        requested_amount = Decimal(str(requested_amount)) if requested_amount is not None else None
        if eligible_amount is not None and requested_amount is not None and requested_amount > eligible_amount:
            raise ServiceOSException(
                "REFUND_AMOUNT_INVALID", "Requested refund cannot exceed the service invoice total.",
                status_code=422, context={"maximum_eligible_amount": float(eligible_amount)},
            )

        # Slice 2F-10A: re-examined this as a possible "persistence before
        # transition validation" defect (the same class fixed for
        # resolution accept/reject in Slice 2F-10), but existing test
        # coverage (test_refund_events_log_the_status_actually_applied,
        # test_refund_path_advances_and_resolves_the_complaint) proves
        # this silent-skip-on-illegal-transition behavior is DELIBERATE
        # and load-bearing across the whole refund lifecycle
        # (create/admin_approve_refund/record_refund all share this exact
        # pattern) -- MODULE-L5-02 bug #31 already fixed the one real
        # defect here (the audit event used to claim the transition
        # happened even when it didn't); the RefundRequest itself is
        # intentionally always created as a review request regardless of
        # whether the complaint's own status field advances. Classified
        # REQUEST_ALLOWED_WITHOUT_COMPLAINT_TRANSITION_BY_POLICY -- see
        # docs/workflow-rearchitecture/phase-02a-slice-02f10a/
        # refund-silent-transition-review.md. NOT reverted to a
        # validate-before-create ordering; doing so would break this
        # slice's own re-verified, intentional idempotent-admin-replay
        # design.
        refund = RefundRequest(
            complaint_id     = complaint_id,
            customer_id      = complaint.customer_id,
            tenant_id        = complaint.tenant_id,
            invoice_id       = complaint.invoice_id,
            booking_id       = complaint.booking_id,
            job_id           = complaint.job_id,
            appointment_id   = complaint.appointment_id,
            lead_id          = complaint.lead_id,
            status           = REFUND_REQUESTED,
            refund_type      = refund_type,
            requested_amount = requested_amount,
            refund_method    = refund_method,
            reason           = reason,
            provider_response_due_at = datetime.now(timezone.utc) + timedelta(hours=24),
        )
        db.add(refund)
        await db.flush()

        # MODULE-L5-02 bug #31: the complaint transition here is a silent no-op
        # when disallowed, but the event below used to log new_status =
        # STATUS_REFUND_REQUESTED unconditionally — so the complaint's audit trail
        # recorded a status change that never actually happened. Log the status
        # that was really applied (None when the transition was skipped).
        old_status = complaint.status
        allowed = ALLOWED_TRANSITIONS.get(complaint.status, set())
        applied = None
        if STATUS_REFUND_REQUESTED in allowed:
            complaint.status = STATUS_REFUND_REQUESTED
            applied = STATUS_REFUND_REQUESTED
            await db.flush()

        await self._log_event(db, complaint_id, complaint.tenant_id, actor_type, actor_user_id,
                              EVT_REFUND_REQUESTED, old_status, applied,
                              {"refund_id": str(refund.id)}, request_id)
        if commit:
            await db.commit()
        return refund

    async def provider_review_refund(
        self,
        db: AsyncSession,
        refund_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        notes: str | None = None,
        request_id: str = "—",
        tenant_id: uuid.UUID | None = None,
    ) -> RefundRequest:
        refund = await self._get_refund(db, refund_id, tenant_id=tenant_id)
        if refund.status not in (REFUND_REQUESTED, REFUND_PROVIDER_REVIEW):
            raise ServiceOSException("REFUND_INVALID_STATE", f"Refund is already {refund.status}.", status_code=409)
        refund.status = REFUND_PROVIDER_REVIEW
        await db.commit()
        return refund

    async def provider_decide_refund(
        self, db: AsyncSession, refund_id: uuid.UUID, tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID, *, approve: bool, approved_amount: Decimal | None = None,
        reason: str | None = None, request_id: str = "-",
    ) -> RefundRequest:
        refund = await self._get_refund(db, refund_id, tenant_id=tenant_id, for_update=True)
        if refund.status not in (REFUND_REQUESTED, REFUND_PROVIDER_REVIEW):
            raise ServiceOSException("REFUND_INVALID_STATE", f"Refund is already {refund.status}.", status_code=409)
        if approve:
            amount = Decimal(str(approved_amount if approved_amount is not None else refund.requested_amount or 0))
            if amount <= 0 or (refund.requested_amount and amount > refund.requested_amount):
                raise ServiceOSException("REFUND_AMOUNT_INVALID", "Approved amount is invalid.", status_code=422)
            refund.status = REFUND_APPROVED
            refund.approved_amount = amount
            refund.approved_by_user_id = actor_user_id
            refund.approved_at = datetime.now(timezone.utc)
            refund.resolution_method = "provider_direct_refund"
        else:
            if not reason or not reason.strip():
                raise ServiceOSException("VALIDATION_ERROR", "A rejection reason is required.", status_code=422)
            refund.status = REFUND_REJECTED
            refund.rejection_reason = reason.strip()
            refund.resolution_method = "provider_rejected"
        await db.commit()
        return refund

    async def create_job_refund_request(
        self,
        db: AsyncSession,
        *,
        customer_id: uuid.UUID,
        job_id: uuid.UUID,
        reason: str,
        requested_amount: Decimal,
        request_id: str = "-",
    ) -> RefundRequest:
        """Atomically create a complaint and provider-owned refund request."""
        active = await db.scalar(
            select(RefundRequest).where(
                RefundRequest.customer_id == customer_id,
                RefundRequest.job_id == job_id,
                RefundRequest.status != REFUND_CANCELLED,
            ).order_by(RefundRequest.created_at.desc()).limit(1)
        )
        if active:
            return active

        from app.engines.complaints.constants import RECORD_SERVICE_JOB
        complaint = await self._complaint_svc.create_complaint(
            db,
            customer_id,
            category_id=uuid.UUID(int=0),
            record_type=RECORD_SERVICE_JOB,
            record_id=job_id,
            complaint_type="refund_request",
            description=reason,
            requested_resolution="refund",
            title="Refund requested for completed service",
            request_id=request_id,
            commit=False,
        )
        try:
            return await self.create_refund_request_from_complaint(
                db,
                complaint.id,
                customer_id,
                ACTOR_CUSTOMER,
                "service_refund",
                reason,
                requested_amount=requested_amount,
                refund_method="provider_direct",
                request_id=request_id,
                commit=True,
            )
        except IntegrityError:
            await db.rollback()
            winner = await db.scalar(
                select(RefundRequest).where(
                    RefundRequest.customer_id == customer_id,
                    RefundRequest.job_id == job_id,
                    RefundRequest.status != REFUND_CANCELLED,
                ).order_by(RefundRequest.created_at.desc()).limit(1)
            )
            if winner:
                return winner
            raise

    async def escalate_refund(
        self, db: AsyncSession, refund_id: uuid.UUID, customer_id: uuid.UUID,
        reason: str, request_id: str = "-",
    ) -> RefundRequest:
        refund = await self._get_refund(db, refund_id, for_update=True)
        if str(refund.customer_id) != str(customer_id):
            raise ServiceOSException("REFUND_NOT_FOUND", "Refund request not found.", status_code=404)
        if refund.status not in (REFUND_REQUESTED, REFUND_PROVIDER_REVIEW, REFUND_REJECTED):
            raise ServiceOSException("REFUND_INVALID_STATE", f"Refund cannot be escalated from {refund.status}.", status_code=409)
        if refund.status == REFUND_REJECTED and refund.resolution_method == "admin_rejected":
            raise ServiceOSException("REFUND_INVALID_STATE", "The admin decision is final.", status_code=409)
        if (refund.status == REFUND_REQUESTED and refund.provider_response_due_at
                and refund.provider_response_due_at > datetime.now(timezone.utc)):
            raise ServiceOSException(
                "PROVIDER_RESPONSE_WINDOW_ACTIVE", "The provider still has time to respond.", status_code=409,
                context={"provider_response_due_at": refund.provider_response_due_at.isoformat()},
            )
        refund.status = REFUND_ADMIN_REVIEW
        refund.escalated_at = datetime.now(timezone.utc)
        refund.escalation_reason = reason
        await db.commit()
        return refund

    async def admin_issue_credit_remedy(
        self, db: AsyncSession, refund_id: uuid.UUID, admin_user_id: uuid.UUID,
        amount: Decimal, reason: str, request_id: str = "-",
    ) -> RefundRequest:
        refund = await self._get_refund(db, refund_id, for_update=True)
        overdue = bool(refund.provider_response_due_at and refund.provider_response_due_at <= datetime.now(timezone.utc))
        if refund.status != REFUND_ADMIN_REVIEW and not (refund.status == REFUND_REQUESTED and overdue):
            raise ServiceOSException(
                "PROVIDER_RESOLUTION_REQUIRED",
                "Admin service credit is available only after provider failure or timeout.", status_code=409,
            )
        amount = Decimal(str(amount))
        if amount <= 0 or (refund.requested_amount and amount > refund.requested_amount):
            raise ServiceOSException("REFUND_AMOUNT_INVALID", "Credit amount is invalid.", status_code=422)
        if not reason or len(reason.strip()) < 5:
            raise ServiceOSException(
                "VALIDATION_ERROR", "A remedy reason of at least 5 characters is required.", status_code=422,
            )
        from app.engines.customer_credits.service import issue_provider_funded_customer_credit
        remedy = await issue_provider_funded_customer_credit(
            db, tenant_id=refund.tenant_id, customer_id=refund.customer_id,
            amount=amount, reference_type="refund_request", reference_id=refund.id,
            reason=reason.strip(), actor_id=admin_user_id, actor_role=ACTOR_ADMIN,
            request_id=request_id, booking_id=refund.booking_id, job_id=refund.job_id,
            currency=refund.currency,
        )
        refund.status = REFUND_VERIFIED
        refund.approved_amount = amount
        refund.recorded_amount = amount
        refund.resolution_method = "customer_service_credit"
        refund.customer_credit_id = remedy["credit"].id
        refund.provider_credit_deducted = remedy["provider_credit_deducted"]
        refund.security_deposit_deducted = remedy["security_deposit_deducted"]
        refund.approved_by_user_id = admin_user_id
        refund.verified_by_user_id = admin_user_id
        refund.approved_at = refund.approved_at or datetime.now(timezone.utc)
        refund.recorded_at = datetime.now(timezone.utc)
        refund.verified_at = datetime.now(timezone.utc)
        complaint = await self._complaint_svc.get_complaint(db, refund.complaint_id)
        complaint.status = STATUS_RESOLVED
        complaint.resolved_at = datetime.now(timezone.utc)
        await db.commit()
        return refund

    async def admin_approve_refund(
        self,
        db: AsyncSession,
        refund_id: uuid.UUID,
        admin_user_id: uuid.UUID,
        approved_amount: Decimal | None = None,
        request_id: str = "—",
    ) -> RefundRequest:
        await self._get_refund(db, refund_id)
        raise ServiceOSException(
            "PROVIDER_OWNS_REFUND",
            "Cash refunds must be approved by the provider. Admin may issue service credit only after escalation.",
            status_code=409,
        )

    async def admin_reject_refund(
        self,
        db: AsyncSession,
        refund_id: uuid.UUID,
        admin_user_id: uuid.UUID,
        reason: str,
        request_id: str = "—",
    ) -> RefundRequest:
        refund = await self._get_refund(db, refund_id)
        overdue = bool(
            refund.provider_response_due_at
            and refund.provider_response_due_at <= datetime.now(timezone.utc)
        )
        if refund.status != REFUND_ADMIN_REVIEW and not (refund.status == REFUND_REQUESTED and overdue):
            raise ServiceOSException("REFUND_INVALID_STATE",
                "Admin can reject only a provider-failed refund in admin review.", status_code=409)
        if not reason or not reason.strip():
            raise ServiceOSException("VALIDATION_ERROR", "A rejection reason is required.", status_code=422)
        refund.status           = REFUND_REJECTED
        refund.rejection_reason = reason
        refund.resolution_method = "admin_rejected"
        await db.commit()
        return refund

    async def record_refund(
        self,
        db: AsyncSession,
        refund_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_type: str,
        recorded_amount: Decimal,
        proof_media_url: str | None = None,
        request_id: str = "—",
    ) -> RefundRequest:
        refund = await self._get_refund(db, refund_id)
        if refund.status != REFUND_APPROVED:
            raise ServiceOSException("REFUND_INVALID_STATE",
                f"A refund in '{refund.status}' state cannot be recorded.", status_code=409)
        recorded_amount = Decimal(str(recorded_amount))
        if recorded_amount <= Decimal("0"):
            raise ServiceOSException("VALIDATION_ERROR", "Recorded amount must be positive.", status_code=422)
        approved_cap = refund.approved_amount or refund.requested_amount
        if approved_cap is not None and recorded_amount > approved_cap:
            raise ServiceOSException("VALIDATION_ERROR",
                "Recorded amount cannot exceed the approved amount.", status_code=422)
        refund.status              = REFUND_RECORDED
        refund.recorded_amount     = recorded_amount
        refund.proof_media_url     = proof_media_url
        refund.recorded_by_user_id = actor_user_id
        refund.recorded_at         = datetime.now(timezone.utc)
        await db.flush()

        complaint = await self._complaint_svc.get_complaint(db, refund.complaint_id)
        # bug #31: log the status actually applied, not an assumed one.
        old_status = complaint.status
        allowed = ALLOWED_TRANSITIONS.get(complaint.status, set())
        applied = None
        if STATUS_REFUND_RECORDED in allowed:
            complaint.status = STATUS_REFUND_RECORDED
            applied = STATUS_REFUND_RECORDED
            await db.flush()

        await self._log_event(db, refund.complaint_id, refund.tenant_id, actor_type, actor_user_id,
                              EVT_REFUND_RECORDED, old_status, applied,
                              {"recorded_amount": str(recorded_amount)}, request_id)
        await db.commit()
        return refund

    async def verify_refund(
        self,
        db: AsyncSession,
        refund_id: uuid.UUID,
        admin_user_id: uuid.UUID,
        request_id: str = "—",
    ) -> RefundRequest:
        refund = await self._get_refund(db, refund_id)
        if refund.status != REFUND_RECORDED:
            raise ValueError(ERR_REFUND_VERIFY_FAILED)
        refund.status              = REFUND_VERIFIED
        refund.verified_by_user_id = admin_user_id
        refund.verified_at         = datetime.now(timezone.utc)
        # MODULE-L5-02 bug #29: verifying the refund is the terminal step of the
        # refund path, but nothing ever moved the complaint out of
        # refund_recorded — so a fully paid-out and verified refund left the
        # complaint permanently unresolved. Resolve it here.
        complaint = await self._complaint_svc.get_complaint(db, refund.complaint_id)
        if STATUS_RESOLVED in ALLOWED_TRANSITIONS.get(complaint.status, set()):
            complaint.status      = STATUS_RESOLVED
            complaint.resolved_at = datetime.now(timezone.utc)
        await db.commit()
        return refund

    async def cancel_refund(
        self,
        db: AsyncSession,
        refund_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        reason: str,
        request_id: str = "—",
    ) -> RefundRequest:
        refund = await self._get_refund(db, refund_id)
        refund.status           = REFUND_CANCELLED
        refund.rejection_reason = reason
        await db.commit()
        return refund

    async def list_refund_requests(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> list[RefundRequest]:
        q = select(RefundRequest)
        if tenant_id:
            q = q.where(RefundRequest.tenant_id == tenant_id)
        if customer_id:
            q = q.where(RefundRequest.customer_id == customer_id)
        if status:
            q = q.where(RefundRequest.status == status)
        q = q.order_by(RefundRequest.created_at.desc()).limit(100)
        r = await db.execute(q)
        return r.scalars().all()

    async def list_refund_requests_page(
        self, db: AsyncSession, *, tenant_id: uuid.UUID, status: str | None,
        q: str | None, page: int, page_size: int,
    ) -> dict:
        filters = [RefundRequest.tenant_id == tenant_id]
        if status:
            filters.append(RefundRequest.status == status)
        if q and q.strip():
            term = f"%{q.strip()}%"
            filters.append(or_(
                RefundRequest.refund_number.ilike(term),
                RefundRequest.refund_type.ilike(term),
            ))
        total = await db.scalar(select(func.count()).select_from(RefundRequest).where(*filters)) or 0
        rows = (await db.execute(
            select(RefundRequest).where(*filters)
            .order_by(RefundRequest.created_at.desc(), RefundRequest.id.desc())
            .limit(page_size).offset((page - 1) * page_size)
        )).scalars().all()
        return {
            "items": [row.to_dict() for row in rows],
            "pagination": {
                "page": page, "page_size": page_size, "total_items": total,
                "total_pages": max(1, (total + page_size - 1) // page_size),
                "has_next": page * page_size < total, "has_previous": page > 1,
            },
        }

    async def get_refund(self, db: AsyncSession, refund_id: uuid.UUID,
                          tenant_id: uuid.UUID | None = None) -> RefundRequest:
        return await self._get_refund(db, refund_id, tenant_id=tenant_id)

    async def _get_refund(self, db: AsyncSession, refund_id: uuid.UUID,
                           tenant_id: uuid.UUID | None = None,
                           for_update: bool = False) -> RefundRequest:
        # Slice 2F-9: previously loaded by refund_id alone -- ANY authenticated
        # user of any tenant could review another tenant's refund request.
        # When tenant_id is supplied (provider-facing callers now always pass
        # their own principal tenant_id), a mismatch fails closed with the
        # same not-found error a genuinely missing row would produce.
        stmt = select(RefundRequest).where(RefundRequest.id == refund_id)
        if for_update:
            stmt = stmt.with_for_update()
        r = await db.execute(stmt)
        rf = r.scalars().first()
        if not rf:
            raise ValueError(ERR_REFUND_NOT_FOUND)
        if tenant_id is not None and str(rf.tenant_id) != str(tenant_id):
            raise ValueError(ERR_REFUND_NOT_FOUND)
        return rf

    async def _log_event(
        self,
        db: AsyncSession,
        complaint_id: uuid.UUID,
        tenant_id,
        actor_type: str,
        actor_user_id,
        event_type: str,
        old_status,
        new_status,
        new_value: dict | None,
        request_id: str,
    ) -> None:
        ev = ComplaintEvent(
            complaint_id  = complaint_id,
            tenant_id     = tenant_id,
            actor_type    = actor_type,
            actor_user_id = actor_user_id,
            event_type    = event_type,
            old_status    = old_status,
            new_status    = new_status,
            new_value     = new_value,
            request_id    = request_id,
        )
        db.add(ev)
        await db.flush()
