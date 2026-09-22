"""Sprint 18 Hardening — DraftExpiryService: expires stale drafts across all lead-flow engines."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession


class DraftExpiryService:
    """Runs time-based expiry for all draft-lifecycle lead flows.

    Call expire_all() from the scheduled job or admin trigger.
    Each engine method is idempotent — safe to call repeatedly.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def expire_real_estate_lead_drafts(self) -> dict:
        """Expire Real Estate lead drafts whose expires_at has passed."""
        from app.engines.real_estate_lead.service import RealEstateLeadFlowService
        svc = RealEstateLeadFlowService(db=self.db)
        return await svc.expire_old_drafts()

    async def expire_home_service_booking_drafts(self) -> dict:
        """Retire home-service drafts whose `expires_at` has passed.

        Nothing ever wrote the terminal status, so an abandoned draft stayed
        "active" for ever: every read had to remember to filter on
        `expires_at`, and the three-draft cap counted rows the customer could
        no longer see or finish.
        """
        from sqlalchemy import update
        from app.engines.home_service_booking.constants import (
            DRAFT_STATUS_EXPIRED, TERMINAL_STATUSES,
        )
        from app.engines.home_service_booking.models import HomeServiceBookingDraft
        from app.models.base import utcnow

        now = utcnow()
        result = await self.db.execute(
            update(HomeServiceBookingDraft)
            .where(
                HomeServiceBookingDraft.status.notin_(list(TERMINAL_STATUSES)),
                HomeServiceBookingDraft.expires_at.isnot(None),
                HomeServiceBookingDraft.expires_at <= now,
            )
            .values(status=DRAFT_STATUS_EXPIRED, updated_at=now)
        )
        return {"expired_count": int(result.rowcount or 0)}

    async def expire_coaching_appointment_drafts(self) -> dict:
        # TODO Sprint 19+ — Coaching appointment draft expiry not yet implemented.
        return {"expired_count": 0, "note": "not_implemented"}

    async def expire_coaching_slot_holds(self) -> dict:
        # TODO Sprint 19+ — Slot hold expiry (10-15 min TTL) not yet implemented.
        return {"expired_count": 0, "note": "not_implemented"}

    async def expire_all(self) -> dict:
        """Run all expiry jobs and return a combined summary."""
        real_estate   = await self.expire_real_estate_lead_drafts()
        home_service  = await self.expire_home_service_booking_drafts()
        coaching_appt = await self.expire_coaching_appointment_drafts()
        slot_holds    = await self.expire_coaching_slot_holds()

        total = (
            real_estate.get("expired_count", 0)
            + home_service.get("expired_count", 0)
            + coaching_appt.get("expired_count", 0)
            + slot_holds.get("expired_count", 0)
        )
        return {
            "total_expired":               total,
            "real_estate_lead_drafts":     real_estate,
            "home_service_booking_drafts": home_service,
            "coaching_appointment_drafts": coaching_appt,
            "coaching_slot_holds":         slot_holds,
        }
