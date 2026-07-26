"""Admin Job Type CRUD + Blueprint Impact Report -- backs the approved Admin
Catalog page's "Add Job Type" action and right-panel "Version & impact".
Mocked unit tests + a live DB smoke test for the impact report shape.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.admin_catalog.job_type_service import JobTypeService, RUNTIME_KNOWN_KEYS, EDITABLE_FIELDS
from app.engines.admin_catalog.blueprint_impact_service import BlueprintImpactService
from app.exceptions import ServiceOSException


def _scalar(value):
    r = MagicMock()
    r.scalar_one_or_none = MagicMock(return_value=value)
    return r


def _make_jt(**kwargs):
    jt = MagicMock()
    defaults = {"id": uuid.uuid4(), "key": "installation", "label": "Installation",
                "description": None, "requires_assessment": False, "allows_quote": False,
                "requires_checklist": True, "is_active": True, "display_order": 4}
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(jt, k, v)
    return jt


class TestJobTypeCrud:
    def test_editable_fields_have_no_monetary_keys(self):
        for f in EDITABLE_FIELDS:
            assert not any(m in f for m in ("price", "fee", "amount", "cost"))

    @pytest.mark.asyncio
    async def test_create_rejects_missing_key_or_label(self):
        svc = JobTypeService(db=MagicMock())
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_job_type({"label": "No key"})
        assert exc.value.error_code == "JOB_TYPE_KEY_LABEL_REQUIRED"

    @pytest.mark.asyncio
    async def test_create_rejects_duplicate_key(self):
        svc = JobTypeService(db=MagicMock())
        svc.db.execute = AsyncMock(return_value=_scalar(_make_jt(key="repair")))
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_job_type({"key": "repair", "label": "Repair"})
        assert exc.value.error_code == "JOB_TYPE_KEY_EXISTS"

    @pytest.mark.asyncio
    async def test_known_key_reports_runtime_supported_true(self):
        svc = JobTypeService(db=MagicMock())
        jt = _make_jt(key="installation")
        d = svc._to_dict(jt)
        assert d["runtime_supported"] is True

    @pytest.mark.asyncio
    async def test_novel_key_reports_runtime_supported_false(self):
        """Honest signal: a brand-new key isn't wired into the field-ops
        transition graph, so it must NOT claim full runtime support."""
        svc = JobTypeService(db=MagicMock())
        jt = _make_jt(key="relocation")  # not in RUNTIME_KNOWN_KEYS
        d = svc._to_dict(jt)
        assert d["runtime_supported"] is False
        assert "relocation" not in RUNTIME_KNOWN_KEYS


class TestBlueprintImpactReport:
    @pytest.mark.asyncio
    async def test_reports_structural_change_between_versions(self):
        svc = BlueprintImpactService(db=MagicMock())
        master = MagicMock(id=uuid.uuid4())
        latest = MagicMock(version_number=2, change_summary="requires_brand: True -> False",
                           snapshot={"job_type": "service", "requires_type": False,
                                     "requires_brand": False, "pricing_model": "fixed", "is_active": True},
                           published_at=None, id=uuid.uuid4())
        previous = MagicMock(version_number=1,
                             snapshot={"job_type": "service", "requires_type": False,
                                       "requires_brand": True, "pricing_model": "fixed", "is_active": True})

        versions_result = MagicMock()
        versions_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[latest, previous])))

        call = [0]
        async def mock_execute(q):
            call[0] += 1
            if call[0] == 1:
                return _scalar(master)         # load master service
            if call[0] == 2:
                return versions_result          # last 2 versions
            r = MagicMock(); r.scalar = MagicMock(return_value=3); return r  # affected + need_review counts
        svc.db.execute = mock_execute

        result = await svc.get_impact_report(master.id)
        assert result["current_version"] == 2
        assert result["previous_version"] == 1
        # requires_brand True -> False == Brand dimension removed from setup.
        assert "Brand" in result["removed_dimensions"]
        assert any(c["field"] == "requires_brand" for c in result["changed_requirements"])

    async def test_impact_report_live_shape(self):
        import asyncio
        from app.database import get_session_factory, init_db
        from sqlalchemy import text
        await init_db()
        factory = get_session_factory()
        async with factory() as db:
            ms_id = (await db.execute(text(
                "SELECT id FROM master_services WHERE deleted_at IS NULL LIMIT 1"))).scalar()
            if not ms_id:
                return
            result = await BlueprintImpactService(db).get_impact_report(ms_id)
            for key in ("current_version", "added_dimensions", "removed_dimensions",
                        "changed_requirements", "tenants_affected", "setups_need_review"):
                assert key in result
            assert isinstance(result["changed_requirements"], list)
