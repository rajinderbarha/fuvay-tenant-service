"""FINAL-L5-05Q — Provider coverage, brand, zone and bulk mutation
permission and tenant-isolation certification.

Investigation found the real Provider-coverage mutation surface in this
codebase is narrower than the mission's assumed data model (no
`provider_zones`/`provider_brands`/`provider_capacity`/`provider_sla`
tables exist -- "Provider" is modeled as "Tenant" throughout, per
FINAL-L5-05O/05P's repeated confirmation). The real, active, admin-side
Provider coverage mutation surface consists of:

1. Tenant Service Areas -- the platform's real "Provider coverage"
   geography assignment, exposed at `/v1/admin/tenants/{id}/service-areas`.
   **Critical discovery**: TWO independent routers both register this
   EXACT path (`app/engines/serviceability/router.py` and
   `app/engines/tenant_engine/admin_router.py`), each backed by a
   different service class (`ServiceabilityService` vs
   `AdminTenantService`). `serviceability.router` is registered first in
   `main.py` (line 154, vs. 349), so FastAPI matches it first and
   `tenant_engine.admin_router`'s identical routes are **completely
   unreachable dead code** for this path -- confirmed via a live HTTP
   call showing the actual response schema/error codes only match
   `ServiceabilityService`. This is a real, previously-unknown
   architecture defect, found only through live API testing (not
   caught by any unit test, since those call the service class
   directly, bypassing the router entirely).
2. Provider Enabled Offerings suspend/reactivate/refresh-readiness
   (`/v1/admin/tenants/{id}/offerings/enabled/{id}/*`).
3. Provider Bookability/Visibility overrides (fixed in FINAL-L5-05P,
   re-verified here).

No dedicated Provider brand-CRUD, zone/zipcode-as-distinct-entities,
capacity, SLA, or blackout-date admin mutation surface exists in this
codebase -- confirmed via exhaustive grep across every engine, not
assumed. This is a genuine "does not exist" finding (same class as
FINAL-L5-05P's Team/Membership finding), not an oversight.

This sprint's real fixes (on the actually-live `ServiceabilityService`
path, `app/engines/serviceability/service.py` + `router.py`):

1. **P0 cross-tenant vulnerability**: `admin_update_service_area`/
   `admin_delete_service_area` captured `tenant_id` from the URL but
   never passed it to the service layer -- `update_service_area`/
   `deactivate_service_area` loaded the target area by `area_id` ALONE,
   with zero tenant-ownership verification (`_assert_owns_tenant` only
   enforces for `actor_role == "tenant_owner"`, a no-op for admin
   callers). Any Super Admin (or any `PLATFORM_ADMIN`-holding role)
   could update/delete another tenant's service area while the route's
   `tenant_id` silently went unchecked. Fixed with an `admin_tenant_id`
   parameter, passed only from the admin router handlers, that raises
   `NotFoundException` on mismatch.
2. **Real concurrency bug**: `create_service_area`'s SELECT-then-INSERT
   duplicate check has no locking -- confirmed via a real concurrent-
   request test (not mocked) that two simultaneous creates with an
   identical payload both silently succeeded. Fixed with a transaction-
   scoped Postgres advisory lock keyed on the exact tenant+coverage
   tuple.

The (now confirmed dead-code, HTTP-unreachable) `AdminTenantService`
duplicate/audit fixes made earlier in this investigation are kept as
defense-in-depth (correct in themselves, and would matter if a future
change reorders router registration or a new caller invokes the service
directly) but are NOT the live-path fix -- documented honestly, not
conflated with the real fix above.

FINAL-L5-05T UPDATE: the duplicate-route architecture flagged here as
unresolved has since been closed. `ServiceabilityService` is now the
single certified canonical owner of Tenant Service Areas (see
`FINAL_L5_05T_ADR_SERVICE_AREA_CANONICAL_OWNER.md`); the shadowed
`AdminTenantService` methods and both duplicate route families (admin
AND, previously-undiscovered here, tenant-portal) were removed entirely
rather than left registered-but-dead. `TestDuplicateRouteRegistrationFinding`
and `TestAdminTenantServiceDefenseInDepthFixesStillCorrect` below are
updated accordingly -- see `tests/test_final_l5_05t_service_area_route_canonicalization.py`
for the full 05T guard suite.
"""
from __future__ import annotations

import uuid
import asyncio
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import get_settings
from app.exceptions import ServiceOSException, NotFoundException
from app.engines.tenant_engine.admin_service import AdminTenantService
from app.engines.serviceability.service import ServiceabilityService

ROOT = Path(__file__).parent.parent

# Real, pre-existing seeded demo tenants (confirmed live via direct SQL).
TENANT_A = uuid.UUID("5209ef33-a53e-4fc0-b3f6-006335b8d712")  # Demo AC Services
TENANT_B = uuid.UUID("f45664c1-50b7-42c5-a115-37fed1bbaf53")  # Isolation Test Services


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


@pytest.fixture
def real_engine():
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, pool_size=5, max_overflow=5)
    yield engine


class TestLiveServiceabilityCrossTenantIsolation:
    """Real Postgres, two real seeded tenants, the ACTUALLY-live service
    class (ServiceabilityService, confirmed via live HTTP to be the real
    handler for /v1/admin/tenants/{id}/service-areas)."""

    @pytest.mark.asyncio
    async def test_admin_tenant_id_mismatch_denies_update(self, real_engine):
        session_factory = async_sessionmaker(real_engine, expire_on_commit=False)
        city = f"L5Q-XTenant-Update-{uuid.uuid4().hex[:8]}"
        try:
            async with session_factory() as db:
                svc = ServiceabilityService(db=db, actor_role="super_admin")
                area = await svc.create_service_area(
                    TENANT_A, {"coverage_type": "city", "city": city, "state": "TestState"}
                )
            area_id = uuid.UUID(area["id"])

            async with session_factory() as db:
                svc = ServiceabilityService(db=db, actor_role="super_admin")
                with pytest.raises(NotFoundException):
                    await svc.update_service_area(area_id, {"priority": 1}, admin_tenant_id=TENANT_B)

            # Confirm zero mutation occurred.
            async with session_factory() as db:
                row = (await db.execute(text(
                    "SELECT priority FROM tenant_service_areas WHERE id = :aid"
                ), {"aid": str(area_id)})).fetchone()
                assert row[0] != 1, "cross-tenant update must not have applied"
        finally:
            async with session_factory() as db:
                await db.execute(text(
                    "DELETE FROM tenant_service_areas WHERE tenant_id = :tid AND city = :city"
                ), {"tid": str(TENANT_A), "city": city})
                await db.commit()

    @pytest.mark.asyncio
    async def test_admin_tenant_id_mismatch_denies_delete(self, real_engine):
        session_factory = async_sessionmaker(real_engine, expire_on_commit=False)
        city = f"L5Q-XTenant-Delete-{uuid.uuid4().hex[:8]}"
        try:
            async with session_factory() as db:
                svc = ServiceabilityService(db=db, actor_role="super_admin")
                area = await svc.create_service_area(
                    TENANT_A, {"coverage_type": "city", "city": city, "state": "TestState"}
                )
            area_id = uuid.UUID(area["id"])

            async with session_factory() as db:
                svc = ServiceabilityService(db=db, actor_role="super_admin")
                with pytest.raises(NotFoundException):
                    await svc.deactivate_service_area(area_id, admin_tenant_id=TENANT_B)

            async with session_factory() as db:
                row = (await db.execute(text(
                    "SELECT is_active FROM tenant_service_areas WHERE id = :aid"
                ), {"aid": str(area_id)})).fetchone()
                assert row[0] is True, "cross-tenant delete attempt must not have deactivated the row"
        finally:
            async with session_factory() as db:
                await db.execute(text(
                    "DELETE FROM tenant_service_areas WHERE tenant_id = :tid AND city = :city"
                ), {"tid": str(TENANT_A), "city": city})
                await db.commit()

    @pytest.mark.asyncio
    async def test_matching_admin_tenant_id_allows_update(self, real_engine):
        session_factory = async_sessionmaker(real_engine, expire_on_commit=False)
        city = f"L5Q-SameTenant-{uuid.uuid4().hex[:8]}"
        try:
            async with session_factory() as db:
                svc = ServiceabilityService(db=db, actor_role="super_admin")
                area = await svc.create_service_area(
                    TENANT_A, {"coverage_type": "city", "city": city, "state": "TestState"}
                )
            area_id = uuid.UUID(area["id"])

            async with session_factory() as db:
                svc = ServiceabilityService(db=db, actor_role="super_admin")
                updated = await svc.update_service_area(area_id, {"priority": 42}, admin_tenant_id=TENANT_A)
                assert updated["priority"] == 42
        finally:
            async with session_factory() as db:
                await db.execute(text(
                    "DELETE FROM tenant_service_areas WHERE tenant_id = :tid AND city = :city"
                ), {"tid": str(TENANT_A), "city": city})
                await db.commit()


class TestLiveServiceabilityDuplicatePreventionRealDB:
    @pytest.mark.asyncio
    async def test_duplicate_service_area_returns_controlled_409(self, real_engine):
        session_factory = async_sessionmaker(real_engine, expire_on_commit=False)
        city = f"L5Q-Dup-{uuid.uuid4().hex[:8]}"
        payload = {"coverage_type": "city", "city": city, "state": "TestState"}
        try:
            async with session_factory() as db:
                svc = ServiceabilityService(db=db, actor_role="super_admin")
                first = await svc.create_service_area(TENANT_A, payload)
                assert first["city"] == city

            async with session_factory() as db:
                svc = ServiceabilityService(db=db, actor_role="super_admin")
                with pytest.raises(ServiceOSException) as exc:
                    await svc.create_service_area(TENANT_A, payload)
                assert exc.value.status_code == 409
        finally:
            async with session_factory() as db:
                await db.execute(text(
                    "DELETE FROM tenant_service_areas WHERE tenant_id = :tid AND city = :city"
                ), {"tid": str(TENANT_A), "city": city})
                await db.commit()

    @pytest.mark.asyncio
    async def test_two_concurrent_creates_same_coverage_produce_exactly_one_row(self, real_engine):
        """Real concurrency, not a unit test. Before this sprint's advisory-
        lock fix, this reproducibly created 2 duplicate active rows."""
        session_factory = async_sessionmaker(real_engine, expire_on_commit=False)
        city = f"L5Q-Concurrency-{uuid.uuid4().hex[:8]}"
        payload = {"coverage_type": "city", "city": city, "state": "TestState"}

        async def do_create():
            async with session_factory() as db:
                svc = ServiceabilityService(db=db, actor_role="super_admin")
                try:
                    result = await svc.create_service_area(TENANT_A, payload)
                    return result
                except Exception:
                    raise

        try:
            results = await asyncio.gather(do_create(), do_create(), return_exceptions=True)
            successes = [r for r in results if not isinstance(r, Exception)]
            assert len(successes) == 1, f"expected exactly 1 success, got {len(successes)}: {results}"

            async with session_factory() as db:
                count = (await db.execute(text(
                    "SELECT COUNT(*) FROM tenant_service_areas WHERE tenant_id = :tid AND city = :city AND is_active = true"
                ), {"tid": str(TENANT_A), "city": city})).scalar_one()
                assert count == 1, f"expected exactly 1 active row after concurrent creates, found {count}"
        finally:
            async with session_factory() as db:
                await db.execute(text(
                    "DELETE FROM tenant_service_areas WHERE tenant_id = :tid AND city = :city"
                ), {"tid": str(TENANT_A), "city": city})
                await db.commit()


class TestDuplicateRouteRegistrationFinding:
    """Static guard pinning the router-shadowing discovery so it isn't
    silently reintroduced or worsened.

    FINAL-L5-05T closed this: the shadow routes were removed entirely
    rather than left dead, so the duplicate-path assertion below is
    inverted from its original 05Q form -- it now pins the ABSENCE of the
    duplicate, not its presence. See
    tests/test_final_l5_05t_service_area_route_canonicalization.py for the
    full route-uniqueness guard suite."""

    def test_serviceability_router_registered_before_tenant_engine_admin_router(self):
        src = _read("app/main.py")
        idx_serviceability = src.index("from app.engines.serviceability.router import router as serviceability_router")
        idx_admin_tenant = src.index("from app.engines.tenant_engine.admin_router import router as admin_tenant_router")
        assert idx_serviceability < idx_admin_tenant, (
            "Router registration order changed -- re-verify which service-areas "
            "implementation is actually live before trusting either one's fixes."
        )

    def test_tenant_engine_admin_router_no_longer_defines_a_service_areas_path(self):
        admin_router_src = _read("app/engines/tenant_engine/admin_router.py")
        assert '"/{tenant_id}/service-areas"' not in admin_router_src
        assert 'service-areas' not in admin_router_src or 'FINAL-L5-05T' in admin_router_src

    def test_tenant_engine_portal_router_no_longer_defines_a_service_areas_path(self):
        portal_router_src = _read("app/engines/tenant_engine/portal_router.py")
        assert '"/service-areas"' not in portal_router_src
        assert '@router.get("/service-areas")' not in portal_router_src


class TestServiceabilityAdminRouterPassesTenantId:
    def test_admin_update_endpoint_passes_admin_tenant_id(self):
        src = _read("app/engines/serviceability/router.py")
        start = src.index("async def admin_update_service_area(")
        end = src.index("\n\n\n", start)
        assert "admin_tenant_id=tenant_id" in src[start:end]

    def test_admin_delete_endpoint_passes_admin_tenant_id(self):
        src = _read("app/engines/serviceability/router.py")
        start = src.index("async def admin_delete_service_area(")
        end = src.index("\n\n\n", start)
        assert "admin_tenant_id=tenant_id" in src[start:end]


class TestOfferingsAuditNowWritten:
    """admin_suspend_offering/admin_reactivate_offering previously wrote
    zero audit events (confirmed via source read before this sprint's fix).
    This IS a live, reachable code path -- no duplicate-router issue here."""

    def test_suspend_offering_writes_platform_audit(self):
        src = _read("app/engines/tenant_engine/admin_router.py")
        start = src.index("async def admin_suspend_offering(")
        end = src.index("\n\n\n", start)
        block = src[start:end]
        assert "record_platform_audit(" in block
        assert '"provider_offering.suspended"' in block

    def test_reactivate_offering_writes_platform_audit(self):
        src = _read("app/engines/tenant_engine/admin_router.py")
        start = src.index("async def admin_reactivate_offering(")
        end = src.index("\n\n\n", start)
        block = src[start:end]
        assert "record_platform_audit(" in block
        assert '"provider_offering.reactivated"' in block

    def test_offering_row_lookup_scopes_by_both_tenant_and_offering_id(self):
        src = _read("app/engines/tenant_engine/admin_router.py")
        start = src.index("async def _fetch_offering_row(")
        end = src.index("\n\n@router", start)
        block = src[start:end]
        assert "_canonical_enabled_offering_rows(db, tenant_id, offering_id)" in block
        provider_src = _read("app/engines/provider_portal/router.py")
        helper_start = provider_src.index("async def _canonical_enabled_offering_rows(")
        helper_end = provider_src.index("\n\n\n", helper_start)
        helper = provider_src[helper_start:helper_end]
        assert "ts.tenant_id=:tid" in helper
        assert "ts.id=:service_id" in helper
        assert 'params["service_id"]' in helper


class TestAdminTenantServiceServiceAreaMethodsRemoved:
    """FINAL-L5-05T: the AdminTenantService service-area methods pinned as
    'defense-in-depth' in FINAL-L5-05Q were dead code for HTTP traffic
    (confirmed here in 05Q) and have since been removed entirely (mission
    rule: 'do not leave unreachable mutation code presented as active').
    This class now pins their ABSENCE, replacing the old
    TestAdminTenantServiceDefenseInDepthFixesStillCorrect."""

    def test_admin_tenant_service_no_longer_defines_service_area_methods(self):
        src = _read("app/engines/tenant_engine/admin_service.py")
        for method in ("async def list_service_areas(", "async def create_service_area(",
                       "async def update_service_area(", "async def delete_service_area(",
                       "async def _load_area(", "def _area_dict("):
            assert method not in src, f"{method} should have been removed in FINAL-L5-05T"
        assert "FINAL-L5-05T" in src


class TestNoUndiscoveredProviderMutationSurface:
    """Pins the investigation's negative findings so a future change that
    silently adds an ungated mutation surface for brands/zones/capacity/
    SLA is caught by CI rather than discovered live."""

    def test_no_dedicated_provider_brand_zone_capacity_sla_tables_exist(self):
        import subprocess
        result = subprocess.run(
            ["git", "grep", "-l", "-E",
             "__tablename__ = \"provider_(zones|zipcodes|brands|capacity|sla|blackout)",
             "--", "app/"],
            cwd=ROOT, capture_output=True, text=True,
        )
        assert result.stdout.strip() == "", (
            "A provider_zones/zipcodes/brands/capacity/sla/blackout table now "
            "exists -- FINAL-L5-05Q's finding that no such admin mutation "
            "surface exists is stale; re-audit and gate the new surface."
        )
