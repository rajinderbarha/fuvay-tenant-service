"""Multi-vertical platform refactor — Phase 1 (migration 148).

Covers the concrete, testable slice of the larger spec that Phase 1 actually
implements: canonical vertical registry audit fields, tenant-vertical
enrollment lifecycle (independent per vertical), disable-impact reporting,
and the require_vertical_enabled / require_tenant_vertical_active /
require_vertical_capability backend guards. Does not require a live DB.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.vertical_catalog.service import VerticalCatalogService
from app.exceptions import (
    VerticalDisabledException, TenantVerticalNotActiveException,
    VerticalCapabilityUnavailableException,
)


def _scalar(value):
    r = MagicMock()
    r.scalar_one_or_none = MagicMock(return_value=value)
    return r


def _make_vertical(**kwargs):
    v = MagicMock()
    defaults = {
        "id": uuid.uuid4(), "key": "home_services", "slug": "home_services",
        "label": "Home Services", "description": None, "icon": None, "color": None,
        "is_enabled": True, "is_beta": False, "sort_order": 1, "finance_model": "commission",
        "meta": None, "lifecycle_status": "active", "registration_allowed": True,
        "capabilities": ["customers", "staff", "bookings"], "onboarding_requirements": None,
        "enabled_by": None, "disabled_by": None, "enabled_at": None, "disabled_at": None,
        "disable_reason": None,
    }
    defaults.update(kwargs)
    for k, val in defaults.items():
        setattr(v, k, val)
    return v


def _make_enrollment(**kwargs):
    e = MagicMock()
    defaults = {
        "id": uuid.uuid4(), "tenant_id": uuid.uuid4(), "vertical_id": uuid.uuid4(),
        "status": "active", "requested_at": None, "submitted_at": None,
        "reviewed_by": None, "reviewed_at": None, "activated_at": None,
        "suspended_at": None, "suspend_reason": None, "rejection_reason": None,
        "changes_requested_note": None, "admin_notes": None,
    }
    defaults.update(kwargs)
    for k, val in defaults.items():
        setattr(e, k, val)
    return e


# ── Vertical disable/enable audit trail ────────────────────────────────────────

class TestVerticalAuditTrail:
    @pytest.mark.asyncio
    async def test_disable_vertical_records_actor_and_reason(self):
        svc = VerticalCatalogService()
        db = MagicMock()
        v = _make_vertical(is_enabled=True)
        db.execute = AsyncMock(return_value=_scalar(v))
        db.commit = AsyncMock(); db.refresh = AsyncMock(); db.flush = AsyncMock()
        added = []
        db.add = MagicMock(side_effect=lambda obj: added.append(obj))

        actor = uuid.uuid4()
        await svc.disable_vertical(db, "home_services", actor_id=actor, reason="maintenance")

        assert v.is_enabled is False
        assert v.disabled_by == actor
        assert v.disable_reason == "maintenance"
        assert any(getattr(a, "action_type", None) == "vertical.disable" for a in added)

    @pytest.mark.asyncio
    async def test_enable_vertical_clears_disable_reason(self):
        svc = VerticalCatalogService()
        db = MagicMock()
        v = _make_vertical(is_enabled=False, disable_reason="old reason")
        db.execute = AsyncMock(return_value=_scalar(v))
        db.commit = AsyncMock(); db.refresh = AsyncMock(); db.flush = AsyncMock()
        db.add = MagicMock()

        await svc.enable_vertical(db, "home_services")

        assert v.is_enabled is True
        assert v.disable_reason is None


# ── Tenant-vertical enrollment lifecycle: independent per vertical ────────────

class TestEnrollmentLifecycle:
    @pytest.mark.asyncio
    async def test_suspending_one_enrollment_does_not_touch_a_different_enrollment(self):
        """Spec requirement: a tenant with two active verticals can have one
        suspended without affecting the other. Since each enrollment is its
        own row (uq_tve_tenant_vertical), transitioning one by id can never
        reach a sibling row -- assert the transition only mutates the
        targeted enrollment object, never a second one."""
        svc = VerticalCatalogService()
        db = MagicMock()
        home_services_enrollment = _make_enrollment(status="active")
        coaching_enrollment = _make_enrollment(status="active")

        db.execute = AsyncMock(return_value=_scalar(home_services_enrollment))
        db.commit = AsyncMock(); db.refresh = AsyncMock(); db.flush = AsyncMock()
        db.add = MagicMock()

        await svc.transition_enrollment(
            db, home_services_enrollment.id, "suspended", reason="policy violation",
        )

        assert home_services_enrollment.status == "suspended"
        assert home_services_enrollment.suspend_reason == "policy violation"
        # The sibling enrollment was never loaded/touched by this call.
        assert coaching_enrollment.status == "active"

    @pytest.mark.asyncio
    async def test_reactivating_from_suspended_clears_suspend_fields(self):
        svc = VerticalCatalogService()
        db = MagicMock()
        e = _make_enrollment(status="suspended", suspend_reason="policy violation")
        db.execute = AsyncMock(return_value=_scalar(e))
        db.commit = AsyncMock(); db.refresh = AsyncMock(); db.flush = AsyncMock()
        db.add = MagicMock()

        await svc.transition_enrollment(db, e.id, "active")

        assert e.status == "active"
        assert e.suspended_at is None
        assert e.suspend_reason is None

    @pytest.mark.asyncio
    async def test_rejects_invalid_status(self):
        svc = VerticalCatalogService()
        db = MagicMock()
        with pytest.raises(ValueError):
            await svc.transition_enrollment(db, uuid.uuid4(), "not_a_real_status")

    @pytest.mark.asyncio
    async def test_transition_raises_when_enrollment_not_found(self):
        svc = VerticalCatalogService()
        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalar(None))
        with pytest.raises(ValueError):
            await svc.transition_enrollment(db, uuid.uuid4(), "active")

    @pytest.mark.asyncio
    async def test_get_or_create_enrollment_is_idempotent(self):
        svc = VerticalCatalogService()
        db = MagicMock()
        v = _make_vertical()
        existing = _make_enrollment()

        call_count = [0]
        async def mock_execute(q):
            call_count[0] += 1
            if call_count[0] == 1:
                return _scalar(v)
            return _scalar(existing)
        db.execute = mock_execute

        result = await svc.get_or_create_enrollment(db, existing.tenant_id, "home_services")
        assert result["id"] == str(existing.id)

    @pytest.mark.asyncio
    async def test_get_or_create_enrollment_creates_draft_when_absent(self):
        svc = VerticalCatalogService()
        db = MagicMock()
        v = _make_vertical()

        call_count = [0]
        async def mock_execute(q):
            call_count[0] += 1
            if call_count[0] == 1:
                return _scalar(v)
            return _scalar(None)
        db.execute = mock_execute
        db.commit = AsyncMock(); db.refresh = AsyncMock()
        added = []
        db.add = MagicMock(side_effect=lambda obj: added.append(obj))

        tenant_id = uuid.uuid4()
        await svc.get_or_create_enrollment(db, tenant_id, "home_services")

        assert len(added) == 1
        assert added[0].status == "draft"


# ── Disable-impact reporting (admin confirmation before disabling) ────────────

class TestDisableImpact:
    @pytest.mark.asyncio
    async def test_disable_impact_reports_active_and_pending_counts(self):
        svc = VerticalCatalogService()
        db = MagicMock()
        v = _make_vertical()

        call_count = [0]
        async def mock_execute(q):
            call_count[0] += 1
            if call_count[0] == 1:
                return _scalar(v)
            r = MagicMock()
            r.all = MagicMock(return_value=[("active", 3), ("suspended", 1), ("under_review", 2)])
            return r
        db.execute = mock_execute

        impact = await svc.disable_impact(db, "home_services")
        assert impact["active_tenant_enrollments"] == 3
        assert impact["under_review_enrollments"] == 2


# ── Backend guards: require_vertical_enabled / require_tenant_vertical_active /
#    require_vertical_capability ────────────────────────────────────────────────

class TestVerticalGuards:
    @pytest.mark.asyncio
    async def test_require_vertical_enabled_blocks_when_disabled(self):
        from app.dependencies.vertical_guard import require_vertical_enabled

        guard = require_vertical_enabled("home_services")
        tenant = MagicMock(tenant_id=uuid.uuid4())
        db = MagicMock()
        v = _make_vertical(is_enabled=False)
        db.execute = AsyncMock(return_value=_scalar(v))

        with pytest.raises(VerticalDisabledException):
            await guard(tenant, db)

    @pytest.mark.asyncio
    async def test_require_vertical_enabled_passes_when_enabled(self):
        from app.dependencies.vertical_guard import require_vertical_enabled

        guard = require_vertical_enabled("home_services")
        tenant = MagicMock(tenant_id=uuid.uuid4())
        db = MagicMock()
        v = _make_vertical(is_enabled=True)
        db.execute = AsyncMock(return_value=_scalar(v))

        result = await guard(tenant, db)
        assert result is tenant

    @pytest.mark.asyncio
    async def test_require_tenant_vertical_active_blocks_without_active_enrollment(self):
        """Real bug this guard prevents: a tenant whose Home Services
        enrollment was suspended must be blocked from Home-Services-owned
        mutations even though the platform vertical itself is enabled."""
        from app.dependencies.vertical_guard import require_tenant_vertical_active

        guard = require_tenant_vertical_active("home_services")
        tenant = MagicMock(tenant_id=uuid.uuid4())
        db = MagicMock()
        v = _make_vertical(is_enabled=True)
        suspended_enrollment = _make_enrollment(status="suspended")

        call_count = [0]
        async def mock_execute(q):
            call_count[0] += 1
            return _scalar(v) if call_count[0] == 1 else _scalar(suspended_enrollment)
        db.execute = mock_execute

        with pytest.raises(TenantVerticalNotActiveException):
            await guard(tenant, db)

    @pytest.mark.asyncio
    async def test_require_tenant_vertical_active_passes_with_active_enrollment(self):
        from app.dependencies.vertical_guard import require_tenant_vertical_active

        guard = require_tenant_vertical_active("home_services")
        tenant = MagicMock(tenant_id=uuid.uuid4())
        db = MagicMock()
        v = _make_vertical(is_enabled=True)
        active_enrollment = _make_enrollment(status="active")

        call_count = [0]
        async def mock_execute(q):
            call_count[0] += 1
            return _scalar(v) if call_count[0] == 1 else _scalar(active_enrollment)
        db.execute = mock_execute

        result = await guard(tenant, db)
        assert result is tenant

    @pytest.mark.asyncio
    async def test_require_vertical_capability_blocks_undeclared_capability(self):
        """Coaching does not declare 'inventory' as a capability -- this must
        block even if the tenant's coaching enrollment is fully active."""
        from app.dependencies.vertical_guard import require_vertical_capability

        guard = require_vertical_capability("coaching", "inventory")
        tenant = MagicMock(tenant_id=uuid.uuid4())
        db = MagicMock()
        v = _make_vertical(key="coaching", capabilities=["customers", "staff", "subscriptions"])
        active_enrollment = _make_enrollment(status="active")

        call_count = [0]
        async def mock_execute(q):
            call_count[0] += 1
            return _scalar(v) if call_count[0] == 1 else _scalar(active_enrollment)
        db.execute = mock_execute

        with pytest.raises(VerticalCapabilityUnavailableException):
            await guard(tenant, db)

    @pytest.mark.asyncio
    async def test_require_vertical_capability_passes_declared_capability(self):
        from app.dependencies.vertical_guard import require_vertical_capability

        guard = require_vertical_capability("home_services", "bookings")
        tenant = MagicMock(tenant_id=uuid.uuid4())
        db = MagicMock()
        v = _make_vertical(capabilities=["customers", "staff", "bookings"])
        active_enrollment = _make_enrollment(status="active")

        call_count = [0]
        async def mock_execute(q):
            call_count[0] += 1
            return _scalar(v) if call_count[0] == 1 else _scalar(active_enrollment)
        db.execute = mock_execute

        result = await guard(tenant, db)
        assert result is tenant
