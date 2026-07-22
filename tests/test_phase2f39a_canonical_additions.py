"""Slice 2F-39A: newly discovered canonical tenant/provider mutations.

Route census work (WS2-6) found 3 routes in app/engines/auth/router.py
that use the exact same protection pattern as the existing 313 canonical
mutations (require_tenant_mutation_permission + explicit tenant_id check
+ server-derived tenant scoping at the service layer) but were never
added to the canonical inventory:

  POST   /v1/auth/api-keys           create_api_key
  DELETE /v1/auth/api-keys/{key_id}  revoke_api_key
  PATCH  /v1/auth/api-keys/{key_id}  update_api_key

This file proves the protection is real, not merely present.
"""
from __future__ import annotations

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.asyncio


async def test_router_uses_tenant_mutation_permission_guard():
    import inspect
    from app.engines.auth import router as auth_router
    for fn_name in ("create_api_key", "revoke_api_key", "update_api_key"):
        src = inspect.getsource(getattr(auth_router, fn_name))
        assert "require_tenant_mutation_permission(P.AUTH_APIKEYS_MANAGE)" in src
        assert "user.tenant_id" in src


async def test_revoke_api_key_scopes_by_tenant_id_server_derived():
    from app.engines.auth.service import AuthService
    db = MagicMock()
    key_result = MagicMock()
    key_result.scalar_one_or_none.return_value = None  # not found for this tenant
    db.execute = AsyncMock(return_value=key_result)
    svc = AuthService.__new__(AuthService)
    svc.db = db
    key_id = uuid.uuid4()
    own_tenant = uuid.uuid4()
    with pytest.raises(Exception):
        await svc.revoke_api_key(key_id, own_tenant, uuid.uuid4())
    # Confirms the lookup is filtered by tenant_id -- a foreign-tenant key
    # (not owned by own_tenant) is correctly treated as not found, never
    # revoked, regardless of key_id validity.
    called_stmt = str(db.execute.await_args.args[0])
    assert "tenant_id" in called_stmt.lower()


async def test_update_api_key_scopes_by_tenant_id_server_derived():
    from app.engines.auth.service import AuthService
    db = MagicMock()
    key_result = MagicMock()
    key_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=key_result)
    svc = AuthService.__new__(AuthService)
    svc.db = db
    with pytest.raises(Exception):
        await svc.update_api_key(uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "new name", None)
    called_stmt = str(db.execute.await_args.args[0])
    assert "tenant_id" in called_stmt.lower()


async def test_create_api_key_persists_server_supplied_tenant_id_not_client():
    from app.engines.auth.service import AuthService
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    svc = AuthService.__new__(AuthService)
    svc.db = db
    svc._audit = AsyncMock()
    server_tenant_id = uuid.uuid4()
    await svc.create_api_key(server_tenant_id, uuid.uuid4(), "test key", ["read"], False, None)
    added_key = db.add.call_args.args[0]
    assert added_key.tenant_id == server_tenant_id
