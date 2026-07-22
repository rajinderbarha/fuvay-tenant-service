"""Slice 2F-18D — First-Use Chat-Media Authority, Atomic Claiming, Metadata
Integrity and URL Revocation Closure.

Covers:
- Unclaimed-asset first-use destination authority (technician must be the
  uploader; office/customer unaffected).
- Atomic claiming via SELECT ... FOR UPDATE.
- Claim metadata tampering resistance (upload strips a forged claim key;
  replace_asset requires thread authority for claimed assets).
- Malformed/conflicting claim fail-closed behavior.
- No-partial-persistence proof for the new rejected paths.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


def _db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    db.get = AsyncMock(return_value=None)
    return db


def _asset_result(asset):
    r = MagicMock()
    r.scalar_one_or_none = MagicMock(return_value=asset)
    return r


def _thread_mocks():
    thread_r = MagicMock()
    part_r = MagicMock()
    part_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
    participants_r = MagicMock()
    participants_r.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    return thread_r, part_r, participants_r


def _user(role, user_id=None, tenant_id=None):
    from app.dependencies.auth import UserContext
    return UserContext(
        user_id=str(user_id or uuid.uuid4()), email="x@example.com", role=role,
        tenant_id=tenant_id, full_name="X", is_verified=True,
    )


def _active_asset(**overrides):
    defaults = dict(
        tenant_id=uuid.uuid4(), customer_id=None, uploaded_by_user_id=uuid.uuid4(),
        owner_type="user", owner_id=uuid.uuid4(), media_context="chat_attachment",
        storage_driver="local", storage_key="k", public_url=None, is_public=False,
        access_level="tenant", status="active", deleted_at=None, metadata_json={},
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Unclaimed-asset first-use destination authority
# ══════════════════════════════════════════════════════════════════════════════

class TestUnclaimedAssetFirstUse:
    @pytest.mark.asyncio
    async def test_technician_cannot_first_claim_unowned_asset(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_ATTACHMENT_NOT_FOUND

        svc = ChatMessageService()
        db = _db()
        shared_tenant = uuid.uuid4()
        technician = _user("technician", tenant_id=str(shared_tenant))
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=shared_tenant)
        thread.id = uuid.uuid4()
        thread_r, part_r, _ = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        job = MagicMock(assigned_staff_id=uuid.UUID(technician.user_id))
        db.get = AsyncMock(return_value=job)
        unowned = _active_asset(tenant_id=shared_tenant, metadata_json={})  # random uploader
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(unowned)])

        with pytest.raises(ValueError, match=ERR_CHAT_ATTACHMENT_NOT_FOUND):
            await svc.send_message(
                db=db, thread_id=thread.id, actor_user_id=uuid.UUID(technician.user_id),
                actor_type="technician", tenant_id=shared_tenant,
                message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
                actor=technician,
            )
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_technician_can_first_claim_own_upload(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread

        svc = ChatMessageService()
        db = _db()
        shared_tenant = uuid.uuid4()
        technician = _user("technician", tenant_id=str(shared_tenant))
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=shared_tenant)
        thread.id = uuid.uuid4()
        thread_r, part_r, participants_r = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        job = MagicMock(assigned_staff_id=uuid.UUID(technician.user_id))
        db.get = AsyncMock(return_value=job)
        own_upload = _active_asset(tenant_id=shared_tenant, metadata_json={},
                                    uploaded_by_user_id=uuid.UUID(technician.user_id))
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(own_upload), participants_r])

        msg = await svc.send_message(
            db=db, thread_id=thread.id, actor_user_id=uuid.UUID(technician.user_id),
            actor_type="technician", tenant_id=shared_tenant,
            message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
            actor=technician,
        )
        assert msg is not None
        assert own_upload.metadata_json.get("chat_thread_id") == str(thread.id)

    @pytest.mark.asyncio
    async def test_office_staff_first_claim_unaffected_by_technician_rule(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread

        svc = ChatMessageService()
        db = _db()
        shared_tenant = uuid.uuid4()
        staff = _user("staff", tenant_id=str(shared_tenant))
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=shared_tenant)
        thread.id = uuid.uuid4()
        thread_r, part_r, participants_r = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        someone_elses_upload = _active_asset(tenant_id=shared_tenant, metadata_json={})
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(someone_elses_upload), participants_r])

        msg = await svc.send_message(
            db=db, thread_id=thread.id, actor_user_id=uuid.UUID(staff.user_id),
            actor_type="provider", tenant_id=shared_tenant,
            message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
            actor=staff,
        )
        assert msg is not None

    @pytest.mark.asyncio
    async def test_customer_first_claim_own_upload_allowed(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread

        svc = ChatMessageService()
        db = _db()
        customer = _user("customer")
        thread = ChatThread(record_type="service_booking", record_id=uuid.uuid4(),
                             status="open", customer_id=uuid.UUID(customer.user_id))
        thread.id = uuid.uuid4()
        thread_r, part_r, participants_r = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        own_upload = _active_asset(customer_id=uuid.UUID(customer.user_id), metadata_json={})
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(own_upload), participants_r])

        msg = await svc.send_message(
            db=db, thread_id=thread.id, actor_user_id=uuid.UUID(customer.user_id),
            actor_type="customer", tenant_id=None,
            message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
            actor=customer,
        )
        assert msg is not None


# ══════════════════════════════════════════════════════════════════════════════
# 2. Atomic claiming
# ══════════════════════════════════════════════════════════════════════════════

class TestAtomicClaiming:
    @pytest.mark.asyncio
    async def test_asset_lookup_uses_select_for_update(self):
        # Proves the asset row is locked (SELECT ... FOR UPDATE), not
        # fetched via db.get() (no lock) -- the mechanism that makes
        # concurrent claim races resolve correctly (see atomic-claiming.md).
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread

        svc = ChatMessageService()
        db = _db()
        shared_tenant = uuid.uuid4()
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=shared_tenant)
        thread.id = uuid.uuid4()
        thread_r, part_r, participants_r = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        asset = _active_asset(tenant_id=shared_tenant, metadata_json={})

        captured_queries = []

        async def _capture_execute(query, *a, **kw):
            captured_queries.append(query)
            if len(captured_queries) == 1:
                return thread_r
            if len(captured_queries) == 2:
                return part_r
            if len(captured_queries) == 3:
                return _asset_result(asset)
            return participants_r

        db.execute = _capture_execute

        await svc.send_message(
            db=db, thread_id=thread.id, actor_user_id=uuid.uuid4(),
            actor_type="provider", tenant_id=shared_tenant,
            message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
        )
        asset_query = captured_queries[2]
        compiled = str(asset_query.compile(compile_kwargs={"literal_binds": False}))
        assert "FOR UPDATE" in compiled.upper()


# ══════════════════════════════════════════════════════════════════════════════
# 3. Claim metadata tampering resistance
# ══════════════════════════════════════════════════════════════════════════════

class TestClaimTamperingResistance:
    def test_upload_strips_client_supplied_claim_key(self):
        from app.engines.media.asset_service import MediaAssetService

        stripped = MediaAssetService._strip_claim_key(
            {"chat_thread_id": str(uuid.uuid4()), "other_field": "kept"}
        )
        assert "chat_thread_id" not in stripped
        assert stripped["other_field"] == "kept"

    def test_strip_claim_key_handles_none(self):
        from app.engines.media.asset_service import MediaAssetService
        assert MediaAssetService._strip_claim_key(None) == {}

    @pytest.mark.asyncio
    async def test_replace_asset_requires_thread_authority_for_claimed_chat_asset(self):
        # A same-tenant staff member authorized to "replace" media in
        # general (per assert_can_replace's tenant-wide rule) must NOT be
        # able to swap a claimed chat_attachment's file content without
        # ALSO passing thread authority for the specific conversation it's
        # claimed by.
        from app.engines.media.asset_service import MediaAssetService
        from app.exceptions import NotFoundException
        from app.engines.platform_notifications.models import ChatThread

        db = _db()
        staff = _user("staff", tenant_id=str(uuid.uuid4()))
        media_id = uuid.uuid4()
        claimed_thread_id = uuid.uuid4()
        old_asset = MagicMock(
            id=media_id, tenant_id=uuid.UUID(staff.tenant_id), customer_id=None,
            uploaded_by_user_id=uuid.uuid4(), owner_type="user", owner_id=uuid.uuid4(),
            media_context="chat_attachment", storage_driver="local", storage_key="k",
            public_url=None, is_public=False, access_level="tenant", status="active",
            metadata_json={"chat_thread_id": str(claimed_thread_id)},
        )
        load_r = MagicMock()
        load_r.scalar_one_or_none = MagicMock(return_value=old_asset)

        foreign_thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                                     status="open", tenant_id=uuid.uuid4())  # different tenant
        foreign_thread.id = claimed_thread_id

        db.execute = AsyncMock(return_value=load_r)
        db.get = AsyncMock(return_value=foreign_thread)

        svc = MediaAssetService(db=db, actor=staff)
        fake_file = MagicMock()

        with pytest.raises(NotFoundException):
            await svc.replace_asset(media_id=media_id, file=fake_file)


# ══════════════════════════════════════════════════════════════════════════════
# 4. Malformed/conflicting claim fail-closed
# ══════════════════════════════════════════════════════════════════════════════

class TestMalformedClaimFailsClosed:
    @pytest.mark.asyncio
    async def test_non_dict_metadata_json_fails_closed(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_ATTACHMENT_NOT_FOUND

        svc = ChatMessageService()
        db = _db()
        shared_tenant = uuid.uuid4()
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=shared_tenant)
        thread.id = uuid.uuid4()
        thread_r, part_r, _ = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        corrupt_asset = _active_asset(tenant_id=shared_tenant, metadata_json="not-a-dict")
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(corrupt_asset)])

        with pytest.raises(ValueError, match=ERR_CHAT_ATTACHMENT_NOT_FOUND):
            await svc.send_message(
                db=db, thread_id=thread.id, actor_user_id=uuid.uuid4(),
                actor_type="provider", tenant_id=shared_tenant,
                message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
            )
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_malformed_claim_value_fails_closed(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_ATTACHMENT_NOT_FOUND

        svc = ChatMessageService()
        db = _db()
        shared_tenant = uuid.uuid4()
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=shared_tenant)
        thread.id = uuid.uuid4()
        thread_r, part_r, _ = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        garbled_asset = _active_asset(tenant_id=shared_tenant,
                                       metadata_json={"chat_thread_id": "not-a-uuid"})
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(garbled_asset)])

        with pytest.raises(ValueError, match=ERR_CHAT_ATTACHMENT_NOT_FOUND):
            await svc.send_message(
                db=db, thread_id=thread.id, actor_user_id=uuid.uuid4(),
                actor_type="provider", tenant_id=shared_tenant,
                message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
            )
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_asset_service_malformed_claim_denied_not_crashed(self):
        from app.engines.media.asset_service import MediaAssetService
        from app.exceptions import ServiceOSException

        db = _db()
        actor = _user("staff", tenant_id=str(uuid.uuid4()))
        asset = MagicMock(metadata_json={"chat_thread_id": ["not", "a", "uuid"]})
        svc = MediaAssetService(db=db, actor=actor)

        with pytest.raises(ServiceOSException) as exc_info:
            await svc._assert_chat_thread_authority(asset)
        assert exc_info.value.error_code == "MEDIA_ACCESS_DENIED"


# ══════════════════════════════════════════════════════════════════════════════
# 5. No partial persistence
# ══════════════════════════════════════════════════════════════════════════════

class TestNoPartialPersistence:
    @pytest.mark.asyncio
    async def test_technician_first_use_rejection_persists_nothing(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_ATTACHMENT_NOT_FOUND

        svc = ChatMessageService()
        db = _db()
        shared_tenant = uuid.uuid4()
        technician = _user("technician", tenant_id=str(shared_tenant))
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=shared_tenant)
        thread.id = uuid.uuid4()
        thread_r, part_r, _ = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        job = MagicMock(assigned_staff_id=uuid.UUID(technician.user_id))
        db.get = AsyncMock(return_value=job)
        unowned = _active_asset(tenant_id=shared_tenant, metadata_json={})
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(unowned)])

        with pytest.raises(ValueError, match=ERR_CHAT_ATTACHMENT_NOT_FOUND):
            await svc.send_message(
                db=db, thread_id=thread.id, actor_user_id=uuid.UUID(technician.user_id),
                actor_type="technician", tenant_id=shared_tenant,
                message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
                actor=technician,
            )
        db.add.assert_not_called()
        db.commit.assert_not_called()
        assert unowned.metadata_json.get("chat_thread_id") is None
