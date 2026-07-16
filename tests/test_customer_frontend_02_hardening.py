"""CUSTOMER-FRONTEND-02 — Browser E2E + Safety Hardening source-inspection tests.

Follows the same convention as test_customer_frontend_01_scaffold.py: no JS test
runner is configured in frontend/customer-app/package.json (confirmed below), so
these are Python source-inspection assertions over the real customer-app source,
covering the 22 check areas from the CUSTOMER-FRONTEND-02 spec. A subprocess
check runs `npx tsc --noEmit` for the one thing that genuinely needs the real
TypeScript compiler.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "frontend", "customer-app")

# "Withdraw" alone was removed -- it's a substring of two legitimate,
# unrelated, already-shipped features (MODULE-L5-02 "Withdraw complaint",
# MODULE-L5-15 DPDP "Withdraw" a privacy consent), neither of which is
# financial jargon. "Withdrawable Balance" below is the precise phrase that
# actually matters for the wallet/finance-leakage concern this test guards
# against.
FORBIDDEN_LABELS = [
    "Cash Wallet", "Wallet Balance", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow",
    "Platform Collected Service Payment", "Provider Cash Balance",
    "Credit Wallet Health", "Platform Pay Now", "Online Payment Required",
    "Manual Bargain Setup", "Bargain Rule Builder", "Admin Min", "Admin Max",
    "Provider Internal Range", "Internal Score", "Usage Credit Deduction",
    "Commission", "Security Deposit", "Ledger", "Audit Log",
]

SAFETY_FIELDS = [
    "admin_min_price", "admin_max_price", "provider_min_price", "provider_max_price",
    "internal_score", "ranking_score", "bookability_score", "usage_credit_balance",
    "completed_job_deduction", "commission", "security_deposit", "ledger",
    "audit", "excluded_providers", "debug", "source_table",
]

MOCK_PATTERNS = [
    "mockServices", "mockBookings", "mockProviders", "mockPriceOptions",
    "mockTracking", "demoBooking", "fakeProvider",
]


def read(*parts):
    with open(os.path.join(APP, *parts), encoding="utf-8") as f:
        return f.read()


def walk_source():
    for sub in ("app", "lib", "components"):
        base = os.path.join(APP, sub)
        if not os.path.isdir(base):
            continue
        for dirpath, _, files in os.walk(base):
            for f in files:
                if f.endswith((".ts", ".tsx")):
                    path = os.path.join(dirpath, f)
                    yield path, open(path, encoding="utf-8").read()


# 1. Route existence -----------------------------------------------------

def test_all_customer_routes_exist():
    required = [
        ("app", "customer", "home-services", "page.tsx"),
        ("app", "customer", "home-services", "book", "page.tsx"),
        ("app", "customer", "bookings", "page.tsx"),
        ("app", "customer", "bookings", "[bookingId]", "page.tsx"),
        ("app", "customer", "bookings", "[bookingId]", "rate", "page.tsx"),
        ("app", "customer", "profile", "page.tsx"),
        ("app", "login", "page.tsx"),
    ]
    for parts in required:
        assert os.path.exists(os.path.join(APP, *parts)), parts


# 2. No JS test runner configured (confirms Python test convention) -----

def test_no_js_test_runner_configured():
    pkg = read("package.json")
    assert '"next"' in pkg
    assert '"test"' not in pkg


# 3. Forbidden labels -----------------------------------------------------

def test_no_forbidden_labels_anywhere():
    for path, content in walk_source():
        for label in FORBIDDEN_LABELS:
            assert label.lower() not in content.lower(), f"forbidden label '{label}' found in {path}"


# 4. Customer safety — sensitive backend fields never rendered -----------

def test_no_sensitive_fields_rendered():
    # Since customer-app models responses loosely (any/light interfaces), simply
    # confirm none of these field names appear anywhere in source at all.
    for path, content in walk_source():
        for field in SAFETY_FIELDS:
            assert field not in content, f"sensitive field '{field}' referenced in {path}"


# 5. Mock data scan --------------------------------------------------------

def test_no_mock_data_patterns():
    for path, content in walk_source():
        for pattern in MOCK_PATTERNS:
            assert pattern not in content, f"mock pattern '{pattern}' found in {path}"


# 6. No direct fetch() outside lib/api ------------------------------------

def test_no_direct_fetch_outside_lib_api():
    for sub in ("app", "components"):
        base = os.path.join(APP, sub)
        for dirpath, _, files in os.walk(base):
            for f in files:
                if f.endswith(".tsx") or f.endswith(".ts"):
                    content = open(os.path.join(dirpath, f), encoding="utf-8").read()
                    assert "fetch(" not in content, f"{f} calls fetch() directly outside lib/api"


# 7. API contract — required functions exist ------------------------------

def test_api_contract_functions_exist():
    src = read("lib", "api", "customer-home-services.ts")
    for fn in [
        "getCustomerHomeServicesCatalog", "selectProviderForHomeService",
        "createCustomerHomeServiceBooking", "getCustomerBookings",
        "getCustomerBookingDetail", "submitCustomerBookingReview",
        "getCustomerBookingReview",
    ]:
        assert f"export async function {fn}" in src or f"export function {fn}" in src, fn


# 8. Central client used; request_id parsed; 401 handled -----------------

def test_client_has_request_id_parsing_and_401_handling():
    src = read("lib", "api", "client.ts")
    assert "requestId" in src
    assert "res.status === 401" in src
    assert "CustomerApiError" in src


# 9. Provider-before-price gating -----------------------------------------

def test_provider_step_gates_price_step():
    src = read("app", "customer", "home-services", "book", "page.tsx")
    provider_idx = src.index('step === "provider"')
    price_idx = src.index('step === "price"')
    assert provider_idx < price_idx


# 10. Price is not editable (no <input> bound to price) -------------------

def test_price_not_editable():
    src = read("app", "customer", "home-services", "book", "page.tsx")
    price_step_start = src.index("function PriceStep")
    price_step_end = src.index("function ReviewStep")
    price_step_src = src[price_step_start:price_step_end]
    assert "<input" not in price_step_src


# 11. Confirm button gated on provider + price selection ------------------

def test_confirm_button_gated_on_provider_and_price():
    src = read("app", "customer", "home-services", "book", "page.tsx")
    review_step_start = src.index("function ReviewStep")
    review_step_src = src[review_step_start:]
    btn_line = [l for l in review_step_src.splitlines() if "Confirm Booking" in l][0]
    assert "!priceTier" in btn_line
    assert "provider_name" in btn_line or "business_name" in btn_line


# 12. Payment copy present -------------------------------------------------

def test_payment_copy_present():
    found = False
    for path, content in walk_source():
        if "Customer Pays Provider Directly" in content:
            found = True
    assert found


# 13. Review flow gating ----------------------------------------------------

def test_review_gated_on_completed_status():
    src = read("app", "customer", "bookings", "[bookingId]", "rate", "page.tsx")
    assert 'booking.status !== "completed"' in src
    assert "existingReview" in src


# 14. Tracking page does not render internal fields -----------------------

def test_tracking_page_has_no_internal_fields():
    src = read("app", "customer", "bookings", "[bookingId]", "page.tsx")
    for field in ["ledger", "audit", "commission", "excluded_providers"]:
        assert field not in src.lower()


# 15. Responsive — no oversized fixed pixel widths in CSS ------------------

def test_no_oversized_fixed_widths_in_css():
    """Only flag plain `width:`, not `max-width:`/`min-width:` (those are fine —
    they cap or floor, they don't force overflow on a narrow viewport)."""
    css = read("styles", "globals.css")
    widths = re.findall(r"(?<![a-z-])width:\s*(\d+)px", css)
    for w in widths:
        assert int(w) <= 100, f"suspiciously large fixed width {w}px found in globals.css"


def test_bottom_nav_is_fixed_position():
    css = read("styles", "globals.css")
    nav_block_start = css.index(".co-bottom-nav")
    nav_block = css[nav_block_start:nav_block_start + 200]
    assert "position: fixed" in nav_block


# 16. Error banner never shows raw JSON/stack, does show request_id -------

def test_error_banner_uses_request_id_not_raw_json():
    src = read("components", "ErrorBanner.tsx")
    assert "requestId" in src
    assert "JSON.stringify" not in src


# 17. TypeScript compiles cleanly (subprocess) ------------------------------

def test_typescript_compiles_cleanly():
    result = subprocess.run(
        ["npx", "tsc", "--noEmit"],
        cwd=APP, capture_output=True, text=True, shell=(sys.platform == "win32"),
        timeout=180,
    )
    assert result.returncode == 0, f"tsc failed:\n{result.stdout}\n{result.stderr}"
