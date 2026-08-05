"""Technician Mobile App Phase Z — GET /v1/mobile/sync/idempotency-status.

Read-only lookup against the EXISTING idempotency cache
(app/core/idempotency.py's IdempotencyMiddleware writes to it on every
successful write; this endpoint only reads it). Proves: (a) an unseen key
reports "unknown" rather than fabricating "confirmed", (b) a key present
in the cache (simulating a prior successful write whose response was lost
to the client) reports "confirmed", (c) tenant isolation -- the cache key
is derived from the CALLER's own JWT tenant_id, never a client-supplied
one, so the same key/path pair for a different tenant reports "unknown".
"""
from __future__ import annotations

import hashlib
import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.dependencies.auth import get_current_user, UserContext
from app.core.idempotency import IDEMPOTENCY_PREFIX


def make_technician_context(tenant_id, user_id=None):
    return UserContext(user_id=user_id or str(uuid.uuid4()), email="staff@serviceos.local", role="technician",
                        tenant_id=tenant_id, full_name="Demo Staff", is_verified=True)


@pytest.mark.asyncio
async def test_unseen_key_reports_unknown_not_confirmed():
    tenant_id = str(uuid.uuid4())
    app.dependency_overrides[get_current_user] = lambda: make_technician_context(tenant_id)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/v1/mobile/sync/idempotency-status",
                params={"key": str(uuid.uuid4()), "path": "/v1/staff/notifications/x/read"},
                headers={"Authorization": "Bearer x"},
            )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "unknown"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_cached_key_reports_confirmed(monkeypatch):
    tenant_id = str(uuid.uuid4())
    key = str(uuid.uuid4())
    path = "/v1/staff/notifications/x/read"
    cache_key = f"{IDEMPOTENCY_PREFIX}{hashlib.sha256(f'{key}:{path}:{tenant_id}'.encode()).hexdigest()}"

    mock_r = AsyncMock()
    mock_r.get = AsyncMock(side_effect=lambda k: '{"status_code":200}' if k == cache_key else None)
    monkeypatch.setattr("app.redis_client._redis", mock_r)

    app.dependency_overrides[get_current_user] = lambda: make_technician_context(tenant_id)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/v1/mobile/sync/idempotency-status", params={"key": key, "path": path},
                headers={"Authorization": "Bearer x"},
            )
        assert response.json()["data"]["status"] == "confirmed"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_same_key_different_tenant_reports_unknown(monkeypatch):
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    key = str(uuid.uuid4())
    path = "/v1/staff/notifications/x/read"
    cache_key_a = f"{IDEMPOTENCY_PREFIX}{hashlib.sha256(f'{key}:{path}:{tenant_a}'.encode()).hexdigest()}"

    mock_r = AsyncMock()
    mock_r.get = AsyncMock(side_effect=lambda k: '{"status_code":200}' if k == cache_key_a else None)
    monkeypatch.setattr("app.redis_client._redis", mock_r)

    app.dependency_overrides[get_current_user] = lambda: make_technician_context(tenant_b)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/v1/mobile/sync/idempotency-status", params={"key": key, "path": path},
                headers={"Authorization": "Bearer x"},
            )
        assert response.json()["data"]["status"] == "unknown"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
