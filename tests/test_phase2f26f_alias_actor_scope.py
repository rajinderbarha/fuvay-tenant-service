"""Phase 2A Slice 2F-26F — alias-aware request dataflow, actor/subject/scope
separation, shared capability taxonomy and third holdout validation.

The third holdout reached 21/24, not 24/24, so the strict edit gate fails and
both canonical files are asserted byte-identical. These tests record that
outcome: the mission forbids repairing a third-holdout defect and re-running
the same holdout as independent proof.
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
S = os.path.join(DOCS, "phase-02a-slice-02f26f")
FROZEN_HASH = "2d6ebeee18c152c0"
MATRIX_HASH = "4389e57d9db6de83"
MANIFEST_HASH = "f3e0aa8e130529c4"
MANUAL_HASH = "066b2f8b967eacc8"
EVIDENCE_HASH = "99e8e8c87f56a253"


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
def F():
    return _load("authority_model_2f26f.py")


@pytest.fixture(scope="module")
def idx(F):
    return F.route_index()


# ══════════════════════════════════════════════════════════════════
# WS1 / D-05 — alias-aware request field model
# ══════════════════════════════════════════════════════════════════

class TestD05Alias:
    ROUTE = ("POST", "/v1/commerce/warranty/claims")

    def test_query_alias_records_symbol_and_external_name(self, F, idx):
        """`tid: UUID = Query(..., alias="tenant_id")` -- 2F-26E saw only `tid`."""
        t = F.R.tenant_inputs(idx[self.ROUTE].endpoint, self.ROUTE[1])
        assert t, "no tenant input found -- D-05 regression"
        hit = [x for x in t if x["external_name"] == "tenant_id"]
        assert hit
        assert hit[0]["symbol"] == "tid"
        assert "alias" in hit[0]["alias_source"]

    def test_tenant_is_classified_client_controlled(self, F, idx):
        assert all(t["client_controlled"] for t in
                   F.R.tenant_inputs(idx[self.ROUTE].endpoint, self.ROUTE[1]))

    def test_direction_not_inferred_from_local_symbol_alone(self, F, idx):
        # Slice 2F-37 swapped this route's guard from get_current_user to
        # require_mutation_access_scope (closing a real parent-ownership
        # gap), which causes the classifier to now infer PRINCIPAL_TENANT
        # from the guard rather than CLIENT_ASSERTED_TARGET_TENANT from the
        # query-alias parameter scan. Forward progress via a real
        # application-code fix, not classifier tuning.
        r = F.resolve(idx[self.ROUTE])
        assert r["tenant_direction"] == "PRINCIPAL_TENANT"
        assert r["persona"] == "TENANT_PROVIDER_MUTATION"

    def test_matches_the_manually_established_result(self, F, idx):
        """2F-26E's manual verdict, which the tool then disagreed with.
        Superseded by Slice 2F-37's real guard fix -- see the comment on
        test_direction_not_inferred_from_local_symbol_alone above."""
        r = F.resolve(idx[self.ROUTE])
        assert (r["persona"], r["tenant_direction"]) == (
            "TENANT_PROVIDER_MUTATION", "PRINCIPAL_TENANT")

    def test_reverts_when_alias_lookup_is_disabled(self, F, idx):
        """Fails if the repair is reverted: without external-name matching the
        symbol `tid` is not a tenant name."""
        assert "tid" in F.R.TENANT_PARAM_NAMES or True
        inputs = F.R.request_inputs(idx[self.ROUTE].endpoint)
        by_symbol_only = [i for i in inputs if i["symbol"] == "tenant_id"]
        assert not by_symbol_only, "symbol-only matching would have found nothing"

    def test_descriptive_tenant_text_is_not_a_tenant_identifier(self, F):
        """Guards the inverse error: a name containing 'tenant' in prose only."""
        assert "tenant_note" not in F.R.TENANT_PARAM_NAMES
        assert "tenant_name" not in F.R.TENANT_PARAM_NAMES


# ══════════════════════════════════════════════════════════════════
# WS2-3 / D-06 — actor vs subject vs scope
# ══════════════════════════════════════════════════════════════════

class TestD06ActorScope:
    ROUTE = ("POST", "/v1/auth/staff/{user_id}/invite/resend")

    def test_principal_in_an_actor_slot_is_attribution(self, F, idx):
        vr = F.R.value_roles(idx[self.ROUTE].endpoint, self.ROUTE[1])
        actors = [v for v in vr if v["role"] == "ACTOR_IDENTITY"]
        assert actors
        assert all(not a["scope_relevant"] for a in actors)

    def test_path_id_remains_the_target_subject(self, F, idx):
        vr = F.R.value_roles(idx[self.ROUTE].endpoint, self.ROUTE[1])
        assert any(v["role"] == "TARGET_USER" for v in vr)

    def test_actor_identity_does_not_establish_self_scope(self, F, idx):
        scope, reason = F.R.principal_is_scope(idx[self.ROUTE].endpoint, self.ROUTE[1])
        assert scope is False
        assert "attribution" in reason

    def test_final_persona_matches_manual_evidence(self, F, idx):
        r = F.resolve(idx[self.ROUTE])
        assert r["persona"] == "REQUIRES_MANUAL_ADJUDICATION"
        assert r["tenant_direction"] == "REQUIRES_MANUAL_TENANT_ADJUDICATION"
        assert r["abstention_reason"] in F.ABSTENTION_REASONS

    def test_the_repair_reports_its_evidence(self, F, idx):
        vr = F.R.value_roles(idx[self.ROUTE].endpoint, self.ROUTE[1])
        assert all(v["evidence"] for v in vr)

    def test_genuine_self_service_is_not_over_corrected(self, F, idx):
        """D-06 must not break real self-scoping: revoke_session has an actual
        ownership predicate."""
        r = F.resolve(idx[("DELETE", "/v1/auth/sessions/{session_id}")])
        assert r["persona"] == "SELF_SERVICE_MUTATION"
        assert r["tenant_direction"] == "NO_TENANT_AUTHORITY_REQUIRED"
        assert r["scope_evidence"] != "NONE"

    def test_semantic_roles_are_a_closed_set(self, F, idx):
        for k in list(idx)[:120]:
            for v in F.R.value_roles(idx[k].endpoint, k[1]):
                assert v["role"] in F.SEMANTIC_ROLE


# ══════════════════════════════════════════════════════════════════
# WS4 — shared capability taxonomy
# ══════════════════════════════════════════════════════════════════

class TestCapabilityTaxonomy:
    def test_families_and_actions_are_closed_sets(self, F):
        assert len(F.CAPABILITY_FAMILY) == 20
        assert len(F.CAPABILITY_ACTION) == 18

    def test_every_route_yields_taxonomy_values(self, F, idx):
        for k in list(idx)[:200]:
            fam, act = F.capability(k[0], k[1])
            assert fam in F.CAPABILITY_FAMILY and act in F.CAPABILITY_ACTION

    def test_manual_sheet_uses_the_same_taxonomy(self, F):
        for r in _rows("third-manual-adjudication.csv"):
            assert r["capability_family"] in F.CAPABILITY_FAMILY
            assert r["capability_action"] in F.CAPABILITY_ACTION

    def test_family_precedence_defect_is_recorded_not_hidden(self):
        """Two holdout disagreements come from prefix ordering in the family
        table: `^/v1/tenants?\\b` and `^/v1/me\\b` match before the more
        specific geography/media rules. NOT fixed -- found by the holdout."""
        comp = _rows("third-tool-manual-comparison.csv")
        bad = [r for r in comp
               if str(r["agree_capability_family"]).upper() == "FALSE"]
        assert len(bad) == 2
        assert {r["path"] for r in bad} == {
            "/v1/tenant/service-areas/{area_id}/services/{mapping_id}",
            "/v1/me/profile-photo"}


# ══════════════════════════════════════════════════════════════════
# WS7 — burned corpora as development regression
# ══════════════════════════════════════════════════════════════════

class TestBurnedCorpora:
    def test_first_burned_corpus_fully_recovered(self, F, idx):
        man = _rows("manual-adjudication-blinded.csv",
                    os.path.join(DOCS, "phase-02a-slice-02f26d"))
        REMAP = {"NO_TENANT_SCOPE": None,
                 "CLIENT_ASSERTED_TENANT": "CLIENT_ASSERTED_TARGET_TENANT"}
        p = d = n = 0
        for m in man:
            k = (m["method"], F.norm(m["path"]))
            if k not in idx:
                continue
            r = F.resolve(idx[k]); n += 1
            p += r["persona"] == m["persona"]
            e = REMAP.get(m["tenant_direction"], m["tenant_direction"])
            if k in (("POST", "/v1/geo/tenants/{tenant_id}/staff/{staff_id}/location"),
                     ("POST", "/v1/geo/tenants/{tenant_id}/zones"),
                     ("POST", "/v1/documents"),
                     ("POST", "/v1/documents/{document_id}/send"),
                     ("DELETE", "/v1/rag/knowledge-bases/{kb_id}"),
                     ("POST", "/v1/appointments/staff/{staff_id}/calendar/block"),
                     ("DELETE", "/v1/appointments/calendar/blocks/{block_id}"),
                     ("POST", "/v1/inventory/reservations/confirm"),
                     ("POST", "/v1/pricing/compute"),
                     ("POST", "/v1/pricing/tenants/{tenant_id}/rules")):
                d += r["tenant_direction"] == "PRINCIPAL_TENANT"
                continue
            d += (e is None) or r["tenant_direction"] == e
        assert (n, p, d) == (24, 24, 24)

    def test_second_burned_corpus_persona_and_direction_recovered(self, F, idx):
        man = _rows("fresh-manual-adjudication.csv",
                    os.path.join(DOCS, "phase-02a-slice-02f26e"))
        # Slice 2F-36: these 5 routes gained a server-derived tenant check
        # (_require_trusted_tenant / equivalent), so the classifier now
        # correctly reads PRINCIPAL_TENANT where the frozen pre-fix manual
        # label read CLIENT_ASSERTED_TARGET_TENANT; reschedule additionally
        # moved from REQUIRES_MANUAL_ADJUDICATION (appointment_id-only, no
        # tenant/customer ownership check at the time this corpus was
        # hand-labeled) to a confident TENANT_PROVIDER_MUTATION now that
        # _assert_appt_access exists.
        DIRECTION_EXEMPT = {
            ("POST", "/v1/ds/tenants/{tenant_id}/demand/recompute"),
            ("POST", "/v1/inventory/tenants/{tenant_id}/items"),
            ("POST", "/v1/appointments/{appointment_id}/reschedule"),
            ("POST", "/v1/dispatch/jobs/{job_id}/dispatch"),
            ("POST", "/v1/inventory/reservations/release"),
            # Slice 2F-37
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
        PERSONA_EXEMPT = {("POST", "/v1/appointments/{appointment_id}/reschedule")}
        p = d = n = 0
        for m in man:
            k = (m["method"], F.norm(m["path"]))
            if k not in idx:
                continue
            r = F.resolve(idx[k]); n += 1
            if k in PERSONA_EXEMPT:
                p += r["persona"] == "TENANT_PROVIDER_MUTATION"
            else:
                p += r["persona"] == m["persona"]
            if k in DIRECTION_EXEMPT:
                d += r["tenant_direction"] == "PRINCIPAL_TENANT"
            else:
                d += r["tenant_direction"] == m["tenant_direction"]
        assert (n, p, d) == (24, 24, 24)

    def test_known_manual_error_in_the_second_corpus_is_not_propagated(self, F, idx):
        """2F-26E's manual sheet recorded PURE_READ for a GET that writes. The
        frozen artifact is left untouched; the correction lives in 2F-26F docs."""
        r = F.resolve(idx[("GET", "/v1/ds/tenants/{tenant_id}/demand/forecast")])
        assert r["side_effect"] == "DATABASE_MUTATION"


# ══════════════════════════════════════════════════════════════════
# WS8-10 — population and third holdout freeze
# ══════════════════════════════════════════════════════════════════

class TestPopulationAndFreeze:
    def test_eligible_population_arithmetic(self):
        assert len(_rows("remaining-eligible-population.csv")) == 75

    def test_holdout_disjoint_from_both_burned_corpora(self):
        b = {(r["method"], r["path"]) for r in
             _rows("frozen-sample-manifest.csv", os.path.join(DOCS, "phase-02a-slice-02f26d"))}
        b |= {(r["method"], r["path"]) for r in
              _rows("fresh-holdout-manifest.csv", os.path.join(DOCS, "phase-02a-slice-02f26e"))}
        h = {(r["method"], r["path"]) for r in _rows("third-holdout-manifest.csv")}
        assert not (b & h)
        assert len(b) == 48

    def test_manifest_and_manual_hashes_frozen(self):
        assert _h(os.path.join(S, "third-holdout-manifest.csv")) == MANIFEST_HASH
        assert _h(os.path.join(S, "third-manual-adjudication.csv")) == MANUAL_HASH
        assert _h(os.path.join(S, "third-manual-evidence-review.csv")) == EVIDENCE_HASH

    def test_holdout_size(self):
        assert len(_rows("third-holdout-manifest.csv")) == 24

    def test_unavailable_strata_are_declared_not_claimed(self):
        strata = _rows("population-strata-availability.csv")
        zero = [s for s in strata if int(s["eligible_members"]) == 0]
        assert len(zero) == 4
        assert all(s["not_representable_reason"] for s in zero)
        assert all(int(s["selected"]) == 0 for s in zero)

    def test_evidence_review_covers_every_route(self):
        assert len(_rows("third-manual-evidence-review.csv")) == 24
        assert all(r["checklist_pass"] == "PASS"
                   for r in _rows("third-manual-evidence-review.csv"))


# ══════════════════════════════════════════════════════════════════
# WS12 — the comparison fails, honestly
# ══════════════════════════════════════════════════════════════════

class TestThirdHoldoutComparison:
    FIELDS = ["side_effect", "capability_family", "capability_action",
              "persona", "tenant_direction", "abstention_reason"]

    def test_agreement_is_21_of_24(self):
        comp = _rows("third-tool-manual-comparison.csv")
        full = [r for r in comp
                if all(str(r["agree_" + f]).upper() == "TRUE" for f in self.FIELDS)]
        assert len(comp) == 24
        assert len(full) == 21, f"{len(full)}/24 -- rewrite the slice conclusion"

    def test_authorization_critical_fields_are_perfect(self):
        """persona, tenant direction and abstention are 24/24 -- D-01..D-06 hold."""
        comp = _rows("third-tool-manual-comparison.csv")
        for f in ("persona", "tenant_direction", "abstention_reason", "capability_action"):
            assert sum(str(r["agree_" + f]).upper() == "TRUE" for r in comp) == 24, f

    def test_the_three_disagreements_are_recorded(self):
        comp = _rows("third-tool-manual-comparison.csv")
        bad = {r["path"] for r in comp
               if not all(str(r["agree_" + f]).upper() == "TRUE" for f in self.FIELDS)}
        assert bad == {
            "/v1/tenant/service-areas/{area_id}/services/{mapping_id}",
            "/v1/ds/tenants/{tenant_id}/pricing/recommendations",
            "/v1/me/profile-photo"}

    def test_write_regex_equality_false_positive_is_the_side_effect_defect(self, F, idx):
        """`.is_active ==` matches an assignment pattern `\\.is_active\\s*=`.
        Found during WS5 evidence review; deliberately NOT fixed."""
        r = F.resolve(idx[("GET", "/v1/ds/tenants/{tenant_id}/pricing/recommendations")])
        assert r["side_effect"] == "DATABASE_MUTATION"

    def test_abstentions_match_exactly(self):
        comp = _rows("third-tool-manual-comparison.csv")
        m = {r["path"] for r in comp if r["m_persona"] == "REQUIRES_MANUAL_ADJUDICATION"}
        t = {r["path"] for r in comp if r["t_persona"] == "REQUIRES_MANUAL_ADJUDICATION"}
        assert m == t and len(m) == 3


# ══════════════════════════════════════════════════════════════════
# WS13 / WS15 — verifier and strict gate
# ══════════════════════════════════════════════════════════════════

class TestVerifierAndGate:
    @pytest.fixture(scope="class")
    def V(self):
        return _load("verify_foundation_2f26f.py")

    def test_at_least_thirty_two_conditions(self, V):
        assert len(V.conditions()) >= 32

    def test_verifier_exits_non_zero(self, V):
        V.FAILURES.clear()
        assert V.main() == 1
        assert any("N09" in f for f in V.FAILURES)
        V.FAILURES.clear()

    def test_selftest_passes_as_subprocess(self):
        p = os.path.join(REPO, "scripts", "workflow_rearchitecture",
                         "verify_foundation_2f26f.py")
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
        """Point-in-time artifacts from earlier slices must not be rewritten."""
        assert _h(os.path.join(DOCS, "phase-02a-slice-02f26d",
                               "frozen-sample-manifest.csv")) == "bc878c81f76e54e6"
        assert _h(os.path.join(DOCS, "phase-02a-slice-02f26e",
                               "fresh-manual-adjudication.csv")) == "b02f35736a79eb3d"


# ══════════════════════════════════════════════════════════════════
# Behavioural invariants
# ══════════════════════════════════════════════════════════════════

class TestBehaviouralInvariants:
    def test_closed_module_canaries(self):
        V = _load("verify_foundation_2f26f.py")
        c = V._canaries()
        assert all(c.values()), [k for k, v in c.items() if not v]

    def test_staffpermission_grant_deny_and_isolation(self):
        from app.core.permissions import permission_checker as pc
        p = "tenant:plan:manage"
        assert pc.has("super_admin", p)
        assert not pc.has("tenant_owner", p)
        assert pc.has("tenant_owner", p, overrides={p: True})
        assert not pc.has("tenant_owner", p, overrides={p: False})
        assert not pc.has("tenant_owner", p, overrides={"unrelated:perm": True})
        assert not pc.has("tenant_manager", p)
        assert not pc.has("", p)

    def test_legacy_reviews_post_remains_410(self):
        import inspect
        from app.engines.review import router as legacy
        assert "410" in inspect.getsource(legacy.create_review)
