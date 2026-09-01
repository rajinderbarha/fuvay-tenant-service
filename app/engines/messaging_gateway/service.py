"""Messaging Gateway service — inbound message -> scripted booking step -> reply.

Deliberately thin, and deliberately deterministic. This module resolves who is
speaking, which draft they are on, and whether the message was a command; the
booking itself is `flow.py`, which asks the admin-defined catalog questions one
at a time and applies each answer through the booking services.

No language model is involved in a customer conversation. `ai_conversation` is
still used for two non-conversational things: its session row is what a booking
draft hangs off, and its `BackendToolExecutor` is the shared implementation of
the backend calls the flow makes.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import structlog
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.messaging_gateway import flow, meta_client, pickers
from app.engines.messaging_gateway.constants import (
    CMD_HELP, CMD_HUMAN, CMD_LINK, CMD_RESET, CMD_START, CMD_STOP, CMD_TRACK,
    CMD_VERIFY, COMMAND_PREFIX,
    CUSTOMER_SERVICE_WINDOW_HOURS,
    HANDOFF_TEXT, HELP_TEXT, KNOWN_COMMANDS, LIVE_BOOKING_STATUSES,
    MAX_SESSIONS_PER_SENDER_PER_HOUR,
    STATUS_DUPLICATE, STATUS_FAILED, STATUS_IGNORED, STATUS_PROCESSED,
    STOP_TEXT, WHATSAPP_BOOKING_FLOW_CTA, WHATSAPP_BOOKING_FLOW_SCREEN,
    WHATSAPP_FLOW_TOKEN_TTL_HOURS,
)
from app.engines.messaging_gateway.meta_client import InboundMessage
from app.engines.messaging_gateway.models import MessagingInboundMessage, MessagingThread

logger = structlog.get_logger(__name__)

GREETING = (
    "Hi{name}! I'm Fuvay. I'll book your home service in a few taps — "
    "just pick from the options below."
)

BUSY_TEXT = (
    "You've started several conversations in a short time. "
    "Please continue in this chat, or try again shortly."
)

UNSUPPORTED_TEXT = (
    "I can only read text messages here. Choose from the options below to "
    "book a service."
)

# A staged Instagram phone is encrypted exactly like an OTP-bound phone, but
# carries this non-secret state marker until the customer explicitly confirms
# that sending a paid OTP to it is intentional.
_PHONE_CONFIRMATION_PREFIX = "confirm:"

#: Every OPTIONS message carries a "Start over" row (see `pickers._paginate`).
#: A prompt that asks for something typed — an address, a phone number, a code
#: — deliberately does not: a button under a question the customer is about to
#: answer in words is clutter beside the thing they were asked for.


def parse_command(text: str) -> str | None:
    """Return the bare command name for a leading slash command, else None.

    Only the FIRST token is considered, so "/fuvay my AC is broken" is a start
    command carrying context rather than an unknown command.
    """
    stripped = (text or "").strip()
    if not stripped.startswith(COMMAND_PREFIX):
        return None
    token = stripped[1:].split(maxsplit=1)[0].lower() if len(stripped) > 1 else ""
    return token if token in KNOWN_COMMANDS else None


def command_remainder(text: str) -> str:
    """Whatever followed the command, e.g. "/fuvay AC not cooling" -> "AC not cooling"."""
    stripped = (text or "").strip()
    parts = stripped.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


async def notify_customer(db: AsyncSession, customer_id, text: str) -> bool:
    """Message a customer on the chat channel they last used, if we still may.

    WhatsApp allows a business-initiated message only inside 24 hours of the
    customer's own last message; outside it, a pre-approved template is the
    only route, and Instagram has no template mechanism at all. So this sends
    when the window is open and reports False when it is not — the caller must
    not assume the customer was told.

    Best-effort by design: a chat notification never decides whether the
    business operation that raised it succeeds.
    """
    if not customer_id:
        return False
    from app.engines.messaging_gateway.config_service import (
        messaging_channel_config_service,
    )

    since = datetime.now(timezone.utc) - timedelta(hours=CUSTOMER_SERVICE_WINDOW_HOURS)
    threads = (await db.execute(
        select(MessagingThread)
        .where(MessagingThread.customer_id == customer_id,
               MessagingThread.opted_out.is_(False),
               MessagingThread.last_inbound_at.isnot(None),
               MessagingThread.last_inbound_at >= since)
        .order_by(MessagingThread.last_inbound_at.desc())
    )).scalars().all()

    for thread in threads:
        config = await messaging_channel_config_service.get(
            db, thread.channel, require_enabled=True,
        )
        if not config:
            continue
        result = await meta_client.send_text(
            thread.channel_user_id, text, channel=thread.channel, config=config,
        )
        if result.get("sent"):
            thread.last_outbound_at = datetime.now(timezone.utc)
            return True
    logger.info("messaging_gateway.notify.window_closed",
                customer_id=str(customer_id), threads=len(threads))
    return False


class MessagingGatewayService:
    def __init__(
        self,
        db: AsyncSession,
        request_id: str = "—",
        channel_config: dict | None = None,
    ):
        self.db = db
        self.request_id = request_id
        self.channel_config = dict(channel_config or {})

    # ── Threads & identity ───────────────────────────────────────────────────

    async def get_or_create_thread(self, msg: InboundMessage) -> MessagingThread:
        thread = (await self.db.execute(
            select(MessagingThread).where(
                MessagingThread.channel == msg.channel,
                MessagingThread.channel_user_id == msg.from_id,
                MessagingThread.channel_business_id == msg.business_id,
            )
        )).scalars().first()
        if thread:
            if msg.display_name and thread.display_name != msg.display_name:
                thread.display_name = msg.display_name
            return thread

        thread = MessagingThread(
            channel=msg.channel,
            channel_user_id=msg.from_id,
            channel_business_id=msg.business_id,
            display_name=msg.display_name,
        )
        try:
            # Keep the inbound idempotency claim outside this savepoint. If a
            # concurrent first message creates the same thread, only this
            # insert rolls back; the already-claimed message must survive.
            async with self.db.begin_nested():
                self.db.add(thread)
                await self.db.flush()
        except IntegrityError:
            # Two messages from the same new sender can arrive concurrently.
            thread = (await self.db.execute(
                select(MessagingThread).where(
                    MessagingThread.channel == msg.channel,
                    MessagingThread.channel_user_id == msg.from_id,
                    MessagingThread.channel_business_id == msg.business_id,
                )
            )).scalars().first()
        return thread

    async def resolve_customer(self, thread: MessagingThread) -> uuid.UUID | None:
        """Link the thread to a customer account by phone number.

        WhatsApp gives us a verified E.164 number — Meta has already proven the
        person controls it. That is the same identity `/v1/auth/otp/verify`
        establishes, so an existing phone-OTP customer is matched here without
        a second verification step.

        A customer row is NOT created for a stranger who merely says hello:
        the account is created at booking confirmation, when there is real
        intent and a name/address to attach. Creating an account per inbound
        message would fill `users` with abandoned rows.
        """
        if thread.customer_id:
            return thread.customer_id
        if thread.channel != "whatsapp":
            return None  # Instagram ids are page-scoped, never a phone number

        from app.engines.auth.models import User

        digits = "".join(ch for ch in thread.channel_user_id if ch.isdigit())
        if not digits:
            return None
        # Stored numbers vary in prefix formatting (+91…, 91…, 0…), so match on
        # the trailing national digits rather than an exact string compare.
        tail = digits[-10:]
        # Matched on the phone ALONE, not on `role == "customer"`, and ordered
        # the same way the confirm path orders it. `users.phone` is globally
        # unique, so a number registered as a technician or a tenant owner has
        # no second row to find — and the booking that number places is
        # attached to exactly that account. Filtering by role here left
        # `thread.customer_id` NULL for those people, so "Track my booking"
        # answered "there is no booking on this number" about a booking they
        # had just made. Confirmed live.
        user = (await self.db.execute(
            select(User).where(
                User.is_active.is_(True),
                User.phone.isnot(None),
                func.right(func.regexp_replace(User.phone, r"\D", "", "g"), 10) == tail,
            ).order_by(
                (User.role == "customer").desc(),
                (User.phone == f"+{digits}").desc(),
            ).limit(1)
        )).scalars().first()
        if user:
            thread.customer_id = user.id
            return user.id
        return None

    # ── Sessions ─────────────────────────────────────────────────────────────

    async def _rate_limited(self, thread: MessagingThread) -> bool:
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        count = (await self.db.execute(
            select(func.count()).select_from(MessagingInboundMessage).where(
                MessagingInboundMessage.thread_id == thread.id,
                MessagingInboundMessage.created_at >= since,
                MessagingInboundMessage.status == STATUS_PROCESSED,
            )
        )).scalar() or 0
        return count > MAX_SESSIONS_PER_SENDER_PER_HOUR * 20

    async def ensure_session(self, thread: MessagingThread) -> uuid.UUID:
        """Return the thread's live agent session, creating one if needed."""
        from app.engines.ai_conversation.models import AIConversationSession
        from app.engines.ai_conversation.service import AIConversationService

        if thread.ai_session_id:
            existing = (await self.db.execute(
                select(AIConversationSession).where(
                    AIConversationSession.id == thread.ai_session_id
                )
            )).scalars().first()
            if existing and existing.is_active:
                return existing.id
            # Closed or turn-capped: fall through and open a fresh one so the
            # customer is never stuck talking to a dead session.

        svc = AIConversationService(self.db)
        session = await svc.create_session(
            customer_id=thread.customer_id,
            context_data={
                "channel": thread.channel,
                "channel_user_id": thread.channel_user_id,
                "display_name": thread.display_name,
            },
        )
        thread.ai_session_id = uuid.UUID(str(session["id"]))
        thread.session_count = (thread.session_count or 0) + 1
        return thread.ai_session_id

    # ── Main entry point ─────────────────────────────────────────────────────

    async def handle_inbound(self, msg: InboundMessage) -> dict:
        """Process one normalised inbound message. Always commits.

        Returns a small dict for logging/tests. Never raises for ordinary
        problems: the webhook must answer 200 or Meta will redeliver forever.
        """
        # ── Idempotency: claim the provider message id first ─────────────────
        record = MessagingInboundMessage(
            channel=msg.channel,
            provider_message_id=msg.provider_message_id,
            from_id=msg.from_id,
            message_type=msg.message_type,
            body=msg.text or None,
            raw_payload=msg.raw,
        )
        self.db.add(record)
        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            logger.info("messaging_gateway.inbound.duplicate",
                        provider_message_id=msg.provider_message_id)
            return {"status": STATUS_DUPLICATE, "reply_sent": False}

        thread = await self.get_or_create_thread(msg)
        record.thread_id = thread.id
        thread.last_inbound_at = datetime.now(timezone.utc)
        await self.resolve_customer(thread)

        flow_error = None
        if msg.flow_response is not None:
            msg.reply_id = await self._validated_flow_reply(thread, msg.flow_response)
            if not msg.reply_id:
                flow_error = (
                    "That booking form has expired or no longer belongs to this "
                    "booking. Reply TIMES to see the current appointments here."
                )

        # A tapped option is customer data, and an option label could
        # legitimately read like a command ("/help" as a brand name), so a tap
        # is never parsed as one.
        tapped = pickers.is_picker_reply(msg.reply_id)
        command = None if tapped else parse_command(msg.text)
        reply: str | None = None
        picker: dict | None = None

        # ── Commands ───────────────────────────────────────────────
        if flow_error:
            reply = flow_error
        elif command == CMD_STOP:
            thread.opted_out = True
            reply = STOP_TEXT
        elif command == CMD_HELP:
            reply = HELP_TEXT
        elif command == CMD_HUMAN:
            thread.human_handoff = True
            reply = HANDOFF_TEXT
        elif command == CMD_TRACK:
            action = await flow._track_step(thread, self, "", msg.channel)
            reply, picker = action.text, action.picker
        elif command == CMD_LINK:
            reply = await self._start_identity_link(thread, command_remainder(msg.text))
        elif command == CMD_VERIFY:
            reply = await self._finish_identity_link(thread, command_remainder(msg.text))
        elif command in (CMD_START, CMD_RESET):
            # /fuvay is the explicit start-over: drop every booking-scoped
            # value, including the previously remembered service area. The
            # booking flow is zipcode-first, so retaining these two fields
            # silently skipped its first question for returning Instagram
            # customers.
            thread.ai_session_id = None
            thread.zipcode = None
            thread.city = None
            thread.pending_customer_id = None
            thread.pending_phone_ciphertext = None
            thread.last_options = None
            thread.opted_out = False
            thread.human_handoff = False
            name = f" {thread.display_name.split()[0]}" if thread.display_name else ""
            reply = GREETING.format(name=name)
            # Open the script at its first question rather than making them
            # send a second message to get going. A typed first question (the
            # zipcode prompt) must be included too; the older code discarded
            # this returned text because the first step used to be a picker.
            opening_text, picker = await self._advance(thread, msg, ignore_input=True)
            if opening_text:
                reply = f"{reply}\n\n{opening_text}"

        # ── A step of the booking ────────────────────────────────────
        elif thread.opted_out:
            # Never advance a draft invisibly after /stop. An explicit
            # /fuvay opts the customer back in and starts a clean flow.
            reply = None
        elif thread.human_handoff:
            reply = None  # a person owns this thread; stay quiet
        elif (
            not tapped
            and not (msg.text or "").strip()
            and not msg.location
            and not msg.location_unavailable
        ):
            reply = UNSUPPORTED_TEXT
        elif await self._rate_limited(thread):
            reply = BUSY_TEXT
        else:
            reply, picker = await self._advance(thread, msg)


        sent = False
        if (reply and not thread.opted_out) or (reply and command == CMD_STOP):
            # /stop still gets its one acknowledgement.
            result = await meta_client.send_text(
                msg.from_id, reply, channel=msg.channel, config=self.channel_config,
            )
            sent = bool(result.get("sent"))
            if sent:
                thread.last_outbound_at = datetime.now(timezone.utc)

        if picker and not thread.opted_out:
            cta = picker.get("cta_url") if msg.channel == "whatsapp" else None
            if cta:
                cta_result = await meta_client.send_cta_url(
                    msg.from_id,
                    str(cta.get("body") or "Open your booking location."),
                    str(cta.get("display_text") or "Open location"),
                    str(cta.get("url") or ""),
                    config=self.channel_config,
                )
                if cta_result.get("sent"):
                    sent = True
                    thread.last_outbound_at = datetime.now(timezone.utc)
            # A second message rather than one combined body: an interactive
            # body is capped far below a text body, so folding the agent's
            # answer into it would truncate the answer to fit the buttons.
            picked = await meta_client.send_options(
                msg.from_id, picker["body"], picker["rows"],
                channel=msg.channel, config=self.channel_config,
                list_button=picker["list_button"],
                section_title=picker["section_title"],
                presentation=picker.get("presentation"),
                flow=picker.get("flow"),
            )
            if picked.get("sent"):
                sent = True
                thread.last_outbound_at = datetime.now(timezone.utc)
                # A typed number is accepted only when that same numbered list
                # was visibly sent. Carousels, buttons and short quick-reply
                # rows must not turn an unrelated "1" into a hidden choice.
                thread.last_options = (
                    [r["id"] for r in picker["rows"]]
                    if picked.get("numbered_options") else None
                )
        elif reply is not None:
            # A turn that offers no options closes the numbered list, so a
            # stray number is not applied to whatever was on offer before it.
            thread.last_options = None

        record.status = (STATUS_PROCESSED if (reply is not None or picker)
                         else STATUS_IGNORED)
        await self.db.commit()
        return {"status": record.status, "reply_sent": sent,
                "thread_id": str(thread.id), "command": command}

    async def booking_status(
        self, thread: MessagingThread, booking_number: str = "",
    ) -> str:
        """One booking's real status, for the Track option in the flow."""
        return await self._latest_booking_status(thread, booking_number)

    async def cancel_options(self, thread: MessagingThread, booking_number: str) -> dict:
        """What the SERVER says about cancelling this booking.

        Eligibility is never decided in the chat: whether a booking can still
        be cancelled depends on the job's status and the published job-type
        workflow, and `get_customer_eligibility` is the authority both the
        mobile app and this read from.
        """
        from app.engines.final_records.models import ServiceBooking
        from app.engines.home_service_assignment.service import (
            HomeServiceJobAssignmentService,
        )

        booking = (await self.db.execute(
            select(ServiceBooking).where(
                ServiceBooking.customer_id == thread.customer_id,
                ServiceBooking.booking_number == booking_number,
            ).limit(1)
        )).scalars().first()
        if not booking:
            return {"can_cancel": False, "reasons": []}
        try:
            eligibility = await HomeServiceJobAssignmentService(self.db).get_customer_eligibility(
                booking.id, thread.customer_id,
            )
        except Exception as exc:  # noqa: BLE001 — a read must not break the chat
            logger.warning("messaging_gateway.cancel_eligibility_failed",
                           booking=booking_number, error=str(exc))
            return {"can_cancel": False, "reasons": []}
        return {
            "booking_id": booking.id,
            "can_cancel": bool(eligibility.get("can_cancel")),
            "block_reason": eligibility.get("cancel_block_reason"),
            "reasons": list(eligibility.get("allowed_cancellation_reasons") or []),
            "version": eligibility.get("version"),
        }

    async def cancel_booking(
        self, thread: MessagingThread, booking_number: str, reason: str,
    ) -> str:
        """Cancel through the same service the app cancels through."""
        from app.engines.home_service_assignment.service import (
            HomeServiceJobAssignmentService,
        )

        options = await self.cancel_options(thread, booking_number)
        from app.engines.messaging_gateway.flow import CANCEL_NOT_ALLOWED, CANCELLED

        if not options.get("can_cancel"):
            return CANCEL_NOT_ALLOWED
        try:
            await HomeServiceJobAssignmentService(self.db).customer_cancel_booking(
                booking_id=options["booking_id"], customer_id=thread.customer_id,
                reason=reason, expected_version=options.get("version"),
                request_id=f"chat:{thread.id}:{booking_number}",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("messaging_gateway.cancel_failed",
                           booking=booking_number, error=str(exc))
            from app.engines.messaging_gateway.flow import CANCEL_FAILED

            return CANCEL_FAILED
        return CANCELLED.format(number=booking_number)

    async def pending_parts(self, thread: MessagingThread) -> list[dict]:
        """Parts a technician needs, waiting on THIS customer's decision.

        Read from the same `PartsRequest` rows the app's parts screen reads,
        at the one status that means the customer owes an answer — a request
        the business has approved and flagged as needing them. Anything else
        is the provider's business, not a question for the customer.
        """
        if not thread.customer_id:
            return []
        from app.engines.execution.constants import (
            PARTS_STATUS_CUSTOMER_APPROVAL_PENDING,
        )
        from app.engines.execution.models import PartsRequest
        from app.engines.final_records.models import ServiceBooking, ServiceJob

        rows = (await self.db.execute(
            select(PartsRequest, ServiceBooking.booking_number)
            .join(ServiceJob, ServiceJob.id == PartsRequest.job_id)
            .join(ServiceBooking, ServiceBooking.id == ServiceJob.booking_id, isouter=True)
            .where(ServiceJob.customer_id == thread.customer_id,
                   PartsRequest.status == PARTS_STATUS_CUSTOMER_APPROVAL_PENDING,
                   PartsRequest.customer_approval_required.is_(True))
            .order_by(PartsRequest.created_at)
        )).all()
        return [
            {
                "id": str(part.id),
                "job_id": str(part.job_id),
                "booking_number": booking_number,
                "part_name": part.part_name,
                "quantity": part.quantity,
                "line_total": str(Decimal(str(part.estimated_cost)) * part.quantity),
                "reason": part.reason,
            }
            for part, booking_number in rows
        ]

    async def pending_quotes(self, thread: MessagingThread) -> list[dict]:
        """Current estimates waiting on this customer's decision.

        The quote service supplies the customer-safe view. It removes provider
        notes and recalculates the amount from visible line items, so chat can
        never ask someone to approve a hidden or unreconciled total.
        """
        if not thread.customer_id:
            return []
        from app.engines.final_records.models import ServiceBooking
        from app.engines.quote_checklist.constants import QS_SENT_TO_CUSTOMER
        from app.engines.quote_checklist.models import ServiceJobQuote
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService

        rows = (await self.db.execute(
            select(ServiceJobQuote, ServiceBooking.booking_number)
            .join(ServiceBooking, ServiceBooking.id == ServiceJobQuote.booking_id,
                  isouter=True)
            .where(
                ServiceJobQuote.customer_id == thread.customer_id,
                ServiceJobQuote.is_current.is_(True),
                ServiceJobQuote.status == QS_SENT_TO_CUSTOMER,
                ServiceBooking.status.in_(LIVE_BOOKING_STATUSES),
            )
            .order_by(ServiceJobQuote.created_at)
            .limit(5)
        )).all()
        quote_service = ServiceJobQuoteService()
        pending = []
        for quote, booking_number in rows:
            safe = await quote_service.get_quote(
                self.db, str(quote.id), customer_id=str(thread.customer_id),
            )
            pending.append({
                "id": str(quote.id),
                "quote_number": quote.quote_number,
                "booking_number": booking_number,
                "currency": quote.currency,
                "amount": safe.get("customer_payable_amount"),
                "notes": safe.get("customer_visible_notes"),
                "items": list(safe.get("items") or []),
            })
        return pending

    async def decide_quote(
        self, thread: MessagingThread, quote_id: str, decision: str,
    ) -> str:
        """Apply a quote decision through the canonical customer service."""
        from app.engines.messaging_gateway.flow import (
            QUOTE_APPROVED, QUOTE_DECIDED_ALREADY, QUOTE_DECLINED,
            QUOTE_REVISION_REQUESTED,
        )
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService

        if not thread.customer_id:
            return QUOTE_DECIDED_ALREADY
        service = ServiceJobQuoteService()
        customer_id = str(thread.customer_id)
        request_id = f"chat:{thread.id}:{quote_id}:{decision}"
        try:
            if decision == "approve":
                await service.customer_approve(
                    self.db, quote_id, customer_id,
                    idempotency_key=request_id, user_id=customer_id,
                    request_id=request_id,
                )
                return QUOTE_APPROVED
            if decision == "decline":
                await service.customer_reject(
                    self.db, quote_id, customer_id,
                    reason="Customer declined the estimate in chat.",
                    user_id=customer_id, request_id=request_id,
                )
                return QUOTE_DECLINED
            if decision == "revise":
                await service.customer_request_revision(
                    self.db, quote_id, customer_id,
                    reason=("Customer requested changes in chat. Contact them in "
                            "this conversation before sending a revised estimate."),
                    user_id=customer_id, request_id=request_id,
                )
                return QUOTE_REVISION_REQUESTED
        except Exception as exc:  # noqa: BLE001 - stale/repeated taps are normal
            logger.info("messaging_gateway.quote_decision_rejected",
                        quote_id=quote_id, decision=decision, error=str(exc))
        return QUOTE_DECIDED_ALREADY

    async def pending_closure_actions(self, thread: MessagingThread) -> list[dict]:
        """Customer acknowledgements required after the technician finishes.

        These are the same handover and direct-payment records rendered by the
        customer app and required by the staff app before final completion.
        """
        if not thread.customer_id:
            return []
        from app.engines.admin_catalog.models import MasterService
        from app.engines.execution.models import CompletionProof
        from app.engines.final_records.models import ServiceBooking, ServiceJob

        rows = (await self.db.execute(
            select(CompletionProof, ServiceJob, ServiceBooking.booking_number,
                   MasterService.service_name)
            .join(ServiceJob, ServiceJob.id == CompletionProof.job_id)
            .join(ServiceBooking, ServiceBooking.id == ServiceJob.booking_id,
                  isouter=True)
            .join(MasterService, MasterService.id == ServiceJob.offering_id,
                  isouter=True)
            .where(
                ServiceJob.customer_id == thread.customer_id,
                CompletionProof.status == "submitted",
                CompletionProof.handover_status.in_(("requested", "customer_unavailable")),
            )
            .order_by(CompletionProof.handover_requested_at)
            .limit(5)
        )).all()
        actions = [{
            "kind": "handover", "job_id": str(job.id),
            "booking_number": booking_number, "service": service_name,
        } for _proof, job, booking_number, service_name in rows]

        from app.engines.invoice_payment.direct_payments_service import DirectPaymentsService
        payments = await DirectPaymentsService(
            self.db, uuid.UUID(int=0), f"chat:{thread.id}",
        ).customer_pending_list(str(thread.customer_id))
        for payment in payments.get("items") or []:
            if payment.get("customer_confirmed") or payment.get("customer_action"):
                continue
            actions.append({
                "kind": "payment", "payment_id": payment["payment_id"],
                "job_id": payment.get("job_id"), "job_ref": payment.get("job_ref"),
                "provider": payment.get("provider_business"),
                "amount": payment.get("service_amount"),
                "currency": payment.get("currency"), "method": payment.get("method"),
            })
        return actions

    async def acknowledge_handover(
        self, thread: MessagingThread, job_id: str,
    ) -> str:
        from app.engines.execution.mobile_completion_proof_service import (
            MobileCompletionProofService,
        )
        from app.engines.messaging_gateway.flow import (
            HANDOVER_ACKNOWLEDGED, HANDOVER_DECIDED_ALREADY,
        )
        try:
            await MobileCompletionProofService().acknowledge_handover(
                self.db, thread.customer_id, uuid.UUID(str(job_id)),
            )
            return HANDOVER_ACKNOWLEDGED
        except Exception as exc:  # stale/repeated controls are expected
            logger.info("messaging_gateway.handover_rejected",
                        job_id=str(job_id), error=str(exc))
            return HANDOVER_DECIDED_ALREADY

    async def decide_payment(
        self, thread: MessagingThread, payment_id: str, decision: str,
    ) -> str:
        from app.engines.invoice_payment.direct_payments_constants import CA_NOT_PAID
        from app.engines.invoice_payment.direct_payments_service import DirectPaymentsService
        from app.engines.messaging_gateway.flow import (
            PAYMENT_CONFIRMED, PAYMENT_DECIDED_ALREADY, PAYMENT_MISMATCH_REPORTED,
        )
        service = DirectPaymentsService(
            self.db, uuid.UUID(int=0), f"chat:{thread.id}:{payment_id}:{decision}",
        )
        try:
            if decision == "confirm":
                await service.customer_confirm(
                    payment_id=uuid.UUID(str(payment_id)),
                    customer_id=str(thread.customer_id),
                )
                return PAYMENT_CONFIRMED
            if decision == "not_paid":
                await service.customer_report_mismatch(
                    payment_id=uuid.UUID(str(payment_id)),
                    customer_id=str(thread.customer_id), action=CA_NOT_PAID,
                    note="Customer reported in chat that this payment was not made.",
                )
                return PAYMENT_MISMATCH_REPORTED
        except Exception as exc:  # stale/repeated controls are expected
            logger.info("messaging_gateway.payment_decision_rejected",
                        payment_id=str(payment_id), decision=decision, error=str(exc))
        return PAYMENT_DECIDED_ALREADY

    async def parts_totals(self, thread: MessagingThread, job_id: str) -> dict:
        """The job's own before/after totals, as the app's parts screen shows.

        Quoted from `customer_list_parts_requests` rather than added up here:
        what a part does to the bill is the execution engine's arithmetic, and
        a second copy of it in the chat would eventually disagree.
        """
        from app.engines.execution.home_service_service import (
            HomeServiceJobExecutionService,
        )
        try:
            return await HomeServiceJobExecutionService().customer_list_parts_requests(
                self.db, uuid.UUID(str(job_id)), thread.customer_id,
            )
        except Exception as exc:  # noqa: BLE001 — a total is not worth a failure
            logger.warning("messaging_gateway.parts_totals_failed",
                           job_id=str(job_id), error=str(exc))
            return {}

    async def decide_parts(
        self, thread: MessagingThread, parts_request_id: str, decision: str,
    ) -> str:
        """Approve or decline through the customer's own decision endpoint."""
        from app.engines.execution.home_service_service import (
            HomeServiceJobExecutionService,
        )
        from app.engines.messaging_gateway.flow import (
            PARTS_APPROVED, PARTS_DECIDED_ALREADY, PARTS_DECLINED,
        )
        try:
            await HomeServiceJobExecutionService().customer_decide_parts_request(
                self.db, uuid.UUID(str(parts_request_id)), thread.customer_id,
                decision=decision,
                reason="Declined in chat" if decision == "decline" else None,
                request_id=f"chat:{thread.id}",
            )
        except Exception as exc:  # noqa: BLE001
            # A repeat tap on an older message lands here, and so does a
            # request the provider has since withdrawn: both mean the same
            # thing to a customer — the decision is no longer theirs to make.
            logger.info("messaging_gateway.parts_decision_rejected",
                        parts_request_id=str(parts_request_id), error=str(exc))
            return PARTS_DECIDED_ALREADY
        return PARTS_APPROVED if decision == "approve" else PARTS_DECLINED

    async def live_bookings(self, thread: MessagingThread) -> list[dict]:
        """Bookings this customer could still be waiting on, newest first.

        Offering "track" for a job that finished last month is noise, and
        naming the service on each row is what makes a choice between two open
        bookings answerable.
        """
        if not thread.customer_id:
            return []
        from app.engines.final_records.models import ServiceBooking

        from app.engines.admin_catalog.models import MasterService

        # The offering's name, not the booking number, is what a customer
        # recognises when choosing between two open bookings.
        rows = (await self.db.execute(
            select(ServiceBooking, MasterService.service_name)
            .join(MasterService, MasterService.id == ServiceBooking.offering_id,
                  isouter=True)
            .where(ServiceBooking.customer_id == thread.customer_id,
                   ServiceBooking.status.in_(LIVE_BOOKING_STATUSES))
            .order_by(ServiceBooking.created_at.desc())
            .limit(10)
        )).all()
        return [
            {
                "number": booking.booking_number,
                "service": service_name or booking.booking_number,
                "status": (booking.status or "").replace("_", " ").title(),
                # Two bookings for the same service are only distinguishable
                # by when the technician is due.
                "when": (booking.preferred_date.strftime("%a %d %b")
                         if booking.preferred_date else None),
            }
            for booking, service_name in rows
        ]

    async def live_booking(self, thread: MessagingThread) -> bool:
        """Is there a booking this customer could still be waiting on?"""
        return bool(await self.live_bookings(thread))

    async def booking_location_cta(
        self, thread: MessagingThread, booking_number: str,
    ) -> dict | None:
        """Return the customer's own saved service address as a map action."""
        if not thread.customer_id or not booking_number:
            return None
        from app.engines.final_records.models import ServiceBooking

        booking = (await self.db.execute(
            select(ServiceBooking).where(
                ServiceBooking.customer_id == thread.customer_id,
                ServiceBooking.booking_number == booking_number,
            ).limit(1)
        )).scalars().first()
        if not booking:
            return None
        return flow._location_cta({
            "address_snapshot": booking.address_snapshot or {},
            "city": getattr(booking, "city", None)
                    or (booking.address_snapshot or {}).get("city"),
            "zipcode": getattr(booking, "zipcode", None)
                       or (booking.address_snapshot or {}).get("zipcode"),
        })

    async def _latest_booking_status(
        self, thread: MessagingThread, booking_number: str = "",
    ) -> str:
        """Return a real booking's status without exposing another user."""
        if not thread.customer_id:
            link_help = (
                " Send /link followed by your mobile number to link it."
                if thread.channel == "instagram" else ""
            )
            return (
                "To protect your booking details, this chat is not linked to a "
                "Fuvay customer account yet. Use the same mobile number as your "
                f"Fuvay account, or open the Fuvay app to track the booking.{link_help}"
            )
        from app.engines.final_records.models import ServiceBooking, ServiceJob

        query = select(ServiceBooking).where(
            # Scoped to the customer as well as the number: a booking number
            # is guessable, and this answers into a chat.
            ServiceBooking.customer_id == thread.customer_id,
        )
        if booking_number:
            query = query.where(ServiceBooking.booking_number == booking_number)
        booking = (await self.db.execute(
            query.order_by(ServiceBooking.created_at.desc()).limit(1)
        )).scalars().first()
        if not booking:
            return "I couldn't find a booking on this account yet. Tell me what service you need to start one."
        job = (await self.db.execute(
            select(ServiceJob).where(ServiceJob.booking_id == booking.id).limit(1)
        )).scalars().first()
        status = (job.status if job else booking.status or "pending").replace("_", " ").title()
        lines = [f"Booking {booking.booking_number}", f"Status: {status}"]

        scheduled_date = getattr(job, "scheduled_date", None) if job else None
        scheduled_window = getattr(job, "scheduled_time_window", None) if job else None
        if scheduled_date:
            visit = f"Visit: {scheduled_date.isoformat()}"
            if scheduled_window:
                visit += f", {scheduled_window}"
            lines.append(visit)

        # A booking goes to a PROVIDER first; that provider then assigns one of
        # their technicians. `assignment_status` is the provider's answer, so
        # reporting it as "Technician" told the customer someone was on the way
        # when nobody had been picked yet. The technician line appears only once
        # `assigned_staff_id` is actually set.
        provider = (booking.provider_snapshot or {}).get("name") if booking.provider_snapshot else None
        assignment = (booking.assignment_status or "").replace("_", " ").title()
        if provider and assignment:
            lines.append(f"Provider: {provider} — {assignment}")
        elif assignment:
            lines.append(f"Provider: {assignment}")

        staff_id = getattr(job, "assigned_staff_id", None) if job else None
        if staff_id:
            from app.engines.auth.models import User

            technician = await self.db.get(User, staff_id)
            lines.append(f"Technician: {technician.full_name if technician else 'Assigned'}")
        else:
            lines.append("Technician: not assigned yet")
        return chr(10).join(lines)

    async def start_phone_verification(self, thread: MessagingThread, phone: str) -> str:
        """Send the booking's phone-confirmation code.

        The same OTP round trip as the /link command — a booking simply asks
        for it in the flow instead of expecting the customer to know a command.
        """
        message = await self._start_identity_link(thread, phone)
        return message.replace(
            "Reply /verify followed by the 6-digit code.",
            "Send the 6-digit code here.",
        )

    async def stage_phone_verification(self, thread: MessagingThread, phone: str) -> None:
        """Retain a candidate number without sending an OTP.

        OTP delivery can carry a direct cost, so typing or correcting a number
        is never itself authorization to send one. The customer must tap the
        explicit Send OTP action before `start_phone_verification` is called.
        """
        from app.engines.platform_notifications.channel_config_service import (
            channel_config_service,
        )

        encrypted = channel_config_service._fernet().encrypt(phone.encode()).decode()
        thread.pending_customer_id = None
        thread.pending_phone_ciphertext = _PHONE_CONFIRMATION_PREFIX + encrypted
        await self.db.flush()

    def phone_verification_requires_confirmation(self, thread: MessagingThread) -> bool:
        return str(thread.pending_phone_ciphertext or "").startswith(
            _PHONE_CONFIRMATION_PREFIX
        )

    async def confirm_phone_verification(self, thread: MessagingThread) -> str:
        """Send one OTP only after the staged number is explicitly confirmed."""
        if not self.phone_verification_requires_confirmation(thread):
            return "Enter the mobile number you want to verify first."
        phone = self.pending_number(thread)
        if not phone:
            thread.pending_customer_id = None
            thread.pending_phone_ciphertext = None
            return "That mobile number could not be read. Please enter it again."
        return await self.start_phone_verification(thread, phone)

    def pending_number(self, thread: MessagingThread) -> str | None:
        """The number an outstanding OTP was sent to, decrypted for display."""
        if not thread.pending_phone_ciphertext:
            return None
        from app.engines.platform_notifications.channel_config_service import (
            channel_config_service,
        )
        try:
            token = str(thread.pending_phone_ciphertext)
            if token.startswith(_PHONE_CONFIRMATION_PREFIX):
                token = token[len(_PHONE_CONFIRMATION_PREFIX):]
            return channel_config_service._fernet().decrypt(
                token.encode()).decode()
        except Exception:  # noqa: BLE001 — an unreadable token is not a label
            return None

    async def finish_phone_verification(self, thread: MessagingThread, code: str) -> str:
        """Confirm the code, WITHOUT losing the booking it was asked for.

        `_finish_identity_link` deliberately drops the conversation session so
        the /link command starts clean under the newly linked identity. Here
        the customer is halfway through a booking, and that draft hangs off the
        session — dropping it silently discards everything they just answered
        and puts them back at "what do you need help with?".
        """
        session_id = thread.ai_session_id
        message = await self._finish_identity_link(thread, code)
        if thread.customer_id and session_id:
            thread.ai_session_id = session_id
            await self._attach_draft_to_customer(session_id, thread.customer_id)
            message = "Number confirmed."
        return message.replace(
            "Send /link with your mobile number to request a new one.",
            "Send your mobile number again to get a new code.",
        ).replace(
            "Send /link to try again.", "Send your mobile number again to try again.",
        ).replace(
            "Send /link to request a new one.",
            "Send your mobile number again to request a new one.",
        )

    async def _attach_draft_to_customer(
        self, session_id: uuid.UUID, customer_id: uuid.UUID,
    ) -> None:
        """The draft was started before we knew who this was; it does now."""
        from app.engines.home_service_booking.models import HomeServiceBookingDraft

        draft = (await self.db.execute(
            select(HomeServiceBookingDraft)
            .where(HomeServiceBookingDraft.ai_session_id == session_id)
            .order_by(HomeServiceBookingDraft.created_at.desc())
            .limit(1)
        )).scalars().first()
        if draft is not None and draft.customer_id is None:
            draft.customer_id = customer_id
            from app.engines.auth.models import User

            user = await self.db.get(User, customer_id)
            # The number was just confirmed, so it is the one to reach them on
            # — and it is what the summary shows back before they confirm.
            if user is not None and user.phone and not draft.customer_phone:
                draft.customer_phone = user.phone
                draft.customer_name = draft.customer_name or user.full_name
            await self.db.flush()

    async def _start_identity_link(self, thread: MessagingThread, phone: str) -> str:
        """Send an OTP to link an Instagram-scoped identity to a customer."""
        if thread.channel == "whatsapp":
            return "WhatsApp is linked automatically using your verified mobile number."
        import re
        if not re.fullmatch(r"\+?[1-9]\d{7,14}", phone or ""):
            return "Send your number with country code, for example: /link +919876543210"
        since = datetime.now(timezone.utc) - timedelta(hours=1)
        link_attempts = int((await self.db.execute(
            select(func.count()).select_from(MessagingInboundMessage).where(
                MessagingInboundMessage.thread_id == thread.id,
                MessagingInboundMessage.created_at >= since,
                MessagingInboundMessage.body.ilike("/link%"),
            )
        )).scalar() or 0)
        if link_attempts > 3:
            return "Too many linking attempts. Please wait before requesting another code."
        from app.engines.auth.models import User
        from app.engines.auth.service import AuthService

        digits = "".join(ch for ch in phone if ch.isdigit())
        tail = digits[-10:]
        user = (await self.db.execute(
            select(User).where(
                User.role == "customer",
                User.is_active.is_(True),
                User.phone.isnot(None),
                func.right(func.regexp_replace(User.phone, r"\D", "", "g"), 10) == tail,
            ).limit(1)
        )).scalars().first()
        thread.pending_customer_id = user.id if user else None
        from app.engines.platform_notifications.channel_config_service import channel_config_service
        thread.pending_phone_ciphertext = channel_config_service._fernet().encrypt(phone.encode()).decode()
        # Enumeration-safe: send_phone_otp has the same response shape. We do
        # not tell an Instagram sender whether a supplied phone is registered.
        await AuthService(self.db).send_phone_otp(phone, "messaging_link")
        await self.db.flush()
        return (
            "If that number belongs to an active Fuvay account, a verification "
            "code has been sent. Reply /verify followed by the 6-digit code."
        )

    async def _finish_identity_link(self, thread: MessagingThread, code: str) -> str:
        """Verify the one-time code and bind this Instagram identity once."""
        if thread.channel == "whatsapp":
            return "WhatsApp is linked automatically using your verified mobile number."
        if not (code or "").isdigit() or len(code) != 6 or not thread.pending_phone_ciphertext:
            return "That code is invalid or expired. Send /link with your mobile number to request a new one."
        from sqlalchemy import and_
        from app.engines.auth.constants import OTP_MAX_ATTEMPTS
        from app.engines.auth.models import OTPRecord, User
        from app.engines.auth.utils import hash_recipient, verify_otp
        from app.models.base import utcnow
        from app.twilio_client import is_verify_configured, verify_check

        from app.engines.platform_notifications.channel_config_service import channel_config_service
        try:
            phone = channel_config_service._fernet().decrypt(thread.pending_phone_ciphertext.encode()).decode()
        except Exception:
            thread.pending_customer_id = None
            thread.pending_phone_ciphertext = None
            return "That code is invalid or expired. Send /link to try again."
        user = await self.db.get(User, thread.pending_customer_id) if thread.pending_customer_id else None
        if user and (not user.phone or not user.is_active):
            thread.pending_customer_id = None
            thread.pending_phone_ciphertext = None
            return "That code is invalid or expired. Send /link to try again."
        approved = False
        if is_verify_configured():
            approved = await verify_check(phone, code)
        else:
            record = (await self.db.execute(
                select(OTPRecord).where(and_(
                    OTPRecord.purpose == "messaging_link",
                    OTPRecord.recipient_hash == hash_recipient(phone),
                    OTPRecord.is_used.is_(False),
                    OTPRecord.expires_at > utcnow(),
                )).order_by(OTPRecord.created_at.desc()).limit(1)
            )).scalars().first()
            if record:
                record.attempts += 1
                if record.attempts <= OTP_MAX_ATTEMPTS and verify_otp(code, record.hashed_otp):
                    record.is_used = True
                    approved = True
                elif record.attempts >= OTP_MAX_ATTEMPTS:
                    record.is_used = True
        if not approved:
            return "That code is invalid or expired. Send /link to request a new one."
        if not user:
            user = User(
                email=f"customer_ig_{uuid.uuid4().hex[:12]}@serviceos.internal",
                phone=phone,
                full_name=thread.display_name or "Instagram Customer",
                role="customer",
                tenant_id=None,
                is_active=True,
                is_verified=True,
                onboarding_complete=False,
                meta={"registration_source": "instagram_booking"},
            )
            self.db.add(user)
            await self.db.flush()
        thread.customer_id = user.id
        thread.pending_customer_id = None
        thread.pending_phone_ciphertext = None
        thread.ai_session_id = None  # next turn gets the newly linked identity
        await self.db.flush()
        return "Your Instagram chat is now linked to Fuvay. You can book services or send /track."

    def _flow_token(self, thread: MessagingThread, draft_id: str) -> str:
        """Create an expiring token binding a Meta Flow to one chat draft."""
        payload = {
            "v": 1,
            "thread": str(thread.id),
            "draft": str(draft_id),
            "exp": int((datetime.now(timezone.utc) + timedelta(
                hours=WHATSAPP_FLOW_TOKEN_TTL_HOURS,
            )).timestamp()),
        }
        encoded = base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode(),
        ).decode().rstrip("=")
        secret = str(self.channel_config.get("app_secret") or "").encode()
        signature = base64.urlsafe_b64encode(
            hmac.new(secret, encoded.encode(), hashlib.sha256).digest(),
        ).decode().rstrip("=")
        return f"sos1.{encoded}.{signature}"

    async def _validated_flow_reply(
        self, thread: MessagingThread, response: dict,
    ) -> str | None:
        """Return the canonical slot picker id from a valid Flow completion."""
        token = str(response.get("flow_token") or "")
        slot_id = str(
            response.get("slot_id")
            or ((response.get("data") or {}).get("slot_id")
                if isinstance(response.get("data"), dict) else "")
            or ""
        ).strip()
        if not token or not slot_id.startswith("sl|"):
            return None
        try:
            version, encoded, supplied_signature = token.split(".", 2)
            if version != "sos1":
                return None
            secret = str(self.channel_config.get("app_secret") or "").encode()
            expected = base64.urlsafe_b64encode(
                hmac.new(secret, encoded.encode(), hashlib.sha256).digest(),
            ).decode().rstrip("=")
            if not hmac.compare_digest(expected, supplied_signature):
                return None
            padded = encoded + "=" * (-len(encoded) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded).decode())
            if int(payload.get("exp") or 0) < int(datetime.now(timezone.utc).timestamp()):
                return None
            if str(payload.get("thread") or "") != str(thread.id):
                return None
            current = await flow._draft(self.db, thread)
            if not current or str(payload.get("draft") or "") != str(current.get("id")):
                return None
        except (
            TypeError, ValueError, KeyError, json.JSONDecodeError,
            binascii.Error, UnicodeDecodeError,
        ):
            return None
        return slot_id

    async def _as_whatsapp_flow(
        self,
        thread: MessagingThread,
        picker: dict | None,
    ) -> dict | None:
        """Upgrade a slot list to the configured Flow, retaining list fallback."""
        flow_id = str(self.channel_config.get("booking_flow_id") or "").strip()
        if not flow_id or not picker:
            return picker
        if not any(str(row.get("id") or "").startswith("sl|")
                   for row in picker.get("rows") or []):
            return picker

        draft = await flow._draft(self.db, thread)
        if not draft or draft.get("preferred_date"):
            return picker
        all_slots = await pickers.build_picker(
            self.db, draft, customer_id=thread.customer_id,
            channel="whatsapp", page=0, capacity_override=200,
        )
        slot_rows = [
            row for row in ((all_slots or {}).get("rows") or [])
            if str(row.get("id") or "").startswith("sl|")
        ]
        if not slot_rows:
            return picker

        from app.engines.admin_catalog.models import MasterService

        offering = None
        if draft.get("offering_id"):
            offering = await self.db.get(
                MasterService, uuid.UUID(str(draft["offering_id"])),
            )
        provider = draft.get("selected_provider_snapshot") or {}
        price = draft.get("price_snapshot") or {}
        provider_name = (
            provider.get("provider_name") or provider.get("name")
            or provider.get("business_name") or "Provider matched"
        )
        display_price = price.get("display_price")
        if not display_price and price.get("standard_price") is not None:
            display_price = f"INR {price['standard_price']}"
        detail_parts = [str(provider_name)]
        if display_price:
            detail_parts.append(f"Price {display_price}")

        upgraded = dict(picker)
        upgraded["body"] = "Choose a live appointment, then return here to review and confirm."
        upgraded["presentation"] = "flow"
        upgraded["flow"] = {
            "id": flow_id,
            "screen": WHATSAPP_BOOKING_FLOW_SCREEN,
            "cta": WHATSAPP_BOOKING_FLOW_CTA,
            "token": self._flow_token(thread, str(draft["id"])),
            "data": {
                "service": str(getattr(offering, "service_name", None) or "Home service")[:80],
                "booking_details": " · ".join(detail_parts)[:300],
                "address": (flow._address({}, draft) or "Service address saved")[:300],
                "available_slots": [{
                    "id": str(row["id"]),
                    "title": str(row.get("title") or "Appointment")[:30],
                    "description": " · ".join(str(value) for value in (
                        row.get("section"), row.get("description"),
                    ) if value)[:300] or "Available",
                } for row in slot_rows[:200]],
            },
        }
        return upgraded

    async def _advance(
        self, thread: MessagingThread, msg: InboundMessage, ignore_input: bool = False,
    ) -> tuple[str | None, dict | None]:
        """Run one step of the scripted booking flow.

        No model is consulted anywhere in here. `flow` reads the customer's
        answer, applies it through the booking services, and returns the next
        admin-defined question — so what the customer sees is exactly what an
        admin configured in the catalog, in the order the catalog defines.
        """
        try:
            # The draft hangs off a conversation session, which is a plain row:
            # creating it costs a insert, not an inference.
            await self.ensure_session(thread)
            turn = await flow.advance(
                self.db, thread,
                text="" if ignore_input else (msg.text or ""),
                reply_id=None if ignore_input else msg.reply_id,
                channel=msg.channel,
                identity=self,
                location=msg.location,
                location_unavailable=msg.location_unavailable,
            )
            picker = turn.picker
            typed = (msg.text or "").strip().lower()
            if msg.channel == "whatsapp" and typed not in {
                "times", "time", "show times", "show time slots",
            }:
                picker = await self._as_whatsapp_flow(thread, picker)
                if picker and picker.get("presentation") == "flow":
                    fallback = "If the booking form does not open, reply TIMES."
                    turn.text = f"{turn.text}\n\n{fallback}" if turn.text else fallback
            return turn.text, picker
        except Exception as exc:
            logger.warning("messaging_gateway.flow.failed",
                           thread_id=str(thread.id), error=str(exc))
            # A failed flush inside a booking service poisons the session.
            # Roll it back so the webhook can still return a controlled reply.
            try:
                await self.db.rollback()
            except Exception:  # noqa: BLE001 - nothing left to salvage
                pass
            return ("Sorry — something went wrong on my side. "
                    "Tap Start over to try again."), None
