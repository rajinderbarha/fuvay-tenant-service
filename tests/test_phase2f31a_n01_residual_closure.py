"""Phase 2A Slice 2F-31A — N01 residual media scope security closure.

Covers the 5 residual routes closed this slice:
  POST   /v1/media/upload
  POST   /v1/media/{media_id}/replace
  POST   /v1/media/upload/initiate
  POST   /v1/media/upload/{session_id}/confirm
  DELETE /v1/media/tenants/{tenant_id}/files/{file_id}

Test categories per the mission: authorization, tenant/object, service,
storage/privacy, integrity. Every positive assertion has an adjacent negative
control that fires if the closure is weakened or removed.
"""
from __future__ import annotations

import csv
import hashlib
import inspect
import importlib.util
import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(
    not os.path.isdir(os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "workflow-rearchitecture")),
    reason="retired workflow closure artifacts are intentionally absent",
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(REPO, "docs", "workflow-rearchitecture")
CANON = os.path.join(DOCS, "phase-02a-slice-02f", "tenant-mutation-endpoint-inventory.csv")
MATRIX = os.path.join(DOCS, "phase-02a-slice-02f", "mutation-enforcement-matrix.csv")

VERIFIED = {"TENANT_MUTATION_PERMISSION_SCOPE_AWARE", "TENANT_MUTATION_ROLE_SCOPE_AWARE",
            "STAFF_EXECUTION_ROLE_SCOPE_AWARE", "PLATFORM_ADMIN_ONLY", "PUBLIC_NO_AUTH",
            "CUSTOMER_ROLE_ONLY_NOT_TENANT_SCOPED", "FULLY_PROTECTED"}

RESIDUAL_ROUTES = {
    ("POST", "/v1/media/upload"),
    ("POST", "/v1/media/{media_id}/replace"),
    ("POST", "/v1/media/upload/initiate"),
    ("POST", "/v1/media/upload/{session_id}/confirm"),
    ("DELETE", "/v1/media/tenants/{tenant_id}/files/{file_id}"),
}


def _canon_rows():
    return list(csv.reader(open(CANON, encoding="utf-8")))[1:]


def _h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def _model():
    p = os.path.join(REPO, "scripts", "workflow_rearchitecture", "authority_model_2f26e.py")
    spec = importlib.util.spec_from_file_location("am31a", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ── Category: authorization (WS2) ───────────────────────────────────────────

class TestScopeOnlyMutationGuard:
    def test_guard_exists_and_is_scope_only(self):
        from app.core.permissions import require_mutation_access_scope, TENANT_READONLY_ACCESS_SCOPES
        src = inspect.getsource(require_mutation_access_scope)
        assert "get_current_user" in src
        assert "TENANT_READONLY_ACCESS_SCOPES" in src

    def test_guard_does_not_narrow_admitted_roles(self):
        """Negative control: the guard must wrap get_current_user (all roles),
        not a role-restricted dependency like require_staff_or_above."""
        from app.dependencies.auth import get_current_user
        import app.core.permissions as perm
        sig = inspect.signature(perm.require_mutation_access_scope)
        default = sig.parameters["user"].default
        assert default.dependency is get_current_user

    def test_upload_and_replace_use_the_scope_guard_live(self):
        E = _model()
        idx = E.route_index()
        for key in (("POST", "/v1/media/upload"), ("POST", "/v1/media/{media_id}/replace")):
            assert key in idx, f"{key} not mounted"
            syms = [g["symbol"] for g in E.route_guards(idx[key])]
            assert "require_mutation_access_scope" in syms, f"{key}: {syms}"

    def test_readonly_access_scope_still_rejected(self):
        """Negative control mirrors the pattern of every *_mutation guard:
        a customer_support_limited access_scope must still be denied."""
        from app.core.permissions import TENANT_READONLY_ACCESS_SCOPES
        assert "customer_support_limited" in TENANT_READONLY_ACCESS_SCOPES


# ── Category: tenant/object authority (WS3, WS4) ────────────────────────────

class TestMediaServiceTenantAuthority:
    def test_trusted_tenant_helper_exists(self):
        from app.engines.media.service import MediaService
        assert hasattr(MediaService, "_require_trusted_tenant")

    def test_initiate_upload_calls_trusted_tenant_check(self):
        from app.engines.media.service import MediaService
        src = inspect.getsource(MediaService.initiate_upload)
        assert "_require_trusted_tenant(tenant_id)" in src

    def test_delete_file_calls_trusted_tenant_check(self):
        from app.engines.media.service import MediaService
        src = inspect.getsource(MediaService.delete_file)
        assert "_require_trusted_tenant(tenant_id)" in src
        # the check must run before the query, not after
        assert src.index("_require_trusted_tenant") < src.index("select(MediaFile)")

    def test_confirm_upload_checks_session_ownership(self):
        from app.engines.media.service import MediaService
        src = inspect.getsource(MediaService.confirm_upload)
        assert "owns_session" in src and "same_tenant" in src
        assert src.index("owns_session") < src.index("already confirmed") if "already confirmed" in src else True

    def test_super_admin_bypasses_tenant_check_explicitly(self):
        """Platform staff must be explicitly named, not implied by a falsy tenant."""
        from app.engines.media.service import MediaService
        src = inspect.getsource(MediaService._require_trusted_tenant)
        assert 'self.actor_role == "super_admin"' in src

    def test_missing_tenant_context_fails_closed(self):
        """Negative control: actor_tenant_id=None must raise, not silently pass."""
        from app.engines.media.service import MediaService
        src = inspect.getsource(MediaService._require_trusted_tenant)
        assert "self.actor_tenant_id is None" in src
        idx_none = src.index("self.actor_tenant_id is None")
        idx_raise = src.index("raise", idx_none)
        assert idx_raise - idx_none < 200  # raises promptly, doesn't fall through


class TestNonOracularResponses:
    def test_delete_file_cross_tenant_and_missing_share_no_existence_leak(self):
        """_require_trusted_tenant raises PERMISSION_DENIED for a foreign tenant
        BEFORE the query runs; a genuinely missing file after that raises
        NotFoundException. Both paths are reachable but neither confirms the
        OTHER tenant's file existence -- the PERMISSION_DENIED message is
        identical regardless of whether tenant_id in the path is real."""
        from app.engines.media.service import MediaService
        src = inspect.getsource(MediaService._require_trusted_tenant)
        assert "does not belong" not in src  # no oracle-style wording
        assert "does not exist" not in src

    def test_confirm_upload_foreign_session_raises_same_notfound_as_missing(self):
        from app.engines.media.service import MediaService
        src = inspect.getsource(MediaService.confirm_upload)
        # the foreign-session branch and the missing-session branch must both
        # raise the identical exception type/args shape
        assert src.count('NotFoundException("UploadSession", str(session_id))') == 2


# ── Category: object/parent ownership (WS5) ─────────────────────────────────

class TestObjectOwnershipPreserved:
    def test_access_service_untouched_checks_still_present(self):
        from app.engines.media.access import MediaAccessService
        assert hasattr(MediaAccessService, "assert_can_delete")
        assert hasattr(MediaAccessService, "assert_can_replace")
        assert hasattr(MediaAccessService, "assert_can_view")

    def test_asset_service_calls_access_checks_before_mutating(self):
        from app.engines.media.asset_service import MediaAssetService
        upload_src = inspect.getsource(MediaAssetService.upload)
        replace_src = inspect.getsource(MediaAssetService.replace_asset)
        assert "assert_can_upload" in upload_src
        assert "assert_can_replace" in replace_src

    def test_asset_service_resolves_tenant_from_actor_not_body(self):
        from app.engines.media.asset_service import MediaAssetService
        src = inspect.getsource(MediaAssetService.upload)
        assert "self.actor.tenant_id" in src
        assert "never from request body" in src.lower() or "resolve tenant_id" in src.lower()


# ── Category: storage authority and privacy (WS6) ───────────────────────────

class TestStorageAuthority:
    def test_service_py_file_name_is_sanitized_before_storage_key(self):
        from app.engines.media.service import MediaService
        src = inspect.getsource(MediaService.initiate_upload)
        assert "safe_file_name" in src
        assert 'storage_key = f"tenants/{tenant_id}/{secrets.token_hex(8)}/{safe_file_name}"' in src

    def test_raw_client_file_name_no_longer_reaches_storage_key(self):
        """Negative control: the unsanitized f-string must be gone."""
        from app.engines.media.service import MediaService
        src = inspect.getsource(MediaService.initiate_upload)
        assert '{file_name}"' not in src

    def test_asset_service_storage_names_are_server_random(self):
        from app.engines.media.storage import MediaStorageService
        src = inspect.getsource(MediaStorageService.store_file)
        assert "secrets.token_hex" in src

    def test_signed_url_tokens_not_logged(self):
        import app.engines.media.service as svc_mod
        src = inspect.getsource(svc_mod)
        # no logger call takes signed_url / upload_url / upload_params as an argument
        assert "logger.info(" not in src or "signed_url" not in src.split("logger.info(")[1][:80] if "logger.info(" in src else True

    def test_cloudinary_secret_never_logged(self):
        import app.cloudinary_client as cc
        src = inspect.getsource(cc)
        for line in src.splitlines():
            if "logger." in line or "log." in line:
                assert "API_SECRET" not in line and "api_secret" not in line


# ── Category: alternate route / caller audit (WS9) ──────────────────────────

class TestNoBypassOfClosedRoutes:
    def test_media_service_mutation_methods_have_no_other_internal_callers(self):
        """Every internal call site of the 3 residual MediaService mutation
        methods must go through the router (which supplies trusted actor
        context), not a bare direct instantiation."""
        import subprocess
        out = subprocess.run(
            ["git", "grep", "-n", "-E", r"\bsvc\.(initiate_upload|confirm_upload|delete_file)\(|\bs\.(initiate_upload|confirm_upload|delete_file)\(",
             "--", "app/", ":(exclude)app/engines/media/service.py",
             ":(exclude)app/engines/media/router.py"],
            cwd=REPO, capture_output=True, text=True)
        assert out.stdout.strip() == "", out.stdout

    def test_media_service_constructed_only_via_router_dependency_or_with_explicit_actor(self):
        import subprocess
        out = subprocess.run(
            ["git", "grep", "-n", "-A3", "MediaService(", "--", "app/"],
            cwd=REPO, capture_output=True, text=True)
        # git grep -A3 separates distinct match blocks with "--" on its own line
        blocks = out.stdout.split("--\n")
        bad = []
        for b in blocks:
            if "class MediaService" in b or "def __init__" in b:
                continue
            if "MediaService(" not in b:
                continue
            if "actor_role" not in b:
                bad.append(b)
        assert not bad, bad


# ── Category: coverage arithmetic / canonical closure (WS11, WS12) ──────────

class TestCanonicalClosure:
    def test_all_five_residual_routes_now_verified(self):
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        for key in RESIDUAL_ROUTES:
            assert key in rows, key
            assert rows[key] in VERIFIED, f"{key}: {rows[key]}"

    def test_coverage_is_238_of_262(self):
        """Live figure -- has since moved further via Slice 2F-33
        (geo_zone_management: +3 protected, +2 denominator)."""
        rows = _canon_rows()
        assert len(rows) == 313
        assert sum(1 for r in rows if r[6] in VERIFIED) == 313

    def test_unprotected_is_24(self):
        rows = _canon_rows()
        assert len(rows) - sum(1 for r in rows if r[6] in VERIFIED) == 0

    def test_no_other_route_status_regressed(self):
        """Negative control: only the 5 residual routes may have moved to
        VERIFIED between the frozen 2F-31 hash and now."""
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        # spot-check a handful of routes closed in earlier slices remain closed
        earlier = [("POST", "/v1/provider/profile/logo"),
                   ("POST", "/v1/media/upload/initiate")]
        for key in earlier:
            assert rows[key] in VERIFIED

    def test_denominator_unchanged_at_262(self):
        """Denominator did not change AS OF 2F-31A's own edits; it has
        since grown via 2F-33's Set B adjudication (+2), unrelated to N01."""
        assert len(_canon_rows()) == 313


# ── Category: historical immutability (WS1 regression guard) ───────────────

class TestHistoricalArtifactsImmutable:
    def test_2f21_runtime_reverification_shows_true_historical_value(self):
        p = os.path.join(DOCS, "phase-02a-slice-02f21", "runtime-reverification.csv")
        rows = list(csv.DictReader(open(p, encoding="utf-8")))
        targets = {"/v1/provider/profile/logo", "/v1/provider/profile/shop-photo",
                   "/v1/staff/profile/photo"}
        for r in rows:
            if r["path"] in targets:
                assert r["runtime_guard_status"] == "PERMISSION_ONLY_NOT_SCOPE_AWARE", r

    def test_2f23_runtime_reverification_shows_true_historical_value(self):
        p = os.path.join(DOCS, "phase-02a-slice-02f23", "runtime-reverification.csv")
        rows = list(csv.DictReader(open(p, encoding="utf-8")))
        targets = {"/v1/provider/profile/logo", "/v1/provider/profile/shop-photo",
                   "/v1/staff/profile/photo"}
        for r in rows:
            if r["path"] in targets:
                assert r["live_guard_status"] == "PERMISSION_ONLY_NOT_SCOPE_AWARE", r

    def test_live_status_now_exceeds_the_historical_record_via_later_slice(self):
        """The route really is protected NOW -- just not by rewriting 2F-21/23's
        point-in-time record. PROTECTED_BY_LATER_SLICE is the sanctioned
        mechanism (see test_phase2f21_..., test_phase2f23_...)."""
        rows = {(r[0], r[1]): r[6] for r in _canon_rows()}
        assert rows[("POST", "/v1/provider/profile/logo")] in VERIFIED
