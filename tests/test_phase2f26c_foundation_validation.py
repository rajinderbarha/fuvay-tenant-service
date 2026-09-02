"""Phase 2A Slice 2F-26C — foundation validation: standalone verifier,
runtime-extensible permission semantics, and the eleven hidden-side-effect
routes.

No canonical data is edited by this slice. The canonical hash is asserted
byte-identical.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.path.isdir(os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "workflow-rearchitecture")),
    reason="retired workflow foundation artifacts are intentionally absent",
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANON = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f",
                     "tenant-mutation-endpoint-inventory.csv")
S26C = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f26c")
FROZEN_HASH = "2d6ebeee18c152c0"


def _load(name):
    p = os.path.join(REPO, "scripts", "workflow_rearchitecture", name)
    spec = importlib.util.spec_from_file_location(name[:-3], p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def V():
    return _load("verify_foundation_2f26c.py")


# ══════════════════════════════════════════════════════════════════
# WS2 — runtime-extensible StaffPermission semantics
# ══════════════════════════════════════════════════════════════════

class TestRuntimeExtensiblePermissions:
    """The 146 guards whose permission is absent from ROLE_PERMISSIONS.

    `{super_admin}` is NOT their complete admitted set: a tenant-scoped
    StaffPermission override can admit a staff principal at runtime.
    """

    ABSENT = "catalog:tiers:write"

    def test_control_permission_is_genuinely_absent_from_the_map(self):
        from app.core.permissions import ROLE_PERMISSIONS
        assert not any(self.ABSENT in v for v in ROLE_PERMISSIONS.values())

    def test_super_admin_admitted_statically(self):
        from app.core.permissions import permission_checker
        assert permission_checker.has("super_admin", self.ABSENT)

    def test_staff_without_override_denied(self):
        from app.core.permissions import permission_checker
        assert not permission_checker.has("staff", self.ABSENT)

    def test_staff_with_matching_grant_admitted(self):
        """Proves the set is runtime-EXTENSIBLE, not statically super-admin-only."""
        from app.core.permissions import permission_checker
        assert permission_checker.has("staff", self.ABSENT, overrides={self.ABSENT: True})

    def test_explicit_deny_overrides_grant(self):
        from app.core.permissions import permission_checker
        assert not permission_checker.has("staff", self.ABSENT, overrides={self.ABSENT: False})

    def test_unrelated_grant_does_not_admit(self):
        """A grant for a different permission must not widen this one."""
        from app.core.permissions import permission_checker
        assert not permission_checker.has(
            "staff", self.ABSENT, overrides={"some:other:permission": True})

    def test_unknown_role_fails_closed(self):
        from app.core.permissions import permission_checker
        assert not permission_checker.has("tenant_manager", self.ABSENT)
        assert not permission_checker.has("", self.ABSENT)


# ══════════════════════════════════════════════════════════════════
# WS4 — the eleven hidden-side-effect routes
# ══════════════════════════════════════════════════════════════════

class TestElevenAdjudicated:
    def _rows(self):
        p = os.path.join(S26C, "hidden-side-effect-route-adjudication.csv")
        return list(csv.DictReader(open(p, encoding="utf-8")))

    def test_all_eleven_present(self):
        assert len(self._rows()) == 11

    def test_none_unresolved(self):
        BEHAVIOURS = {"DATABASE_MUTATION", "EXTERNAL_SIDE_EFFECT",
                      "DATABASE_AND_EXTERNAL_MUTATION", "AUDIT_ONLY_MUTATION",
                      "BUSINESS_SIGNIFICANT_CACHE_MUTATION", "TOKEN_OR_SESSION_MUTATION",
                      "PURE_READ_FALSE_POSITIVE", "DEPRECATED_TERMINAL", "DISCONNECTED",
                      "PRODUCT_DECISION_REQUIRED"}
        PERSONAS = {"TENANT_PROVIDER_MUTATION", "CUSTOMER_SELF_SERVICE_MUTATION",
                    "PLATFORM_ADMIN_MUTATION", "PLATFORM_INTERNAL_MUTATION",
                    "PUBLIC_OR_UNAUTHENTICATED_MUTATION", "TRUSTED_CALLBACK_MUTATION",
                    "DEPRECATED_MUTATION", "DISCONNECTED_MUTATION",
                    "PRODUCT_DECISION_REQUIRED"}
        for r in self._rows():
            assert r["behavior"] in BEHAVIOURS, r
            assert r["persona"] in PERSONAS, r

    def test_every_mutation_verdict_has_qualified_call_evidence(self):
        """Unqualified method-name matching caused cross-engine collisions in
        2F-26; every write verdict must name a resolved class.method."""
        for r in self._rows():
            if r["behavior"] == "DATABASE_MUTATION":
                assert r["evidence"], r
                assert ":" in r["evidence"] or r["evidence"] == "handler-level only", r

    def test_qualified_call_graph_names_a_service_class(self):
        p = os.path.join(S26C, "hidden-side-effect-qualified-call-graph.csv")
        rows = list(csv.DictReader(open(p, encoding="utf-8")))
        assert rows
        for r in rows:
            assert r["service_class"] and r["bound_method"]
            assert r["resolution"] == "ANNOTATION_OR_MODULE_IMPORT"

    def test_two_tenant_routes_absent_from_canonical_are_recorded_not_applied(self):
        """The only edit candidates. They are recorded as proposals; the strict
        gate forbids applying them until the validation sample passes."""
        proposed = [r for r in self._rows()
                    if r["persona"] == "TENANT_PROVIDER_MUTATION" and r["in_canonical"] == "no"]
        assert len(proposed) == 2
        paths = {r["path"] for r in proposed}
        assert "/v1/webhooks/endpoints/{endpoint_id}" in paths
        assert "/v1/geo/zones/{zone_id}" in paths


# ══════════════════════════════════════════════════════════════════
# WS1 — the standalone verifier must be able to FAIL
# ══════════════════════════════════════════════════════════════════

class TestVerifierDiscrimination:
    def test_verifier_currently_fails_on_the_missing_sample(self, V):
        """Live proof of discrimination: the sample was not run, and the
        verifier reports exactly that rather than passing."""
        V.FAILURES.clear()
        rc = V.main()
        assert rc == 1
        assert any("validation sample" in f for f in V.FAILURES), V.FAILURES

    def test_failing_condition_is_recorded(self, V):
        V.FAILURES.clear()
        V.check("deliberate", False)
        assert V.FAILURES == ["deliberate"]

    def test_verifier_is_independently_executable(self):
        """Not merely pytest assertions -- it has a __main__ entry point."""
        p = os.path.join(REPO, "scripts", "workflow_rearchitecture",
                         "verify_foundation_2f26c.py")
        src = open(p, encoding="utf-8").read()
        assert 'if __name__ == "__main__":' in src
        assert "sys.exit(main())" in src


# ══════════════════════════════════════════════════════════════════
# WS9 — strict canonical edit gate
# ══════════════════════════════════════════════════════════════════

class TestCanonicalFrozen:
    def test_hash_unchanged(self):
        h = hashlib.sha256(open(CANON, "rb").read()).hexdigest()[:16]
        assert h == FROZEN_HASH, f"canonical changed: {h}"

    def test_coverage_unchanged(self):
        rows = list(csv.reader(open(CANON, encoding="utf-8")))[1:]
        V = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
             "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
             "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}
        assert len(rows) == 313
        assert sum(1 for r in rows if r[6] in V) == 313


# ══════════════════════════════════════════════════════════════════
# WS11 — behavioural invariants
# ══════════════════════════════════════════════════════════════════

class TestBehaviouralInvariants:
    def test_job_close_still_creates_review_request(self):
        import inspect
        from app.engines.field_ops import service as fo
        src = inspect.getsource(fo)
        assert "actor_tenant_id=job.tenant_id" in src and "trusted_internal=True" in src

    def test_package_purchase_self_attestation_remains_closed(self):
        import inspect
        from app.engines.package_commerce import tenant_router as pc
        src = inspect.getsource(pc.tenant_purchase_package)
        assert "require_tenant_owner_mutation" in src and "is_paid=False" in src

    def test_customer_review_idor_protection_remains(self):
        import inspect
        from app.engines.customer_reviews import review_service as rs
        assert "_get_review_scoped" in inspect.getsource(rs.ReviewService.flag_review)

    def test_legacy_review_parent_ownership_remains(self):
        import inspect
        from app.engines.review.service import ReviewService
        assert "field_ops.models import Job" in inspect.getsource(
            ReviewService.create_review_request)

    def test_compliance_withdraw_consent_remains_tenant_scoped(self):
        import inspect
        from app.engines.compliance import provider_router as comp
        assert "require_tenant_owner_mutation" in inspect.getsource(comp)

    def test_legacy_reviews_post_remains_410(self):
        import inspect
        from app.engines.review import router as legacy
        assert "410" in inspect.getsource(legacy.create_review)
