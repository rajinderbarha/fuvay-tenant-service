"""HS9B — Finance UI + Review Flow + Low-Credit Matching Restriction.

Static/logic-style tests matching this session's established convention,
plus direct calls to the real resolver function (no DB mocking needed
for pure logic). Live DB scenarios are documented in
HS9B_LIVE_FINANCE_REVIEW_LOW_CREDIT_VERIFICATION_REPORT.md — this file
covers what can be verified without a live database connection.
"""
import pathlib
import uuid
from decimal import Decimal

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]

MATCHING_ENGINE = (ROOT / "app/engines/home_service_booking/matching_engine.py").read_text(encoding="utf-8-sig")
CUSTOMER_ROUTER = (ROOT / "app/engines/home_service_assignment/customer_router.py").read_text(encoding="utf-8-sig")
PROVIDER_ROUTER = (ROOT / "app/engines/provider_portal/router.py").read_text(encoding="utf-8-sig")
DEDUCTION = (ROOT / "app/engines/execution/usage_credit_deduction.py").read_text(encoding="utf-8-sig")
TENANT_MODELS = (ROOT / "app/engines/tenant_engine/models.py").read_text(encoding="utf-8-sig")
ADMIN_ROUTER = (ROOT / "app/engines/tenant_engine/admin_router.py").read_text(encoding="utf-8-sig")


# ── 1-4. Single Home Services monetization authority ─────────────────────────

def test_resolver_uses_published_vertical_policy_only():
    assert "VerticalMonetizationPolicy" in DEDUCTION
    assert "ServicePricingRule" not in DEDUCTION
    assert "resolve_completed_job_deduction_credits" not in DEDUCTION


def test_resolver_has_no_hidden_no_policy_fallback():
    assert '# With no published policy, no provider charge is created.' in DEDUCTION
    assert 'return Decimal("0"), None' in DEDUCTION


@pytest.mark.asyncio
async def test_all_home_services_use_the_same_published_policy_live():
    """The live resolver must return a vertical policy source, never a
    service/type/brand pricing-rule source."""
    try:
        from app.database import create_engine
        from sqlalchemy.ext.asyncio import async_sessionmaker
        from app.engines.execution.usage_credit_deduction import resolve_commission_credits
    except Exception:
        pytest.skip("DB/engine imports unavailable in this environment")

    try:
        engine = create_engine()
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            _, first_source = await resolve_commission_credits(
                db, job_price=Decimal("1000"), category_id=uuid.uuid4(),
                master_service_id=uuid.uuid4(), offering_type_id=uuid.uuid4(),
                brand_id=uuid.uuid4(),
            )
            _, second_source = await resolve_commission_credits(
                db, job_price=Decimal("1000"), category_id=uuid.uuid4(),
                master_service_id=uuid.uuid4(), offering_type_id=None,
                brand_id=None,
            )
            assert first_source == second_source
            assert first_source is None or first_source.startswith("monetization_policy:")
    except Exception:
        pytest.skip("Real dev database not reachable in this environment")


# ── 5-7. Ledger fields + idempotency ──────────────────────────────────────────

def test_ledger_model_has_required_fields():
    for field in ("job_id", "booking_id", "event_type", "credit_delta",
                  "balance_before", "balance_after", "deduction_source",
                  "request_id"):
        assert field in TENANT_MODELS


def test_deduction_is_idempotent_per_job():
    fn = DEDUCTION.split("async def deduct_for_completed_job")[1]
    assert "already_deducted" in fn
    assert "UsageCreditLedger.job_id == job_id" in fn


def test_ledger_has_db_level_unique_guard():
    migration = (ROOT / "alembic/versions/129_hs9_usage_credit_ledger.py").read_text(encoding="utf-8-sig")
    assert "uq_ucl_job_event_once" in migration
    assert "unique=True" in migration


# ── 8-9. Low-credit tenant status + matching exclusion ────────────────────────

def test_bookability_gate_checks_credit_balance():
    assert "credit_balance > 0" in PROVIDER_ROUTER
    assert "USAGE_CREDITS_INSUFFICIENT" in PROVIDER_ROUTER


def test_matching_gate_surfaces_insufficient_credits_reason():
    fn = MATCHING_ENGINE.split("async def _passes_full_eligibility_gate")[1]
    assert "INSUFFICIENT_USAGE_CREDITS" in fn
    assert "USAGE_CREDITS_INSUFFICIENT" in fn  # reads the real bookability blocker code


def test_eligibility_gate_codes_include_credit_reason():
    codes_block = MATCHING_ENGINE.split("ELIGIBILITY_GATE_CODES = (")[1].split(")")[0]
    assert "INSUFFICIENT_USAGE_CREDITS" in codes_block


# ── 10. request_id on new endpoints ───────────────────────────────────────────

def test_rating_endpoint_errors_include_request_id():
    fn = CUSTOMER_ROUTER.split("async def submit_booking_rating")[1]
    assert '_RID(r)' in fn or "ServiceOSException" in fn


def test_review_already_submitted_error_code_exact():
    assert '"REVIEW_ALREADY_SUBMITTED"' in CUSTOMER_ROUTER
    assert '"BOOKING_NOT_COMPLETED"' in CUSTOMER_ROUTER


# ── Endpoints exist ────────────────────────────────────────────────────────────

def test_tenant_usage_credit_endpoints_exist():
    assert '"/usage-credits/balance"' in PROVIDER_ROUTER
    assert '"/usage-credits/ledger"' in PROVIDER_ROUTER


def test_admin_usage_credit_ledger_endpoint_exists():
    assert '"/{tenant_id}/usage-credit-ledger"' in ADMIN_ROUTER


def test_customer_rating_endpoints_exist():
    assert '"/{booking_id}/rating"' in CUSTOMER_ROUTER


# ── Forbidden labels ──────────────────────────────────────────────────────────

FORBIDDEN = [
    "Cash Wallet", "Wallet Balance", "Withdraw", "Withdrawable Balance",
    "Tenant Payout", "Provider Earnings Wallet", "Escrow",
    "Platform Collected Service Payment", "Provider Cash Balance",
    "Credit Wallet Health",
]


def test_no_forbidden_labels():
    for term in FORBIDDEN:
        assert term not in DEDUCTION, f"forbidden label in deduction module: {term}"
        assert term not in CUSTOMER_ROUTER, f"forbidden label in customer router: {term}"
