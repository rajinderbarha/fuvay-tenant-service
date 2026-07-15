"""MODULE-L5-23 — package-based storage quota, home services exempt.

Media upload enforced a hardcoded 5GB quota for every tenant, ignoring the
package the provider chose. Per product: home services is exempt (unlimited);
every other vertical is capped by its chosen package's quota
(tenant_limits.max_storage_gb, written on package approval).
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.media.service import MediaService, DEFAULT_STORAGE_QUOTA_GB, _GB


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
    svc.db = db
    return svc


class TestStorageQuota:
    @pytest.mark.asyncio
    async def test_home_services_is_exempt(self):
        svc = _svc_with_vertical_and_limit("home_services", 2)
        q = await svc._effective_storage_quota_bytes(uuid.uuid4())
        assert q is None, "home services must be unlimited"

    @pytest.mark.asyncio
    async def test_home_services_case_insensitive(self):
        svc = _svc_with_vertical_and_limit("Home_Services", None)
        assert await svc._effective_storage_quota_bytes(uuid.uuid4()) is None

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
