"""HS6B (completion pass) — closes the remaining gaps from the first
HS6B pass: break/holiday/booking-window integration into the real
matching eligibility gate, per-candidate exclusion reason codes, and
admin diagnostics exposure of canonical sources + excluded providers.

Live-verified this pass against the real database (temporarily setting
tenants.status='active' for the real dev tenant, restored after):
- Holiday-blocked request -> excluded_providers: [{'reason_code':
  'BLOCKED_BY_HOLIDAY'}]
- Break-blocked request -> excluded_providers: [{'reason_code':
  'BLOCKED_BY_BREAK'}]
- Valid time -> 0 exclusions, provider selected.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MATCHING_ENGINE = (ROOT / "app/engines/home_service_booking/matching_engine.py").read_text(encoding="utf-8-sig")
AUTO_PRICE_ROUTER = (ROOT / "app/engines/admin_catalog/auto_price_options_router.py").read_text(encoding="utf-8-sig")
DIAGNOSTICS_PAGE = (ROOT / "frontend/super-admin/app/admin/home-services/matching-diagnostics/page.tsx").read_text(encoding="utf-8-sig")
API_TS = (ROOT / "frontend/super-admin/lib/api.ts").read_text(encoding="utf-8-sig")


# ── 1. Eligibility gate returns reason codes, not just bool ──────────────────
def test_eligibility_gate_returns_reason_code():
    sig = MATCHING_ENGINE.split("async def _passes_full_eligibility_gate(")[1][:400]
    assert "tuple[bool, str | None]" in sig


def test_gate_reuses_hs5b_matching_inputs_for_time_checks():
    fn = MATCHING_ENGINE.split("async def _passes_full_eligibility_gate")[1]
    assert "get_tenant_home_services_matching_inputs" in fn
    assert "from app.engines.provider_portal.router import" in fn


def test_gate_checks_break_holiday_booking_window():
    fn = MATCHING_ENGINE.split("async def _passes_full_eligibility_gate")[1]
    assert '"BLOCKED_BY_BREAK"' in fn
    assert '"BLOCKED_BY_HOLIDAY"' in fn
    assert '"OUTSIDE_BOOKING_WINDOW"' in fn


def test_gate_does_not_reimplement_time_logic():
    # The gate must call the shared HS5B function, not duplicate its
    # break/exception SQL inline.
    fn = MATCHING_ENGINE.split("async def _passes_full_eligibility_gate")[1]
    assert "break_start_time" not in fn
    assert "tenant_availability_exceptions" not in fn


# ── 2. select_best_provider surfaces per-candidate exclusion reasons ────────
def test_select_best_provider_accepts_requested_at():
    sig = MATCHING_ENGINE.split("async def select_best_provider(")[1][:600]
    assert "requested_at: str | None = None" in sig


def test_select_best_provider_returns_excluded_providers():
    fn = MATCHING_ENGINE.split("async def select_best_provider(")[1].split("async def _passes_full_eligibility_gate")[0]
    assert '"excluded_providers"' in fn
    assert "reason_code" in fn


# ── 3. Admin diagnostics router surfaces canonical sources ───────────────────
def test_diagnostics_router_exposes_canonical_sources():
    assert '"bookability_source": "canonical_provider_status"' in AUTO_PRICE_ROUTER
    assert '"area_coverage_source": "normalized_service_area_coverage"' in AUTO_PRICE_ROUTER


def test_diagnostics_router_accepts_requested_at():
    fn = AUTO_PRICE_ROUTER.split("requested_at = body.get")[0][-200:]
    assert "requested_at" in AUTO_PRICE_ROUTER


def test_diagnostics_router_returns_excluded_providers():
    assert '"excluded_providers": match.get("excluded_providers", [])' in AUTO_PRICE_ROUTER


# ── 4. Admin diagnostics UI shows the new panels ──────────────────────────────
def test_diagnostics_page_shows_canonical_sources_panel():
    assert "Canonical Sources" in DIAGNOSTICS_PAGE
    assert "Bookability Source:" in DIAGNOSTICS_PAGE
    assert "Area Coverage Source:" in DIAGNOSTICS_PAGE


def test_diagnostics_page_shows_excluded_providers_with_reasons():
    assert "Excluded Providers" in DIAGNOSTICS_PAGE
    assert "ep.reason_code" in DIAGNOSTICS_PAGE


def test_api_type_includes_new_fields():
    interface_block = API_TS.split("export interface MatchingDiagnosticsResult")[1].split("export const autoPriceOptionsApi")[0]
    assert "excluded_providers" in interface_block
    assert "bookability_source" in interface_block
    assert "area_coverage_source" in interface_block


# ── 5. Forbidden labels ────────────────────────────────────────────────────────
FORBIDDEN = [
    "Manual Bargain Setup", "Bargain Rule Builder", "Bargain Settings",
    "Cash Wallet", "Wallet Balance", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow",
    "Platform Collected Service Payment", "Provider Cash Balance", "Credit Wallet Health",
]


def test_no_forbidden_labels():
    for term in FORBIDDEN:
        assert term not in DIAGNOSTICS_PAGE, f"forbidden label found: {term}"
        assert term not in MATCHING_ENGINE, f"forbidden label found: {term}"
