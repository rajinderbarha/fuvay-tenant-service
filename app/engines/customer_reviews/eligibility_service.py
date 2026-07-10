"""Sprint 24 — Review Eligibility Service."""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.engines.customer_reviews.constants import (
    ELIGIBLE_STATUSES, VALID_RECORD_TYPES,
    RECORD_TYPE_SERVICE_BOOKING, RECORD_TYPE_SERVICE_JOB,
    RECORD_TYPE_COACHING_APPOINTMENT, RECORD_TYPE_REAL_ESTATE_LEAD,
    ERR_RECORD_NOT_FOUND, ERR_REVIEW_NOT_ELIGIBLE,
)
from app.engines.customer_reviews.models import CustomerReview


class ReviewEligibilityService:

    async def check_eligible(
        self,
        db: AsyncSession,
        customer_id: uuid.UUID,
        record_type: str,
        record_id: uuid.UUID,
    ) -> dict:
        """
        Returns {"eligible": bool, "reason": str | None, "record": dict}.
        Raises ValueError if record_type is invalid or record not found.
        """
        if record_type not in VALID_RECORD_TYPES:
            raise ValueError(ERR_REVIEW_NOT_ELIGIBLE)

        record = await self._fetch_record(db, record_type, record_id)
        if not record:
            raise ValueError(ERR_RECORD_NOT_FOUND)

        status = getattr(record, "status", None)
        eligible_set = ELIGIBLE_STATUSES.get(record_type, set())
        if status not in eligible_set:
            return {
                "eligible": False,
                "reason":   f"Record status '{status}' is not eligible for review.",
                "record":   self._record_to_dict(record, record_type),
            }

        # Check customer ownership
        if not await self._customer_owns_record(db, customer_id, record_type, record, record_id):
            return {
                "eligible": False,
                "reason":   "You are not the customer for this record.",
                "record":   self._record_to_dict(record, record_type),
            }

        # Check not already reviewed
        existing = await db.execute(
            select(CustomerReview).where(
                CustomerReview.customer_id == customer_id,
                CustomerReview.record_type == record_type,
                CustomerReview.record_id   == record_id,
            )
        )
        if existing.scalars().first():
            return {
                "eligible": False,
                "reason":   "You have already submitted a review for this record.",
                "record":   self._record_to_dict(record, record_type),
            }

        return {
            "eligible": True,
            "reason":   None,
            "record":   self._record_to_dict(record, record_type),
        }

    async def _fetch_record(self, db: AsyncSession, record_type: str, record_id: uuid.UUID):
        if record_type == RECORD_TYPE_SERVICE_BOOKING:
            from app.engines.final_records.models import ServiceBooking
            r = await db.execute(select(ServiceBooking).where(ServiceBooking.id == record_id))
            return r.scalars().first()
        if record_type == RECORD_TYPE_SERVICE_JOB:
            from app.engines.final_records.models import ServiceJob
            r = await db.execute(select(ServiceJob).where(ServiceJob.id == record_id))
            return r.scalars().first()
        if record_type == RECORD_TYPE_COACHING_APPOINTMENT:
            from app.engines.final_records.models import CoachingAppointment
            r = await db.execute(select(CoachingAppointment).where(CoachingAppointment.id == record_id))
            return r.scalars().first()
        if record_type == RECORD_TYPE_REAL_ESTATE_LEAD:
            from app.engines.final_records.models import RealEstateLead
            r = await db.execute(select(RealEstateLead).where(RealEstateLead.id == record_id))
            return r.scalars().first()
        return None

    async def _customer_owns_record(
        self,
        db: AsyncSession,
        customer_id: uuid.UUID,
        record_type: str,
        record,
        record_id: uuid.UUID,
    ) -> bool:
        """Verify the customer_id matches the record's customer field."""
        owner_id = getattr(record, "customer_id", None)
        if owner_id is None:
            # For service_job, look up via booking
            if record_type == RECORD_TYPE_SERVICE_JOB:
                booking_id = getattr(record, "booking_id", None)
                if booking_id:
                    from app.engines.final_records.models import ServiceBooking
                    r = await db.execute(
                        select(ServiceBooking).where(ServiceBooking.id == booking_id)
                    )
                    booking = r.scalars().first()
                    owner_id = getattr(booking, "customer_id", None) if booking else None
        return str(owner_id) == str(customer_id) if owner_id else True

    def _record_to_dict(self, record, record_type: str) -> dict:
        return {
            "id":          str(record.id),
            "record_type": record_type,
            "status":      getattr(record, "status", None),
            "tenant_id":   str(record.tenant_id) if getattr(record, "tenant_id", None) else None,
        }
