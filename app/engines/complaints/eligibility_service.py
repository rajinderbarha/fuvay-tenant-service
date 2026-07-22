"""Sprint 25 — Complaint Eligibility Service."""
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.engines.complaints.constants import (
    ELIGIBLE_STATUSES, VALID_RECORD_TYPES,
    RECORD_SERVICE_BOOKING, RECORD_SERVICE_JOB, RECORD_SERVICE_INVOICE,
    RECORD_COACHING_APPOINTMENT, RECORD_REAL_ESTATE_LEAD, RECORD_CUSTOMER_REVIEW,
    STATUS_OPEN, STATUS_AWAITING_PROVIDER, STATUS_AWAITING_CUSTOMER,
    STATUS_UNDER_ADMIN_REVIEW, STATUS_RESOLUTION_PROPOSED,
    ERR_COMPLAINT_INVALID_RECORD_TYPE, ERR_COMPLAINT_RECORD_NOT_FOUND,
    ERR_COMPLAINT_NOT_ELIGIBLE, ERR_COMPLAINT_WINDOW_EXPIRED,
    ERR_COMPLAINT_DUPLICATE_OPEN, ERR_COMPLAINT_ACCESS_DENIED,
)
from app.engines.complaints.models import CustomerComplaint, ComplaintPolicy

OPEN_STATUSES = {
    STATUS_OPEN, STATUS_AWAITING_PROVIDER, STATUS_AWAITING_CUSTOMER,
    STATUS_UNDER_ADMIN_REVIEW, STATUS_RESOLUTION_PROPOSED,
}


class ComplaintEligibilityService:

    async def check_eligible(
        self,
        db: AsyncSession,
        customer_id: uuid.UUID,
        record_type: str,
        record_id: uuid.UUID,
        complaint_type: str | None = None,
        category_id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
    ) -> dict:
        if record_type not in VALID_RECORD_TYPES:
            raise ValueError(ERR_COMPLAINT_INVALID_RECORD_TYPE)

        record = await self._fetch_record(db, record_type, record_id)
        if not record:
            raise ValueError(ERR_COMPLAINT_RECORD_NOT_FOUND)

        status = getattr(record, "status", None)
        eligible_set = ELIGIBLE_STATUSES.get(record_type, set())
        if status not in eligible_set:
            return {"eligible": False, "reason": f"Record status '{status}' not eligible for complaint.",
                    "reason_code": ERR_COMPLAINT_NOT_ELIGIBLE}

        if not await self._customer_owns_record(db, customer_id, record_type, record):
            return {"eligible": False, "reason": "Not the customer for this record.",
                    "reason_code": ERR_COMPLAINT_ACCESS_DENIED}

        policy = await self.get_complaint_policy(db, category_id, tenant_id)
        window_hours = policy.complaint_window_hours if policy else 168

        created_at = getattr(record, "created_at", None)
        if created_at:
            if isinstance(created_at, datetime) and created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - created_at
            if age > timedelta(hours=window_hours):
                return {"eligible": False, "reason": f"Complaint window of {window_hours}h has expired.",
                        "reason_code": ERR_COMPLAINT_WINDOW_EXPIRED}

        allow_dup = policy.allow_duplicate_open_complaints if policy else False
        if not allow_dup and complaint_type:
            has_open = await self.check_duplicate_open_complaint(
                db, customer_id, record_type, record_id, complaint_type
            )
            if has_open:
                return {"eligible": False, "reason": "An open complaint already exists for this record.",
                        "reason_code": ERR_COMPLAINT_DUPLICATE_OPEN}

        return {
            "eligible": True,
            "reason":   None,
            "reason_code": None,
            "policy":   policy.to_dict() if policy else None,
        }

    async def get_complaint_policy(
        self,
        db: AsyncSession,
        category_id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
    ) -> ComplaintPolicy | None:
        if category_id:
            r = await db.execute(
                select(ComplaintPolicy).where(
                    ComplaintPolicy.category_id == category_id,
                    ComplaintPolicy.is_active    == True,
                )
            )
            p = r.scalars().first()
            if p:
                return p
        r = await db.execute(
            select(ComplaintPolicy).where(
                ComplaintPolicy.category_id == None,
                ComplaintPolicy.tenant_id   == None,
                ComplaintPolicy.policy_key  == "default",
                ComplaintPolicy.is_active   == True,
            )
        )
        return r.scalars().first()

    async def check_duplicate_open_complaint(
        self,
        db: AsyncSession,
        customer_id: uuid.UUID,
        record_type: str,
        record_id: uuid.UUID,
        complaint_type: str,
    ) -> bool:
        r = await db.execute(
            select(CustomerComplaint).where(
                CustomerComplaint.customer_id    == customer_id,
                CustomerComplaint.record_type    == record_type,
                CustomerComplaint.record_id      == record_id,
                CustomerComplaint.complaint_type == complaint_type,
                CustomerComplaint.status.in_(list(OPEN_STATUSES)),
            )
        )
        return r.scalars().first() is not None

    async def _fetch_record(self, db: AsyncSession, record_type: str, record_id: uuid.UUID):
        try:
            if record_type == RECORD_SERVICE_BOOKING:
                from app.engines.final_records.models import ServiceBooking
                r = await db.execute(select(ServiceBooking).where(ServiceBooking.id == record_id))
                return r.scalars().first()
            if record_type == RECORD_SERVICE_JOB:
                from app.engines.final_records.models import ServiceJob
                r = await db.execute(select(ServiceJob).where(ServiceJob.id == record_id))
                return r.scalars().first()
            if record_type == RECORD_COACHING_APPOINTMENT:
                from app.engines.final_records.models import CoachingAppointment
                r = await db.execute(select(CoachingAppointment).where(CoachingAppointment.id == record_id))
                return r.scalars().first()
            if record_type == RECORD_REAL_ESTATE_LEAD:
                from app.engines.final_records.models import RealEstateLead
                r = await db.execute(select(RealEstateLead).where(RealEstateLead.id == record_id))
                return r.scalars().first()
            if record_type == RECORD_SERVICE_INVOICE:
                from app.engines.invoice_payment.models import ServiceInvoice
                r = await db.execute(select(ServiceInvoice).where(ServiceInvoice.id == record_id))
                return r.scalars().first()
            if record_type == RECORD_CUSTOMER_REVIEW:
                from app.engines.customer_reviews.models import CustomerReview
                r = await db.execute(select(CustomerReview).where(CustomerReview.id == record_id))
                return r.scalars().first()
        except Exception:
            pass
        return None

    async def _customer_owns_record(
        self,
        db: AsyncSession,
        customer_id: uuid.UUID,
        record_type: str,
        record,
    ) -> bool:
        owner_id = getattr(record, "customer_id", None)
        if owner_id:
            return str(owner_id) == str(customer_id)
        # For service_job, look up booking
        if record_type == RECORD_SERVICE_JOB:
            booking_id = getattr(record, "booking_id", None)
            if booking_id:
                try:
                    from app.engines.final_records.models import ServiceBooking
                    r = await db.execute(select(ServiceBooking).where(ServiceBooking.id == booking_id))
                    booking = r.scalars().first()
                    if booking:
                        return str(booking.customer_id) == str(customer_id)
                except Exception:
                    pass
        return True
