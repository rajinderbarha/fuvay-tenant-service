"""Slice 2F-39A4: authorization defects found and fixed while resolving
the 21 PRODUCT_DECISION_REQUIRED routes flagged by Slice 2F-39A3.

Each test targets one confirmed real defect: a mutation that either had
zero tenant/identity scoping, or used an untrusted lookup helper while an
established, already-proven-correct sibling in the same file used the
trusted one.
"""
from __future__ import annotations

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.asyncio


class TestServiceCatalogDeactivateItemTenantScoping:
    def _svc(self, actor_role, actor_tenant_id):
        from app.engines.service_catalog.service import ServiceCatalogService
        svc = ServiceCatalogService.__new__(ServiceCatalogService)
        svc.db = MagicMock()
        svc.actor_role = actor_role
        svc.actor_tenant_id = actor_tenant_id
        return svc

    async def test_deactivating_another_tenants_item_is_rejected(self):
        my_tenant = uuid.uuid4()
        other_tenant = uuid.uuid4()
        svc = self._svc("tenant_owner", my_tenant)
        item = MagicMock(tenant_id=other_tenant, is_active=True)
        r = MagicMock(); r.scalar_one_or_none.return_value = item
        svc.db.execute = AsyncMock(return_value=r)
        with pytest.raises(Exception):
            await svc.deactivate_item(uuid.uuid4())

    async def test_deactivating_own_tenants_item_succeeds(self):
        my_tenant = uuid.uuid4()
        svc = self._svc("tenant_owner", my_tenant)
        item = MagicMock(tenant_id=my_tenant, is_active=True)
        r = MagicMock(); r.scalar_one_or_none.return_value = item
        svc.db.execute = AsyncMock(return_value=r)
        svc._dict = MagicMock(return_value={"is_active": False})
        result = await svc.deactivate_item(uuid.uuid4())
        assert item.is_active is False
        assert result == {"is_active": False}

    async def test_super_admin_can_deactivate_any_tenants_item(self):
        svc = self._svc("super_admin", None)
        item = MagicMock(tenant_id=uuid.uuid4(), is_active=True)
        r = MagicMock(); r.scalar_one_or_none.return_value = item
        svc.db.execute = AsyncMock(return_value=r)
        svc._dict = MagicMock(return_value={"is_active": False})
        await svc.deactivate_item(uuid.uuid4())
        assert item.is_active is False


class TestInventoryReplenishTenantScoping:
    def _svc(self, actor_role, actor_tenant_id):
        from app.engines.inventory.service import InventoryService
        svc = InventoryService.__new__(InventoryService)
        svc.db = MagicMock()
        svc.actor_role = actor_role
        svc.actor_tenant_id = actor_tenant_id
        svc._publish = AsyncMock()
        return svc

    async def test_replenish_for_another_tenant_is_rejected(self):
        my_tenant = uuid.uuid4()
        other_tenant = uuid.uuid4()
        svc = self._svc("tenant_owner", my_tenant)
        with pytest.raises(Exception):
            await svc.request_replenishment(other_tenant, uuid.uuid4(), 10)

    async def test_replenish_for_own_tenant_succeeds(self):
        my_tenant = uuid.uuid4()
        svc = self._svc("tenant_owner", my_tenant)
        result = await svc.request_replenishment(my_tenant, uuid.uuid4(), 10)
        assert result["status"] == "pending"


class TestNotificationTestChannelTenantScoping:
    def _svc(self, actor_role, actor_tenant_id):
        from app.engines.notification.service import NotificationService
        svc = NotificationService.__new__(NotificationService)
        svc.actor_role = actor_role
        svc.actor_tenant_id = actor_tenant_id
        return svc

    async def test_testing_another_tenants_channel_is_rejected(self):
        svc = self._svc("tenant_owner", uuid.uuid4())
        with pytest.raises(Exception):
            await svc.test_channel(uuid.uuid4(), "sms")

    async def test_testing_own_tenants_channel_succeeds(self):
        my_tenant = uuid.uuid4()
        svc = self._svc("tenant_owner", my_tenant)
        result = await svc.test_channel(my_tenant, "sms")
        assert result["test_sent"] is True


class TestPaymentTenantScoping:
    def _svc(self, actor_role, actor_tenant_id):
        from app.engines.payment.service import PaymentService
        svc = PaymentService.__new__(PaymentService)
        svc.db = MagicMock()
        svc.actor_role = actor_role
        svc.actor_tenant_id = actor_tenant_id
        return svc

    async def test_create_order_for_another_tenant_is_rejected(self):
        svc = self._svc("tenant_owner", uuid.uuid4())
        with pytest.raises(Exception):
            await svc.create_payment_order(uuid.uuid4(), None, None,
                                            __import__("decimal").Decimal("100"),
                                            "customer_payment", "razorpay")

    async def test_generate_invoice_for_another_tenant_is_rejected(self):
        svc = self._svc("tenant_owner", uuid.uuid4())
        with pytest.raises(Exception):
            await svc.generate_invoice(uuid.uuid4(), None, None,
                                        __import__("decimal").Decimal("100"),
                                        __import__("decimal").Decimal("0"), [], "service")

    async def test_super_admin_can_create_order_for_any_tenant(self):
        svc = self._svc("super_admin", None)
        with patch("app.engines.payment.service.razorpay_client.create_order",
                   new=AsyncMock(return_value={"id": "order_123"})), \
             patch("app.engines.payment.service.get_settings") as mock_settings:
            mock_settings.return_value.RAZORPAY_KEY_ID = "test_key"
            result = await svc.create_payment_order(
                uuid.uuid4(), None, None, __import__("decimal").Decimal("100"),
                "customer_payment", "razorpay")
        assert result["gateway"] == "razorpay"


class TestRagKnowledgeBaseTenantScoping:
    def _svc(self, actor_role, actor_tenant_id):
        from app.engines.rag.service import RAGService
        svc = RAGService.__new__(RAGService)
        svc.db = MagicMock()
        svc.db.flush = AsyncMock()
        svc.actor_role = actor_role
        svc.actor_tenant_id = actor_tenant_id
        svc.actor_id = uuid.uuid4()
        svc._publish = AsyncMock()
        svc._kb_dict = MagicMock(return_value={"created": True})
        return svc

    async def test_create_kb_for_another_tenant_is_rejected(self):
        svc = self._svc("tenant_owner", uuid.uuid4())
        with pytest.raises(Exception):
            await svc.create_kb(uuid.uuid4(), "name", None, None, 512, 64, 5)

    async def test_create_kb_for_own_tenant_succeeds(self):
        my_tenant = uuid.uuid4()
        svc = self._svc("tenant_owner", my_tenant)
        result = await svc.create_kb(my_tenant, "name", None, None, 512, 64, 5)
        assert result == {"created": True}

    async def test_update_kb_uses_trusted_lookup(self):
        from app.engines.rag.service import RAGService
        svc = self._svc("tenant_owner", uuid.uuid4())
        svc._get_kb_trusted = AsyncMock(side_effect=Exception("NOT_FOUND"))
        svc._get_kb = AsyncMock()
        with pytest.raises(Exception):
            await svc.update_kb(uuid.uuid4(), {"name": "new"})
        svc._get_kb_trusted.assert_awaited_once()
        svc._get_kb.assert_not_awaited()


class TestDispatchAcceptRejectIdentityScoping:
    def _svc(self, actor_role, actor_id):
        from app.engines.dispatch.service import DispatchService
        svc = DispatchService.__new__(DispatchService)
        svc.db = MagicMock()
        svc.actor_role = actor_role
        svc.actor_id = actor_id
        return svc

    async def test_accepting_job_as_another_staff_member_is_rejected(self):
        me = uuid.uuid4()
        other_staff = uuid.uuid4()
        svc = self._svc("technician", me)
        with pytest.raises(Exception):
            await svc.accept_job("job-1", other_staff)

    async def test_accepting_job_as_self_succeeds(self):
        me = uuid.uuid4()
        svc = self._svc("technician", me)
        rec = MagicMock(status="pending", expires_at=None)
        r = MagicMock(); r.scalar_one_or_none.return_value = rec
        svc.db.execute = AsyncMock(return_value=r)
        svc._get_job = AsyncMock(return_value=None)
        svc._rec_dict = MagicMock(return_value={"accepted": True})
        result = await svc.accept_job("job-1", me)
        assert rec.assigned_staff_id == me
        assert result == {"accepted": True}

    async def test_rejecting_job_as_another_staff_member_is_rejected(self):
        me = uuid.uuid4()
        other_staff = uuid.uuid4()
        svc = self._svc("technician", me)
        with pytest.raises(Exception):
            await svc.reject_job("job-1", other_staff, "not available")

    async def test_super_admin_can_accept_job_as_any_staff(self):
        svc = self._svc("super_admin", uuid.uuid4())
        rec = MagicMock(status="pending", expires_at=None)
        r = MagicMock(); r.scalar_one_or_none.return_value = rec
        svc.db.execute = AsyncMock(return_value=r)
        svc._get_job = AsyncMock(return_value=None)
        svc._rec_dict = MagicMock(return_value={"accepted": True})
        await svc.accept_job("job-1", uuid.uuid4())
        assert rec.status is not None


class TestDataScienceAcknowledgeAnomalyTenantScoping:
    def _svc(self, actor_role, actor_tenant_id):
        from app.engines.data_science.service import DSService
        svc = DSService.__new__(DSService)
        svc.db = MagicMock()
        svc.actor_role = actor_role
        svc.actor_tenant_id = actor_tenant_id
        svc.actor_id = uuid.uuid4()
        return svc

    async def test_acknowledging_another_tenants_anomaly_is_rejected(self):
        svc = self._svc("tenant_owner", uuid.uuid4())
        anomaly = MagicMock(tenant_id=uuid.uuid4(), status="open")
        r = MagicMock(); r.scalar_one_or_none.return_value = anomaly
        svc.db.execute = AsyncMock(return_value=r)
        with pytest.raises(Exception):
            await svc.acknowledge_anomaly(uuid.uuid4(), "notes")

    async def test_acknowledging_own_tenants_anomaly_succeeds(self):
        my_tenant = uuid.uuid4()
        svc = self._svc("tenant_owner", my_tenant)
        anomaly = MagicMock(tenant_id=my_tenant, status="open")
        r = MagicMock(); r.scalar_one_or_none.return_value = anomaly
        svc.db.execute = AsyncMock(return_value=r)
        svc._anomaly_dict = MagicMock(return_value={"acknowledged": True})
        result = await svc.acknowledge_anomaly(uuid.uuid4(), "notes")
        assert anomaly.status == "acknowledged"
        assert result == {"acknowledged": True}
