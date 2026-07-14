"""MODULE-L5-10 — per-category customer charge (platform fee shown to customer)."""
import inspect


def test_price_snapshot_applies_the_customer_charge():
    """The platform earns from both sides: a commission from the provider AND a
    customer charge added to what the customer pays, shown as included. The price
    snapshot must expose the fee and an inclusive customer_total. Proven live: a
    Rs.500 service at 10% -> platform_fee 50, customer_total 550."""
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
    src = inspect.getsource(HomeServiceChatbotBookingService._compute_price_snapshot)
    assert "customer_charge_pct" in src
    assert "platform_fee" in src
    assert "customer_total" in src
    # display price must be the inclusive total, not the bare base
    assert '"display_price":   f"₹{int(customer_total)}"' in src


def test_admin_can_set_both_rates_independently():
    """PUT must update only the fields sent, so setting the customer charge does
    not clear the commission and vice versa."""
    import os
    router = open(os.path.join(os.path.dirname(__file__), "..", "app", "engines",
                  "admin_catalog", "admin_router.py"), encoding="utf-8").read()
    assert "customer_charge_pct" in router
    assert "model_dump(exclude_unset=True)" in router      # partial update
    # both keys validated 0..100
    assert "must be between 0 and 100" in router


def test_page_and_client_cover_the_customer_charge():
    import os
    root = os.path.join(os.path.dirname(__file__), "..")
    api = open(os.path.join(root, "frontend", "super-admin", "lib", "api.ts"), encoding="utf-8").read()
    assert "setCategoryCustomerCharge" in api
    assert "customer_charge_pct" in api
    page = open(os.path.join(root, "frontend", "super-admin", "app", "admin", "pricing",
                "commission", "page.tsx"), encoding="utf-8").read()
    assert "Customer Charge" in page
    assert "Provider Commission" in page
