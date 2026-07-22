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
    MSG_TEXT, MSG_SYSTEM, VIS_THREAD, VIS_ADMIN_ONLY, VIS_PROVIDER_ONLY, VIS_CUSTOMER_ONLY,
    MSG_SENT, RECIP_CUSTOMER, RECIP_PROVIDER, RECIP_STAFF, RECIP_TECHNICIAN, RECIP_ADMIN,
    ERR_CHAT_THREAD_NOT_FOUND, ERR_CHAT_THREAD_ACCESS_DENIED,
    ERR_CHAT_THREAD_CLOSED, ERR_CHAT_MESSAGE_REQUIRED,
    ERR_CHAT_MESSAGE_NOT_FOUND, ERR_CHAT_CANNOT_SEND,
    ERR_CHAT_RECORD_NOT_FOUND, ERR_CHAT_RECORD_ACCESS_DENIED,
    ERR_CHAT_INVALID_VISIBILITY,
    ERR_CHAT_ATTACHMENT_NOT_FOUND, ERR_CHAT_ATTACHMENT_ACCESS_DENIED,
)

# Record types _resolve_record_parties can actually verify against a real
# row. Any other record_type legitimately resolves to (None, None) and is
# not blocked here — but for these types, a caller-supplied record_id that
# doesn't resolve to a real row (or resolves to a DIFFERENT tenant's row
# than the caller's own) must never silently create an orphaned/mismatched
# thread.
_RESOLVABLE_RECORD_TYPES = ("service_booking", "service_job", "complaint")
_VALID_VISIBILITIES = {VIS_THREAD, VIS_ADMIN_ONLY, VIS_PROVIDER_ONLY, VIS_CUSTOMER_ONLY}
from app.engines.platform_notifications.models import (
    ChatThread, ChatThreadParticipant, ChatMessage, ChatMessageRead, InAppNotification,
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

    async def _resolve_record_parties(
        self, db: AsyncSession, record_type: str, record_id: uuid.UUID,
    ) -> tuple[uuid.UUID | None, uuid.UUID | None]:
        """The (tenant_id, customer_id) that own a linked record.

        A customer opening a thread only knows its own id — the provider side is
        implied by the booking/job/complaint. Without resolving it the thread is
        created with tenant_id=NULL and the provider, who lists threads by their
        tenant, never sees the customer's messages. So chat is only two-sided if
        the tenant is filled in here.
        """
        try:
            if record_type in ("service_booking", "service_job"):
                from app.engines.final_records.models import ServiceBooking, ServiceJob
                if record_type == "service_job":
                    job = await db.get(ServiceJob, record_id)
                    if job is None:
                        return (None, None)
                    booking = await db.get(ServiceBooking, job.booking_id) if job.booking_id else None
                else:
                    booking = await db.get(ServiceBooking, record_id)
                if booking is not None:
                    return (booking.tenant_id, booking.customer_id)
            elif record_type == "complaint":
                from app.engines.complaints.models import CustomerComplaint
                comp = await db.get(CustomerComplaint, record_id)
                if comp is not None:
                    return (comp.tenant_id, comp.customer_id)
        except Exception:
            # Resolution is best-effort; never block thread creation on it.
            return (None, None)
        return (None, None)

    async def _provider_participants(
        self, db: AsyncSession, tenant_id: uuid.UUID, record_type: str, record_id: uuid.UUID,
    ) -> list[dict]:
        """The provider-side users who should be in a thread: the tenant owner,
        plus the staff member assigned to the record (if any). Without these the
        provider cannot see or open the customer's thread."""
        parts: list[dict] = []
        try:
            from app.engines.tenant_engine.models import Tenant
            tenant = await db.get(Tenant, tenant_id)
            owner_id = getattr(tenant, "owner_user_id", None) if tenant else None
            if owner_id:
                parts.append({"user_id": owner_id, "participant_type": RECIP_PROVIDER,
                              "tenant_id": tenant_id})

            staff_id = None
            if record_type in ("service_booking", "service_job"):
                from app.engines.final_records.models import ServiceBooking, ServiceJob
                if record_type == "service_job":
                    job = await db.get(ServiceJob, record_id)
                else:
                    booking = await db.get(ServiceBooking, record_id)
                    job = (await db.execute(
                        select(ServiceJob).where(ServiceJob.booking_id == record_id))
                    ).scalars().first() if booking else None
                staff_id = getattr(job, "assigned_staff_id", None) if job else None
            if staff_id and str(staff_id) != str(owner_id):
                parts.append({"user_id": staff_id, "participant_type": RECIP_STAFF,
                              "tenant_id": tenant_id})
        except Exception:
            return parts
        return parts

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
        # Fill in whichever party the caller didn't supply from the linked record,
        # so a customer-created thread still knows its provider (and vice versa).
        # Real router callers always supply exactly one side (provider/staff
        # supply tenant_id only; customer supplies customer_id only), so this
        # is also exactly the branch that needs to verify the record — a
        # caller supplying BOTH already claims full, pre-validated identity
        # and skips resolution (as before).
        if tenant_id is None or customer_id is None:
            rec_tenant, rec_customer = await self._resolve_record_parties(db, record_type, record_id)
            if record_type in _RESOLVABLE_RECORD_TYPES and rec_tenant is None:
                # The record_id doesn't resolve to a real row of this type —
                # refuse to create a thread pinned to a record that doesn't exist.
                raise ValueError(ERR_CHAT_RECORD_NOT_FOUND)
            if (
                tenant_id is not None
                and rec_tenant is not None
                and str(tenant_id) != str(rec_tenant)
            ):
                # Caller's own tenant does not own the referenced record —
                # refuse to let a provider/staff user pin a thread to another
                # tenant's job.
                raise ValueError(ERR_CHAT_RECORD_ACCESS_DENIED)
            if (
                customer_id is not None
                and rec_customer is not None
                and str(customer_id) != str(rec_customer)
            ):
                # Caller-supplied customer_id does not match the record's
                # actual customer — refuse to let a customer pin a thread to
                # another customer's booking/job/complaint.
                raise ValueError(ERR_CHAT_RECORD_ACCESS_DENIED)
            tenant_id = tenant_id or rec_tenant
            customer_id = customer_id or rec_customer

        # Seed the OTHER side as participants. Threads are participant-gated for
        # both listing and access, so a customer-created thread is invisible to
        # the provider unless the provider side is added here. Add the tenant
        # owner (and the assigned staff, if any) as provider-side participants.
        if tenant_id is not None:
            provider_parts = await self._provider_participants(db, tenant_id, record_type, record_id)
            existing_ids = {str(p.get("user_id")) for p in (initial_participants or [])}
            initial_participants = (initial_participants or []) + [
                p for p in provider_parts if str(p["user_id"]) not in existing_ids
                and str(p["user_id"]) != str(actor_user_id)
            ]
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
        # A provider/staff user sees every thread for THEIR TENANT — not only the
        # threads they were individually added to. The provider handling chat is
        # rarely the exact user a customer-opened thread happened to seed, so
        # participant-only scoping made customer threads invisible to the rest of
        # the provider's team. The customer side stays scoped to its own threads.
        if actor_type in (RECIP_PROVIDER, RECIP_STAFF) and tenant_id:
            q = select(ChatThread).where(ChatThread.tenant_id == tenant_id)
        else:
            part_q = select(ChatThreadParticipant.thread_id).where(
                ChatThreadParticipant.user_id == actor_user_id,
                ChatThreadParticipant.left_at == None,
            )
            thread_ids = [row[0] for row in (await db.execute(part_q)).all()]
            q = select(ChatThread).where(ChatThread.id.in_(thread_ids))
            if actor_type == RECIP_CUSTOMER:
                q = q.where(ChatThread.customer_id == actor_user_id)
        if status:
            q = q.where(ChatThread.status == status)

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
        # Slice 2F-18A: denial always raises ERR_CHAT_THREAD_NOT_FOUND (not
        # ERR_CHAT_THREAD_ACCESS_DENIED) so a nonexistent thread and a
        # real-but-unauthorized thread are externally privacy equivalent
        # (same error_code -> same 404 via the generic domain-code status
        # mapping in app/exceptions.py, matching the established
        # Booking-series precedent). ERR_CHAT_THREAD_ACCESS_DENIED is kept
        # as a constant for internal/log use only.
        if actor_type == RECIP_ADMIN:
            return  # Admin can access all threads
        if actor_type == RECIP_CUSTOMER:
            # A customer may only touch its own thread — ownership IS the gate.
            if str(thread.customer_id) != str(actor_user_id):
                raise ValueError(ERR_CHAT_THREAD_NOT_FOUND)
            return
        if actor_type == RECIP_TECHNICIAN:
            # Ratified interim policy (Slice 2F-18A): a technician gets NO
            # tenant-wide access. Access requires either (a) being currently
            # assigned to the exact parent ServiceJob a resolvable thread is
            # linked to (live assignment, not a stale participant snapshot —
            # a technician reassigned off the job loses access even if an
            # old participant row still exists), or (b) for record types
            # this service cannot resolve to a Job/assignment, an explicit
            # ACTIVE (not left) participant row.
            job = await self._resolve_job_for_thread(db, thread)
            if job is not None:
                if str(getattr(job, "assigned_staff_id", None) or "") == str(actor_user_id):
                    return
                raise ValueError(ERR_CHAT_THREAD_NOT_FOUND)
            r = await db.execute(
                select(ChatThreadParticipant).where(
                    ChatThreadParticipant.thread_id == thread.id,
                    ChatThreadParticipant.user_id == actor_user_id,
                    ChatThreadParticipant.left_at == None,  # noqa: E711
                )
            )
            if not r.scalars().first():
                raise ValueError(ERR_CHAT_THREAD_NOT_FOUND)
            return
        if actor_type in (RECIP_PROVIDER, RECIP_STAFF):
            # Tenant match is the gate for the office/owner side: any
            # authorized office user of the owning tenant may handle its
            # customer threads (not only the one who happens to be a
            # participant row). Technician is handled separately above and
            # NEVER reaches this branch.
            if thread.tenant_id and tenant_id and str(thread.tenant_id) == str(tenant_id):
                return
            raise ValueError(ERR_CHAT_THREAD_NOT_FOUND)
        # Anyone else must be an active participant.
        r = await db.execute(
            select(ChatThreadParticipant).where(
                ChatThreadParticipant.thread_id == thread.id,
                ChatThreadParticipant.user_id == actor_user_id,
                ChatThreadParticipant.left_at == None,  # noqa: E711
            )
        )
        if not r.scalars().first():
            raise ValueError(ERR_CHAT_THREAD_NOT_FOUND)

    async def _resolve_job_for_thread(self, db: AsyncSession, thread: ChatThread):
        """The ServiceJob a resolvable thread is linked to, or None.

        Only `service_job`/`service_booking` record types resolve to a real
        assignment concept — never adapts a ServiceJob id to field_ops.Job
        or a ServiceBooking id to the legacy Booking model.
        """
        try:
            if thread.record_type == "service_job":
                from app.engines.final_records.models import ServiceJob
                return await db.get(ServiceJob, thread.record_id)
            if thread.record_type == "service_booking":
                from app.engines.final_records.models import ServiceJob
                r = await db.execute(
                    select(ServiceJob).where(ServiceJob.booking_id == thread.record_id)
                )
                return r.scalars().first()
        except Exception:
            return None
        return None

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
        actor: "UserContext | None" = None,
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

        # Visibility is caller-supplied free text on every router; reject any
        # value outside the known enum, and only an admin may set a
        # restricted (non-thread-wide) visibility — a provider/staff/customer
        # sender cannot mark their own message admin_only/provider_only/
        # customer_only to hide it from (or fake exclusivity to) the other
        # side of the conversation.
        if visibility not in _VALID_VISIBILITIES:
            raise ValueError(ERR_CHAT_INVALID_VISIBILITY)
        if visibility != VIS_THREAD and actor_type != RECIP_ADMIN:
            raise ValueError(ERR_CHAT_INVALID_VISIBILITY)

        await self._validate_attachments(db, thread, media_urls, actor)

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
        await self._notify_other_participants(db, thread, actor_user_id, actor_type, message_text)
        await db.commit()
        return msg

    async def _validate_attachments(
        self, db: AsyncSession, thread: ChatThread, media_urls, actor,
    ) -> None:
        """Slice 2F-18B: ATTACHMENT_MODEL_SUPPORTED disposition, reusing the
        EXISTING media authorization helper instead of a tenant-only check.

        `media_ids` reference `app.engines.media.models.MediaAsset` rows (a
        real, existing media engine — not built here). Every referenced ID
        must, using only EXISTING MediaAsset fields (no new column, no
        migration):

        1. Resolve to a real, active (not soft-deleted / not
           `status != "active"`) asset.
        2. Have `media_context == "chat_attachment"` — the media engine's
           own pre-existing purpose taxonomy already distinguishes chat
           attachments from unrelated contexts (`provider_document`,
           `customer_profile_photo`, ...); using an asset uploaded for a
           different purpose in a chat message is rejected as an
           unsupported reference, not silently allowed.
        3. Belong to the same tenant as the thread (tenant equality; kept
           from 2F-18A).
        4. Belong to the same customer as the thread, when BOTH the thread
           and the asset carry a `customer_id` — this uses the asset's
           EXISTING `customer_id` column to reject cross-customer
           substitution within the same tenant (Media B attached to
           Customer A's thread), which Slice 2F-18A's tenant-only check
           could not catch.
        5. Pass `MediaAccessService.assert_can_view(actor, asset)` — the
           EXISTING, centralized media access-control helper
           (`app.engines.media.access`), reused directly rather than
           duplicated. This is what actually proves the ACTING PRINCIPAL
           (not just the tenant) is authorized to use/view this specific
           asset: a customer may only view their own uploads; a
           tenant_owner/staff/technician may view any customer-context
           asset in their own tenant (existing, tenant-wide-for-media
           policy — see `known-limitations.md` for why this is not
           narrowed further here) or their own uploads.

        Every rejection raises the SAME error code regardless of which
        condition failed — privacy equivalence (a caller cannot
        distinguish "doesn't exist" from "belongs to someone else" from
        "wrong context" from "not authorized to view").

        `actor` (a `UserContext`) is optional for backward compatibility
        with internal/system callers that have no end-user principal; when
        `None`, step 5 is skipped (there is no principal to check) but
        steps 1-4 (existence, context, tenant, customer) still apply.
        """
        if not media_urls or not isinstance(media_urls, dict):
            return
        media_ids = media_urls.get("media_ids")
        if not media_ids:
            return
        from app.engines.media.models import MediaAsset
        from app.engines.media.asset_service import MediaAssetRecord
        from app.engines.media.access import MediaAccessService
        from app.exceptions import ServiceOSException

        access = MediaAccessService()
        validated_assets = []
        for mid in media_ids:
            try:
                asset_id = uuid.UUID(str(mid))
            except (ValueError, TypeError, AttributeError):
                raise ValueError(ERR_CHAT_ATTACHMENT_NOT_FOUND)
            # Slice 2F-18D: SELECT ... FOR UPDATE, not db.get(), so the row
            # is locked for the rest of THIS transaction. A concurrent
            # request attaching the SAME asset to a different thread blocks
            # here until this transaction commits or rolls back, then
            # re-reads the now-current claim and correctly loses the race
            # (see atomic-claiming.md) — no migration, no new mechanism,
            # just the existing Postgres row-lock the async driver already
            # supports.
            r = await db.execute(
                select(MediaAsset).where(MediaAsset.id == asset_id).with_for_update()
            )
            asset = r.scalar_one_or_none()
            if asset is None:
                raise ValueError(ERR_CHAT_ATTACHMENT_NOT_FOUND)
            if getattr(asset, "deleted_at", None) is not None:
                raise ValueError(ERR_CHAT_ATTACHMENT_NOT_FOUND)
            if getattr(asset, "status", "active") != "active":
                raise ValueError(ERR_CHAT_ATTACHMENT_NOT_FOUND)
            if getattr(asset, "media_context", None) != "chat_attachment":
                raise ValueError(ERR_CHAT_ATTACHMENT_NOT_FOUND)
            if (
                thread.tenant_id is not None
                and getattr(asset, "tenant_id", None) is not None
                and str(asset.tenant_id) != str(thread.tenant_id)
            ):
                raise ValueError(ERR_CHAT_ATTACHMENT_NOT_FOUND)
            if (
                thread.customer_id is not None
                and getattr(asset, "customer_id", None) is not None
                and str(asset.customer_id) != str(thread.customer_id)
            ):
                raise ValueError(ERR_CHAT_ATTACHMENT_NOT_FOUND)
            if actor is not None:
                try:
                    access.assert_can_view(actor, MediaAssetRecord.from_orm(asset))
                except ServiceOSException:
                    raise ValueError(ERR_CHAT_ATTACHMENT_NOT_FOUND)

            # Slice 2F-18D: parse the existing claim defensively — a
            # malformed metadata_json shape (not a dict, or a
            # chat_thread_id value that isn't a real UUID) must fail
            # closed, never be treated as "unclaimed" (which would allow
            # a stale/corrupt claim to be silently overwritten).
            meta = asset.metadata_json
            if not isinstance(meta, dict):
                raise ValueError(ERR_CHAT_ATTACHMENT_NOT_FOUND)
            raw_claim = meta.get("chat_thread_id")
            claimed_thread_id: uuid.UUID | None = None
            if raw_claim is not None:
                try:
                    claimed_thread_id = uuid.UUID(str(raw_claim))
                except (ValueError, TypeError, AttributeError):
                    raise ValueError(ERR_CHAT_ATTACHMENT_NOT_FOUND)

            if claimed_thread_id is not None:
                # Slice 2F-18C: same-customer cross-Job/cross-conversation
                # reuse guard — already claimed by a DIFFERENT thread.
                if claimed_thread_id != thread.id:
                    raise ValueError(ERR_CHAT_ATTACHMENT_NOT_FOUND)
            else:
                # Slice 2F-18D: safe first-use destination authority.
                # `assert_can_view` above proves the sender may VIEW the
                # asset — necessary, not sufficient, for CHOOSING which
                # conversation to first-claim it into. A technician's
                # authority is Job-assignment-scoped, not tenant-oversight-
                # scoped (unlike tenant_owner/staff, whose tenant-wide
                # customer oversight is the ratified, existing, unmodified
                # office policy) — so a technician's OWN upload is the only
                # evidence this codebase has that they legitimately chose
                # this destination. Everyone else reaching this point
                # (customer, tenant_owner, staff) already had their
                # authority proven above (customer_id match / tenant match
                # + assert_can_view); "first thread supplied by the caller"
                # is never, by itself, treated as proof of context for
                # anyone.
                if actor is not None and actor.role == "technician":
                    if str(getattr(asset, "uploaded_by_user_id", None)) != str(actor.user_id):
                        raise ValueError(ERR_CHAT_ATTACHMENT_NOT_FOUND)
                # Slice 2F-18E: office (tenant_owner/staff) first-use
                # destination authority. Tenant equality and customer
                # equality alone are not sufficient evidence for a
                # Job-linked customer/technician conversation — the SAME
                # customer can have multiple concurrent threads (multiple
                # ServiceJobs), and MediaAsset has no Job/thread column to
                # disambiguate which one an asset was "for." A thread with
                # no customer party at all (`thread.customer_id is None`
                # — a provider-internal conversation) carries no external
                # audience, so office sharing there needs no further
                # proof. A thread WITH a customer party is only a safe
                # office first-use destination when the office actor is
                # themselves the asset's uploader — the only evidence
                # available, absent a schema change, that THIS office
                # user chose THIS specific asset for THIS specific
                # conversation rather than any of the customer's other
                # threads.
                if (
                    actor is not None
                    and actor.role in ("tenant_owner", "staff")
                    and thread.customer_id is not None
                    and str(getattr(asset, "uploaded_by_user_id", None)) != str(actor.user_id)
                ):
                    raise ValueError(ERR_CHAT_ATTACHMENT_NOT_FOUND)

            validated_assets.append(asset)

        for asset in validated_assets:
            meta = asset.metadata_json if isinstance(asset.metadata_json, dict) else {}
            if meta.get("chat_thread_id") is None:
                new_meta = dict(meta)
                new_meta["chat_thread_id"] = str(thread.id)
                asset.metadata_json = new_meta

    async def _notify_other_participants(
        self, db: AsyncSession, thread: ChatThread, sender_user_id: uuid.UUID,
        sender_type: str, message_text: str | None,
    ) -> None:
        """Raise an in-app notification for every active participant except the
        sender, so a new message actually reaches the other side.

        The chat engine's docstring promised this but never did it — a customer's
        message never alerted the provider (or vice versa), so the recipient only
        saw it if they happened to open the thread. Each notification deep-links to
        the recipient's own chat surface.
        """
        rows = (await db.execute(
            select(ChatThreadParticipant).where(
                ChatThreadParticipant.thread_id == thread.id,
                ChatThreadParticipant.left_at == None,  # noqa: E711
            )
        )).scalars().all()
        preview = (message_text or "Sent an attachment").strip()
        if len(preview) > 140:
            preview = preview[:137] + "…"
        sender_label = {"customer": "customer", "provider": "provider",
                        "staff": "technician", "admin": "support"}.get(sender_type, sender_type)
        for p in rows:
            if str(p.user_id) == str(sender_user_id):
                continue
            if p.participant_type == "customer":
                url = f"/customer/chat/{thread.id}"
            elif p.participant_type == "staff":
                url = f"/staff/chat/{thread.id}"
            else:
                url = f"/provider/chat/{thread.id}"
            db.add(InAppNotification(
                user_id=p.user_id,
                tenant_id=thread.tenant_id,
                notification_type="chat.message",
                title=f"New message from {sender_label}",
                body=preview,
                action_url=url,
                action_label="Open chat",
                source_record_type="chat_thread",
                source_record_id=thread.id,
                severity="info",
            ))

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
