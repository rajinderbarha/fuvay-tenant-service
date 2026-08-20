"""MODULE-L5-10 — per-category commission rate (was hardcoded flat 10%)."""
import inspect
import os


def test_resolve_rate_is_category_aware():
    """_resolve_rate was a hardcoded flat DEFAULT_COMMISSION_RATE for every
    category regardless of value. It must now read the category's commission_pct
    and fall back to the default only when unset.

    Updated 2026-08-05: _resolve_rate no longer inlines that lookup -- it
    delegates to resolve_provider_commission_rate(), the single canonical
    rate resolver shared with the Home Services charging path. The behaviour
    this test guards is unchanged, so the assertions now follow the
    delegation instead of asserting on the caller's source text (which would
    fail purely because the logic moved, not because it regressed)."""
    from app.engines.invoice_payment.commission_service import (
        ServiceCommissionService, resolve_provider_commission_rate,
    )
    src = inspect.getsource(ServiceCommissionService._resolve_rate)
    assert "resolve_provider_commission_rate" in src   # delegates, never re-implements

    resolver = inspect.getsource(resolve_provider_commission_rate)
    assert "ServiceCategory" in resolver               # loads the category
    assert "commission_pct" in resolver                # and reads its rate
    assert "DEFAULT_COMMISSION_RATE" in resolver       # fallback retained
    # and calculate_commission must pass the invoice's category to it
    calc = inspect.getsource(ServiceCommissionService.calculate_commission)
    assert "self._resolve_rate(db, inv.category_id)" in calc


def test_admin_endpoints_and_page_exist():
    root = os.path.join(os.path.dirname(__file__), "..")
    router = open(os.path.join(root, "app", "engines", "admin_catalog", "admin_router.py"),
                  encoding="utf-8").read()
    assert '/category-commission-rates' in router
    assert 'must be between 0 and 100' in router   # range guard
    page = os.path.join(root, "frontend", "super-admin", "app", "admin", "pricing",
                        "commission", "page.tsx")
    assert os.path.isfile(page)
    # Home Services now has one finance authority: Monetization. Provider
    # Charges is a transaction ledger and must not expose a second editor.
    fin_page = open(os.path.join(root, "frontend", "super-admin", "app", "admin",
                                 "home-services", "finance", "page.tsx"),
                    encoding="utf-8").read()
    assert "Category Commission Overrides" not in fin_page
    assert "setCategoryCommissionRate" not in fin_page
    assert "single provider commission rate for Home Services" in fin_page
    detail = open(os.path.join(root, "frontend", "super-admin", "app", "admin",
                               "categories", "[id]", "page.tsx"), encoding="utf-8").read()
    assert "getCategoryCommissionAuthority" in detail
    assert "upsertCategoryConfig" not in detail         # no duplicate category editor
    assert "only provider and customer charge configuration authority" in detail
    nav = open(os.path.join(root, "frontend", "super-admin", "components", "layout",
                            "AdminLayout.tsx"), encoding="utf-8").read()
    assert "/admin/home-services/finance" in nav       # reachable from the menu


def test_new_pages_are_reachable_from_navigation():
    """The user asked that the menu be updated everywhere for the pages built
    this session."""
    root = os.path.join(os.path.dirname(__file__), "..")
    # provider complaints -> tenant nav. Path corrected 2026-08-05: the nav
    # pointed at /provider/complaints, but the real, canonical tenant
    # complaints workspace is /home-services/complaints (backed by
    # /v1/tenant/home-services/complaints on the shared complaints engine).
    # Assert the live path, not the superseded one.
    tnav = open(os.path.join(root, "frontend", "tenant-portal", "components", "layout",
                             "TenantLayout.tsx"), encoding="utf-8").read()
    assert "/home-services/complaints" in tnav
    # Customer is native-only. The deleted web customer app must not be
    # resurrected merely to satisfy an obsolete navigation assertion.
    assert not os.path.isdir(os.path.join(root, "frontend", "customer-app"))
