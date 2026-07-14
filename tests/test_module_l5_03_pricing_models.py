"""MODULE-L5-03 — canonical pricing-model registry: single source of truth + HTTP endpoint.

Uses the repo's established in-process AsyncClient + dependency_overrides pattern
(see test_final_l5_01b_admin_tenant_rbac.py) — deterministic, no live DB/seed.
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.dependencies.auth import get_current_user, UserContext
from app.engines.admin_catalog.service import PRICING_MODEL_REGISTRY, VALID_PRICING_MODELS
import e2e.pricing_model_registry_guard as guard


def _user(role, tenant_id=None):
    return UserContext(user_id=str(uuid.uuid4()), email=f"{role}@test.local", role=role,
                       tenant_id=tenant_id, full_name=role, is_verified=True)


def test_valid_models_derived_from_registry():
    assert VALID_PRICING_MODELS == set(PRICING_MODEL_REGISTRY)


def test_every_model_has_label_and_required_fields():
    for code, meta in PRICING_MODEL_REGISTRY.items():
        assert meta.get("label"), code
        assert meta.get("required_fields"), code


def test_registry_guard_passes():
    assert guard.check() == []


@pytest.mark.asyncio
async def test_pricing_models_endpoint_serves_registry():
    app.dependency_overrides[get_current_user] = lambda: _user("super_admin")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/v1/admin/pricing-models", headers={"Authorization": "Bearer x"})
        assert r.status_code == 200, r.text
        body = r.json()["data"]
        codes = {m["code"] for m in body["pricing_models"]}
        assert codes == set(PRICING_MODEL_REGISTRY)
        assert body["count"] == len(PRICING_MODEL_REGISTRY)
        for m in body["pricing_models"]:
            assert m["label"] and m["required_fields"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_pricing_models_endpoint_available_to_tenant_owner():
    # Dropdown metadata must be readable by tenant portal too, not just admins.
    app.dependency_overrides[get_current_user] = lambda: _user("tenant_owner", tenant_id=str(uuid.uuid4()))
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/v1/admin/pricing-models", headers={"Authorization": "Bearer x"})
        assert r.status_code == 200, r.text
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_pricing_models_endpoint_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/v1/admin/pricing-models")
    assert r.status_code == 401, r.text
