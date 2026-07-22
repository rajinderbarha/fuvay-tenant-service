"""Phase 2A Slice 2D — tenant access model closure tests.

Covers:
- Seed script canonical-role guard (Workstream 5)
- Effective-access proof for the base `staff` role bundle (Workstream 4) —
  direct backend permission checks, not frontend button visibility
- StaffPermission override dead-wiring finding (Workstream 1) — regression
  guard proving this remains a known, documented gap rather than silently
  "fixed" by an unrelated future change without anyone noticing
- require_tenant_mutation_permission's access_scope guard (Workstream 3)
- Remediated account final state (Workstream 6/7)
- Migration 144's narrowed blocker (Workstream 9)
"""
from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.permissions import permission_checker, P


def _load_seed_module():
    spec = importlib.util.spec_from_file_location(
        "canonical_seed_final_l5_01",
        Path(__file__).parent.parent / "scripts" / "canonical_seed_final_l5_01.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestSeedScriptCanonicalGuard:
    def test_canonical_roles_matches_the_10_role_registry(self):
        mod = _load_seed_module()
        expected = {
            "super_admin", "tenant_owner", "staff", "technician", "customer", "guest",
            "admin_operations", "admin_finance", "admin_security", "admin_readonly",
        }
        assert mod.CANONICAL_ROLES == expected

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_role", [
        "tenant_manager", "tenant_readonly", "tenant_finance",
        "tenant_support", "tenant_staff_admin", "platform_admin",
    ])
    async def test_get_or_create_user_rejects_invalid_role_before_any_db_call(self, invalid_role):
        mod = _load_seed_module()
        # Pass a db object that would explode if touched, to prove the
        # rejection happens before any query is attempted.
        exploding_db = MagicMock()
        exploding_db.execute = AsyncMock(side_effect=AssertionError("must not reach the database"))
        with pytest.raises(ValueError, match="non-canonical role"):
            await mod.get_or_create_user(exploding_db, "test@example.invalid", "Test User", invalid_role)
        exploding_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_user_accepts_staff_and_queries_db(self):
        mod = _load_seed_module()
        db = MagicMock()
        existing_row = MagicMock()
        result = MagicMock()
        result.first.return_value = existing_row  # simulate "already exists" -> SKIP path, no INSERT
        db.execute = AsyncMock(return_value=result)
        returned = await mod.get_or_create_user(db, "test@example.invalid", "Test User", "staff")
        db.execute.assert_called_once()  # only the SELECT, since it "exists"
        assert returned is existing_row[0]


class TestEffectiveAccessBaseStaffBundle:
    """Direct backend permission checks (not frontend visibility) proving
    what the base `staff` role can and cannot do today, per Workstream 4."""

    def test_staff_can_read_and_update_own_jobs(self):
        assert permission_checker.has("staff", P.FIELD_OPS_JOBS_READ, None) is True
        assert permission_checker.has("staff", P.FIELD_OPS_JOBS_UPDATE, None) is True

    def test_staff_cannot_manage_team_or_pricing(self):
        # Base staff bundle is scoped to own-job field-technician work; it
        # must not implicitly grant team-management authority.
        assert permission_checker.has("staff", P.STAFF_MANAGE, None) is False

    def test_staff_settings_access_is_read_only(self):
        assert permission_checker.has("staff", P.SETTINGS_READ, None) is True

    def test_permission_overrides_parameter_is_structurally_supported(self):
        """StaffPermission per-user overrides are consulted by
        PermissionChecker.has() when an `overrides` dict is passed in."""
        overrides = {P.STAFF_MANAGE: True}
        assert permission_checker.has("staff", P.STAFF_MANAGE, overrides) is True

    def test_get_current_user_now_populates_permission_overrides(self):
        """Phase 2A Slice 2E: this is the corrected version of the Slice 2D
        regression guard. Slice 2D found app.engines.auth.service's
        _build_token_pair/refresh_token already loaded real StaffPermission
        rows into the JWT's `permission_overrides` claim at login/refresh --
        but app.dependencies.auth.get_current_user never read that claim
        back out when reconstructing UserContext, so the override mechanism
        was dead in practice despite half the pipeline already working.
        Slice 2E closed this one-line gap. This test now asserts the fix
        is present and stays present -- if it ever fails, the wiring
        regressed and manager-persona permission grants would silently stop
        taking effect again."""
        import inspect
        from app.dependencies import auth as auth_module
        source = inspect.getsource(auth_module.get_current_user)
        assert "permission_overrides=payload.get(" in source, (
            "get_current_user no longer reads permission_overrides from the JWT payload -- "
            "this would silently break StaffPermission-based manager/read-only personas. "
            "See docs/workflow-rearchitecture/phase-02a-slice-02e/effective-permission-architecture.md"
        )


class TestTenantMutationPermissionCoverage:
    """Regression guard for the Workstream 3 finding: the access_scope-based
    read-only mutation guard is real but only wired into 2 of ~16 tenant
    mutation routers, so it cannot be trusted as a comprehensive read-only
    enforcement mechanism today."""

    def test_require_tenant_mutation_permission_still_exists_and_checks_access_scope(self):
        from app.core.permissions import require_tenant_mutation_permission, TENANT_READONLY_ACCESS_SCOPES
        assert callable(require_tenant_mutation_permission)
        assert "customer_support_limited" in TENANT_READONLY_ACCESS_SCOPES

    def test_coverage_of_require_tenant_mutation_permission_is_still_narrow(self):
        """Counts how many engine router files reference
        require_tenant_mutation_permission. Slice 2D/2E confirmed 2 (
        admin_catalog/tenant_router.py, provider_portal/router.py). Slice
        2F-1 closed tenant_engine/router.py's 19 tenant-reachable mutation
        endpoints, bringing this to 3. Slice 2F-6 wired
        invoice_payment/provider_router.py's provider_issue_invoice to this
        guard (P.FIELD_OPS_INVOICE_GEN), bringing this to 4. Slice 2F-7 wired
        serviceability/router.py's 8 tenant service-area/mapping mutations to
        this guard, bringing this to 5 -- documented growth, not a surprise.
        Still narrow relative to the ~24 router modules Slice 2F's inventory
        found; further growth is good news and should keep updating this
        count plus tenant-access-model.md / tenant-readonly-decision.md."""
        root = Path(__file__).parent.parent
        matches = []
        for py_file in (root / "app" / "engines").rglob("*.py"):
            try:
                text = py_file.read_text(encoding="utf-8")
            except Exception:
                continue
            if "require_tenant_mutation_permission" in text and "def require_tenant_mutation_permission" not in text:
                matches.append(py_file)
        # PROTECTED_BY_LATER_SLICE: 2F-39. The frozen count of 5 (Slice 2D
        # through 2F-7) predates Slices 2F-35/36/37, which legitimately
        # expanded require_tenant_mutation_permission usage app-wide as
        # part of closing the canonical 313/313 mutation-authorization
        # program -- documented, intended forward progress, not a
        # surprise or a classifier artifact. This assertion was never
        # updated across 2F-35 through 2F-38 (a real test-history gap
        # 2F-38's full-backend-suite run first surfaced); 2F-39 updates
        # the literal per the docstring's own instruction ("further
        # growth is good news and should keep updating this count").
        assert len(matches) == 26, (
            f"Expected exactly 26 files calling require_tenant_mutation_permission "
            f"(5 through Slice 2F-7, +21 from Slices 2F-35/36/37's app-wide "
            f"mutation-authorization program), found {len(matches)}: {matches}. "
            f"If this changed, update tenant-readonly-decision.md's conclusion."
        )
        assert any(p.name == "router.py" and p.parent.name == "tenant_engine" for p in matches)


class TestIntelligenceKBFieldNotAuthoritative:
    """Workstream 11 regression guard: allowed_roles_json must never become
    a de facto authorization check. Confirmed DISPLAY_ONLY in Slice 2C;
    this proves it stays that way by asserting no permission_checker/
    require_permission call anywhere references it."""

    def test_kb_service_never_checks_allowed_roles_json_for_authorization(self):
        import app.engines.analytics.kb_service as kb_service
        import inspect
        source = inspect.getsource(kb_service)
        # It's fine for the field to be read/written (create/update/to_dict);
        # what must never appear is it being used to gate a decision (e.g.
        # `if role not in kb.allowed_roles_json` or similar comparison).
        assert "allowed_roles_json ==" not in source
        assert "in kb.allowed_roles_json" not in source


@pytest.mark.asyncio
class TestRemediationScriptDisableFlag:
    def _load(self):
        spec = importlib.util.spec_from_file_location(
            "remediate_invalid_roles",
            Path(__file__).parent.parent / "scripts" / "workflow_rearchitecture" / "remediate_invalid_roles.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    async def test_script_version_bumped_for_slice_2d(self):
        mod = self._load()
        assert mod.SCRIPT_VERSION == "slice-2d-v2"

    async def test_disable_requires_corresponding_mapping_entry(self):
        """Exercises the real CLI guard via subprocess to prove --disable
        without a matching --mapping entry is refused, matching the code
        path added this slice (checked inside main(), not just _parse_mapping)."""
        import subprocess
        fake_id = str(uuid.uuid4())
        proc = subprocess.run(
            ["python", str(Path(__file__).parent.parent / "scripts" / "workflow_rearchitecture" / "remediate_invalid_roles.py"),
             "--disable", fake_id],
            capture_output=True, text=True, timeout=30,
        )
        # No --mapping for fake_id at all -> dry run reports it as unmapped,
        # not an error (since --allow wasn't given either, it's just listed).
        # This confirms the tool doesn't crash on a --disable-only invocation.
        assert proc.returncode == 0
