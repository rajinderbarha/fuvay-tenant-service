"""Messaging Gateway service — inbound message -> existing AI agent -> reply.

Deliberately thin. All conversational intelligence, tool calling and booking
logic belongs to `app.engines.ai_conversation`; this module only resolves who
is speaking, which session they are in, and whether the message was a command.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.messaging_gateway import handoff, meta_client
from app.engines.messaging_gateway.constants import (
    CMD_HELP, CMD_HUMAN, CMD_RESET, CMD_START, CMD_STOP, COMMAND_PREFIX,
    HANDOFF_TEXT, HELP_TEXT, KNOWN_COMMANDS, MAX_SESSIONS_PER_SENDER_PER_HOUR,
    STATUS_DUPLICATE, STATUS_FAILED, STATUS_IGNORED, STATUS_PROCESSED,
    STOP_TEXT,
)
from app.engines.messaging_gateway.meta_client import InboundMessage
from app.engines.messaging_gateway.models import MessagingInboundMessage, MessagingThread

logger = structlog.get_logger(__name__)

GREETING = (
    "Hi{name}! I'm Fuvay. Tell me what you need — for example "
    "\"AC not cooling in Ludhiana\" — and I'll get it booked."
)

BUSY_TEXT = (
    "You've started several conversations in a short time. "
    "Please continue in this chat, or try again shortly."
)

UNSUPPORTED_TEXT = (
    "I can only read text messages here. Please describe what you need in a "
    "message, and you can add photos once we've started your booking."
)


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


class MessagingGatewayService:
    def __init__(self, db: AsyncSession, request_id: str = "—"):
        self.db = db
        self.request_id = request_id

    # ── Threads & identity ───────────────────────────────────────────────────

    async def get_or_create_thread(self, msg: InboundMessage) -> MessagingThread:
        thread = (await self.db.execute(
            select(MessagingThread).where(
                MessagingThread.channel == msg.channel,
                MessagingThread.channel_user_id == msg.from_id,
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
        self.db.add(thread)
        try:
            await self.db.flush()
        except IntegrityError:
            # Two messages from the same new sender can arrive concurrently.
            await self.db.rollback()
            thread = (await self.db.execute(
                select(MessagingThread).where(
                    MessagingThread.channel == msg.channel,
                    MessagingThread.channel_user_id == msg.from_id,
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
        user = (await self.db.execute(
            select(User).where(
                User.role == "customer",
                User.phone.isnot(None),
                func.right(func.regexp_replace(User.phone, r"\D", "", "g"), 10) == tail,
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

        command = parse_command(msg.text)
        reply: str | None = None

        # ── Commands ─────────────────────────────────────────────────────────
        if command == CMD_STOP:
            thread.opted_out = True
            reply = STOP_TEXT
        elif command == CMD_HELP:
            reply = HELP_TEXT
        elif command == CMD_HUMAN:
            thread.human_handoff = True
            reply = HANDOFF_TEXT
        elif command in (CMD_START, CMD_RESET):
            # /fuvay is the explicit start-over: drop the old session so the
            # next turn opens a clean one, and re-enable a stopped thread.
            thread.ai_session_id = None
            thread.opted_out = False
            thread.human_handoff = False
            carried = command_remainder(msg.text)
            if not carried:
                name = f" {thread.display_name.split()[0]}" if thread.display_name else ""
                reply = GREETING.format(name=name)
            else:
                # "/fuvay AC not cooling" — start fresh AND answer the request
                # in one turn instead of making them type it twice.
                reply = await self._ask_agent(thread, carried)

        # ── Ordinary message ─────────────────────────────────────────────────
        elif thread.human_handoff:
            reply = None  # an agent owns this thread; stay quiet
        elif not (msg.text or "").strip():
            reply = UNSUPPORTED_TEXT
        elif await self._rate_limited(thread):
            reply = BUSY_TEXT
        else:
            reply = await self._ask_agent(thread, msg.text)

        sent = False
        if reply and not thread.opted_out or (reply and command == CMD_STOP):
            # /stop still gets its one acknowledgement.
            result = await meta_client.send_text(msg.from_id, reply, channel=msg.channel)
            sent = bool(result.get("sent"))
            if sent:
                thread.last_outbound_at = datetime.now(timezone.utc)

        record.status = STATUS_PROCESSED if reply is not None else STATUS_IGNORED
        await self.db.commit()
        return {"status": record.status, "reply_sent": sent,
                "thread_id": str(thread.id), "command": command}

    async def _ask_agent(self, thread: MessagingThread, text: str) -> str:
        """Hand the message to the existing DeepSeek agent and return its reply."""
        from app.engines.ai_conversation.service import AIConversationService

        try:
            session_id = await self.ensure_session(thread)
            svc = AIConversationService(self.db)
            result = await svc.send_message(
                session_id=session_id,
                user_message=text,
                customer_id=thread.customer_id,
            )
            reply = str(result.get("reply") or "").strip() or (
                "Sorry — I didn't catch that. Could you say it another way?"
            )
            suffix = await self._maybe_handoff(thread, session_id)
            return f"{reply}\n\n{suffix}" if suffix else reply
        except Exception as exc:
            # The agent's own guards (session closed, turn cap, rate limit)
            # raise; a customer should get a usable sentence, not a 500.
            logger.warning("messaging_gateway.agent.failed",
                           thread_id=str(thread.id), error=str(exc))
            thread.ai_session_id = None
            return ("Sorry — something went wrong on my side. "
                    "Send /fuvay to start again.")

    async def _maybe_handoff(self, thread: MessagingThread, session_id: uuid.UUID) -> str | None:
        """Return a one-line prompt + link when the draft needs a screen.

        Comparison steps — pick a type or brand from a list, compare matched
        providers, pick a slot from a grid — are not conversation. Rather than
        let the agent interrogate the customer through them, hand off once.

        Best-effort throughout: a handoff is an enhancement to the reply, so
        any failure here must leave the customer with the agent's answer rather
        than an error.
        """
        try:
            draft = await self._resolve_draft(session_id)
            reason = handoff.detect_handoff(draft)
            if not reason:
                return None

            # Do not re-send the same link every turn; one per reason per draft
            # until it is used or expires.
            draft_id = uuid.UUID(str(draft["id"])) if draft.get("id") else None
            if await self._handoff_already_open(draft_id, reason):
                return None

            url = await handoff.issue_link(
                self.db,
                thread_id=thread.id,
                customer_id=thread.customer_id,
                draft_id=draft_id,
                reason=reason,
            )
            if not url:
                return None
            return f"{handoff.REASON_TEXT.get(reason, 'Continue here:')}\n{url}"
        except Exception as exc:
            logger.warning("messaging_gateway.handoff.failed",
                           thread_id=str(thread.id), error=str(exc))
            return None

    async def _resolve_draft(self, session_id: uuid.UUID) -> dict | None:
        """The booking draft attached to this agent session, enriched.

        `required_fields` is NOT a column — the booking service derives it from
        the offering's `is_type_required` / `is_brand_required` /
        `requires_schedule` flags. `detect_handoff` needs it to tell "this draft
        has no brand because none is required" from "this draft is stuck waiting
        for a brand", so it is recomputed here from the same flags.
        """
        from app.engines.admin_catalog.models import MasterService
        from app.engines.home_service_booking.models import HomeServiceBookingDraft

        row = (await self.db.execute(
            select(HomeServiceBookingDraft)
            .where(HomeServiceBookingDraft.ai_session_id == session_id)
            .order_by(HomeServiceBookingDraft.created_at.desc())
            .limit(1)
        )).scalars().first()
        if not row:
            return None

        data = row.to_dict()
        required = ["issue_summary", "city"]
        offering = await self.db.get(MasterService, row.offering_id) if row.offering_id else None
        if offering is not None:
            if offering.is_type_required:
                required.append("offering_type_id")
            if offering.is_brand_required:
                required.append("brand_id")
            if offering.requires_schedule:
                required.append("preferred_date")
        data["required_fields"] = required
        return data

    async def _handoff_already_open(self, draft_id: uuid.UUID | None, reason: str) -> bool:
        if not draft_id:
            return False
        # Imported locally and aliased: `text` is a parameter name throughout
        # this class, so a module-level import would be shadowed.
        from sqlalchemy import text as _text
        found = (await self.db.execute(_text("""
            SELECT 1 FROM messaging_handoff_links
             WHERE draft_id = :d AND reason = :r
               AND status = 'active' AND expires_at > now()
             LIMIT 1
        """), {"d": str(draft_id), "r": reason})).first()
        return bool(found)
