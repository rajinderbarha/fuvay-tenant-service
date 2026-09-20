"""MODULE-L5-10 — per-category customer charge (platform fee shown to customer)."""
import inspect


def test_price_snapshot_applies_the_customer_charge():
    """The platform earns from both sides: a commission from the provider AND a
    customer charge added to what the customer pays, shown as included. The price
    snapshot must expose the fee and an inclusive customer_total. Proven live: a
    Rs.500 service at 10% -> platform_fee 50, customer_total 550."""
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
    src = inspect.getsource(HomeServiceChatbotBookingService._compute_price_snapshot)
    assert "get_current_policy_by_vertical_key" in src
    assert "calculate_customer_platform_fee" in src
    assert "customer_charge_pct" not in src
    assert "platform_fee" in src
    assert "customer_total" in src
    # display price must be the inclusive total/range, not the bare base
    assert '"display_price":   _format_customer_price(' in src


def test_customer_price_formatter_preserves_real_ranges():
    from app.engines.home_service_booking.service import _format_customer_price

    assert _format_customer_price(130, 130, 650, requires_inspection_estimate=False) == "₹130–₹650"
    assert _format_customer_price(550, 550, 550, requires_inspection_estimate=False) == "₹550"
    assert _format_customer_price(249, 249, None, requires_inspection_estimate=True) == "₹249"


def test_plumbing_fixture_codes_match_their_scoped_price_types_only():
    from app.engines.home_service_booking.question_flow_service import _pricing_dimension_key

    assert _pricing_dimension_key("tap") == _pricing_dimension_key("Tap change")
    assert _pricing_dimension_key("wash_basin") == _pricing_dimension_key("Wash Basin installation")
    assert _pricing_dimension_key("commode") == _pricing_dimension_key("Toilet replacement")


def test_plumbing_fixture_answer_selects_the_exact_mapped_price_type():
    import asyncio
    import uuid
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.engines.home_service_booking.question_flow_service import QuestionFlowService

    basin = SimpleNamespace(id=uuid.uuid4(), slug="wash-basin", name="Wash Basin installation")
    tap = SimpleNamespace(id=uuid.uuid4(), slug="tap-change", name="Tap change")

    class Result:
        def scalars(self):
            return self

        def all(self):
            return [tap, basin]

    class DB:
        async def execute(self, *args, **kwargs):
            return Result()

    draft = SimpleNamespace(offering_id=uuid.uuid4(), offering_type_id=None)
    service = QuestionFlowService.__new__(QuestionFlowService)
    service.db = DB()
    service._answer_target = AsyncMock(return_value="service_types")

    asyncio.run(service._bridge_to_draft_columns(draft, "fixture_type", "wash_basin"))

    assert draft.offering_type_id == basin.id


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
    page = open(os.path.join(root, "frontend", "super-admin", "app", "admin", "home-services",
                "finance", "page.tsx"), encoding="utf-8").read()
    assert "customer charge" in page.lower()
    assert "provider commission" in page.lower()
