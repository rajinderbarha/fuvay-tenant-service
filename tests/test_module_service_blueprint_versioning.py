"""Service Blueprint Versioning (migration 153) -- the last of the 4 backend
contracts identified missing in the frontend wizard's preflight audit.
Structural admin edits (job_type/requires_type/requires_brand/pricing_model/
is_active) publish a new version and supersede the previous one; cosmetic
edits (name/description/icons) never do. Tenants track which version their
setup was built against, and get an honest, fail-closed "update required"
signal rather than silently being assumed current. No live DB required.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.admin_catalog.service import AdminCatalogService
from app.engines.admin_catalog.tenant_service import TenantCatalogService


def _scalar(value):
    r = MagicMock()
    r.scalar_one_or_none = MagicMock(return_value=value)
    return r


def _make_svc(**kwargs):
    v = MagicMock()
    defaults = {
        "id": uuid.uuid4(), "job_type": "repair", "is_type_required": False,
        "is_brand_required": True, "pricing_model": "fixed", "is_active": True,
    }
    defaults.update(kwargs)
    for k, val in defaults.items():
        setattr(v, k, val)
    return v


def _make_version(**kwargs):
    v = MagicMock()
    defaults = {"id": uuid.uuid4(), "version_number": 1, "status": "published", "change_summary": None}
    defaults.update(kwargs)
    for k, val in defaults.items():
        setattr(v, k, val)
    return v


class TestStructuralChangeDetection:
    @pytest.mark.asyncio
    async def test_no_new_version_when_only_cosmetic_fields_change(self):
        svc = _make_svc()
        before = {"job_type": svc.job_type, "requires_type": svc.is_type_required,
                   "requires_brand": svc.is_brand_required, "pricing_model": svc.pricing_model,
                   "is_active": svc.is_active}
        # Nothing structural changed -- e.g. only service_name was updated.
        admin_svc = AdminCatalogService(db=MagicMock())
        result = await admin_svc._publish_new_blueprint_version_if_structural_change(svc, before)
        assert result is None

    @pytest.mark.asyncio
    async def test_new_version_published_when_requires_brand_changes(self):
        svc = _make_svc(is_brand_required=False)  # changed from True -> False
        before = {"job_type": "repair", "requires_type": False,
                   "requires_brand": True, "pricing_model": "fixed", "is_active": True}

        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalar(None))  # no prior version
        db.add = MagicMock()
        db.flush = AsyncMock()
        admin_svc = AdminCatalogService(db=db)

        result = await admin_svc._publish_new_blueprint_version_if_structural_change(svc, before)
        assert result is not None
        assert result.version_number == 1
        assert "requires_brand" in result.change_summary

    @pytest.mark.asyncio
    async def test_version_number_increments_and_supersedes_previous(self):
        svc = _make_svc(pricing_model="range")  # changed from "fixed"
        before = {"job_type": "repair", "requires_type": False,
                   "requires_brand": True, "pricing_model": "fixed", "is_active": True}
        prior_version = _make_version(version_number=3, status="published")

        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalar(prior_version))
        db.add = MagicMock()
        db.flush = AsyncMock()
        admin_svc = AdminCatalogService(db=db)

        result = await admin_svc._publish_new_blueprint_version_if_structural_change(svc, before)
        assert result.version_number == 4
        assert prior_version.status == "superseded"


class TestTenantUpdateRequiredDetection:
    @pytest.mark.asyncio
    async def test_up_to_date_when_versions_match(self):
        ts = MagicMock()
        latest_id = uuid.uuid4()
        ts.master_service_id = uuid.uuid4()
        ts.blueprint_version_id = latest_id
        latest = _make_version(id=latest_id, version_number=2)

        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalar(latest))
        svc = TenantCatalogService(db=db, actor_tenant_id=None, actor_role="super_admin")
        svc._load_tenant_service = AsyncMock(return_value=ts)

        result = await svc.get_blueprint_update_status(ts.id)
        assert result["update_required"] is False
        assert result["current_version"] == 2

    @pytest.mark.asyncio
    async def test_legacy_setup_with_no_version_fails_closed_to_update_required(self):
        """Pre-versioning tenant setups (blueprint_version_id=NULL) must
        never be silently treated as up to date."""
        ts = MagicMock()
        ts.master_service_id = uuid.uuid4()
        ts.blueprint_version_id = None
        latest = _make_version(version_number=3)

        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalar(latest))
        svc = TenantCatalogService(db=db, actor_tenant_id=None, actor_role="super_admin")
        svc._load_tenant_service = AsyncMock(return_value=ts)

        result = await svc.get_blueprint_update_status(ts.id)
        assert result["update_required"] is True
        assert result["current_version"] is None

    @pytest.mark.asyncio
    async def test_outdated_version_reports_changelog(self):
        ts = MagicMock()
        ts.master_service_id = uuid.uuid4()
        old_version_id = uuid.uuid4()
        ts.blueprint_version_id = old_version_id
        latest = _make_version(version_number=3)
        current = _make_version(id=old_version_id, version_number=1)

        call_count = [0]
        async def mock_execute(q):
            call_count[0] += 1
            if call_count[0] == 1:
                return _scalar(latest)
            if call_count[0] == 2:
                return _scalar(current)
            r = MagicMock()
            r.__iter__ = lambda self: iter([("requires_brand: True -> False",), ("pricing_model: fixed -> range",)])
            return r

        db = MagicMock()
        db.execute = mock_execute
        svc = TenantCatalogService(db=db, actor_tenant_id=None, actor_role="super_admin")
        svc._load_tenant_service = AsyncMock(return_value=ts)

        result = await svc.get_blueprint_update_status(ts.id)
        assert result["update_required"] is True
        assert result["current_version"] == 1
        assert result["latest_version"] == 3
        assert len(result["changes"]) == 2

    @pytest.mark.asyncio
    async def test_no_blueprint_version_exists_at_all_is_not_flagged(self):
        """A master service that predates blueprint versioning entirely (no
        rows in service_blueprint_versions for it) can't be diffed -- must
        not falsely claim update_required."""
        ts = MagicMock()
        ts.master_service_id = uuid.uuid4()
        ts.blueprint_version_id = None

        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalar(None))  # no versions at all
        svc = TenantCatalogService(db=db, actor_tenant_id=None, actor_role="super_admin")
        svc._load_tenant_service = AsyncMock(return_value=ts)

        result = await svc.get_blueprint_update_status(ts.id)
        assert result["update_required"] is False
        assert result["latest_version"] is None
