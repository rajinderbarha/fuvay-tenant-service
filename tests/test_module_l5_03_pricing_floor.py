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


def test_zero_below_floor_is_rejected():
    """The original bug: Decimal('0') is falsy and skipped the floor check."""
    v = _validator()
    with pytest.raises(ServiceOSException) as e:
        v(_svc(min_price=Decimal("100")), None, Decimal("0"), None, None)
    assert e.value.error_code == "TENANT_PRICE_BELOW_ADMIN_MIN"


def test_below_floor_is_rejected():
    v = _validator()
    with pytest.raises(ServiceOSException) as e:
        v(_svc(min_price=Decimal("100")), None, Decimal("50"), None, None)
    assert e.value.error_code == "TENANT_PRICE_BELOW_ADMIN_MIN"


def test_above_ceiling_is_rejected():
    v = _validator()
    with pytest.raises(ServiceOSException) as e:
        v(_svc(max_price=Decimal("100")), None, None, Decimal("150"), None)
    assert e.value.error_code == "TENANT_PRICE_ABOVE_ADMIN_MAX"


def test_negative_is_rejected():
    v = _validator()
    with pytest.raises(ServiceOSException) as e:
        v(_svc(min_price=None), None, None, None, Decimal("-1"))
    assert e.value.error_code == "TENANT_PRICE_NEGATIVE"


def test_valid_at_or_above_floor_passes():
    v = _validator()
    v(_svc(min_price=Decimal("100"), max_price=Decimal("500")),
      Decimal("200"), Decimal("100"), Decimal("500"), Decimal("0"))  # equal-to-floor min ok; 0 visit fee ok (no floor)


def test_guard_passes_on_real_repo():
    assert guard.check() == []
