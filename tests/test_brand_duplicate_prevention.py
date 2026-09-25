"""Regression tests for canonical, case-insensitive brand identity."""
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.admin_catalog.brand_service import BrandService, normalize_brand_name
from app.exceptions import ServiceOSException


@pytest.mark.parametrize("typed", ["lg", "LG", " L.G. "])
@pytest.mark.asyncio
async def test_create_rejects_normalized_duplicate_even_when_force_is_supplied(typed):
    existing = SimpleNamespace(id=uuid.uuid4(), name="LG")
    db = MagicMock()
    db.scalar = AsyncMock(return_value=existing)

    with pytest.raises(ServiceOSException) as error:
        await BrandService(db).create_brand({"name": typed, "force": True})

    assert error.value.error_code == "BRAND_DUPLICATE"
    assert error.value.status_code == 409
    assert error.value.context["existing_brand_id"] == str(existing.id)
    assert normalize_brand_name(typed) == "lg"
    db.add.assert_not_called()


def test_migration_retires_lowercase_lg_and_adds_database_guard():
    migration = (Path(__file__).parents[1] / "alembic" / "versions" /
                 "377_prevent_duplicate_brand_names.py").read_text(encoding="utf-8")
    assert "lower(btrim(name)) = 'lg'" in migration
    assert "replacement_brand_id = target_id" in migration
    assert "uq_brands_live_normalized_name" in migration
    assert "unique=True" in migration
