"""Generic Catalog Dimension Engine (migration 154) -- backs the approved
Admin Catalog page's Dimensions tab + right-panel readiness. Closes the
largest gap from that page's preflight audit: Type and Brand were hardcoded
tables with no way to add a future dimension (Capacity/Size/Model/Delivery
Mode) through configuration. Structural flags only -- no monetary fields.
Fully mocked; a live DB check confirms the seed + a real readiness call.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.admin_catalog.dimension_service import CatalogDimensionService, SJD_FLAGS
from app.exceptions import ServiceOSException


def _scalar(value):
    r = MagicMock()
    r.scalar_one_or_none = MagicMock(return_value=value)
    return r


def _make_dim(**kwargs):
    d = MagicMock()
    defaults = {"id": uuid.uuid4(), "key": "capacity", "name": "Capacity",
                "data_type": "single_select", "legacy_source": None, "is_active": True,
                "display_order": 3, "description": None}
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(d, k, v)
    d.to_dict = MagicMock(return_value={"id": str(defaults["id"]), "key": defaults["key"],
                                         "name": defaults["name"], "legacy_source": defaults["legacy_source"]})
    return d


class TestMonetaryFieldRejection:
    """The platform's admin-never-sets-price rule, enforced structurally."""

    def test_sjd_flags_contains_no_monetary_amount_keys(self):
        # `affects_price` is an allowed boolean flag ("this dimension MAY
        # affect the tenant's price") -- it holds no amount. Everything else
        # must not even hint at a monetary VALUE.
        forbidden = ("amount", "cost", "min_", "max_", "_fee", "fee_")
        for flag in SJD_FLAGS:
            assert not any(f in flag for f in forbidden), f"'{flag}' looks like a monetary amount"
        assert "affects_price" in SJD_FLAGS  # the one allowed price-adjacent flag, boolean only

    @pytest.mark.asyncio
    async def test_set_dimension_rejects_unknown_or_monetary_flags(self):
        svc = CatalogDimensionService(db=MagicMock())
        svc._load_dimension = AsyncMock(return_value=_make_dim())
        with pytest.raises(ServiceOSException) as exc:
            await svc.set_service_job_dimension(uuid.uuid4(), uuid.uuid4(), uuid.uuid4(),
                                                {"enabled": True, "base_price": 500})
        assert exc.value.error_code == "INVALID_DIMENSION_FLAGS"


class TestGenericDimensionCreation:
    @pytest.mark.asyncio
    async def test_create_dimension_rejects_bad_data_type(self):
        svc = CatalogDimensionService(db=MagicMock())
        svc.db.execute = AsyncMock(return_value=_scalar(None))
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_dimension({"key": "capacity", "name": "Capacity", "data_type": "nonsense"})
        assert exc.value.error_code == "INVALID_DATA_TYPE"

    @pytest.mark.asyncio
    async def test_create_dimension_rejects_duplicate_key(self):
        svc = CatalogDimensionService(db=MagicMock())
        svc.db.execute = AsyncMock(return_value=_scalar(_make_dim(key="type")))
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_dimension({"key": "type", "name": "Type"})
        assert exc.value.error_code == "DIMENSION_KEY_EXISTS"

    @pytest.mark.asyncio
    async def test_cannot_add_values_to_a_legacy_dimension(self):
        """Type/Brand values live in service_types/brands, not here."""
        svc = CatalogDimensionService(db=MagicMock())
        svc._load_dimension = AsyncMock(return_value=_make_dim(key="brand", legacy_source="brands"))
        with pytest.raises(ServiceOSException) as exc:
            await svc.add_value(uuid.uuid4(), {"code": "lg", "label": "LG"})
        assert exc.value.error_code == "LEGACY_DIMENSION_VALUE_READONLY"


class TestServiceJobDimensionConfig:
    @pytest.mark.asyncio
    async def test_unconfigured_dimension_returns_disabled_defaults(self):
        svc = CatalogDimensionService(db=MagicMock())
        dim = _make_dim()

        dims_result = MagicMock()
        dims_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[dim])))
        cfg_result = MagicMock()
        cfg_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))

        call = [0]
        async def mock_execute(q):
            call[0] += 1
            return dims_result if call[0] == 1 else cfg_result
        svc.db.execute = mock_execute
        svc._value_count = AsyncMock(return_value=0)

        result = await svc.get_service_job_dimensions(uuid.uuid4(), uuid.uuid4())
        assert result["dimensions"][0]["config"]["enabled"] is False
        assert result["dimensions"][0]["value_count"] == 0


class TestBlueprintReadinessLive:
    async def test_readiness_returns_percentage_and_checklist_shape(self):
        """Live DB smoke test: readiness must return the exact right-panel
        contract (percent + checks[] + actions_required[] + affected count)."""
        import asyncio
        from app.database import get_session_factory, init_db
        from sqlalchemy import text

        await init_db()
        factory = get_session_factory()
        async with factory() as db:
            ms_id = (await db.execute(text(
                "SELECT id FROM master_services WHERE deleted_at IS NULL LIMIT 1"))).scalar()
            if not ms_id:
                return  # no data in this environment
            svc = CatalogDimensionService(db=db)
            result = await svc.get_blueprint_readiness(ms_id, None)
            assert isinstance(result["percent"], int)
            assert 0 <= result["percent"] <= 100
            assert isinstance(result["checks"], list) and len(result["checks"]) == 4
            for c in result["checks"]:
                assert "label" in c and "passed" in c
            assert isinstance(result["actions_required"], list)
            assert "tenant_setups_affected" in result

    async def test_seeded_dimensions_exist(self):
        import asyncio
        from app.database import get_session_factory, init_db
        from sqlalchemy import text

        await init_db()
        factory = get_session_factory()
        async with factory() as db:
            keys = [r[0] for r in (await db.execute(text(
                "SELECT key FROM catalog_dimensions ORDER BY display_order"))).fetchall()]
            assert "type" in keys and "brand" in keys
