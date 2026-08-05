"""HOME-SERVICES-ADMIN-GATING: closes the gap flagged in a prior audit pass —
Home Services *operational admin* routers (Catalog Console, Booking Drafts,
Operations, Service Job Assignments, Service Jobs admin actions, and the
Home Services slice of Finance Hub) previously carried NO `require_vertical_enabled`
dependency, unlike the customer-facing booking router which already had it.

Part 1 is a systemic route-inventory test: it walks the live FastAPI app's
registered routes (unwrapping fastapi's `_IncludedRouter` wrapper) and asserts
every endpoint under the gated prefixes carries the `vertical_guard_home_services`
dependency somewhere in its resolved dependency graph. This is deliberately not
a handful of spot checks — it enumerates every method on every path under each
prefix so a newly added endpoint that forgets the guard fails this test.

Part 2 is a functional test against the live server proving: disabling
home_services blocks a real operational endpoint with VERTICAL_DISABLED (not
500), Coaching is unaffected, Business Vertical Controls/audit remain
reachable, and re-enabling restores access.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.in"
ADMIN_PASS = "Password123!"

pytestmark = pytest.mark.anyio

# Prefixes that must carry the home_services vertical guard on every route.
GATED_PREFIXES = [
    "/v1/admin/home-services/service-catalog",
    "/v1/admin/home-services/booking-drafts",
    "/v1/admin/home-services/operations",
    "/v1/admin/service-job-assignments",
    "/v1/admin/service-jobs",
    "/v1/admin/finance/home-services",
]

GUARD_NAME = "vertical_guard_home_services"

# ═══════════════════════════════════════════════════════════════════════════
# Part 3 — Shared routers (provider_portal, complaints, customer_reviews,
# quote_checklist admin routers). These routers are used identically by every
# Business Vertical, so they were NOT given the static router-level
# `vertical_guard_home_services` dependency used above (doing so would wrongly
# block Coaching/Real Estate/etc too). Instead, single-resource endpoints that
# resolve to exactly one tenant-owned record (a tenant_id/job_id/quote_id/
# review_id/flag_id/rework_id/refund_id path param, looked up server-side to
# the owning tenant's `vertical` column) carry the dynamic
# `vertical_guard_dynamic` dependency from
# `app.dependencies.vertical_guard.require_dynamic_vertical_enabled`, which
# is a no-op unless that specific resource's vertical is disabled. Endpoints
# that genuinely span every tenant/vertical at once (lists, summaries,
# templates, policies) are deliberately left with neither guard.
DYNAMIC_GUARD_NAME = "vertical_guard_dynamic"

# (path, methods) pairs that MUST carry the dynamic per-resource guard.
DYNAMIC_GATED_ROUTES = [
    ("/v1/admin/onboarding/providers/{tenant_id}/send-reminder", {"POST"}),
    ("/v1/admin/onboarding/providers/{tenant_id}", {"GET"}),
    ("/v1/admin/onboarding/providers/{tenant_id}/approve", {"POST"}),
    ("/v1/admin/onboarding/providers/{tenant_id}/reject", {"POST"}),
    ("/v1/admin/onboarding/providers/{tenant_id}/request-changes", {"POST"}),
    ("/v1/admin/onboarding/providers/{tenant_id}/refresh", {"POST"}),
    ("/v1/admin/onboarding/providers/{tenant_id}/items/{checklist_key}/override", {"PUT"}),
    ("/v1/admin/bookability/providers/{tenant_id}", {"GET"}),
    ("/v1/admin/bookability/providers/{tenant_id}/audit-logs", {"GET"}),
    ("/v1/admin/bookability/providers/{tenant_id}/refresh", {"POST"}),
    ("/v1/admin/bookability/providers/{tenant_id}/override-visibility", {"POST"}),
    ("/v1/admin/bookability/providers/{tenant_id}/override-visibility", {"DELETE"}),
    ("/v1/admin/bookability/providers/{tenant_id}/override-bookability", {"POST"}),
    ("/v1/admin/bookability/providers/{tenant_id}/override-bookability", {"DELETE"}),
    ("/v1/admin/monetization/providers/{tenant_id}", {"GET"}),
    ("/v1/admin/monetization/providers/{tenant_id}/sync", {"POST"}),
    ("/v1/admin/complaints/{complaint_id}", {"GET"}),
    ("/v1/admin/complaints/{complaint_id}/assign", {"POST"}),
    ("/v1/admin/complaints/{complaint_id}/priority", {"POST"}),
    ("/v1/admin/complaints/{complaint_id}/request-provider-response", {"POST"}),
    ("/v1/admin/complaints/{complaint_id}/messages", {"POST"}),
    ("/v1/admin/complaints/{complaint_id}/messages", {"GET"}),
    ("/v1/admin/complaints/{complaint_id}/propose-resolution", {"POST"}),
    ("/v1/admin/complaints/{complaint_id}/resolutions", {"GET"}),
    ("/v1/admin/complaints/{complaint_id}/reject", {"POST"}),
    ("/v1/admin/complaints/{complaint_id}/resolve", {"POST"}),
    ("/v1/admin/complaints/{complaint_id}/close", {"POST"}),
    ("/v1/admin/complaints/{complaint_id}/events", {"GET"}),
    ("/v1/admin/complaints/{complaint_id}/start-ai-settlement", {"POST"}),
    ("/v1/admin/complaints/{complaint_id}/finalize-settlement", {"POST"}),
    ("/v1/admin/complaints/{complaint_id}/settlement-proposals", {"POST"}),
    ("/v1/admin/complaints/{complaint_id}/settlement-proposals", {"GET"}),
    ("/v1/admin/complaints/{complaint_id}/ai-session", {"GET"}),
    ("/v1/admin/complaints/{complaint_id}/timeline", {"GET"}),
    ("/v1/admin/rework-requests/{rework_id}/approve", {"POST"}),
    ("/v1/admin/rework-requests/{rework_id}/reject", {"POST"}),
    ("/v1/admin/rework-requests/{rework_id}/assign", {"POST"}),
    ("/v1/admin/refund-requests/{refund_id}/approve", {"POST"}),
    ("/v1/admin/refund-requests/{refund_id}/reject", {"POST"}),
    ("/v1/admin/refund-requests/{refund_id}/record", {"POST"}),
    ("/v1/admin/refund-requests/{refund_id}/verify", {"POST"}),
    ("/v1/admin/reviews/{review_id}", {"GET"}),
    ("/v1/admin/reviews/{review_id}/approve", {"POST"}),
    ("/v1/admin/reviews/{review_id}/reject", {"POST"}),
    ("/v1/admin/reviews/{review_id}/hide", {"POST"}),
    ("/v1/admin/reviews/{review_id}", {"DELETE"}),
    ("/v1/admin/reviews/{review_id}/events", {"GET"}),
    ("/v1/admin/review-flags/{flag_id}/resolve", {"POST"}),
    ("/v1/admin/review-replies/{review_id}/approve", {"POST"}),
    ("/v1/admin/review-replies/{review_id}/reject", {"POST"}),
    ("/v1/admin/rating-summaries/tenant/{tenant_id}/recompute", {"POST"}),
    ("/admin/checklist-templates/jobs/{job_id}", {"GET"}),
    ("/admin/quotes/jobs/{job_id}", {"GET"}),
    ("/admin/quotes/{quote_id}", {"GET"}),
    ("/admin/quotes/{quote_id}/events", {"GET"}),
]

# (path, methods) pairs that are genuinely shared/vertical-agnostic (lists,
# summaries, templates, policies) and MUST NOT carry either guard.
SHARED_UNGATED_ROUTES = [
    ("/v1/admin/providers/summary", {"GET"}),
    ("/v1/admin/onboarding/providers", {"GET"}),
    ("/v1/admin/bookability/providers", {"GET"}),
    ("/v1/admin/monetization/providers", {"GET"}),
    ("/v1/admin/complaints/summary", {"GET"}),
    ("/v1/admin/complaints/list", {"GET"}),
    ("/v1/admin/complaints", {"GET"}),
    ("/v1/admin/rework-requests", {"GET"}),
    ("/v1/admin/refund-requests", {"GET"}),
    ("/v1/admin/complaint-policies", {"GET"}),
    ("/v1/admin/reviews/summary", {"GET"}),
    ("/v1/admin/reviews", {"GET"}),
    ("/v1/admin/review-flags", {"GET"}),
    ("/v1/admin/review-replies", {"GET"}),
    ("/v1/admin/review-policies", {"GET"}),
    ("/v1/admin/rating-summaries", {"GET"}),
    ("/v1/admin/rating-summaries/staff", {"GET"}),
    ("/admin/checklist-templates", {"GET"}),
    ("/admin/checklist-templates", {"POST"}),
    ("/admin/checklist-templates/{template_id}", {"GET"}),
]


def _iter_app_routes():
    """Unwraps fastapi's `_IncludedRouter` wrapper (used internally by
    app.include_router in this FastAPI version) to reach the real APIRoute
    objects with their resolved `.dependant`."""
    from app.main import app
    for r in app.routes:
        if type(r).__name__ == "_IncludedRouter":
            yield from r.original_router.routes
        else:
            yield r


def _flatten_dependency_names(dependant, acc=None):
    acc = acc if acc is not None else []
    for sub in dependant.dependencies:
        acc.append(getattr(sub.call, "__name__", "?"))
        _flatten_dependency_names(sub, acc)
    return acc


class TestRouteInventoryGating:
    """Static/systemic proof — enumerates every registered route+method under
    the Home Services operational admin prefixes."""

    def test_every_home_services_admin_route_has_vertical_guard(self):
        checked = []
        ungated = []
        for route in _iter_app_routes():
            path = getattr(route, "path", "")
            if not any(path == p or path.startswith(p + "/") for p in GATED_PREFIXES):
                continue
            dependant = getattr(route, "dependant", None)
            if dependant is None:
                continue
            names = _flatten_dependency_names(dependant)
            methods = sorted(getattr(route, "methods", []) or [])
            checked.append((path, methods))
            if GUARD_NAME not in names:
                ungated.append((path, methods))

        # Sanity: we actually found routes to check (guards against a typo'd
        # prefix silently matching nothing and passing trivially).
        assert len(checked) >= 25, (
            f"expected >=25 routes under gated Home Services admin prefixes, found {len(checked)} "
            "— prefix list may be stale"
        )
        assert not ungated, f"Home Services admin routes missing vertical guard: {ungated}"

    def test_exempted_surfaces_are_not_accidentally_gated(self):
        """Vertical Controls / enable-disable / audit surfaces must remain
        reachable regardless of home_services enabled state — confirm they do
        NOT carry the home_services-specific guard (they're vertical-agnostic
        or self-referential and would deadlock if gated)."""
        exempt_prefixes = [
            "/v1/admin/verticals",
            "/v1/admin/tenant-vertical-enrollments",
            "/v1/admin/catalog",  # modules_router — platform catalog module toggles, not HS-scoped
        ]
        for route in _iter_app_routes():
            path = getattr(route, "path", "")
            if not any(path == p or path.startswith(p + "/") for p in exempt_prefixes):
                continue
            dependant = getattr(route, "dependant", None)
            if dependant is None:
                continue
            names = _flatten_dependency_names(dependant)
            assert GUARD_NAME not in names, f"{path} unexpectedly gated on home_services vertical"


class TestSharedRouterDynamicGating:
    """Static/systemic proof for the 4 shared routers (provider_portal,
    complaints, customer_reviews, quote_checklist admin routers). Unlike Part
    1, these are NOT blanket-prefix-gated -- only specific single-resource
    endpoints carry the dynamic guard, so this walks an explicit route list
    rather than a prefix."""

    def _route_index(self):
        index = {}
        for route in _iter_app_routes():
            path = getattr(route, "path", "")
            dependant = getattr(route, "dependant", None)
            if dependant is None:
                continue
            methods = frozenset(getattr(route, "methods", []) or [])
            index[(path, methods)] = _flatten_dependency_names(dependant)
        return index

    def test_dynamic_gated_routes_carry_the_dynamic_guard(self):
        index = self._route_index()
        missing = []
        for path, methods in DYNAMIC_GATED_ROUTES:
            names = index.get((path, frozenset(methods)))
            if names is None:
                missing.append((path, methods, "ROUTE_NOT_FOUND"))
            elif DYNAMIC_GUARD_NAME not in names:
                missing.append((path, methods, "GUARD_MISSING"))
        assert not missing, f"expected dynamic vertical guard on: {missing}"

    def test_shared_ungated_routes_carry_neither_guard(self):
        index = self._route_index()
        problems = []
        for path, methods in SHARED_UNGATED_ROUTES:
            names = index.get((path, frozenset(methods)))
            if names is None:
                problems.append((path, methods, "ROUTE_NOT_FOUND"))
                continue
            if GUARD_NAME in names or DYNAMIC_GUARD_NAME in names:
                problems.append((path, methods, "UNEXPECTEDLY_GATED"))
        assert not problems, f"shared/vertical-agnostic routes must stay ungated: {problems}"


# ═══════════════════════════════════════════════════════════════════════════
# Functional — live server
# ═══════════════════════════════════════════════════════════════════════════

_TOKENS: dict = {}


async def _login(email, password):
    async with AsyncClient(base_url=BASE, timeout=30) as c:
        r = await c.post("/v1/auth/login", json={"email": email, "password": password})
        return r.json()["data"]["access_token"] if r.status_code == 200 else None


@pytest_asyncio.fixture(scope="module")
async def admin_token(anyio_backend):
    if "admin" not in _TOKENS:
        tok = await _login(ADMIN_EMAIL, ADMIN_PASS)
        assert tok, "admin login failed"
        _TOKENS["admin"] = tok
    return _TOKENS["admin"]


@pytest_asyncio.fixture
async def admin(admin_token):
    async with AsyncClient(base_url=BASE, headers={"Authorization": f"Bearer {admin_token}"}, timeout=30) as c:
        yield c


@pytest_asyncio.fixture
async def ensure_enabled(admin):
    yield
    await admin.post("/v1/admin/verticals/home_services/enable")


class TestFunctionalGating:

    async def test_disabled_blocks_operations_endpoint_with_vertical_disabled(self, admin, ensure_enabled):
        await admin.post("/v1/admin/verticals/home_services/disable", json={"reason": "gating test"})
        r = await admin.get("/v1/admin/home-services/operations")
        assert r.status_code == 403, r.text
        assert r.json().get("error_code") == "VERTICAL_DISABLED"

    async def test_disabled_blocks_catalog_console_endpoint(self, admin, ensure_enabled):
        await admin.post("/v1/admin/verticals/home_services/disable", json={"reason": "gating test"})
        r = await admin.get("/v1/admin/home-services/service-catalog/services")
        assert r.status_code == 403, r.text
        assert r.json().get("error_code") == "VERTICAL_DISABLED"

    async def test_disabled_blocks_service_job_assignments_endpoint(self, admin, ensure_enabled):
        await admin.post("/v1/admin/verticals/home_services/disable", json={"reason": "gating test"})
        r = await admin.get("/v1/admin/service-job-assignments")
        assert r.status_code == 403, r.text
        assert r.json().get("error_code") == "VERTICAL_DISABLED"

    async def test_disabled_blocks_hs_finance_endpoint(self, admin, ensure_enabled):
        await admin.post("/v1/admin/verticals/home_services/disable", json={"reason": "gating test"})
        r = await admin.get("/v1/admin/finance/home-services/summary")
        assert r.status_code == 403, r.text
        assert r.json().get("error_code") == "VERTICAL_DISABLED"

    async def test_shared_finance_endpoints_unaffected_by_home_services_disable(self, admin, ensure_enabled):
        """The rest of Finance Hub (deposits/topups/payouts/wallets — NOT
        home-services-scoped) must remain reachable."""
        await admin.post("/v1/admin/verticals/home_services/disable", json={"reason": "gating test"})
        r = await admin.get("/v1/admin/finance/summary")
        assert r.status_code != 403 or r.json().get("error_code") != "VERTICAL_DISABLED", r.text

    async def test_vertical_controls_audit_and_dpdp_remain_reachable(self, admin, ensure_enabled):
        await admin.post("/v1/admin/verticals/home_services/disable", json={"reason": "gating test"})
        r1 = await admin.get("/v1/admin/verticals", params={"include_disabled": "true"})
        assert r1.status_code == 200, r1.text
        r2 = await admin.get("/v1/admin/verticals/home_services/audit")
        assert r2.status_code == 200, r2.text
        # Re-enable must also stay reachable while disabled (else no recovery path).
        r3 = await admin.post("/v1/admin/verticals/home_services/enable")
        assert r3.status_code == 200, r3.text

    async def test_coaching_vertical_completely_unaffected(self, admin, ensure_enabled):
        before = (await admin.get("/v1/admin/verticals", params={"include_disabled": "true"})).json()["data"]["items"]
        coaching_before = next((v for v in before if v["key"] == "coaching"), None)
        if coaching_before is None:
            pytest.skip("coaching vertical not present in this environment")
        await admin.post("/v1/admin/verticals/home_services/disable", json={"reason": "isolation test"})
        after = (await admin.get("/v1/admin/verticals", params={"include_disabled": "true"})).json()["data"]["items"]
        coaching_after = next(v for v in after if v["key"] == "coaching")
        assert coaching_before["is_enabled"] == coaching_after["is_enabled"]

    async def test_re_enable_restores_operational_access(self, admin, ensure_enabled):
        await admin.post("/v1/admin/verticals/home_services/disable", json={"reason": "gating test"})
        blocked = await admin.get("/v1/admin/home-services/operations")
        assert blocked.status_code == 403

        r = await admin.post("/v1/admin/verticals/home_services/enable")
        assert r.status_code == 200

        restored = await admin.get("/v1/admin/home-services/operations")
        assert restored.status_code == 200, restored.text


# ═══════════════════════════════════════════════════════════════════════════
# Part 4 — Functional proof for the 4 shared routers' dynamic per-resource
# gating, and for the {vertical}-parameterized hs_review_router.
# ═══════════════════════════════════════════════════════════════════════════

import uuid as _uuid


async def _find_home_services_tenant_id(admin: AsyncClient) -> str | None:
    """Discovers a real tenant belonging to home_services via the admin
    onboarding queue, so the provider_portal functional tests exercise the
    dynamic guard against an actual resolvable resource rather than a
    fabricated id."""
    r = await admin.get("/v1/admin/onboarding/providers", params={"vertical_type": "home_services", "page_size": 1})
    if r.status_code != 200:
        return None
    items = r.json().get("data", {}).get("providers", [])
    return items[0]["tenant_id"] if items else None


class TestSharedRouterFunctionalGating:
    """Live proof that the dynamic per-resource guard actually blocks when the
    resolved resource's vertical is disabled, using a REAL home_services
    tenant discovered from the running database (this environment currently
    has exactly one seeded tenant, which is home_services -- there is no
    seeded non-home_services tenant here to prove cross-vertical isolation
    for provider_portal directly; that isolation is instead proven via the
    {vertical}-parameterized hs_review_router below, and via the
    Coaching-unaffected checks already covered in TestFunctionalGating)."""

    async def test_provider_portal_tenant_scoped_endpoint_blocked_when_disabled(self, admin, ensure_enabled):
        tenant_id = await _find_home_services_tenant_id(admin)
        if not tenant_id:
            pytest.skip("no home_services tenant seeded in this environment")

        await admin.post("/v1/admin/verticals/home_services/disable", json={"reason": "shared-router gating test"})
        r = await admin.get(f"/v1/admin/onboarding/providers/{tenant_id}")
        assert r.status_code == 403, r.text
        assert r.json().get("error_code") == "VERTICAL_DISABLED"

        r2 = await admin.get(f"/v1/admin/bookability/providers/{tenant_id}")
        assert r2.status_code == 403, r2.text
        assert r2.json().get("error_code") == "VERTICAL_DISABLED"

    async def test_provider_portal_list_endpoints_unaffected_by_disable(self, admin, ensure_enabled):
        """The multi-tenant list/summary endpoints on the same router must
        stay reachable -- they span every vertical's providers at once and
        were deliberately left ungated."""
        await admin.post("/v1/admin/verticals/home_services/disable", json={"reason": "shared-router gating test"})
        r = await admin.get("/v1/admin/onboarding/providers")
        assert r.status_code == 200, r.text
        r2 = await admin.get("/v1/admin/bookability/providers")
        assert r2.status_code == 200, r2.text
        r3 = await admin.get("/v1/admin/providers/summary")
        assert r3.status_code == 200, r3.text

    async def test_provider_portal_tenant_scoped_endpoint_restored_on_enable(self, admin, ensure_enabled):
        tenant_id = await _find_home_services_tenant_id(admin)
        if not tenant_id:
            pytest.skip("no home_services tenant seeded in this environment")

        await admin.post("/v1/admin/verticals/home_services/disable", json={"reason": "shared-router gating test"})
        blocked = await admin.get(f"/v1/admin/onboarding/providers/{tenant_id}")
        assert blocked.status_code == 403

        r = await admin.post("/v1/admin/verticals/home_services/enable")
        assert r.status_code == 200
        restored = await admin.get(f"/v1/admin/onboarding/providers/{tenant_id}")
        assert restored.status_code == 200, restored.text

    async def test_complaints_reviews_quote_checklist_dynamic_guard_does_not_500(self, admin, ensure_enabled):
        """Environment-limited proof: this database has no seeded complaints/
        reviews/quotes rows, so the dynamic guard's resolver always returns
        None (no matching tenant-owned record) for these three routers here
        -- it cannot be live-proven to actually BLOCK in this environment the
        way the provider_portal/hs_review_router cases above are. What IS
        verified: the dependency is wired (route-inventory test), and it must
        never turn a normal 404 (resource not found) into a 500 when the
        resolver can't find a tenant -- i.e. the None-passthrough path is
        exercised and safe."""
        await admin.post("/v1/admin/verticals/home_services/disable", json={"reason": "shared-router gating test"})
        fake_id = str(_uuid.uuid4())
        for path in (
            f"/v1/admin/complaints/{fake_id}",
            f"/v1/admin/reviews/{fake_id}",
            f"/admin/quotes/{fake_id}",
        ):
            r = await admin.get(path)
            assert r.status_code != 500, f"{path} -> 500: {r.text}"


class TestHsReviewRouterVerticalParamIsolation:
    """The {vertical}-parameterized review router (hs_review_router.py)
    already resolves its vertical dynamically from the path via
    require_vertical_domain_scope and fails closed with VERTICAL_DISABLED --
    this proves it correctly isolates home_services from other verticals on
    the exact same route."""

    async def test_home_services_path_blocked_when_disabled(self, admin, ensure_enabled):
        await admin.post("/v1/admin/verticals/home_services/disable", json={"reason": "hs-review-router test"})
        r = await admin.get("/v1/admin/verticals/home_services/reviews/moderation/summary")
        assert r.status_code == 403, r.text
        assert r.json().get("error_code") == "VERTICAL_DISABLED"

    async def test_other_vertical_same_route_independent_of_home_services_state(self, admin, ensure_enabled):
        """Coaching's own enabled/disabled state (whatever it is in this
        environment) must not change because of the home_services toggle --
        the exact same route path just resolves a different vertical_key."""
        before = await admin.get("/v1/admin/verticals/coaching/reviews/moderation/summary")

        await admin.post("/v1/admin/verticals/home_services/disable", json={"reason": "hs-review-router test"})
        during = await admin.get("/v1/admin/verticals/coaching/reviews/moderation/summary")
        assert during.status_code == before.status_code

        await admin.post("/v1/admin/verticals/home_services/enable")
        after = await admin.get("/v1/admin/verticals/coaching/reviews/moderation/summary")
        assert after.status_code == before.status_code

    async def test_re_enable_restores_home_services_path(self, admin, ensure_enabled):
        await admin.post("/v1/admin/verticals/home_services/disable", json={"reason": "hs-review-router test"})
        blocked = await admin.get("/v1/admin/verticals/home_services/reviews/moderation/summary")
        assert blocked.status_code == 403

        r = await admin.post("/v1/admin/verticals/home_services/enable")
        assert r.status_code == 200
        restored = await admin.get("/v1/admin/verticals/home_services/reviews/moderation/summary")
        assert restored.status_code == 200, restored.text
