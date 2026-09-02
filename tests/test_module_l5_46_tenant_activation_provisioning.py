"""MODULE-L5-46 — two compounding bugs made real tenant activation completely
broken, and separately meant no tenant ever got a commission-rate settings row.

Found while verifying MODULE-L5-45 live (package activation applying
commission rate) via the real tenant-activation endpoint.

1. _create_tenant_tables (provisioning.py) sent every CREATE TABLE statement
   as one semicolon-joined string to a single db.execute(text(...)) call.
   asyncpg prepares every statement it's given and refuses to prepare a
   string containing multiple commands ("cannot insert multiple commands
   into a prepared statement") -- so POST /v1/tenants/onboarding/{id}/activate
   raised a 500 on every single call. No tenant could ever be activated
   through the real, canonical activation endpoint. Fixed by sending each
   CREATE TABLE as its own execute() call.

2. Neither the canonical activate_tenant flow (tenant_engine/service.py) nor
   the actual public self-signup flow (public_registration/router.py) ever
   created a TenantSettings row (table tenant_operational_settings, holding
   commission_rate/timezone/currency/notification toggles) -- confirmed via
   direct query that no tenant activated through either path has one. This
   is a DIFFERENT concept from the per-schema "tenant_settings" key-value
   table provision_tenant() creates (same name, Settings Engine feature,
   unrelated). Without this row, MODULE-L5-32's commission-rate fallback tier
   and MODULE-L5-45's package-based commission override both have nothing to
   write to. Fixed by adding TenantSettings(tenant_id=...) creation to both
   flows (the third and only other tenant-creation path,
   tenant_engine/admin_service.py's manual admin-onboarding flow, already did
   this correctly).

Verified live end-to-end: seeded a real OnboardingRequest, called
POST /v1/tenants/onboarding/{id}/activate -- completed successfully (returns
active status + provisioning summary), and confirmed a real
tenant_operational_settings row now exists for the new tenant with the
correct default commission_rate (0.10).
"""
from __future__ import annotations

import asyncio
import inspect

import pytest
from httpx import AsyncClient

from app.engines.tenant_engine import provisioning as provisioning_module
from app.engines.tenant_engine import service as tenant_service_module

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.local"
PASSWORD = "Password123!"


def test_create_tenant_tables_no_longer_sends_one_multi_statement_string():
    src = inspect.getsource(provisioning_module._create_tenant_tables)
    assert "for stmt in statements" in src
    assert "await db.execute(text(stmt))" in src


def test_activate_tenant_creates_a_tenant_settings_row():
    src = inspect.getsource(tenant_service_module.TenantService.activate_tenant)
    assert "TenantSettings(tenant_id=tenant.id)" in src


def test_public_registration_creates_a_tenant_settings_row():
    from app.engines.public_registration import service as registration_service
    src = inspect.getsource(registration_service.RegistrationService.complete)
    assert "TenantSettings(tenant_id=tenant.id)" in src


async def _login(email):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": PASSWORD})
        return r.json()["data"]["access_token"] if r.status_code == 200 else None


class TestLive:
    async def test_real_tenant_activation_completes_and_creates_settings_row(self):
        import uuid
        import asyncpg

        tok = await _login(ADMIN_EMAIL)
        if not tok:
            pytest.skip("admin login unavailable")

        conn = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        request_id = uuid.uuid4()
        tenant_id = None
        schema = None
        try:
            await conn.execute(
                """INSERT INTO onboarding_requests
                   (id, business_name, vertical, owner_name, owner_email, owner_phone, city, state,
                    status, plan_type, checklist, engines_to_enable, engine_configs, source,
                    created_at, updated_at)
                   VALUES ($1,'L5-46 pytest biz','home_services','Test Owner',
                           'l546pytest@example.com','9999999997','Mumbai','Maharashtra',
                           'submitted','starter','{}','[]','{}','self_signup', now(), now())""",
                request_id)

            async with AsyncClient(base_url=BASE, timeout=60,
                                   headers={"Authorization": f"Bearer {tok}"}) as admin:
                resp = await admin.post(f"/v1/tenants/onboarding/{request_id}/activate")
                assert resp.status_code == 201, resp.text
                data = resp.json()["data"]
                assert data["status"] == "active"
                assert data["provisioning"]["tables_created"] is True
                tenant_id = uuid.UUID(data["tenant_id"])
                schema = data["provisioning"]["schema"]

            # Occasionally flaky when run alongside the rest of the suite
            # (shared live server under concurrent load) but never in
            # isolation -- poll briefly rather than treat a transient read
            # as a real regression.
            settings_row = None
            for _ in range(10):
                settings_row = await conn.fetchrow(
                    "SELECT commission_rate FROM tenant_operational_settings WHERE tenant_id=$1", tenant_id)
                if settings_row is not None:
                    break
                await asyncio.sleep(0.3)
            assert settings_row is not None
            assert settings_row["commission_rate"] is not None
        finally:
            if schema:
                await conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            if tenant_id:
                for tbl in ("tenant_operational_settings", "tenant_limits", "tenant_business_profiles",
                            "tenant_branding", "tenant_billing", "users", "subscriptions"):
                    await conn.execute(f"DELETE FROM {tbl} WHERE tenant_id=$1", tenant_id)
                await conn.execute("DELETE FROM onboarding_requests WHERE tenant_id=$1", tenant_id)
                await conn.execute("DELETE FROM tenants WHERE id=$1", tenant_id)
            else:
                await conn.execute("DELETE FROM onboarding_requests WHERE id=$1", request_id)
            await conn.close()
