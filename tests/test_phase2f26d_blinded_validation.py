"""Phase 2A Slice 2F-26D — blinded stratified classifier validation.

The sample was frozen before any classifier verdict was generated, and the
manual adjudications were frozen before the classifier was run. The sample
found real defects, so the strict edit gate fails and the canonical CSV is
asserted byte-identical.

These tests deliberately assert the FAILURE. Slice 2F-26D is forbidden from
tuning the classifier and re-running the same sample as independent proof, so
the recorded outcome is the defect, not a repair.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANON = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f",
                     "tenant-mutation-endpoint-inventory.csv")
S26D = os.path.join(REPO, "docs", "workflow-rearchitecture", "phase-02a-slice-02f26d")
FROZEN_HASH = "2d6ebeee18c152c0"
MANIFEST_HASH = "bc878c81f76e54e6"
MANUAL_HASH = "ad0e23e162b4fb6c"


def _rows(name):
    return list(csv.DictReader(open(os.path.join(S26D, name), encoding="utf-8")))


def _h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


@pytest.fixture(scope="module")
def V():
    p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "verify_foundation_2f26d.py")
    spec = importlib.util.spec_from_file_location("v26d", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ══════════════════════════════════════════════════════════════════
# WS1 — sample freeze and blinding discipline
# ══════════════════════════════════════════════════════════════════

class TestSampleFreeze:
    def test_manifest_hash_matches_the_frozen_value(self):
        """If the manifest changed after freezing, the blinding claim is void."""
        assert _h(os.path.join(S26D, "frozen-sample-manifest.csv")) == MANIFEST_HASH

    def test_manual_verdicts_hash_matches_the_frozen_value(self):
        assert _h(os.path.join(S26D, "manual-adjudication-blinded.csv")) == MANUAL_HASH

    def test_sample_is_at_least_twenty_routes(self):
        assert len(_rows("frozen-sample-manifest.csv")) >= 20

    def test_sample_is_stratified(self):
        assert len({r["stratum"] for r in _rows("frozen-sample-manifest.csv")}) >= 4

    def test_prior_exposure_is_declared_not_hidden(self):
        """Routes used as 2F-26B control fixtures are not blind and say so."""
        man = _rows("frozen-sample-manifest.csv")
        assert any(r["prior_exposure"] == "CONTROL_FIXTURE_NOT_BLIND" for r in man)


# ══════════════════════════════════════════════════════════════════
# WS2 — the sample found defects; agreement is NOT 100%
# ══════════════════════════════════════════════════════════════════

class TestAgreementFails:
    def test_combined_agreement_is_below_one_hundred_percent(self):
        comp = _rows("tool-vs-manual-comparison.csv")
        both = [r for r in comp
                if r["agree_persona"] == "AGREE" and r["agree_tenant"] == "AGREE"]
        assert len(both) < len(comp), "gate would pass -- rewrite this slice's conclusion"
        assert len(both) == 4 and len(comp) == 24

    def test_two_routes_are_mis_personaed_as_platform_admin(self):
        """require_tenant_mutation_permission with a permission absent from
        ROLE_PERMISSIONS resolves statically to {super_admin}; the classifier
        then calls the route platform-admin. 2F-26C proved that permission is
        runtime-extensible, so the collapse is wrong."""
        comp = _rows("tool-vs-manual-comparison.csv")
        bad = [r for r in comp if r["agree_persona"] == "DISAGREE"]
        assert len(bad) == 2
        assert {r["path"] for r in bad} == {
            "/v1/tenants/{tenant_id}/plan/upgrade",
            "/v1/tenants/{tenant_id}/terminate/confirm"}
        for r in bad:
            assert r["tool_persona"] == "PLATFORM_ADMIN_MUTATION"
            assert r["manual_persona"] == "TENANT_PROVIDER_MUTATION"

    def test_the_mis_personaed_permissions_really_are_runtime_extensible(self):
        """Proves the manual verdict, not merely asserts it."""
        from app.core.permissions import ROLE_PERMISSIONS, permission_checker
        for perm in ("tenant:plan:manage", "tenant:terminate"):
            assert not any(perm in v for v in ROLE_PERMISSIONS.values())
            assert permission_checker.has("super_admin", perm)
            assert not permission_checker.has("tenant_owner", perm)
            assert permission_checker.has("tenant_owner", perm, overrides={perm: True})

    def test_tenant_direction_is_unknown_on_most_of_the_sample(self):
        comp = _rows("tool-vs-manual-comparison.csv")
        unknown = [r for r in comp if r["tool_tenant"] == "UNKNOWN_TENANT_ROLE"]
        assert len(unknown) == 14

    def test_taxonomy_mismatch_is_accounted_separately_from_classifier_defect(self):
        """Four disagreements are my own vocabulary error, not the tool's."""
        VOCAB = {"PRINCIPAL_TENANT", "PLATFORM_ADMIN_TARGET_TENANT",
                 "CLIENT_ASSERTED_TENANT", "UNKNOWN_TENANT_ROLE"}
        manual = _rows("manual-adjudication-blinded.csv")
        assert len([r for r in manual if r["tenant_direction"] not in VOCAB]) == 4


# ══════════════════════════════════════════════════════════════════
# WS4 — verifier negative fixtures
# ══════════════════════════════════════════════════════════════════

class TestVerifierNegativeFixtures:
    def test_sixteen_named_conditions(self, V):
        assert len(V.conditions()) == 16

    def test_every_condition_can_produce_a_failure(self, V):
        """A check that cannot fail is not a check."""
        for name, _sat, _d in V.conditions():
            V.FAILURES.clear()
            V.check(name, False)
            assert V.FAILURES == [name]
        V.FAILURES.clear()

    def test_verifier_exits_non_zero_right_now(self, V):
        V.FAILURES.clear()
        assert V.main() == 1
        assert len(V.FAILURES) == 6
        V.FAILURES.clear()

    def test_verifier_is_independently_executable(self):
        p = os.path.join(REPO, "scripts", "workflow_rearchitecture",
                         "verify_foundation_2f26d.py")
        rc = subprocess.run([sys.executable, p], capture_output=True, cwd=REPO).returncode
        assert rc == 1

    def test_selftest_mode_passes(self, V):
        V.FAILURES.clear()
        assert V.selftest() == 0
        V.FAILURES.clear()


# ══════════════════════════════════════════════════════════════════
# WS5 — strict edit gate: nothing applied
# ══════════════════════════════════════════════════════════════════

class TestCanonicalFrozen:
    def test_hash_unchanged(self):
        assert _h(CANON) == FROZEN_HASH

    def test_coverage_unchanged(self):
        rows = list(csv.reader(open(CANON, encoding="utf-8")))[1:]
        V = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
             "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
             "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}
        assert len(rows) == 313
        assert sum(1 for r in rows if r[6] in V) == 313

    def test_neither_proposed_row_was_applied(self):
        for r in _rows("proposed-canonical-row-diff.csv"):
            assert r["applied"].upper() == "NO"

    def test_classifier_source_was_not_tuned_this_slice(self):
        """The mission forbids tuning the classifier and re-running the same
        sample as independent proof."""
        p = os.path.join(REPO, "scripts", "workflow_rearchitecture",
                         "resolve_guards_2f26b.py")
        assert _h(p) == "b1e61c218e745194"


# ══════════════════════════════════════════════════════════════════
# WS6 — behavioural invariants (closures intact)
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
