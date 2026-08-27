"""FINAL-L5-05P — Tenant, Provider and Staff mutation action permission
certification. Static/unit-level guards proving the real, bounded fixes
made this sprint are correct and self-consistent:

1. `app/engines/provider_portal/admin_router.py` had 6 mutation endpoints
   (provider onboarding refresh/send-reminder/checklist-item-override, and
   bookability refresh/override-visibility/remove-visibility/override-
   bookability/remove-bookability) gated by ONLY `get_current_user` -- any
   authenticated principal of ANY role (including customer/technician,
   not just admins) could invoke them. All are now real, gated endpoints.
2. Provider onboarding approve/reject/request-more-info have real, distinct
   backend permissions (TENANT_APPROVE/TENANT_REJECT/
   TENANT_REQUEST_MORE_INFO/TENANT_ONBOARDING_READ) that were granted to
   ZERO non-super-admin roles before this sprint, despite the mission's
   own expected policy (Operations Admin: Tenant/Provider verify = ALLOW).
   admin_operations now holds these 4 permissions; no other non-super-
   admin role does.
3. `app/admin/tenants/[id]/page.tsx` (the mission's own named highest-risk
   example, 3095 lines) had ZERO frontend permission checks across ~24
   mutation actions. The onboarding approve/reject/refresh, offerings
   suspend/reactivate/refresh, bookability override/remove x2, tenant
   suspend/reinstate/request-changes/send-notification/
   export, staff deactivate, user suspend, and add-staff/add-user/add-area
   triggers are now individually gated.

Live cross-role HTTP/Chromium evidence is captured separately in
docs/final-l5-05/FINAL_L5_05P_LIVE_API_MATRIX.md and the Chromium spec.
"""
from __future__ import annotations

from pathlib import Path

from app.core.permissions import P, ROLE_PERMISSIONS, permission_checker

ROOT = Path(__file__).parent.parent


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class TestProviderPortalMutationEndpointsAreGated:
    """All 6 previously-unauthenticated mutation endpoints in
    provider_portal/admin_router.py must now require either a real
    permission or, at minimum, super_admin."""

    def test_no_mutation_endpoint_relies_only_on_get_current_user(self):
        src = _read("app/engines/provider_portal/admin_router.py")
        import re
        lines = src.split("\n")
        offenders = []
        for i, line in enumerate(lines):
            m = re.match(r'@admin_router\.(post|put|delete|patch)\("([^"]+)"', line)
            if not m:
                continue
            method, path = m.groups()
            window = "\n".join(lines[i:i + 15])
            if "Depends(get_current_user" in window and "Depends(require_permission" not in window and "Depends(require_super_admin" not in window:
                offenders.append(f"{method.upper()} {path}")
        assert offenders == [], f"Ungated mutation endpoints remain: {offenders}"

    def test_send_reminder_requires_super_admin(self):
        src = _read("app/engines/provider_portal/admin_router.py")
        start = src.index("async def send_provider_reminder(")
        end = src.index("):\n", start)
        assert "require_super_admin" in src[start:end]

    def test_onboarding_refresh_requires_super_admin(self):
        src = _read("app/engines/provider_portal/admin_router.py")
        start = src.index("async def refresh_provider_onboarding(")
        end = src.index("):\n", start)
        assert "require_super_admin" in src[start:end]

    def test_checklist_item_override_requires_tenant_approve(self):
        src = _read("app/engines/provider_portal/admin_router.py")
        start = src.index("async def override_onboarding_item(")
        end = src.index("):\n", start)
        assert "P.TENANT_APPROVE" in src[start:end]

    def test_bookability_refresh_requires_super_admin(self):
        src = _read("app/engines/provider_portal/admin_router.py")
        start = src.index("async def refresh_bookability(")
        end = src.index("):\n", start)
        assert "require_super_admin" in src[start:end]

    def test_all_four_visibility_bookability_override_endpoints_require_super_admin(self):
        src = _read("app/engines/provider_portal/admin_router.py")
        for fn in ("override_visibility", "remove_visibility_override",
                   "override_bookability", "remove_bookability_override"):
            start = src.index(f"async def {fn}(")
            end = src.index("):\n", start)
            assert "require_super_admin" in src[start:end], f"{fn} must require_super_admin"


class TestTenantOnboardingLifecyclePermissions:
    """TENANT_APPROVE/TENANT_REJECT/TENANT_REQUEST_MORE_INFO/
    TENANT_ONBOARDING_READ are real, pre-existing backend permissions that
    were granted to zero non-super-admin roles before this sprint."""

    def test_admin_operations_holds_all_four_onboarding_permissions(self):
        for perm in (P.TENANT_APPROVE, P.TENANT_REJECT, P.TENANT_REQUEST_MORE_INFO, P.TENANT_ONBOARDING_READ):
            assert permission_checker.has("admin_operations", perm), f"admin_operations must hold {perm}"

    def test_finance_admin_does_not_hold_onboarding_mutation_permissions(self):
        assert not permission_checker.has("admin_finance", P.TENANT_APPROVE)
        assert not permission_checker.has("admin_finance", P.TENANT_REJECT)

    def test_security_admin_does_not_hold_onboarding_mutation_permissions(self):
        assert not permission_checker.has("admin_security", P.TENANT_APPROVE)
        assert not permission_checker.has("admin_security", P.TENANT_REJECT)

    def test_admin_readonly_does_not_hold_onboarding_mutation_permissions(self):
        assert not permission_checker.has("admin_readonly", P.TENANT_APPROVE)
        assert not permission_checker.has("admin_readonly", P.TENANT_REJECT)
        assert not permission_checker.has("admin_readonly", P.TENANT_REQUEST_MORE_INFO)

    def test_backend_approve_reject_request_changes_endpoints_use_real_permissions(self):
        src = _read("app/engines/provider_portal/admin_router.py")
        for fn, perm in (
            ("approve_provider_onboarding", "P.TENANT_APPROVE"),
            ("reject_provider_onboarding", "P.TENANT_REJECT"),
            ("request_changes_provider_onboarding", "P.TENANT_REQUEST_MORE_INFO"),
        ):
            start = src.index(f"async def {fn}(")
            end = src.index("):\n", start)
            assert perm in src[start:end]


class TestTenantDetailPageActionGating:
    """app/admin/tenants/[id]/page.tsx -- the mission's own named
    highest-risk example -- now has usePermissions wired and every
    identified mutation action individually gated."""

    def test_page_imports_use_permissions(self):
        src = _read("frontend/super-admin/app/admin/tenants/[id]/page.tsx")
        assert 'usePermissions' in src

    def test_onboarding_tab_gates_approve_reject_by_real_permission(self):
        src = _read("frontend/super-admin/app/admin/tenants/[id]/page.tsx")
        assert 'perm.has("tenants.approve")' in src
        assert 'perm.has("tenants.reject")' in src

    def test_tenant_lifecycle_actions_gated_by_super_admin_role(self):
        src = _read("frontend/super-admin/app/admin/tenants/[id]/page.tsx")
        # Suspend/Reinstate/Request Changes/Send Notification/
        # Export all call backend endpoints requiring super_admin (not yet
        # granular) -- must be gated by role check, not left unguarded.
        count = src.count('perm.role === "super_admin"')
        assert count >= 10, f'Expected at least 10 perm.role === "super_admin" gates, found {count}'

    def test_bookability_override_actions_gated(self):
        src = _read("frontend/super-admin/app/admin/tenants/[id]/page.tsx")
        idx = src.index("function BookabilityTab(")
        end = src.index("\n}\n", idx)
        block = src[idx:end]
        assert block.count('perm.role === "super_admin"') >= 5

    def test_staff_and_user_row_mutations_gated(self):
        src = _read("frontend/super-admin/app/admin/tenants/[id]/page.tsx")
        # Deactivate staff row action
        idx = src.index("deactivateStaffAction.loading}")
        window = src[max(0, idx - 300):idx]
        assert 'perm.role === "super_admin"' in window
        # Suspend user row action
        idx2 = src.index("suspendUserAction.loading}")
        window2 = src[max(0, idx2 - 300):idx2]
        assert 'perm.role === "super_admin"' in window2

    def test_add_staff_add_user_add_area_triggers_gated(self):
        src = _read("frontend/super-admin/app/admin/tenants/[id]/page.tsx")
        for trigger in ("setAddStaffOpen(true)", "setAddUserOpen(true)", "setAddAreaOpen(true)"):
            idx = src.index(trigger)
            window = src[max(0, idx - 150):idx]
            assert 'perm.role === "super_admin"' in window, f"{trigger} is missing its super_admin gate"


class TestBookabilityProvidersListPageGating:
    def test_bulk_refresh_gated_by_super_admin(self):
        src = _read("frontend/super-admin/app/admin/bookability/providers/page.tsx")
        assert 'usePermissions' in src
        idx = src.index("Bulk Re-evaluate")
        window = src[max(0, idx - 500):idx]
        assert 'perm.role === "super_admin"' in window


class TestStaffPagesAreReadOnly:
    """/admin/staff and /admin/staff/[id] were confirmed (via source read)
    to have zero mutation actions -- a genuine finding, not an oversight
    to fix. This guard pins that fact so a future regression (adding an
    ungated mutation) is caught."""

    def test_staff_list_page_has_no_use_action_hooks(self):
        src = _read("frontend/super-admin/app/admin/staff/page.tsx")
        assert "useAction(" not in src

    def test_staff_detail_page_has_no_use_action_hooks(self):
        src = _read("frontend/super-admin/app/admin/staff/[id]/page.tsx")
        assert "useAction(" not in src


class TestPermissionCatalogValidity:
    def test_all_new_tenant_permission_keys_exist_in_backend_registry(self):
        backend_keys = {
            P.TENANT_ONBOARDING_READ, P.TENANT_APPROVE, P.TENANT_REJECT, P.TENANT_REQUEST_MORE_INFO,
        }
        src = _read("frontend/super-admin/lib/permission-catalog.ts")
        for key in backend_keys:
            assert f'"{key}"' in src, f"{key} referenced conceptually but missing from permission-catalog.ts"
