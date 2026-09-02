"""P0 Tenant 360 Enterprise UI Redesign.

Static source-inspection tests (consistent with other page-redesign suites in
this repo) verifying the Tenant Detail page has: grouped tabs (not 23 flat tabs
in one row), an 8-card KPI grid, a bigger/premium hero card with tenant ID copy
and a More Actions menu, reason-gated Request Changes / Send Notification
modals, and a Provider Readiness card with a progress bar + clickable failed
items. No mock data — all values still come from the existing real API hooks.
"""
import os

PAGE = os.path.join(
    os.path.dirname(__file__), "..", "frontend", "super-admin", "app", "admin", "tenants", "[id]", "page.tsx")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestGroupedTabs:
    def test_tab_groups_defined(self):
        src = _read(PAGE)
        assert "TAB_GROUPS" in src

    def test_seven_groups_present(self):
        src = _read(PAGE)
        for label in ["Overview", "Setup", "Operations", "Finance", "Trust & Quality", "Media", "Audit"]:
            assert f'label: "{label}"' in src

    def test_group_pill_nav_renders(self):
        src = _read(PAGE)
        assert "groupForTab(tab).key === g.key" in src

    def test_subtabs_filtered_by_active_group(self):
        src = _read(PAGE)
        assert "TABS.filter(tb => groupForTab(tab).tabs.includes(tb.id))" in src


class TestHeroCard:
    def test_hero_has_tenant_id_copy(self):
        src = _read(PAGE)
        assert "copyTenantId" in src

    def test_hero_has_more_actions_menu(self):
        src = _read(PAGE)
        assert "moreOpen" in src
        assert "Request Changes" in src
        assert "Send Notification" in src

    def test_hero_shows_verification_and_bookable_status(self):
        src = _read(PAGE)
        assert "verification_status" in src
        assert "Bookable" in src

    def test_hero_premium_design(self):
        # Provider 360 redesign: hero uses gradient accent strip + glass card style
        src = _read(PAGE)
        assert "linear-gradient" in src
        assert "boxShadow" in src


class TestKpiGrid:
    def test_provider_kpi_cards(self):
        src = _read(PAGE)
        for label in [
            "Usage Credit Balance", "Credits Deducted Lifetime",
            "Health Score", "Staff Members", "Average Rating", "Open Complaints", "Active Jobs",
        ]:
            assert f'label="{label}"' in src
        assert 'label="Security Deposit Held"' not in src

    def test_kpi_grid_responsive_columns(self):
        src = _read(PAGE)
        # Responsive KPI grid uses kpiCols variable (1 mobile / 2 tablet / 4 desktop)
        assert "kpiCols" in src
        assert "gridTemplateColumns:`repeat(${kpiCols},1fr)`" in src

    def test_no_payout_or_wallet_language_in_kpi_labels(self):
        # KPI card labels specifically must not use payout/wallet language — a page
        # disclaimer elsewhere legitimately says "not a payout balance" (compliance
        # copy), which is fine; only the KPI *labels* themselves are checked here.
        src = _read(PAGE)
        assert "Wallet Balance" not in src
        assert 'label="Payout' not in src


class TestSensitiveActionModals:
    def test_request_changes_requires_reason(self):
        src = _read(PAGE)
        assert "disabled={!reqChangesMsg.trim()}" in src

    def test_send_notification_requires_message(self):
        src = _read(PAGE)
        assert "disabled={!notifyMsg.trim()}" in src

    def test_suspend_still_requires_reason(self):
        src = _read(PAGE)
        assert "Confirm Suspension" in src

    def test_uses_real_admin_tenants_api(self):
        src = _read(PAGE)
        assert "adminTenantsApi.requestChanges" in src
        assert "adminTenantsApi.sendNotification" in src


class TestReadinessCard:
    def test_progress_bar_present(self):
        src = _read(PAGE)
        assert "pct}%" in src or "{pct}%" in src

    def test_failed_items_are_clickable(self):
        src = _read(PAGE)
        assert "jumpTab" in src
        assert "setTab(c.jumpTab as Tab)" in src

    def test_failed_items_use_danger_color(self):
        # Provider 360 redesign: failed checks use danger-bg/border/text styling
        src = _read(PAGE)
        assert "var(--danger-text)" in src
        assert "var(--success-text)" in src
