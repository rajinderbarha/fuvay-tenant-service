"""Category Rates rebuild — vertical_monetization backend additions.

Static source-inspection style (consistent with test_p0_finance_enterprise.py's
convention in this repo — no live DB fixture required). Covers:
  - the new /impact endpoint (Selected Policy Inspector numbers)
  - invalid_mappings drift signal in the summary
  - FINANCE_AUDIT_READ permission gap fix (was defined but granted to no
    bundle except super_admin's wildcard)
  - read routes are never gated by require_vertical_enabled (a disabled
    vertical's historical policy must still be viewable)
  - cross-vertical isolation of the impact query (category_id scoping)
"""
import os

ROOT = os.path.dirname(os.path.dirname(__file__))
POLICY_SERVICE = os.path.join(ROOT, "app", "engines", "vertical_monetization", "policy_service.py")
ADMIN_ROUTER = os.path.join(ROOT, "app", "engines", "vertical_monetization", "admin_router.py")
PERMISSIONS_FILE = os.path.join(ROOT, "app", "core", "permissions.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestImpactEndpoint:
    def test_router_has_impact_route(self):
        src = _read(ADMIN_ROUTER)
        assert '"/verticals/{key}/impact"' in src

    def test_impact_route_requires_read_permission_not_disabled_gate(self):
        src = _read(ADMIN_ROUTER)
        # locate the impact handler block
        idx = src.index('"/verticals/{key}/impact"')
        block = src[idx: idx + 600]
        assert "P.FINANCE_MONETIZATION_READ" in block
        assert "require_vertical_enabled" not in block

    def test_policy_service_get_impact_scopes_by_category_id(self):
        src = _read(POLICY_SERVICE)
        assert "async def get_impact" in src
        idx = src.index("async def get_impact")
        block = src[idx: idx + 3200]
        assert "ServiceGroup.category_id.in_(category_ids)" in block
        assert "MasterService.category_id.in_(category_ids)" in block
        # honest gap for non-home_services verticals
        assert "active_or_in_progress_jobs_available" in block

    def test_impact_only_computes_live_jobs_for_home_services(self):
        src = _read(POLICY_SERVICE)
        idx = src.index("async def get_impact")
        block = src[idx: idx + 2200]
        assert 'if key == "home_services":' in block


class TestInvalidMappingsSummary:
    def test_summary_reports_invalid_mappings_count(self):
        src = _read(ADMIN_ROUTER)
        assert '"invalid_mappings": invalid_mappings' in src

    def test_mapping_invalid_compares_finance_model_tag_to_policy_provider_model(self):
        src = _read(ADMIN_ROUTER)
        assert "v.finance_model.upper() != current.provider_model" in src

    def test_mapping_invalid_only_set_when_current_policy_exists(self):
        # a vertical with no published policy is "Needs review", not "Invalid" --
        # those are distinct states and must not double-count.
        src = _read(ADMIN_ROUTER)
        idx = src.index("mapping_invalid = False")
        block = src[idx: idx + 500]
        assert "if current:" in block


class TestFinanceAuditReadPermissionGap:
    """FINANCE_AUDIT_READ was defined (permissions.py:352) but referenced
    nowhere in ROLE_PERMISSIONS except super_admin's P.ALL wildcard -- a
    Finance Admin opening Category Rates' Audit tab would 403. Fixed by
    granting it to admin_finance (full) and admin_readonly (view-only,
    matching every other *_READ pattern in that bundle)."""

    def test_admin_finance_bundle_grants_audit_read(self):
        src = _read(PERMISSIONS_FILE)
        idx = src.index('"admin_finance": [')
        end = src.index('"admin_security": [')
        block = src[idx:end]
        assert "P.FINANCE_AUDIT_READ" in block

    def test_admin_readonly_bundle_grants_audit_read(self):
        src = _read(PERMISSIONS_FILE)
        idx = src.index('"admin_readonly": [')
        block = src[idx: idx + 4000]
        assert "P.FINANCE_AUDIT_READ" in block

    def test_admin_readonly_still_lacks_draft_and_publish(self):
        src = _read(PERMISSIONS_FILE)
        idx = src.index('"admin_readonly": [')
        block = src[idx: idx + 4000]
        assert "P.FINANCE_MONETIZATION_DRAFT" not in block
        assert "P.FINANCE_MONETIZATION_PUBLISH" not in block


class TestPolicyReadRoutesNeverBlockedByVerticalDisabled:
    """A disabled vertical's historical policy and audit trail must remain
    viewable (only NEW runtime activity is blocked by require_vertical_enabled
    elsewhere in the codebase) -- none of monetization's GET routes may
    depend on that guard."""

    def test_no_read_route_depends_on_require_vertical_enabled(self):
        src = _read(ADMIN_ROUTER)
        assert "require_vertical_enabled" not in src
