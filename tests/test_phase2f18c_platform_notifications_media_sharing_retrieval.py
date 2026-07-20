"""Slice 2F-18C — Chat Media Sharing, Recipient Authorization, Retrieval and
Revocation Closure.

Covers:
- Same-customer cross-Job/cross-conversation media reuse rejection (via the
  metadata_json first-use thread claim).
- Retrieval-time thread authority for chat_attachment assets
  (MediaAssetService._assert_chat_thread_authority).
- Missing-vs-unauthorized privacy equivalence at the retrieval routes.
- staff_send_message no longer silently drops media_ids.
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
# 1. Same-customer cross-Job/cross-conversation reuse (thread-claim lock)
# ══════════════════════════════════════════════════════════════════════════════

class TestThreadClaimLock:
    @pytest.mark.asyncio
    async def test_first_use_claims_asset_for_its_thread(self):
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
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(asset), participants_r])

        await svc.send_message(
            db=db, thread_id=thread.id, actor_user_id=uuid.uuid4(),
            actor_type="provider", tenant_id=shared_tenant,
            message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
        )
        assert asset.metadata_json.get("chat_thread_id") == str(thread.id)

    @pytest.mark.asyncio
    async def test_reuse_within_same_thread_allowed(self):
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
        # Already claimed by THIS SAME thread (e.g. a second message reusing
        # the same photo within one conversation).
        asset = _active_asset(tenant_id=shared_tenant, metadata_json={"chat_thread_id": str(thread.id)})
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(asset), participants_r])

        msg = await svc.send_message(
            db=db, thread_id=thread.id, actor_user_id=uuid.uuid4(),
            actor_type="provider", tenant_id=shared_tenant,
            message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
        )
        assert msg is not None

    @pytest.mark.asyncio
    async def test_cross_job_reuse_within_same_customer_rejected(self):
        # ServiceJob A1's photo, already claimed by Thread A1, is attempted
        # to be reused in Thread A2 -- SAME customer, SAME tenant, but a
        # DIFFERENT conversation/Job. This is exactly the gap 2F-18B could
        # not close (no job_id column) -- the thread-claim lock closes it.
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_ATTACHMENT_NOT_FOUND

        svc = ChatMessageService()
        db = _db()
        shared_tenant = uuid.uuid4()
        shared_customer = uuid.uuid4()
        thread_a1_id = uuid.uuid4()
        thread_a2 = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                                status="open", tenant_id=shared_tenant, customer_id=shared_customer)
        thread_a2.id = uuid.uuid4()
        thread_r, part_r, _ = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread_a2)))
        media_a1 = _active_asset(tenant_id=shared_tenant, customer_id=shared_customer,
                                  metadata_json={"chat_thread_id": str(thread_a1_id)})
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(media_a1)])

        with pytest.raises(ValueError, match=ERR_CHAT_ATTACHMENT_NOT_FOUND):
            await svc.send_message(
                db=db, thread_id=thread_a2.id, actor_user_id=uuid.uuid4(),
                actor_type="provider", tenant_id=shared_tenant,
                message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
            )
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_partial_batch_failure_does_not_claim_earlier_asset(self):
        # Two media_ids in one message: the first is valid/unclaimed, the
        # second fails validation -- the first must NOT end up claimed
        # in-memory since the whole message is rejected.
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
        good_asset = _active_asset(tenant_id=shared_tenant, metadata_json={})
        bad_asset = _active_asset(tenant_id=uuid.uuid4())  # cross-tenant -> rejected
        db.execute = AsyncMock(side_effect=[
            thread_r, part_r, _asset_result(good_asset), _asset_result(bad_asset),
        ])

        with pytest.raises(ValueError, match=ERR_CHAT_ATTACHMENT_NOT_FOUND):
            await svc.send_message(
                db=db, thread_id=thread.id, actor_user_id=uuid.uuid4(),
                actor_type="provider", tenant_id=shared_tenant,
                message_text=None,
                media_urls={"media_ids": [str(uuid.uuid4()), str(uuid.uuid4())]},
            )
        assert good_asset.metadata_json.get("chat_thread_id") is None
        db.add.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════════
# 2. Retrieval-time thread authority
# ══════════════════════════════════════════════════════════════════════════════

class TestRetrievalTimeThreadAuthority:
    @pytest.mark.asyncio
    async def test_unassigned_technician_denied_retrieval_of_job_thread_media(self):
        from app.engines.media.asset_service import MediaAssetService
        from app.engines.platform_notifications.models import ChatThread
        from app.exceptions import ServiceOSException

        db = _db()
        technician = _user("technician", tenant_id=str(uuid.uuid4()))
        thread_id = uuid.uuid4()
        asset = MagicMock(
            id=uuid.uuid4(), tenant_id=uuid.UUID(technician.tenant_id), customer_id=None,
            uploaded_by_user_id=uuid.uuid4(), owner_type="user", owner_id=uuid.uuid4(),
            media_context="chat_attachment", storage_driver="local", storage_key="k",
            public_url=None, is_public=False, access_level="tenant", status="active",
            metadata_json={"chat_thread_id": str(thread_id)},
        )
        svc = MediaAssetService(db=db, actor=technician)

        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=uuid.UUID(technician.tenant_id))
        thread.id = thread_id
        job = MagicMock(assigned_staff_id=uuid.uuid4())  # not this technician
        db.get = AsyncMock(side_effect=[thread, job])

        with pytest.raises(ServiceOSException) as exc_info:
            await svc._assert_chat_thread_authority(asset)
        assert exc_info.value.error_code == "MEDIA_ACCESS_DENIED"

    @pytest.mark.asyncio
    async def test_assigned_technician_allowed_retrieval(self):
        from app.engines.media.asset_service import MediaAssetService
        from app.engines.platform_notifications.models import ChatThread

        db = _db()
        technician = _user("technician", tenant_id=str(uuid.uuid4()))
        thread_id = uuid.uuid4()
        asset = MagicMock(metadata_json={"chat_thread_id": str(thread_id)})
        svc = MediaAssetService(db=db, actor=technician)

        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=uuid.UUID(technician.tenant_id))
        thread.id = thread_id
        job = MagicMock(assigned_staff_id=uuid.UUID(technician.user_id))
        db.get = AsyncMock(side_effect=[thread, job])

        await svc._assert_chat_thread_authority(asset)  # no exception == allowed

    @pytest.mark.asyncio
    async def test_unclaimed_asset_skips_thread_check_for_office_persona(self):
        # Slice 2F-18D narrows the UNCLAIMED case for technician specifically
        # (see TestUnclaimedAssetFirstUse below) -- office personas
        # (tenant_owner/staff) still skip the thread check entirely for an
        # unclaimed asset, per the ratified, unmodified tenant-wide office
        # policy (assert_can_view already ran and authorized this call).
        from app.engines.media.asset_service import MediaAssetService

        db = _db()
        actor = _user("staff", tenant_id=str(uuid.uuid4()))
        asset = MagicMock(metadata_json={})
        svc = MediaAssetService(db=db, actor=actor)

        await svc._assert_chat_thread_authority(asset)
        db.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_super_admin_bypasses_thread_check(self):
        from app.engines.media.asset_service import MediaAssetService

        db = _db()
        actor = _user("super_admin")
        asset = MagicMock(metadata_json={"chat_thread_id": str(uuid.uuid4())})
        svc = MediaAssetService(db=db, actor=actor)

        await svc._assert_chat_thread_authority(asset)
        db.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_asset_unifies_missing_and_denied_to_not_found(self):
        from app.engines.media.asset_service import MediaAssetService
        from app.exceptions import NotFoundException

        db = _db()
        actor = _user("customer")
        asset = MagicMock(
            id=uuid.uuid4(), media_context="chat_attachment", customer_id=uuid.uuid4(),
            tenant_id=None, uploaded_by_user_id=uuid.uuid4(), owner_type="user",
            owner_id=uuid.uuid4(), storage_driver="local", storage_key="k",
            public_url=None, is_public=False, access_level="tenant", status="active",
            metadata_json={},
        )
        r = MagicMock()
        r.scalar_one_or_none = MagicMock(return_value=asset)
        db.execute = AsyncMock(return_value=r)
        svc = MediaAssetService(db=db, actor=actor)

        with pytest.raises(NotFoundException):
            await svc.get_asset(asset.id)


# ══════════════════════════════════════════════════════════════════════════════
# 3. Dropped media_ids fix
# ══════════════════════════════════════════════════════════════════════════════

class TestStaffSendMessageForwardsMedia:
    def test_staff_send_message_forwards_media_ids(self):
        import inspect
        from app.engines.platform_notifications import provider_router
        src = inspect.getsource(provider_router.staff_send_message)
        assert "media_urls" in src and "body.media_ids" in src


# ══════════════════════════════════════════════════════════════════════════════
# 4. No partial persistence for new rejected paths
# ══════════════════════════════════════════════════════════════════════════════

class TestNoPartialPersistence:
    @pytest.mark.asyncio
    async def test_cross_job_reuse_rejection_persists_nothing(self):
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
        other_thread_id = uuid.uuid4()
        asset = _active_asset(tenant_id=shared_tenant,
                               metadata_json={"chat_thread_id": str(other_thread_id)})
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(asset)])

        with pytest.raises(ValueError, match=ERR_CHAT_ATTACHMENT_NOT_FOUND):
            await svc.send_message(
                db=db, thread_id=thread.id, actor_user_id=uuid.uuid4(),
                actor_type="provider", tenant_id=shared_tenant,
                message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
            )
        db.add.assert_not_called()
        db.commit.assert_not_called()
