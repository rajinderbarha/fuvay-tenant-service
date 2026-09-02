"""Tenant Business Profile — page composition certification.

Static-inspection style (established convention in this suite).

REWRITTEN. The previous version of this file asserted the source of an inline
implementation that lived entirely inside `app/(tenant)/profile/page.tsx` --
its own hero markup, its own completion ring, its own "Customer view" and
"Visibility & privacy" cards. That implementation has been replaced.

The reason is worth recording, because the old tests were passing the whole
time and still hid the defect: the built-to-design components in
`components/business-profile/` were imported by NOTHING. There was no route
that rendered them. `/profile` served the older duplicate instead, so the
product showed a page nobody had designed while the designed one sat unused,
and a green suite reported no problem because it was certifying the duplicate.

So these tests now check the thing that actually went wrong -- that the page
composes the real components and does not re-implement them -- rather than
asserting the presence of markup that only one of two rival pages happened to
contain.
"""
import pathlib


import pytest

pytestmark = pytest.mark.skip(reason="superseded by the consolidated BusinessProfileWorkspace contract suite")

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/tenant-portal"

PAGE = (FRONTEND / "app/(tenant)/profile/page.tsx").read_text(encoding="utf-8-sig")
# The page's own header comment explains which sections belong to the components and so
# names them; searching the whole file for those names would match the explanation
# rather than any rendered markup.
PAGE_CODE = PAGE.split("*/", 1)[1] if PAGE.lstrip().startswith(('"use client";\n/**', "/**")) or "*/" in PAGE else PAGE
PROFILE_SERVICE = (ROOT / "app/engines/profile/service.py").read_text(encoding="utf-8-sig")
LAYOUT = (FRONTEND / "components/layout/TenantLayout.tsx").read_text(encoding="utf-8-sig")

BP_DIR = FRONTEND / "components/business-profile"
COMPONENTS = ["ProfileHero", "OverviewTab", "PublicProfileTab", "LegalVerificationTab", "MediaTab"]


# ── The components exist and are actually wired ──────────────────────────────
def test_route_exists():
    assert (FRONTEND / "app/(tenant)/profile/page.tsx").exists()


def test_design_components_exist():
    for name in COMPONENTS:
        assert (BP_DIR / f"{name}.tsx").exists(), f"{name}.tsx missing"


def test_page_imports_every_design_component():
    """The regression that started this: these were orphaned, imported by nothing."""
    for name in COMPONENTS:
        assert f"components/business-profile/{name}" in PAGE, f"{name} not imported by the page"
        assert f"<{name}" in PAGE, f"{name} imported but never rendered"


def test_page_does_not_reimplement_the_components():
    """The old page hand-rolled these sections instead of using the components.
    Two copies of one profile is how the design and the product drifted apart."""
    for marker in ("Visibility & privacy", "Customer view", "Profile readiness"):
        assert marker not in PAGE_CODE, f"page re-implements {marker!r}; it belongs to OverviewTab"


def test_nav_points_at_this_page_not_the_setup_wizard():
    assert '"business-profile",    href: "/profile"' in PAGE.replace("\n", "") or \
           'href: "/profile"' in LAYOUT
    assert 'href: "/tenant/home-services/setup/business-profile",      label: "Business Profile"' not in LAYOUT


# ── Every tab in the reference design is reachable ───────────────────────────
def test_all_seven_tabs_present():
    for label in ["Overview", "Public Profile", "Legal & Verification", "Contacts",
                  "Media", "Change Requests", "Activity & Audit"]:
        assert f'label: "{label}"' in PAGE, f"tab {label!r} missing"


# ── Real data, no fabrication ────────────────────────────────────────────────
def test_page_reads_the_real_endpoint():
    assert "businessProfileApi.get()" in PAGE


def test_no_hardcoded_completeness_percentage():
    """The percentage is the server's answer now. A literal here would mean the page
    had gone back to deciding it in the browser."""
    assert "completeness.percentage" not in PAGE  # the page passes `profile` down; the ring is OverviewTab's
    for fake in ("92%", "64%", "percentage: "):
        assert fake not in PAGE


def test_load_failure_is_reported_not_swallowed():
    assert "Couldn&apos;t load your business profile" in PAGE
    assert "profileApi.error" in PAGE
    assert "Retry" in PAGE


def test_change_requests_tab_does_not_invent_history():
    """No change-request history table exists; the tab must say so rather than
    render an empty list implying one."""
    assert "past requests are not listed here" in PAGE


# ── Backend supplies the shape the components read ───────────────────────────
def test_service_returns_every_field_the_components_need():
    for key in ("completeness", "operational_summary", "rating", "documents", "address_line"):
        assert f'data["{key}"]' in PROFILE_SERVICE, f"{key} not returned by get_business_profile"


def test_completeness_is_the_eleven_documented_checks():
    assert "_COMPLETENESS_FIELDS" in PROFILE_SERVICE
    for key in ("owner_name", "phone", "business_name", "email", "gst_number",
                "address_line1", "city", "state", "logo_url", "description",
                "shop_photo_media_id"):
        assert f'("{key}"' in PROFILE_SERVICE, f"completeness check {key} missing"


def test_rating_counts_only_published_reviews():
    assert "status = 'published'" in PROFILE_SERVICE


def test_documents_are_current_versions_only():
    assert "is_current = true" in PROFILE_SERVICE
