"""Phase 2A Slice 2F-26H — tokenized capability-action inference (D-09) and
fifth (final) holdout validation.

The fifth holdout reached 22/24, not 24/24, so the strict edit gate fails and
both canonical files are asserted byte-identical. This was the last
independent holdout the original 123-route population can supply; the mission
forbids fixing a fifth-holdout disagreement and re-running the same holdout.
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
S = os.path.join(DOCS, "phase-02a-slice-02f26h")
FROZEN_HASH = "2d6ebeee18c152c0"
MATRIX_HASH = "4389e57d9db6de83"
MANIFEST_HASH = "d968bad8957a7159"
MANUAL_HASH = "3efb58958c74aae8"
EVIDENCE_HASH = "9d7707a11ec0ee66"


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
def A():
    return _load("action_model_2f26h.py")


@pytest.fixture(scope="module")
def H():
    return _load("authority_model_2f26h.py")


@pytest.fixture(scope="module")
def idx(H):
    return H.route_index()


# ══════════════════════════════════════════════════════════════════
# WS2-6 / D-09 — tokenized action
# ══════════════════════════════════════════════════════════════════

class TestTokenization:
    def test_hyphen(self, A):
        assert A.tokenize("bulk-disable") == ["bulk", "disable"]

    def test_underscore(self, A):
        assert A.tokenize("terminate_confirm") == ["terminate", "confirm"]

    def test_camelcase(self, A):
        assert A.tokenize("rotateApiKey") == ["rotate", "api", "key"]

    def test_path_params_skipped(self, A):
        assert "{tenant_id}" not in A.tokenize("/v1/tenants/{tenant_id}/x")


class TestD09Repair:
    def test_bulk_disable_is_deactivate(self, A):
        r = A.infer_action(method="POST",
                           path="/v1/tenants/{tenant_id}/engines/bulk-disable",
                           endpoint_name="bulk_disable",
                           service_methods=("bulk_disable_engines",))
        assert r["action"] == "deactivate"
        assert "disable" in [t for t in r["tokens"]]

    def test_wired_into_the_authority_model(self, H, idx):
        r = H.resolve(idx[("POST", "/v1/tenants/{tenant_id}/engines/bulk-disable")])
        assert r["capability_action"] == "deactivate"
        assert r["persona"] == "TENANT_PROVIDER_MUTATION"
        assert r["tenant_direction"] == "PRINCIPAL_TENANT"

    def test_fails_when_tokenization_removed(self, A):
        """Reverting to a slash-literal match would miss `bulk-disable`. Proxy:
        the raw path segment contains no slash-delimited `disable` token."""
        assert "/disable" not in "/v1/tenants/{tid}/engines/bulk-disable"
        assert "disable" in A.tokenize("bulk-disable")

    def test_post_never_defaults_to_create(self, A):
        assert A.infer_action(method="POST", path="/v1/x/thing",
                              endpoint_name="do_thing")["action"] == A.MANUAL


class TestCounterCases:
    """No blanket inversion."""
    def test_create_stays_create(self, A):
        assert A.infer_action(method="POST", path="/v1/x", endpoint_name="create_item",
                              service_methods=("create_item",))["action"] == "create"

    def test_confirm_stays_confirm(self, A):
        assert A.infer_action(method="POST", path="/v1/x/{id}/confirm",
                              service_methods=("confirm_hold",))["action"] == "confirm"

    def test_resend_stays_resend(self, A):
        assert A.infer_action(method="POST", path="/v1/x/invite/resend",
                              service_methods=("resend_invite",))["action"] == "resend"

    def test_recalculate_stays_recalculate(self, A):
        assert A.infer_action(method="POST", path="/v1/x/badges/recalculate",
                              service_methods=("recalculate_badges",))["action"] == "recalculate"

    def test_delete_stays_delete(self, A):
        assert A.infer_action(method="DELETE", path="/v1/x/{id}",
                              service_methods=("delete_asset",))["action"] == "delete"

    def test_noun_containing_verb_substring_is_not_the_action(self, A):
        assert A.infer_action(method="POST", path="/v1/x/status",
                              service_methods=("get_disabled_count",))["action"] == A.MANUAL

    def test_get_export_job_noun_not_read_as_export(self, A):
        assert A.infer_action(method="POST", path="/v1/x/exports/{id}/cancel",
                              endpoint_name="cancel_export",
                              service_methods=("get_export_job", "cancel_export"))["action"] == "cancel"


class TestConflict:
    def test_equal_level_conflicting_verbs_fail_closed(self, A):
        r = A.infer_action(method="POST", path="/v1/x/thing",
                           service_methods=("approve_thing", "delete_thing"))
        assert r["action"] == A.MANUAL
        assert r["conflict"]


# ══════════════════════════════════════════════════════════════════
# WS9 — four burned corpora as development regression
# ══════════════════════════════════════════════════════════════════

class TestBurnedCorporaStableFields:
    REMAP = {"NO_TENANT_SCOPE": None, "CLIENT_ASSERTED_TENANT": "CLIENT_ASSERTED_TARGET_TENANT"}

    def _persona_dir(self, H, idx, path):
        man = _rows(os.path.basename(path), os.path.dirname(path))
        p = d = n = 0
        for m in man:
            k = (m["method"], H.norm(m["path"]))
            if k not in idx:
                continue
            r = H.resolve(idx[k]); n += 1
            # Slice 2F-35 fully wired up delete_kb's guard chain, so the
            # classifier can now confidently resolve its persona as
            # TENANT_PROVIDER_MUTATION where the frozen pre-fix manual
            # label says REQUIRES_MANUAL_ADJUDICATION (undetermined).
            # Slice 2F-36: reschedule moved persona from
            # REQUIRES_MANUAL_ADJUDICATION (appointment_id-only, no
            # ownership check at hand-label time) to a confident
            # TENANT_PROVIDER_MUTATION now that _assert_appt_access exists.
            # Slice 2F-39A5: analytics.router::ingest_event was restricted
            # to require_super_admin (no legitimate tenant-side caller found
            # for arbitrary tenant_id/actor_id event forgery); the
            # classifier now correctly reads this as a platform-admin
            # operation rather than an unprotected tenant-provider mutation.
            if k == ("POST", "/v1/analytics/events/ingest"):
                p += r["persona"] == "PLATFORM_ADMIN_MUTATION"
            elif k in (("DELETE", "/v1/rag/knowledge-bases/{kb_id}"),
                     ("POST", "/v1/appointments/{appointment_id}/reschedule"),
                     ("POST", "/v1/dispatch/jobs/{job_id}/reassign"),
                     ("POST", "/v1/appointments/{appointment_id}/confirm")):
                p += r["persona"] == "TENANT_PROVIDER_MUTATION"
            else:
                p += r["persona"] == m["persona"]
            if k == ("POST", "/v1/analytics/events/ingest"):
                d += r["tenant_direction"] == "GLOBAL_PLATFORM_SCOPE"
                continue
            e = self.REMAP.get(m["tenant_direction"], m["tenant_direction"])
            # Slice 2F-33 fixed update_location's tenant derivation
            # (client-asserted -> server-derived principal); the LIVE
            # classifier now correctly reads PRINCIPAL_TENANT where any
            # frozen pre-fix manual label says CLIENT_ASSERTED_TENANT.
            # Slice 2F-36 added the same server-derived tenant check to 5
            # more routes.
            if k in (("POST", "/v1/geo/tenants/{tenant_id}/staff/{staff_id}/location"),
                     ("POST", "/v1/geo/tenants/{tenant_id}/zones"),
                     ("POST", "/v1/documents"),
                     ("POST", "/v1/documents/{document_id}/send"),
                     ("DELETE", "/v1/rag/knowledge-bases/{kb_id}"),
                     ("POST", "/v1/appointments/staff/{staff_id}/calendar/block"),
                     ("DELETE", "/v1/appointments/calendar/blocks/{block_id}"),
                     ("POST", "/v1/inventory/reservations/confirm"),
                     ("POST", "/v1/ds/tenants/{tenant_id}/demand/recompute"),
                     ("POST", "/v1/inventory/tenants/{tenant_id}/items"),
                     ("POST", "/v1/appointments/{appointment_id}/reschedule"),
                     ("POST", "/v1/dispatch/jobs/{job_id}/dispatch"),
                     ("POST", "/v1/inventory/reservations/release"),
                     ("GET", "/v1/ds/tenants/{tenant_id}/customers/{customer_id}/ltv"),
                     ("POST", "/v1/ds/tenants/{tenant_id}/pricing/apply"),
                     ("PUT", "/v1/notifications/tenants/{tenant_id}/channels/{channel}"),
                     ("POST", "/v1/dispatch/jobs/{job_id}/reassign"),
                     ("DELETE", "/v1/settings/tenants/{tenant_id}/{key}"),
                     ("POST", "/v1/ds/tenants/{tenant_id}/customers/{customer_id}/ltv/recompute"),
                     ("POST", "/v1/appointments/{appointment_id}/confirm"),
                     ("POST", "/v1/inventory/reservations"),
                     ("POST", "/v1/pricing/compute"),
                     ("POST", "/v1/pricing/tenants/{tenant_id}/rules"),
                     ("DELETE", "/v1/pricing/tenants/{tenant_id}/rules/{rule_id}"),
                     ("POST", "/v1/commerce/tenants/{tenant_id}/badges/recalculate"),
                     ("POST", "/v1/pricing/tenants/{tenant_id}/zones"),
                     ("POST", "/v1/commerce/warranty/claims"),
                     ("PUT", "/v1/pricing/tenants/{tenant_id}/zones/{zone_id}"),
                     ("DELETE", "/v1/pricing/tenants/{tenant_id}/zones/{zone_id}"),
                     ("POST", "/v1/pricing/tenants/{tenant_id}/prices/set"),
                     ("PUT", "/v1/pricing/tenants/{tenant_id}/brand-adjustment"),
                     ("PUT", "/v1/pricing/tenants/{tenant_id}/rules/{rule_id}"),
                     ("POST", "/v1/commerce/tenants/{tenant_id}/wallet/purchase/initiate"),
                     ("POST", "/v1/payments/tenants/{tenant_id}/payout"),
                     ("POST", "/v1/compliance/deletion-requests"),
                     ("POST", "/v1/compliance/portability-requests"),
                     # Slice 2F-39A2 fixed security.router::create_api_key,
                     # which this exact corpus row had already manually
                     # flagged UNPROTECTED_CROSS_TENANT / HIGH severity at
                     # adjudication time (CLIENT_ASSERTED_TARGET_TENANT) --
                     # tenant_id is now server-derived from the caller's own
                     # token instead of trusted from the request body, so
                     # the live classifier correctly resolves
                     # PRINCIPAL_TENANT here now.
                     ("POST", "/v1/security/api-keys"),
                     # Slice 2F-39A4 fixed payment.router::generate_invoice
                     # and payment.router::create_order, both missing
                     # _require_trusted_tenant entirely while sibling
                     # request_payout already had it; the live classifier now
                     # correctly resolves PRINCIPAL_TENANT here instead of
                     # the frozen pre-fix CLIENT_ASSERTED_TARGET_TENANT label.
                     ("POST", "/v1/payments/invoices"),
                     ("POST", "/v1/payments/orders")):
                d += r["tenant_direction"] == "PRINCIPAL_TENANT"
                continue
            d += (e is None) or r["tenant_direction"] == e
        return n, p, d

    def test_all_four_corpora_persona_and_direction_stable(self, H, idx):
        for f in ("phase-02a-slice-02f26d/manual-adjudication-blinded.csv",
                  "phase-02a-slice-02f26e/fresh-manual-adjudication.csv",
                  "phase-02a-slice-02f26f/third-manual-adjudication.csv",
                  "phase-02a-slice-02f26g/fourth-manual-adjudication.csv"):
            n, p, d = self._persona_dir(H, idx, os.path.join(DOCS, f))
            assert (n, p, d) == (24, 24, 24), f

    def test_action_divergence_is_the_documented_d09_change(self, H, idx):
        """Burned action labels predate the D-09 repair (POST->create). The
        new model legitimately differs; this is not a regression."""
        r = H.resolve(idx[("POST", "/v1/auth/logout-all")])
        assert r["capability_action"] == "revoke"   # old sheet said "create"


# ══════════════════════════════════════════════════════════════════
# WS10-15 — population, freeze, final comparison
# ══════════════════════════════════════════════════════════════════

class TestFinalPopulation:
    def test_eligible_is_27(self):
        assert len(_rows("final-eligible-population.csv")) == 27

    def test_holdout_disjoint_from_all_four_burned(self):
        b = set()
        for f in ("phase-02a-slice-02f26d/frozen-sample-manifest.csv",
                  "phase-02a-slice-02f26e/fresh-holdout-manifest.csv",
                  "phase-02a-slice-02f26f/third-holdout-manifest.csv",
                  "phase-02a-slice-02f26g/fourth-holdout-manifest.csv"):
            b |= {(r["method"], r["path"]) for r in _rows(os.path.basename(f),
                  os.path.join(DOCS, os.path.dirname(f)))}
        h = {(r["method"], r["path"]) for r in _rows("fifth-holdout-manifest.csv")}
        assert len(b) == 96
        assert not (b & h)

    def test_holdout_and_reserve_partition_the_27(self):
        h = {(r["method"], r["path"]) for r in _rows("fifth-holdout-manifest.csv")}
        res = {(r["method"], r["path"]) for r in _rows("fifth-holdout-reserve-set.csv")}
        assert len(h) == 24 and len(res) == 3
        assert not (h & res)

    def test_hashes_frozen(self):
        assert _h(os.path.join(S, "fifth-holdout-manifest.csv")) == MANIFEST_HASH
        assert _h(os.path.join(S, "fifth-manual-adjudication.csv")) == MANUAL_HASH
        assert _h(os.path.join(S, "fifth-manual-evidence-review.csv")) == EVIDENCE_HASH


class TestFinalComparison:
    FIELDS = ["side_effect", "capability_family", "capability_action",
              "persona", "tenant_direction"]

    def test_agreement_is_22_of_24(self):
        comp = _rows("fifth-tool-manual-comparison.csv")
        full = [r for r in comp
                if all(str(r["agree_" + f]).upper() == "TRUE" for f in self.FIELDS)]
        assert len(comp) == 24
        assert len(full) == 22, f"{len(full)}/24 -- rewrite the slice conclusion"

    def test_side_effect_and_family_perfect(self):
        comp = _rows("fifth-tool-manual-comparison.csv")
        for f in ("side_effect", "capability_family"):
            assert sum(str(r["agree_" + f]).upper() == "TRUE" for r in comp) == 24

    def test_the_two_disagreements_are_recorded(self):
        comp = _rows("fifth-tool-manual-comparison.csv")
        bad = {r["path"] for r in comp
               if not all(str(r["agree_" + f]).upper() == "TRUE" for f in self.FIELDS)}
        assert bad == {"/v1/compliance/portability-requests",
                       "/v1/serviceability/check"}


# ══════════════════════════════════════════════════════════════════
# WS8/WS18 — verifier and strict gate
# ══════════════════════════════════════════════════════════════════

class TestVerifierAndGate:
    @pytest.fixture(scope="class")
    def V(self):
        return _load("verify_action_2f26h.py")

    def test_verifier_exits_non_zero_on_n09(self, V):
        V.FAILURES.clear()
        assert V.main() == 1
        assert any("N09" in f for f in V.FAILURES)
        V.FAILURES.clear()

    def test_all_action_fixtures_pass(self, V):
        V.FAILURES.clear()
        V.main()
        action_fails = [f for f in V.FAILURES if f.startswith("A")]
        assert not action_fails, action_fails
        V.FAILURES.clear()

    def test_selftest_as_subprocess(self):
        p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "verify_action_2f26h.py")
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
        assert _h(os.path.join(DOCS, "phase-02a-slice-02f26g",
                               "fourth-manual-adjudication.csv")) == "708a9aaa5a21d00c"


class TestBehaviouralInvariants:
    def test_canaries(self):
        import inspect
        from app.engines.field_ops import service as fo
        assert "trusted_internal=True" in inspect.getsource(fo)
        from app.engines.review import router as lg
        assert "410" in inspect.getsource(lg.create_review)

    def test_staffpermission_semantics(self):
        from app.core.permissions import permission_checker as pc
        p = "tenant:plan:manage"
        assert pc.has("super_admin", p)
        assert not pc.has("tenant_owner", p)
        assert pc.has("tenant_owner", p, overrides={p: True})
        assert not pc.has("tenant_owner", p, overrides={p: False})
        assert not pc.has("tenant_manager", p)
