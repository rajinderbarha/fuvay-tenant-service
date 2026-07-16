"""MODULE-L5-45 — package activation never applied the purchased package's
storage quota or commission rate to the tenant, for any tenant, ever.

Investigation while assessing whether to delete field_ops-style dead code
(purchase_package()/TenantPackagePurchase, confirmed fully unreachable since
MODULE-L5-30/36/38) surfaced something more important: _apply_storage_quota
and _apply_commission_rate were ONLY ever called from that dead method.
activate_tenant_package_assignment -- the real, live activation path, called
on admin tenant approval -- never called either helper. Every tenant approved
through the real flow kept whatever quota/commission they already had,
regardless of the package they actually bought. app/engines/media/service.py's
own docstring assumes this already happens ("tenant_limits.max_storage_gb,
which the package engine writes on package approval").

Deeper still: _apply_storage_quota/_apply_commission_rate only ever UPDATED
an existing TenantLimits/TenantSettings row -- and confirmed via direct query,
ZERO tenants in the platform have either row (nothing creates them during
onboarding), so even if activation had called these helpers all along, they
would have silently done nothing for every tenant, ever.

Fix: activate_tenant_package_assignment now loads the package and applies
both, and both helpers now create the row (with model defaults) when missing
instead of silently no-op'ing.

Verified live: seeded a package with storage_quota_gb=88/commission_rate=15,
purchased + activated it for a real tenant with no prior tenant_limits/
tenant_operational_settings rows, confirmed both rows were created with the
correct values (max_storage_gb=88, commission_rate=0.15).
"""
from __future__ import annotations

import inspect
import uuid
from decimal import Decimal

import pytest

from app.engines.package_commerce import service as pkg_service_module

TENANT_ID = uuid.UUID("5209ef33-a53e-4fc0-b3f6-006335b8d712")


def test_activation_calls_the_quota_and_commission_helpers():
    src = inspect.getsource(pkg_service_module.PackageCommerceService.activate_tenant_package_assignment)
    assert "_apply_storage_quota" in src
    assert "_apply_commission_rate" in src


def test_helpers_create_the_row_when_missing():
    quota_src = inspect.getsource(pkg_service_module.PackageCommerceService._apply_storage_quota)
    commission_src = inspect.getsource(pkg_service_module.PackageCommerceService._apply_commission_rate)
    assert "self.db.add(TenantLimits(" in quota_src
    assert "self.db.add(TenantSettings(" in commission_src


@pytest.mark.asyncio
async def test_activation_creates_and_sets_limits_and_commission_live():
    import asyncpg
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    conn = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
    pkg_id = None
    assignment_id = None
    try:
        had_limits = await conn.fetchval(
            "SELECT count(*) FROM tenant_limits WHERE tenant_id=$1", TENANT_ID)
        had_settings = await conn.fetchval(
            "SELECT count(*) FROM tenant_operational_settings WHERE tenant_id=$1", TENANT_ID)
        if had_limits or had_settings:
            pytest.skip("tenant already has limits/settings rows; test needs a clean slate")

        pkg_id = uuid.uuid4()
        await conn.execute(
            """INSERT INTO service_packages
               (id, name, slug, package_type, package_price, security_deposit_amount,
                included_credit_amount, storage_quota_gb, commission_rate, is_active,
                display_order, created_at, updated_at)
               VALUES ($1,'L5-45 pytest pkg',$2,'credit_topup',500,0,0,88,15.0,true,0,now(),now())""",
            pkg_id, f"l5-45-pytest-{str(pkg_id)[:8]}")
        assignment_id = uuid.uuid4()
        await conn.execute(
            """INSERT INTO tenant_package_assignments
               (id, tenant_id, package_id, package_type, status, selected_at, created_at, updated_at)
               VALUES ($1,$2,$3,'credit_topup','selected', now(), now(), now())""",
            assignment_id, TENANT_ID, pkg_id)

        engine = create_async_engine(
            "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos", echo=False)
        Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        try:
            async with Session() as db:
                svc = pkg_service_module.PackageCommerceService(
                    db=db, request_id="test-l545", actor_id=None, actor_role="super_admin")
                result = await svc.activate_tenant_package_assignment(TENANT_ID)
                await db.commit()
                assert result["status"] == "active"
        finally:
            await engine.dispose()

        limits_row = await conn.fetchrow(
            "SELECT max_storage_gb FROM tenant_limits WHERE tenant_id=$1", TENANT_ID)
        settings_row = await conn.fetchrow(
            "SELECT commission_rate FROM tenant_operational_settings WHERE tenant_id=$1", TENANT_ID)
        assert limits_row["max_storage_gb"] == 88
        assert settings_row["commission_rate"] == Decimal("0.1500")
    finally:
        if assignment_id is not None:
            await conn.execute("DELETE FROM tenant_package_assignments WHERE id=$1", assignment_id)
        if pkg_id is not None:
            await conn.execute("DELETE FROM service_packages WHERE id=$1", pkg_id)
        await conn.execute("DELETE FROM tenant_limits WHERE tenant_id=$1", TENANT_ID)
        await conn.execute("DELETE FROM tenant_operational_settings WHERE tenant_id=$1", TENANT_ID)
        await conn.close()
