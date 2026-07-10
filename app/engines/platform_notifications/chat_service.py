"""Sprint 27 — Chat Thread + Message Services.

Rules:
- Thread requires linked record.
- Provider cannot access other tenant's threads.
- Customer cannot access other customer's threads.
- Closed/blocked threads block new messages.
- Message visibility enforced per sender_type.
- All sends create audit log + notification to other participants.
"""
from __future__ import annotations
import uuid
import random
import string
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.platform_notifications.constants import (
    THREAD_OPEN, THREAD_CLOSED, THREAD_ARCHIVED, THREAD_BLOCKED,
    TERMINAL_THREAD_STATUSES,
    MSG_TEXT, MSG_SYSTEM, VIS_THREAD,
    MSG_SENT, RECIP_CUSTOMER, RECIP_PROVIDER, RECIP_STAFF, RECIP_ADMIN,
    ERR_CHAT_THREAD_NOT_FOUND, ERR_CHAT_THREAD_ACCESS_DENIED,
    ERR_CHAT_THREAD_CLOSED, ERR_CHAT_MESSAGE_REQUIRED,
    ERR_CHAT_MESSAGE_NOT_FOUND, ERR_CHAT_CANNOT_SEND,
)
from app.engines.platform_notifications.models import (
    ChatThread, ChatThreadParticipant, ChatMessage, ChatMessageRead,
)

log = structlog.get_logger("chat_service")
utcnow = lambda: datetime.now(timezone.utc)


def _gen_thread_number() -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"THR-{suffix}"


class ChatThreadService:

    async def get_or_create_thread(
        self,
        db: AsyncSession,
        record_type: str,
        record_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_type: str,
        tenant_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
    ) -> ChatThread:
        r = await db.execute(
            select(ChatThread).where(
                ChatThread.record_type == record_type,
                ChatThread.record_id == record_id,
            )
        )
        thread = r.scalars().first()
        if thread:
            await self.validate_thread_access(db, thread, actor_user_id, actor_type, tenant_id)
            return thread
        return await self.create_thread(
            db=db, record_type=record_type, record_id=record_id,
            actor_user_id=actor_user_id, actor_type=actor_type,
            tenant_id=tenant_id, customer_id=customer_id,
        )

    async def create_thread(
        self,
        db: AsyncSession,
        record_type: str,
        record_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_type: str,
        tenant_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        initial_participants: list[dict] | None = None,
    ) -> ChatThread:
        thread = ChatThread(
            thread_number=_gen_thread_number(),
            tenant_id=tenant_id,
            customer_id=customer_id,
            record_type=record_type,
            record_id=record_id,
            status=THREAD_OPEN,
            created_by_user_id=actor_user_id,
        )
        db.add(thread)
        await db.flush()

        # Add creator as participant
        participants = initial_participants or []
        creator_already_added = any(str(p.get("user_id")) == str(actor_user_id) for p in participants)
        if not creator_already_added:
            participants = [{"user_id": actor_user_id, "participant_type": actor_type,
                             "tenant_id": tenant_id}] + participants

        for p in participants:
            await self._add_participant(db, thread.id, p)

        await db.commit()
        return thread

    async def list_threads(
        self,
        db: AsyncSession,
        actor_user_id: uuid.UUID,
        actor_type: str,
        tenant_id: uuid.UUID | None = None,
        status: str | None = None,
        limit: int = 30,
        offset: int = 0,
    ) -> dict:
        # Find thread IDs where user is participant
        part_q = select(ChatThreadParticipant.thread_id).where(
            ChatThreadParticipant.user_id == actor_user_id,
            ChatThreadParticipant.left_at == None,
        )
        part_r = await db.execute(part_q)
        thread_ids = [row[0] for row in part_r.all()]

        q = select(ChatThread).where(ChatThread.id.in_(thread_ids))
        if status:
            q = q.where(ChatThread.status == status)
        if actor_type in (RECIP_PROVIDER, RECIP_STAFF) and tenant_id:
            q = q.where(ChatThread.tenant_id == tenant_id)
        elif actor_type == RECIP_CUSTOMER:
            q = q.where(ChatThread.customer_id == actor_user_id)

        total_r = await db.execute(select(func.count()).select_from(q.subquery()))
        total = total_r.scalar_one()
        r = await db.execute(q.order_by(ChatThread.last_message_at.desc().nullslast()).limit(limit).offset(offset))
        items = r.scalars().all()
        return {"items": [t.to_dict() for t in items], "total": total}

    async def get_thread(
        self,
        db: AsyncSession,
        thread_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_type: str,
        tenant_id: uuid.UUID | None = None,
    ) -> ChatThread:
        r = await db.execute(select(ChatThread).where(ChatThread.id == thread_id))
        thread = r.scalars().first()
        if not thread:
            raise ValueError(ERR_CHAT_THREAD_NOT_FOUND)
        await self.validate_thread_access(db, thread, actor_user_id, actor_type, tenant_id)
        return thread

    async def close_thread(
        self,
        db: AsyncSession,
        thread_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_type: str,
        reason: str | None = None,
    ) -> ChatThread:
        r = await db.execute(select(ChatThread).where(ChatThread.id == thread_id))
        thread = r.scalars().first()
        if not thread:
            raise ValueError(ERR_CHAT_THREAD_NOT_FOUND)
        thread.status = THREAD_CLOSED
        await db.commit()
        return thread

    async def validate_thread_access(
        self,
        db: AsyncSession,
        thread: ChatThread,
        actor_user_id: uuid.UUID,
        actor_type: str,
        tenant_id: uuid.UUID | None,
    ) -> None:
        if actor_type == RECIP_ADMIN:
            return  # Admin can access all threads
        if actor_type == RECIP_CUSTOMER:
            if str(thread.customer_id) != str(actor_user_id):
                raise ValueError(ERR_CHAT_THREAD_ACCESS_DENIED)
        elif actor_type in (RECIP_PROVIDER, RECIP_STAFF):
            if tenant_id and thread.tenant_id and str(thread.tenant_id) != str(tenant_id):
                raise ValueError(ERR_CHAT_THREAD_ACCESS_DENIED)
        # Verify participant record
        r = await db.execute(
            select(ChatThreadParticipant).where(
                ChatThreadParticipant.thread_id == thread.id,
                ChatThreadParticipant.user_id == actor_user_id,
            )
        )
        if not r.scalars().first() and actor_type != RECIP_ADMIN:
            raise ValueError(ERR_CHAT_THREAD_ACCESS_DENIED)

    async def add_participant(
        self,
        db: AsyncSession,
        thread_id: uuid.UUID,
        participant: dict,
    ) -> ChatThreadParticipant:
        return await self._add_participant(db, thread_id, participant)

    async def _add_participant(
        self,
        db: AsyncSession,
        thread_id: uuid.UUID,
        participant: dict,
    ) -> ChatThreadParticipant:
        user_id = participant["user_id"]
        r = await db.execute(
            select(ChatThreadParticipant).where(
                ChatThreadParticipant.thread_id == thread_id,
                ChatThreadParticipant.user_id == uuid.UUID(str(user_id)),
            )
        )
        existing = r.scalars().first()
        if existing:
            return existing
        p = ChatThreadParticipant(
            thread_id=thread_id,
            user_id=uuid.UUID(str(user_id)),
            participant_type=participant.get("participant_type", "customer"),
            tenant_id=participant.get("tenant_id"),
            can_read=participant.get("can_read", True),
            can_send=participant.get("can_send", True),
        )
        db.add(p)
        await db.flush()
        return p


class ChatMessageService:

    def __init__(self, thread_svc: ChatThreadService | None = None):
        self._thread_svc = thread_svc or ChatThreadService()

    async def send_message(
        self,
        db: AsyncSession,
        thread_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_type: str,
        tenant_id: uuid.UUID | None,
        message_text: str | None,
        message_type: str = MSG_TEXT,
        visibility: str = VIS_THREAD,
        media_urls: list | None = None,
        metadata: dict | None = None,
    ) -> ChatMessage:
        # Validate thread exists and is open
        r = await db.execute(select(ChatThread).where(ChatThread.id == thread_id))
        thread = r.scalars().first()
        if not thread:
            raise ValueError(ERR_CHAT_THREAD_NOT_FOUND)
        if thread.status in TERMINAL_THREAD_STATUSES:
            raise ValueError(ERR_CHAT_THREAD_CLOSED)

        # Validate actor is participant with can_send
        await self._thread_svc.validate_thread_access(db, thread, actor_user_id, actor_type, tenant_id)
        part_r = await db.execute(
            select(ChatThreadParticipant).where(
                ChatThreadParticipant.thread_id == thread_id,
                ChatThreadParticipant.user_id == actor_user_id,
            )
        )
        participant = part_r.scalars().first()
        if participant and not participant.can_send and actor_type != RECIP_ADMIN:
            raise ValueError(ERR_CHAT_CANNOT_SEND)

        if not message_text and not media_urls:
            raise ValueError(ERR_CHAT_MESSAGE_REQUIRED)

        msg = ChatMessage(
            thread_id=thread_id,
            sender_user_id=actor_user_id,
            sender_type=actor_type,
            message_type=message_type,
            message_text=message_text,
            media_urls=media_urls,
            metadata=metadata,
            visibility=visibility,
            delivery_status=MSG_SENT,
        )
        db.add(msg)
        thread.last_message_at = utcnow()
        await db.commit()
        return msg

    async def list_messages(
        self,
        db: AsyncSession,
        thread_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_type: str,
        tenant_id: uuid.UUID | None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        r = await db.execute(select(ChatThread).where(ChatThread.id == thread_id))
        thread = r.scalars().first()
        if not thread:
            raise ValueError(ERR_CHAT_THREAD_NOT_FOUND)
        await self._thread_svc.validate_thread_access(db, thread, actor_user_id, actor_type, tenant_id)

        q = select(ChatMessage).where(
            ChatMessage.thread_id == thread_id,
            ChatMessage.is_hidden == False,
        )
        total_r = await db.execute(select(func.count()).select_from(q.subquery()))
        total = total_r.scalar_one()
        r = await db.execute(q.order_by(ChatMessage.created_at.asc()).limit(limit).offset(offset))
        all_msgs = r.scalars().all()
        visible = [m.to_dict(actor_type) for m in all_msgs if m.to_dict(actor_type)]
        return {"items": visible, "total": total}

    async def mark_thread_read(
        self,
        db: AsyncSession,
        thread_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        actor_type: str,
        tenant_id: uuid.UUID | None,
    ) -> int:
        r = await db.execute(select(ChatThread).where(ChatThread.id == thread_id))
        thread = r.scalars().first()
        if not thread:
            raise ValueError(ERR_CHAT_THREAD_NOT_FOUND)
        await self._thread_svc.validate_thread_access(db, thread, actor_user_id, actor_type, tenant_id)

        msg_r = await db.execute(
            select(ChatMessage).where(ChatMessage.thread_id == thread_id)
        )
        messages = msg_r.scalars().all()
        count = 0
        for msg in messages:
            read_r = await db.execute(
                select(ChatMessageRead).where(
                    ChatMessageRead.message_id == msg.id,
                    ChatMessageRead.user_id == actor_user_id,
                )
            )
            if not read_r.scalars().first():
                db.add(ChatMessageRead(
                    message_id=msg.id,
                    thread_id=thread_id,
                    user_id=actor_user_id,
                    read_at=utcnow(),
                ))
                count += 1
        if count:
            await db.commit()
        return count

    async def add_system_message(
        self,
        db: AsyncSession,
        thread_id: uuid.UUID,
        message_text: str,
        metadata: dict | None = None,
    ) -> ChatMessage:
        r = await db.execute(select(ChatThread).where(ChatThread.id == thread_id))
        thread = r.scalars().first()
        if not thread:
            raise ValueError(ERR_CHAT_THREAD_NOT_FOUND)
        msg = ChatMessage(
            thread_id=thread_id,
            sender_user_id=None,
            sender_type="system",
            message_type=MSG_SYSTEM,
            message_text=message_text,
            visibility=VIS_THREAD,
            metadata=metadata,
            delivery_status=MSG_SENT,
        )
        db.add(msg)
        thread.last_message_at = utcnow()
        await db.commit()
        return msg

    async def moderate_message(
        self,
        db: AsyncSession,
        message_id: uuid.UUID,
        admin_user_id: uuid.UUID,
        reason: str,
    ) -> ChatMessage:
        r = await db.execute(select(ChatMessage).where(ChatMessage.id == message_id))
        msg = r.scalars().first()
        if not msg:
            raise ValueError(ERR_CHAT_MESSAGE_NOT_FOUND)
        msg.is_hidden = True
        msg.hidden_by_user_id = admin_user_id
        msg.hidden_at = utcnow()
        if msg.msg_metadata is None:
            msg.msg_metadata = {}
        msg.msg_metadata["hide_reason"] = reason
        await db.commit()
        return msg
