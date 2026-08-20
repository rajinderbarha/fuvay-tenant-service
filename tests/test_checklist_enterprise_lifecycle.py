from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.checklist_catalog import constants as c
from app.engines.checklist_catalog import service as svc
from app.exceptions import ServiceOSException


@pytest.mark.asyncio
async def test_retire_requires_reason():
    with pytest.raises(ServiceOSException) as exc:
        await svc.archive_template(AsyncMock(), MagicMock(), archived_by=None, reason="x")
    assert exc.value.error_code == "CHECKLIST_RETIRE_REASON_REQUIRED"


@pytest.mark.asyncio
async def test_retire_disables_active_mappings_but_preserves_rows():
    template = MagicMock(id=uuid.uuid4(), status="active")
    active = MagicMock(status=c.MAPPING_STATUS_ACTIVE)
    disabled = MagicMock(status=c.MAPPING_STATUS_DISABLED)
    result = MagicMock()
    result.scalars.return_value.all.return_value = [active]
    db = AsyncMock(); db.execute = AsyncMock(return_value=result); db.add = MagicMock(); db.flush = AsyncMock()
    retired = await svc.archive_template(db, template, archived_by=None, reason="Superseded by safety checklist")
    assert retired.status == c.TEMPLATE_STATUS_ARCHIVED
    assert active.status == c.MAPPING_STATUS_DISABLED
    assert active.disable_reason.startswith("Template retired:")
    assert disabled.status == c.MAPPING_STATUS_DISABLED


@pytest.mark.asyncio
async def test_restore_keeps_mappings_explicitly_disabled():
    template = MagicMock(status=c.TEMPLATE_STATUS_ARCHIVED, archived_at=MagicMock(), archived_by=uuid.uuid4(), archive_reason="old")
    db = AsyncMock(); db.add = MagicMock(); db.flush = AsyncMock()
    restored = await svc.restore_template(db, template, restored_by=uuid.uuid4(), reason="Required for new workflow")
    assert restored.status == c.TEMPLATE_STATUS_ACTIVE
    assert restored.archived_at is None
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_disable_mapping_requires_reason():
    with pytest.raises(ServiceOSException) as exc:
        await svc.disable_mapping(AsyncMock(), MagicMock(), None, "")
    assert exc.value.error_code == "CHECKLIST_MAPPING_DISABLE_REASON_REQUIRED"


@pytest.mark.asyncio
async def test_enable_mapping_rejects_retired_template():
    mapping = MagicMock(checklist_template_version_id=uuid.uuid4())
    version = MagicMock(status=c.VERSION_PUBLISHED, checklist_template_id=uuid.uuid4())
    template = MagicMock(status=c.TEMPLATE_STATUS_ARCHIVED)
    db = AsyncMock(); db.get = AsyncMock(side_effect=[version, template])
    with pytest.raises(ServiceOSException):
        await svc.enable_mapping(db, mapping, None)


@pytest.mark.asyncio
async def test_enable_mapping_clears_disable_metadata():
    mapping = MagicMock(checklist_template_version_id=uuid.uuid4(), status=c.MAPPING_STATUS_DISABLED,
                        disabled_at=MagicMock(), disable_reason="old")
    version = MagicMock(status=c.VERSION_PUBLISHED, checklist_template_id=uuid.uuid4())
    template = MagicMock(status=c.TEMPLATE_STATUS_ACTIVE)
    db = AsyncMock(); db.get = AsyncMock(side_effect=[version, template]); db.add = MagicMock(); db.flush = AsyncMock()
    enabled = await svc.enable_mapping(db, mapping, uuid.uuid4())
    assert enabled.status == c.MAPPING_STATUS_ACTIVE
    assert enabled.disabled_at is None
    assert enabled.disable_reason is None


def test_enterprise_export_registry_supports_checklist_resources():
    from app.engines.enterprise_grid.filter_registry import EnterpriseFilterRegistry
    from app.engines.enterprise_grid.resource_adapters import is_runtime_supported
    assert "archive_reason" in EnterpriseFilterRegistry.get_allowed_export_fields("admin_checklist_templates")
    assert "disable_reason" in EnterpriseFilterRegistry.get_allowed_export_fields("admin_checklist_mappings")
    assert is_runtime_supported("admin_checklist_templates")
    assert is_runtime_supported("admin_checklist_mappings")
