"""
Sprint 34B — White Gradient Design System tests.
Verifies token files, CSS variable correctness, component fixes,
and that old warm/earthy palette is removed from touched files.
"""
import os
import re

ROOT      = os.path.dirname(os.path.dirname(__file__))
SA_CSS    = os.path.join(ROOT, "frontend", "super-admin",  "styles", "globals.css")
TP_CSS    = os.path.join(ROOT, "frontend", "tenant-portal","styles", "globals.css")
SA_LIB    = os.path.join(ROOT, "frontend", "super-admin",  "lib")
TP_LIB    = os.path.join(ROOT, "frontend", "tenant-portal","lib")
SA_UI     = os.path.join(ROOT, "frontend", "super-admin",  "components", "shared", "ui.tsx")
TP_UI     = os.path.join(ROOT, "frontend", "tenant-portal","components", "shared", "ui.tsx")
SA_LAY    = os.path.join(ROOT, "frontend", "super-admin",  "components", "layout", "AdminLayout.tsx")
TP_LAY    = os.path.join(ROOT, "frontend", "tenant-portal","components", "layout", "TenantLayout.tsx")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Phase 3: Light theme tokens ───────────────────────────────────────────────

def test_light_theme_bg_is_white_sa():
    src = _read(SA_CSS)
    # Light bg must be pure white
    assert "--bg:" in src and "#FFFFFF" in src

def test_light_theme_bg_is_white_tp():
    src = _read(TP_CSS)
    assert "--bg:" in src and "#FFFFFF" in src

def test_light_theme_has_bg_gradient_sa():
    src = _read(SA_CSS)
    assert "--bg-gradient:" in src

def test_light_theme_has_bg_gradient_tp():
    src = _read(TP_CSS)
    assert "--bg-gradient:" in src

def test_light_theme_has_primary_gradient_sa():
    src = _read(SA_CSS)
    assert "--primary-gradient:" in src

def test_light_theme_has_primary_gradient_tp():
    src = _read(TP_CSS)
    assert "--primary-gradient:" in src

def test_light_surface_sunken_is_clean_white_gray_sa():
    src = _read(SA_CSS)
    # Old cream value #F6EECD must be gone
    assert "#F6EECD" not in src

def test_light_surface_sunken_is_clean_white_gray_tp():
    src = _read(TP_CSS)
    assert "#F6EECD" not in src

def test_old_warm_bg_removed_sa():
    src = _read(SA_CSS)
    # Old warm cream background must be gone
    assert "#FAF8F2" not in src

def test_old_warm_bg_removed_tp():
    src = _read(TP_CSS)
    assert "#FAF8F2" not in src

def test_old_cream_border_removed_sa():
    src = _read(SA_CSS)
    assert "#EDE5C8" not in src

def test_old_cream_border_removed_tp():
    src = _read(TP_CSS)
    assert "#EDE5C8" not in src

def test_light_border_is_clean_blue_gray_sa():
    src = _read(SA_CSS)
    assert "--border:" in src and "#E2E8F0" in src

def test_light_border_is_clean_blue_gray_tp():
    src = _read(TP_CSS)
    assert "--border:" in src and "#E2E8F0" in src

def test_light_text_primary_is_navy_sa():
    src = _read(SA_CSS)
    assert "--text-primary:" in src and "#0F172A" in src

def test_light_text_primary_is_navy_tp():
    src = _read(TP_CSS)
    assert "--text-primary:" in src and "#0F172A" in src

def test_old_warm_text_removed_sa():
    src = _read(SA_CSS)
    # Old warm near-black text color
    assert "#1A1A18" not in src

def test_old_warm_text_removed_tp():
    src = _read(TP_CSS)
    assert "#1A1A18" not in src

def test_light_brand_is_blue_sa():
    src = _read(SA_CSS)
    assert "--brand:" in src and "#2563EB" in src

def test_light_brand_is_blue_tp():
    src = _read(TP_CSS)
    assert "--brand:" in src and "#2563EB" in src

def test_old_teal_brand_removed_sa():
    src = _read(SA_CSS)
    # Old teal brand color
    assert "#3F756C" not in src

def test_old_teal_brand_removed_tp():
    src = _read(TP_CSS)
    assert "#3F756C" not in src

def test_light_info_is_blue_not_teal_sa():
    src = _read(SA_CSS)
    # Info section must use blue
    info_match = re.search(r'--info:\s+([^;]+);', src)
    assert info_match and "2563EB" in info_match.group(1)

def test_light_info_is_blue_not_teal_tp():
    src = _read(TP_CSS)
    info_match = re.search(r'--info:\s+([^;]+);', src)
    assert info_match and "2563EB" in info_match.group(1)

# ── Phase 4: Dark theme tokens ────────────────────────────────────────────────

def test_dark_bg_is_charcoal_not_pure_black_sa():
    src = _read(SA_CSS)
    # Dark bg should be charcoal #111827, not pure black #000000 or near-black #111110
    assert "#111110" not in src

def test_dark_bg_is_charcoal_not_pure_black_tp():
    src = _read(TP_CSS)
    assert "#111110" not in src

def test_dark_theme_has_charcoal_bg_sa():
    # Check the dark section specifically
    src = _read(SA_CSS)
    dark_section = src[src.index("[data-theme=\"dark\"]"):]
    assert "#111827" in dark_section

def test_dark_theme_has_charcoal_bg_tp():
    src = _read(TP_CSS)
    dark_section = src[src.index("[data-theme=\"dark\"]"):]
    assert "#111827" in dark_section

def test_dark_sidebar_is_navy_sa():
    src = _read(SA_CSS)
    dark_section = src[src.index("[data-theme=\"dark\"]"):]
    assert "--sidebar-bg:" in dark_section and "#0F172A" in dark_section

def test_sidebar_is_navy_in_light_mode_sa():
    src = _read(SA_CSS)
    light_section = src[:src.index("[data-theme=\"dark\"]")]
    assert "--sidebar-bg:" in light_section and "#0F172A" in light_section

def test_old_teal_sidebar_removed_sa():
    src = _read(SA_CSS)
    # Old teal sidebar bg
    assert "#3F756C" not in src

def test_old_teal_sidebar_removed_tp():
    src = _read(TP_CSS)
    assert "#2D5951" not in src

# ── Phase 5: Shadow/radius/spacing/typography tokens (design-tokens.ts) ──────

def test_design_tokens_file_exists_sa():
    assert os.path.exists(os.path.join(SA_LIB, "design-tokens.ts"))

def test_design_tokens_file_exists_tp():
    assert os.path.exists(os.path.join(TP_LIB, "design-tokens.ts"))

def test_design_tokens_exports_radius():
    src = _read(os.path.join(SA_LIB, "design-tokens.ts"))
    assert "export const radius" in src

def test_design_tokens_exports_shadows():
    src = _read(os.path.join(SA_LIB, "design-tokens.ts"))
    assert "export const shadows" in src

def test_design_tokens_exports_spacing():
    src = _read(os.path.join(SA_LIB, "design-tokens.ts"))
    assert "export const spacing" in src

def test_design_tokens_exports_typography():
    src = _read(os.path.join(SA_LIB, "design-tokens.ts"))
    assert "export const typography" in src

def test_design_tokens_exports_component_tokens():
    src = _read(os.path.join(SA_LIB, "design-tokens.ts"))
    assert "export const componentTokens" in src or "componentTokens" in src

def test_design_tokens_exports_status_styles():
    src = _read(os.path.join(SA_LIB, "design-tokens.ts"))
    assert "statusStyles" in src

def test_design_tokens_exports_get_status_style():
    src = _read(os.path.join(SA_LIB, "design-tokens.ts"))
    assert "getStatusStyle" in src

def test_design_tokens_exports_chart_colors():
    src = _read(os.path.join(SA_LIB, "design-tokens.ts"))
    assert "chartColors" in src

def test_design_tokens_no_old_teal():
    src = _read(os.path.join(SA_LIB, "design-tokens.ts"))
    assert "#3F756C" not in src

def test_design_tokens_uses_css_vars():
    src = _read(os.path.join(SA_LIB, "design-tokens.ts"))
    assert "var(--" in src

# ── Phase 8/9: Btn component uses tokens not hardcoded hex ───────────────────

def test_btn_no_hardcoded_danger_hover_sa():
    src = _read(SA_UI)
    assert "#fee2e2" not in src

def test_btn_no_hardcoded_danger_hover_tp():
    src = _read(TP_UI)
    assert "#fee2e2" not in src

def test_btn_no_hardcoded_success_hover_sa():
    src = _read(SA_UI)
    assert "#dcfce7" not in src

def test_btn_no_hardcoded_success_hover_tp():
    src = _read(TP_UI)
    assert "#dcfce7" not in src

def test_btn_no_hardcoded_warning_hover_sa():
    src = _read(SA_UI)
    assert "#fef3c7" not in src

def test_btn_no_hardcoded_warning_hover_tp():
    src = _read(TP_UI)
    assert "#fef3c7" not in src

def test_btn_primary_uses_gradient_sa():
    src = _read(SA_UI)
    assert "primary-gradient" in src

def test_btn_primary_uses_gradient_tp():
    src = _read(TP_UI)
    assert "primary-gradient" in src

def test_btn_primary_has_shadow_on_hover_sa():
    src = _read(SA_UI)
    # Primary btn should have shadow for depth
    assert "shadow-md" in src or "shadow-sm" in src

# ── Phase 7: Layout background gradient ──────────────────────────────────────

def test_admin_layout_main_uses_gradient():
    src = _read(SA_LAY)
    assert "bg-gradient" in src

def test_tenant_layout_main_uses_gradient():
    src = _read(TP_LAY)
    assert "bg-gradient" in src

def test_admin_layout_outer_bg_uses_token():
    src = _read(SA_LAY)
    # Should not have old hardcoded --bg without fallback
    assert "var(--bg" in src

# ── Phase 13: Sidebar styling ─────────────────────────────────────────────────

def test_admin_layout_sidebar_uses_sidebar_bg_token():
    src = _read(SA_LAY)
    assert "var(--sidebar-bg)" in src

def test_tenant_layout_sidebar_uses_sidebar_bg_token():
    src = _read(TP_LAY)
    assert "var(--sidebar-bg)" in src

def test_admin_layout_no_teal_sidebar():
    src = _read(SA_LAY)
    # Old teal sidebar bg — the color should no longer be hardcoded in layout
    assert "#3F756C" not in src

def test_tenant_layout_no_teal_sidebar():
    src = _read(TP_LAY)
    assert "#2D5951" not in src

# ── Phase 14: Status system tokens ──────────────────────────────────────────

def test_status_labels_still_exists_sa():
    assert os.path.exists(os.path.join(SA_LIB, "status-labels.ts"))

def test_status_labels_still_exists_tp():
    assert os.path.exists(os.path.join(TP_LIB, "status-labels.ts"))

def test_design_tokens_has_force_password_change_status():
    src = _read(os.path.join(SA_LIB, "design-tokens.ts"))
    assert "force_password_change" in src

def test_design_tokens_has_pending_activation_status():
    src = _read(os.path.join(SA_LIB, "design-tokens.ts"))
    assert "pending_activation" in src

# ── Phase 19: No regression — old palette not in shared components ────────────

def test_ui_no_old_teal_sa():
    src = _read(SA_UI)
    assert "#3F756C" not in src

def test_ui_no_old_teal_tp():
    src = _read(TP_UI)
    assert "#3F756C" not in src

def test_ui_no_old_cream_sa():
    src = _read(SA_UI)
    assert "#FAF8F2" not in src and "#F6EECD" not in src and "#EDE5C8" not in src

def test_ui_no_old_cream_tp():
    src = _read(TP_UI)
    assert "#FAF8F2" not in src and "#F6EECD" not in src and "#EDE5C8" not in src

def test_layout_tsx_no_classname_sa():
    from tests.test_sprint34a_ui_foundation import _read as read34
    src = read34(os.path.join(ROOT, "frontend", "super-admin", "components", "shared", "layout.tsx"))
    assert "className=" not in src

def test_no_tailwind_in_ui_tsx_sa():
    src = _read(SA_UI)
    # className is allowed for our own CSS classes (e.g. "skeleton", "animate-*")
    # but not for Tailwind utility classes like "flex", "text-sm", "bg-blue-500"
    tailwind_pattern = re.compile(r'className="[^"]*(?:flex|grid|text-(?:sm|lg|xl|2xl)|bg-(?:blue|red|green|gray)|p-\d|m-\d|rounded-)[^"]*"')
    assert not tailwind_pattern.search(src)

def test_no_tailwind_in_ui_tsx_tp():
    src = _read(TP_UI)
    tailwind_pattern = re.compile(r'className="[^"]*(?:flex|grid|text-(?:sm|lg|xl|2xl)|bg-(?:blue|red|green|gray)|p-\d|m-\d|rounded-)[^"]*"')
    assert not tailwind_pattern.search(src)
