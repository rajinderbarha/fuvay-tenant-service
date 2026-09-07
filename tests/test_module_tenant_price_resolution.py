"""Deterministic tenant price resolution (TenantCatalogService.resolve_
tenant_price). Precedence: exact type+brand override -> type-only override
-> brand-only override (fixed/non-type-based services) -> tenant default ->
none. Never invents a price, never uses an admin price, never falls back to
another tenant's or vertical's price. No live DB required -- fully mocked.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.admin_catalog.tenant_service import TenantCatalogService


def _scalar(value):
    r = MagicMock()
    r.scalar_one_or_none = MagicMock(return_value=value)
    return r


def _make_ts(**kwargs):
    ts = MagicMock()
    defaults = {
        "id": uuid.uuid4(), "tenant_id": uuid.uuid4(), "master_service_id": uuid.uuid4(),
        "tenant_min_price": None, "tenant_max_price": None,
        # "all" coverage mode short-circuits the coverage gate with no extra
        # query -- these precedence tests are about price resolution, not
        # coverage gating (see TestCoverageGate below for that).
        "type_coverage_mode": "all", "brand_coverage_mode": "all",
    }
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(ts, k, v)
    return ts


def _make_tst(**kwargs):
    t = MagicMock()
    defaults = {"id": uuid.uuid4(), "tenant_min_price": None, "tenant_max_price": None}
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(t, k, v)
    return t


def _make_tsb(**kwargs):
    b = MagicMock()
    defaults = {"id": uuid.uuid4(), "tenant_min_price": None, "tenant_max_price": None}
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(b, k, v)
    return b


def _svc(db, actor_tenant_id=None, actor_role="tenant_owner"):
    # Existing precedence cases use legacy service-wide coverage. The new
    # per-type lookup returns NULL; explicit scoped coverage has real-SQL
    # tests in test_tenant_type_brand_coverage.py.
    legacy_execute = db.execute
    async def execute(statement, *args, **kwargs):
        if str(statement).startswith("SELECT tenant_service_types.brand_coverage"):
            return _scalar(None)
        return await legacy_execute(statement, *args, **kwargs)
    db.execute = AsyncMock(side_effect=execute)
    return TenantCatalogService(db=db, actor_tenant_id=actor_tenant_id, actor_role=actor_role)


class TestPrecedenceOrder:
    @pytest.mark.asyncio
    async def test_type_and_brand_override_is_most_specific(self):
        """Item 15: type-and-brand price is the most specific rule."""
        ts = _make_ts(tenant_min_price=Decimal("800"), tenant_max_price=Decimal("1200"))
        tst = _make_tst(tenant_min_price=Decimal("1200"), tenant_max_price=Decimal("1800"))
        tsb = _make_tsb(tenant_min_price=Decimal("1400"), tenant_max_price=Decimal("2000"))

        db = MagicMock()
        db.execute = AsyncMock(side_effect=[_scalar(ts), _scalar(tsb)])
        svc = _svc(db, actor_tenant_id=ts.tenant_id)

        result = await svc.resolve_tenant_price(ts.id, service_type_id=uuid.uuid4(), brand_id=uuid.uuid4())
        assert result["resolved"] is True
        assert result["source"] == "type_brand_override"
        assert result["minimum_price"] == 1400.0
        assert result["maximum_price"] == 2000.0

    @pytest.mark.asyncio
    async def test_type_price_overrides_tenant_default(self):
        """Item 13."""
        ts = _make_ts(tenant_min_price=Decimal("800"), tenant_max_price=Decimal("1200"))
        tst = _make_tst(tenant_min_price=Decimal("1200"), tenant_max_price=Decimal("1800"))

        db = MagicMock()
        # 1st call: load_tenant_service. 2nd: exact type+brand (none, brand_id
        # not supplied so this query is skipped). 2nd real call: type-only.
        db.execute = AsyncMock(side_effect=[_scalar(ts), _scalar(tst)])
        svc = _svc(db, actor_tenant_id=ts.tenant_id)

        result = await svc.resolve_tenant_price(ts.id, service_type_id=uuid.uuid4())
        assert result["resolved"] is True
        assert result["source"] == "type_override"
        assert result["minimum_price"] == 1200.0

    @pytest.mark.asyncio
    async def test_brand_only_resolves_for_fixed_service(self):
        """Item 14: brand price resolves when applicable (no type)."""
        ts = _make_ts(tenant_min_price=Decimal("800"), tenant_max_price=Decimal("1200"))
        tsb = _make_tsb(tenant_min_price=Decimal("900"), tenant_max_price=Decimal("1300"))

        db = MagicMock()
        db.execute = AsyncMock(side_effect=[_scalar(ts), _scalar(tsb)])
        svc = _svc(db, actor_tenant_id=ts.tenant_id)

        result = await svc.resolve_tenant_price(ts.id, brand_id=uuid.uuid4())
        assert result["resolved"] is True
        assert result["source"] == "brand_override"

    @pytest.mark.asyncio
    async def test_tenant_default_resolves_when_no_overrides(self):
        """Item 12."""
        ts = _make_ts(tenant_min_price=Decimal("800"), tenant_max_price=Decimal("1200"))
        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalar(ts))
        svc = _svc(db, actor_tenant_id=ts.tenant_id)

        result = await svc.resolve_tenant_price(ts.id)
        assert result["resolved"] is True
        assert result["source"] == "tenant_default"
        assert result["minimum_price"] == 800.0

    @pytest.mark.asyncio
    async def test_exact_only_pricing_without_tenant_default(self):
        """Item 16: exact-only pricing works without a tenant default."""
        ts = _make_ts(tenant_min_price=None, tenant_max_price=None)
        tsb = _make_tsb(tenant_min_price=Decimal("800"), tenant_max_price=Decimal("1100"))

        db = MagicMock()
        db.execute = AsyncMock(side_effect=[_scalar(ts), _scalar(tsb)])
        svc = _svc(db, actor_tenant_id=ts.tenant_id)

        result = await svc.resolve_tenant_price(ts.id, service_type_id=uuid.uuid4(), brand_id=uuid.uuid4())
        assert result["resolved"] is True
        assert result["source"] == "type_brand_override"

    @pytest.mark.asyncio
    async def test_missing_price_returns_no_price_result(self):
        """Item 17."""
        ts = _make_ts()  # no default set
        db = MagicMock()
        # load_ts, exact type+brand (miss), type-only (miss), brand-only (miss)
        db.execute = AsyncMock(side_effect=[_scalar(ts), _scalar(None), _scalar(None), _scalar(None)])
        svc = _svc(db, actor_tenant_id=ts.tenant_id)

        result = await svc.resolve_tenant_price(ts.id, service_type_id=uuid.uuid4(), brand_id=uuid.uuid4())
        assert result["resolved"] is False
        assert result["reason"] == "NO_TENANT_PRICE_FOR_COMBINATION"

    @pytest.mark.asyncio
    async def test_unsupported_combination_falls_through_to_default_not_invented(self):
        """A combination with no exact/type override still correctly falls
        back to the tenant default rather than resolving falsely."""
        ts = _make_ts(tenant_min_price=Decimal("500"), tenant_max_price=Decimal("700"))
        db = MagicMock()
        db.execute = AsyncMock(side_effect=[_scalar(ts), _scalar(None), _scalar(None), _scalar(None)])
        svc = _svc(db, actor_tenant_id=ts.tenant_id)

        result = await svc.resolve_tenant_price(ts.id, service_type_id=uuid.uuid4(), brand_id=uuid.uuid4())
        assert result["resolved"] is True
        assert result["source"] == "tenant_default"


class TestCrossTenantIsolation:
    @pytest.mark.asyncio
    async def test_one_tenants_price_never_resolves_for_another_tenant(self):
        """Item 19: cross-tenant access denied outright (404, not a wrong price)."""
        from app.exceptions import NotFoundException
        other_tenant_id = uuid.uuid4()
        ts = _make_ts(tenant_id=other_tenant_id, tenant_min_price=Decimal("800"), tenant_max_price=Decimal("1200"))
        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalar(ts))
        svc = _svc(db, actor_tenant_id=uuid.uuid4(), actor_role="tenant_owner")  # different tenant

        with pytest.raises(NotFoundException):
            await svc.resolve_tenant_price(ts.id)

    @pytest.mark.asyncio
    async def test_platform_admin_can_resolve_any_tenants_price(self):
        """Platform roles legitimately operate cross-tenant (read-only support/audit use)."""
        ts = _make_ts(tenant_min_price=Decimal("800"), tenant_max_price=Decimal("1200"))
        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalar(ts))
        svc = _svc(db, actor_tenant_id=None, actor_role="super_admin")

        result = await svc.resolve_tenant_price(ts.id)
        assert result["resolved"] is True


class TestCoverageGate:
    """Coverage modes (migration 152): ALL / SELECTED_ONLY / ALL_EXCEPT.
    An unsupported combination must never resolve to a price, even if a
    stray override row technically exists for it."""

    @pytest.mark.asyncio
    async def test_all_except_mode_excludes_the_row_present(self):
        """Item 10: 'All except selected' -- the tenant supports every brand
        EXCEPT the ones with a row here."""
        ts = _make_ts(brand_coverage_mode="all_except", tenant_min_price=Decimal("800"), tenant_max_price=Decimal("1200"))
        excluded_brand_id = uuid.uuid4()
        db = MagicMock()
        # load_ts, then brand-supported check (row exists -> excluded)
        db.execute = AsyncMock(side_effect=[_scalar(ts), _scalar(MagicMock())])
        svc = _svc(db, actor_tenant_id=ts.tenant_id)

        result = await svc.resolve_tenant_price(ts.id, brand_id=excluded_brand_id)
        assert result["resolved"] is False
        assert result["reason"] == "COMBINATION_NOT_SUPPORTED"

    @pytest.mark.asyncio
    async def test_all_except_mode_allows_brand_with_no_row(self):
        """A brand NOT in the exclusion rows is supported and falls through
        to tenant-default pricing."""
        ts = _make_ts(brand_coverage_mode="all_except", tenant_min_price=Decimal("800"), tenant_max_price=Decimal("1200"))
        db = MagicMock()
        # load_ts, exclusion-row check (none -> supported), brand-only price
        # override lookup (none) -> falls through to tenant default.
        db.execute = AsyncMock(side_effect=[_scalar(ts), _scalar(None), _scalar(None)])
        svc = _svc(db, actor_tenant_id=ts.tenant_id)

        result = await svc.resolve_tenant_price(ts.id, brand_id=uuid.uuid4())
        assert result["resolved"] is True
        assert result["source"] == "tenant_default"

    @pytest.mark.asyncio
    async def test_selected_only_mode_rejects_brand_without_row(self):
        """Item 9: 'Selected only' -- a brand with no explicit row is NOT
        supported, regardless of any price data."""
        ts = _make_ts(brand_coverage_mode="selected")
        db = MagicMock()
        db.execute = AsyncMock(side_effect=[_scalar(ts), _scalar(None)])  # not in selected set
        svc = _svc(db, actor_tenant_id=ts.tenant_id)

        result = await svc.resolve_tenant_price(ts.id, brand_id=uuid.uuid4())
        assert result["resolved"] is False
        assert result["reason"] == "COMBINATION_NOT_SUPPORTED"

    @pytest.mark.asyncio
    async def test_selected_type_but_excluded_for_that_type_still_blocked(self):
        """Item 11: tenant supports LG only for Split, not Window --
        modeled as: type coverage is 'all' (both types offered), but this
        specific brand has no row for the Window type_id, so brand support
        (evaluated per the combination, not globally) fails for Window+LG
        while succeeding for Split+LG (proven by test_type_and_brand_override
        already passing with an enabled row)."""
        ts = _make_ts(type_coverage_mode="all", brand_coverage_mode="selected")
        window_type_id = uuid.uuid4()
        db = MagicMock()
        db.execute = AsyncMock(side_effect=[_scalar(ts), _scalar(None)])  # no brand row for this combo
        svc = _svc(db, actor_tenant_id=ts.tenant_id)

        result = await svc.resolve_tenant_price(ts.id, service_type_id=window_type_id, brand_id=uuid.uuid4())
        assert result["resolved"] is False
        assert result["reason"] == "COMBINATION_NOT_SUPPORTED"


class TestPublishValidation:
    def test_coverage_membership_queries_are_bounded(self):
        """A selected brand legitimately has one routing row plus one row
        per selected type.  Membership is an existence check, so it must not
        call ``scalar_one_or_none`` on an unbounded multi-row result."""
        import inspect

        type_source = inspect.getsource(TenantCatalogService.is_type_supported)
        brand_source = inspect.getsource(TenantCatalogService.is_brand_supported)
        assert ".limit(1)" in type_source
        assert ".limit(1)" in brand_source

    @pytest.mark.asyncio
    async def test_simple_service_missing_price_and_visit_fee_fails_validation(self):
        ts = _make_ts(requires_type=False, requires_brand=False,
                       tenant_min_price=None, tenant_max_price=None, tenant_visit_fee=None,
                       job_type="repair", job_type_id=None)
        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalar(ts))
        svc = _svc(db, actor_tenant_id=ts.tenant_id)

        result = await svc.validate_for_publish(ts.id)
        assert result["valid"] is False
        assert result["errors"][0]["code"] == "MISSING_TENANT_PRICE"
        assert result["errors"][0]["step"] == "pricing"

    @pytest.mark.asyncio
    async def test_simple_service_with_visit_fee_passes_validation(self):
        """Repair/inspection-workflow services need a visit fee, not a
        final repair price range."""
        ts = _make_ts(requires_type=False, requires_brand=False,
                       tenant_min_price=None, tenant_max_price=None, tenant_visit_fee=Decimal("199"),
                       job_type="repair", job_type_id=None)
        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalar(ts))
        svc = _svc(db, actor_tenant_id=ts.tenant_id)

        result = await svc.validate_for_publish(ts.id)
        assert result["valid"] is True
        assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_simple_service_with_default_price_passes_validation(self):
        ts = _make_ts(requires_type=False, requires_brand=False,
                       tenant_min_price=Decimal("800"), tenant_max_price=Decimal("1200"),
                       job_type="service", job_type_id=None)
        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalar(ts))
        svc = _svc(db, actor_tenant_id=ts.tenant_id)

        result = await svc.validate_for_publish(ts.id)
        assert result["valid"] is True


class TestNoAdminFallback:
    @pytest.mark.asyncio
    async def test_no_admin_price_is_ever_used_as_fallback(self):
        """Item 18: the resolver never queries ServicePricingRule (admin) at
        all -- confirmed structurally, not just by absent test data."""
        import inspect
        src = inspect.getsource(TenantCatalogService.resolve_tenant_price)
        assert "ServicePricingRule" not in src
        assert "_find_admin_pricing_rule" not in src
