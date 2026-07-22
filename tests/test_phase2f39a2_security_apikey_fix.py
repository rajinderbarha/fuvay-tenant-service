"""Slice 2F-39A2: real authorization defect found and fixed in
app/engines/security/router.py::create_api_key.

Before this slice: the endpoint used require_permission(P.TENANT_UPDATE)
(not require_tenant_mutation_permission), so a tenant-side user with the
documented read-only access_scope 'customer_support_limited' could still
create an API key -- exactly what require_tenant_mutation_permission
exists to block. It also trusted a client-supplied body["tenant_id"] with
zero comparison to the caller's own tenant, letting any tenant_owner
create an API key scoped to any OTHER tenant (a cross-tenant IDOR).

Both are fixed: guard swapped to require_tenant_mutation_permission, and
tenant_id is now server-derived from the authenticated user's own token.
"""
from __future__ import annotations

import inspect
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.asyncio


def test_route_uses_tenant_mutation_permission_not_bare_permission():
    from app.engines.security import router as security_router
    src = inspect.getsource(security_router.create_api_key)
    assert "require_tenant_mutation_permission(P.TENANT_UPDATE)" in src


def test_route_does_not_trust_client_supplied_tenant_id():
    from app.engines.security import router as security_router
    src = inspect.getsource(security_router.create_api_key)
    assert 'body["tenant_id"]' not in src
    assert "u.tenant_id" in src


async def test_no_tenant_context_is_rejected_before_any_service_call():
    from app.engines.security import router as security_router
    from app.exceptions import ServiceOSException

    class FakeUser:
        tenant_id = None

    class FakeRequest:
        async def json(self):
            raise AssertionError("must not parse body before tenant context check")

    with pytest.raises(ServiceOSException):
        await security_router.create_api_key(FakeRequest(), u=FakeUser(), s=MagicMock())


async def test_created_key_is_scoped_to_the_callers_own_tenant_not_the_body():
    from app.engines.security import router as security_router

    caller_tenant = uuid.uuid4()
    spoofed_tenant = uuid.uuid4()

    class FakeUser:
        tenant_id = str(caller_tenant)

    class FakeState:
        request_id = "req_test"

    class FakeRequest:
        state = FakeState()

        async def json(self):
            # An attacker-controlled body naming a DIFFERENT tenant.
            return {"tenant_id": str(spoofed_tenant), "name": "attacker key"}

    fake_svc = MagicMock()
    fake_svc.create_api_key = AsyncMock(return_value={"key_id": str(uuid.uuid4())})

    await security_router.create_api_key(FakeRequest(), u=FakeUser(), s=fake_svc)

    called_tenant_id = fake_svc.create_api_key.await_args.args[0]
    assert called_tenant_id == caller_tenant
    assert called_tenant_id != spoofed_tenant
