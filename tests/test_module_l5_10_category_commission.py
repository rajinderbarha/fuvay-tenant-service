"""MODULE-L5-10 — per-category commission rate (was hardcoded flat 10%)."""
import inspect
import os


def test_resolve_rate_is_category_aware():
    """_resolve_rate was a hardcoded flat DEFAULT_COMMISSION_RATE for every
    category regardless of value. It must now read the category's commission_pct
    and fall back to the default only when unset."""
    from app.engines.invoice_payment.commission_service import ServiceCommissionService
    src = inspect.getsource(ServiceCommissionService._resolve_rate)
    assert "ServiceCategory.commission_pct" in src
    assert "DEFAULT_COMMISSION_RATE" in src           # fallback retained
    # and calculate_commission must pass the invoice's category to it
    calc = inspect.getsource(ServiceCommissionService.calculate_commission)
    assert "self._resolve_rate(db, inv.category_id)" in calc


def test_admin_endpoints_and_page_exist():
    root = os.path.join(os.path.dirname(__file__), "..")
    router = open(os.path.join(root, "app", "engines", "admin_catalog", "admin_router.py"),
                  encoding="utf-8").read()
    assert '/category-commission-rates' in router
    assert 'commission_pct must be between 0 and 100' in router   # range guard
    page = os.path.join(root, "frontend", "super-admin", "app", "admin", "pricing",
                        "commission", "page.tsx")
    assert os.path.isfile(page)
    nav = open(os.path.join(root, "frontend", "super-admin", "components", "layout",
                            "AdminLayout.tsx"), encoding="utf-8").read()
    assert "/admin/pricing/commission" in nav          # reachable from the menu


def test_new_pages_are_reachable_from_navigation():
    """The user asked that the menu be updated everywhere for the pages built
    this session."""
    root = os.path.join(os.path.dirname(__file__), "..")
    # provider complaints -> tenant nav
    tnav = open(os.path.join(root, "frontend", "tenant-portal", "components", "layout",
                             "TenantLayout.tsx"), encoding="utf-8").read()
    assert "/provider/complaints" in tnav
    # customer complaints -> profile entry
    prof = open(os.path.join(root, "frontend", "customer-app", "app", "customer",
                             "profile", "page.tsx"), encoding="utf-8").read()
    assert "/customer/complaints" in prof
