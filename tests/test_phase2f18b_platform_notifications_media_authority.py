"""Slice 2F-18B — Media Attachment Authority, Same-Tenant IDOR, Visibility
and Final Coverage Closure.

Covers:
- Reuse of the existing MediaAccessService.assert_can_view helper (not a
  duplicated policy).
- Same-tenant cross-customer media substitution rejection.
- media_context purpose-taxonomy enforcement (chat_attachment only).
- Deleted/inactive asset rejection.
- Privacy-equivalent rejection across every failure mode.
- No-partial-persistence proof for every new rejected path.
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
        access_level="tenant", status="active", deleted_at=None,
        metadata_json={},
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


class TestAttachmentContextTaxonomy:
    @pytest.mark.asyncio
    async def test_wrong_media_context_rejected(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_ATTACHMENT_NOT_FOUND

        svc = ChatMessageService()
        db = _db()
        shared_tenant = uuid.uuid4()
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=shared_tenant)
        thread_r, part_r, _ = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        # A real, active, same-tenant asset -- but uploaded for a DIFFERENT
        # purpose (e.g. a provider document), not a chat attachment.
        wrong_context_asset = _active_asset(tenant_id=shared_tenant, media_context="provider_document")
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(wrong_context_asset)])

        with pytest.raises(ValueError, match=ERR_CHAT_ATTACHMENT_NOT_FOUND):
            await svc.send_message(
                db=db, thread_id=uuid.uuid4(), actor_user_id=uuid.uuid4(),
                actor_type="provider", tenant_id=shared_tenant,
                message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
            )
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_correct_media_context_accepted(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread

        svc = ChatMessageService()
        db = _db()
        shared_tenant = uuid.uuid4()
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=shared_tenant)
        thread_r, part_r, participants_r = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        asset = _active_asset(tenant_id=shared_tenant, media_context="chat_attachment")
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(asset), participants_r])

        msg = await svc.send_message(
            db=db, thread_id=uuid.uuid4(), actor_user_id=uuid.uuid4(),
            actor_type="provider", tenant_id=shared_tenant,
            message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
        )
        assert msg is not None


class TestAttachmentLifecycleState:
    @pytest.mark.asyncio
    async def test_soft_deleted_asset_rejected(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_ATTACHMENT_NOT_FOUND
        from datetime import datetime, timezone

        svc = ChatMessageService()
        db = _db()
        shared_tenant = uuid.uuid4()
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=shared_tenant)
        thread_r, part_r, _ = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        deleted_asset = _active_asset(tenant_id=shared_tenant, deleted_at=datetime.now(timezone.utc))
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(deleted_asset)])

        with pytest.raises(ValueError, match=ERR_CHAT_ATTACHMENT_NOT_FOUND):
            await svc.send_message(
                db=db, thread_id=uuid.uuid4(), actor_user_id=uuid.uuid4(),
                actor_type="provider", tenant_id=shared_tenant,
                message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
            )
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_inactive_status_asset_rejected(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_ATTACHMENT_NOT_FOUND

        svc = ChatMessageService()
        db = _db()
        shared_tenant = uuid.uuid4()
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=shared_tenant)
        thread_r, part_r, _ = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        quarantined_asset = _active_asset(tenant_id=shared_tenant, status="quarantined")
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(quarantined_asset)])

        with pytest.raises(ValueError, match=ERR_CHAT_ATTACHMENT_NOT_FOUND):
            await svc.send_message(
                db=db, thread_id=uuid.uuid4(), actor_user_id=uuid.uuid4(),
                actor_type="provider", tenant_id=shared_tenant,
                message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
            )
        db.add.assert_not_called()


class TestSameTenantCustomerIDOR:
    @pytest.mark.asyncio
    async def test_cross_customer_media_within_same_tenant_rejected(self):
        # Media B (customer B's upload) attached to Customer A's thread --
        # both same tenant. 2F-18A's tenant-only check would have allowed
        # this; this slice's customer_id check must reject it.
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_ATTACHMENT_NOT_FOUND

        svc = ChatMessageService()
        db = _db()
        shared_tenant = uuid.uuid4()
        customer_a = uuid.uuid4()
        customer_b = uuid.uuid4()
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=shared_tenant, customer_id=customer_a)
        thread_r, part_r, _ = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        media_b = _active_asset(tenant_id=shared_tenant, customer_id=customer_b)
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(media_b)])

        with pytest.raises(ValueError, match=ERR_CHAT_ATTACHMENT_NOT_FOUND):
            await svc.send_message(
                db=db, thread_id=uuid.uuid4(), actor_user_id=uuid.uuid4(),
                actor_type="provider", tenant_id=shared_tenant,
                message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
            )
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_same_customer_media_accepted(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread

        svc = ChatMessageService()
        db = _db()
        shared_tenant = uuid.uuid4()
        customer_a = uuid.uuid4()
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=shared_tenant, customer_id=customer_a)
        thread_r, part_r, participants_r = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        own_media = _active_asset(tenant_id=shared_tenant, customer_id=customer_a)
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(own_media), participants_r])

        msg = await svc.send_message(
            db=db, thread_id=uuid.uuid4(), actor_user_id=uuid.uuid4(),
            actor_type="provider", tenant_id=shared_tenant,
            message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
        )
        assert msg is not None


class TestMediaAccessServiceReuse:
    @pytest.mark.asyncio
    async def test_customer_cannot_attach_another_customers_upload(self):
        # Reuses the REAL MediaAccessService.assert_can_view -- a customer
        # actor whose user_id doesn't match the asset's customer_id must be
        # rejected even when tenant/context/lifecycle checks all pass.
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_ATTACHMENT_NOT_FOUND

        svc = ChatMessageService()
        db = _db()
        actual_uploader = uuid.uuid4()
        caller = _user("customer", user_id=uuid.uuid4())
        thread = ChatThread(record_type="service_booking", record_id=uuid.uuid4(),
                             status="open", customer_id=uuid.UUID(caller.user_id))
        thread_r, part_r, _ = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        # Asset belongs to a DIFFERENT customer than the caller, but happens
        # to have no tenant_id/customer_id set on the asset itself (so the
        # tenant/customer_id pre-checks in chat_service pass through) --
        # only MediaAccessService's own uploaded_by/customer check catches it.
        foreign_asset = _active_asset(tenant_id=None, customer_id=None,
                                       uploaded_by_user_id=actual_uploader)
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(foreign_asset)])

        with pytest.raises(ValueError, match=ERR_CHAT_ATTACHMENT_NOT_FOUND):
            await svc.send_message(
                db=db, thread_id=uuid.uuid4(), actor_user_id=uuid.UUID(caller.user_id),
                actor_type="customer", tenant_id=None,
                message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
                actor=caller,
            )
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_technician_attaching_unowned_unclaimed_asset_now_rejected(self):
        # CORRECTED by Slice 2F-18D (see documentation-corrections.md):
        # this test previously documented tenant-wide technician media
        # view/attach as accepted, unnarrowed, existing MediaAccessService
        # behavior. Slice 2F-18D's first-use destination-authority rule
        # requires a technician to be the asset's OWN uploader to first-use
        # attach an unclaimed asset -- tenant membership (and even a valid
        # Job assignment) is no longer sufficient by itself. This asset's
        # uploader is a random, unrelated user, so the attach is now denied.
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_ATTACHMENT_NOT_FOUND

        svc = ChatMessageService()
        db = _db()
        shared_tenant = uuid.uuid4()
        technician = _user("technician", tenant_id=str(shared_tenant))
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=shared_tenant)
        thread_r, part_r, _ = _thread_mocks()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        # Technician branch of validate_thread_access requires assignment;
        # simulate an assigned job.
        job = MagicMock(assigned_staff_id=uuid.UUID(technician.user_id))
        db.get = AsyncMock(return_value=job)
        unowned_asset = _active_asset(tenant_id=shared_tenant)  # uploaded_by is a random unrelated user
        db.execute = AsyncMock(side_effect=[thread_r, part_r, _asset_result(unowned_asset)])

        with pytest.raises(ValueError, match=ERR_CHAT_ATTACHMENT_NOT_FOUND):
            await svc.send_message(
                db=db, thread_id=uuid.uuid4(), actor_user_id=uuid.UUID(technician.user_id),
                actor_type="technician", tenant_id=shared_tenant,
                message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
                actor=technician,
            )
        db.add.assert_not_called()


class TestAttachmentBasics:
    @pytest.mark.asyncio
    async def test_missing_asset_and_cross_tenant_asset_share_error_code(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_ATTACHMENT_NOT_FOUND

        svc = ChatMessageService()

        # Missing
        db1 = _db()
        thread1 = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                              status="open", tenant_id=uuid.uuid4())
        thread_r1, part_r1, _ = _thread_mocks()
        thread_r1.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread1)))
        db1.execute = AsyncMock(side_effect=[thread_r1, part_r1, _asset_result(None)])
        with pytest.raises(ValueError, match=ERR_CHAT_ATTACHMENT_NOT_FOUND):
            await svc.send_message(
                db=db1, thread_id=uuid.uuid4(), actor_user_id=uuid.uuid4(),
                actor_type="provider", tenant_id=thread1.tenant_id,
                message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
            )

        # Cross-tenant
        db2 = _db()
        thread2 = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                              status="open", tenant_id=uuid.uuid4())
        thread_r2, part_r2, _ = _thread_mocks()
        thread_r2.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread2)))
        db2.execute = AsyncMock(side_effect=[thread_r2, part_r2, _asset_result(_active_asset(tenant_id=uuid.uuid4()))])
        with pytest.raises(ValueError, match=ERR_CHAT_ATTACHMENT_NOT_FOUND):
            await svc.send_message(
                db=db2, thread_id=uuid.uuid4(), actor_user_id=uuid.uuid4(),
                actor_type="provider", tenant_id=thread2.tenant_id,
                message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
            )
        # Both raised the exact same error_code -- externally indistinguishable.
