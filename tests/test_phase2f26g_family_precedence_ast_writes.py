"""Phase 2A Slice 2F-26G — deterministic capability-family precedence (D-07),
AST-based write detection (D-08) and fourth-holdout validation.

The fourth holdout reached 23/24, not 24/24, so the strict edit gate fails and
both canonical files are asserted byte-identical. A NEW defect (D-09,
action-token matching misses the hyphenated word `bulk-disable`) was found by
the holdout; the mission forbids fixing it and re-running the same holdout.
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
DOCS = os.path.join(REPO, "docs", "workflow-rearchitecture")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")
S = os.path.join(DOCS, "phase-02a-slice-02f26g")
FROZEN_HASH = "2d6ebeee18c152c0"
MATRIX_HASH = "4389e57d9db6de83"
MANIFEST_HASH = "5a835bcc011e90a1"
MANUAL_HASH = "708a9aaa5a21d00c"
EVIDENCE_HASH = "85a64b8c76d5631c"


def _rows(n, base=S):
    return list(csv.DictReader(open(os.path.join(base, n), encoding="utf-8")))


def _h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name[:-3], os.path.join(REPO, "scripts", "workflow_rearchitecture", name))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def FAM():
    return _load("capability_rules_2f26g.py")


@pytest.fixture(scope="module")
def WD():
    return _load("write_detector_2f26g.py")


@pytest.fixture(scope="module")
def G():
    return _load("authority_model_2f26g.py")


@pytest.fixture(scope="module")
def idx(G):
    return G.route_index()


# ══════════════════════════════════════════════════════════════════
# WS1-3 / D-07 — deterministic family precedence
# ══════════════════════════════════════════════════════════════════

class TestD07Precedence:
    def test_service_areas_outranks_general_tenant(self, FAM):
        fam, rid, lvl, fb = FAM.resolve_family("/v1/tenant/service-areas/x/services/y")
        assert fam == "geography_serviceability"
        assert lvl == 2

    def test_profile_photo_outranks_general_me(self, FAM):
        assert FAM.resolve_family("/v1/me/profile-photo")[0] == "media"

    def test_normal_tenant_governance_route_unaffected(self, FAM):
        assert FAM.resolve_family("/v1/tenants/x/suspend")[0] == "tenant_governance"

    def test_normal_me_route_is_identity_access(self, FAM):
        assert FAM.resolve_family("/v1/me/preferences")[0] == "identity_access"

    def test_two_equal_priority_conflicting_rules_raise(self, FAM):
        import re
        saved = FAM._COMPILED
        FAM._COMPILED = saved + [("Z1", 4, 50, re.compile(r"^/v1/zzz"), "pricing"),
                                 ("Z2", 4, 50, re.compile(r"^/v1/zzz"), "billing")]
        try:
            with pytest.raises(FAM.FamilyConflict):
                FAM.resolve_family("/v1/zzz/x")
        finally:
            FAM._COMPILED = saved

    def test_no_shadowing_over_all_mounted_paths(self, FAM, idx):
        report = FAM.audit(sorted({k[1] for k in idx}))
        assert not report["shadowed"], report["shadowed"][:5]
        assert not report["conflicts"], report["conflicts"][:5]
        assert not report["fallback_captured"], report["fallback_captured"][:5]

    def test_fallback_is_explicit(self, FAM):
        fam, rid, lvl, fb = FAM.resolve_family("/v1/totally/unknown/engine")
        assert fb is True and fam == "other" and rid == "R500"

    def test_moving_two_rows_was_not_the_fix(self, FAM):
        """The repair is a levelled contract, not a reordered list: level is an
        explicit field, and same-level conflicts raise rather than pick one."""
        levels = {lvl for _, lvl, _, _, _ in FAM.RULES}
        assert levels <= {2, 3, 4}
        assert all(pri > 0 for _, _, pri, _, _ in FAM.RULES)


# ══════════════════════════════════════════════════════════════════
# WS4-6 / D-08 — AST write detection vs comparison
# ══════════════════════════════════════════════════════════════════

class TestD08Writes:
    POSITIVE = ["model.is_active = False", "setattr(model, 'is_active', False)",
                "update(Model).values(is_active=False)", "model.counter += 1",
                "db.delete(model)"]
    NEGATIVE = ["x = Model.is_active == True", "if Model.is_active != False: pass",
                "q = query.where(Model.is_active == True)", "r = model.is_active",
                "serialized['is_active'] = model.is_active", "y = a <= b",
                "z = (n := compute())"]

    def test_positives_are_writes(self, WD):
        for s in self.POSITIVE:
            assert WD.writes_model(s), s

    def test_negatives_are_not_writes(self, WD):
        for s in self.NEGATIVE:
            assert not WD.writes_model(s), s

    def test_equality_can_never_be_assignment(self, WD):
        """The grammar guarantees it: == is ast.Compare, = is ast.Assign."""
        assert not WD.writes_model("Model.is_active == value")
        assert WD.writes_model("model.is_active = value")

    def test_the_exposing_route_is_now_pure_read(self, G, idx):
        r = G.resolve(idx[("GET", "/v1/ds/tenants/{tenant_id}/pricing/recommendations")])
        assert r["side_effect"] == "PURE_READ"
        assert r["side_effect_confidence"] == "HIGH_AST"

    def test_the_genuine_mutating_get_still_detected(self, G, idx):
        r = G.resolve(idx[("GET", "/v1/ds/tenants/{tenant_id}/customers/{customer_id}/ltv")])
        assert r["side_effect"] == "DATABASE_MUTATION"

    def test_regex_fallback_is_low_confidence(self, WD):
        # unparseable source forces the fallback path
        hits = WD.ast_writes("def broken(:\n    model.is_active = 1")
        if hits:
            assert WD.confidence("def broken(:\n    model.is_active = 1") == "LOW_REGEX_FALLBACK"

    def test_third_holdout_route_is_a_permanent_fixture(self, G, idx):
        """WS6: the D-08 exposing route stays a burned-set regression."""
        assert ("GET", "/v1/ds/tenants/{tenant_id}/pricing/recommendations") in idx


# ══════════════════════════════════════════════════════════════════
# WS7 — three burned corpora as development regression
# ══════════════════════════════════════════════════════════════════

class TestBurnedCorpora:
    REMAP = {"NO_TENANT_SCOPE": None,
             "CLIENT_ASSERTED_TENANT": "CLIENT_ASSERTED_TARGET_TENANT"}

    # Slice 2F-36: these 5 routes gained a server-derived tenant check
    # (_require_trusted_tenant / equivalent), so the classifier now
    # correctly reads PRINCIPAL_TENANT where a frozen pre-fix manual label
    # says CLIENT_ASSERTED_TENANT.
    DIRECTION_EXEMPT_2F36 = {
        ("POST", "/v1/appointments/staff/{staff_id}/calendar/block"),
        ("DELETE", "/v1/appointments/calendar/blocks/{block_id}"),
        ("POST", "/v1/inventory/reservations/confirm"),
        ("POST", "/v1/ds/tenants/{tenant_id}/demand/recompute"),
        ("POST", "/v1/inventory/tenants/{tenant_id}/items"),
        ("POST", "/v1/appointments/{appointment_id}/reschedule"),
        ("POST", "/v1/dispatch/jobs/{job_id}/dispatch"),
        ("POST", "/v1/inventory/reservations/release"),
        # Slice 2F-37
        ("POST", "/v1/pricing/compute"),
        ("POST", "/v1/pricing/tenants/{tenant_id}/rules"),
        ("DELETE", "/v1/pricing/tenants/{tenant_id}/rules/{rule_id}"),
        ("POST", "/v1/commerce/tenants/{tenant_id}/badges/recalculate"),
        ("POST", "/v1/pricing/tenants/{tenant_id}/zones"),
        ("POST", "/v1/commerce/warranty/claims"),
        # Slice 2F-39A4: payment.router::generate_invoice gained
        # _require_trusted_tenant (was missing it entirely while sibling
        # request_payout already had it); classifier now correctly reads
        # PRINCIPAL_TENANT where the frozen pre-fix label read
        # CLIENT_ASSERTED_TARGET_TENANT.
        ("POST", "/v1/payments/invoices"),
    }
    # reschedule additionally moved persona from REQUIRES_MANUAL_ADJUDICATION
    # (appointment_id-only, no ownership check at hand-label time) to a
    # confident TENANT_PROVIDER_MUTATION now that _assert_appt_access exists.
    PERSONA_EXEMPT_2F36 = {("POST", "/v1/appointments/{appointment_id}/reschedule")}

    def _run(self, G, idx, path):
        man = _rows(os.path.basename(path), os.path.dirname(path))
        p = d = n = 0
        for m in man:
            k = (m["method"], G.norm(m["path"]))
            if k not in idx:
                continue
            r = G.resolve(idx[k]); n += 1
            if k in self.PERSONA_EXEMPT_2F36:
                p += r["persona"] == "TENANT_PROVIDER_MUTATION"
            else:
                p += r["persona"] == m["persona"]
            e = self.REMAP.get(m["tenant_direction"], m["tenant_direction"])
            # Slice 2F-33 fixed update_location's tenant derivation
            # (client-asserted -> server-derived principal); the LIVE
            # classifier now correctly reads PRINCIPAL_TENANT where any
            # frozen pre-fix manual label says CLIENT_ASSERTED_TENANT.
            if k in {("POST", "/v1/geo/tenants/{tenant_id}/staff/{staff_id}/location"),
                     ("POST", "/v1/geo/tenants/{tenant_id}/zones"),
                     ("POST", "/v1/documents"),
                     ("POST", "/v1/documents/{document_id}/send"),
                     ("DELETE", "/v1/rag/knowledge-bases/{kb_id}")} | self.DIRECTION_EXEMPT_2F36:
                d += r["tenant_direction"] == "PRINCIPAL_TENANT"
                continue
            d += (e is None) or r["tenant_direction"] == e
        return n, p, d

    def test_first_corpus(self, G, idx):
        assert self._run(G, idx, os.path.join(
            DOCS, "phase-02a-slice-02f26d", "manual-adjudication-blinded.csv")) == (24, 24, 24)

    def test_second_corpus(self, G, idx):
        assert self._run(G, idx, os.path.join(
            DOCS, "phase-02a-slice-02f26e", "fresh-manual-adjudication.csv")) == (24, 24, 24)

    def test_third_corpus_family_and_side_effect_recovered(self, G, idx):
        man = _rows("third-manual-adjudication.csv",
                    os.path.join(DOCS, "phase-02a-slice-02f26f"))
        fa = se = n = 0
        for m in man:
            r = G.resolve(idx[(m["method"], G.norm(m["path"]))]); n += 1
            fa += r["capability_family"] == m["capability_family"]
            se += r["side_effect"] == m["side_effect"]
        assert (n, fa, se) == (24, 24, 24)


# ══════════════════════════════════════════════════════════════════
# WS8-12 — population, freeze, comparison
# ══════════════════════════════════════════════════════════════════

class TestPopulationAndHoldout:
    def test_eligible_population_is_51(self):
        assert len(_rows("remaining-eligible-population.csv")) == 51

    def test_holdout_disjoint_from_all_three_burned(self):
        b = set()
        for f in ("phase-02a-slice-02f26d/frozen-sample-manifest.csv",
                  "phase-02a-slice-02f26e/fresh-holdout-manifest.csv",
                  "phase-02a-slice-02f26f/third-holdout-manifest.csv"):
            b |= {(r["method"], r["path"]) for r in _rows(os.path.basename(f),
                  os.path.join(DOCS, os.path.dirname(f)))}
        h = {(r["method"], r["path"]) for r in _rows("fourth-holdout-manifest.csv")}
        assert len(b) == 72
        assert not (b & h)

    def test_hashes_frozen(self):
        assert _h(os.path.join(S, "fourth-holdout-manifest.csv")) == MANIFEST_HASH
        assert _h(os.path.join(S, "fourth-manual-adjudication.csv")) == MANUAL_HASH
        assert _h(os.path.join(S, "fourth-manual-evidence-review.csv")) == EVIDENCE_HASH

    def test_holdout_size(self):
        assert len(_rows("fourth-holdout-manifest.csv")) == 24

    def test_unavailable_strata_declared_not_claimed(self):
        strata = _rows("population-strata-availability.csv")
        zero = [s for s in strata if int(s["eligible_members"]) == 0]
        assert len(zero) == 5
        assert all(s["not_representable_reason"] and int(s["selected"]) == 0 for s in zero)


class TestFourthComparison:
    FIELDS = ["side_effect", "capability_family", "capability_action",
              "persona", "tenant_direction", "abstention_reason"]

    def test_agreement_is_23_of_24(self):
        comp = _rows("fourth-tool-manual-comparison.csv")
        full = [r for r in comp
                if all(str(r["agree_" + f]).upper() == "TRUE" for f in self.FIELDS)]
        assert len(comp) == 24
        assert len(full) == 23, f"{len(full)}/24 -- rewrite the slice conclusion"

    def test_d01_through_d08_fields_are_perfect(self):
        """persona, direction, family, side_effect, abstention all 24/24."""
        comp = _rows("fourth-tool-manual-comparison.csv")
        for f in ("persona", "tenant_direction", "capability_family",
                  "side_effect", "abstention_reason"):
            assert sum(str(r["agree_" + f]).upper() == "TRUE" for r in comp) == 24, f

    def test_the_single_disagreement_is_the_new_d09_defect(self):
        comp = _rows("fourth-tool-manual-comparison.csv")
        bad = [r for r in comp
               if not all(str(r["agree_" + f]).upper() == "TRUE" for f in self.FIELDS)]
        assert len(bad) == 1
        r = bad[0]
        assert r["path"] == "/v1/tenants/{tenant_id}/engines/bulk-disable"
        assert r["m_capability_action"] == "deactivate"
        assert r["t_capability_action"] == "create"

    def test_d09_root_cause(self, G, idx):
        """Action-token regex requires `/disable`; the segment is `bulk-disable`,
        so it fell through to the POST default. NOT fixed -- found by the
        holdout that measures the classifier."""
        r = G.resolve(idx[("POST", "/v1/tenants/{tenant_id}/engines/bulk-disable")])
        assert r["capability_action"] == "create"

    def test_abstentions_match_exactly(self):
        comp = _rows("fourth-tool-manual-comparison.csv")
        m = {r["path"] for r in comp if r["m_persona"] == "REQUIRES_MANUAL_ADJUDICATION"}
        t = {r["path"] for r in comp if r["t_persona"] == "REQUIRES_MANUAL_ADJUDICATION"}
        assert m == t


# ══════════════════════════════════════════════════════════════════
# WS13-15 — verifier and strict gate
# ══════════════════════════════════════════════════════════════════

class TestVerifierAndGate:
    @pytest.fixture(scope="class")
    def V(self):
        return _load("verify_foundation_2f26g.py")

    def test_condition_count(self, V):
        assert len(V.conditions()) >= 36

    def test_verifier_exits_non_zero_on_n09(self, V):
        V.FAILURES.clear()
        assert V.main() == 1
        assert any("N09" in f for f in V.FAILURES)
        V.FAILURES.clear()

    def test_selftest_passes_as_subprocess(self):
        p = os.path.join(REPO, "scripts", "workflow_rearchitecture",
                         "verify_foundation_2f26g.py")
        assert subprocess.run([sys.executable, p, "--selftest"],
                              capture_output=True, cwd=REPO).returncode == 0

    def test_canonical_and_matrix_unchanged(self):
        assert _h(CANON) == FROZEN_HASH
        assert _h(MATRIX) == MATRIX_HASH

    def test_coverage_unchanged(self):
        rows = list(csv.reader(open(CANON, encoding="utf-8")))[1:]
        V = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
             "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
             "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}
        assert len(rows) == 313
        assert sum(1 for r in rows if r[6] in V) == 313

    def test_neither_proposed_row_applied(self):
        for r in _rows("proposed-route-reconfirmation.csv"):
            assert r["applied"].upper() == "NO"
            assert r["final_protection"] == "UNPROTECTED"

    def test_historical_artifacts_unchanged(self):
        assert _h(os.path.join(DOCS, "phase-02a-slice-02f26f",
                               "third-manual-adjudication.csv")) == "066b2f8b967eacc8"
        assert _h(os.path.join(DOCS, "phase-02a-slice-02f26e",
                               "fresh-holdout-manifest.csv")) == "aeeb3fe510bf9671"


class TestBehaviouralInvariants:
    def test_canaries(self):
        V = _load("verify_foundation_2f26g.py")
        c = V._canaries()
        assert all(c.values()), [k for k, v in c.items() if not v]

    def test_staffpermission_semantics(self):
        from app.core.permissions import permission_checker as pc
        p = "tenant:plan:manage"
        assert pc.has("super_admin", p)
        assert not pc.has("tenant_owner", p)
        assert pc.has("tenant_owner", p, overrides={p: True})
        assert not pc.has("tenant_owner", p, overrides={p: False})
        assert not pc.has("tenant_manager", p)

    def test_legacy_reviews_410(self):
        import inspect
        from app.engines.review import router as legacy
        assert "410" in inspect.getsource(legacy.create_review)
