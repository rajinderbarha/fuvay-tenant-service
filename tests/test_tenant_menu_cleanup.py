"""
TENANT MENU CLEANUP — Tests
Verifies that old pricing/bargain setup items are removed and
the correct Setup menu is in place.
"""
import re
import pathlib

ROOT = pathlib.Path(__file__).parent.parent

TENANT_LAYOUT = ROOT / "frontend/tenant-portal/components/layout/TenantLayout.tsx"
NAV_CONFIG = ROOT / "frontend/tenant-portal/lib/nav-config.ts"
PROVIDER_PRICING = ROOT / "frontend/tenant-portal/app/(tenant)/provider/pricing/page.tsx"
CUSTOMER_PRICE_PREVIEW = ROOT / "frontend/tenant-portal/app/(tenant)/provider/customer-price-preview/page.tsx"
TENANT_SETUP_SERVICES = ROOT / "frontend/tenant-portal/app/(tenant)/tenant/setup/services/page.tsx"
SERVICE_SETUP = ROOT / "frontend/tenant-portal/app/(tenant)/provider/service-setup/page.tsx"


def read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


# ── 1. Setup menu renders ─────────────────────────────────────────────────────
def test_setup_group_present_in_tenant_layout():
    src = read(TENANT_LAYOUT)
    assert 'label: "Setup"' in src


# ── 2. Setup Checklist appears ────────────────────────────────────────────────
def test_setup_checklist_in_nav():
    src = read(TENANT_LAYOUT)
    assert "Setup Checklist" in src


# ── 3. Business Profile appears ───────────────────────────────────────────────
def test_business_profile_in_nav():
    src = read(TENANT_LAYOUT)
    assert "Business Profile" in src


# ── 4. Service Areas appears ──────────────────────────────────────────────────
def test_service_areas_in_setup_group():
    src = read(TENANT_LAYOUT)
    # Service Areas must be inside the Setup group block
    setup_block = re.search(r'label: "Setup".*?label: "Team"', src, re.DOTALL)
    assert setup_block, "Setup group not found"
    assert "Service Areas" in setup_block.group()


# ── 5. Service Setup appears ──────────────────────────────────────────────────
def test_service_setup_in_nav():
    src = read(TENANT_LAYOUT)
    assert "Service Setup" in src


# ── 6. Availability appears ───────────────────────────────────────────────────
def test_availability_in_nav():
    # Externally renamed since this test was written: "Availability" ->
    # "Business Hours" (same feature, new label, route moved to
    # /tenant/setup/availability).
    src = read(TENANT_LAYOUT)
    assert "Business Hours" in src


# ── 7. Service Pricing Setup does not appear ──────────────────────────────────
def test_service_pricing_setup_not_in_nav():
    src = read(TENANT_LAYOUT)
    assert "Service Pricing Setup" not in src


# ── 8. Pricing Setup does not appear ─────────────────────────────────────────
def test_pricing_setup_not_in_nav():
    src = read(TENANT_LAYOUT)
    # "Pricing Setup" must not appear in the nav items
    assert '"Pricing Setup"' not in src


# ── 9. Customer Price Preview not in nav ──────────────────────────────────────
def test_customer_price_preview_not_in_nav():
    src = read(TENANT_LAYOUT)
    assert "Customer Price Preview" not in src


# ── 10. Bargain Settings not in nav ───────────────────────────────────────────
def test_bargain_settings_not_in_nav():
    src = read(TENANT_LAYOUT)
    assert "Bargain Settings" not in src


# ── 11. Bargain Rules not in nav ──────────────────────────────────────────────
def test_bargain_rules_not_in_nav():
    src = read(TENANT_LAYOUT)
    assert "Bargain Rules" not in src


# ── 12. Manual Bargain Setup not in nav ──────────────────────────────────────
def test_manual_bargain_setup_not_in_nav():
    src = read(TENANT_LAYOUT)
    assert "Manual Bargain Setup" not in src


# ── 13. Old pricing route shows deprecated message / redirect ────────────────
# NOTE (HS0 cleanup): the canonical Service Setup page was moved from
# /provider/service-setup to /tenant/setup/services in the later "Tenant Home
# Services Service Setup Wizard" sprint. These assertions originally pointed
# at /provider/service-setup as the redirect target because that was
# canonical when this test was written; that page is now itself deprecated
# (see SERVICE_SETUP tests below). Updated to point at the current canonical
# route rather than deleting the test.
def test_old_pricing_route_shows_deprecated_message():
    src = read(PROVIDER_PRICING)
    assert "has moved" in src or "deprecated" in src.lower() or "moved" in src.lower()
    assert "/tenant/setup/services" in src


def test_old_pricing_route_has_cta():
    src = read(PROVIDER_PRICING)
    assert "Go to Service Setup" in src or "setup/services" in src


# ── 14. Old customer-price-preview route shows deprecated message ─────────────
def test_customer_price_preview_route_shows_deprecated_message():
    src = read(CUSTOMER_PRICE_PREVIEW)
    assert "moved" in src.lower()
    assert "/tenant/setup/services" in src


def test_old_service_setup_route_shows_deprecated_message():
    # /provider/service-setup is the superseded duplicate; it must point
    # forward to the canonical /tenant/setup/services wizard.
    src = read(SERVICE_SETUP)
    assert "has moved" in src or "moved" in src.lower()
    assert "/tenant/setup/services" in src


# ── 15. Canonical Service Setup wizard contains provider price range step ────
def test_service_setup_has_provider_price_range():
    src = read(TENANT_SETUP_SERVICES)
    assert "tenantMinPrice" in src or "tenant_min_price" in src or "providerMinPrice" in src or "provider_min_price" in src
    assert "tenantMaxPrice" in src or "tenant_max_price" in src or "providerMaxPrice" in src or "provider_max_price" in src


# ── 16. Canonical Service Setup wizard contains Low/Mid/High preview ────────
def test_service_setup_has_low_mid_high_preview():
    src = read(TENANT_SETUP_SERVICES)
    assert "Low" in src and "Mid" in src and "High" in src


# ── 17. No forbidden wallet/payout labels ────────────────────────────────────
FORBIDDEN_LABELS = [
    "Wallet Balance", "Cash Wallet", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow", "Provider Cash Balance",
]

def test_no_forbidden_labels_in_tenant_layout():
    src = read(TENANT_LAYOUT)
    for label in FORBIDDEN_LABELS:
        assert label not in src, f"Forbidden label found in TenantLayout: {label!r}"


def test_no_forbidden_labels_in_nav_config():
    src = read(NAV_CONFIG)
    for label in FORBIDDEN_LABELS:
        assert label not in src, f"Forbidden label found in nav-config: {label!r}"


def test_no_forbidden_labels_in_service_setup():
    src = read(SERVICE_SETUP)
    for label in FORBIDDEN_LABELS:
        assert label not in src, f"Forbidden label found in service-setup: {label!r}"


# ── 18. No NaN/null/undefined exposed ────────────────────────────────────────
def test_service_setup_pricing_uses_safe_fallback():
    src = read(SERVICE_SETUP)
    # Low/Mid/High values use null-safe fallback
    assert "?? " in src or "?.toLocaleString" in src or "?? \"—\"" in src


# ── nav-config.ts consistency ─────────────────────────────────────────────────
def test_nav_config_setup_group_has_correct_items():
    src = read(NAV_CONFIG)
    assert "Setup Checklist" in src
    assert "Business Profile" in src
    assert "Service Areas" in src
    assert "Service Setup" in src
    assert "Availability" in src


def test_nav_config_no_old_pricing_items():
    src = read(NAV_CONFIG)
    assert '"Pricing Setup"' not in src
    assert "Service Pricing Setup" not in src
    assert "Customer Price Preview" not in src


def test_nav_config_has_no_dead_pricing_mapping():
    # HS0 cleanup: the old "pricing" path-to-nav-id mapping (pointing at the
    # removed "Pricing Setup" nav item) was deleted outright rather than
    # redirected, since the feature itself was removed from the tenant menu.
    src = read(NAV_CONFIG)
    assert 'pricing:              "provider-pricing"' not in src


# ── Finance group labels ───────────────────────────────────────────────────────
def test_finance_group_uses_correct_labels():
    src = read(TENANT_LAYOUT)
    assert "Package & Credits" in src
    assert "Usage Credit Ledger" in src
    assert "Security Deposit" in src


def test_coverage_group_removed_from_nav():
    src = read(TENANT_LAYOUT)
    # The standalone "Coverage" top-level group was removed; Service Coverage
    # is now folded into the Setup group instead of losing the feature.
    assert 'label: "Coverage"' not in src
    assert "Service Coverage" in src
