"""Phase 2A Slice 2F-27 — dual-review reconciliation.

Two methodologically-distinct adjudication streams (persistence-first and
authority-first) were run over all 123 mixed-persona routes and disagreed on
41. Every disagreement was resolved with source evidence. The review produced
59 tenant-mutation add-candidates versus the 2 carefully hand-verified ones
from prior slices — evidence that single-agent automated dual-review is not
authoritative for canonical edits. Zero canonical edits were applied; both
canonical files are asserted byte-identical.
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
S = os.path.join(DOCS, "phase-02a-slice-02f27")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")
FROZEN_HASH = "2d6ebeee18c152c0"
MATRIX_HASH = "4389e57d9db6de83"
POP_HASH = "ecdf8a830b07b95e"


def _rows(n, base=S):
    return list(csv.DictReader(open(os.path.join(base, n), encoding="utf-8")))


def _h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


class TestPopulationAndStreams:
    def test_population_is_123_and_frozen(self):
        assert len(_rows("frozen-mixed-persona-population.csv")) == 123
        assert _h(os.path.join(S, "frozen-mixed-persona-population.csv")) == POP_HASH

    def test_both_reviewers_cover_all_123(self):
        assert len(_rows("reviewer-a-adjudication.csv")) == 123
        assert len(_rows("reviewer-b-adjudication.csv")) == 123

    def test_reviewer_files_are_not_identical(self):
        a = open(os.path.join(S, "reviewer-a-adjudication.csv")).read()
        b = open(os.path.join(S, "reviewer-b-adjudication.csv")).read()
        assert a != b

    def test_streams_genuinely_disagree(self):
        A = {(r["method"], r["path"]): r for r in _rows("reviewer-a-adjudication.csv")}
        B = {(r["method"], r["path"]): r for r in _rows("reviewer-b-adjudication.csv")}
        dis = [k for k in A if A[k]["persona"] != B[k]["persona"]
               or A[k]["tenant_direction"] != B[k]["tenant_direction"]]
        assert len(dis) == 41


class TestResolutionAndPartition:
    def test_every_disagreement_resolved(self):
        A = {(r["method"], r["path"]): r for r in _rows("reviewer-a-adjudication.csv")}
        B = {(r["method"], r["path"]): r for r in _rows("reviewer-b-adjudication.csv")}
        disp = {k for k in A if A[k]["persona"] != B[k]["persona"]
                or A[k]["tenant_direction"] != B[k]["tenant_direction"]}
        resolved = {(r["method"], r["path"]) for r in _rows("disagreement-resolution.csv")}
        assert disp <= resolved

    def test_final_partition_totals_123(self):
        final = _rows("final-persona-partition.csv")
        assert len(final) == 123
        assert len({(r["method"], r["path"]) for r in final}) == 123

    def test_no_route_left_unresolved(self):
        final = _rows("final-persona-partition.csv")
        bad = [r for r in final if r["final_persona"] in
               ("MIXED_PERSONA", "UNKNOWN", "UNVERIFIED", "HELD")]
        assert not bad

    def test_partition_totals(self):
        from collections import Counter
        c = Counter(r["final_persona"] for r in _rows("final-persona-partition.csv"))
        assert c["TENANT_PROVIDER_MUTATION"] == 87
        assert c["PRODUCT_DECISION_REQUIRED"] == 21
        assert c["SELF_SERVICE_MUTATION"] == 10
        assert c["READ_ONLY_NOT_MUTATION"] == 5
        assert sum(c.values()) == 123


class TestCanonicalUnchanged:
    def test_canonical_and_matrix_frozen(self):
        assert _h(CANON) == FROZEN_HASH
        assert _h(MATRIX) == MATRIX_HASH

    def test_coverage_recount_unchanged(self):
        rows = list(csv.reader(open(CANON, encoding="utf-8")))[1:]
        V = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
             "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
             "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}
        assert len(rows) == 313
        assert sum(1 for r in rows if r[6] in V) == 313

    def test_add_candidate_count_far_exceeds_two(self):
        """The 59-vs-2 gap is the evidence that automated dual-review cannot
        authoritatively drive canonical edits."""
        m = _rows("canonical-runtime-row-matching.csv")
        miss = [r for r in m if r["row_result"] == "MISSING_ROW_ADD_CANDIDATE"]
        assert len(miss) == 59


class TestVerifier:
    @pytest.fixture(scope="class")
    def V(self):
        p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "verify_dualreview_2f27.py")
        spec = importlib.util.spec_from_file_location("v27", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_verifier_passes(self, V):
        V.FAILURES.clear()
        assert V.main() == 0
        V.FAILURES.clear()

    def test_every_condition_can_fail(self, V):
        for name, _s, _d in V.conditions():
            key = name.split()[0].lower()
            assert any(x[0] == name and not x[1] for x in V.conditions({key: False})), name

    def test_selftest_subprocess(self):
        p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "verify_dualreview_2f27.py")
        assert subprocess.run([sys.executable, p, "--selftest"],
                              capture_output=True, cwd=REPO).returncode == 0


class TestClosuresIntact:
    def test_canaries(self):
        import inspect
        from app.engines.field_ops import service as fo
        assert "trusted_internal=True" in inspect.getsource(fo)
        from app.engines.review import router as lg
        assert "410" in inspect.getsource(lg.create_review)

    def test_staffpermission(self):
        from app.core.permissions import permission_checker as pc
        assert pc.has("super_admin", "tenant:plan:manage")
        assert not pc.has("tenant_owner", "tenant:plan:manage")
        assert pc.has("tenant_owner", "tenant:plan:manage", overrides={"tenant:plan:manage": True})
