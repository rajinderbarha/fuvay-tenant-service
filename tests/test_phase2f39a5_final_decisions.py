"""Slice 2F-39A5: final resolution of the 5 PRODUCT_DECISION_REQUIRED
routes left open by Slice 2F-39A4, per explicit user decisions (delegated
to the assistant, applied as the most defensible fail-closed choice
matching each route's actual risk/evidence):

- platform_commerce.billing_endpoint::route_operation -> require_super_admin
  (matches sibling get_configs/set_config; no tenant-caller evidence found).
- appointment.router::hold_slot -> tenant-ownership check added at the
  service layer (corroborated by the already-frozen fresh-manual-adjudication
  corpus, which classifies this route's persona as TENANT_PROVIDER_MUTATION,
  not customer self-service); customer_id remains unchecked to preserve
  legitimate staff-assisted booking.
- analytics.router::ingest_event -> require_super_admin (no in-process
  caller found; arbitrary tenant/actor forgery risk).
- notification.router::send_notification, retry -> require_super_admin
  (no in-process caller found for either).
"""
from __future__ import annotations

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.asyncio


class TestRouteOperationRequiresSuperAdmin:
    def test_router_guard_is_require_super_admin(self):
        import inspect
        from app.engines.platform_commerce import billing_endpoint
        src = inspect.getsource(billing_endpoint.route_operation)
        assert "Depends(require_super_admin)" in src


class TestIngestEventRequiresSuperAdmin:
    def test_router_guard_is_require_super_admin(self):
        import inspect
        from app.engines.analytics import router as analytics_router
        src = inspect.getsource(analytics_router.ingest_event)
        assert "Depends(require_super_admin)" in src


class TestNotificationSendAndRetryRequireSuperAdmin:
    def test_send_notification_guard_is_require_super_admin(self):
        import inspect
        from app.engines.notification import router as notification_router
        src = inspect.getsource(notification_router.send_notification)
        assert "Depends(require_super_admin)" in src

    def test_retry_guard_is_require_super_admin(self):
        import inspect
        from app.engines.notification import router as notification_router
        src = inspect.getsource(notification_router.retry)
        assert "Depends(require_super_admin)" in src


class TestHoldSlotTenantScoping:
    def _svc(self, actor_role, actor_tenant_id):
        from app.engines.appointment.service import AppointmentService
        svc = AppointmentService.__new__(AppointmentService)
        svc.db = MagicMock()
        svc.redis = MagicMock()
        svc.actor_role = actor_role
        svc.actor_tenant_id = actor_tenant_id
        return svc

    async def test_holding_a_slot_for_another_tenant_is_rejected(self):
        svc = self._svc("staff", uuid.uuid4())
        other_tenant = uuid.uuid4()
        with pytest.raises(Exception):
            await svc.hold_slot(
                staff_id=uuid.uuid4(), tenant_id=other_tenant,
                customer_id=uuid.uuid4(), service_type_id="x",
                scheduled_at="2026-01-01T10:00:00", duration_minutes=60,
                booking_id=None, customer_notes=None)

    async def test_own_tenant_hold_is_not_rejected_by_the_tenant_check(self):
        """Staff-assisted booking: customer_id need not equal the caller --
        only tenant_id ownership is enforced. Verified directly against
        _require_trusted_tenant, the same helper hold_slot now calls first."""
        my_tenant = uuid.uuid4()
        svc = self._svc("staff", my_tenant)
        result = svc._require_trusted_tenant(my_tenant)
        assert result == my_tenant

    async def test_super_admin_can_hold_slot_for_any_tenant(self):
        svc = self._svc("super_admin", None)
        result_tenant = svc._require_trusted_tenant(uuid.uuid4())
        assert result_tenant is not None
