"""API contract checks for the customer side of the booking lifecycle.

Customer-prefixed booking, tracking, quote, payment, invoice, and activity
routes must reject tenant/staff identities before any record lookup occurs.
Ownership checks alone are insufficient because a non-customer may otherwise
exercise a customer-only action when UUIDs happen to overlap or a downstream
service omits a check.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient

from app.core.permissions import require_staff_or_above_mutation
from app.dependencies.auth import (
    UserContext,
    get_current_user,
    require_customer,
    require_staff_or_above,
    require_staff_or_technician_only,
    require_technician,
)
from app.main import app


CUSTOMER_BOOKING_PREFIXES = (
    "/v1/customer/home-services",
    "/v1/customer/bookings",
    "/v1/customer/my-activity",
    "/v1/customer/confirm",
    "/v1/customer/service-jobs",
    "/v1/customer/service-invoices",
    "/v1/customer/direct-payments",
    "/v1/customer/quotes",
)


def _depends_on_customer_guard(dependant) -> bool:
    return dependant.call is require_customer or any(
        _depends_on_customer_guard(child) for child in dependant.dependencies
    )


_STAFF_GUARDS = {
    require_staff_or_above,
    require_staff_or_above_mutation,
    require_staff_or_technician_only,
    require_technician,
}


def _depends_on_staff_guard(dependant) -> bool:
    return dependant.call in _STAFF_GUARDS or any(
        _depends_on_staff_guard(child) for child in dependant.dependencies
    )


def test_every_customer_booking_route_has_customer_role_guard():
    unguarded = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path.startswith(CUSTOMER_BOOKING_PREFIXES):
            if not _depends_on_customer_guard(route.dependant):
                unguarded.append((sorted(route.methods), route.path))
    assert not unguarded, f"customer booking routes missing require_customer: {unguarded}"


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["tenant_owner", "staff", "technician", "super_admin"])
async def test_non_customer_roles_are_rejected_before_booking_lookup(role: str):
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()),
        email=f"{role}@serviceos.local",
        role=role,
        tenant_id=str(uuid.uuid4()) if role != "super_admin" else None,
        full_name="Wrong Role",
        is_verified=True,
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                f"/v1/customer/bookings/{uuid.uuid4()}",
                headers={"Authorization": "Bearer test"},
            )
        assert response.status_code == 403, response.text
        assert response.json()["error_code"] == "PERMISSION_DENIED"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_every_native_staff_booking_route_has_staff_role_guard():
    unguarded = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path.startswith(("/v1/staff/service-jobs", "/v1/staff/mobile-")):
            if not _depends_on_staff_guard(route.dependant):
                unguarded.append((sorted(route.methods), route.path))
    assert not unguarded, f"native staff booking routes missing a staff guard: {unguarded}"


@pytest.mark.asyncio
async def test_customer_role_is_rejected_before_staff_job_lookup():
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=str(uuid.uuid4()),
        email="customer@serviceos.local",
        role="customer",
        tenant_id=None,
        full_name="Wrong Role",
        is_verified=True,
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                f"/v1/staff/service-jobs/{uuid.uuid4()}/checklists",
                headers={"Authorization": "Bearer test"},
            )
        assert response.status_code == 403, response.text
    finally:
        app.dependency_overrides.pop(get_current_user, None)
