"""Slice 2F-39A3: 2 real authorization defects found and fixed during
route-classification tranche 3.
"""
from __future__ import annotations

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.asyncio


class TestChatDeleteMessageOwnership:
    def _svc(self, actor_id):
        from app.engines.chat.service import ChatService
        svc = ChatService.__new__(ChatService)
        svc.db = MagicMock()
        svc.actor_id = actor_id
        return svc

    async def test_deleting_someone_elses_message_is_rejected(self):
        me = uuid.uuid4()
        someone_else = uuid.uuid4()
        svc = self._svc(actor_id=me)
        msg = MagicMock(sender_id=someone_else, is_deleted=False)
        msg_result = MagicMock()
        msg_result.scalar_one_or_none.return_value = msg
        svc.db.execute = AsyncMock(return_value=msg_result)
        with pytest.raises(Exception):
            await svc.delete_message(uuid.uuid4(), uuid.uuid4())

    async def test_deleting_own_message_succeeds(self):
        me = uuid.uuid4()
        svc = self._svc(actor_id=me)
        msg = MagicMock(sender_id=me, is_deleted=False)
        msg_result = MagicMock()
        msg_result.scalar_one_or_none.return_value = msg
        svc.db.execute = AsyncMock(return_value=msg_result)
        svc._msg_dict = MagicMock(return_value={"id": "x"})
        result = await svc.delete_message(uuid.uuid4(), uuid.uuid4())
        assert result == {"id": "x"}
        assert msg.is_deleted is True


class TestComplianceConsentSelfService:
    def _request(self, user_id, tenant_id=None):
        body = {"user_id": str(user_id), "consent_type": "marketing", "action": "granted"}
        if tenant_id:
            body["tenant_id"] = str(tenant_id)

        class FakeState:
            request_id = "req_test"

        class FakeRequest:
            state = FakeState()

            async def json(self_inner):
                return body
        return FakeRequest()

    async def test_record_consent_for_another_user_is_rejected(self):
        from app.engines.compliance import router as compliance_router
        me = str(uuid.uuid4())
        other = uuid.uuid4()

        class FakeUser:
            role = "customer"
            user_id = me

        with pytest.raises(Exception):
            await compliance_router.record_consent(
                self._request(other), u=FakeUser(), s=MagicMock())

    async def test_record_consent_for_self_is_accepted(self):
        from app.engines.compliance import router as compliance_router
        me = uuid.uuid4()

        class FakeUser:
            role = "customer"
            user_id = str(me)

        fake_svc = MagicMock()
        fake_svc.record_consent = AsyncMock(return_value={"recorded": True})
        await compliance_router.record_consent(self._request(me), u=FakeUser(), s=fake_svc)
        called_user_id = fake_svc.record_consent.await_args.args[0]
        assert called_user_id == me

    async def test_withdraw_consent_for_another_user_is_rejected(self):
        from app.engines.compliance import router as compliance_router
        me = str(uuid.uuid4())
        other = uuid.uuid4()

        class FakeRequest:
            async def json(self_inner):
                return {"user_id": str(other), "consent_type": "marketing"}

        class FakeUser:
            role = "customer"
            user_id = me

        with pytest.raises(Exception):
            await compliance_router.withdraw_consent(FakeRequest(), u=FakeUser(), s=MagicMock())

    async def test_super_admin_can_record_consent_for_another_user(self):
        from app.engines.compliance import router as compliance_router
        other = uuid.uuid4()

        class FakeUser:
            role = "super_admin"
            user_id = str(uuid.uuid4())

        fake_svc = MagicMock()
        fake_svc.record_consent = AsyncMock(return_value={"recorded": True})
        await compliance_router.record_consent(self._request(other), u=FakeUser(), s=fake_svc)
        called_user_id = fake_svc.record_consent.await_args.args[0]
        assert called_user_id == other
