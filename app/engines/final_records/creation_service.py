"""Sprint 19 — FinalCreationService.

Converts confirmed chatbot drafts into real records:
  HomeServiceBookingDraft  → ServiceBooking + ServiceJob
  CoachingAppointmentDraft → CoachingAppointment
  RealEstateLeadDraft      → RealEstateLead

Replaces the old svc.confirm_draft() call in each engine's router.
Each finalize() method:
  1. Checks idempotency — returns existing record if already confirmed
  2. Validates draft ownership and status (ready_for_confirmation)
  3. Generates sequential number
  4. Creates final record(s)
  5. Marks draft confirmed + emits draft event
  6. Creates CustomerBookingConfirmation (idempotency lock)
  7. Logs to FinalCreationAuditLog
  8. Returns result dict

Caller is responsible for committing the DB session after this returns.
Does NOT push notifications or assign technicians (Sprint 20+).
"""
from __future__ import annotations
import uuid
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import datetime, timezone

from app.engines.final_records.constants import (
    DRAFT_TYPE_HOME_SERVICE, DRAFT_TYPE_COACHING, DRAFT_TYPE_REAL_ESTATE,
    RESULT_TYPE_SERVICE_BOOKING, RESULT_TYPE_COACHING_APPOINTMENT, RESULT_TYPE_REAL_ESTATE_LEAD,
    AUDIT_BOOKING_CREATED, AUDIT_APPOINTMENT_CREATED, AUDIT_LEAD_CREATED,
    AUDIT_CONFIRMATION_DUPLICATE,
    ERR_DRAFT_NOT_FOUND, ERR_DRAFT_NOT_READY, ERR_ACCESS_DENIED,
    ERR_SLOT_HOLD_MISSING, ERR_SLOT_HOLD_EXPIRED, ERR_SLOT_HOLD_ALREADY_CONVERTED,
)
from app.engines.final_records.idempotency import ConfirmationLockService
from app.engines.final_records.models import (
    ServiceBooking, ServiceJob, CoachingAppointment, RealEstateLead, FinalCreationAuditLog,
)
from app.engines.final_records.number_service import (
    generate_booking_number, generate_job_number,
    generate_appointment_number, generate_lead_number,
)

log = logging.getLogger(__name__)

_READY     = "ready_for_confirmation"
_CONFIRMED = "confirmed"
_TERMINAL  = {"confirmed", "expired", "cancelled", "failed"}
_utcnow    = lambda: datetime.now(timezone.utc)


def _uuid(val) -> uuid.UUID | None:
    if val is None:
        return None
    return val if isinstance(val, uuid.UUID) else uuid.UUID(str(val))


class HomeServiceFinalCreationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db   = db
        self.lock = ConfirmationLockService(db)

    async def finalize(
        self,
        draft_id:        uuid.UUID,
        customer_id:     uuid.UUID | None = None,
        idempotency_key: str | None       = None,
        request_id:      str | None       = None,
    ) -> dict:
        from app.engines.home_service_booking.models import (
            HomeServiceBookingDraft, HomeServiceBookingDraftEvent,
        )

        # 1. Idempotency — return existing if already confirmed
        existing = await self.lock.check_and_raise_if_duplicate(DRAFT_TYPE_HOME_SERVICE, draft_id)
        if existing:
            await self._audit(AUDIT_CONFIRMATION_DUPLICATE, DRAFT_TYPE_HOME_SERVICE, draft_id,
                              RESULT_TYPE_SERVICE_BOOKING, existing.result_id, existing.result_number,
                              customer_id, None, request_id, {"reason": "duplicate_confirmation"})
            return {
                "idempotent":      True,
                "booking_number":  existing.result_number,
                "booking_id":      str(existing.result_id),
                "confirmation_id": str(existing.id),
            }

        # 2. Load + validate draft
        result = await self.db.execute(
            select(HomeServiceBookingDraft).where(HomeServiceBookingDraft.id == draft_id)
        )
        draft = result.scalars().first()
        if not draft:
            raise ValueError(ERR_DRAFT_NOT_FOUND)
        if customer_id and draft.customer_id and draft.customer_id != customer_id:
            raise ValueError(ERR_ACCESS_DENIED)
        if draft.status != _READY:
            raise ValueError(ERR_DRAFT_NOT_READY)

        # HOME-SERVICES-RUNTIME-SAFETY Phase 2A.2 (spec section 8): finalize()
        # must INDEPENDENTLY revalidate Job Type/Blueprint context, not trust
        # that mark_ready_for_confirmation's earlier check still holds --
        # time has passed (an admin could have deactivated the job type or
        # published a new blueprint version in the window between the draft
        # becoming ready and the customer clicking confirm). No partial
        # Booking/Job may be created if this fails.
        from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
        job_type_error = await HomeServiceChatbotBookingService(db=self.db)._validate_job_type_context(draft)
        if job_type_error:
            raise ValueError(job_type_error["code"])

        # 3. Generate numbers
        booking_number = await generate_booking_number(self.db)
        job_number     = await generate_job_number(self.db)

        # HS7 fix: the customer's selected price tier/amount and the
        # constant Home-Services payment mode lived only in
        # draft.booking_summary (set by confirm_price_choice) and were never
        # copied onto the booking's own price_snapshot — customer-facing
        # booking tracking/detail screens had no way to show which tier was
        # actually chosen once the draft was gone.
        draft_summary = draft.booking_summary or {}
        booking_price_snapshot = {
            **(draft.price_snapshot or {}),
            "selected_price_option": draft_summary.get("selected_price_tier"),
            "selected_price_amount": draft_summary.get("customer_offer"),
            "payment_mode":          "customer_pays_provider_directly",
        }

        # 4a. Create ServiceBooking
        booking = ServiceBooking(
            booking_number        = booking_number,
            draft_id              = draft.id,
            customer_id           = draft.customer_id,
            tenant_id             = draft.selected_tenant_id,
            category_id           = draft.category_id,
            offering_id           = draft.offering_id,
            # Phase 2A.1: read ONLY from the trusted, already-validated draft
            # state -- finalize()'s own signature has no job-type-bearing
            # parameter, so there is no confirmation-payload path that could
            # ever override this.
            job_type_id           = draft.job_type_id,
            # Phase 2A.2: the exact catalog link + the exact IMMUTABLE
            # workflow-version row snapshotted when the draft resolved its
            # Job Type -- never re-derived here, never re-resolved to
            # "whatever is current now".
            master_service_job_type_id = draft.master_service_job_type_id,
            service_job_workflow_id    = draft.service_job_workflow_id,
            selected_problem_id        = draft.selected_problem_id,
            ai_session_id         = draft.ai_session_id,
            customer_name         = draft.customer_name,
            customer_phone        = draft.customer_phone,
            city                  = draft.city,
            zipcode               = draft.zipcode,
            address_snapshot      = draft.address_snapshot,
            preferred_date        = draft.preferred_date,
            preferred_time_window = draft.preferred_time_window,
            price_snapshot        = booking_price_snapshot,
            provider_snapshot     = draft.selected_provider_snapshot,
            issue_summary         = draft.issue_summary,
            issue_details         = draft.issue_details,
            status                = "pending_assignment",
        )
        self.db.add(booking)
        await self.db.flush()
        await self.db.refresh(booking)

        # 4b. Create ServiceJob
        job = ServiceJob(
            job_number            = job_number,
            booking_id            = booking.id,
            customer_id           = draft.customer_id,
            tenant_id             = draft.selected_tenant_id,
            category_id           = draft.category_id,
            offering_id           = draft.offering_id,
            # Phase 2A.1: copied from the booking just created above (itself
            # copied only from the trusted draft), so booking and job always
            # agree on the exact Job Type.
            job_type_id           = booking.job_type_id,
            master_service_job_type_id = booking.master_service_job_type_id,
            service_job_workflow_id    = booking.service_job_workflow_id,
            selected_problem_id        = booking.selected_problem_id,
            scheduled_date        = draft.preferred_date,
            scheduled_time_window = draft.preferred_time_window,
            city                  = draft.city,
            zipcode               = draft.zipcode,
            address_snapshot      = draft.address_snapshot,
            status                = "pending_assignment",
        )
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)

        # 5. Confirm draft + emit event
        draft.status = _CONFIRMED
        event = HomeServiceBookingDraftEvent(
            draft_id   = draft.id,
            actor_type = "backend",
            event_type = "draft_confirmed",
            new_value  = {"status": _CONFIRMED, "booking_number": booking_number},
            message    = f"Booking {booking_number} and Job {job_number} created",
            request_id = request_id,
        )
        self.db.add(event)
        await self.db.flush()

        # 6. Confirmation lock
        confirmation = await self.lock.create_lock(
            draft_type      = DRAFT_TYPE_HOME_SERVICE,
            draft_id        = draft.id,
            customer_id     = draft.customer_id,
            idempotency_key = idempotency_key,
            result_type     = RESULT_TYPE_SERVICE_BOOKING,
            result_id       = booking.id,
            result_number   = booking_number,
        )

        # 7. Audit
        await self._audit(AUDIT_BOOKING_CREATED, DRAFT_TYPE_HOME_SERVICE, draft.id,
                          RESULT_TYPE_SERVICE_BOOKING, booking.id, booking_number,
                          draft.customer_id, draft.selected_tenant_id, request_id,
                          {"job_id": str(job.id), "job_number": job_number})

        # 8. MODULE-L5-27: tell the provider a new booking arrived so they assign a
        # technician, and confirm to the customer. Confirming a booking only
        # emitted internal events, so the provider had to poll to discover new
        # work and the customer got no bell notification.
        await self._notify_booking_confirmed(
            booking_id=booking.id, booking_number=booking_number,
            tenant_id=draft.selected_tenant_id, customer_id=draft.customer_id)

        booking_summary = draft.booking_summary or {}
        return {
            "idempotent":                  False,
            "booking_number":              booking_number,
            "booking_id":                  str(booking.id),
            "job_number":                  job_number,
            "job_id":                      str(job.id),
            "status":                      booking.status,
            "booking_status":              "confirmed",
            "confirmation_id":             str(confirmation.id),
            "selected_provider_tenant_id": str(draft.selected_tenant_id) if draft.selected_tenant_id else None,
            "selected_price_option":       booking_summary.get("selected_price_tier"),
            "selected_price_amount":       booking_summary.get("customer_offer"),
            "payment_mode":                "customer_pays_provider_directly",
        }

    async def _notify_booking_confirmed(self, *, booking_id, booking_number,
                                        tenant_id, customer_id) -> None:
        """Notify the provider (a new booking to staff) and the customer (their
        booking is confirmed). Best-effort — never block confirmation on it."""
        try:
            from app.engines.platform_notifications.models import InAppNotification
            if customer_id:
                self.db.add(InAppNotification(
                    user_id=customer_id, tenant_id=tenant_id,
                    notification_type="booking.confirmed",
                    title="Your booking is confirmed",
                    body=f"Booking {booking_number} is confirmed. We'll assign a professional shortly.",
                    action_url=f"/customer/bookings/{booking_id}",
                    action_label="View booking",
                    source_record_type="service_bookings", source_record_id=booking_id,
                    severity="info"))
            if tenant_id:
                from app.engines.tenant_engine.models import Tenant
                tenant = await self.db.get(Tenant, tenant_id)
                owner_id = getattr(tenant, "owner_user_id", None) if tenant else None
                if owner_id:
                    self.db.add(InAppNotification(
                        user_id=owner_id, tenant_id=tenant_id,
                        notification_type="booking.new",
                        title="New booking received",
                        body=f"Booking {booking_number} came in. Assign a technician to get started.",
                        action_url="/service-jobs",
                        action_label="View jobs",
                        source_record_type="service_bookings", source_record_id=booking_id,
                        severity="info"))
        except Exception:
            # Notification must never break booking confirmation.
            pass

    async def _audit(self, action, draft_type, draft_id, result_type, result_id, result_number,
                     customer_id, tenant_id, request_id, details=None):
        try:
            self.db.add(FinalCreationAuditLog(
                action=action, draft_type=draft_type, draft_id=draft_id,
                result_type=result_type, result_id=result_id, result_number=result_number,
                customer_id=customer_id, tenant_id=tenant_id, request_id=request_id,
                details=details or {},
            ))
            await self.db.flush()
        except Exception as exc:
            log.warning("audit log failed: %s", exc)


class CoachingFinalCreationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db   = db
        self.lock = ConfirmationLockService(db)

    async def finalize(
        self,
        draft_id:        uuid.UUID,
        customer_id:     uuid.UUID | None = None,
        idempotency_key: str | None       = None,
        request_id:      str | None       = None,
    ) -> dict:
        from app.engines.coaching_appointment.models import (
            CoachingAppointmentDraft, CoachingAppointmentDraftEvent,
            CoachingAppointmentSlotHold,
        )

        # 1. Idempotency
        existing = await self.lock.check_and_raise_if_duplicate(DRAFT_TYPE_COACHING, draft_id)
        if existing:
            await self._audit(AUDIT_CONFIRMATION_DUPLICATE, DRAFT_TYPE_COACHING, draft_id,
                              RESULT_TYPE_COACHING_APPOINTMENT, existing.result_id, existing.result_number,
                              customer_id, None, request_id, {"reason": "duplicate_confirmation"})
            return {
                "idempotent":         True,
                "appointment_number": existing.result_number,
                "appointment_id":     str(existing.result_id),
                "confirmation_id":    str(existing.id),
            }

        # 2. Load + validate draft
        result = await self.db.execute(
            select(CoachingAppointmentDraft).where(CoachingAppointmentDraft.id == draft_id)
        )
        draft = result.scalars().first()
        if not draft:
            raise ValueError(ERR_DRAFT_NOT_FOUND)
        if customer_id and draft.customer_id and draft.customer_id != customer_id:
            raise ValueError(ERR_ACCESS_DENIED)
        if draft.status != _READY:
            raise ValueError(ERR_DRAFT_NOT_READY)

        # 2b. Find and validate slot hold — must exist, be held, and not expired
        hold_result = await self.db.execute(
            select(CoachingAppointmentSlotHold).where(
                CoachingAppointmentSlotHold.draft_id == draft.id,
            )
        )
        slot_hold = hold_result.scalars().first()

        if not slot_hold:
            raise ValueError(ERR_SLOT_HOLD_MISSING)
        if slot_hold.hold_status == "converted":
            raise ValueError(ERR_SLOT_HOLD_ALREADY_CONVERTED)
        if slot_hold.hold_status != "held":
            raise ValueError(ERR_SLOT_HOLD_MISSING)
        if slot_hold.expires_at.replace(tzinfo=timezone.utc) <= _utcnow():
            raise ValueError(ERR_SLOT_HOLD_EXPIRED)

        # 3. Generate number
        appt_number = await generate_appointment_number(self.db)

        # 4. Create CoachingAppointment
        appt = CoachingAppointment(
            appointment_number       = appt_number,
            draft_id                 = draft.id,
            customer_id              = draft.customer_id,
            tenant_id                = draft.selected_tenant_id,
            category_id              = draft.category_id,
            offering_id              = draft.offering_id,
            ai_session_id            = draft.ai_session_id,
            staff_member_id          = draft.selected_staff_member_id,
            student_name             = draft.student_name,
            student_phone            = draft.student_phone,
            student_email            = draft.student_email,
            target_exam              = draft.target_exam,
            target_band              = draft.target_band,
            preferred_mode           = draft.preferred_mode,
            selected_date            = draft.selected_date,
            selected_time_start      = draft.selected_time_start,
            selected_time_end        = draft.selected_time_end,
            city                     = draft.city,
            appointment_fee_snapshot = draft.appointment_fee_snapshot,
            provider_snapshot        = draft.selected_provider_snapshot,
            status                   = "confirmed",
        )
        self.db.add(appt)
        await self.db.flush()
        await self.db.refresh(appt)

        # 4b. Convert slot hold — same transaction as appointment creation
        slot_hold.hold_status = "converted"
        await self.db.flush()

        # 5. Confirm draft + emit event
        draft.status = _CONFIRMED
        event = CoachingAppointmentDraftEvent(
            draft_id   = draft.id,
            actor_type = "backend",
            event_type = "draft_confirmed",
            new_value  = {
                "status":             _CONFIRMED,
                "appointment_number": appt_number,
                "slot_hold_converted": str(slot_hold.id),
            },
            message    = f"Appointment {appt_number} created; slot hold {slot_hold.id} converted",
            request_id = request_id,
        )
        self.db.add(event)
        await self.db.flush()

        # 6. Confirmation lock
        confirmation = await self.lock.create_lock(
            draft_type      = DRAFT_TYPE_COACHING,
            draft_id        = draft.id,
            customer_id     = draft.customer_id,
            idempotency_key = idempotency_key,
            result_type     = RESULT_TYPE_COACHING_APPOINTMENT,
            result_id       = appt.id,
            result_number   = appt_number,
        )

        # 7. Audit
        await self._audit(AUDIT_APPOINTMENT_CREATED, DRAFT_TYPE_COACHING, draft.id,
                          RESULT_TYPE_COACHING_APPOINTMENT, appt.id, appt_number,
                          draft.customer_id, draft.selected_tenant_id, request_id,
                          {"slot_hold_id": str(slot_hold.id), "slot_hold_converted": True})

        return {
            "idempotent":         False,
            "appointment_number": appt_number,
            "appointment_id":     str(appt.id),
            "status":             appt.status,
            "confirmation_id":    str(confirmation.id),
            "slot_hold_converted": True,
        }

    async def _audit(self, action, draft_type, draft_id, result_type, result_id, result_number,
                     customer_id, tenant_id, request_id, details=None):
        try:
            self.db.add(FinalCreationAuditLog(
                action=action, draft_type=draft_type, draft_id=draft_id,
                result_type=result_type, result_id=result_id, result_number=result_number,
                customer_id=customer_id, tenant_id=tenant_id, request_id=request_id,
                details=details or {},
            ))
            await self.db.flush()
        except Exception as exc:
            log.warning("audit log failed: %s", exc)


class RealEstateFinalCreationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db   = db
        self.lock = ConfirmationLockService(db)

    async def finalize(
        self,
        draft_id:        uuid.UUID,
        customer_id:     uuid.UUID | None = None,
        idempotency_key: str | None       = None,
        request_id:      str | None       = None,
    ) -> dict:
        from app.engines.real_estate_lead.models import RealEstateLeadDraft
        # Real estate drafts use different event model
        from app.engines.real_estate_lead.models import RealEstateLeadDraftEvent

        # 1. Idempotency
        existing = await self.lock.check_and_raise_if_duplicate(DRAFT_TYPE_REAL_ESTATE, draft_id)
        if existing:
            await self._audit(AUDIT_CONFIRMATION_DUPLICATE, DRAFT_TYPE_REAL_ESTATE, draft_id,
                              RESULT_TYPE_REAL_ESTATE_LEAD, existing.result_id, existing.result_number,
                              customer_id, None, request_id, {"reason": "duplicate_confirmation"})
            return {
                "idempotent":      True,
                "lead_number":     existing.result_number,
                "lead_id":         str(existing.result_id),
                "confirmation_id": str(existing.id),
            }

        # 2. Load + validate
        result = await self.db.execute(
            select(RealEstateLeadDraft).where(RealEstateLeadDraft.id == draft_id)
        )
        draft = result.scalars().first()
        if not draft:
            raise ValueError(ERR_DRAFT_NOT_FOUND)
        if customer_id and draft.customer_id and draft.customer_id != customer_id:
            raise ValueError(ERR_ACCESS_DENIED)
        if draft.status != _READY:
            raise ValueError(ERR_DRAFT_NOT_READY)

        # 3. Generate number
        lead_number = await generate_lead_number(self.db)

        # 4. Build lead_score_snapshot from lead_score table if available
        lead_score_snapshot = None
        try:
            from app.engines.real_estate_lead.models import RealEstateLeadScore
            score_result = await self.db.execute(
                select(RealEstateLeadScore).where(RealEstateLeadScore.draft_id == draft.id)
                .order_by(RealEstateLeadScore.created_at.desc()).limit(1)
            )
            score_row = score_result.scalars().first()
            if score_row:
                lead_score_snapshot = {
                    "score": score_row.score,
                    "label": score_row.label,
                }
        except Exception:
            pass

        # 5. Create RealEstateLead
        lead = RealEstateLead(
            lead_number           = lead_number,
            draft_id              = draft.id,
            customer_id           = draft.customer_id,
            tenant_id             = draft.selected_tenant_id,
            agent_id              = draft.selected_agent_id,
            category_id           = draft.category_id,
            offering_id           = draft.offering_id,
            ai_session_id         = draft.ai_session_id,
            lead_intent           = draft.lead_intent,
            property_type         = draft.property_type,
            city                  = draft.city,
            locality              = draft.locality,
            zipcode               = draft.zipcode,
            budget_min            = draft.budget_min,
            budget_max            = draft.budget_max,
            rent_min              = draft.rent_min,
            rent_max              = draft.rent_max,
            customer_snapshot     = {
                "name":                   draft.customer_name,
                "phone":                  draft.customer_phone,
                "email":                  draft.customer_email,
                "preferred_contact_time": draft.preferred_contact_time,
            },
            requirement_snapshot  = draft.requirement_snapshot or draft.lead_summary or {},
            lead_score_snapshot   = lead_score_snapshot,
            provider_snapshot     = draft.selected_provider_snapshot,
            fallback_payload      = draft.fallback_payload,
            status                = "new",
        )
        self.db.add(lead)
        await self.db.flush()
        await self.db.refresh(lead)

        # 6. Confirm draft + emit event
        draft.status = _CONFIRMED
        event = RealEstateLeadDraftEvent(
            draft_id   = draft.id,
            actor_type = "backend",
            event_type = "draft_confirmed",
            new_value  = {"status": _CONFIRMED, "lead_number": lead_number},
            message    = f"Lead {lead_number} created",
            request_id = request_id,
        )
        self.db.add(event)
        await self.db.flush()

        # 7. Confirmation lock
        confirmation = await self.lock.create_lock(
            draft_type      = DRAFT_TYPE_REAL_ESTATE,
            draft_id        = draft.id,
            customer_id     = draft.customer_id,
            idempotency_key = idempotency_key,
            result_type     = RESULT_TYPE_REAL_ESTATE_LEAD,
            result_id       = lead.id,
            result_number   = lead_number,
        )

        # 8. Audit
        await self._audit(AUDIT_LEAD_CREATED, DRAFT_TYPE_REAL_ESTATE, draft.id,
                          RESULT_TYPE_REAL_ESTATE_LEAD, lead.id, lead_number,
                          draft.customer_id, draft.selected_tenant_id, request_id,
                          {"lead_intent": draft.lead_intent, "city": draft.city})

        return {
            "idempotent":      False,
            "lead_number":     lead_number,
            "lead_id":         str(lead.id),
            "status":          lead.status,
            "confirmation_id": str(confirmation.id),
        }

    async def _audit(self, action, draft_type, draft_id, result_type, result_id, result_number,
                     customer_id, tenant_id, request_id, details=None):
        try:
            self.db.add(FinalCreationAuditLog(
                action=action, draft_type=draft_type, draft_id=draft_id,
                result_type=result_type, result_id=result_id, result_number=result_number,
                customer_id=customer_id, tenant_id=tenant_id, request_id=request_id,
                details=details or {},
            ))
            await self.db.flush()
        except Exception as exc:
            log.warning("audit log failed: %s", exc)
