"""Slice 2F-18E — Office First-Use Sharing, Asset Replacement, Transaction
Atomicity, Retrieval Lifecycle and Final Coverage Closure.

Covers:
- Office (tenant_owner/staff) first-use ambiguous-sharing rejection into a
  customer-linked thread when the office actor is not the uploader.
- Office first-use allowed into provider-internal threads (no customer
  party) and when the office actor IS the uploader.
- replace_asset authorization distinguishing view from replace.
- Retrieval lifecycle enforcement (deleted/inactive chat_attachment assets).
- Transaction-boundary/no-intermediate-commit proof.
- No-partial-state proof for the new rejected paths.
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


def _user(role, user_id=None, tenant_id=None, access_scope=None):
    from app.dependencies.auth import UserContext
    return UserContext(
        user_id=str(user_id or uuid.uuid4()), email="x@example.com", role=role,
        tenant_id=tenant_id, full_name="X", is_verified=True, access_scope=access_scope,
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
# 1. Office first-use ambiguity
# ══════════════════════════════════════════════════════════════════════════════

class TestOfficeFirstUseAmbiguity:
    @pytest.mark.asyncio
    async def test_staff_cannot_first_claim_unowned_asset_into_customer_thread(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_ATTACHMENT_NOT_FOUND

        svc = ChatMessageService()
        db = _db()
        shared_tenant = uuid.uuid4()
        customer_id = uuid.uuid4()
        staff = _user("staff", tenant_id=str(shared_tenant))
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=shared_tenant, customer_id=customer_id)
        thread.id = uuid.uuid4()
        thread_r, part_r, _ = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        unowned = _active_asset(tenant_id=shared_tenant, customer_id=customer_id, metadata_json={})
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(unowned)])

        with pytest.raises(ValueError, match=ERR_CHAT_ATTACHMENT_NOT_FOUND):
            await svc.send_message(
                db=db, thread_id=thread.id, actor_user_id=uuid.UUID(staff.user_id),
                actor_type="provider", tenant_id=shared_tenant,
                message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
                actor=staff,
            )
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_staff_can_first_claim_own_upload_into_customer_thread(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread

        svc = ChatMessageService()
        db = _db()
        shared_tenant = uuid.uuid4()
        customer_id = uuid.uuid4()
        staff = _user("staff", tenant_id=str(shared_tenant))
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=shared_tenant, customer_id=customer_id)
        thread.id = uuid.uuid4()
        thread_r, part_r, participants_r = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        own_upload = _active_asset(tenant_id=shared_tenant, customer_id=customer_id,
                                    metadata_json={}, uploaded_by_user_id=uuid.UUID(staff.user_id))
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(own_upload), participants_r])

        msg = await svc.send_message(
            db=db, thread_id=thread.id, actor_user_id=uuid.UUID(staff.user_id),
            actor_type="provider", tenant_id=shared_tenant,
            message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
            actor=staff,
        )
        assert msg is not None
        assert own_upload.metadata_json.get("chat_thread_id") == str(thread.id)

    @pytest.mark.asyncio
    async def test_staff_can_first_claim_into_provider_internal_thread(self):
        # No customer party at all -- no external audience risk, so office
        # sharing needs no uploader-match evidence.
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread

        svc = ChatMessageService()
        db = _db()
        shared_tenant = uuid.uuid4()
        staff = _user("staff", tenant_id=str(shared_tenant))
        thread = ChatThread(record_type="admin_internal", record_id=uuid.uuid4(),
                             status="open", tenant_id=shared_tenant, customer_id=None)
        thread.id = uuid.uuid4()
        found = MagicMock()
        found.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=MagicMock())))
        thread_r, part_r, participants_r = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        unowned = _active_asset(tenant_id=shared_tenant, customer_id=None, metadata_json={})
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(unowned), participants_r])

        msg = await svc.send_message(
            db=db, thread_id=thread.id, actor_user_id=uuid.UUID(staff.user_id),
            actor_type="provider", tenant_id=shared_tenant,
            message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
            actor=staff,
        )
        assert msg is not None

    @pytest.mark.asyncio
    async def test_tenant_owner_same_ambiguity_rule_as_staff(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_ATTACHMENT_NOT_FOUND

        svc = ChatMessageService()
        db = _db()
        shared_tenant = uuid.uuid4()
        customer_id = uuid.uuid4()
        owner = _user("tenant_owner", tenant_id=str(shared_tenant))
        thread = ChatThread(record_type="service_booking", record_id=uuid.uuid4(),
                             status="open", tenant_id=shared_tenant, customer_id=customer_id)
        thread.id = uuid.uuid4()
        thread_r, part_r, _ = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        unowned = _active_asset(tenant_id=shared_tenant, customer_id=customer_id, metadata_json={})
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(unowned)])

        with pytest.raises(ValueError, match=ERR_CHAT_ATTACHMENT_NOT_FOUND):
            await svc.send_message(
                db=db, thread_id=thread.id, actor_user_id=uuid.UUID(owner.user_id),
                actor_type="provider", tenant_id=shared_tenant,
                message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
                actor=owner,
            )
        db.add.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════════
# 2. replace_asset authorization (view != replace)
# ══════════════════════════════════════════════════════════════════════════════

class TestReplaceAssetAuthorization:
    @pytest.mark.asyncio
    async def test_uploader_can_replace_own_asset(self):
        from app.engines.media.asset_service import MediaAssetService

        db = _db()
        uploader = _user("customer")
        asset = _active_asset(uploaded_by_user_id=uuid.UUID(uploader.user_id), metadata_json={})
        svc = MediaAssetService(db=db, actor=uploader)

        await svc._assert_chat_attachment_replace_authority(asset)  # no exception

    @pytest.mark.asyncio
    async def test_staff_with_mutation_scope_can_replace_tenant_asset(self):
        from app.engines.media.asset_service import MediaAssetService

        db = _db()
        tenant_id = uuid.uuid4()
        staff = _user("staff", tenant_id=str(tenant_id))
        asset = _active_asset(tenant_id=tenant_id, uploaded_by_user_id=uuid.uuid4(), metadata_json={})
        svc = MediaAssetService(db=db, actor=staff)

        await svc._assert_chat_attachment_replace_authority(asset)  # no exception

    @pytest.mark.asyncio
    async def test_readonly_staff_denied_replace(self):
        from app.engines.media.asset_service import MediaAssetService
        from app.exceptions import ServiceOSException

        db = _db()
        tenant_id = uuid.uuid4()
        staff = _user("staff", tenant_id=str(tenant_id), access_scope="customer_support_limited")
        asset = _active_asset(tenant_id=tenant_id, uploaded_by_user_id=uuid.uuid4(), metadata_json={})
        svc = MediaAssetService(db=db, actor=staff)

        with pytest.raises(ServiceOSException):
            await svc._assert_chat_attachment_replace_authority(asset)

    @pytest.mark.asyncio
    async def test_customer_cannot_replace_provider_asset(self):
        from app.engines.media.asset_service import MediaAssetService
        from app.exceptions import ServiceOSException

        db = _db()
        customer = _user("customer")
        asset = _active_asset(uploaded_by_user_id=uuid.uuid4(), metadata_json={})  # different uploader
        svc = MediaAssetService(db=db, actor=customer)

        with pytest.raises(ServiceOSException):
            await svc._assert_chat_attachment_replace_authority(asset)

    @pytest.mark.asyncio
    async def test_technician_cannot_replace_unowned_asset(self):
        from app.engines.media.asset_service import MediaAssetService
        from app.exceptions import ServiceOSException

        db = _db()
        tenant_id = uuid.uuid4()
        technician = _user("technician", tenant_id=str(tenant_id))
        asset = _active_asset(tenant_id=tenant_id, uploaded_by_user_id=uuid.uuid4(), metadata_json={})
        svc = MediaAssetService(db=db, actor=technician)

        with pytest.raises(ServiceOSException):
            await svc._assert_chat_attachment_replace_authority(asset)

    @pytest.mark.asyncio
    async def test_foreign_tenant_staff_denied_replace(self):
        from app.engines.media.asset_service import MediaAssetService
        from app.exceptions import ServiceOSException

        db = _db()
        staff = _user("staff", tenant_id=str(uuid.uuid4()))
        asset = _active_asset(tenant_id=uuid.uuid4(), uploaded_by_user_id=uuid.uuid4(), metadata_json={})
        svc = MediaAssetService(db=db, actor=staff)

        with pytest.raises(ServiceOSException):
            await svc._assert_chat_attachment_replace_authority(asset)

    @pytest.mark.asyncio
    async def test_super_admin_can_replace_any_asset(self):
        from app.engines.media.asset_service import MediaAssetService

        db = _db()
        admin = _user("super_admin")
        asset = _active_asset(uploaded_by_user_id=uuid.uuid4(), metadata_json={})
        svc = MediaAssetService(db=db, actor=admin)

        await svc._assert_chat_attachment_replace_authority(asset)  # no exception


# ══════════════════════════════════════════════════════════════════════════════
# 3. Retrieval lifecycle enforcement
# ══════════════════════════════════════════════════════════════════════════════

class TestRetrievalLifecycle:
    def test_deleted_chat_attachment_rejected(self):
        from app.engines.media.asset_service import MediaAssetService
        from app.exceptions import NotFoundException
        from datetime import datetime, timezone

        db = _db()
        actor = _user("staff", tenant_id=str(uuid.uuid4()))
        asset = _active_asset(deleted_at=datetime.now(timezone.utc))
        svc = MediaAssetService(db=db, actor=actor)

        with pytest.raises(NotFoundException):
            svc._assert_chat_attachment_lifecycle(asset, uuid.uuid4())

    def test_quarantined_chat_attachment_rejected(self):
        from app.engines.media.asset_service import MediaAssetService
        from app.exceptions import NotFoundException

        db = _db()
        actor = _user("staff", tenant_id=str(uuid.uuid4()))
        asset = _active_asset(status="quarantined")
        svc = MediaAssetService(db=db, actor=actor)

        with pytest.raises(NotFoundException):
            svc._assert_chat_attachment_lifecycle(asset, uuid.uuid4())

    def test_active_chat_attachment_passes_lifecycle_check(self):
        from app.engines.media.asset_service import MediaAssetService

        db = _db()
        actor = _user("staff", tenant_id=str(uuid.uuid4()))
        asset = _active_asset()
        svc = MediaAssetService(db=db, actor=actor)

        svc._assert_chat_attachment_lifecycle(asset, uuid.uuid4())  # no exception

    def test_non_chat_attachment_context_unaffected(self):
        from app.engines.media.asset_service import MediaAssetService

        db = _db()
        actor = _user("staff", tenant_id=str(uuid.uuid4()))
        asset = _active_asset(media_context="provider_document", status="quarantined")
        svc = MediaAssetService(db=db, actor=actor)

        svc._assert_chat_attachment_lifecycle(asset, uuid.uuid4())  # no exception -- scoped out


# ══════════════════════════════════════════════════════════════════════════════
# 4. Transaction boundary / no intermediate commit
# ══════════════════════════════════════════════════════════════════════════════

class TestTransactionBoundary:
    @pytest.mark.asyncio
    async def test_no_commit_before_claim_and_message_are_both_ready(self):
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

        commit_calls_before_add = []
        original_add = db.add

        def _tracking_add(obj):
            commit_calls_before_add.append(db.commit.call_count)
            return original_add(obj)
        db.add = MagicMock(side_effect=_tracking_add)

        await svc.send_message(
            db=db, thread_id=thread.id, actor_user_id=uuid.uuid4(),
            actor_type="provider", tenant_id=shared_tenant,
            message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
        )
        # db.add (message + notification rows) must all happen with ZERO
        # prior commits -- the claim and the message share one transaction.
        assert all(c == 0 for c in commit_calls_before_add)
        assert db.commit.call_count == 1
        assert asset.metadata_json.get("chat_thread_id") == str(thread.id)

    @pytest.mark.asyncio
    async def test_commit_failure_propagates_not_swallowed(self):
        # Proves a failure after claim-assignment is not silently caught --
        # the caller's session-lifecycle rollback (standard, established
        # throughout this initiative) is what actually undoes the
        # in-memory claim; this test proves the exception is never
        # swallowed so that rollback mechanism is reachable.
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
        db.commit = AsyncMock(side_effect=RuntimeError("simulated commit failure"))

        with pytest.raises(RuntimeError):
            await svc.send_message(
                db=db, thread_id=thread.id, actor_user_id=uuid.uuid4(),
                actor_type="provider", tenant_id=shared_tenant,
                message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
            )


# ══════════════════════════════════════════════════════════════════════════════
# 5. No partial state
# ══════════════════════════════════════════════════════════════════════════════

class TestNoPartialState:
    @pytest.mark.asyncio
    async def test_ambiguous_office_share_persists_nothing(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_ATTACHMENT_NOT_FOUND

        svc = ChatMessageService()
        db = _db()
        shared_tenant = uuid.uuid4()
        customer_id = uuid.uuid4()
        staff = _user("staff", tenant_id=str(shared_tenant))
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=shared_tenant, customer_id=customer_id)
        thread.id = uuid.uuid4()
        thread_r, part_r, _ = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        unowned = _active_asset(tenant_id=shared_tenant, customer_id=customer_id, metadata_json={})
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(unowned)])

        with pytest.raises(ValueError, match=ERR_CHAT_ATTACHMENT_NOT_FOUND):
            await svc.send_message(
                db=db, thread_id=thread.id, actor_user_id=uuid.UUID(staff.user_id),
                actor_type="provider", tenant_id=shared_tenant,
                message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
                actor=staff,
            )
        db.add.assert_not_called()
        db.commit.assert_not_called()
        assert unowned.metadata_json.get("chat_thread_id") is None
