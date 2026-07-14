"""Sprint 25 — Refund Request Service (no real money movement)."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
        request_id: str = "—",
    ) -> RefundRequest:
        complaint = await self._complaint_svc.get_complaint(db, complaint_id)
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
        )
        db.add(refund)
        await db.flush()

        allowed = ALLOWED_TRANSITIONS.get(complaint.status, set())
        if STATUS_REFUND_REQUESTED in allowed:
            complaint.status = STATUS_REFUND_REQUESTED
            await db.flush()

        await self._log_event(db, complaint_id, complaint.tenant_id, actor_type, actor_user_id,
                              EVT_REFUND_REQUESTED, None, STATUS_REFUND_REQUESTED,
                              {"refund_id": str(refund.id)}, request_id)
        await db.commit()
        return refund

    async def provider_review_refund(
        self,
        db: AsyncSession,
        refund_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        notes: str | None = None,
        request_id: str = "—",
    ) -> RefundRequest:
        refund = await self._get_refund(db, refund_id)
        refund.status = REFUND_PROVIDER_REVIEW
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
        refund = await self._get_refund(db, refund_id)
        if approved_amount is not None:
            if refund.requested_amount and approved_amount > refund.requested_amount:
                raise ValueError(ERR_REFUND_AMOUNT_INVALID)
        refund.status              = REFUND_APPROVED
        refund.approved_amount     = approved_amount or refund.requested_amount
        refund.approved_by_user_id = admin_user_id
        refund.approved_at         = datetime.now(timezone.utc)
        await db.flush()

        complaint = await self._complaint_svc.get_complaint(db, refund.complaint_id)
        allowed = ALLOWED_TRANSITIONS.get(complaint.status, set())
        if STATUS_REFUND_APPROVED in allowed:
            complaint.status = STATUS_REFUND_APPROVED
            await db.flush()

        await self._log_event(db, refund.complaint_id, refund.tenant_id, ACTOR_ADMIN, admin_user_id,
                              EVT_REFUND_APPROVED, None, STATUS_REFUND_APPROVED,
                              {"approved_amount": str(refund.approved_amount)}, request_id)
        await db.commit()
        return refund

    async def admin_reject_refund(
        self,
        db: AsyncSession,
        refund_id: uuid.UUID,
        admin_user_id: uuid.UUID,
        reason: str,
        request_id: str = "—",
    ) -> RefundRequest:
        refund = await self._get_refund(db, refund_id)
        refund.status           = REFUND_REJECTED
        refund.rejection_reason = reason
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
        refund.status              = REFUND_RECORDED
        refund.recorded_amount     = recorded_amount
        refund.proof_media_url     = proof_media_url
        refund.recorded_by_user_id = actor_user_id
        refund.recorded_at         = datetime.now(timezone.utc)
        await db.flush()

        complaint = await self._complaint_svc.get_complaint(db, refund.complaint_id)
        allowed = ALLOWED_TRANSITIONS.get(complaint.status, set())
        if STATUS_REFUND_RECORDED in allowed:
            complaint.status = STATUS_REFUND_RECORDED
            await db.flush()

        await self._log_event(db, refund.complaint_id, refund.tenant_id, actor_type, actor_user_id,
                              EVT_REFUND_RECORDED, None, STATUS_REFUND_RECORDED,
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

    async def get_refund(self, db: AsyncSession, refund_id: uuid.UUID) -> RefundRequest:
        return await self._get_refund(db, refund_id)

    async def _get_refund(self, db: AsyncSession, refund_id: uuid.UUID) -> RefundRequest:
        r = await db.execute(select(RefundRequest).where(RefundRequest.id == refund_id))
        rf = r.scalars().first()
        if not rf:
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
