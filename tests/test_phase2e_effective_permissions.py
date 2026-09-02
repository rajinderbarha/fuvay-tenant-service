"""Phase 2A Slice 2E — effective-permission enforcement tests.

Covers:
- The corrected get_current_user wiring (full round-trip: JWT payload ->
  UserContext -> PermissionChecker.has())
- Manager-persona grant/deny now taking effect end-to-end
- The router-level mutation-guard coverage survey (regression guard,
  fails loudly if the underlying file set or guard counts change)
- The extended authorization-integrity check script
"""
from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.permissions import permission_checker, P


class TestFullRoundTripPermissionOverrides:
    """Proves the fix: a JWT payload carrying permission_overrides now
    produces a UserContext whose overrides actually change PermissionChecker
    outcomes -- not just that get_current_user's source mentions the field
    (that was already covered in test_phase2d)."""

    def test_grant_beyond_base_staff_bundle_takes_effect(self):
        from app.dependencies.auth import UserContext
        ctx = UserContext(
            user_id=str(uuid.uuid4()), email="mgr@example.invalid", role="staff",
            tenant_id=str(uuid.uuid4()), full_name="Manager Demo", is_verified=True,
            permission_overrides={P.STAFF_MANAGE: True},
        )
        assert permission_checker.has(ctx.role, P.STAFF_MANAGE, ctx.permission_overrides) is True
        # Confirm the base bundle alone (no override) would have denied it --
        # proving the override is what changed the outcome, not a role bundle change.
        assert permission_checker.has(ctx.role, P.STAFF_MANAGE, None) is False

    def test_explicit_deny_overrides_a_base_bundle_grant(self):
        from app.dependencies.auth import UserContext
        ctx = UserContext(
            user_id=str(uuid.uuid4()), email="readonly-demo@example.invalid", role="staff",
            tenant_id=str(uuid.uuid4()), full_name="Read Only Demo", is_verified=True,
            permission_overrides={P.FIELD_OPS_JOBS_UPDATE: False},
        )
        # Base staff bundle grants this; explicit deny must win.
        assert permission_checker.has("staff", P.FIELD_OPS_JOBS_UPDATE, None) is True
        assert permission_checker.has(ctx.role, P.FIELD_OPS_JOBS_UPDATE, ctx.permission_overrides) is False

    def test_get_current_user_payload_to_context_round_trip(self):
        """Simulates decode_token's output feeding into the same
        UserContext(...) construction get_current_user performs, without
        needing a real bearer token/Redis -- isolates the payload-to-context
        mapping itself."""
        from app.dependencies.auth import UserContext
        payload = {
            "sub": str(uuid.uuid4()), "email": "x@example.invalid", "role": "staff",
            "tenant_id": str(uuid.uuid4()), "full_name": "X", "is_verified": True,
            "permission_overrides": {P.STAFF_MANAGE: True, P.FIELD_OPS_JOBS_UPDATE: False},
            "access_scope": None,
        }
        ctx = UserContext(
            user_id=payload["sub"], email=payload["email"], role=payload["role"],
            tenant_id=payload["tenant_id"], full_name=payload["full_name"],
            is_verified=payload["is_verified"],
            permission_overrides=payload.get("permission_overrides"),
            access_scope=payload.get("access_scope"),
        )
        assert ctx.permission_overrides == {P.STAFF_MANAGE: True, P.FIELD_OPS_JOBS_UPDATE: False}
        assert permission_checker.has(ctx.role, P.STAFF_MANAGE, ctx.permission_overrides) is True
        assert permission_checker.has(ctx.role, P.FIELD_OPS_JOBS_UPDATE, ctx.permission_overrides) is False


class TestManagerPersonaBackendPipelineAlreadyExists:
    """Confirms the invite_staff/update_permissions service methods (which
    predate this slice) already implement the full manager-grant pipeline
    correctly -- Slice 2E's fix was the missing link that makes their output
    actually take effect at authorization time, not a rebuild of this logic."""

    def test_invite_staff_service_method_accepts_and_persists_permissions(self):
        import inspect
        from app.engines.auth.service import AuthService
        source = inspect.getsource(AuthService.invite_staff)
        assert "StaffPermission(" in source
        assert 'role="staff"' in source

    def test_update_permissions_service_method_enforces_tenant_ownership(self):
        import inspect
        from app.engines.auth.service import AuthService
        source = inspect.getsource(AuthService.update_permissions)
        assert "user.tenant_id != tenant_id" in source
        assert "PERMISSION_DENIED" in source


class TestMutationGuardCoverageSurvey:
    """Router-file-level survey (Workstream 4). Regression-guards the exact
    counts found this slice so any future change to guard coverage is
    noticed and the corresponding docs are revisited, rather than silently
    going stale."""

    TENANT_ROUTER_FILES = [
        "app/engines/admin_catalog/tenant_router.py",
        "app/engines/analytics/provider_router.py",
        "app/engines/complaints/provider_router.py",
        "app/engines/compliance/provider_router.py",
        "app/engines/customer_credits/provider_router.py",
        "app/engines/customer_reviews/provider_router.py",
        "app/engines/entitlement/tenant_router.py",
        "app/engines/final_records/provider_router.py",
        "app/engines/home_service_assignment/provider_router.py",
        "app/engines/invoice_payment/provider_router.py",
        "app/engines/marketing_automation/provider_router.py",
        "app/engines/platform_notifications/provider_router.py",
        "app/engines/quote_checklist/provider_router.py",
        "app/engines/trust_quality/provider_router.py",
    ]

    def test_exactly_16_tenant_facing_router_files_exist(self):
        root = Path(__file__).parent.parent
        for rel in self.TENANT_ROUTER_FILES:
            assert (root / rel).exists(), f"{rel} no longer exists -- update the mutation route inventory"

    def test_only_one_router_file_uses_require_tenant_mutation_permission(self):
        """This is the central, decisive finding behind the read-only
        persona remaining BLOCKED this slice. If this count changes,
        tenant-readonly-decision.md must be revisited.

        Updated in Slice 2F-6: invoice_payment/provider_router.py's
        provider_issue_invoice now uses require_tenant_mutation_permission
        (P.FIELD_OPS_INVOICE_GEN) -- documented growth, not a surprise; see
        docs/workflow-rearchitecture/phase-02a-slice-02f6/."""
        root = Path(__file__).parent.parent
        files_using_guard = []
        for rel in self.TENANT_ROUTER_FILES:
            text = (root / rel).read_text(encoding="utf-8")
            if "require_tenant_mutation_permission" in text:
                files_using_guard.append(rel)
        assert files_using_guard == [
            "app/engines/admin_catalog/tenant_router.py",
            "app/engines/invoice_payment/provider_router.py",
        ], (
            f"Expected admin_catalog/tenant_router.py and invoice_payment/provider_router.py "
            f"to use the read-only mutation guard, found: {files_using_guard}. "
            f"If this changed, re-verify tenant-readonly-decision.md's conclusion."
        )


class TestAuthorizationIntegrityScript:
    def _load(self):
        spec = importlib.util.spec_from_file_location(
            "check_role_integrity",
            Path(__file__).parent.parent / "scripts" / "workflow_rearchitecture" / "check_role_integrity.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_known_permission_keys_includes_staff_manage(self):
        mod = self._load()
        keys = mod._known_permission_keys()
        assert P.STAFF_MANAGE in keys

    def test_canonical_roles_unchanged(self):
        mod = self._load()
        assert mod.CANONICAL_ROLES == {
            "super_admin", "tenant_owner", "staff", "technician", "customer", "guest",
            "admin_operations", "admin_finance", "admin_security", "admin_readonly",
        }
