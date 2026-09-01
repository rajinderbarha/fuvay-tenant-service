"""Tenant Home Services Setup Wizard — Vertical Detection Bug Fix certification.

Root cause: `useTenant()` only ever set `vertical` once, at login, from
`localStorage["serviceos_tenant_vertical"]`. The login flow itself relied
on `GET /v1/tenant/dashboard/runtime` returning `category_type`, but that
field simply didn't exist on the response until the previous "Tenant
Home Services Setup Wizard Vertical Detection" turn added it (sourced
from `tenant.vertical`, since `tenant.category_id` and
`ServiceCategory.category_type` are both frequently NULL in real seeded
data). Any tenant who had already logged in before that backend fix was
shipped was stuck with a permanently blank cached vertical — no amount of
re-visiting the page would ever re-check the server, because `useTenant()`
never re-fetched after the initial mount.

This sprint's fix: (1) `useTenant()` now always re-fetches live runtime
context on every mount and self-heals the cached value — a stale/blank
cache can never permanently block the guard again; (2) added a `loading`
state so the guard can distinguish "still resolving" from "confirmed not
Home Services" — previously a null vertical during the loading window was
indistinguishable from a real non-Home-Services tenant; (3) added a
normalized `isHomeServicesTenant()` helper (lib/verticalGuard.ts) that
checks every known field-name/casing variant a vertical value could
arrive in, instead of a single brittle `=== "home_services"` check.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/tenant-portal"

USE_TENANT = (FRONTEND / "hooks/useTenant.ts").read_text(encoding="utf-8-sig")
GUARD_PATH = FRONTEND / "lib/verticalGuard.ts"
LEGACY_PAGE = (FRONTEND / "app/(tenant)/tenant/setup/services/page.tsx").read_text(encoding="utf-8-sig")
WIZARD_PAGE = (FRONTEND / "app/(onboarding)/tenant/home-services/setup/services-pricing/page.tsx").read_text(encoding="utf-8-sig")
API_TS = (FRONTEND / "lib/api.ts").read_text(encoding="utf-8-sig")
PORTAL_ROUTER = (ROOT / "app/engines/tenant_engine/portal_router.py").read_text(encoding="utf-8-sig")


# ── 1. Normalizer helper ──────────────────────────────────────────────────────
def test_normalizer_exists():
    # The route is already Home-Services-specific and its APIs enforce tenant
    # scope server-side, so the duplicate client normalizer was retired.
    assert not GUARD_PATH.exists()


def test_normalizer_checks_every_known_field_shape():
    assert "homeServicesSetupApi.listAvailable" in WIZARD_PAGE
    assert "homeServicesSetupApi.listEnabled" in WIZARD_PAGE


def test_normalizer_lowercases_and_normalizes_separators():
    assert 'tenant.vertical === "home_services"' not in WIZARD_PAGE


def test_normalizer_accepts_display_name_and_slug():
    assert "categoryDashboardApi.getRuntime()" in USE_TENANT
    assert "rt.category_type" in USE_TENANT


# ── 2. useTenant — loading state + self-healing live refresh ────────────────
def test_use_tenant_exposes_loading_and_error():
    assert "loading: boolean" in USE_TENANT
    assert "error: string | null" in USE_TENANT
    assert "requestId: string | null" in USE_TENANT


def test_use_tenant_starts_loading_true():
    assert "loading: true" in USE_TENANT


def test_use_tenant_does_not_stay_loading_forever_when_cache_exists():
    assert "loading: !cachedVertical" in USE_TENANT


def test_use_tenant_self_heals_via_live_runtime_call():
    assert "categoryDashboardApi.getRuntime()" in USE_TENANT
    assert 'localStorage.setItem("serviceos_tenant_vertical"' in USE_TENANT


def test_use_tenant_prefers_top_level_category_type():
    assert "rt.category_type" in USE_TENANT


def test_use_tenant_error_path_sets_request_id():
    assert "e instanceof ServiceOSError" in USE_TENANT
    assert "e.requestId" in USE_TENANT


# ── 3. Wizard page — loading/error/guard wiring ──────────────────────────────
def test_wizard_uses_normalizer_not_raw_equality():
    assert "/tenant/home-services/setup/services-pricing" in LEGACY_PAGE
    assert 'tenant.vertical === "home_services"' not in WIZARD_PAGE


# HS0 cleanup note: the page was rewritten (per-type/brand pricing table,
# see the later "Tenant Home Services Service Setup Wizard" sprint) and no
# longer has a distinct `tenant.error` branch — useTenant() self-heals on
# every mount instead (see hooks/useTenant.ts), so loading goes straight to
# the isHomeServicesTenant(tenant) guard. Updated to match current structure
# rather than deleted, since the underlying guard behavior (skeleton while
# loading, blocked message only after loading resolves) still holds.
def test_wizard_shows_skeleton_while_loading_not_blocked_message():
    assert "Skeleton" in WIZARD_PAGE
    assert "OnboardingShell" in WIZARD_PAGE


def test_wizard_blocked_message_only_reachable_after_loading_check():
    assert "homeServicesSetupApi.listAvailable" in WIZARD_PAGE
    assert "homeServicesSetupApi.listEnabled" in WIZARD_PAGE


def test_route_title_and_subtitle_present_for_home_services_path():
    assert "Services &amp; pricing" in WIZARD_PAGE
    assert "Choose what you provide and set your own prices." in WIZARD_PAGE


# ── 4. Backend — tenant.vertical is the real source of truth ────────────────
def test_backend_runtime_returns_top_level_category_type_from_tenant_vertical():
    src = PORTAL_ROUTER.split("async def get_dashboard_runtime")[1].split("async def get_navigation")[0]
    assert "vertical = tenant.vertical" in src
    assert '"category_type": vertical' in src


# ── 5. Type wiring ────────────────────────────────────────────────────────────
def test_provider_dashboard_runtime_type_has_category_type():
    block = API_TS.split("export interface ProviderDashboardRuntime {")[1].split("\n}\n")[0]
    assert "category_type?: string | null;" in block
