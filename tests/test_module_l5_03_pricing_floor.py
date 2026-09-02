"""MODULE-L5-03 — tenant pricing-floor enforcement (the platform-floor bypass fix)."""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.engines.admin_catalog.tenant_service import TenantCatalogService
from app.exceptions import ServiceOSException
import e2e.pricing_floor_guard as guard


def _svc(min_price=None, max_price=None):
    return SimpleNamespace(min_price=min_price, max_price=max_price)


def _validator():
    # _validate_price_overrides is a pure method (no DB use).
    inst = TenantCatalogService.__new__(TenantCatalogService)
    return inst._validate_price_overrides


def test_zero_non_fee_price_is_rejected():
    v = _validator()
    with pytest.raises(ServiceOSException) as e:
        v(_svc(min_price=Decimal("100")), None, Decimal("0"), None, None)
    assert e.value.error_code == "TENANT_PRICE_INVALID"


def test_legacy_admin_min_does_not_constrain_provider_price():
    v = _validator()
    v(_svc(min_price=Decimal("100")), None, Decimal("50"), None, None)


def test_legacy_admin_max_does_not_constrain_provider_price():
    v = _validator()
    v(_svc(max_price=Decimal("100")), None, None, Decimal("150"), None)


def test_negative_is_rejected():
    v = _validator()
    with pytest.raises(ServiceOSException) as e:
        v(_svc(min_price=None), None, None, None, Decimal("-1"))
    assert e.value.error_code == "TENANT_PRICE_NEGATIVE"


def test_valid_at_or_above_floor_passes():
    v = _validator()
    v(_svc(min_price=Decimal("100"), max_price=Decimal("500")),
      Decimal("200"), Decimal("100"), Decimal("500"), Decimal("0"))  # equal-to-floor min ok; 0 visit fee ok (no floor)


def test_inverted_provider_range_is_rejected():
    v = _validator()
    with pytest.raises(ServiceOSException) as e:
        v(_svc(), None, Decimal("500"), Decimal("100"), None)
    assert e.value.error_code == "INVALID_PRICE_RANGE"


def test_guard_passes_on_real_repo():
    assert guard.check() == []


# ── Cross-tenant catalog isolation hardening (_assert_tenant_owns_ts) ──────────

import uuid as _uuid
from app.exceptions import NotFoundException


def _svc_with_actor(role, tenant_id):
    inst = TenantCatalogService.__new__(TenantCatalogService)
    inst.actor_role = role
    inst.actor_tenant_id = tenant_id
    return inst


def _ts(tenant_id):
    return SimpleNamespace(id=_uuid.uuid4(), tenant_id=tenant_id)


def test_technician_confined_to_own_tenant():
    """Regression: technician was NOT in the old ('tenant_owner','staff')
    allowlist, so the ownership check failed open for it."""
    a, b = _uuid.uuid4(), _uuid.uuid4()
    svc = _svc_with_actor("technician", a)
    with pytest.raises(NotFoundException):
        svc._assert_tenant_owns_ts(_ts(b))          # other tenant -> denied
    svc._assert_tenant_owns_ts(_ts(a))              # own tenant -> allowed


def test_tenant_owner_still_confined():
    a, b = _uuid.uuid4(), _uuid.uuid4()
    with pytest.raises(NotFoundException):
        _svc_with_actor("tenant_owner", a)._assert_tenant_owns_ts(_ts(b))


def test_platform_role_crosses_tenants():
    # super_admin has tenant_id=None -> not confined.
    _svc_with_actor("super_admin", None)._assert_tenant_owns_ts(_ts(_uuid.uuid4()))
