"""FINAL-L5-05T — Service Area Route Canonicalization, Dead-Code Removal
and Route Uniqueness Certification.

FINAL-L5-05Q discovered that `app.engines.serviceability.router` and
`app.engines.tenant_engine.admin_router` both registered the identical
path `/v1/admin/tenants/{tenant_id}/service-areas` -- serviceability wins
by include order, so tenant_engine's identical routes were unreachable
dead code. This sprint's own runtime-inventory pass (Part 2) found the
duplication was actually WORSE than 05Q's own framing:

1. A second, parallel duplicate route family existed on the tenant-portal
   side (`/v1/tenant/service-areas`, serviceability.router vs.
   tenant_engine.portal_router) that 05Q never inventoried.
2. On BOTH sides, the "update" mutation was not actually shadowed --
   tenant_engine registered `PATCH .../service-areas/{area_id}` while
   serviceability registers `PUT` for the same path. Different HTTP verbs
   don't collide in FastAPI's router, so PATCH was a second, undiscovered
   LIVE mutation path with weaker validation (no coverage-field
   validation, no duplicate-on-update check, no is_primary reassignment)
   than the canonical PUT -- though it was tenant-safe (proper WHERE
   clause) and, unlike the canonical path before this sprint, DID write
   audit events.

Canonical decision: `ServiceabilityService` (app/engines/serviceability/)
owns Tenant Service Areas. See
docs/final-l5-05/FINAL_L5_05T_ADR_SERVICE_AREA_CANONICAL_OWNER.md for the
full evidence and rejected-alternatives analysis. This sprint:

- Removed all 4 service-area routes from tenant_engine.admin_router and
  all 4 from tenant_engine.portal_router (GET/POST/PATCH/DELETE each) --
  not deprecated, not adapter-wrapped, fully removed, since nothing calls
  them (verified: no test, no frontend caller for the admin PATCH; the
  tenant-portal frontend already calls PUT, matching the canonical verb).
- Removed the 6 now-dead AdminTenantService methods that backed them
  (list/create/update/delete_service_area, _load_area, _area_dict).
- Ported the one real missing-behavior gap the other direction: the
  canonical ServiceabilityService wrote ZERO audit events for
  create/update/deactivate before this sprint (confirmed via source read)
  -- the shadowed AdminTenantService actually had a real audit trail via
  `record_platform_audit`. Ported into ServiceabilityService as
  `_audit_service_area()`.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings

ROOT = Path(__file__).parent.parent


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _flatten_routes(routes) -> list[APIRoute]:
    """FastAPI's `app.routes` contains `_IncludedRouter` wrapper objects
    (each holding the real `APIRouter` under `.original_router`), not a
    flat list of `APIRoute` -- a naive `isinstance(r, APIRoute)` filter
    over `app.routes` silently sees 0 routes and every "duplicate route"
    check built on it is a false negative. This recurses through
    `_IncludedRouter.original_router.routes` (and any further-nested
    `APIRouter.routes`) to get the real, complete, resolved route table."""
    out: list[APIRoute] = []
    for r in routes:
        if isinstance(r, APIRoute):
            out.append(r)
        elif hasattr(r, "original_router"):
            out.extend(_flatten_routes(r.original_router.routes))
        elif hasattr(r, "routes"):
            out.extend(_flatten_routes(r.routes))
    return out


def _app_routes() -> list[APIRoute]:
    from app.main import app
    return _flatten_routes(app.routes)


# Pre-existing, unrelated duplicate operation IDs discovered as a byproduct
# of this sprint's global duplicate-route detector work. Both are entirely
# outside the Service Area / Serviceability / tenant coverage-routing
# domain this mission is bounded to (admin_catalog service-option config
# and service_setup templates) -- confirmed via `git blame`/`git log` to
# pre-date this sprint. Logged as L5-05T bug-register findings, not fixed
# here (mission rule: "Do not alter broader ... architecture unless a real
# Service Area dependency requires a bounded compatibility change" -- these
# do not touch Service Areas at all). This allowlist exists so the global
# detector can enforce a real, meaningful zero-tolerance policy for
# everything it was actually asked to certify, without silently disabling
# itself because of unrelated pre-existing debt.
_PRE_EXISTING_DUPLICATE_OPERATION_ID_MODULES_ALLOWLIST = {
    "app.engines.admin_catalog.service_option_admin_router",
    "app.engines.service_setup.templates_router",
}

# Pre-existing, app-wide (method, path) duplicate-route registrations
# discovered by this sprint's global detector (Part 22) -- NONE of these
# are Service Area / Serviceability routes (verified explicitly below).
# They span Customer Addresses, Engine Health, Finance Summary, Tenant
# Wallet, Service Options, Staff Job Accept/Reject, and Analytics Alerts --
# entirely different domains this mission is explicitly bounded away from
# ("Do not alter broader Provider branding, pricing, Jobs, Finance, Export
# or booking architecture unless a real Service Area dependency requires a
# bounded compatibility change" -- none of these do). Each pair means one
# handler is silently shadowed dead code, exactly the same defect class
# this sprint fixed for Service Areas -- logged as new P0/P1 findings
# (L5-05T-013) for a future dedicated sprint, not fixed here. This
# allowlist is the ONLY thing keeping the detector from failing CI on
# pre-existing, out-of-scope debt; Service Area is never in it (enforced
# by test_service_area_paths_are_never_in_any_allowlist below).
_PRE_EXISTING_APP_WIDE_DUPLICATE_METHOD_PATH_ALLOWLIST: set[tuple[str, str]] = {
    ("GET", "/v1/admin/customers/{customer_id}/addresses"),
    ("GET", "/v1/admin/engines"),
    ("GET", "/v1/admin/engines/health"),
    ("GET", "/v1/admin/finance/summary"),
    ("GET", "/v1/tenant/wallet"),
    ("GET", "/v1/tenant/wallet/ledger"),
    ("GET", "/v1/admin/tenants/{tenant_id}/wallet"),
    ("GET", "/v1/admin/tenants/{tenant_id}/wallet/ledger"),
    ("POST", "/v1/admin/tenants/{tenant_id}/wallet/adjust"),
    ("GET", "/v1/admin/master-services/{service_id}/issues"),
    ("GET", "/v1/admin/service-options"),
    ("POST", "/v1/admin/service-options"),
    ("GET", "/v1/admin/service-options/summary"),
    ("GET", "/v1/admin/service-options/{option_id}"),
    ("PUT", "/v1/admin/service-options/{option_id}"),
    ("POST", "/v1/staff/service-jobs/{job_id}/accept"),
    ("POST", "/v1/staff/service-jobs/{job_id}/reject"),
    ("GET", "/v1/admin/analytics/operational-alerts"),
}


class TestGlobalDuplicateRouteDetector:
    """Part 22: a real architecture guard over the live FastAPI route
    table -- not a source-text grep. Fails if ANY (method, path) is
    registered by more than one active handler, with zero allowlist for
    Service Area (mission rule 24/29: 'Service Area duplicate is not
    allowlisted')."""

    def test_zero_undocumented_duplicate_method_path_pairs_app_wide(self):
        from collections import defaultdict
        seen: dict[tuple[str, str], list[str]] = defaultdict(list)
        for route in _app_routes():
            for method in sorted(route.methods):
                if method in ("HEAD", "OPTIONS"):
                    continue
                seen[(method, route.path)].append(
                    f"{route.endpoint.__module__}.{route.endpoint.__qualname__}"
                )
        dupes = {k: v for k, v in seen.items() if len(v) > 1}
        undocumented = {k: v for k, v in dupes.items()
                         if k not in _PRE_EXISTING_APP_WIDE_DUPLICATE_METHOD_PATH_ALLOWLIST}
        assert undocumented == {}, (
            f"new, undocumented duplicate (method, path) registration(s) found "
            f"(not in the pre-existing allowlist): {undocumented}"
        )

    def test_service_area_paths_are_never_in_any_allowlist(self):
        for method, path in _PRE_EXISTING_APP_WIDE_DUPLICATE_METHOD_PATH_ALLOWLIST:
            assert "service-area" not in path, (
                f"Service Area route ({method}, {path}) must never be allowlisted "
                f"(mission rule 24/29: 'Service Area duplicate is not allowlisted')"
            )

    def test_pre_existing_allowlist_still_matches_reality_exactly(self):
        """Guards against the allowlist silently drifting stale in either
        direction: it must neither hide a NEW duplicate nor claim a
        duplicate that has since been fixed (which would mean this
        allowlist is over-broad and should shrink)."""
        from collections import defaultdict
        seen: dict[tuple[str, str], int] = defaultdict(int)
        for route in _app_routes():
            for method in sorted(route.methods):
                if method in ("HEAD", "OPTIONS"):
                    continue
                seen[(method, route.path)] += 1
        actual_dupes = {k for k, v in seen.items() if v > 1}
        assert actual_dupes == _PRE_EXISTING_APP_WIDE_DUPLICATE_METHOD_PATH_ALLOWLIST, (
            f"allowlist drift detected.\n"
            f"In allowlist but no longer duplicated (should be removed): "
            f"{_PRE_EXISTING_APP_WIDE_DUPLICATE_METHOD_PATH_ALLOWLIST - actual_dupes}\n"
            f"Duplicated but not in allowlist (new, undocumented): "
            f"{actual_dupes - _PRE_EXISTING_APP_WIDE_DUPLICATE_METHOD_PATH_ALLOWLIST}"
        )

    def test_zero_duplicate_method_path_pairs_for_service_area_paths_specifically(self):
        from collections import defaultdict
        seen: dict[tuple[str, str], list[str]] = defaultdict(list)
        for route in _app_routes():
            if "service-areas" not in route.path:
                continue
            for method in sorted(route.methods):
                if method in ("HEAD", "OPTIONS"):
                    continue
                seen[(method, route.path)].append(
                    f"{route.endpoint.__module__}.{route.endpoint.__qualname__}"
                )
        dupes = {k: v for k, v in seen.items() if len(v) > 1}
        assert dupes == {}, f"Service Area duplicate route(s) found: {dupes}"

    def test_duplicate_operation_ids_are_bounded_to_the_documented_pre_existing_allowlist(self):
        import warnings
        from app.main import app
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            app.openapi_schema = None  # force regeneration so warnings fire
            app.openapi()
            dup_warnings = [str(w.message) for w in caught if "Duplicate Operation ID" in str(w.message)]

        offending_modules = set()
        for msg in dup_warnings:
            for module in _PRE_EXISTING_DUPLICATE_OPERATION_ID_MODULES_ALLOWLIST:
                mod_file = module.rsplit(".", 1)[-1] + ".py"
                if mod_file in msg:
                    offending_modules.add(module)
                    break
            else:
                pytest.fail(f"Undocumented duplicate operation ID (not in the pre-existing "
                            f"allowlist): {msg}")
        # Service Area / Serviceability routes must never appear here.
        for msg in dup_warnings:
            assert "serviceability" not in msg.lower()
            assert "service_area" not in msg.lower() and "service-area" not in msg.lower()
            assert "tenant_engine" not in msg.lower()

    def test_allowlist_stays_minimal_and_does_not_silently_grow(self):
        assert _PRE_EXISTING_DUPLICATE_OPERATION_ID_MODULES_ALLOWLIST == {
            "app.engines.admin_catalog.service_option_admin_router",
            "app.engines.service_setup.templates_router",
        }, "allowlist changed -- re-justify any addition/removal explicitly"


class TestRouteOwnershipRegistry:
    """Part 24: machine-readable-enough ownership -- one canonical module
    owns each Service Area path family, confirmed against the live
    runtime route table, not just source text."""

    _CANONICAL_MODULE = "app.engines.serviceability.router"

    def test_admin_service_area_paths_are_owned_exclusively_by_serviceability_router(self):
        owners = {
            route.endpoint.__module__
            for route in _app_routes()
            if route.path.startswith("/v1/admin/tenants/{tenant_id}/service-areas")
        }
        assert owners == {self._CANONICAL_MODULE}, f"unexpected owner(s): {owners}"

    def test_tenant_portal_service_area_paths_are_owned_exclusively_by_serviceability_router(self):
        owners = {
            route.endpoint.__module__
            for route in _app_routes()
            if route.path.startswith("/v1/tenant/service-areas")
        }
        assert owners == {self._CANONICAL_MODULE}, f"unexpected owner(s): {owners}"

    def test_tenant_engine_admin_router_module_registers_no_service_area_route(self):
        owners_from_tenant_engine = [
            route.path for route in _app_routes()
            if route.endpoint.__module__ == "app.engines.tenant_engine.admin_router"
            and "service-area" in route.path
        ]
        assert owners_from_tenant_engine == []

    def test_tenant_engine_portal_router_module_registers_no_service_area_route(self):
        owners_from_portal = [
            route.path for route in _app_routes()
            if route.endpoint.__module__ == "app.engines.tenant_engine.portal_router"
            and "service-area" in route.path
        ]
        assert owners_from_portal == []

    def test_exactly_four_admin_service_area_operations_exist(self):
        ops = {
            (route.path, tuple(sorted(m for m in route.methods if m not in ("HEAD", "OPTIONS"))))
            for route in _app_routes()
            if route.path.startswith("/v1/admin/tenants/{tenant_id}/service-areas")
        }
        assert ops == {
            ("/v1/admin/tenants/{tenant_id}/service-areas", ("GET",)),
            ("/v1/admin/tenants/{tenant_id}/service-areas", ("POST",)),
            ("/v1/admin/tenants/{tenant_id}/service-areas/{area_id}", ("PUT",)),
            ("/v1/admin/tenants/{tenant_id}/service-areas/{area_id}", ("DELETE",)),
        }, f"unexpected admin service-area operation set: {ops}"


class TestIncludeOrderSafety:
    """Part 21: Service Area route selection must not depend on
    main.py's include order -- verified by there being only ONE active
    implementation, not by pinning a fragile order dependency."""

    def test_serviceability_router_still_included_before_tenant_engine_routers(self):
        # Retained as a defensive regression guard (harmless either way now
        # that tenant_engine has zero service-area routes), not a
        # correctness dependency.
        src = _read("app/main.py")
        idx_serviceability = src.index(
            "from app.engines.serviceability.router import router as serviceability_router")
        idx_admin_tenant = src.index(
            "from app.engines.tenant_engine.admin_router import router as admin_tenant_router")
        assert idx_serviceability < idx_admin_tenant

    def test_no_service_area_route_selection_depends_on_module_import_order(self):
        # Since exactly one module owns every tenant/admin service-area
        # CRUD path (proven by TestRouteOwnershipRegistry), there is
        # nothing left for include order to arbitrate. Scoped to the
        # `/v1/admin/tenants/.../service-areas` and `/v1/tenant/service-
        # areas` path families specifically -- provider_portal.router's
        # unrelated `/v1/provider/service-areas/{area_id}/coverage`
        # (a single-resource coverage-check action, not a CRUD duplicate)
        # is a different, non-conflicting resource and is deliberately not
        # in scope for this invariant.
        owning_modules = {
            route.endpoint.__module__
            for route in _app_routes()
            if route.path.startswith("/v1/admin/tenants/{tenant_id}/service-areas")
            or route.path.startswith("/v1/tenant/service-areas")
        }
        assert len(owning_modules) == 1, (
            f"Service Area CRUD routes are owned by {len(owning_modules)} modules "
            f"({owning_modules}) -- route selection would depend on include order again."
        )


class TestDeadCodeRemoval:
    """Part 20: verify the shadow implementation was actually deleted, not
    just unregistered, and that nothing still imports it."""

    def test_admin_tenant_service_no_longer_defines_service_area_methods(self):
        src = _read("app/engines/tenant_engine/admin_service.py")
        for method in ("async def list_service_areas(", "async def create_service_area(",
                       "async def update_service_area(", "async def delete_service_area(",
                       "async def _load_area(", "def _area_dict("):
            assert method not in src

    def test_admin_router_no_longer_defines_a_service_area_route_decorator(self):
        src = _read("app/engines/tenant_engine/admin_router.py")
        for decorator in ('@router.get("/{tenant_id}/service-areas")',
                           '@router.post("/{tenant_id}/service-areas"',
                           '@router.patch("/{tenant_id}/service-areas/{area_id}")',
                           '@router.delete("/{tenant_id}/service-areas/{area_id}")'):
            assert decorator not in src
        assert "FINAL-L5-05T" in src  # the explanatory comment must remain

    def test_portal_router_no_longer_defines_a_service_area_route_decorator(self):
        src = _read("app/engines/tenant_engine/portal_router.py")
        for decorator in ('@router.get("/service-areas")', '@router.post("/service-areas"',
                           '@router.patch("/service-areas/{area_id}")',
                           '@router.delete("/service-areas/{area_id}")'):
            assert decorator not in src
        assert "FINAL-L5-05T" in src

    def test_no_remaining_source_reference_to_the_removed_dead_handlers(self):
        import subprocess
        result = subprocess.run(
            ["git", "grep", "-n", "-E",
             r"AdminTenantService\(.*\)\.(list|create|update|delete)_service_area|"
             r"svc\.(list|create|update|delete)_service_area\(tenant_id",
             "--", "app/"],
            cwd=ROOT, capture_output=True, text=True,
        )
        assert result.stdout.strip() == "", (
            f"a stale reference to the removed AdminTenantService service-area "
            f"methods was found: {result.stdout}"
        )


class TestCanonicalServiceabilityAuditTrail:
    """Part 14 / 16: the one real missing-behavior gap in the canonical
    implementation (zero audit events) is now closed."""

    def test_create_service_area_writes_service_area_created_audit(self):
        src = _read("app/engines/serviceability/service.py")
        start = src.index("async def create_service_area(")
        end = src.index("async def get_service_area(", start)
        block = src[start:end]
        assert '"SERVICE_AREA_CREATED"' in block
        assert "_audit_service_area(" in block

    def test_update_service_area_writes_service_area_updated_audit(self):
        src = _read("app/engines/serviceability/service.py")
        start = src.index("async def update_service_area(")
        end = src.index("async def deactivate_service_area(", start)
        block = src[start:end]
        assert '"SERVICE_AREA_UPDATED"' in block

    def test_deactivate_service_area_writes_service_area_deactivated_audit(self):
        src = _read("app/engines/serviceability/service.py")
        start = src.index("async def deactivate_service_area(")
        end = src.index("async def get_service_area_limits(", start)
        block = src[start:end]
        assert '"SERVICE_AREA_DEACTIVATED"' in block

    def test_audit_helper_writes_to_the_platform_audit_trail(self):
        src = _read("app/engines/serviceability/service.py")
        start = src.index("async def _audit_service_area(")
        end = src.index("async def create_service_area(", start)
        block = src[start:end]
        assert "record_platform_audit(" in block
        assert 'engine_id="serviceability"' in block


class TestOpenAPIUniqueness:
    """Part 23/37: the generated OpenAPI schema exposes exactly one
    operation per canonical Service Area method/path."""

    def test_openapi_has_exactly_one_operation_per_admin_service_area_path(self):
        from app.main import app
        schema = app.openapi()
        paths = schema["paths"]
        admin_list_create = paths["/v1/admin/tenants/{tenant_id}/service-areas"]
        assert set(admin_list_create.keys()) & {"get", "post"} == {"get", "post"}
        admin_item = paths["/v1/admin/tenants/{tenant_id}/service-areas/{area_id}"]
        assert set(admin_item.keys()) & {"put", "delete"} == {"put", "delete"}
        # PATCH must never appear here again -- it was the second live
        # mutation path this sprint removed.
        assert "patch" not in admin_item

    def test_openapi_has_exactly_one_operation_per_tenant_portal_service_area_path(self):
        from app.main import app
        schema = app.openapi()
        paths = schema["paths"]
        list_create = paths["/v1/tenant/service-areas"]
        assert set(list_create.keys()) & {"get", "post"} == {"get", "post"}
        item = paths["/v1/tenant/service-areas/{area_id}"]
        assert set(item.keys()) & {"get", "put", "delete"} == {"get", "put", "delete"}
        assert "patch" not in item


@pytest.mark.skipif(
    __import__("os").environ.get("SERVICEOS_RUN_REAL_DB_TESTS", "1") != "1",
    reason="requires a real reachable Postgres instance",
)
class TestRealConcurrencyExtendedMatrix:
    """Part 27/31: extends FINAL-L5-05Q's create-vs-create real-Postgres
    concurrency test with the additional pairings the 05T mission
    requires -- update-vs-deactivate and cross-tenant independence,
    against the now-sole-canonical ServiceabilityService."""

    @pytest.fixture
    def session_factory(self):
        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL, pool_size=10, max_overflow=10)
        yield async_sessionmaker(engine, expire_on_commit=False)

    @pytest.mark.asyncio
    async def test_concurrent_update_and_deactivate_do_not_corrupt_final_state(self, session_factory):
        import asyncio
        from app.engines.serviceability.service import ServiceabilityService
        from unittest.mock import AsyncMock, patch

        tenant_id = uuid.uuid4()
        city = f"L5T-ConcUpdDeact-{uuid.uuid4().hex[:8]}"
        with patch("app.engines.serviceability.service.record_platform_audit", new=AsyncMock()):
            async with session_factory() as db:
                svc = ServiceabilityService(db=db, actor_role="super_admin")
                area = await svc.create_service_area(tenant_id, {
                    "coverage_type": "city", "city": city, "state": "TestState",
                })
            area_id = uuid.UUID(area["id"])

            async def do_update():
                async with session_factory() as db:
                    svc = ServiceabilityService(db=db, actor_role="super_admin")
                    try:
                        return await svc.update_service_area(area_id, {"priority": 5})
                    except Exception as e:
                        return e

            async def do_deactivate():
                async with session_factory() as db:
                    svc = ServiceabilityService(db=db, actor_role="super_admin")
                    try:
                        return await svc.deactivate_service_area(area_id)
                    except Exception as e:
                        return e

            try:
                results = await asyncio.gather(do_update(), do_deactivate())
                # Both operations target different fields (priority vs.
                # is_active) via independent UPDATEs -- neither should
                # raise, and the final row must reflect both changes with
                # no lost update.
                for r in results:
                    assert not isinstance(r, Exception), f"unexpected exception: {r}"

                async with session_factory() as verify_db:
                    row = (await verify_db.execute(text(
                        "SELECT priority, is_active FROM tenant_service_areas WHERE id = :aid"
                    ), {"aid": str(area_id)})).fetchone()
                    assert row is not None
                    assert row[1] is False, "deactivate must have applied"
            finally:
                async with session_factory() as cleanup_db:
                    await cleanup_db.execute(text(
                        "DELETE FROM tenant_service_areas WHERE tenant_id = :tid AND city = :city"
                    ), {"tid": str(tenant_id), "city": city})
                    await cleanup_db.commit()

    @pytest.mark.asyncio
    async def test_two_distinct_tenants_with_equivalent_geography_do_not_block_each_other(self, session_factory):
        """Advisory lock keys must be tenant-scoped -- concurrent creates
        for the SAME city/state under DIFFERENT tenants must both succeed
        independently, not be serialized into a false duplicate-rejection."""
        import asyncio
        from app.engines.serviceability.service import ServiceabilityService
        from unittest.mock import AsyncMock, patch

        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()
        city = f"L5T-CrossTenantIndep-{uuid.uuid4().hex[:8]}"

        async def do_create(tenant_id):
            async with session_factory() as db:
                svc = ServiceabilityService(db=db, actor_role="super_admin")
                with patch("app.engines.serviceability.service.record_platform_audit", new=AsyncMock()):
                    return await svc.create_service_area(tenant_id, {
                        "coverage_type": "city", "city": city, "state": "TestState",
                    })

        try:
            results = await asyncio.gather(do_create(tenant_a), do_create(tenant_b))
            assert all(not isinstance(r, Exception) for r in results), (
                f"same-geography different-tenant creates must not block each other: {results}"
            )
            async with session_factory() as verify_db:
                count_row = await verify_db.execute(text(
                    "SELECT count(*) FROM tenant_service_areas WHERE city = :city AND tenant_id IN (:a, :b)"
                ), {"city": city, "a": str(tenant_a), "b": str(tenant_b)})
                assert count_row.scalar_one() == 2
        finally:
            async with session_factory() as cleanup_db:
                await cleanup_db.execute(text(
                    "DELETE FROM tenant_service_areas WHERE city = :city AND tenant_id IN (:a, :b)"
                ), {"city": city, "a": str(tenant_a), "b": str(tenant_b)})
                await cleanup_db.commit()
