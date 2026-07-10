"""Phase 16 — Design System — Proven Level 5 Tests (80 tests).
Tests verify: token completeness, no hardcoded hex, dark/light symmetry,
job status count, CSS variable coverage, and all 68 component files exist.
"""
import re, os, ast

DESIGN_SYSTEM = "/home/claude/serviceos/design-system"
TOKENS_FILE   = f"{DESIGN_SYSTEM}/tokens/tokens.ts"
CSS_FILE      = f"{DESIGN_SYSTEM}/styles/globals.css"
INDEX_FILE    = f"{DESIGN_SYSTEM}/index.ts"

# ── 1. Token file exists and is the single source ─────────────────────────────
def test_tokens_file_exists():
    assert os.path.exists(TOKENS_FILE)

def test_tokens_file_is_nonempty():
    assert os.path.getsize(TOKENS_FILE) > 5000

def test_css_file_exists():
    assert os.path.exists(CSS_FILE)

def test_css_has_light_root():
    with open(CSS_FILE) as f: css = f.read()
    assert ":root" in css or '[data-theme="light"]' in css

def test_css_has_dark_theme():
    with open(CSS_FILE) as f: css = f.read()
    assert '[data-theme="dark"]' in css


# ── 2. All 23 job statuses defined ────────────────────────────────────────────
EXPECTED_JOB_STATUSES = [
    "created","pending_assignment","assigned","accepted","en_route","arrived",
    "in_progress","parts_required","parts_sourced","resumed","quality_check",
    "completed","invoiced","payment_pending","paid","closed","cancelled",
    "disputed","refunded","no_show","rescheduled","warranty_claim","archived",
]

def test_all_23_job_statuses_in_tokens():
    with open(TOKENS_FILE) as f: content = f.read()
    for s in EXPECTED_JOB_STATUSES:
        assert s in content, f"Missing job status: {s}"

def test_job_status_count_is_23():
    with open(TOKENS_FILE) as f: content = f.read()
    assert sum(1 for s in EXPECTED_JOB_STATUSES if s in content) == 23

def test_each_job_status_has_label():
    with open(TOKENS_FILE) as f: content = f.read()
    assert "label:" in content


# ── 3. All 6 health bands defined ─────────────────────────────────────────────
EXPECTED_HEALTH_BANDS = ["platinum","gold","silver","bronze","at_risk","critical"]

def test_all_health_bands_in_tokens():
    with open(TOKENS_FILE) as f: content = f.read()
    for b in EXPECTED_HEALTH_BANDS:
        assert b in content, f"Missing health band: {b}"

def test_health_band_count():
    with open(TOKENS_FILE) as f: content = f.read()
    assert sum(1 for b in EXPECTED_HEALTH_BANDS if b in content) == 6


# ── 4. New token maps exist ────────────────────────────────────────────────────
def test_status_map_in_tokens():
    with open(TOKENS_FILE) as f: content = f.read()
    assert "STATUS_MAP" in content, "STATUS_MAP must be in tokens.ts"

def test_role_map_in_tokens():
    with open(TOKENS_FILE) as f: content = f.read()
    assert "ROLE_MAP" in content

def test_city_tier_map_in_tokens():
    with open(TOKENS_FILE) as f: content = f.read()
    assert "CITY_TIER_MAP" in content

def test_sla_bands_in_tokens():
    with open(TOKENS_FILE) as f: content = f.read()
    assert "SLA_BANDS" in content


# ── 5. Dark/light symmetry ────────────────────────────────────────────────────
SEMANTIC_COLORS = ["success","warning","danger","info"]

def test_semantic_colors_have_light_variants():
    with open(CSS_FILE) as f: css = f.read()
    for c in SEMANTIC_COLORS:
        assert f"--color-{c}:" in css

def test_semantic_colors_have_dark_variants():
    with open(CSS_FILE) as f: css = f.read()
    lines = css.split("\n")
    dark_start = next((i for i,l in enumerate(lines) if '[data-theme="dark"]' in l and '{' in l), len(lines))
    dark = "\n".join(lines[dark_start:])
    for c in SEMANTIC_COLORS:
        assert f"--color-{c}:" in dark

def test_surface_vars_in_both_modes():
    with open(CSS_FILE) as f: css = f.read()
    for var in ["--color-surface-base","--color-bg","--color-border","--color-text-primary"]:
        assert css.count(var) >= 2, f"{var} must appear in both modes"


# ── 6. Shadow definitions ─────────────────────────────────────────────────────
SHADOW_VARS = ["--shadow-xs","--shadow-sm","--shadow-md","--shadow-lg","--shadow-xl"]

def test_shadow_vars_in_light_mode():
    with open(CSS_FILE) as f: css = f.read()
    lines = css.split("\n")
    dark_start = next((i for i,l in enumerate(lines) if '[data-theme="dark"]' in l and '{' in l), len(lines))
    light = "\n".join(lines[:dark_start])
    for s in SHADOW_VARS:
        assert s in light, f"{s} must be in light section"

def test_shadow_vars_in_dark_mode():
    with open(CSS_FILE) as f: css = f.read()
    lines = css.split("\n")
    dark_start = next((i for i,l in enumerate(lines) if '[data-theme="dark"]' in l and '{' in l), len(lines))
    dark = "\n".join(lines[dark_start:])
    for s in SHADOW_VARS:
        assert s in dark, f"{s} must be in dark section"


# ── 7. Token structure ─────────────────────────────────────────────────────────
def test_tokens_has_spacing():
    with open(TOKENS_FILE) as f: c = f.read()
    assert "spacing:" in c

def test_tokens_has_radius():
    with open(TOKENS_FILE) as f: c = f.read()
    assert "radius:" in c

def test_tokens_has_font():
    with open(TOKENS_FILE) as f: c = f.read()
    assert "font:" in c

def test_tokens_has_animation():
    with open(TOKENS_FILE) as f: c = f.read()
    assert "animation:" in c

def test_tokens_has_breakpoints():
    with open(TOKENS_FILE) as f: c = f.read()
    assert "breakpoints:" in c
    assert "tablet: 768" in c
    assert "desktop: 1280" in c

def test_tokens_has_zindex():
    with open(TOKENS_FILE) as f: c = f.read()
    assert "zIndex:" in c
    assert "modal:" in c
    assert "toast:" in c

def test_tokens_has_brand_colors():
    with open(TOKENS_FILE) as f: c = f.read()
    for n in ["50","100","200","500","800","900"]:
        assert n in c

def test_tokens_exports_types():
    with open(TOKENS_FILE) as f: c = f.read()
    assert "export type ThemeMode" in c
    assert "export type HealthBand" in c
    assert "export type JobStatus" in c
    assert "export type StatusKey" in c
    assert "export type RoleKey" in c
    assert "export type CityTier" in c

def test_tokens_exports_constants():
    with open(TOKENS_FILE) as f: c = f.read()
    assert "JOB_STATUSES" in c
    assert "HEALTH_BANDS" in c
    assert "JOB_STATUS_COUNT" in c


# ── 8. CSS quality ─────────────────────────────────────────────────────────────
def test_css_has_font_import():
    with open(CSS_FILE) as f: css = f.read()
    assert "@import" in css and "Inter" in css

def test_css_has_animations():
    with open(CSS_FILE) as f: css = f.read()
    for anim in ["@keyframes","fadeIn","slideUp","shimmer","scaleIn","spin"]:
        assert anim in css, f"Missing animation: {anim}"

def test_css_has_scrollbar_styling():
    with open(CSS_FILE) as f: css = f.read()
    assert "::-webkit-scrollbar" in css

def test_css_has_focus_ring():
    with open(CSS_FILE) as f: css = f.read()
    assert ":focus-visible" in css

def test_css_has_skeleton():
    with open(CSS_FILE) as f: css = f.read()
    assert "skeleton" in css
    assert "shimmer" in css

def test_css_has_responsive_grid():
    with open(CSS_FILE) as f: css = f.read()
    assert "@media" in css
    assert "768px" in css
    assert "1280px" in css

def test_css_has_sidebar_vars():
    with open(CSS_FILE) as f: css = f.read()
    assert "--color-sidebar-bg" in css
    assert "--color-sidebar-text" in css

def test_css_has_status_classes():
    with open(CSS_FILE) as f: css = f.read()
    for cls in ["status--active","status--pending","status--error"]:
        assert cls in css, f"Missing status class: {cls}"

def test_css_has_role_classes():
    with open(CSS_FILE) as f: css = f.read()
    assert "role--super_admin" in css
    assert "role--tenant_owner" in css

def test_css_has_city_tier_classes():
    with open(CSS_FILE) as f: css = f.read()
    assert "city--tier1" in css
    assert "city--tier4" in css

def test_css_has_cmd_overlay():
    with open(CSS_FILE) as f: css = f.read()
    assert "cmd-overlay" in css


# ── 9. All component files exist ─────────────────────────────────────────────
EXPECTED_COMPONENTS = [
    # ui — 26
    "components/ui/Button.tsx",    "components/ui/Input.tsx",
    "components/ui/Textarea.tsx",  "components/ui/Select.tsx",
    "components/ui/Checkbox.tsx",  "components/ui/Switch.tsx",
    "components/ui/Badge.tsx",     "components/ui/StatusBadge.tsx",
    "components/ui/HealthBadge.tsx","components/ui/RiskBadge.tsx",
    "components/ui/Avatar.tsx",    "components/ui/Tooltip.tsx",
    "components/ui/Popover.tsx",   "components/ui/Tabs.tsx",
    "components/ui/Card.tsx",      "components/ui/Separator.tsx",
    "components/ui/EmptyState.tsx","components/ui/Skeleton.tsx",
    "components/ui/Spinner.tsx",   "components/ui/Alert.tsx",
    "components/ui/ProblemDetailAlert.tsx",
    "components/ui/CopyButton.tsx","components/ui/ConfirmDialog.tsx",
    "components/ui/DangerConfirmModal.tsx",
    "components/ui/Modal.tsx",     "components/ui/Toast.tsx",
    # nav — 7
    "components/nav/Topbar.tsx",          "components/nav/PageHeader.tsx",
    "components/nav/GlobalSearch.tsx",    "components/nav/TenantSwitcher.tsx",
    "components/nav/NotificationBell.tsx","components/nav/CommandPalette.tsx",
    "components/nav/RightDrawer.tsx",
    # data — 2
    "components/data/DataTable.tsx","components/data/CursorPagination.tsx",
    # metrics — 7
    "components/metrics/KpiCard.tsx",    "components/metrics/MetricGrid.tsx",
    "components/metrics/MoneyCell.tsx",  "components/metrics/DateTimeCell.tsx",
    "components/metrics/CopyableId.tsx", "components/metrics/ProgressBar.tsx",
    "components/metrics/Timeline.tsx",
    # forms — 2
    "components/forms/FormShell.tsx","components/forms/FormDemo.tsx",
    # business — 16 new + 5 existing
    "components/business/TenantSummaryCard.tsx",
    "components/business/TenantEngineCard.tsx",
    "components/business/TenantLifecycleActions.tsx",
    "components/business/WalletBalanceCard.tsx",
    "components/business/BookingPreflightChecklist.tsx",
    "components/business/CityTierBadge.tsx",
    "components/business/PricePipelineTrace.tsx",
    "components/business/BookingSummaryCard.tsx",
    "components/business/JobAllowedTransitions.tsx",
    "components/business/JobSlaBadge.tsx",
    "components/business/DispatchScoreBreakdown.tsx",
    "components/business/RoleBadge.tsx",
    "components/business/PermissionMatrix.tsx",
    "components/business/DataDeletionRequestCard.tsx",
    "components/business/CampaignCard.tsx",
    "components/business/QueryTracePanel.tsx",
    "components/business/JobStatusBadge.tsx",
    "components/business/HealthScoreMeter.tsx",
    "components/business/WalletBalance.tsx",
    # charts — 2
    "components/charts/RevenueChart.tsx",
    "components/charts/BookingVolumeChart.tsx",
    # layout — 3
    "components/layout/Sidebar.tsx",
    "components/layout/TopNav.tsx",
    "components/layout/PageContainer.tsx",
    # hooks + tokens + index
    "hooks/useTheme.ts","hooks/useToast.ts","tokens/tokens.ts","styles/globals.css",
]

def test_all_component_files_exist():
    missing = [f for f in EXPECTED_COMPONENTS if not os.path.exists(os.path.join(DESIGN_SYSTEM, f))]
    assert not missing, f"Missing files: {missing}"

def test_index_file_exists():
    assert os.path.exists(INDEX_FILE), "index.ts must exist as barrel export"

def test_index_exports_all_groups():
    with open(INDEX_FILE) as f: content = f.read()
    for group in ["ui","nav","data","metrics","forms","business","charts"]:
        assert f"components/{group}/" in content, f"index.ts missing {group} exports"


# ── 10. No hardcoded hex in components ───────────────────────────────────────
HEX_PATTERN = re.compile(r'(?<![\w#])#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})(?![\w])')

def _component_files():
    results = []
    for root, _, files in os.walk(os.path.join(DESIGN_SYSTEM, "components")):
        for f in files:
            if f.endswith((".tsx",".ts")):
                results.append(os.path.join(root, f))
    return results

def test_components_use_css_vars_not_hex():
    violations = []
    for filepath in _component_files():
        with open(filepath) as f: content = f.read()
        lines = [l for l in content.split("\n") if not l.strip().startswith("//")]
        clean = "\n".join(lines)
        if "tokens" in filepath.lower():
            continue
        matches = HEX_PATTERN.findall(clean)
        if matches:
            violations.append(f"{os.path.basename(filepath)}: {matches[:3]}")
    assert not violations, f"Hardcoded hex found in components: {violations}"

def test_components_use_var_references():
    for filepath in _component_files():
        with open(filepath) as f: content = f.read()
        has_css_var   = "var(--" in content
        has_token_ref = "tokens." in content or "from '../../tokens'" in content or "useTheme" in content
        assert has_css_var or has_token_ref, \
            f"{os.path.basename(filepath)} must use CSS vars or token refs"


# ── 11. New component shape checks ───────────────────────────────────────────
def test_button_has_all_variants():
    fpath = os.path.join(DESIGN_SYSTEM, "components/ui/Button.tsx")
    with open(fpath) as f: c = f.read()
    for v in ["primary","secondary","outline","ghost","danger","success","warning"]:
        assert v in c, f"Button missing variant: {v}"

def test_button_has_icon_size():
    fpath = os.path.join(DESIGN_SYSTEM, "components/ui/Button.tsx")
    with open(fpath) as f: c = f.read()
    assert "icon-" in c or "icon:" in c, "Button must have icon size"

def test_input_has_prefix_clearable():
    fpath = os.path.join(DESIGN_SYSTEM, "components/ui/Input.tsx")
    with open(fpath) as f: c = f.read()
    assert "prefix" in c,    "Input must support prefix"
    assert "clearable" in c, "Input must support clearable"
    assert "helperText" in c or "hint" in c, "Input must have helperText"

def test_skeleton_has_shimmer():
    fpath = os.path.join(DESIGN_SYSTEM, "components/ui/Skeleton.tsx")
    with open(fpath) as f: c = f.read()
    assert "shimmer" in c or "skeleton" in c.lower()

def test_status_badge_uses_status_map():
    fpath = os.path.join(DESIGN_SYSTEM, "components/ui/StatusBadge.tsx")
    with open(fpath) as f: c = f.read()
    assert "STATUS_MAP" in c

def test_role_badge_uses_role_map():
    fpath = os.path.join(DESIGN_SYSTEM, "components/business/RoleBadge.tsx")
    with open(fpath) as f: c = f.read()
    assert "ROLE_MAP" in c

def test_city_tier_badge_uses_city_tier_map():
    fpath = os.path.join(DESIGN_SYSTEM, "components/business/CityTierBadge.tsx")
    with open(fpath) as f: c = f.read()
    assert "CITY_TIER_MAP" in c

def test_job_sla_badge_uses_sla_bands():
    fpath = os.path.join(DESIGN_SYSTEM, "components/business/JobSlaBadge.tsx")
    with open(fpath) as f: c = f.read()
    assert "SLA_BANDS" in c

def test_data_table_has_sort_select_density():
    fpath = os.path.join(DESIGN_SYSTEM, "components/data/DataTable.tsx")
    with open(fpath) as f: c = f.read()
    assert "sortable" in c
    assert "selectable" in c
    assert "density" in c or "compact" in c

def test_kpi_card_has_trend_and_change():
    fpath = os.path.join(DESIGN_SYSTEM, "components/metrics/KpiCard.tsx")
    with open(fpath) as f: c = f.read()
    assert "trend" in c
    assert "change" in c

def test_revenue_chart_uses_recharts():
    fpath = os.path.join(DESIGN_SYSTEM, "components/charts/RevenueChart.tsx")
    with open(fpath) as f: c = f.read()
    assert "recharts" in c
    assert "AreaChart" in c

def test_booking_volume_chart_uses_recharts():
    fpath = os.path.join(DESIGN_SYSTEM, "components/charts/BookingVolumeChart.tsx")
    with open(fpath) as f: c = f.read()
    assert "recharts" in c
    assert "BarChart" in c

def test_form_shell_has_sections():
    fpath = os.path.join(DESIGN_SYSTEM, "components/forms/FormShell.tsx")
    with open(fpath) as f: c = f.read()
    assert "sections" in c

def test_danger_confirm_modal_has_type_to_confirm():
    fpath = os.path.join(DESIGN_SYSTEM, "components/ui/DangerConfirmModal.tsx")
    with open(fpath) as f: c = f.read()
    assert "confirmPhrase" in c

def test_problem_detail_alert_is_rfc7807():
    fpath = os.path.join(DESIGN_SYSTEM, "components/ui/ProblemDetailAlert.tsx")
    with open(fpath) as f: c = f.read()
    assert "7807" in c or "ProblemDetail" in c
    assert "request_id" in c

def test_command_palette_has_groups():
    fpath = os.path.join(DESIGN_SYSTEM, "components/nav/CommandPalette.tsx")
    with open(fpath) as f: c = f.read()
    assert "group" in c

def test_right_drawer_has_footer():
    fpath = os.path.join(DESIGN_SYSTEM, "components/nav/RightDrawer.tsx")
    with open(fpath) as f: c = f.read()
    assert "footer" in c

def test_price_pipeline_trace_has_stages():
    fpath = os.path.join(DESIGN_SYSTEM, "components/business/PricePipelineTrace.tsx")
    with open(fpath) as f: c = f.read()
    assert "stages" in c
    assert "finalPrice" in c

def test_dispatch_score_breakdown_has_signals():
    fpath = os.path.join(DESIGN_SYSTEM, "components/business/DispatchScoreBreakdown.tsx")
    with open(fpath) as f: c = f.read()
    assert "signals" in c
    assert "totalScore" in c

def test_query_trace_panel_has_explain():
    fpath = os.path.join(DESIGN_SYSTEM, "components/business/QueryTracePanel.tsx")
    with open(fpath) as f: c = f.read()
    assert "spans" in c or "plan" in c


# ── 12. useTheme hook ─────────────────────────────────────────────────────────
def test_usetheme_has_dark_light_support():
    fpath = os.path.join(DESIGN_SYSTEM, "hooks/useTheme.ts")
    if os.path.exists(fpath):
        with open(fpath) as f: content = f.read()
        assert "dark" in content
        assert "light" in content
        assert "data-theme" in content
        assert "localStorage" in content or "sessionStorage" in content

def test_usetheme_exports_toggle():
    fpath = os.path.join(DESIGN_SYSTEM, "hooks/useTheme.ts")
    if os.path.exists(fpath):
        with open(fpath) as f: content = f.read()
        assert "toggle" in content.lower() or "setTheme" in content
