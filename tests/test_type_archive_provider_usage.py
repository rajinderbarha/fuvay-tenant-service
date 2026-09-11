from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from app.engines.admin_catalog.types_service import TypesService


def _single(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _many(values):
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    return result


@pytest.mark.asyncio
async def test_archive_type_disables_live_dependencies_and_preserves_rows():
    type_id = uuid.uuid4()
    service_id = uuid.uuid4()
    service_type = SimpleNamespace(
        id=type_id,
        name="Duplicate Split",
        status="inactive",
        is_active=False,
        deleted_at=None,
        updated_at=None,
    )
    tenant_service_id = uuid.uuid4()
    provider_type = SimpleNamespace(is_enabled=True, tenant_service_id=tenant_service_id)
    provider_brand = SimpleNamespace(is_enabled=True, tenant_service_id=tenant_service_id)
    mapping = SimpleNamespace(status="active", updated_at=None)
    service_link = SimpleNamespace(master_service_id=service_id, is_active=True)

    db = MagicMock()
    db.execute = AsyncMock(side_effect=[
        _single(service_type),
        _many([provider_type]),
        _many([provider_brand]),
        _many([mapping]),
        _many([service_link]),
    ])
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    bump_revision = AsyncMock()
    with patch(
        "app.engines.admin_catalog.tenant_setup_revision.bump_tenant_setup_revision",
        bump_revision,
    ):
        result = await TypesService(db).archive_type(
            type_id, "Duplicate master type is no longer needed"
        )

    assert provider_type.is_enabled is False
    assert provider_brand.is_enabled is False
    assert mapping.status == "archived"
    assert mapping.updated_at is not None
    assert service_link.is_active is False
    assert service_type.status == "archived"
    assert service_type.is_active is False
    assert service_type.deleted_at is not None
    bump_revision.assert_awaited_once_with(
        db, service_id, affected_tenant_service_ids={tenant_service_id}
    )
    db.commit.assert_awaited_once()
    assert result == {
        "type_id": str(type_id),
        "status": "archived",
        "provider_usages_disabled": 1,
        "provider_brand_links_disabled": 1,
        "catalog_mappings_archived": 1,
        "service_links_disabled": 1,
    }


@pytest.mark.asyncio
async def test_archive_unused_type_does_not_draft_unrelated_provider_services():
    """An unused duplicate Type can be retired without removing every
    provider of the parent service from customer and Instagram discovery."""
    type_id = uuid.uuid4()
    service_id = uuid.uuid4()
    service_type = SimpleNamespace(
        id=type_id, name="Unused duplicate", status="inactive", is_active=False,
        deleted_at=None, updated_at=None,
    )
    service_link = SimpleNamespace(master_service_id=service_id, is_active=True)

    db = MagicMock()
    db.execute = AsyncMock(side_effect=[
        _single(service_type), _many([]), _many([]), _many([]), _many([service_link]),
    ])
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    bump_revision = AsyncMock()
    with patch(
        "app.engines.admin_catalog.tenant_setup_revision.bump_tenant_setup_revision",
        bump_revision,
    ):
        await TypesService(db).archive_type(
            type_id, "Unused duplicate type is no longer needed"
        )

    bump_revision.assert_awaited_once_with(
        db, service_id, affected_tenant_service_ids=set()
    )


def test_type_archive_dialog_explains_automatic_cleanup():
    page = open(
        "frontend/super-admin/app/admin/types-brands/page.tsx",
        encoding="utf-8",
    ).read()
    assert "disabled in provider service configurations" in page
    assert "Historical bookings and jobs remain unchanged" in page

