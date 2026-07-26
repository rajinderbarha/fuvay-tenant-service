"""Multi-vertical Phase 3 — GET /v1/tenant/navigation now returns a real
`vertical_context` block (vertical_key/capabilities/enrollment_status),
resolved server-side from the tenant's own row -- the source the frontend
sidebar (TenantLayout.tsx) now reads instead of hardcoded per-vertical-key
lookup tables. No live DB required.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_tenant(**kwargs):
    t = MagicMock()
    defaults = {"id": uuid.uuid4(), "vertical": "home_services", "category_id": None}
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(t, k, v)
    return t


def _make_vertical(**kwargs):
    v = MagicMock()
    defaults = {
        "id": uuid.uuid4(), "key": "home_services", "label": "Home Services",
        "is_enabled": True, "capabilities": ["customers", "staff", "bookings", "jobs"],
    }
    defaults.update(kwargs)
    for k, val in defaults.items():
        setattr(v, k, val)
    return v


def _make_enrollment(**kwargs):
    e = MagicMock()
    defaults = {"status": "active"}
    defaults.update(kwargs)
    for k, val in defaults.items():
        setattr(e, k, val)
    return e


class TestNavigationVerticalContext:
    @pytest.mark.asyncio
    async def test_navigation_includes_real_vertical_capabilities_and_enrollment_status(self):
        from app.engines.tenant_engine.portal_router import get_navigation

        tenant = _make_tenant(vertical="coaching")
        vertical = _make_vertical(key="coaching", label="Coaching",
                                   capabilities=["customers", "staff", "coaches", "appointments"])
        enrollment = _make_enrollment(status="active")

        # tenant.category_id is None, so the category lookup branch is
        # skipped entirely -- real call order is: tenant, vertical, enrollment.
        db = MagicMock()
        scalar_calls = [tenant, vertical, enrollment]
        async def mock_scalar(q):
            return scalar_calls.pop(0)
        db.scalar = mock_scalar

        user = MagicMock(user_id=str(tenant.id), tenant_id=str(tenant.id))
        request = MagicMock()
        request.state.request_id = "req_test"
        request.headers = {}

        with patch("app.engines.tenant_engine.portal_router.entitlement_service") as mock_ent:
            mock_ent.get_tenant_categories = AsyncMock(return_value=[])
            result = await get_navigation(request=request, db=db, user=user)

        ctx = result.data["vertical_context"]
        assert ctx["vertical_key"] == "coaching"
        assert ctx["enrollment_status"] == "active"
        assert "appointments" in ctx["capabilities"]
        assert "jobs" not in ctx["capabilities"]

    @pytest.mark.asyncio
    async def test_navigation_vertical_context_is_none_when_tenant_has_no_vertical(self):
        from app.engines.tenant_engine.portal_router import get_navigation

        tenant = _make_tenant(vertical=None)
        db = MagicMock()
        scalar_calls = [tenant, None]
        async def mock_scalar(q):
            return scalar_calls.pop(0)
        db.scalar = mock_scalar

        user = MagicMock(user_id=str(tenant.id), tenant_id=str(tenant.id))
        request = MagicMock()
        request.state.request_id = "req_test"
        request.headers = {}

        with patch("app.engines.tenant_engine.portal_router.entitlement_service") as mock_ent:
            mock_ent.get_tenant_categories = AsyncMock(return_value=[])
            result = await get_navigation(request=request, db=db, user=user)

        assert result.data["vertical_context"] is None
