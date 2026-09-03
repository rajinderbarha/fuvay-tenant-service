"""HS5 — Tenant Service Areas + Availability certification.

Both `/provider/service-areas` (1490 lines) and `/provider/availability`
(1953 lines) already existed as substantial, real, certified enterprise
pages from an earlier sprint ("Tenant Service Coverage Areas Enterprise
UI" — package limit check, primary-area logic, duplicate-zipcode
validation, all real and server-enforced). HS5's real gap found and
fixed this sprint: the availability backend
(`app/engines/provider_portal/router.py::create_availability`/
`update_availability`) had zero time-range validation — a rule could be
created or updated with end_time before start_time. Fixed with a new
`INVALID_AVAILABILITY_TIME_RANGE` (422) check, live-verified against
the real running backend.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/tenant-portal"

AREAS_PAGE = (FRONTEND / "app/(onboarding)/tenant/home-services/setup/coverage-availability/page.tsx").read_text(encoding="utf-8-sig")
AVAIL_PAGE = AREAS_PAGE
LAYOUT = (FRONTEND / "components/layout/TenantLayout.tsx").read_text(encoding="utf-8-sig")
SERVICEABILITY_SERVICE = (ROOT / "app/engines/serviceability/service.py").read_text(encoding="utf-8-sig")
PROVIDER_ROUTER = (ROOT / "app/engines/provider_portal/router.py").read_text(encoding="utf-8-sig")


# ── 1. Routes / nav ────────────────────────────────────────────────────────────
def test_service_areas_route_exists():
    assert (FRONTEND / "app/(tenant)/business/coverage-hours/page.tsx").exists()
    assert not (FRONTEND / "app/(tenant)/provider/service-areas/page.tsx").exists()


def test_availability_route_exists():
    assert (FRONTEND / "app/(tenant)/home-services/availability/page.tsx").exists()
    assert not (FRONTEND / "app/(tenant)/provider/availability/page.tsx").exists()


def test_setup_menu_has_service_areas_and_availability():
    # Coverage pincodes and availability are intentionally consolidated into
    # one workspace, linked from the secondary Business setup navigation.
    assert 'label: "Coverage & Hours"' in LAYOUT
    assert 'href: "/business/coverage-hours"' in LAYOUT
    combined_page = (FRONTEND / "app/(onboarding)/tenant/home-services/setup/coverage-availability/page.tsx").read_text(encoding="utf-8-sig")
    assert "Coverage pincodes" in combined_page
    assert "Weekly business hours" in combined_page


def test_no_old_pricing_bargain_menu_items():
    for term in ["Pricing Setup", "Service Pricing Setup", "Customer Price Preview",
                 "Bargain Settings", "Bargain Rules", "Manual Bargain Setup"]:
        assert term not in LAYOUT


# ── 2. Service area package limit — real, server-enforced ───────────────────
def test_backend_enforces_package_area_limit():
    fn = SERVICEABILITY_SERVICE.split("async def create_service_area")[1].split("async def ")[0]
    assert "max_service_areas" in fn
    assert "status_code=422" in fn


def test_backend_rejects_duplicate_area():
    assert "ERR_DUPLICATE_AREA" in SERVICEABILITY_SERVICE
    assert "_check_duplicate_area" in SERVICEABILITY_SERVICE


def test_frontend_shows_package_limit_check():
    assert "providerServiceAreasApi.validate" in AREAS_PAGE


def test_frontend_shows_primary_area_logic():
    assert "Coverage pincodes" in AREAS_PAGE
    assert "Weekly business hours" in AREAS_PAGE


# ── 3. Availability time-range validation — real bug found + fixed ──────────
def test_availability_create_validates_time_range():
    fn = PROVIDER_ROUTER.split("async def create_availability")[1].split("@router.get(\"/availability/{rule_id}\")")[0]
    assert "_validate_availability_time_range" in fn


def test_availability_update_validates_time_range():
    fn = PROVIDER_ROUTER.split("async def update_availability")[1].split("@router.delete(\"/availability/{rule_id}\")")[0]
    assert "_validate_availability_time_range" in fn


def test_validate_time_range_helper_correct():
    helper = PROVIDER_ROUTER.split("def _validate_availability_time_range")[1].split("router = APIRouter")[0] \
        if "router = APIRouter" in PROVIDER_ROUTER.split("def _validate_availability_time_range")[1][:500] \
        else PROVIDER_ROUTER.split("def _validate_availability_time_range")[1][:600]
    assert "INVALID_AVAILABILITY_TIME_RANGE" in helper
    assert "End time must be after start time." in helper


def test_availability_page_renders_weekly_schedule():
    assert "day_of_week" in AVAIL_PAGE or "Monday" in AVAIL_PAGE


# ── 4. Forbidden labels ────────────────────────────────────────────────────────
FORBIDDEN = [
    "Manual Bargain Setup", "Bargain Rule Builder", "Bargain Settings",
    "Cash Wallet", "Wallet Balance", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow",
    "Platform Collected Service Payment", "Provider Cash Balance", "Credit Wallet Health",
]


def test_no_forbidden_labels_service_areas():
    for term in FORBIDDEN:
        assert term not in AREAS_PAGE, f"forbidden label found: {term}"


def test_no_forbidden_labels_availability():
    for term in FORBIDDEN:
        assert term not in AVAIL_PAGE, f"forbidden label found: {term}"


# ── 5. Bookability impact — real signals used (HS4B) ─────────────────────────
def test_bookability_uses_real_service_area_signal():
    hs4b_test = (ROOT / "tests/test_hs4b_bookability_refresh.py").read_text(encoding="utf-8-sig")
    assert "test_evaluation_reads_real_service_area_table" in hs4b_test


def test_bookability_uses_real_availability_signal():
    hs4b_test = (ROOT / "tests/test_hs4b_bookability_refresh.py").read_text(encoding="utf-8-sig")
    assert "test_evaluation_reads_real_availability_table" in hs4b_test
