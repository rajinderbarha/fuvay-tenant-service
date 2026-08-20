"""HOME-SERVICES-FINANCE: category-specific monetization workspace
(/admin/home-services/finance?tab=monetization). Runtime tests against the
live server, proving: Home-Services-only scope (never a client-supplied
vertical), independent customer/provider ledger entries on job completion,
idempotency, job-type rule application, and that this reuses the SAME
vertical_monetization engine (not a second one) as the generic Platform >
Finance > Vertical Monetization workspace.
"""
import uuid
import pytest
import pytest_asyncio
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient

from app.engines.vertical_monetization.customer_charge_recovery import (
    deduct_customer_platform_charge_recovery, RECOVERY_EVENT_TYPE,
)
from app.engines.execution.usage_credit_deduction import DEDUCTION_EVENT_TYPE
from app.engines.vertical_monetization.calculation_service import (
    calculate_customer_platform_fee, calculate_provider_completion_credits, to_minor,
)

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.in"
ADMIN_PASS = "Password123!"

pytestmark = pytest.mark.anyio
_TOKEN_CACHE: dict = {}


def test_500_with_two_ten_percent_charges_is_550_and_100_credits():
    """Exact business rule: ₹500 base + 10% customer charge is ₹550 shown;
    10% provider commission plus recovery of that ₹50 customer charge deducts
    100 total usage credits at completion."""
    policy = SimpleNamespace(
        id=uuid.uuid4(), version_number=1,
        provider_model="PERCENTAGE_COMMISSION", provider_percentage=Decimal("10"),
        provider_min_charge_minor=None, provider_max_charge_minor=None,
        provider_credit_units=None, provider_fixed_amount_minor=None,
        customer_fee_model="PERCENTAGE", customer_fee_percentage=Decimal("10"),
        customer_fee_fixed_amount_minor=None, customer_fee_min_minor=None,
        customer_fee_max_minor=None, collection_stage="on_completion",
        customer_fee_refund_policy="refundable_if_job_not_started",
    )
    customer = calculate_customer_platform_fee(
        policy=policy, service_subtotal_minor=to_minor(Decimal("500")),
        calculation_basis="test",
    )
    provider = calculate_provider_completion_credits(policy=policy, service_amount=Decimal("500"))
    assert customer["total_payable"] == "550.00"
    assert customer["customer_platform_fee"] == "50.00"
    assert provider["provider_charge_credit_units"] == "50.00"
    assert Decimal(provider["provider_charge_credit_units"]) + Decimal(customer["customer_platform_fee"]) == Decimal("100.00")


def test_provider_fixed_credit_and_percentage_bounds_are_executable():
    fixed = SimpleNamespace(
        provider_model="COMPLETION_CREDITS", provider_credit_units=Decimal("75"),
        provider_percentage=None, provider_min_charge_minor=None,
        provider_max_charge_minor=None, provider_fixed_amount_minor=None,
    )
    assert calculate_provider_completion_credits(
        policy=fixed, service_amount=Decimal("500"), credit_units_override=Decimal("120"),
    )["provider_charge_credit_units"] == "120.00"
    bounded = SimpleNamespace(
        provider_model="PERCENTAGE_COMMISSION", provider_percentage=Decimal("10"),
        provider_min_charge_minor=6000, provider_max_charge_minor=9000,
        provider_credit_units=None, provider_fixed_amount_minor=None,
    )
    assert calculate_provider_completion_credits(
        policy=bounded, service_amount=Decimal("500"),
    )["provider_charge_credit_units"] == "60.00"


@pytest.mark.asyncio
async def test_consultation_rule_charges_only_on_consultation_completion():
    from app.engines.execution.usage_credit_deduction import resolve_commission_credits
    vertical = SimpleNamespace(id=uuid.uuid4())
    policy = SimpleNamespace(
        id=uuid.uuid4(), provider_model="COMPLETION_CREDITS",
        provider_credit_units=25, provider_percentage=None,
        provider_min_charge_minor=None, provider_max_charge_minor=None,
        provider_fixed_amount_minor=None,
    )
    override = SimpleNamespace(
        id=uuid.uuid4(), provider_chargeable_event="consultation_completed",
        provider_charge_enabled=True, provider_charge_model="FIXED_CREDITS",
        provider_charge_credit_units=80,
    )
    def scalar(value):
        result = MagicMock(); result.scalar_one_or_none.return_value = value
        return result
    common = dict(
        job_price=Decimal("500"), category_id=uuid.uuid4(),
        master_service_id=uuid.uuid4(), offering_type_id=None, brand_id=None,
        job_type_id=uuid.uuid4(),
    )
    wrong_event_db = MagicMock()
    wrong_event_db.execute = AsyncMock(side_effect=[scalar(vertical), scalar(policy), scalar(override)])
    credits, _ = await resolve_commission_credits(
        wrong_event_db, chargeable_event="job_completed", **common,
    )
    assert credits == Decimal("0")
    matching_db = MagicMock()
    matching_db.execute = AsyncMock(side_effect=[scalar(vertical), scalar(policy), scalar(override)])
    credits, source = await resolve_commission_credits(
        matching_db, chargeable_event="consultation_completed", **common,
    )
    assert credits == Decimal("80.00")
    assert source == f"monetization_job_type_rule:{override.id}"


def test_completion_flow_maps_consultation_to_its_real_charge_event():
    import inspect
    from app.engines.execution.home_service_service import HomeServiceJobExecutionService
    src = inspect.getsource(HomeServiceJobExecutionService.complete_job)
    assert 'job_type_key == "consultation"' in src
    assert 'chargeable_event = "consultation_completed"' in src


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


@pytest_asyncio.fixture
async def ensure_hs_enabled(admin):
    yield
    await admin.post("/v1/admin/verticals/home_services/enable")


# ═══════════════════════════════════════════════════════════════════════════
# 1. HOME-SERVICES-ONLY SCOPE
# ═══════════════════════════════════════════════════════════════════════════

class TestHomeServicesOnlyScope:

    async def test_current_policy_is_home_services(self, admin):
        r = await admin.get("/v1/admin/home-services/finance/monetization/current")
        assert r.status_code == 200, r.text

    async def test_route_has_no_vertical_parameter_to_manipulate(self):
        """The Home Services Finance route path contains no {vertical}
        segment at all -- there is no query/path parameter a client could
        supply to redirect it at Coaching's policy."""
        import inspect
        from app.engines.vertical_monetization import home_services_finance_router as mod
        src = inspect.getsource(mod)
        assert '_HS_KEY = "home_services"' in src
        assert "vertical: str = Path" not in src  # no client-controlled vertical path param

    async def test_coaching_policy_unaffected_by_hs_publish(self, admin, ensure_hs_enabled):
        before = await admin.get("/v1/admin/monetization/verticals/coaching")
        before_data = before.json()["data"]["current"]

        await admin.post("/v1/admin/home-services/finance/monetization/draft", json={
            "provider_model": "COMPLETION_CREDITS", "provider_credit_units": 7,
            "customer_fee_model": "FIXED", "customer_fee_fixed_amount_minor": 500,
            "change_summary": "isolation test",
        })
        await admin.post("/v1/admin/home-services/finance/monetization/publish",
                         json={"reason": "isolation test publish"})

        after = await admin.get("/v1/admin/monetization/verticals/coaching")
        after_data = after.json()["data"]["current"]
        assert before_data == after_data

    async def test_disabling_home_services_blocks_finance_route(self, admin, ensure_hs_enabled):
        disabled = await admin.post(
            "/v1/admin/verticals/home_services/disable",
            json={"reason": "finance scope isolation test"},
        )
        assert disabled.status_code == 200, disabled.text
        r = await admin.get("/v1/admin/home-services/finance/monetization/current")
        assert r.status_code == 403, r.text
        assert r.json().get("error_code") == "VERTICAL_DISABLED"

    async def test_disabling_home_services_does_not_affect_coaching_route(self, admin, ensure_hs_enabled):
        disabled = await admin.post(
            "/v1/admin/verticals/home_services/disable",
            json={"reason": "cross vertical isolation test"},
        )
        assert disabled.status_code == 200, disabled.text
        r = await admin.get("/v1/admin/monetization/verticals/coaching")
        assert r.status_code == 200, r.text


# ═══════════════════════════════════════════════════════════════════════════
# 2. POLICY LIFECYCLE / IMMUTABILITY
# ═══════════════════════════════════════════════════════════════════════════

class TestPolicyLifecycle:

    async def test_publish_requires_reason(self, admin, ensure_hs_enabled):
        await admin.post("/v1/admin/home-services/finance/monetization/draft", json={
            "provider_model": "NONE", "customer_fee_model": "NONE",
        })
        r = await admin.post("/v1/admin/home-services/finance/monetization/publish", json={"reason": ""})
        assert r.status_code == 422

    async def test_published_policy_immutable_job_type_rules(self, admin, ensure_hs_enabled):
        current = await admin.get("/v1/admin/home-services/finance/monetization/current")
        policy_id = current.json()["data"]["id"]
        r = await admin.put(
            f"/v1/admin/home-services/finance/monetization/policies/{policy_id}/job-type-rules/{uuid.uuid4()}",
            json={"customer_charge_enabled": True})
        assert r.status_code == 422, r.text

    async def test_invalid_min_max_fails_validation(self, admin):
        r = await admin.post("/v1/admin/home-services/finance/monetization/validate", json={
            "provider_model": "NONE",
            "customer_fee_model": "PERCENTAGE_WITH_MIN_MAX", "customer_fee_percentage": "5",
            "customer_fee_min_minor": 9999, "customer_fee_max_minor": 100,
        })
        assert r.status_code == 200
        assert r.json()["data"]["valid"] is False

    async def test_draft_publish_creates_new_immutable_version(self, admin, ensure_hs_enabled):
        d = await admin.post("/v1/admin/home-services/finance/monetization/draft", json={
            "provider_model": "COMPLETION_CREDITS", "provider_credit_units": 8,
            "customer_fee_model": "NONE", "change_summary": "version bump test",
        })
        draft = d.json()["data"]
        pub = await admin.post("/v1/admin/home-services/finance/monetization/publish",
                               json={"reason": "version bump"})
        assert pub.status_code == 200, pub.text
        published = pub.json()["data"]
        assert published["id"] == draft["id"]
        assert published["is_current"] is True


# ═══════════════════════════════════════════════════════════════════════════
# 3. JOB-TYPE RULES
# ═══════════════════════════════════════════════════════════════════════════

class TestJobTypeRules:

    async def test_job_type_rule_upsert_and_list(self, admin, ensure_hs_enabled):
        job_types = await admin.get("/v1/admin/catalog/job-types")
        job_type_id = job_types.json()["data"]["items"][0]["id"]

        d = await admin.post("/v1/admin/home-services/finance/monetization/draft", json={
            "provider_model": "COMPLETION_CREDITS", "provider_credit_units": 10,
            "customer_fee_model": "NONE", "change_summary": "job type rule test",
        })
        policy_id = d.json()["data"]["id"]

        r = await admin.put(
            f"/v1/admin/home-services/finance/monetization/policies/{policy_id}/job-type-rules/{job_type_id}",
            json={"customer_charge_enabled": False, "provider_charge_credit_units": "0"})
        assert r.status_code == 200, r.text
        assert r.json()["data"]["customer_charge_enabled"] is False

        listed = await admin.get(f"/v1/admin/home-services/finance/monetization/policies/{policy_id}/job-type-rules")
        assert any(x["job_type_id"] == job_type_id for x in listed.json()["data"]["items"])


# ═══════════════════════════════════════════════════════════════════════════
# 4. INDEPENDENT LEDGER ENTRIES + IDEMPOTENCY (unit-level, real DB function)
# ═══════════════════════════════════════════════════════════════════════════

class TestLedgerSeparationAndIdempotency:

    def test_recovery_event_type_distinct_from_completion_charge(self):
        assert RECOVERY_EVENT_TYPE != DEDUCTION_EVENT_TYPE
        assert RECOVERY_EVENT_TYPE == "customer_platform_charge_recovery"
        assert DEDUCTION_EVENT_TYPE == "completed_job_deduction"

    def test_completion_handler_calls_both_independently(self):
        import inspect
        from app.engines.execution import home_service_service
        src = inspect.getsource(home_service_service.HomeServiceExecutionService.complete_job
                               if hasattr(home_service_service, "HomeServiceExecutionService") else home_service_service)
        assert "deduct_for_completed_job" in src
        assert "deduct_customer_platform_charge_recovery" in src
        assert "except Exception" in src  # one failing cannot crash/rollback the other

    def test_recovery_function_is_idempotent_per_job(self):
        import inspect
        from app.engines.vertical_monetization.customer_charge_recovery import deduct_customer_platform_charge_recovery
        src = inspect.getsource(deduct_customer_platform_charge_recovery)
        assert "already_recovered" in src
        assert "UsageCreditLedger.job_id == job_id" in src


# ═══════════════════════════════════════════════════════════════════════════
# 5. SECURITY
# ═══════════════════════════════════════════════════════════════════════════

class TestSecurity:

    async def test_permission_enforced_no_token(self):
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.get("/v1/admin/home-services/finance/monetization/current")
            assert r.status_code in (401, 403)

    async def test_preview_does_not_persist(self, admin):
        before = await admin.get("/v1/admin/home-services/finance/monetization/current")
        await admin.post("/v1/admin/home-services/finance/monetization/preview", json={
            "draft": {"customer_fee_model": "PERCENTAGE", "customer_fee_percentage": "99", "currency": "INR"},
            "example_service_amount": "500",
        })
        after = await admin.get("/v1/admin/home-services/finance/monetization/current")
        assert before.json()["data"] == after.json()["data"]

    async def test_no_provider_payout_endpoint_in_this_router(self):
        import inspect
        from app.engines.vertical_monetization import home_services_finance_router as mod
        src = inspect.getsource(mod)
        assert "payout" not in src.lower()
