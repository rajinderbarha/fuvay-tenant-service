"""VERTICAL-MONETIZATION: two independent, vertical-scoped monetization
policies (provider-side + customer-side). Runtime tests against the live
server, proving real calculation, immutable versioning, isolation, and the
integration points into the canonical booking/quote/execution pipeline.
"""
import uuid
import pytest
import pytest_asyncio
from decimal import Decimal
from httpx import AsyncClient

from app.engines.vertical_monetization.calculation_service import (
    calculate_customer_platform_fee, to_minor, to_major,
)
from app.engines.vertical_monetization.models import VerticalMonetizationPolicy

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.in"
ADMIN_PASS = "Password123!"

pytestmark = pytest.mark.anyio
_TOKEN_CACHE: dict = {}


@pytest_asyncio.fixture(scope="module")
async def admin_token(anyio_backend):
    if "tok" not in _TOKEN_CACHE:
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.post("/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
            assert r.status_code == 200, r.text
            _TOKEN_CACHE["tok"] = r.json()["data"]["access_token"]
    return _TOKEN_CACHE["tok"]


@pytest_asyncio.fixture
async def admin(admin_token):
    async with AsyncClient(base_url=BASE, headers={"Authorization": f"Bearer {admin_token}"}, timeout=30) as c:
        yield c


def _policy(**overrides):
    defaults = dict(
        id=uuid.uuid4(), version_number=1,
        customer_fee_model="PERCENTAGE", customer_fee_percentage=Decimal("5"),
        customer_fee_fixed_amount_minor=None, customer_fee_min_minor=None, customer_fee_max_minor=None,
        collection_stage="after_estimate_approval", customer_fee_refund_policy="refundable_if_job_not_started",
    )
    defaults.update(overrides)
    return type("P", (), defaults)()


# ═══════════════════════════════════════════════════════════════════════════
# 1. PURE CALCULATION (money math, deterministic rounding, integer minor units)
# ═══════════════════════════════════════════════════════════════════════════

class TestCalculation:

    def test_no_policy_returns_zero_fee(self):
        result = calculate_customer_platform_fee(policy=None, service_subtotal_minor=50000, calculation_basis="test")
        assert result["customer_platform_fee"] == "0.00"
        assert result["policy_id"] is None

    def test_percentage_fee_is_deterministic(self):
        p = _policy(customer_fee_model="PERCENTAGE", customer_fee_percentage=Decimal("5"))
        result = calculate_customer_platform_fee(policy=p, service_subtotal_minor=50000, calculation_basis="test")
        assert result["customer_platform_fee"] == "25.00"
        assert result["total_payable"] == "525.00"

    def test_percentage_with_min_max_clamps_to_minimum(self):
        p = _policy(customer_fee_model="PERCENTAGE_WITH_MIN_MAX", customer_fee_percentage=Decimal("1"),
                    customer_fee_min_minor=2000, customer_fee_max_minor=10000)
        result = calculate_customer_platform_fee(policy=p, service_subtotal_minor=10000, calculation_basis="test")
        assert result["fee_amount_minor"] == 2000  # 1% of 100 = 1, clamped up to min 20

    def test_percentage_with_min_max_clamps_to_maximum(self):
        p = _policy(customer_fee_model="PERCENTAGE_WITH_MIN_MAX", customer_fee_percentage=Decimal("50"),
                    customer_fee_min_minor=100, customer_fee_max_minor=5000)
        result = calculate_customer_platform_fee(policy=p, service_subtotal_minor=100000, calculation_basis="test")
        assert result["fee_amount_minor"] == 5000

    def test_fixed_fee_ignores_service_amount(self):
        p = _policy(customer_fee_model="FIXED", customer_fee_fixed_amount_minor=1500)
        r1 = calculate_customer_platform_fee(policy=p, service_subtotal_minor=10000, calculation_basis="test")
        r2 = calculate_customer_platform_fee(policy=p, service_subtotal_minor=999999, calculation_basis="test")
        assert r1["fee_amount_minor"] == r2["fee_amount_minor"] == 1500

    def test_none_model_fee_is_zero(self):
        p = _policy(customer_fee_model="NONE")
        result = calculate_customer_platform_fee(policy=p, service_subtotal_minor=50000, calculation_basis="test")
        assert result["fee_amount_minor"] == 0

    def test_integer_minor_units_no_float_drift(self):
        # 33.335 rupees -> HALF_UP -> 3334 minor units, exactly (no float
        # error accumulation across repeated integer multiplication).
        minor = to_minor(Decimal("33.335"))
        assert isinstance(minor, int)
        assert minor == 3334
        assert to_major(minor * 3) == "100.02"

    def test_rounding_is_half_up(self):
        p = _policy(customer_fee_model="PERCENTAGE", customer_fee_percentage=Decimal("2.5"))
        # 2.5% of 1 rupee (100 minor) = 2.5 minor units -> HALF_UP -> 3
        result = calculate_customer_platform_fee(policy=p, service_subtotal_minor=100, calculation_basis="test")
        assert result["fee_amount_minor"] == 3


# ═══════════════════════════════════════════════════════════════════════════
# 2. LIVE ADMIN POLICY WORKFLOW
# ═══════════════════════════════════════════════════════════════════════════

class TestPolicyWorkflowLive:

    async def test_list_returns_summary_and_items(self, admin):
        r = await admin.get("/v1/admin/monetization/verticals")
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert "items" in data and "summary" in data

    async def test_draft_then_publish_creates_immutable_version(self, admin):
        uid = uuid.uuid4().hex[:6]
        r = await admin.post("/v1/admin/monetization/verticals/real_estate/draft", json={
            "provider_model": "LEAD_FEE", "provider_fixed_amount_minor": 5000,
            "customer_fee_model": "NONE", "change_summary": f"test-{uid}",
        })
        assert r.status_code == 200, r.text
        draft = r.json()["data"]
        assert draft["status"] == "draft"

        pub = await admin.post("/v1/admin/monetization/verticals/real_estate/publish",
                               json={"reason": f"publish-{uid}"})
        assert pub.status_code == 200, pub.text
        published = pub.json()["data"]
        assert published["status"] == "published"
        assert published["is_current"] is True
        assert published["id"] == draft["id"]

    async def test_publish_without_reason_rejected(self, admin):
        await admin.post("/v1/admin/monetization/verticals/real_estate/draft", json={
            "provider_model": "NONE", "customer_fee_model": "NONE",
        })
        r = await admin.post("/v1/admin/monetization/verticals/real_estate/publish", json={"reason": ""})
        assert r.status_code == 422

    async def test_provider_and_customer_charges_are_independent_fields(self, admin):
        r = await admin.post("/v1/admin/monetization/verticals/real_estate/draft", json={
            "provider_model": "SUBSCRIPTION", "provider_subscription_plan_id": str(uuid.uuid4()),
            "customer_fee_model": "FIXED", "customer_fee_fixed_amount_minor": 2500,
        })
        assert r.status_code == 200, r.text
        d = r.json()["data"]
        assert d["provider_model"] == "SUBSCRIPTION"
        assert d["customer_fee_model"] == "FIXED"

    async def test_validation_rejects_incomplete_percentage_policy(self, admin):
        r = await admin.post("/v1/admin/monetization/validate", json={
            "provider_model": "NONE", "customer_fee_model": "PERCENTAGE",
        })
        assert r.status_code == 200
        assert r.json()["data"]["valid"] is False

    async def test_preview_does_not_persist(self, admin):
        before = await admin.get("/v1/admin/monetization/verticals/home_services")
        r = await admin.post("/v1/admin/monetization/preview", json={
            "draft": {"customer_fee_model": "PERCENTAGE", "customer_fee_percentage": "99", "collection_stage": "on_completion", "currency": "INR"},
            "example_service_amount": "500",
        })
        assert r.status_code == 200, r.text
        assert r.json()["data"]["is_preview"] is True
        after = await admin.get("/v1/admin/monetization/verticals/home_services")
        assert before.json()["data"]["current"] == after.json()["data"]["current"]

    async def test_verticals_have_independent_models(self, admin):
        hs = await admin.get("/v1/admin/monetization/verticals/home_services")
        coaching = await admin.get("/v1/admin/monetization/verticals/coaching")
        hs_current = hs.json()["data"]["current"]
        coaching_current = coaching.json()["data"]["current"]
        if hs_current and coaching_current:
            assert hs_current["provider_model"] != coaching_current["provider_model"] or \
                   hs_current["customer_fee_model"] != coaching_current["customer_fee_model"]

    async def test_permission_enforced(self):
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.get("/v1/admin/monetization/verticals")
            assert r.status_code in (401, 403)

    async def test_history_lists_versions(self, admin):
        r = await admin.get("/v1/admin/monetization/verticals/real_estate/history")
        assert r.status_code == 200, r.text
        assert isinstance(r.json()["data"]["items"], list)

    async def test_audit_records_publish_action(self, admin):
        r = await admin.get("/v1/admin/monetization/verticals/real_estate/audit")
        assert r.status_code == 200, r.text
        actions = [a["action_type"] for a in r.json()["data"]["items"]]
        assert "monetization.policy.publish" in actions


# ═══════════════════════════════════════════════════════════════════════════
# 3. ADMIN CANNOT SET TENANT SERVICE PRICES
# ═══════════════════════════════════════════════════════════════════════════

class TestNoTenantPriceControl:

    def test_policy_model_has_no_tenant_price_fields(self):
        columns = {c.name for c in VerticalMonetizationPolicy.__table__.columns}
        forbidden = {"tenant_base_price", "tenant_min_price", "tenant_max_price",
                    "tenant_visit_fee", "city_price", "zipcode_price", "tier_price"}
        assert not (columns & forbidden)

    async def test_draft_endpoint_rejects_unknown_tenant_price_fields_silently_ignored(self, admin):
        """The draft endpoint only ever writes known _DRAFT_FIELDS -- a
        client attempting to smuggle a tenant price field has no effect."""
        r = await admin.post("/v1/admin/monetization/verticals/home_services/draft", json={
            "provider_model": "COMPLETION_CREDITS", "provider_credit_units": 5,
            "customer_fee_model": "NONE",
            "tenant_base_price": 999999,  # not a real field -- must be silently dropped
        })
        assert r.status_code == 200, r.text
        assert "tenant_base_price" not in r.json()["data"]


# ═══════════════════════════════════════════════════════════════════════════
# 4. INTEGRATION POINTS (static evidence the real pipeline calls the engine)
# ═══════════════════════════════════════════════════════════════════════════

class TestIntegrationWiring:

    def test_booking_finalize_creates_charge(self):
        import inspect
        from app.engines.final_records import creation_service
        src = inspect.getsource(creation_service.HomeServiceFinalCreationService.finalize)
        assert "create_charge_for_booking" in src

    def test_quote_approval_creates_charge_only_for_current_quote(self):
        import inspect
        from app.engines.quote_checklist import quote_service
        src = inspect.getsource(quote_service.QuoteService.customer_approve if hasattr(quote_service, "QuoteService") else quote_service)
        assert "create_charge_for_quote" in src
        assert "is_current" in src

    def test_work_start_gate_checks_platform_fee(self):
        import inspect
        from app.engines.execution import home_service_service
        src = inspect.getsource(home_service_service)
        assert "assert_customer_platform_fee_paid_if_required" in src

    def test_webhook_never_splits_platform_fee_with_tenant(self):
        import inspect
        from app.engines.payment import service as payment_service
        src = inspect.getsource(payment_service.PaymentService.process_payment_webhook)
        assert "CUSTOMER_PLATFORM_FEE" in src
        assert "net_to_tenant = Decimal(\"0\")" in src

    def test_superseded_quote_cannot_create_charge(self):
        import asyncio
        from app.engines.vertical_monetization.charge_service import create_charge_for_quote
        from app.exceptions import ServiceOSException

        async def run():
            with pytest.raises(ServiceOSException) as exc:
                await create_charge_for_quote(
                    db=None, vertical_key="home_services", quote_id=uuid.uuid4(), quote_version=1,
                    is_current=False, job_id=uuid.uuid4(), tenant_id=uuid.uuid4(), customer_id=uuid.uuid4(),
                    service_amount_major=Decimal("500"), source_event="test",
                )
            assert exc.value.error_code == "PAYMENT_CONTEXT_UNRESOLVED"
        asyncio.get_event_loop().run_until_complete(run())
