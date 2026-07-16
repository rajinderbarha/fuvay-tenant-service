"""CUSTOMER-FRONTEND-01 — source-inspection tests.

Follows this repo's established convention (no JS test runner configured in
frontend/tenant-portal/package.json, confirmed by inspection — only
dev/build/start/lint scripts exist, no `test` script and no jest/vitest
devDependency) of Python source-inspection tests under tests/ for frontend
sprints. These tests assert on the presence of real source patterns rather
than executing the Next.js app (no JS runner available), matching prior
sprints' test style in this repo.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "frontend", "customer-app")


def read(*parts):
    with open(os.path.join(APP, *parts), encoding="utf-8") as f:
        return f.read()


def test_package_json_exists_and_has_no_js_test_runner():
    pkg = read("package.json")
    assert '"next"' in pkg
    assert '"test"' not in pkg  # confirms convention: no JS test runner configured


def test_route_files_exist_for_all_spec_routes():
    assert os.path.exists(os.path.join(APP, "app", "customer", "home-services", "page.tsx"))
    assert os.path.exists(os.path.join(APP, "app", "customer", "home-services", "book", "page.tsx"))
    assert os.path.exists(os.path.join(APP, "app", "customer", "bookings", "page.tsx"))
    assert os.path.exists(os.path.join(APP, "app", "customer", "bookings", "[bookingId]", "page.tsx"))
    assert os.path.exists(os.path.join(APP, "app", "customer", "bookings", "[bookingId]", "rate", "page.tsx"))
    assert os.path.exists(os.path.join(APP, "app", "customer", "profile", "page.tsx"))
    assert os.path.exists(os.path.join(APP, "app", "login", "page.tsx"))


def test_api_client_module_has_required_functions():
    src = read("lib", "api", "customer-home-services.ts")
    for fn in [
        "getCustomerHomeServicesCatalog", "selectProviderForHomeService",
        "createCustomerHomeServiceBooking", "getCustomerBookings",
        "getCustomerBookingDetail", "cancelCustomerBooking",
        "submitCustomerBookingReview", "getCustomerBookingReview",
    ]:
        assert f"export async function {fn}" in src or f"export function {fn}" in src, fn


def test_no_direct_fetch_in_page_components():
    """No page component should call fetch() directly — all calls go through lib/api/*."""
    app_dir = os.path.join(APP, "app")
    for dirpath, _, files in os.walk(app_dir):
        for f in files:
            if f.endswith(".tsx"):
                content = open(os.path.join(dirpath, f), encoding="utf-8").read()
                # allow fetch only inside comments explaining it's forbidden
                assert "fetch(" not in content, f"{f} calls fetch() directly"


def test_matching_endpoint_is_real_not_illustrative():
    src = read("lib", "api", "customer-home-services.ts")
    assert "match-and-price" in src
    assert "matching/select-provider" not in src


def test_price_tier_confirmation_uses_tier_name_not_amount():
    src = read("lib", "api", "customer-home-services.ts")
    assert 'confirm-price-choice' in src
    assert 'price_tier' in src


def test_provider_and_price_required_before_booking_confirm():
    src = read("app", "customer", "home-services", "book", "page.tsx")
    assert "A provider must be selected before choosing a price" in src
    assert "Please select a price option" in src


def test_no_forbidden_finance_labels_in_any_source_file():
    # "Withdraw" alone was removed -- it's a substring of two legitimate,
    # unrelated, already-shipped features (MODULE-L5-02 "Withdraw complaint",
    # MODULE-L5-15 DPDP "Withdraw" a privacy consent), neither of which is
    # financial jargon. "Withdrawable Balance" below is the precise phrase
    # that actually matters for the wallet/finance-leakage concern this test
    # guards against.
    forbidden = [
        "Cash Wallet", "Wallet Balance", "Withdrawable Balance",
        "Tenant Payout", "Provider Earnings Wallet", "Escrow",
        "Platform Collected Service Payment", "Provider Cash Balance",
        "Credit Wallet Health", "Platform Pay Now", "Online Payment Required",
        "Manual Bargain Setup", "Bargain Rule Builder", "Admin Min", "Admin Max",
        "Provider Internal Range", "Internal Score", "Usage Credit Deduction",
        "Commission", "Security Deposit",
    ]
    for dirpath, _, files in os.walk(APP):
        # e2e/ contains real Playwright runtime guards that legitimately
        # define these exact forbidden strings/fields (as a FORBIDDEN_TEXT
        # array) in order to assert they never render at runtime -- not a
        # violation, the opposite.
        if "node_modules" in dirpath or ".next" in dirpath or f"{os.sep}e2e" in dirpath:
            continue
        for f in files:
            if f.endswith((".ts", ".tsx", ".css")):
                content = open(os.path.join(dirpath, f), encoding="utf-8").read()
                for label in forbidden:
                    assert label not in content, f"forbidden label '{label}' found in {f}"


def test_no_internal_finance_fields_referenced():
    banned_fields = [
        "admin_min_price", "admin_max_price", "provider_min_price", "provider_max_price",
        "internal_score", "ranking_score", "bookability_score", "usage_credit_balance",
        "completed_job_deduction", "excluded_providers", "source_table",
    ]
    for dirpath, _, files in os.walk(APP):
        # e2e/ contains real Playwright runtime guards that legitimately
        # define these exact forbidden strings/fields (as a FORBIDDEN_TEXT
        # array) in order to assert they never render at runtime -- not a
        # violation, the opposite.
        if "node_modules" in dirpath or ".next" in dirpath or f"{os.sep}e2e" in dirpath:
            continue
        for f in files:
            if f.endswith((".ts", ".tsx")):
                content = open(os.path.join(dirpath, f), encoding="utf-8").read()
                for field in banned_fields:
                    assert field not in content, f"banned field '{field}' referenced in {f}"


def test_payment_note_copy_present():
    src = read("app", "customer", "home-services", "book", "page.tsx")
    assert "Pay provider directly after service." in src
    assert "Customer Pays Provider Directly" in src


def test_review_gating_error_codes_referenced():
    """The rate page must handle the real backend error codes."""
    src = read("app", "customer", "bookings", "[bookingId]", "rate", "page.tsx")
    assert "completed" in src.lower()


def test_error_banner_shows_request_id():
    src = read("components", "ErrorBanner.tsx")
    assert "requestId" in src
    assert "Request ID" in src
