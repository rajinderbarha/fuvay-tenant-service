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

"""
import inspect

from app.engines.ai_conversation.backend_tools import BackendToolExecutor


def test_category_offerings_imports_real_model():
    """Regression check updated for the backend-first re-architecture:
    `_tool_get_category_offerings` now delegates to
    `offering_catalog_service.list_serviceable_offerings` (shared with the
    customer-facing assistant-bootstrap endpoint) rather than querying
    `MasterOffering` inline -- but the real invariant this test protects
    (never reference the dead `app.engines.customer_flow.models` module,
    never silently return zero real offerings) still holds via the shared
    function, confirmed by `test_140412_zipcode_offering_isolation.py`."""
    src = inspect.getsource(BackendToolExecutor._tool_get_category_offerings)
    assert "app.engines.customer_flow.models" not in src
    assert "MasterOffering" not in src
    assert "list_serviceable_offerings" in src


def test_check_service_area_imports_real_model():
    src = inspect.getsource(BackendToolExecutor._tool_check_service_area)
    assert "GeoZone" not in src
    assert "from app.engines.serviceability.models import TenantServiceArea" in src


def test_broken_imports_actually_resolve():
    from app.engines.admin_catalog.models import ServiceCategory, MasterOffering  # noqa: F401
    from app.engines.serviceability.models import TenantServiceArea  # noqa: F401
    from app.engines.media.models import MediaFile  # noqa: F401


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

