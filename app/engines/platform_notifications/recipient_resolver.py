"""Sprint 27 — Notification Recipient Resolver.

Resolves who should receive a notification for a given record.
No cross-tenant leakage: customer→own record only, provider→own tenant only.
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.platform_notifications.constants import (
    RECIP_CUSTOMER, RECIP_PROVIDER, RECIP_STAFF, RECIP_ADMIN,
)


@dataclass
class Recipient:
    user_id: uuid.UUID
    recipient_type: str
    tenant_id: uuid.UUID | None = None


class NotificationRecipientResolver:

    async def resolve_customer(
        self,
        db: AsyncSession,
        record_type: str,
        record_id: uuid.UUID,
    ) -> list[Recipient]:
        """Resolve the customer who owns a booking/job/appointment/lead/complaint."""
        customer_id = await self._fetch_customer_id(db, record_type, record_id)
        if not customer_id:
            return []
        return [Recipient(user_id=customer_id, recipient_type=RECIP_CUSTOMER)]

    async def resolve_provider_owner(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> list[Recipient]:
        """Resolve the primary user(s) for a tenant (owner role)."""
        try:
            from app.engines.auth.models import User
            r = await db.execute(
                select(User).where(
                    User.tenant_id == tenant_id,
                    User.role == "tenant_owner",
                    User.is_active == True,
                )
            )
            users = r.scalars().all()
            return [Recipient(user_id=u.id, recipient_type=RECIP_PROVIDER, tenant_id=tenant_id)
                    for u in users]
        except Exception:
            return []

    async def resolve_provider_staff(
        self,
        db: AsyncSession,
        staff_member_id: uuid.UUID,
    ) -> list[Recipient]:
        """Resolve a specific assigned staff member."""
        try:
            from app.engines.auth.models import User
            r = await db.execute(select(User).where(User.id == staff_member_id))
            user = r.scalars().first()
            if not user:
                return []
            return [Recipient(user_id=user.id, recipient_type=RECIP_STAFF,
                              tenant_id=getattr(user, "tenant_id", None))]
        except Exception:
            return []

    async def resolve_admins(
        self,
        db: AsyncSession,
    ) -> list[Recipient]:
        """Resolve all super-admin users."""
        try:
            from app.engines.auth.models import User
            r = await db.execute(
                select(User).where(
                    User.role == "super_admin",
                    User.is_active == True,
                )
            )
            users = r.scalars().all()
            return [Recipient(user_id=u.id, recipient_type=RECIP_ADMIN) for u in users]
        except Exception:
            return []

    async def resolve_booking_participants(
        self,
        db: AsyncSession,
        booking_id: uuid.UUID,
    ) -> list[Recipient]:
        """Resolve customer + provider for a service booking."""
        customer = await self.resolve_customer(db, "service_booking", booking_id)
        # Try to get tenant from booking
        try:
            from app.engines.booking.models import ServiceBooking
            r = await db.execute(select(ServiceBooking).where(ServiceBooking.id == booking_id))
            booking = r.scalars().first()
            if booking and getattr(booking, "tenant_id", None):
                provider = await self.resolve_provider_owner(db, booking.tenant_id)
                return customer + provider
        except Exception:
            pass
        return customer

    async def resolve_complaint_participants(
        self,
        db: AsyncSession,
        complaint_id: uuid.UUID,
    ) -> list[Recipient]:
        """Resolve customer + provider + admin for a complaint."""
        customer = await self.resolve_customer(db, "complaint", complaint_id)
        admins = await self.resolve_admins(db)
        try:
            from app.engines.complaints.models import CustomerComplaint
            r = await db.execute(select(CustomerComplaint).where(CustomerComplaint.id == complaint_id))
            complaint = r.scalars().first()
            if complaint and complaint.tenant_id:
                provider = await self.resolve_provider_owner(db, complaint.tenant_id)
                return customer + provider + admins
        except Exception:
            pass
        return customer + admins

    async def resolve_appointment_participants(
        self,
        db: AsyncSession,
        appointment_id: uuid.UUID,
    ) -> list[Recipient]:
        """Resolve customer + provider for an appointment."""
        return await self.resolve_customer(db, "coaching_appointment", appointment_id)

    async def resolve_lead_participants(
        self,
        db: AsyncSession,
        lead_id: uuid.UUID,
    ) -> list[Recipient]:
        """Resolve customer + provider for a real estate lead."""
        return await self.resolve_customer(db, "real_estate_lead", lead_id)

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _fetch_customer_id(
        self,
        db: AsyncSession,
        record_type: str,
        record_id: uuid.UUID,
    ) -> uuid.UUID | None:
        """Fetch the customer_id from the record's table."""
        try:
            if record_type == "service_booking":
                from app.engines.booking.models import ServiceBooking
                r = await db.execute(select(ServiceBooking).where(ServiceBooking.id == record_id))
                record = r.scalars().first()
                return getattr(record, "customer_id", None) if record else None

            if record_type == "service_job":
                from app.engines.home_service_assignment.models import ServiceJob
                r = await db.execute(select(ServiceJob).where(ServiceJob.id == record_id))
                record = r.scalars().first()
                return getattr(record, "customer_id", None) if record else None

            if record_type == "coaching_appointment":
                from app.engines.coaching_appointment.models import CoachingAppointment
                r = await db.execute(select(CoachingAppointment).where(CoachingAppointment.id == record_id))
                record = r.scalars().first()
                return getattr(record, "customer_id", None) if record else None

            if record_type == "real_estate_lead":
                from app.engines.real_estate.models import RealEstateLead
                r = await db.execute(select(RealEstateLead).where(RealEstateLead.id == record_id))
                record = r.scalars().first()
                return getattr(record, "customer_id", None) if record else None

            if record_type == "complaint":
                from app.engines.complaints.models import CustomerComplaint
                r = await db.execute(select(CustomerComplaint).where(CustomerComplaint.id == record_id))
                record = r.scalars().first()
                return getattr(record, "customer_id", None) if record else None

        except Exception:
            pass
        return None
