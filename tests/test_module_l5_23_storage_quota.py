"""MODULE-L5-23 — tenant media storage quota enforcement.

Home Services providers receive a fixed shared 1 GB allowance. Other verticals
continue to use the quota written by their approved package.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.media.service import (
    MediaService,
    DEFAULT_STORAGE_QUOTA_GB,
    HOME_SERVICES_STORAGE_QUOTA_GB,
    _GB,
)
from app.exceptions import ServiceOSException


def _svc_with_vertical_and_limit(vertical, max_storage_gb):
    svc = MediaService.__new__(MediaService)
    db = MagicMock()

    async def _scalar(stmt):
        # First scalar() call resolves the vertical; second resolves the limits.
        # We disambiguate by a tiny state machine on the mock.
        raise AssertionError("unused")

    # scalar is called twice: once for vertical, once for TenantLimits row.
    limits = MagicMock()
    limits.max_storage_gb = max_storage_gb
    db.scalar = AsyncMock(side_effect=[vertical, (limits if max_storage_gb is not None else None)])
    db.execute = AsyncMock()
    svc.db = db
    return svc


class TestStorageQuota:
    @pytest.mark.asyncio
    async def test_home_services_has_fixed_one_gb_limit(self):
        svc = _svc_with_vertical_and_limit("home_services", 2)
        q = await svc._effective_storage_quota_bytes(uuid.uuid4())
        assert q == HOME_SERVICES_STORAGE_QUOTA_GB * _GB
        assert svc.db.scalar.await_count == 1

    @pytest.mark.asyncio
    async def test_home_services_case_insensitive(self):
        svc = _svc_with_vertical_and_limit("Home_Services", None)
        assert await svc._effective_storage_quota_bytes(uuid.uuid4()) == _GB

    @pytest.mark.asyncio
    async def test_other_vertical_uses_package_quota(self):
        svc = _svc_with_vertical_and_limit("coaching", 3)
        q = await svc._effective_storage_quota_bytes(uuid.uuid4())
        assert q == int(3 * _GB)

    @pytest.mark.asyncio
    async def test_other_vertical_without_limit_falls_back_to_default(self):
        svc = _svc_with_vertical_and_limit("real_estate", None)
        q = await svc._effective_storage_quota_bytes(uuid.uuid4())
        assert q == int(DEFAULT_STORAGE_QUOTA_GB * _GB)

    @pytest.mark.asyncio
    async def test_capacity_guard_requires_deletion_when_upload_would_exceed_limit(self):
        tenant_id = uuid.uuid4()
        svc = _svc_with_vertical_and_limit("home_services", None)
        svc._tenant_storage_usage = AsyncMock(return_value=(_GB - 100, 8))

        with pytest.raises(ServiceOSException) as error:
            await svc.assert_storage_capacity(tenant_id, 101)

        assert error.value.error_code == "PLAN_LIMIT_EXCEEDED"
        assert error.value.blocking_rule == "tenant_media_storage_quota_exceeded"
        assert error.value.context["bytes_to_free"] == 1
        assert "Delete unused media files" in error.value.detail
        svc.db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_quota_payload_drives_warning_and_full_dashboard_states(self):
        tenant_id = uuid.uuid4()
        svc = _svc_with_vertical_and_limit("home_services", None)
        svc.actor_role = "tenant_owner"
        svc.actor_tenant_id = tenant_id
        svc._tenant_storage_usage = AsyncMock(return_value=(_GB, 12))

        result = await svc.get_storage_quota(tenant_id)

        assert result["quota_bytes"] == _GB
        assert result["usage_pct"] == 100.0
        assert result["bytes_remaining"] == 0
        assert result["bytes_over_limit"] == 0
        assert result["is_full"] is True
        assert result["can_upload"] is False
        assert result["action_required"] is True
        assert result["alert"] is True
