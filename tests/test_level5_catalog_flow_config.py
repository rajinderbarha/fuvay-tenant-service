"""LEVEL-5 REMEDIATION (2026-08-01, G6) — real functional tests for
GET /v1/catalog/master/flow/config.

The pre-existing tests for this endpoint (tests/test_sprint38_universal_catalog.py)
only asserted that certain substrings ("steps", "finance_model", "service_booking")
appear somewhere in the router's source file — they never actually called the
handler, so they never caught the real defect: `steps` was referenced before
assignment in every code path except the "no category found" fallback,
guaranteeing an UnboundLocalError (HTTP 500) on any request that actually
resolved a category. These tests call the handler directly against mocked
service/db objects and assert real response content, per the requirement not
to "merely test that the route exists."
"""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.admin_catalog.customer_router import get_flow_config


def _id():
    return uuid.uuid4()


def make_request():
    r = MagicMock()
    r.state.request_id = "test-req"
    return r


def make_service(cat_data=None, svc_data=None, canonical=None):
    """Builds a mocked AdminCatalogService + patches _resolve_canonical_flow_flags."""
    svc = MagicMock()
    svc.get_category = AsyncMock(return_value=cat_data)
    svc.get_master_service = AsyncMock(return_value=svc_data)
    svc.db = MagicMock()
    return svc


def base_category(**overrides):
    d = {
        "category_id": str(_id()),
        "name": "AC & Cooling",
        "is_active": True,
        "is_customer_visible": True,
        "customer_flow_type": "service_booking",
        "finance_model": "direct_payment",
        "requires_issue_type": False,
        "requires_brand": False,
        "requires_service_option": False,
        "requires_schedule": True,
        "requires_location": True,
    }
    d.update(overrides)
    return d


def base_service(category_id, **overrides):
    d = {
        "service_id": str(_id()),
        "category_id": category_id,
        "service_name": "AC Repair",
        "requires_issue_type": False,
        "is_brand_required": False,
        "is_type_required": False,
        "requires_schedule": True,
        "requires_address": True,
        "is_active": True,
    }
    d.update(overrides)
    return d


async def _call(category_id=None, service_id=None, svc=None, canonical=None, monkeypatch=None):
    """Invokes get_flow_config with _resolve_canonical_flow_flags patched to
    return `canonical` (or None to force the legacy-flag fallback path)."""
    import app.engines.admin_catalog.customer_router as router_mod
    async def fake_resolve(db, sid):
        return canonical
    monkeypatch.setattr(router_mod, "_resolve_canonical_flow_flags", fake_resolve)
    return await get_flow_config(r=make_request(), category_id=category_id, service_id=service_id, s=svc)


class TestValidCategory:
    async def test_valid_category_returns_steps_no_crash(self, monkeypatch):
        """This is the exact crash scenario: a resolvable category with no
        exact job-type match (legacy-flag fallback branch) — this used to
        raise UnboundLocalError on every call."""
        cid = _id()
        cat = base_category(category_id=str(cid), requires_schedule=True, requires_location=True)
        svc = make_service(cat_data=cat)
        result = await _call(category_id=cid, svc=svc, canonical=None, monkeypatch=monkeypatch)
        assert result.data["steps"] == ["enter_location", "select_schedule", "confirm"]

    async def test_valid_category_and_service_no_workflow_falls_back_to_legacy_flags(self, monkeypatch):
        cid = _id()
        sid = _id()
        cat = base_category(category_id=str(cid))
        svcdata = base_service(str(cid), is_brand_required=True, is_type_required=False)
        svc = make_service(cat_data=cat, svc_data=svcdata)
        result = await _call(category_id=cid, service_id=sid, svc=svc, canonical=None, monkeypatch=monkeypatch)
        assert result.data["requires_brand"] is True
        assert result.data["requires_service_option"] is False
        assert "select_brand" in result.data["steps"]
        assert "select_option" not in result.data["steps"]


class TestInvalidCategory:
    async def test_no_category_or_service_returns_generic_default(self, monkeypatch):
        svc = make_service(cat_data=None, svc_data=None)
        result = await _call(category_id=None, service_id=None, svc=svc, monkeypatch=monkeypatch)
        assert result.data["flow_type"] == "service_booking"
        assert result.data["steps"] == ["select_service", "confirm"]


class TestDisabledCategory:
    async def test_inactive_category_fails_closed(self, monkeypatch):
        cid = _id()
        cat = base_category(category_id=str(cid), is_active=False)
        svc = make_service(cat_data=cat)
        result = await _call(category_id=cid, svc=svc, monkeypatch=monkeypatch)
        assert result.data["available"] is False
        assert result.data["reason"] == "CATEGORY_UNAVAILABLE"
        assert result.data["steps"] == []

    async def test_not_customer_visible_category_fails_closed(self, monkeypatch):
        cid = _id()
        cat = base_category(category_id=str(cid), is_customer_visible=False)
        svc = make_service(cat_data=cat)
        result = await _call(category_id=cid, svc=svc, monkeypatch=monkeypatch)
        assert result.data["available"] is False
        assert result.data["reason"] == "CATEGORY_UNAVAILABLE"

    async def test_inactive_service_fails_closed(self, monkeypatch):
        cid = _id()
        sid = _id()
        cat = base_category(category_id=str(cid))
        svcdata = base_service(str(cid), is_active=False)
        svc = make_service(cat_data=cat, svc_data=svcdata)
        result = await _call(category_id=cid, service_id=sid, svc=svc, monkeypatch=monkeypatch)
        assert result.data["available"] is False
        assert result.data["reason"] == "SERVICE_UNAVAILABLE"


class TestNoWorkflow:
    async def test_no_workflow_uses_legacy_category_flags_only(self, monkeypatch):
        cid = _id()
        cat = base_category(category_id=str(cid), requires_issue_type=True, requires_brand=True)
        svc = make_service(cat_data=cat, svc_data=None)
        result = await _call(category_id=cid, svc=svc, canonical=None, monkeypatch=monkeypatch)
        assert result.data["requires_issue_type"] is True
        assert result.data["requires_brand"] is True
        assert "select_issue_type" in result.data["steps"]
        assert "select_brand" in result.data["steps"]


class TestRepairRoutineInstallationViaCanonicalBlueprint:
    async def test_repair_job_type_requires_issue_and_no_brand(self, monkeypatch):
        cid = _id(); sid = _id()
        cat = base_category(category_id=str(cid))
        svcdata = base_service(str(cid))
        svc = make_service(cat_data=cat, svc_data=svcdata)
        # canonical = (requires_issue, requires_brand, requires_option, requires_schedule, requires_location)
        canonical = (True, False, False, False, True)
        result = await _call(category_id=cid, service_id=sid, svc=svc, canonical=canonical, monkeypatch=monkeypatch)
        assert result.data["requires_issue_type"] is True
        assert result.data["requires_brand"] is False
        assert result.data["steps"] == ["select_issue_type", "enter_location", "confirm"]

    async def test_routine_maintenance_requires_schedule_no_issue(self, monkeypatch):
        cid = _id(); sid = _id()
        cat = base_category(category_id=str(cid))
        svcdata = base_service(str(cid))
        svc = make_service(cat_data=cat, svc_data=svcdata)
        canonical = (False, False, False, True, True)
        result = await _call(category_id=cid, service_id=sid, svc=svc, canonical=canonical, monkeypatch=monkeypatch)
        assert result.data["requires_issue_type"] is False
        assert result.data["steps"] == ["enter_location", "select_schedule", "confirm"]

    async def test_installation_requires_brand_and_option(self, monkeypatch):
        cid = _id(); sid = _id()
        cat = base_category(category_id=str(cid))
        svcdata = base_service(str(cid))
        svc = make_service(cat_data=cat, svc_data=svcdata)
        canonical = (False, True, True, True, True)
        result = await _call(category_id=cid, service_id=sid, svc=svc, canonical=canonical, monkeypatch=monkeypatch)
        assert result.data["steps"] == [
            "select_brand", "select_option", "enter_location", "select_schedule", "confirm",
        ]


class TestTypeAndBrandCombinations:
    async def test_type_enabled_brand_disabled(self, monkeypatch):
        cid = _id(); sid = _id()
        cat = base_category(category_id=str(cid))
        svcdata = base_service(str(cid))
        svc = make_service(cat_data=cat, svc_data=svcdata)
        canonical = (False, False, True, False, False)  # requires_option only
        result = await _call(category_id=cid, service_id=sid, svc=svc, canonical=canonical, monkeypatch=monkeypatch)
        assert result.data["requires_service_option"] is True
        assert result.data["requires_brand"] is False
        assert "select_option" in result.data["steps"]
        assert "select_brand" not in result.data["steps"]

    async def test_brand_enabled_type_disabled(self, monkeypatch):
        cid = _id(); sid = _id()
        cat = base_category(category_id=str(cid))
        svcdata = base_service(str(cid))
        svc = make_service(cat_data=cat, svc_data=svcdata)
        canonical = (False, True, False, False, False)  # requires_brand only
        result = await _call(category_id=cid, service_id=sid, svc=svc, canonical=canonical, monkeypatch=monkeypatch)
        assert result.data["requires_brand"] is True
        assert result.data["requires_service_option"] is False
        assert "select_brand" in result.data["steps"]
        assert "select_option" not in result.data["steps"]


class TestRequiredVsOptionalQuestions:
    async def test_all_optional_yields_confirm_only(self, monkeypatch):
        cid = _id(); sid = _id()
        cat = base_category(category_id=str(cid))
        svcdata = base_service(str(cid))
        svc = make_service(cat_data=cat, svc_data=svcdata)
        canonical = (False, False, False, False, False)
        result = await _call(category_id=cid, service_id=sid, svc=svc, canonical=canonical, monkeypatch=monkeypatch)
        assert result.data["steps"] == ["confirm"]

    async def test_all_required_yields_full_step_order(self, monkeypatch):
        cid = _id(); sid = _id()
        cat = base_category(category_id=str(cid))
        svcdata = base_service(str(cid))
        svc = make_service(cat_data=cat, svc_data=svcdata)
        canonical = (True, True, True, True, True)
        result = await _call(category_id=cid, service_id=sid, svc=svc, canonical=canonical, monkeypatch=monkeypatch)
        assert result.data["steps"] == [
            "select_issue_type", "select_brand", "select_option",
            "enter_location", "select_schedule", "confirm",
        ]
