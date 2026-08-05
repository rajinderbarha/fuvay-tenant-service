"""UX-05 — Home Services Provider Bookability / Provider Matching / Matching
Diagnostics / Home Services Settings consolidation.

Scope note: this suite covers what this pass actually changed --
  1. The bookability override endpoints now reject a positive override
     (override=true) outright, so no admin action can make an ineligible
     provider eligible; only a negative Admin Hold (override=false + reason)
     is permitted.
  2. The standalone Provider Bookability nav entry/page and standalone Home
     Services Settings nav entry were removed; the old bookability route is
     now a redirect-only stub pointing at the merged Provider Matching page's
     "Provider Eligibility" tab, so exactly one live implementation remains.
  3. Provider Matching's tab order is Diagnostics / Provider Eligibility /
     Live Decisions / Policy Reference / Audit.

It does NOT attempt to re-prove the full L5-58 diagnostics/matching-engine
consolidation (see tests/test_module_l5_58_provider_matching.py for that) or
claim full coverage of every item in the UX-05 spec -- several larger pieces
(a dedicated Business Verticals admin surface, full contextual base-readiness
enum, derived Admin Hold data model/migration, cascading blueprint-derived
type/brand selectors) were not implemented in this pass; see the final report
for the honest gap list.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADMIN_ROUTER = (ROOT / "app/engines/provider_portal/admin_router.py").read_text(encoding="utf-8")
FRONTEND = ROOT / "frontend/super-admin"


class TestPositiveOverrideProhibited:
    def test_override_bookability_rejects_positive_override(self):
        idx = ADMIN_ROUTER.index("async def override_bookability(")
        end = ADMIN_ROUTER.index("\n\n\n", idx)
        block = ADMIN_ROUTER[idx:end]
        assert "if override:" in block
        assert "Positive bookability override is prohibited" in block
        assert "status_code=400" in block

    def test_override_visibility_rejects_positive_override(self):
        idx = ADMIN_ROUTER.index("async def override_visibility(")
        end = ADMIN_ROUTER.index("\n\n\n", idx)
        block = ADMIN_ROUTER[idx:end]
        assert "if override:" in block
        assert "Positive visibility override is prohibited" in block
        assert "status_code=400" in block

    def test_admin_hold_requires_a_reason(self):
        for fn in ("async def override_bookability(", "async def override_visibility("):
            idx = ADMIN_ROUTER.index(fn)
            end = ADMIN_ROUTER.index("\n\n\n", idx)
            block = ADMIN_ROUTER[idx:end]
            assert "if not reason:" in block
            assert "A reason is required to apply an Admin Hold." in block


class TestStandaloneBookabilityPageRemoved:
    def test_old_route_redirects_to_provider_matching_eligibility_tab(self):
        src = (FRONTEND / "app/admin/bookability/providers/page.tsx").read_text(encoding="utf-8")
        assert "router.replace" in src
        assert "/admin/home-services/provider-matching?tab=eligibility" in src
        # Confirms no second live implementation lives at the old URL.
        assert "adminBookabilityApi.listProviders" not in src
        assert "Bulk Re-evaluate" not in src

    def test_nav_config_has_no_standalone_bookability_entry(self):
        src = (FRONTEND / "lib/nav-config.ts").read_text(encoding="utf-8")
        assert 'id: "bookability"' not in src
        assert 'id: "hs-settings"' not in src

    def test_admin_layout_has_no_standalone_bookability_or_settings_entry(self):
        src = (FRONTEND / "components/layout/AdminLayout.tsx").read_text(encoding="utf-8")
        assert 'id: "bookability", href: "/admin/bookability/providers"' not in src
        assert 'id: "hs-settings", href: "/admin/home-services/settings"' not in src


class TestProviderEligibilityTabWiredIntoProviderMatching:
    def test_tab_order_is_diagnostics_eligibility_live_policy_audit(self):
        src = (FRONTEND / "app/admin/home-services/provider-matching/page.tsx").read_text(encoding="utf-8")
        idx = src.index('["diagnostics", "Diagnostics"]')
        window = src[idx:idx + 400]
        # Ordered as they appear in the tab-bar array literal.
        assert window.index('"diagnostics"') < window.index('"eligibility"')
        assert window.index('"eligibility"') < window.index('"live"')
        assert window.index('"live"') < window.index('"policy"')
        assert window.index('"policy"') < window.index('"audit"')

    def test_eligibility_tab_reuses_canonical_bookability_api_not_a_new_engine(self):
        src = (FRONTEND / "app/admin/home-services/provider-matching/page.tsx").read_text(encoding="utf-8")
        assert "function ProviderEligibilityTab()" in src
        assert "adminBookabilityApi.listProviders" in src
        assert "adminBookabilityApi.bulkRefresh" in src
        assert "Re-evaluate Eligibility" in src

    def test_eligibility_tab_has_no_global_bookable_kpi_language(self):
        src = (FRONTEND / "app/admin/home-services/provider-matching/page.tsx").read_text(encoding="utf-8")
        idx = src.index("function ProviderEligibilityTab()")
        block = src[idx:]
        # No KPI tile labeled bare "Bookable" -- only "Eligible for Context".
        assert '{ label: "Bookable"' not in block
        assert "Eligible for Context" in block

    def test_eligibility_tab_states_positive_override_is_impossible(self):
        src = (FRONTEND / "app/admin/home-services/provider-matching/page.tsx").read_text(encoding="utf-8")
        idx = src.index("function ProviderEligibilityTab()")
        block = src[idx:]
        assert "Override policy" in block
        assert "not possible" in block
        assert "Admin Hold" in block


class TestHomeServicesSettingsCleanup:
    # As of this pass, /admin/home-services/settings is itself a redirect
    # stub into the canonical Business Verticals workspace (a real
    # /admin/verticals/[key]?tab=capabilities page with its own
    # "Capabilities & Policies" tab) -- so the settings page no longer
    # renders any flag UI (including "Manual Bargain Rules") at all.
    def test_old_settings_route_redirects_to_business_verticals_capabilities(self):
        src = (FRONTEND / "app/admin/home-services/settings/page.tsx").read_text(encoding="utf-8")
        assert "router.replace" in src
        assert "/admin/verticals/home_services" in src
        assert "tab=capabilities" in src

    def test_business_verticals_capabilities_tab_exists(self):
        src = (FRONTEND / "app/admin/verticals/[key]/page.tsx").read_text(encoding="utf-8")
        assert "capabilities" in src
        assert "Capabilities & Policies" in src
