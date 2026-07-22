"""Slice 2F-18A — Technician Scope, Participant Authority, Attachment
Ownership, Error Privacy and Final Coverage Closure.

Covers:
- Technician chat policy (assigned-job-only / active-participant-only, NOT
  tenant-wide).
- list_threads excludes technician from the tenant-wide branch.
- Privacy-equivalent thread-access errors (foreign == missing).
- Attachment/media ownership validation (existence + tenant match).
- Dependency semantics (direct invocation, not just introspection).
- Customer-router object-ownership reverification.
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


# ══════════════════════════════════════════════════════════════════════════════
# 1. Technician thread-access policy
# ══════════════════════════════════════════════════════════════════════════════

class TestTechnicianThreadAccessPolicy:
    @pytest.mark.asyncio
    async def test_assigned_technician_allowed(self):
        from app.engines.platform_notifications.chat_service import ChatThreadService
        from app.engines.platform_notifications.models import ChatThread

        svc = ChatThreadService()
        db = _db()
        technician_id = uuid.uuid4()
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=uuid.uuid4())
        thread.id = uuid.uuid4()
        job = MagicMock(assigned_staff_id=technician_id)
        db.get = AsyncMock(return_value=job)

        await svc.validate_thread_access(db, thread, technician_id, "technician", None)
        # No exception raised == allowed.

    @pytest.mark.asyncio
    async def test_unassigned_technician_denied(self):
        from app.engines.platform_notifications.chat_service import ChatThreadService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_THREAD_NOT_FOUND

        svc = ChatThreadService()
        db = _db()
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=uuid.uuid4())
        thread.id = uuid.uuid4()
        job = MagicMock(assigned_staff_id=uuid.uuid4())  # someone else
        db.get = AsyncMock(return_value=job)

        with pytest.raises(ValueError, match=ERR_CHAT_THREAD_NOT_FOUND):
            await svc.validate_thread_access(db, thread, uuid.uuid4(), "technician", None)

    @pytest.mark.asyncio
    async def test_technician_assigned_to_other_job_denied(self):
        # Technician assigned to Job A tries to access Job B's thread.
        from app.engines.platform_notifications.chat_service import ChatThreadService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_THREAD_NOT_FOUND

        svc = ChatThreadService()
        db = _db()
        technician_id = uuid.uuid4()
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=uuid.uuid4())
        thread.id = uuid.uuid4()
        job_b = MagicMock(assigned_staff_id=uuid.uuid4())  # not this technician
        db.get = AsyncMock(return_value=job_b)

        with pytest.raises(ValueError, match=ERR_CHAT_THREAD_NOT_FOUND):
            await svc.validate_thread_access(db, thread, technician_id, "technician", None)

    @pytest.mark.asyncio
    async def test_active_participant_technician_allowed_for_unresolvable_record_type(self):
        from app.engines.platform_notifications.chat_service import ChatThreadService
        from app.engines.platform_notifications.models import ChatThread

        svc = ChatThreadService()
        db = _db()
        technician_id = uuid.uuid4()
        thread = ChatThread(record_type="admin_internal", record_id=uuid.uuid4(),
                             status="open", tenant_id=uuid.uuid4())
        thread.id = uuid.uuid4()
        # _resolve_job_for_thread returns None for this record_type (no db.get call
        # needed); the participant lookup query returns a hit.
        found = MagicMock()
        found.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=MagicMock())))
        db.execute = AsyncMock(return_value=found)

        await svc.validate_thread_access(db, thread, technician_id, "technician", None)

    @pytest.mark.asyncio
    async def test_removed_participant_technician_denied(self):
        from app.engines.platform_notifications.chat_service import ChatThreadService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_THREAD_NOT_FOUND

        svc = ChatThreadService()
        db = _db()
        technician_id = uuid.uuid4()
        thread = ChatThread(record_type="admin_internal", record_id=uuid.uuid4(),
                             status="open", tenant_id=uuid.uuid4())
        thread.id = uuid.uuid4()
        # The query filters left_at == None -- a removed participant's row
        # would not match, so the mock simulates "no active row found".
        not_found = MagicMock()
        not_found.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
        db.execute = AsyncMock(return_value=not_found)

        with pytest.raises(ValueError, match=ERR_CHAT_THREAD_NOT_FOUND):
            await svc.validate_thread_access(db, thread, technician_id, "technician", None)

    @pytest.mark.asyncio
    async def test_technician_tenant_membership_alone_is_not_sufficient(self):
        # A technician who shares the thread's tenant_id, is NOT assigned to
        # the job, and has NO participant row must still be denied -- proves
        # tenant membership alone does not grant Job-conversation access.
        from app.engines.platform_notifications.chat_service import ChatThreadService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_THREAD_NOT_FOUND

        svc = ChatThreadService()
        db = _db()
        shared_tenant = uuid.uuid4()
        technician_id = uuid.uuid4()
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=shared_tenant)
        thread.id = uuid.uuid4()
        job = MagicMock(assigned_staff_id=uuid.uuid4())
        db.get = AsyncMock(return_value=job)

        with pytest.raises(ValueError, match=ERR_CHAT_THREAD_NOT_FOUND):
            await svc.validate_thread_access(db, thread, technician_id, "technician", shared_tenant)


class TestListThreadsExcludesTechnicianFromTenantWide:
    @pytest.mark.asyncio
    async def test_technician_list_threads_is_participant_scoped_not_tenant_wide(self):
        from app.engines.platform_notifications.chat_service import ChatThreadService

        svc = ChatThreadService()
        db = _db()
        technician_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        part_result = MagicMock()
        part_result.all = MagicMock(return_value=[])
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=0)
        list_result = MagicMock()
        list_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        db.execute = AsyncMock(side_effect=[part_result, count_result, list_result])

        await svc.list_threads(db, technician_id, "technician", tenant_id=tenant_id)
        # First call must be the participant-id lookup (not a tenant-wide
        # ChatThread.tenant_id query) -- proven by the side_effect ordering
        # succeeding without error (a tenant-wide query would be the 1st and
        # only call, and this would raise StopIteration on the 2nd .execute).
        assert db.execute.await_count == 3


# ══════════════════════════════════════════════════════════════════════════════
# 2. Privacy-equivalent thread errors
# ══════════════════════════════════════════════════════════════════════════════

class TestPrivacyEquivalentThreadErrors:
    @pytest.mark.asyncio
    async def test_foreign_tenant_and_missing_thread_share_error_code(self):
        from app.engines.platform_notifications.chat_service import ChatThreadService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_THREAD_NOT_FOUND

        svc = ChatThreadService()
        db_missing = _db()
        none_r = MagicMock()
        none_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
        db_missing.execute = AsyncMock(return_value=none_r)

        with pytest.raises(ValueError, match=ERR_CHAT_THREAD_NOT_FOUND):
            await svc.get_thread(db_missing, uuid.uuid4(), uuid.uuid4(), "provider", uuid.uuid4())

        db_foreign = _db()
        foreign_thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                                     status="open", tenant_id=uuid.uuid4())
        foreign_thread.id = uuid.uuid4()
        found_r = MagicMock()
        found_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=foreign_thread)))
        db_foreign.execute = AsyncMock(return_value=found_r)

        with pytest.raises(ValueError, match=ERR_CHAT_THREAD_NOT_FOUND):
            await svc.get_thread(db_foreign, foreign_thread.id, uuid.uuid4(), "provider", uuid.uuid4())
        # Both raised the exact same error_code -- externally indistinguishable.

    def test_thread_not_found_maps_to_404_not_403(self):
        from app.exceptions import _domain_code_status
        from app.engines.platform_notifications.constants import (
            ERR_CHAT_THREAD_NOT_FOUND, ERR_CHAT_THREAD_ACCESS_DENIED,
        )
        assert _domain_code_status(ERR_CHAT_THREAD_NOT_FOUND) == 404
        # The old code still maps to 403 if ever raised elsewhere -- proves
        # the fix is about WHICH code is raised, not a global remap.
        assert _domain_code_status(ERR_CHAT_THREAD_ACCESS_DENIED) == 403


# ══════════════════════════════════════════════════════════════════════════════
# 3. Attachment/media ownership
# ══════════════════════════════════════════════════════════════════════════════

class TestAttachmentOwnership:
    @pytest.mark.asyncio
    async def test_nonexistent_media_asset_rejected(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_ATTACHMENT_NOT_FOUND

        svc = ChatMessageService()
        db = _db()
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=uuid.uuid4())
        thread_r = MagicMock()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        part_r = MagicMock()
        part_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
        asset_r = MagicMock()
        asset_r.scalar_one_or_none = MagicMock(return_value=None)  # MediaAsset lookup finds nothing
        db.execute = AsyncMock(side_effect=[thread_r, part_r, asset_r])

        with pytest.raises(ValueError, match=ERR_CHAT_ATTACHMENT_NOT_FOUND):
            await svc.send_message(
                db=db, thread_id=uuid.uuid4(), actor_user_id=uuid.uuid4(),
                actor_type="provider", tenant_id=thread.tenant_id,
                message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
            )
        db.add.assert_not_called()
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_cross_tenant_media_asset_rejected(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_ATTACHMENT_NOT_FOUND

        svc = ChatMessageService()
        db = _db()
        thread_tenant = uuid.uuid4()
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=thread_tenant)
        thread_r = MagicMock()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        part_r = MagicMock()
        part_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
        foreign_asset = MagicMock(tenant_id=uuid.uuid4())  # different tenant
        asset_r = MagicMock()
        asset_r.scalar_one_or_none = MagicMock(return_value=foreign_asset)
        db.execute = AsyncMock(side_effect=[thread_r, part_r, asset_r])

        with pytest.raises(ValueError, match=ERR_CHAT_ATTACHMENT_NOT_FOUND):
            await svc.send_message(
                db=db, thread_id=uuid.uuid4(), actor_user_id=uuid.uuid4(),
                actor_type="provider", tenant_id=thread_tenant,
                message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
            )
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_same_tenant_media_asset_accepted(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread

        svc = ChatMessageService()
        db = _db()
        shared_tenant = uuid.uuid4()
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=shared_tenant)
        thread_r = MagicMock()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        part_r = MagicMock()
        part_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
        participants_r = MagicMock()
        participants_r.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        own_asset = MagicMock(tenant_id=shared_tenant, customer_id=None,
                               deleted_at=None, status="active", media_context="chat_attachment",
                               metadata_json={})
        asset_r = MagicMock()
        asset_r.scalar_one_or_none = MagicMock(return_value=own_asset)
        db.execute = AsyncMock(side_effect=[thread_r, part_r, asset_r, participants_r])

        msg = await svc.send_message(
            db=db, thread_id=uuid.uuid4(), actor_user_id=uuid.uuid4(),
            actor_type="provider", tenant_id=shared_tenant,
            message_text=None, media_urls={"media_ids": [str(uuid.uuid4())]},
        )
        assert msg.media_urls == {"media_ids": [msg.media_urls["media_ids"][0]]}

    @pytest.mark.asyncio
    async def test_malformed_media_id_rejected(self):
        from app.engines.platform_notifications.chat_service import ChatMessageService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_ATTACHMENT_NOT_FOUND

        svc = ChatMessageService()
        db = _db()
        thread = ChatThread(record_type="service_job", record_id=uuid.uuid4(),
                             status="open", tenant_id=uuid.uuid4())
        thread_r = MagicMock()
        thread_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        part_r = MagicMock()
        part_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))
        db.execute = AsyncMock(side_effect=[thread_r, part_r])

        with pytest.raises(ValueError, match=ERR_CHAT_ATTACHMENT_NOT_FOUND):
            await svc.send_message(
                db=db, thread_id=uuid.uuid4(), actor_user_id=uuid.uuid4(),
                actor_type="provider", tenant_id=thread.tenant_id,
                message_text=None, media_urls={"media_ids": ["not-a-uuid"]},
            )
        db.add.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════════
# 4. Dependency semantics — direct invocation
# ══════════════════════════════════════════════════════════════════════════════

def _user(role, tenant_id=None, access_scope=None, force_password_change=False):
    from app.dependencies.auth import UserContext
    return UserContext(
        user_id=str(uuid.uuid4()), email="x@example.com", role=role,
        tenant_id=tenant_id, full_name="X", is_verified=True,
        force_password_change=force_password_change, access_scope=access_scope,
    )


class TestDependencySemantics:
    @pytest.mark.asyncio
    async def test_owner_or_office_staff_mutation_admits_tenant_owner(self):
        from app.core.permissions import require_owner_or_office_staff_mutation
        u = _user("tenant_owner", tenant_id=str(uuid.uuid4()))
        result = await require_owner_or_office_staff_mutation(u)
        assert result is u

    @pytest.mark.asyncio
    async def test_owner_or_office_staff_mutation_rejects_technician(self):
        from app.core.permissions import require_owner_or_office_staff_mutation
        from app.exceptions import ServiceOSException
        u = _user("technician", tenant_id=str(uuid.uuid4()))
        with pytest.raises(ServiceOSException):
            await require_owner_or_office_staff_mutation(u)

    @pytest.mark.asyncio
    async def test_owner_or_office_staff_mutation_denies_readonly_scope(self):
        from app.core.permissions import require_owner_or_office_staff_mutation
        from app.exceptions import ServiceOSException
        u = _user("staff", tenant_id=str(uuid.uuid4()), access_scope="customer_support_limited")
        with pytest.raises(ServiceOSException):
            await require_owner_or_office_staff_mutation(u)

    @pytest.mark.asyncio
    async def test_owner_or_office_staff_mutation_rejects_unknown_role(self):
        from app.core.permissions import require_owner_or_office_staff_mutation
        from app.exceptions import ServiceOSException
        u = _user("office_staff", tenant_id=str(uuid.uuid4()))  # prohibited alias
        with pytest.raises(ServiceOSException):
            await require_owner_or_office_staff_mutation(u)

    @pytest.mark.asyncio
    async def test_owner_or_office_staff_mutation_rejects_customer(self):
        from app.core.permissions import require_owner_or_office_staff_mutation
        from app.exceptions import ServiceOSException
        u = _user("customer")
        with pytest.raises(ServiceOSException):
            await require_owner_or_office_staff_mutation(u)

    @pytest.mark.asyncio
    async def test_staff_or_technician_only_admits_technician(self):
        from app.dependencies.auth import require_staff_or_technician_only
        u = _user("technician", tenant_id=str(uuid.uuid4()))
        result = await require_staff_or_technician_only(u)
        assert result is u

    @pytest.mark.asyncio
    async def test_staff_or_technician_only_rejects_tenant_owner(self):
        from app.dependencies.auth import require_staff_or_technician_only
        from app.exceptions import ServiceOSException
        u = _user("tenant_owner", tenant_id=str(uuid.uuid4()))
        with pytest.raises(ServiceOSException):
            await require_staff_or_technician_only(u)

    @pytest.mark.asyncio
    async def test_staff_or_technician_only_rejects_customer(self):
        from app.dependencies.auth import require_staff_or_technician_only
        from app.exceptions import ServiceOSException
        u = _user("customer")
        with pytest.raises(ServiceOSException):
            await require_staff_or_technician_only(u)

    @pytest.mark.asyncio
    async def test_staff_or_technician_only_rejects_prohibited_alias(self):
        from app.dependencies.auth import require_staff_or_technician_only
        from app.exceptions import ServiceOSException
        u = _user("manager")
        with pytest.raises(ServiceOSException):
            await require_staff_or_technician_only(u)

    @pytest.mark.asyncio
    async def test_require_customer_rejects_tenant_owner(self):
        from app.dependencies.auth import require_customer
        from app.exceptions import ServiceOSException
        u = _user("tenant_owner", tenant_id=str(uuid.uuid4()))
        with pytest.raises(ServiceOSException):
            await require_customer(u)

    @pytest.mark.asyncio
    async def test_require_customer_admits_customer(self):
        from app.dependencies.auth import require_customer
        u = _user("customer")
        result = await require_customer(u)
        assert result is u


# ══════════════════════════════════════════════════════════════════════════════
# 5. Customer-router object-ownership reverification
# ══════════════════════════════════════════════════════════════════════════════

class TestCustomerRouterObjectOwnership:
    @pytest.mark.asyncio
    async def test_customer_cannot_read_foreign_thread(self):
        from app.engines.platform_notifications.chat_service import ChatThreadService
        from app.engines.platform_notifications.models import ChatThread
        from app.engines.platform_notifications.constants import ERR_CHAT_THREAD_NOT_FOUND

        svc = ChatThreadService()
        db = _db()
        other_customer = uuid.uuid4()
        thread = ChatThread(record_type="service_booking", record_id=uuid.uuid4(),
                             status="open", customer_id=other_customer)
        found_r = MagicMock()
        found_r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=thread)))
        db.execute = AsyncMock(return_value=found_r)

        with pytest.raises(ValueError, match=ERR_CHAT_THREAD_NOT_FOUND):
            await svc.get_thread(db, uuid.uuid4(), uuid.uuid4(), "customer", None)

    @pytest.mark.asyncio
    async def test_customer_router_does_not_import_tenant_mutation_dependency(self):
        # No customer_router.py route should ever depend on a
        # tenant-mutation-scope guard (require_owner_or_office_staff_mutation)
        # -- customer identity/ownership is the correct gate, not tenant
        # mutation scope.
        from app.engines.platform_notifications import customer_router as m
        for router in (m.customer_notif_router, m.customer_chat_router):
            for route in router.routes:
                names = set()

                def walk(dependant):
                    if dependant.call is not None and hasattr(dependant.call, "__name__"):
                        names.add(dependant.call.__name__)
                    for sub in dependant.dependencies:
                        walk(sub)
                walk(route.dependant)
                assert "require_owner_or_office_staff_mutation" not in names
                assert "require_customer" in names
