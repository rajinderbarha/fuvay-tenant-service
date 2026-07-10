"""Sprint 17 — AppointmentSlotAvailabilityService.

Generates real available slots from StaffWorkingHours, subtracts StaffCalendarBlocks,
active slot holds, and existing confirmed appointments.

No fake slots. If no slots, returns empty list with safe message.
"""
from __future__ import annotations
import uuid
from datetime import date, datetime, time, timedelta, timezone

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.coaching_appointment.constants import (
    DEFAULT_SEARCH_DAYS, DEFAULT_SLOT_LIMIT,
    HOLD_STATUS_HELD, ERR_NEXT_AVAILABLE_SLOT_NOT_FOUND,
)
from app.engines.coaching_appointment.center_discovery import CoachingCenterDiscoveryService

logger = structlog.get_logger("coaching.slot_service")
utcnow = lambda: datetime.now(timezone.utc)


class AppointmentSlotAvailabilityService:
    """
    Computes real available slots for a given tenant + offering + date.

    Sources used:
    - StaffWorkingHours (slot generation)
    - StaffCalendarBlock (block subtraction)
    - CoachingAppointmentSlotHold (hold subtraction)
    - Appointment (confirmed appointment subtraction, if any)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_available_slots(
        self,
        tenant_id: uuid.UUID,
        offering_id: uuid.UUID,
        date_str: str,
        preferred_mode: str | None = None,
        exclude_draft_id: uuid.UUID | None = None,
    ) -> dict:
        """
        Returns all available slots for a tenant on a given date.
        Excludes slots that are already held (except for the same draft)
        or confirmed in appointments.
        """
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return {"date": date_str, "slots": [], "error": "Invalid date format"}

        dow = target_date.weekday()  # 0=Mon

        try:
            from app.engines.appointment.models import StaffWorkingHours, StaffCalendarBlock, Appointment
            from app.engines.appointment.constants import AS
            from app.engines.coaching_appointment.models import CoachingAppointmentSlotHold

            # Get all staff for this tenant that have working hours on this day
            wh_q = select(StaffWorkingHours).where(
                StaffWorkingHours.tenant_id == tenant_id,
                StaffWorkingHours.day_of_week == dow,
                StaffWorkingHours.is_active == True,
            )
            wh_rows = (await self.db.execute(wh_q)).scalars().all()

            if not wh_rows:
                return {
                    "tenant_id": str(tenant_id),
                    "date": date_str,
                    "slots": [],
                    "message": "No working hours configured for this date.",
                }

            # Get calendar blocks for this date
            block_q = select(StaffCalendarBlock).where(
                StaffCalendarBlock.tenant_id == tenant_id,
                StaffCalendarBlock.block_date == date_str,
            )
            blocks = (await self.db.execute(block_q)).scalars().all()

            # Get active slot holds (exclude our own draft hold)
            hold_q = select(CoachingAppointmentSlotHold).where(
                CoachingAppointmentSlotHold.tenant_id == tenant_id,
                CoachingAppointmentSlotHold.slot_date == target_date,
                CoachingAppointmentSlotHold.hold_status == HOLD_STATUS_HELD,
                CoachingAppointmentSlotHold.expires_at > utcnow(),
            )
            if exclude_draft_id:
                hold_q = hold_q.where(
                    CoachingAppointmentSlotHold.draft_id != exclude_draft_id
                )
            holds = (await self.db.execute(hold_q)).scalars().all()
            held_keys: set[tuple] = {(h.start_time, h.staff_member_id) for h in holds}

            # Get confirmed appointments for this tenant/date
            try:
                appt_q = select(Appointment).where(
                    Appointment.tenant_id == tenant_id,
                    Appointment.status.in_([AS.HOLD, AS.CONFIRMED, AS.REMINDED, AS.IN_PROGRESS]),
                )
                appts = (await self.db.execute(appt_q)).scalars().all()
                booked_slots: set = {a.scheduled_at.replace(tzinfo=None) for a in appts}
            except Exception:
                booked_slots = set()

            slots: list[dict] = []

            for wh in wh_rows:
                staff_id = wh.staff_id

                # Check full-day block for this staff
                full_day_blocked = any(
                    b.is_full_day and b.staff_id == staff_id for b in blocks
                )
                if full_day_blocked:
                    continue

                # Build block ranges for this staff
                blocked_ranges: list[tuple] = []
                for b in blocks:
                    if b.staff_id != staff_id:
                        continue
                    bs = datetime.strptime(f"{date_str} {b.start_time}", "%Y-%m-%d %H:%M")
                    be = datetime.strptime(f"{date_str} {b.end_time}", "%Y-%m-%d %H:%M")
                    blocked_ranges.append((bs, be))

                # Generate slots
                start_t = datetime.strptime(wh.start_time, "%H:%M").time()
                end_t   = datetime.strptime(wh.end_time, "%H:%M").time()
                duration = wh.slot_duration
                buffer   = wh.buffer_minutes

                current = datetime.combine(target_date, start_t)
                end_dt  = datetime.combine(target_date, end_t)

                while current + timedelta(minutes=duration) <= end_dt:
                    slot_end = current + timedelta(minutes=duration)

                    # Skip if blocked
                    in_block = any(bs <= current < be or bs < slot_end <= be
                                   for bs, be in blocked_ranges)
                    if in_block:
                        current += timedelta(minutes=duration + buffer)
                        continue

                    # Skip if booked in appointment table
                    if current in booked_slots:
                        current += timedelta(minutes=duration + buffer)
                        continue

                    # Skip if held
                    slot_time = current.time()
                    if (slot_time, staff_id) in held_keys:
                        current += timedelta(minutes=duration + buffer)
                        continue

                    slots.append({
                        "start_time":       current.strftime("%H:%M"),
                        "end_time":         slot_end.strftime("%H:%M"),
                        "staff_member_id":  str(staff_id),
                        "mode":             preferred_mode or "offline",
                        "available":        True,
                        "remaining_capacity": 1,  # 1 staff = 1 slot capacity
                    })
                    current += timedelta(minutes=duration + buffer)

            return {
                "tenant_id": str(tenant_id),
                "date": date_str,
                "slots": slots,
                "total_available": len(slots),
            }

        except Exception as exc:
            logger.warning("slot_service.get_available_slots.failed", error=str(exc))
            return {"tenant_id": str(tenant_id), "date": date_str, "slots": [], "error": str(exc)}

    async def find_next_available_slots(
        self,
        category_id: uuid.UUID,
        offering_id: uuid.UUID,
        city: str | None,
        zipcode: str | None,
        preferred_mode: str | None,
        preferred_date: str,
        tenant_id: uuid.UUID | None = None,
        limit: int = DEFAULT_SLOT_LIMIT,
        search_days: int = DEFAULT_SEARCH_DAYS,
        exclude_draft_id: uuid.UUID | None = None,
    ) -> dict:
        """
        Search for the next available slots starting from preferred_date.

        Strategy:
        1. Check preferred_date first
        2. If no slots, scan next search_days days
        3. Return earliest available slots from bookable centers
        4. Mark first result as is_recommended=True
        5. If nothing found in search window, return fallback_available=True
        """
        try:
            base_date = datetime.strptime(preferred_date, "%Y-%m-%d").date()
        except ValueError:
            base_date = datetime.now(timezone.utc).date()

        # Get bookable centers to search
        discovery = CoachingCenterDiscoveryService(self.db)
        center_result = await discovery.find_centers(
            category_id=category_id,
            offering_id=offering_id,
            city=city,
            zipcode=zipcode,
            preferred_mode=preferred_mode,
            limit=20,
        )

        if not center_result.get("available"):
            return {
                "requested_date": preferred_date,
                "requested_date_available": False,
                "next_available_slots": [],
                "fallback_available": True,
                "fallback_type": "center_call_back_request",
                "message": "No coaching centers available in your area.",
            }

        centers = center_result.get("centers", [])

        # If caller specified a tenant_id, filter to just that tenant
        if tenant_id:
            centers = [c for c in centers if c.get("provider_ref") == str(tenant_id)]
            if not centers:
                centers = center_result.get("centers", [])

        # Check preferred date first
        requested_date_available = False
        all_found: list[dict] = []

        for search_offset in range(search_days + 1):
            check_date = base_date + timedelta(days=search_offset)
            date_str   = check_date.isoformat()

            for center in centers:
                t_id_str = center.get("provider_ref")
                if not t_id_str:
                    continue
                try:
                    t_id = uuid.UUID(t_id_str)
                except ValueError:
                    continue

                slot_result = await self.get_available_slots(
                    tenant_id=t_id,
                    offering_id=offering_id,
                    date_str=date_str,
                    preferred_mode=preferred_mode,
                    exclude_draft_id=exclude_draft_id,
                )
                for s in slot_result.get("slots", []):
                    if search_offset == 0:
                        requested_date_available = True
                    all_found.append({
                        "provider_ref":          t_id_str,
                        "business_name":         center.get("business_name", "—"),
                        "slot_date":             date_str,
                        "start_time":            s["start_time"],
                        "end_time":              s["end_time"],
                        "staff_member_id":       s.get("staff_member_id"),
                        "mode":                  s.get("mode", preferred_mode or "offline"),
                        "remaining_capacity":    s.get("remaining_capacity", 1),
                        "is_recommended":        False,
                        "recommendation_reason": None,
                    })
                if len(all_found) >= limit and search_offset > 0:
                    break

            if len(all_found) >= limit:
                break

        if not all_found:
            return {
                "requested_date":            preferred_date,
                "requested_date_available":  False,
                "next_available_slots":      [],
                "fallback_available":        True,
                "fallback_type":             "center_call_back_request",
                "message":                   "No slots are available right now, but we can ask the center to call you when a slot opens.",
                "reason_code":               ERR_NEXT_AVAILABLE_SLOT_NOT_FOUND,
            }

        # Sort by date+time and mark first as recommended
        all_found.sort(key=lambda x: (x["slot_date"], x["start_time"]))
        all_found = all_found[:limit]
        all_found[0]["is_recommended"] = True
        all_found[0]["recommendation_reason"] = "Earliest available slot"

        msg = (
            f"Slots are available on {preferred_date}."
            if requested_date_available
            else f"No slots on {preferred_date}. Next available: {all_found[0]['slot_date']} at {all_found[0]['start_time']}."
        )

        return {
            "requested_date":            preferred_date,
            "requested_date_available":  requested_date_available,
            "next_available_slots":      all_found,
            "fallback_available":        False,
            "message":                   msg,
            "assistant_conversion_hint": {
                "type":                    "suggest_next_available",
                "recommended_slot_index":  0,
                "message_key":             "requested_date_full_next_slot_available",
            } if not requested_date_available else None,
        }
