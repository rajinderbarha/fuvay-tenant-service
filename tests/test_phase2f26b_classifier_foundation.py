"""Phase 2A Slice 2F-26B — classifier foundation: guard resolution, tenant
authority direction, control fixtures and closed-module canaries.

Slice 2F-26A was blocked by two defects. Both are fixture-guarded here:

  BLOCKER 1  "references tenant_id" was read as "scoped to the caller's
             tenant". `POST /v1/tenants/{tenant_id}/suspend` (super-admin) was
             classified TENANT_PROVIDER on that basis.
  BLOCKER 2  Router-local guard aliases (`_provider_guard =
             require_owner_or_office_staff_mutation`) were unknown to the
             static map, so role resolution degraded silently and
             `POST /v1/provider/notifications/mark-all-read` was classified
             PLATFORM_INTERNAL -- a verdict that would have REMOVED a row
             belonging to the closed platform-notifications module.

No canonical data is edited by this slice. These tests validate the tooling.
"""
from __future__ import annotations

import importlib.util
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANON = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f",
                     "tenant-mutation-endpoint-inventory.csv")
FROZEN_HASH = "2d6ebeee18c152c0"


def _resolver():
    p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "resolve_guards_2f26b.py")
    spec = importlib.util.spec_from_file_location("resolve_guards_2f26b", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def R():
    return _resolver()


@pytest.fixture(scope="module")
def routes(R):
    return R.route_index()


# ══════════════════════════════════════════════════════════════════
# WS1/WS2 — guard resolution completeness
# ══════════════════════════════════════════════════════════════════

class TestGuardResolution:
    def test_every_guard_symbol_resolves(self, R, routes):
        unresolved = []
        for key, rt in routes.items():
            for g in R.route_guards(rt):
                if not g["resolved"]:
                    unresolved.append((key, g["symbol"]))
        assert unresolved == [], f"{len(unresolved)} unresolved: {unresolved[:5]}"

    def test_router_local_alias_resolves_to_its_real_target(self, R, routes):
        """BLOCKER 2 fixture: `_provider_guard` is a module-level alias."""
        key = ("POST", "/v1/provider/notifications/mark-all-read")
        assert key in routes
        guards = R.route_guards(routes[key])
        names = {g["symbol"] for g in guards} | {g["resolved_to"] for g in guards}
        assert "require_owner_or_office_staff_mutation" in names, names

    def test_unresolved_guard_fails_closed_not_open(self, R):
        """A guard the resolver cannot resolve must yield None, never a
        permissive default."""
        fake = [{"symbol": "require_mystery", "resolved_to": "?", "chain": "x",
                 "resolved": False, "permission": "", "roles_resolved": ""}]
        roles, note = R.admitted_roles(fake)
        assert roles is None
        assert "unresolved" in note

    def test_permission_reverse_index_is_exact_not_guessed(self, R):
        """Three-segment and dotted permissions must map exactly."""
        from app.core.permissions import ROLE_PERMISSIONS
        import itertools
        perms = set(itertools.chain.from_iterable(ROLE_PERMISSIONS.values()))
        sample = [p for p in perms if p.count(":") >= 2][:3]
        for p in sample:
            assert R.permission_from_name("require_" + p.replace(":", "_")) == p


# ══════════════════════════════════════════════════════════════════
# WS3 — principal vs target tenant (BLOCKER 1)
# ══════════════════════════════════════════════════════════════════

class TestTenantAuthorityDirection:
    def test_platform_admin_target_tenant_is_not_tenant_provider(self, R, routes):
        """BLOCKER 1 fixture, the exact route that broke 2F-26A."""
        key = ("POST", "/v1/tenants/{tenant_id}/suspend")
        assert key in routes
        out = R.classify(routes[key])
        assert out["tenant_authority"] == "PLATFORM_ADMIN_TARGET_TENANT"
        assert out["persona"] == "PLATFORM_ADMIN_MUTATION", out

    def test_principal_tenant_route_is_tenant_provider(self, R, routes):
        key = ("POST", "/v1/tenant/packages/{package_id}/purchase")
        assert key in routes
        out = R.classify(routes[key])
        assert out["persona"] == "TENANT_PROVIDER_MUTATION", out

    def test_tenant_id_symbol_alone_never_decides(self, R, routes):
        """The same symbol appears in both; only ORIGIN separates them."""
        admin = R.classify(routes[("POST", "/v1/tenants/{tenant_id}/suspend")])
        tenant = R.classify(routes[("POST", "/v1/tenant/packages/{package_id}/purchase")])
        assert admin["persona"] != tenant["persona"]
        assert admin["tenant_authority"] != tenant["tenant_authority"]


# ══════════════════════════════════════════════════════════════════
# WS5 — control fixtures
# ══════════════════════════════════════════════════════════════════

CONTROLS = [
    ("POST", "/v1/tenants/{tenant_id}/suspend", "PLATFORM_ADMIN_MUTATION",
     "platform-admin acting upon a tenant"),
    ("POST", "/v1/provider/notifications/mark-all-read", "TENANT_PROVIDER_MUTATION",
     "provider route behind a router-local guard alias"),
    ("POST", "/v1/customer/reviews/{review_id}/flag", "CUSTOMER_SELF_SERVICE_MUTATION",
     "canonical customer self-service mutation"),
    ("POST", "/v1/reviews/{review_id}/flag", "TENANT_PROVIDER_MUTATION",
     "generic-prefix tenant mutation (legacy review engine)"),
    ("POST", "/v1/provider/reviews/{review_id}/reply", "TENANT_PROVIDER_MUTATION",
     "provider mutation behind require_tenant_owner_mutation"),
    # Mixed role set (admin_finance + tenant_owner) with a PATH tenant whose
    # ownership check lives in the SERVICE (`_assert_owns_tenant_deposit`).
    # The classifier cannot see that from the route, and correctly declines to
    # guess: REQUIRES_MANUAL_ADJUDICATION is the right, safe outcome here.
    ("GET", "/v1/commerce/tenants/{tenant_id}/deposit",
     "REQUIRES_MANUAL_ADJUDICATION", "mutating GET with lazy row creation"),
]


class TestControlFixtures:
    @pytest.mark.parametrize("method,path,expected,label", CONTROLS)
    def test_control(self, R, routes, method, path, expected, label):
        key = (method, path)
        assert key in routes, f"control route not mounted: {key} ({label})"
        out = R.classify(routes[key])
        assert out["persona"] != "UNRESOLVED_FAIL_CLOSED", (label, out)
        if expected is not None:
            assert out["persona"] == expected, (label, out)

    def test_no_control_is_unresolved(self, R, routes):
        """Every control must reach a definite persona.

        Tenant-authority direction may legitimately be UNKNOWN_TENANT_ROLE when
        the persona is already fixed by the resolved ROLE SET -- e.g.
        `mark-all-read` is scoped by `u.user_id`, not by tenant, yet its guard
        admits only tenant-side roles. An earlier draft of this assertion
        demanded tenant authority even in that case and so failed the
        classifier for being correct.
        """
        for method, path, _e, label in CONTROLS:
            out = R.classify(routes[(method, path)])
            assert out["persona"] != "UNRESOLVED_FAIL_CLOSED", (label, out)


# ══════════════════════════════════════════════════════════════════
# WS6 — closed-module canaries
# ══════════════════════════════════════════════════════════════════

CANARIES = [
    ("POST", "/v1/provider/notifications/mark-all-read", "platform_notifications"),
    ("POST", "/v1/provider/reviews/{review_id}/flag", "customer_reviews"),
    ("POST", "/v1/reviews/{review_id}/reply", "legacy review"),
    ("POST", "/v1/tenant/packages/{package_id}/purchase", "Package Commerce"),
    ("POST", "/v1/provider/compliance/requests", "compliance"),
]


class TestClosedModuleCanaries:
    @pytest.mark.parametrize("method,path,module", CANARIES)
    def test_closed_module_route_still_classifies_as_tenant(self, R, routes,
                                                            method, path, module):
        """The classifier must never propose demoting a closed-module row."""
        key = (method, path)
        assert key in routes, f"{module} route vanished: {key}"
        out = R.classify(routes[key])
        assert out["persona"] == "TENANT_PROVIDER_MUTATION", (module, out)

    @pytest.mark.parametrize("method,path,module", CANARIES)
    def test_closed_module_row_present_in_canonical(self, method, path, module):
        import csv
        rows = list(csv.reader(open(CANON, encoding="utf-8")))[1:]
        keys = {(r[0], r[1] if r[1].startswith("/v1/") else "/v1" + r[1]) for r in rows}
        assert (method, path) in keys, f"{module} canonical row missing: {method} {path}"


# ══════════════════════════════════════════════════════════════════
# WS12 — strict canonical edit gate
# ══════════════════════════════════════════════════════════════════

class TestCanonicalFrozen:
    def test_canonical_hash_unchanged(self):
        import hashlib
        h = hashlib.sha256(open(CANON, "rb").read()).hexdigest()[:16]
        assert h == FROZEN_HASH, f"canonical CSV changed: {h} != {FROZEN_HASH}"

    def test_coverage_unchanged(self):
        import csv
        rows = list(csv.reader(open(CANON, encoding="utf-8")))[1:]
        V = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
             "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
             "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}
        assert len(rows) == 313
        assert sum(1 for r in rows if r[6] in V) == 313
