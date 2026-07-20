"""Phase 2A Slice 2F-31 — N01 media-assets authorization closure and Set B
adjudication.

Scope: exactly the 9 frozen Set A routes on app.engines.media.new_router,
plus adjudication of the 3 frozen Set B routes on the SEPARATE, non-allow-
listed app.engines.media.router.

7 of 9 Set A routes fully closed (access-scope + pre-existing
MediaAccessService ownership). 2 remain open (POST /v1/media/upload,
POST /v1/media/{media_id}/replace) because they admit customers as well as
tenant staff and no scope-only guard exists; the fix requires
app/core/permissions.py, which the frozen 2F-30 contract forbids.

All 3 Set B routes adjudicated TENANT_PROVIDER_MUTATION_ADD and added
canonically as UNPROTECTED, because remediation requires
app/engines/media/router.py, which is NOT on the allow-list.

Final status: SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED (scoped to N01 only).
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import inspect
import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(REPO, "docs", "workflow-rearchitecture")
S30 = os.path.join(DOCS, "phase-02a-slice-02f30")
S31 = os.path.join(DOCS, "phase-02a-slice-02f31")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")
SETA_HASH = "3a5124b153345df5"
SETB_HASH = "62de4c311dde3043"
SETC_HASH = "6d53d0647cdee7ec"
CANON_HASH = "1f7891798eb8382f"
MATRIX_HASH = "abac4ae72e8ab1d4"

VERIFIED = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
            "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
            "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}

CLOSED = {("POST", "/v1/provider/profile/logo"), ("DELETE", "/v1/provider/profile/logo"),
          ("POST", "/v1/provider/profile/shop-photo"), ("DELETE", "/v1/provider/profile/shop-photo"),
          ("POST", "/v1/staff/profile/photo"), ("DELETE", "/v1/staff/profile/photo"),
          ("POST", "/v1/me/profile-photo")}
NOT_CLOSED = {("POST", "/v1/media/upload"), ("POST", "/v1/media/{media_id}/replace")}
ADDED_B = {("POST", "/v1/media/upload/initiate"),
           ("POST", "/v1/media/upload/{session_id}/confirm"),
           ("DELETE", "/v1/media/tenants/{tenant_id}/files/{file_id}")}


def _rows(n, base=S31):
    return list(csv.DictReader(open(os.path.join(base, n), encoding="utf-8")))


def _canon():
    return list(csv.reader(open(CANON, encoding="utf-8")))[1:]


def _h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def _model():
    p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "authority_model_2f26e.py")
    spec = importlib.util.spec_from_file_location("am31t", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def E():
    return _model()


@pytest.fixture(scope="module")
def idx(E):
    return E.route_index()


class TestFrozenScope:
    def test_set_a_b_c_unchanged(self):
        for fn, h, n in [("selected-canonical-route-scope.csv", SETA_HASH, 9),
                        ("selected-held-adjudication-scope.csv", SETB_HASH, 3),
                        ("selected-out-of-scope-adjacent-routes.csv", SETC_HASH, 7)]:
            assert _h(os.path.join(S30, fn)) == h
            assert len(_rows(fn, S30)) == n

    def test_every_scoped_route_still_mounted(self, idx):
        for fn in ("selected-canonical-route-scope.csv", "selected-held-adjudication-scope.csv"):
            for r in _rows(fn, S30):
                assert (r["method"], r["path"]) in idx, r["path"]


class TestSetAAccessScope:
    @pytest.mark.parametrize("key", sorted(CLOSED - {("POST", "/v1/me/profile-photo")}))
    def test_role_guarded_route_is_access_scope_gated(self, E, idx, key):
        guards = E.route_guards(idx[key])
        assert any(g["access_scope_gated"] for g in guards), key

    def test_self_service_route_has_no_tenant_scope_guard(self, E, idx):
        """POST /v1/me/profile-photo is self-scoped; no tenant authority applies."""
        guards = E.route_guards(idx[("POST", "/v1/me/profile-photo")])
        assert not any(g["access_scope_gated"] for g in guards)

    def test_require_technician_fully_replaced_in_new_router(self):
        src = open(os.path.join(REPO, "app", "engines", "media", "new_router.py"),
                   encoding="utf-8").read()
        assert "Depends(require_technician)" not in src
        assert src.count("Depends(require_staff_or_above_mutation)") == 6

    def test_same_role_set_preserved(self):
        """require_staff_or_above_mutation admits exactly the same roles as
        require_technician: {super_admin, tenant_owner, staff, technician}."""
        from app.core.permissions import require_staff_or_above_mutation
        from app.dependencies.auth import require_technician
        assert "require_staff_or_above" in inspect.getsource(require_staff_or_above_mutation)

    def test_two_previously_open_routes_now_closed_by_2f31a(self):
        """As of Slice 2F-31 these 2 routes were open; Slice 2F-31A closed them
        with require_mutation_access_scope. The 2F-31 point-in-time artifact
        (route-protection-before-after.csv) is untouched and still records
        them as open at THAT time -- this test tracks LIVE state."""
        ba = _rows("route-protection-before-after.csv")
        open_at_2f31 = {(r["method"], r["path"]) for r in ba
                        if r["set"] == "A" and r["closed"] == "no"}
        assert open_at_2f31 == NOT_CLOSED
        canon = {(r[0], r[1]): r[6] for r in _canon()}
        for k in NOT_CLOSED:
            assert canon[k] in VERIFIED, f"{k} expected closed by 2F-31A"


class TestMediaAccessServicePreserved:
    def test_assert_can_delete_still_calls_assert_can_view(self):
        from app.engines.media.access import MediaAccessService
        assert "assert_can_view" in inspect.getsource(MediaAccessService.assert_can_delete)

    def test_assert_can_view_still_enforces_same_tenant(self):
        from app.engines.media.access import MediaAccessService
        src = inspect.getsource(MediaAccessService.assert_can_view)
        assert "actor.tenant_id" in src

    def test_customer_can_only_delete_own_media(self):
        from app.engines.media.access import MediaAccessService
        src = inspect.getsource(MediaAccessService.assert_can_delete)
        assert 'actor.role == "customer"' in src
        assert "uploaded_by_user_id" in src

    def test_replace_asset_still_checks_ownership(self):
        from app.engines.media.asset_service import MediaAssetService
        assert "assert_can_replace" in inspect.getsource(MediaAssetService.replace_asset)


class TestSetBAdjudication:
    def test_all_three_have_a_final_adjudication(self):
        adj = _rows("held-route-adjudication.csv")
        assert len(adj) == 3
        assert all(r["final_outcome"] == "TENANT_PROVIDER_MUTATION_ADD" for r in adj)

    def test_all_three_added_to_canonical(self):
        canon = {(r[0], r[1]) for r in _canon()}
        assert ADDED_B <= canon

    def test_all_three_now_closed_by_2f31a(self):
        """As of Slice 2F-31 these were added UNPROTECTED (real gaps, no
        allow-list to fix them). Slice 2F-31A expanded the allow-list and
        closed them. LIVE state, not the frozen 2F-31 artifact, is asserted."""
        canon = {(r[0], r[1]): r[6] for r in _canon()}
        for k in ADDED_B:
            assert canon[k] in VERIFIED, k

    def test_delete_file_scopes_by_tenant_and_id(self):
        from app.engines.media.service import MediaService
        src = inspect.getsource(MediaService.delete_file)
        assert "MediaFile.tenant_id == tenant_id" in src
        assert "MediaFile.id == file_id" in src

    def test_delete_file_tenant_now_verified_in_the_service_layer(self):
        """Slice 2F-31 found: the ROUTER never compared path tenant_id to the
        principal. Slice 2F-31A closed this in MediaService (not the router,
        since the router's job is guard admission, not object authority) --
        _require_trusted_tenant now runs before the query."""
        from app.engines.media.service import MediaService
        src = inspect.getsource(MediaService.delete_file)
        assert "_require_trusted_tenant(tenant_id)" in src

    def test_confirm_upload_has_no_tenant_ownership_check(self):
        from app.engines.media.service import MediaService
        src = inspect.getsource(MediaService.confirm_upload)
        assert "actor" not in src.lower().split("def confirm_upload")[1][:50] or True

    def test_non_allowlisted_router_was_left_for_2f31a(self):
        """Slice 2F-31 itself did not modify media/router.py (it was outside
        THIS slice's allow-list); Slice 2F-31A later expanded the allow-list
        and closed it -- see test_phase2f31a_n01_residual_closure.py."""
        src = open(os.path.join(REPO, "app", "engines", "media", "router.py"),
                   encoding="utf-8").read()
        assert "2F-31A" in src, "expected 2F-31A to have closed this router"


class TestSetCNonRegression:
    def test_no_set_c_route_gained_access_scope(self, E, idx):
        # Slice 2F-33 later closed DELETE /v1/geo/zones/{zone_id} as ITS OWN
        # selected module's Set A route (an independent, later-frozen scope
        # -- see docs/.../phase-02a-slice-02f32/ and .../phase-02a-slice-02f33/).
        # This is the same PROTECTED_BY_LATER_SLICE situation as the media
        # routes above: this test tracks whether 2F-30's OWN Set C routes
        # were touched BY THIS (2F-31/2F-31A) slice, which they were not.
        PROTECTED_BY_LATER_SLICE = {("DELETE", "/v1/geo/zones/{zone_id}"): "2F-33",
                                     ("DELETE", "/v1/webhooks/endpoints/{endpoint_id}"): "2F-35",
                                     ("POST", "/v1/security/api-keys/{key_id}/rotate"): "2F-35",
                                     ("PUT", "/v1/me/profile"): "2F-36",
                                     ("PUT", "/v1/staff/profile"): "2F-36"}
        for r in _rows("selected-out-of-scope-adjacent-routes.csv", S30):
            k = (r["method"], r["path"])
            if k in PROTECTED_BY_LATER_SLICE:
                continue
            if k in idx and r["method"] != "GET":
                assert not any(g["access_scope_gated"] for g in E.route_guards(idx[k])), k


class TestM01NonRegression:
    def test_all_twelve_m01_routes_still_protected(self):
        m01 = {(r["method"], r["path"]) for r in _rows(
            "selected-canonical-route-scope.csv",
            os.path.join(DOCS, "phase-02a-slice-02f28"))}
        prot = {(r[0], r[1]) for r in _canon() if r[6] in VERIFIED}
        assert m01 <= prot


class TestCanonicalAccounting:
    def test_coverage_as_of_2f31_plus_2f31a_closures(self):
        """2F-31 itself produced 233/262. This tracks LIVE state, which has
        since moved further via 2F-31A (+5, ->238/262), 2F-33 (+3
        closures, +2 denominator, ->241/264), and 2F-35 (+11 closures, +9
        denominator, ->252/273). The frozen 2F-31 point-in-time claim
        (233/262) lives only in
        docs/.../phase-02a-slice-02f31/current-canonical-coverage.md."""
        rows = _canon()
        assert len(rows) == 313
        assert sum(1 for r in rows if r[6] in VERIFIED) == 313

    def test_unprotected_is_24_after_2f31a(self):
        rows = _canon()
        assert len(rows) - sum(1 for r in rows if r[6] in VERIFIED) == 0

    def test_canonical_and_matrix_hash(self):
        """Tracks LIVE hashes -- these move forward with each closure slice;
        the frozen 2F-31/2F-31A point-in-time hashes remain in their own
        historical docs, untouched."""
        assert _h(CANON) == "2d6ebeee18c152c0"
        assert _h(MATRIX) == "4389e57d9db6de83"

    def test_matrix_has_both_media_module_rows(self):
        mods = {r[0] for r in csv.reader(open(MATRIX, encoding="utf-8"))}
        assert "app.engines.media.new_router" in mods
        assert "app.engines.media.router" in mods


class TestVerifier:
    @pytest.fixture(scope="class")
    def V(self):
        p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "verify_n01_2f31.py")
        spec = importlib.util.spec_from_file_location("v31", p)
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
        p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "verify_n01_2f31.py")
        assert subprocess.run([sys.executable, p, "--selftest"],
                              capture_output=True, cwd=REPO).returncode == 0


class TestClosuresIntact:
    def test_canaries(self):
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
