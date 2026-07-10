"""Sprint 17 — CoachingAppointmentFlowService.

19 public methods covering the full coaching appointment draft lifecycle.

Rules:
- Backend is source of truth (fee, slot availability, center selection)
- DeepSeek only collects field values — never decides anything
- No final appointment creation in this sprint (Sprint 19)
- Required fields driven by MasterOffering flags, not hardcoded
- Slot must be held before ready_for_confirmation
"""
from __future__ import annotations
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import and_, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.coaching_appointment.constants import (
    ACTOR_AI, ACTOR_BACKEND, ACTOR_CUSTOMER, ACTOR_SYSTEM,
    COACHING_CATEGORY_ALIASES,
    DRAFT_EXPIRY_HOURS, DRAFT_STATUS_CANCELLED, DRAFT_STATUS_COLLECTING_DETAILS,
    DRAFT_STATUS_CONFIRMED, DRAFT_STATUS_DRAFT, DRAFT_STATUS_EXPIRED,
    DRAFT_STATUS_FAILED, DRAFT_STATUS_LOCATION_CHECKED, DRAFT_STATUS_READY_FOR_CONFIRMATION,
    DRAFT_STATUS_SLOT_SELECTED, DRAFT_STATUS_SLOTS_LOADED,
    ERR_CATEGORY_INVALID, ERR_CONFIRMATION_NOT_READY, ERR_DATE_REQUIRED,
    ERR_DRAFT_ACCESS_DENIED, ERR_DRAFT_NOT_FOUND, ERR_DRAFT_TERMINAL,
    ERR_FEE_ESTIMATE_FAILED, ERR_LOCATION_REQUIRED, ERR_MODE_REQUIRED,
    ERR_NO_CENTER_AVAILABLE, ERR_NO_SLOT_AVAILABLE, ERR_OFFERING_INVALID,
    ERR_REQUIRED_FIELD_MISSING, ERR_SLOT_ALREADY_HELD, ERR_SLOT_REQUIRED,
    EVENT_DRAFT_CANCELLED, EVENT_DRAFT_CONFIRMED, EVENT_DRAFT_CREATED,
    EVENT_DRAFT_FAILED, EVENT_FALLBACK_INQUIRY_PREPARED, EVENT_FEE_ESTIMATED,
    EVENT_FIELD_COLLECTED, EVENT_NO_SLOT_ON_REQUESTED_DATE, EVENT_NEXT_AVAILABLE_SLOTS_LOADED,
    EVENT_PROVIDER_OPTIONS_LOADED, EVENT_RECOMMENDED_SLOT_SUGGESTED,
    EVENT_SLOT_HELD, EVENT_SLOT_SELECTED, EVENT_SLOTS_LOADED,
    EVENT_SUMMARY_GENERATED,
    FEE_STATUS_ESTIMATED, FEE_STATUS_FAILED, FEE_STATUS_FREE, FEE_STATUS_PENDING,
    HOLD_STATUS_EXPIRED, HOLD_STATUS_HELD, HOLD_STATUS_RELEASED,
    LOC_STATUS_AVAILABLE, LOC_STATUS_NOT_AVAILABLE, LOC_STATUS_PENDING,
    MODE_OFFLINE, SLOT_HOLD_EXPIRY_MINUTES, SLOT_STATUS_FALLBACK,
    SLOT_STATUS_HELD, SLOT_STATUS_LOADED, SLOT_STATUS_NEXT_FOUND,
    SLOT_STATUS_NO_SLOT, SLOT_STATUS_PENDING, SLOT_STATUS_SELECTED,
    TERMINAL_STATUSES,
)
from app.engines.coaching_appointment.models import (
    CoachingAppointmentDraft,
    CoachingAppointmentDraftEvent,
    CoachingAppointmentSlotHold,
)
from app.engines.coaching_appointment.center_discovery import CoachingCenterDiscoveryService
from app.engines.coaching_appointment.slot_service import AppointmentSlotAvailabilityService
from app.exceptions import ServiceOSException

logger = structlog.get_logger("coaching.appointment.service")
utcnow = lambda: datetime.now(timezone.utc)

# Allowed update fields (guards against frontend injecting forbidden data)
ALLOWED_UPDATE_FIELDS = {
    "student_name", "student_phone", "student_email", "student_age",
    "current_education", "target_exam", "target_band",
    "preferred_mode", "city", "zipcode",
    "selected_date", "notes",
}


class CoachingAppointmentFlowService:
    """
    Manages the full coaching appointment draft lifecycle.
    All business decisions (fee, slots, center selection) are made here.
    DeepSeek only supplies text/field values via the chat layer.
    """

    def __init__(self, db: AsyncSession, request_id: str = "—"):
        self.db          = db
        self.request_id  = request_id
        self._discovery  = CoachingCenterDiscoveryService(db)
        self._slot_svc   = AppointmentSlotAvailabilityService(db)

    # ══════════════════════════════════════════════════════════════════════════
    # 1. START DRAFT
    # ══════════════════════════════════════════════════════════════════════════

    async def start_appointment_draft(
        self,
        customer_id: uuid.UUID | None,
        ai_session_id: uuid.UUID | None,
        category_slug: str,
        offering_slug: str,
    ) -> dict:
        from app.engines.admin_catalog.models import ServiceCategory, MasterOffering

        # Resolve category
        slug_lower = category_slug.lower().strip()
        cat_q = select(ServiceCategory).where(
            ServiceCategory.is_active == True,
            ServiceCategory.is_customer_visible == True,
        )
        cats = (await self.db.execute(cat_q)).scalars().all()
        category = next(
            (c for c in cats if c.slug.lower() in COACHING_CATEGORY_ALIASES
             or c.slug.lower() == slug_lower
             or c.name.lower().replace(" ", "-") == slug_lower),
            None,
        )
        if not category:
            raise ServiceOSException(ERR_CATEGORY_INVALID, f"Category '{category_slug}' not found or inactive.")

        # Resolve offering
        off_q = select(MasterOffering).where(
            MasterOffering.category_id == category.id,
            MasterOffering.is_active == True,
        )
        offerings = (await self.db.execute(off_q)).scalars().all()
        offering = next(
            (o for o in offerings if o.slug.lower() == offering_slug.lower()),
            None,
        )
        if not offering:
            raise ServiceOSException(ERR_OFFERING_INVALID, f"Offering '{offering_slug}' not found or inactive.")

        expires_at = utcnow() + timedelta(hours=DRAFT_EXPIRY_HOURS)
        draft = CoachingAppointmentDraft(
            customer_id=customer_id,
            ai_session_id=ai_session_id,
            category_id=category.id,
            offering_id=offering.id,
            status=DRAFT_STATUS_DRAFT,
            expires_at=expires_at,
        )
        self.db.add(draft)
        await self.db.flush()
        await self.db.refresh(draft)

        await self._emit_event(draft.id, ACTOR_BACKEND, EVENT_DRAFT_CREATED,
                               message=f"Draft started for {offering.name}")

        required_fields = self._compute_required_fields(offering)
        return {
            **draft.to_dict(),
            "offering_name":    offering.name,
            "offering_class":   offering.offering_class,
            "required_fields":  required_fields,
            "appointment_fee":  float(offering.default_appointment_fee),
            "fee_type":         "free" if offering.default_appointment_fee == 0 else "fixed",
        }

    # ══════════════════════════════════════════════════════════════════════════
    # 2. GET DRAFT
    # ══════════════════════════════════════════════════════════════════════════

    async def get_appointment_draft(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
    ) -> dict:
        draft = await self._get_draft(draft_id, customer_id)
        missing = await self._get_missing_fields_for_draft(draft)
        return {**draft.to_dict(), "missing_fields": missing}

    # ══════════════════════════════════════════════════════════════════════════
    # 3. UPDATE DRAFT FIELDS
    # ══════════════════════════════════════════════════════════════════════════

    async def update_draft_fields(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
        payload: dict,
    ) -> dict:
        draft = await self._get_draft(draft_id, customer_id)
        self._guard_terminal(draft)

        updated_fields: list[str] = []
        for field, value in payload.items():
            if field not in ALLOWED_UPDATE_FIELDS:
                continue
            if field == "selected_date" and isinstance(value, str):
                try:
                    value = datetime.strptime(value, "%Y-%m-%d").date()
                except ValueError:
                    continue
            if hasattr(draft, field):
                setattr(draft, field, value)
                updated_fields.append(field)

        if draft.status == DRAFT_STATUS_DRAFT and updated_fields:
            draft.status = DRAFT_STATUS_COLLECTING_DETAILS

        await self.db.flush()
        await self.db.refresh(draft)
        await self._emit_event(draft.id, ACTOR_CUSTOMER, EVENT_FIELD_COLLECTED,
                               new_value={"fields": updated_fields})

        missing = await self._get_missing_fields_for_draft(draft)
        return {**draft.to_dict(), "missing_fields": missing, "updated_fields": updated_fields}

    # ══════════════════════════════════════════════════════════════════════════
    # 4. SYNC FROM AI SESSION
    # ══════════════════════════════════════════════════════════════════════════

    async def sync_draft_from_ai_session(self, ai_session_id: uuid.UUID) -> dict | None:
        """Pull collected_fields from AI session and apply to the linked draft."""
        try:
            from app.engines.ai_conversation.models import AIConversationSession
            sess_r = await self.db.execute(
                select(AIConversationSession).where(AIConversationSession.id == ai_session_id)
            )
            session = sess_r.scalar_one_or_none()
            if not session or not session.collected_fields:
                return None

            r = await self.db.execute(
                select(CoachingAppointmentDraft).where(
                    CoachingAppointmentDraft.ai_session_id == ai_session_id,
                    CoachingAppointmentDraft.status.not_in(list(TERMINAL_STATUSES)),
                ).order_by(CoachingAppointmentDraft.created_at.desc()).limit(1)
            )
            draft = r.scalar_one_or_none()
            if not draft:
                return None

            return await self.update_draft_fields(draft.id, draft.customer_id, session.collected_fields)
        except Exception as exc:
            logger.warning("coaching.sync_from_ai_session.failed", error=str(exc))
            return None

    # ══════════════════════════════════════════════════════════════════════════
    # 5-6. REQUIRED FIELDS / MISSING FIELDS
    # ══════════════════════════════════════════════════════════════════════════

    async def validate_required_fields(self, draft_id: uuid.UUID) -> dict:
        draft = await self._get_draft(draft_id, None)
        missing = await self._get_missing_fields_for_draft(draft)
        return {"is_valid": len(missing) == 0, "missing_fields": missing}

    async def get_missing_fields(self, draft_id: uuid.UUID) -> list[str]:
        draft = await self._get_draft(draft_id, None)
        return await self._get_missing_fields_for_draft(draft)

    # ══════════════════════════════════════════════════════════════════════════
    # 7. FIND BOOKABLE CENTERS
    # ══════════════════════════════════════════════════════════════════════════

    async def find_bookable_centers(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
    ) -> dict:
        draft = await self._get_draft(draft_id, customer_id)

        result = await self._discovery.find_centers(
            category_id=draft.category_id,
            offering_id=draft.offering_id,
            city=draft.city,
            zipcode=draft.zipcode,
            preferred_mode=draft.preferred_mode,
        )

        draft.provider_options = result.get("centers", [])
        draft.location_status  = result.get("location_status", LOC_STATUS_PENDING)

        if result.get("available"):
            draft.status = DRAFT_STATUS_LOCATION_CHECKED
            await self._emit_event(draft.id, ACTOR_BACKEND, EVENT_PROVIDER_OPTIONS_LOADED,
                                   new_value={"count": result["available_center_count"]})
        else:
            draft.location_status = LOC_STATUS_NOT_AVAILABLE

        await self.db.flush()
        await self.db.refresh(draft)
        return {**draft.to_dict(), **result}

    # ══════════════════════════════════════════════════════════════════════════
    # 8. LOAD AVAILABLE SLOTS
    # ══════════════════════════════════════════════════════════════════════════

    async def load_available_slots(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
        tenant_id: uuid.UUID | None = None,
        date_str: str | None = None,
    ) -> dict:
        draft = await self._get_draft(draft_id, customer_id)

        t_id   = tenant_id or draft.selected_tenant_id
        d_str  = date_str or (draft.selected_date.isoformat() if draft.selected_date else None)

        if not t_id:
            raise ServiceOSException(ERR_NO_CENTER_AVAILABLE, "No center selected. Call find-centers first.")
        if not d_str:
            raise ServiceOSException(ERR_DATE_REQUIRED, "selected_date is required before loading slots.")

        result = await self._slot_svc.get_available_slots(
            tenant_id=t_id,
            offering_id=draft.offering_id,
            date_str=d_str,
            preferred_mode=draft.preferred_mode,
            exclude_draft_id=draft_id,
        )

        has_slots = bool(result.get("slots"))
        draft.slot_status = SLOT_STATUS_LOADED if has_slots else SLOT_STATUS_NO_SLOT
        draft.status = DRAFT_STATUS_SLOTS_LOADED

        if has_slots:
            await self._emit_event(draft.id, ACTOR_BACKEND, EVENT_SLOTS_LOADED,
                                   new_value={"count": len(result["slots"]), "date": d_str})
        else:
            await self._emit_event(draft.id, ACTOR_BACKEND, EVENT_NO_SLOT_ON_REQUESTED_DATE,
                                   new_value={"date": d_str})

        await self.db.flush()
        await self.db.refresh(draft)
        return {**draft.to_dict(), **result}

    # ══════════════════════════════════════════════════════════════════════════
    # 9. FIND NEXT AVAILABLE SLOTS
    # ══════════════════════════════════════════════════════════════════════════

    async def find_next_available_slots(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
        search_days: int = 14,
        preferred_date: str | None = None,
    ) -> dict:
        draft = await self._get_draft(draft_id, customer_id)

        p_date = preferred_date or (draft.selected_date.isoformat() if draft.selected_date else datetime.now(timezone.utc).date().isoformat())

        result = await self._slot_svc.find_next_available_slots(
            category_id=draft.category_id,
            offering_id=draft.offering_id,
            city=draft.city,
            zipcode=draft.zipcode,
            preferred_mode=draft.preferred_mode,
            preferred_date=p_date,
            tenant_id=draft.selected_tenant_id,
            search_days=search_days,
            exclude_draft_id=draft_id,
        )

        draft.next_available_slots = result.get("next_available_slots", [])
        draft.status = DRAFT_STATUS_SLOTS_LOADED

        if result.get("next_available_slots"):
            next_slots = result["next_available_slots"]
            recommended = next((s for s in next_slots if s.get("is_recommended")), next_slots[0] if next_slots else None)
            draft.recommended_slot_snapshot = recommended
            draft.slot_status = SLOT_STATUS_NEXT_FOUND
            await self._emit_event(draft.id, ACTOR_BACKEND, EVENT_NEXT_AVAILABLE_SLOTS_LOADED,
                                   new_value={"count": len(next_slots)})
            if recommended:
                await self._emit_event(draft.id, ACTOR_BACKEND, EVENT_RECOMMENDED_SLOT_SUGGESTED,
                                       new_value=recommended)
        elif result.get("fallback_available"):
            draft.slot_status = SLOT_STATUS_FALLBACK
            # Build fallback inquiry payload
            draft.fallback_inquiry_payload = self._build_fallback_payload(draft)
            await self._emit_event(draft.id, ACTOR_BACKEND, EVENT_FALLBACK_INQUIRY_PREPARED)

        await self.db.flush()
        await self.db.refresh(draft)
        return {**draft.to_dict(), **result}

    # ══════════════════════════════════════════════════════════════════════════
    # 10. SELECT SLOT
    # ══════════════════════════════════════════════════════════════════════════

    async def select_slot(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
        tenant_id: uuid.UUID,
        slot_date: str,
        start_time: str,
        end_time: str,
        mode: str | None = None,
        staff_member_id: uuid.UUID | None = None,
    ) -> dict:
        draft = await self._get_draft(draft_id, customer_id)
        self._guard_terminal(draft)

        slot_date_obj  = datetime.strptime(slot_date, "%Y-%m-%d").date()
        start_time_obj = datetime.strptime(start_time, "%H:%M").time()
        end_time_obj   = datetime.strptime(end_time, "%H:%M").time()

        # Verify slot is actually available (backend validates — no fake slots)
        slot_result = await self._slot_svc.get_available_slots(
            tenant_id=tenant_id,
            offering_id=draft.offering_id,
            date_str=slot_date,
            preferred_mode=mode or draft.preferred_mode,
            exclude_draft_id=draft_id,
        )
        available_times = {s["start_time"] for s in slot_result.get("slots", [])}
        if start_time not in available_times:
            raise ServiceOSException(
                ERR_SLOT_ALREADY_HELD,
                f"Slot {start_time} on {slot_date} is not available (held or booked). Choose another slot.",
            )

        draft.selected_tenant_id   = tenant_id
        draft.selected_staff_member_id = staff_member_id
        draft.selected_date        = slot_date_obj
        draft.selected_time_start  = start_time_obj
        draft.selected_time_end    = end_time_obj
        draft.preferred_mode       = mode or draft.preferred_mode or MODE_OFFLINE
        draft.slot_snapshot        = {
            "tenant_id":       str(tenant_id),
            "slot_date":       slot_date,
            "start_time":      start_time,
            "end_time":        end_time,
            "mode":            mode or draft.preferred_mode,
            "staff_member_id": str(staff_member_id) if staff_member_id else None,
        }
        draft.slot_status = SLOT_STATUS_SELECTED
        draft.status      = DRAFT_STATUS_SLOT_SELECTED

        await self.db.flush()
        await self.db.refresh(draft)
        await self._emit_event(draft.id, ACTOR_CUSTOMER, EVENT_SLOT_SELECTED,
                               new_value=draft.slot_snapshot)

        # Auto-hold after selecting
        hold_result = await self.hold_slot(draft_id, customer_id)
        return {**draft.to_dict(), "slot_hold": hold_result}

    # ══════════════════════════════════════════════════════════════════════════
    # 11. HOLD SLOT
    # ══════════════════════════════════════════════════════════════════════════

    async def hold_slot(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
    ) -> dict:
        draft = await self._get_draft(draft_id, customer_id)

        if not draft.selected_date or not draft.selected_time_start:
            raise ServiceOSException(ERR_SLOT_REQUIRED, "No slot selected yet.")

        # Release any existing hold for this draft
        await self.release_slot_hold(draft_id, customer_id)

        expires_at = utcnow() + timedelta(minutes=SLOT_HOLD_EXPIRY_MINUTES)
        hold = CoachingAppointmentSlotHold(
            draft_id=draft_id,
            tenant_id=draft.selected_tenant_id,
            staff_member_id=draft.selected_staff_member_id,
            offering_id=draft.offering_id,
            slot_date=draft.selected_date,
            start_time=draft.selected_time_start,
            end_time=draft.selected_time_end,
            hold_status=HOLD_STATUS_HELD,
            expires_at=expires_at,
        )
        self.db.add(hold)
        await self.db.flush()
        await self.db.refresh(hold)

        draft.slot_status = SLOT_STATUS_HELD
        await self.db.flush()
        await self.db.refresh(draft)
        await self._emit_event(draft.id, ACTOR_BACKEND, EVENT_SLOT_HELD,
                               new_value={"expires_at": expires_at.isoformat()})

        return {
            "hold_id":        str(hold.id),
            "expires_at":     expires_at.isoformat(),
            "hold_ttl_min":   SLOT_HOLD_EXPIRY_MINUTES,
            "message":        f"Slot held for {SLOT_HOLD_EXPIRY_MINUTES} minutes.",
        }

    # ══════════════════════════════════════════════════════════════════════════
    # 12. RELEASE SLOT HOLD
    # ══════════════════════════════════════════════════════════════════════════

    async def release_slot_hold(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None = None,
    ) -> dict:
        r = await self.db.execute(
            select(CoachingAppointmentSlotHold).where(
                CoachingAppointmentSlotHold.draft_id == draft_id,
                CoachingAppointmentSlotHold.hold_status == HOLD_STATUS_HELD,
            )
        )
        holds = r.scalars().all()
        for h in holds:
            h.hold_status = HOLD_STATUS_RELEASED
        await self.db.flush()
        return {"released": len(holds)}

    # ══════════════════════════════════════════════════════════════════════════
    # 13. RESOLVE APPOINTMENT FEE
    # ══════════════════════════════════════════════════════════════════════════

    async def resolve_appointment_fee(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
    ) -> dict:
        draft = await self._get_draft(draft_id, customer_id)

        try:
            from app.engines.admin_catalog.models import MasterOffering
            r = await self.db.execute(
                select(MasterOffering).where(MasterOffering.id == draft.offering_id)
            )
            offering = r.scalar_one_or_none()
            if not offering:
                raise ServiceOSException(ERR_FEE_ESTIMATE_FAILED, "Offering not found.")

            appt_fee = offering.default_appointment_fee or Decimal("0")
            currency = offering.currency or "INR"

            if appt_fee == 0:
                fee_type    = "free"
                display_fee = "Free"
                message     = f"This {offering.name} is free. No appointment fee required."
                draft.fee_status = FEE_STATUS_FREE
            else:
                fee_type    = "fixed"
                display_fee = f"₹{appt_fee:,.0f}"
                message     = f"Appointment fee is {display_fee}."
                draft.fee_status = FEE_STATUS_ESTIMATED

            fee_snapshot = {
                "fee_type":    fee_type,
                "amount":      float(appt_fee),
                "currency":    currency,
                "display_fee": display_fee,
                "message":     message,
                "source":      "backend_catalog",
            }
            draft.appointment_fee_snapshot = fee_snapshot
            await self.db.flush()
            await self.db.refresh(draft)
            await self._emit_event(draft.id, ACTOR_BACKEND, EVENT_FEE_ESTIMATED,
                                   new_value=fee_snapshot)
            return {**draft.to_dict(), "fee_snapshot": fee_snapshot}

        except ServiceOSException:
            raise
        except Exception as exc:
            draft.fee_status = FEE_STATUS_FAILED
            await self.db.flush()
            logger.warning("coaching.resolve_fee.failed", error=str(exc))
            raise ServiceOSException(ERR_FEE_ESTIMATE_FAILED, "Unable to resolve appointment fee.")

    # ══════════════════════════════════════════════════════════════════════════
    # 14. BUILD APPOINTMENT SUMMARY
    # ══════════════════════════════════════════════════════════════════════════

    async def build_appointment_summary(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
    ) -> dict:
        draft = await self._get_draft(draft_id, customer_id)

        try:
            from app.engines.admin_catalog.models import MasterOffering, ServiceCategory
            r = await self.db.execute(
                select(MasterOffering).where(MasterOffering.id == draft.offering_id)
            )
            offering = r.scalar_one_or_none()
            from app.engines.tenant_engine.models import Tenant
            center = None
            if draft.selected_tenant_id:
                cr = await self.db.execute(
                    select(Tenant).where(Tenant.id == draft.selected_tenant_id)
                )
                center = cr.scalar_one_or_none()

        except Exception:
            offering = None
            center   = None

        summary = {
            "offering_name":     offering.name if offering else str(draft.offering_id),
            "preferred_mode":    draft.preferred_mode,
            "city":              draft.city,
            "zipcode":           draft.zipcode,
            "center_name":       (center.business_name or center.tenant_name) if center else None,
            "selected_date":     draft.selected_date.isoformat() if draft.selected_date else None,
            "selected_time":     draft.selected_time_start.isoformat() if draft.selected_time_start else None,
            "student_name":      draft.student_name,
            "student_phone":     draft.student_phone,
            "student_email":     draft.student_email,
            "target_exam":       draft.target_exam,
            "target_band":       draft.target_band,
            "appointment_fee":   draft.appointment_fee_snapshot,
            "notes":             draft.notes,
        }

        draft.appointment_summary = summary
        await self.db.flush()
        await self.db.refresh(draft)
        await self._emit_event(draft.id, ACTOR_BACKEND, EVENT_SUMMARY_GENERATED)
        return {**draft.to_dict(), "appointment_summary": summary}

    # ══════════════════════════════════════════════════════════════════════════
    # 15. PREPARE FALLBACK INQUIRY PAYLOAD
    # ══════════════════════════════════════════════════════════════════════════

    async def prepare_fallback_inquiry_payload(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
    ) -> dict:
        draft = await self._get_draft(draft_id, customer_id)
        payload = self._build_fallback_payload(draft)
        draft.fallback_inquiry_payload = payload
        draft.slot_status = SLOT_STATUS_FALLBACK
        await self.db.flush()
        await self.db.refresh(draft)
        await self._emit_event(draft.id, ACTOR_BACKEND, EVENT_FALLBACK_INQUIRY_PREPARED,
                               new_value=payload)
        return {
            **draft.to_dict(),
            "fallback_available": True,
            "fallback_type":      "center_call_back_request",
            "fallback_payload":   payload,
            "message":            "No slots are available right now, but we can ask the center to call you when a slot opens.",
        }

    # ══════════════════════════════════════════════════════════════════════════
    # 16. MARK READY FOR CONFIRMATION
    # ══════════════════════════════════════════════════════════════════════════

    async def mark_ready_for_confirmation(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
    ) -> dict:
        draft = await self._get_draft(draft_id, customer_id)
        self._guard_terminal(draft)

        missing = await self._get_missing_fields_for_draft(draft)
        if missing:
            raise ServiceOSException(ERR_REQUIRED_FIELD_MISSING,
                                     f"Missing required fields: {', '.join(missing)}")

        # Must have a held slot
        hold_r = await self.db.execute(
            select(CoachingAppointmentSlotHold).where(
                CoachingAppointmentSlotHold.draft_id == draft_id,
                CoachingAppointmentSlotHold.hold_status == HOLD_STATUS_HELD,
                CoachingAppointmentSlotHold.expires_at > utcnow(),
            )
        )
        hold = hold_r.scalar_one_or_none()
        if not hold:
            raise ServiceOSException(ERR_SLOT_REQUIRED,
                                     "Slot must be held before confirming. Select and hold a slot first.")

        draft.status = DRAFT_STATUS_READY_FOR_CONFIRMATION
        await self.db.flush()
        await self.db.refresh(draft)
        return {**draft.to_dict(), "ready_for_confirmation": True}

    # ══════════════════════════════════════════════════════════════════════════
    # 17. CONFIRM DRAFT
    # ══════════════════════════════════════════════════════════════════════════

    async def confirm_draft(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
    ) -> dict:
        draft = await self._get_draft(draft_id, customer_id)
        if draft.status not in {DRAFT_STATUS_SLOT_SELECTED, DRAFT_STATUS_READY_FOR_CONFIRMATION}:
            raise ServiceOSException(
                ERR_CONFIRMATION_NOT_READY,
                f"Draft must be in slot_selected or ready_for_confirmation status (current: {draft.status}).",
            )

        # Verify slot hold is still active
        hold_r = await self.db.execute(
            select(CoachingAppointmentSlotHold).where(
                CoachingAppointmentSlotHold.draft_id == draft_id,
                CoachingAppointmentSlotHold.hold_status == HOLD_STATUS_HELD,
                CoachingAppointmentSlotHold.expires_at > utcnow(),
            )
        )
        hold = hold_r.scalar_one_or_none()
        if not hold:
            raise ServiceOSException(
                ERR_SLOT_REQUIRED,
                "Slot hold has expired. Please select and hold a slot again.",
            )

        draft.status = DRAFT_STATUS_CONFIRMED
        await self.db.flush()
        await self.db.refresh(draft)
        await self._emit_event(draft.id, ACTOR_CUSTOMER, EVENT_DRAFT_CONFIRMED)

        payload = {
            "category_id":           str(draft.category_id),
            "offering_id":           str(draft.offering_id),
            "tenant_id":             str(draft.selected_tenant_id) if draft.selected_tenant_id else None,
            "staff_member_id":       str(draft.selected_staff_member_id) if draft.selected_staff_member_id else None,
            "slot_snapshot":         draft.slot_snapshot,
            "student_snapshot": {
                "student_name":      draft.student_name,
                "student_phone":     draft.student_phone,
                "student_email":     draft.student_email,
                "student_age":       draft.student_age,
                "target_exam":       draft.target_exam,
                "target_band":       draft.target_band,
                "preferred_mode":    draft.preferred_mode,
                "city":              draft.city,
                "zipcode":           draft.zipcode,
            },
            "appointment_fee_snapshot": draft.appointment_fee_snapshot,
        }
        return {
            "success": True,
            "data": {
                "draft_id":  str(draft.id),
                "status":    "confirmed",
                "next_step": "final_appointment_creation_in_sprint_19",
                "appointment_ready_payload": payload,
            },
        }

    # ══════════════════════════════════════════════════════════════════════════
    # 18. CANCEL DRAFT
    # ══════════════════════════════════════════════════════════════════════════

    async def cancel_draft(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
        reason: str | None = None,
    ) -> dict:
        draft = await self._get_draft(draft_id, customer_id)
        if draft.status in TERMINAL_STATUSES:
            raise ServiceOSException(ERR_DRAFT_TERMINAL, f"Draft is already {draft.status}.")

        draft.status = DRAFT_STATUS_CANCELLED
        await self.release_slot_hold(draft_id)
        await self.db.flush()
        await self.db.refresh(draft)
        await self._emit_event(draft.id, ACTOR_CUSTOMER, EVENT_DRAFT_CANCELLED,
                               message=reason)
        return {**draft.to_dict(), "cancelled": True}

    # ══════════════════════════════════════════════════════════════════════════
    # 19. EXPIRE OLD DRAFTS AND SLOT HOLDS
    # ══════════════════════════════════════════════════════════════════════════

    async def expire_old_drafts_and_slot_holds(self) -> dict:
        now = utcnow()

        # Expire drafts
        r = await self.db.execute(
            select(CoachingAppointmentDraft).where(
                CoachingAppointmentDraft.expires_at < now,
                CoachingAppointmentDraft.status.not_in(list(TERMINAL_STATUSES)),
            )
        )
        drafts = r.scalars().all()
        for d in drafts:
            d.status = DRAFT_STATUS_EXPIRED

        # Expire slot holds
        r2 = await self.db.execute(
            select(CoachingAppointmentSlotHold).where(
                CoachingAppointmentSlotHold.expires_at < now,
                CoachingAppointmentSlotHold.hold_status == HOLD_STATUS_HELD,
            )
        )
        holds = r2.scalars().all()
        for h in holds:
            h.hold_status = HOLD_STATUS_EXPIRED

        await self.db.flush()
        return {"expired_drafts": len(drafts), "expired_holds": len(holds)}

    # ══════════════════════════════════════════════════════════════════════════
    # ADMIN METHODS
    # ══════════════════════════════════════════════════════════════════════════

    async def admin_list_drafts(
        self,
        status: str | None = None,
        city: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        q = select(CoachingAppointmentDraft).order_by(
            CoachingAppointmentDraft.created_at.desc()
        )
        if status:
            q = q.where(CoachingAppointmentDraft.status == status)
        if city:
            q = q.where(CoachingAppointmentDraft.city.ilike(f"%{city}%"))

        offset = (page - 1) * page_size
        q = q.offset(offset).limit(page_size)
        rows = (await self.db.execute(q)).scalars().all()
        return {
            "drafts": [r.to_dict() for r in rows],
            "page": page,
            "page_size": page_size,
        }

    async def admin_get_draft(self, draft_id: uuid.UUID) -> dict:
        r = await self.db.execute(
            select(CoachingAppointmentDraft).where(CoachingAppointmentDraft.id == draft_id)
        )
        draft = r.scalar_one_or_none()
        if not draft:
            raise ServiceOSException(ERR_DRAFT_NOT_FOUND, f"Draft {draft_id} not found.")
        return draft.to_dict()

    async def admin_get_draft_events(self, draft_id: uuid.UUID) -> dict:
        r = await self.db.execute(
            select(CoachingAppointmentDraftEvent).where(
                CoachingAppointmentDraftEvent.draft_id == draft_id
            ).order_by(CoachingAppointmentDraftEvent.created_at)
        )
        events = r.scalars().all()
        return {"draft_id": str(draft_id), "events": [e.to_dict() for e in events]}

    async def admin_list_slot_holds(
        self,
        status: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        q = select(CoachingAppointmentSlotHold).order_by(
            CoachingAppointmentSlotHold.created_at.desc()
        )
        if status:
            q = q.where(CoachingAppointmentSlotHold.hold_status == status)
        offset = (page - 1) * page_size
        q = q.offset(offset).limit(page_size)
        rows = (await self.db.execute(q)).scalars().all()
        return {"holds": [r.to_dict() for r in rows], "page": page, "page_size": page_size}

    # ══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    async def _get_draft(
        self,
        draft_id: uuid.UUID,
        customer_id: uuid.UUID | None,
    ) -> CoachingAppointmentDraft:
        r = await self.db.execute(
            select(CoachingAppointmentDraft).where(CoachingAppointmentDraft.id == draft_id)
        )
        draft = r.scalar_one_or_none()
        if not draft:
            raise ServiceOSException(ERR_DRAFT_NOT_FOUND, f"Draft {draft_id} not found.")
        if customer_id and draft.customer_id and draft.customer_id != customer_id:
            raise ServiceOSException(ERR_DRAFT_ACCESS_DENIED, "Access denied to this draft.")
        return draft

    def _guard_terminal(self, draft: CoachingAppointmentDraft) -> None:
        if draft.status in TERMINAL_STATUSES:
            raise ServiceOSException(ERR_DRAFT_TERMINAL,
                                     f"Draft is in terminal status ({draft.status}). No further updates allowed.")

    async def _get_missing_fields_for_draft(self, draft: CoachingAppointmentDraft) -> list[str]:
        try:
            from app.engines.admin_catalog.models import MasterOffering
            r = await self.db.execute(
                select(MasterOffering).where(MasterOffering.id == draft.offering_id)
            )
            offering = r.scalar_one_or_none()
        except Exception:
            offering = None
        return self._compute_missing_fields(draft, offering)

    def _compute_required_fields(self, offering: Any) -> list[str]:
        fields = ["student_name", "student_phone", "preferred_mode", "selected_date"]
        if offering and getattr(offering, "requires_address", False):
            fields.append("city")
        if offering and getattr(offering, "requires_slot", False):
            fields.append("selected_date")
        return list(dict.fromkeys(fields))  # deduplicate preserving order

    def _compute_missing_fields(self, draft: CoachingAppointmentDraft, offering: Any) -> list[str]:
        missing: list[str] = []
        if not draft.student_name:
            missing.append("student_name")
        if not draft.student_phone:
            missing.append("student_phone")
        if not draft.preferred_mode:
            missing.append("preferred_mode")
        if not draft.selected_date:
            missing.append("selected_date")
        if draft.preferred_mode == MODE_OFFLINE and not draft.city:
            missing.append("city")
        if offering and getattr(offering, "requires_slot", False) and not draft.slot_snapshot:
            missing.append("selected_slot")
        return missing

    def _build_fallback_payload(self, draft: CoachingAppointmentDraft) -> dict:
        return {
            "customer_name":   draft.student_name,
            "customer_phone":  draft.student_phone,
            "offering_id":     str(draft.offering_id),
            "preferred_mode":  draft.preferred_mode,
            "city":            draft.city,
            "zipcode":         draft.zipcode,
            "preferred_date":  draft.selected_date.isoformat() if draft.selected_date else None,
            "target_exam":     draft.target_exam,
            "notes":           draft.notes,
            "reason":          "no_slot_available",
        }

    async def _emit_event(
        self,
        draft_id: uuid.UUID,
        actor_type: str,
        event_type: str,
        old_value: dict | None = None,
        new_value: dict | None = None,
        message: str | None = None,
    ) -> None:
        try:
            event = CoachingAppointmentDraftEvent(
                draft_id=draft_id,
                actor_type=actor_type,
                event_type=event_type,
                old_value=old_value,
                new_value=new_value,
                message=message,
                request_id=self.request_id,
            )
            self.db.add(event)
            await self.db.flush()
        except Exception as exc:
            logger.warning("coaching.emit_event.failed", error=str(exc))
