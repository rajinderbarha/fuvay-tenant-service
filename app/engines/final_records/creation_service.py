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
from decimal import Decimal, InvalidOperation

from sqlalchemy import select, text as sa_text
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
from app.engines.execution.constants import JS_ACCEPTED
from app.engines.final_records.idempotency import ConfirmationLockService
from app.engines.final_records.models import (
    ServiceBooking, ServiceJob, CoachingAppointment, RealEstateLead, FinalCreationAuditLog,
)
from app.engines.final_records.number_service import (
    generate_booking_number, generate_job_number,
    generate_appointment_number, generate_lead_number,
)
from app.core.security import (
    enforce_booking_action_limits,
    enforce_social_confirmation_limit,
)
from app.exceptions import ServiceOSException
from app.config import get_settings

log = logging.getLogger(__name__)

_READY     = "ready_for_confirmation"
_CONFIRMED = "confirmed"
_TERMINAL  = {"confirmed", "expired", "cancelled", "failed"}
_utcnow    = lambda: datetime.now(timezone.utc)


def _uuid(val) -> uuid.UUID | None:
    if val is None:
        return None
    return val if isinstance(val, uuid.UUID) else uuid.UUID(str(val))


def _booking_service_amount(price_snapshot: dict | None) -> Decimal:
    """The service amount a platform fee is calculated against, in major units.

    Read from the booking's own frozen price snapshot, in the order of how
    specific each value is to what the customer actually agreed to:

      selected_price_amount -> the tier/amount they chose
      standard_price        -> the single fee-inclusive price they were shown
      base_price            -> the resolved service price
      visit_fee             -> inspection mode: the visit is the only amount
                              agreed up front, the repair is quoted later

    Returns 0 when the snapshot carries no usable amount. That is deliberate and
    safe: a zero-amount charge row still records the policy and preserves the
    audit trail, whereas GUESSING a service amount would compute a real fee
    against a number the customer never saw. An inspection-mode booking's repair
    fee is charged later from the approved quote (create_charge_for_quote), not
    here.
    """
    snapshot = price_snapshot or {}
    for key in ("selected_price_amount", "standard_price", "base_price", "visit_fee"):
        raw = snapshot.get(key)
        if raw in (None, ""):
            continue
        try:
            value = Decimal(str(raw))
        except (InvalidOperation, ValueError, TypeError):
            continue
        if value > 0:
            return value
    return Decimal("0")


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
        ip_address:      str | None       = None,
        source_channel:  str | None       = None,
        source_actor_id: str | None       = None,
    ) -> dict:
        from app.engines.home_service_booking.models import (
            HomeServiceBookingDraft, HomeServiceBookingDraftEvent,
        )

        # 1. Idempotency — return existing if already confirmed
        existing = await self.lock.check_and_raise_if_duplicate(DRAFT_TYPE_HOME_SERVICE, draft_id)
        if existing:
            # Keep retry responses contract-compatible with the first
            # confirmation. Mobile/API callers need the job id immediately
            # for tracking and a network retry must not mysteriously lose it.
            existing_job = (await self.db.execute(
                select(ServiceJob).where(ServiceJob.booking_id == existing.result_id)
            )).scalars().first()
            await self._audit(AUDIT_CONFIRMATION_DUPLICATE, DRAFT_TYPE_HOME_SERVICE, draft_id,
                              RESULT_TYPE_SERVICE_BOOKING, existing.result_id, existing.result_number,
                              customer_id, None, request_id, {"reason": "duplicate_confirmation"})
            return {
                "idempotent":      True,
                "booking_number":  existing.result_number,
                "booking_id":      str(existing.result_id),
                "job_number":      existing_job.job_number if existing_job else None,
                "job_id":          str(existing_job.id) if existing_job else None,
                "status":          existing_job.status if existing_job else None,
                "booking_status":  "confirmed",
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

        # Social channels have their own message/session/draft controls and a
        # sender-scoped confirmation ceiling. Reusing the customer-app quota
        # here made five app + Instagram bookings consume one shared budget,
        # after which a valid Confirm tap only received the generic failure
        # message. The sender id is page/channel scoped and stable across chat
        # restarts, which is the correct abuse-control identity for this path.
        if source_channel in {"instagram", "whatsapp"} and source_actor_id:
            await enforce_social_confirmation_limit(
                f"{source_channel}:{source_actor_id}"
            )
        else:
            await enforce_booking_action_limits(
                "confirm",
                actor_id=str(draft.customer_id or customer_id or draft.ai_session_id),
                ip_address=ip_address,
            )

        # One customer may have only one active booking for a service. Lock on
        # that stable identity so two different drafts (or two devices) cannot
        # race through confirmation with different slots.
        has_booking_identity = bool(draft.customer_id and draft.offering_id)
        if has_booking_identity and get_settings().APP_ENV in ("staging", "production"):
            duplicate_key = f"{draft.customer_id}:{draft.offering_id}"
            await self.db.execute(
                sa_text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                {"key": f"booking-confirm:{duplicate_key}"},
            )
        if has_booking_identity:
            duplicate = (await self.db.execute(
                select(ServiceBooking).where(
                    ServiceBooking.customer_id == draft.customer_id,
                    ServiceBooking.offering_id == draft.offering_id,
                    ServiceBooking.status.notin_(("completed", "cancelled", "failed")),
                ).order_by(ServiceBooking.created_at.desc()).limit(1)
            )).scalars().first()
            if isinstance(duplicate, ServiceBooking):
                raise ServiceOSException(
                    "DUPLICATE_ACTIVE_BOOKING",
                    f"This service is already booked as {duplicate.booking_number}.",
                    status_code=409,
                    resolution="Track or cancel the existing booking before booking this service again.",
                    context={"booking_id": str(duplicate.id), "booking_number": duplicate.booking_number},
                )

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
        booking_service = HomeServiceChatbotBookingService(db=self.db)
        offering = await booking_service._get_offering(draft.offering_id)
        missing = await booking_service._compute_missing_fields(draft, offering)
        if missing:
            raise ServiceOSException("REQUIRED_FIELD_MISSING", "Complete booking details: " + ", ".join(missing), status_code=422)
        from app.engines.admin_catalog.addon_runtime import validate_frozen_addons
        await validate_frozen_addons(self.db, draft)

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
            "selected_price_amount": draft_summary.get("agreed_price", draft_summary.get("customer_offer")),
            "payment_mode":          "customer_pays_provider_directly",
        }

        # Freeze the catalog answers once. The same snapshot supplies the
        # explicit customer note projection below, so a later catalog relabel
        # can never rewrite what the customer submitted.
        answer_snapshot = await self._build_answer_snapshot(draft)
        customer_note = next((
            str(answer.get("answer_label") or "").strip()
            for answer in reversed((answer_snapshot or {}).get("answers") or [])
            if str(answer.get("question_type") or "").lower() in {"text", "textarea", "long_text"}
            and str(answer.get("answer_label") or "").strip()
        ), None)

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
            customer_photo_urls   = list(draft.photo_urls or []),
            customer_note         = customer_note,
            status                = "pending_assignment",
            # Real bug fixed here: `answer_snapshot` is a real column and
            # QuestionFlowService.build_answer_snapshot() exists to fill it,
            # but nothing ever called it from finalize -- so the column was
            # NULL on every booking ever created, and the "what you told us"
            # section of the customer's booking page was permanently empty.
            # Resolved ONCE here, at finalize, so a later question/option
            # relabel can never change what a historical booking shows.
            answer_snapshot       = answer_snapshot,
            # Urgency carried from the draft, where it was set by the customer
            # genuinely picking from the emergency slot list. The surcharge is
            # read from the summary the customer was SHOWN before confirming
            # and frozen here, so a tenant editing their rate afterwards can
            # never change what this customer agreed to pay.
            is_emergency          = bool(getattr(draft, "is_emergency", False)),
            emergency_surcharge   = self._frozen_emergency_surcharge(draft),
        )
        self.db.add(booking)
        await self.db.flush()
        await self.db.refresh(booking)

        # 4a-bis. Lock in the slot the customer was actually promised.
        #
        # The offer they accepted was resolved when the summary was built,
        # which may have been minutes ago -- another customer can have taken
        # the last place in that slot since. So the promise is ALWAYS
        # re-validated against live provider capacity here, never trusted
        # from the earlier offer. If it is gone we roll forward to the next
        # genuinely available slot rather than silently overbooking the
        # provider or dropping the schedule entirely.
        promised_date = None
        promised_window = None
        summary_slot = (draft.booking_summary or {}).get("promised_slot") or {}
        if draft.selected_tenant_id:
            # Capacity is shared across services and time windows (daily cap),
            # including the fallback slot search. Serialize the entire decision.
            await self.db.execute(
                sa_text("SELECT pg_advisory_xact_lock(hashtextextended(:capacity_key, 0))"),
                {"capacity_key": f"home-service-capacity:{draft.selected_tenant_id}"},
            )
            from app.engines.home_service_booking.provider_slot_service import (
                find_earliest_available_slot, slot_has_capacity,
            )
            import datetime as _dt
            offered_date = summary_slot.get("date")
            offered_window = summary_slot.get("time_window")
            if offered_date and offered_window:
                try:
                    # `booking_summary` is JSONB, so a real round-tripped
                    # summary always carries an ISO string -- but an
                    # in-memory/mocked draft can hand back a real date.
                    # Accept both rather than raising inside confirmation.
                    d = (offered_date if isinstance(offered_date, _dt.date)
                         else _dt.date.fromisoformat(str(offered_date)))
                    # Serialize confirmations for the same provider/service/slot.
                    # Without this transaction-scoped lock, two concurrent
                    # requests could both observe the last place as free before
                    # either inserted its job, exceeding technician capacity.
                    slot_lock_key = (
                        f"home-service-slot:{draft.selected_tenant_id}:"
                        f"{draft.offering_id}:{d.isoformat()}:{offered_window}"
                    )
                    await self.db.execute(
                        sa_text("SELECT pg_advisory_xact_lock(hashtextextended(:slot_key, 0))"),
                        {"slot_key": slot_lock_key},
                    )
                    if await slot_has_capacity(
                        self.db, tenant_id=draft.selected_tenant_id,
                        day=d, time_window=offered_window,
                        master_service_id=draft.offering_id,
                        job_type_id=draft.job_type_id,
                    ):
                        promised_date, promised_window = d, offered_window
                except (ValueError, TypeError):
                    pass
            if promised_date is None:
                try:
                    fresh = await find_earliest_available_slot(
                        self.db, tenant_id=draft.selected_tenant_id,
                        master_service_id=draft.offering_id,
                        job_type_id=draft.job_type_id,
                    )
                    if fresh:
                        promised_date = _dt.date.fromisoformat(str(fresh["date"]))
                        promised_window = fresh["time_window"]
                except Exception as exc:  # noqa: BLE001 -- never fail a paid booking
                    log.warning("booking.promised_slot_revalidate_failed error=%s", exc)

        # 4b. Create ServiceJob
        #
        # AUTO-ACCEPTANCE (product rule): a provider who is ACTIVE and had real
        # capacity in the promised slot has already opted in -- they control
        # whether they receive work by activating/deactivating themselves, so
        # asking them to "accept" each job again is a redundant gate that just
        # leaves work sitting idle while the customer waits.
        #
        # This also fixes a real defect: `pending_assignment` is not a key in
        # execution.constants.JOB_TRANSITIONS at all, so it has NO legal
        # outbound transition -- jobs created there could not be progressed
        # through the normal status machine (166 such rows exist).
        #
        # Falls back to `pending_assignment` when the provider is not active or
        # no slot could be promised: those are genuinely unresolved states that
        # a human must look at, and auto-accepting them would be a lie.
        auto_accept = bool(
            draft.selected_tenant_id
            and promised_date is not None
            and await self._tenant_is_active(draft.selected_tenant_id)
        )
        job_status = JS_ACCEPTED if auto_accept else "pending_assignment"
        # Provider acceptance and technician assignment are separate facts.
        # The business can accept immediately, but the job remains unassigned
        # until a real staff member owns it.
        assignment_status = "unassigned"

        # Booking and job are two projections of the same customer request.
        # Auto-accepting only the job left My Bookings at "Request confirmed"
        # while Booking Details claimed a provider was assigned. Keep both
        # records atomic so every app sees the same backend state.
        if auto_accept:
            booking.status = JS_ACCEPTED
            booking.assignment_status = assignment_status

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
            # The slot the customer was actually shown and accepted on the
            # review screen wins. `preferred_*` remains the fallback for any
            # flow that sets it explicitly. Without this the job was created
            # with NO schedule at all for the whole assistant flow (which
            # never sets preferred_date), so the provider had no idea when
            # the customer expected them and capacity was never consumed.
            scheduled_date        = promised_date or draft.preferred_date,
            scheduled_time_window = promised_window or draft.preferred_time_window,
            city                  = draft.city,
            zipcode               = draft.zipcode,
            address_snapshot      = draft.address_snapshot,
            status                = job_status,
            assignment_status     = assignment_status,
            is_emergency          = booking.is_emergency,
        )
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)

        # An auto-accepted job must still leave the same audit trail a manual
        # acceptance would, so the provider's own timeline/history shows how it
        # reached `accepted` and nothing downstream has to special-case a job
        # that "was never accepted by anyone".
        if auto_accept:
            from app.engines.execution.constants import EV_JOB_ACCEPTED
            from app.engines.execution.models import ServiceJobExecutionEvent
            self.db.add(ServiceJobExecutionEvent(
                booking_id=booking.id, job_id=job.id, tenant_id=job.tenant_id,
                staff_member_id=None, actor_user_id=None, actor_role="system",
                event_type=EV_JOB_ACCEPTED, old_status=None, new_status=JS_ACCEPTED,
                notes="Auto-accepted: provider is active and had capacity in the promised slot.",
                event_metadata={
                    "auto_accepted": True,
                    "reason": "provider_active_with_capacity",
                    "promised_date": promised_date.isoformat() if promised_date else None,
                    "promised_window": promised_window,
                    "is_emergency": bool(booking.is_emergency),
                },
                request_id=request_id,
            ))

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

        # 9. Customer platform fee (vertical_monetization).
        #
        # Real production gap fixed here: the entire vertical_monetization
        # engine -- policies, charge records, calculation -- existed and could
        # be configured and "published" by Super Admin, but NOTHING in the live
        # booking pipeline ever called it. No customer platform fee was ever
        # created for any booking, so a published PLATFORM_FEE policy earned
        # the platform nothing.
        #
        # Deliberately non-fatal: a monetization misconfiguration must never
        # block a booking the customer has already paid for and confirmed.
        # `create_charge_for_booking` is itself idempotent (keyed
        # "booking:{id}") and returns None when the vertical has no policy.
        # SECOND production gap, found live: the call above was missing three
        # REQUIRED keyword-only arguments (customer_id, service_amount_major,
        # source_event), so it raised TypeError on EVERY booking. The broad
        # `except` -- there so a monetization misconfiguration cannot block a
        # confirmed booking -- swallowed it into a warning, which meant the fix
        # described above was never actually in effect: still no charge row for
        # any booking, ever. Confirmed by the real log line
        # "monetization.booking_charge_failed ... missing 3 required
        # keyword-only arguments".
        try:
            from app.engines.vertical_monetization.charge_service import create_charge_for_booking
            await create_charge_for_booking(
                self.db, vertical_key="home_services",
                booking_id=booking.id, tenant_id=draft.selected_tenant_id,
                customer_id=draft.customer_id,
                service_amount_major=_booking_service_amount(booking_price_snapshot),
                source_event="booking_confirmed",
            )
        except Exception as exc:  # noqa: BLE001 -- never fail a confirmed booking
            log.warning("monetization.booking_charge_failed booking_id=%s error=%s",
                        booking.id, exc)

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
            "selected_price_amount":       booking_summary.get("agreed_price", booking_summary.get("customer_offer")),
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

    async def _tenant_is_active(self, tenant_id) -> bool:
        """Whether the provider is currently accepting work.

        Deliberately fails CLOSED: any unexpected state (missing tenant, a
        status this code does not recognise) means no auto-acceptance, so the
        job lands in `pending_assignment` for a human rather than being
        auto-committed to a provider who may be suspended.
        """
        row = (await self.db.execute(sa_text(
            "SELECT status, suspended_at, terminated_at FROM tenants WHERE id=:tid"
        ), {"tid": str(tenant_id)})).fetchone()
        if not row:
            return False
        m = row._mapping
        return (
            str(m.get("status")) == "active"
            and m.get("suspended_at") is None
            and m.get("terminated_at") is None
        )

    @staticmethod
    def _frozen_emergency_surcharge(draft):
        """The emergency surcharge exactly as the customer was shown it.

        Taken from `draft.booking_summary`, which is what the review/chat
        screen rendered before they pressed Confirm -- deliberately NOT a
        fresh read of `tenant_services.tenant_emergency_surcharge`. Re-reading
        it here would let a tenant who edited their rate mid-session bill a
        customer something they never agreed to.
        """
        if not getattr(draft, "is_emergency", False):
            return None
        raw = (draft.booking_summary or {}).get("emergency_surcharge")
        if raw in (None, ""):
            return None
        try:
            value = Decimal(str(raw))
        except (InvalidOperation, ValueError, TypeError):
            return None
        return value if value > 0 else None

    async def _build_answer_snapshot(self, draft) -> dict | None:
        """The immutable record of what the customer actually answered.

        Imported lazily to keep the final_records engine from taking a
        module-level dependency on home_service_booking (the reverse
        direction already exists and would cycle).

        A failure here must never block a confirmed booking: the answers are
        a receipt detail, not part of the commitment being made. It is logged
        loudly rather than swallowed silently, because a NULL snapshot is
        exactly the bug this method was added to fix.
        """
        try:
            from app.engines.home_service_booking.question_flow_service import QuestionFlowService
            return await QuestionFlowService(db=self.db).build_answer_snapshot(draft)
        except Exception as exc:  # pragma: no cover - defensive
            log.warning("answer snapshot build failed for draft %s: %s", draft.id, exc)
            return None


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
