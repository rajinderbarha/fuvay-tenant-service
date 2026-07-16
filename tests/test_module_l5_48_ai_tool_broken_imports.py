"""MODULE-L5-48 — two AI-chat backend tools + tenant storage-quota usage
always silently failed/reported wrong.

Found while triaging bare `except Exception:` swallow-sites platform-wide.
`BackendToolExecutor._tool_get_category_offerings` imported a module that
does not exist (`app.engines.customer_flow.models`), and
`_tool_check_service_area` imported a model that does not exist
(`app.engines.geo.models.GeoZone`). Both were wrapped in
`except Exception as exc: logger.warning(...)`, so every single call from
every customer conversation always hit the except branch and returned the
"unable to load"/fallback response -- never once returning real data.

Worse for `_tool_check_service_area`: its failure fallback hardcodes
`"available": True`, so a real customer asking "do you serve <city>?" was
always told yes regardless of actual coverage, since the real lookup could
never run.

Fixed: `_tool_get_category_offerings` now imports `MasterOffering` from
`app.engines.admin_catalog.models` (where it actually lives).
`_tool_check_service_area` now queries `TenantServiceArea` from
`app.engines.serviceability.models` (the real city/zipcode coverage table)
instead of a `GeoZone` model that was never defined anywhere in `geo.models`.

Same broken-import sweep also found `PackageCommerceService._count_storage_used`
(app/engines/package_commerce/service.py) importing a nonexistent
`app.engines.media.models.TenantMedia` (real media files live in `MediaFile`,
column `size_bytes` not `file_size_bytes`). Wrapped in the same
`except Exception: return 0.0` pattern, so every tenant's storage-quota page
(GET /v1/tenant/packages/storage-quota, GET
/v1/admin/packages/tenants/{id}/storage-quota) has always reported 0GB used
regardless of real usage -- quota enforcement was silently a no-op.
"""
import inspect

from app.engines.ai_conversation.backend_tools import BackendToolExecutor
from app.engines.package_commerce.service import PackageCommerceService


def test_category_offerings_imports_real_model():
    src = inspect.getsource(BackendToolExecutor._tool_get_category_offerings)
    assert "app.engines.customer_flow.models" not in src
    assert "from app.engines.admin_catalog.models import ServiceCategory, MasterOffering" in src


def test_check_service_area_imports_real_model():
    src = inspect.getsource(BackendToolExecutor._tool_check_service_area)
    assert "GeoZone" not in src
    assert "from app.engines.serviceability.models import TenantServiceArea" in src


def test_broken_imports_actually_resolve():
    from app.engines.admin_catalog.models import ServiceCategory, MasterOffering  # noqa: F401
    from app.engines.serviceability.models import TenantServiceArea  # noqa: F401
    from app.engines.media.models import MediaFile  # noqa: F401


def test_count_storage_used_imports_real_model():
    src = inspect.getsource(PackageCommerceService._count_storage_used)
    assert "TenantMedia" not in src
    assert "file_size_bytes" not in src
    assert "from app.engines.media.models import MediaFile" in src
    assert "MediaFile.size_bytes" in src


class TestLive:
    async def test_tools_return_real_data_not_silent_fallback(self):
        import pytest
        from sqlalchemy import select, func
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from app.engines.admin_catalog.models import ServiceCategory, MasterOffering

        try:
            engine = create_async_engine(
                "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/serviceos")
            Session = async_sessionmaker(engine, expire_on_commit=False)
        except Exception:
            pytest.skip("db not reachable")

        async with Session() as db:
            r = await db.execute(
                select(MasterOffering).where(MasterOffering.is_active == True).limit(1))
            offering = r.scalars().first()
            if not offering:
                pytest.skip("no active master_offerings in this environment")
            cat_r = await db.execute(
                select(ServiceCategory).where(ServiceCategory.id == offering.category_id))
            category = cat_r.scalars().first()

            tool = BackendToolExecutor(db, customer_id=None)
            result = await tool._tool_get_category_offerings(
                category.name.lower().replace(" ", "-"))
            assert "note" not in result
            assert result["total"] >= 1
            assert any(o["name"] == offering.name for o in result["offerings"])
        await engine.dispose()

    async def test_storage_used_reflects_real_media_files(self):
        import uuid
        import pytest
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from app.engines.media.models import MediaFile

        try:
            engine = create_async_engine(
                "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/serviceos")
            Session = async_sessionmaker(engine, expire_on_commit=False)
        except Exception:
            pytest.skip("db not reachable")

        tenant_id = uuid.UUID("5209ef33-a53e-4fc0-b3f6-006335b8d712")
        async with Session() as db:
            mf = MediaFile(
                tenant_id=tenant_id, owner_id=uuid.uuid4(), entity_type="test",
                entity_id="l5-48-live", original_name="test.jpg", storage_key="test/l5-48",
                mime_type="image/jpeg", size_bytes=500 * 1024 * 1024,
            )
            db.add(mf)
            await db.commit()
            try:
                svc = PackageCommerceService(db)
                used_gb = await svc._count_storage_used(tenant_id)
                assert used_gb > 0.4
            finally:
                await db.delete(mf)
                await db.commit()
        await engine.dispose()
