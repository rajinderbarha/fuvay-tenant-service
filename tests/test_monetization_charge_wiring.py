"""Platform-fee charges are actually created at booking and quote approval.

REAL PRODUCTION BUG these lock down: both call sites into
vertical_monetization.charge_service were missing three REQUIRED keyword-only
arguments (customer_id, service_amount_major,
source_event). Each call therefore raised TypeError on EVERY booking and EVERY
quote approval -- and each is wrapped in a deliberately broad `except` (so a
monetization misconfiguration cannot block a confirmed booking), which turned
the crash into a log line nobody read.

The net effect: the engine, its policies and its calculation all existed and
were configurable by Super Admin, the call sites existed and looked correct, and
NO platform fee was ever charged for anything. Confirmed live by the log
"monetization.booking_charge_failed ... missing 3 required keyword-only
arguments".

A signature check is the right guard here precisely BECAUSE the exception is
swallowed: no functional test of booking would ever fail, so nothing but this
would notice the call breaking again.
"""
from __future__ import annotations

import inspect
import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.final_records.creation_service import _booking_service_amount
from app.engines.quote_checklist.quote_service import _quote_payable_amount
from app.engines.vertical_monetization.charge_service import (
    create_charge_for_booking, create_charge_for_quote,
)
from app.engines.quote_checklist.quote_service import ServiceJobQuoteService


def _required_kwargs(func) -> set[str]:
    """Keyword-only parameters with no default -- the ones a caller MUST pass."""
    return {
        name for name, p in inspect.signature(func).parameters.items()
        if p.kind is inspect.Parameter.KEYWORD_ONLY and p.default is inspect.Parameter.empty
    }


def _call_kwargs(source: str, func_name: str) -> set[str]:
    """The keyword names a source snippet passes to `func_name(...)`."""
    start = source.index(f"{func_name}(")
    depth = 0
    end = start
    for i in range(start, len(source)):
        if source[i] == "(":
            depth += 1
        elif source[i] == ")":
            depth -= 1
            if depth == 0:
                end = i
                break
    call = source[start:end]
    return {
        line.split("=")[0].strip()
        for line in call.replace("\n", " ").split(",")
        if "=" in line and line.split("=")[0].strip().isidentifier()
    }


def test_booking_call_site_passes_every_required_argument():
    from app.engines.final_records import creation_service
    source = inspect.getsource(creation_service.HomeServiceFinalCreationService.finalize)
    passed = _call_kwargs(source, "create_charge_for_booking")
    missing = _required_kwargs(create_charge_for_booking) - passed - {"db"}
    assert missing == set(), (
        f"create_charge_for_booking would raise TypeError -- missing {sorted(missing)}. "
        "The surrounding `except` hides this, so no booking test would catch it."
    )


def test_quote_call_site_passes_every_required_argument():
    from app.engines.quote_checklist import quote_service
    source = inspect.getsource(quote_service)
    passed = _call_kwargs(source, "create_charge_for_quote")
    missing = _required_kwargs(create_charge_for_quote) - passed - {"db"}
    assert missing == set(), (
        f"create_charge_for_quote would raise TypeError -- missing {sorted(missing)}."
    )


# ── Amount resolution ─────────────────────────────────────────────────────

def test_booking_amount_prefers_what_the_customer_actually_chose():
    assert _booking_service_amount(
        {"selected_price_amount": "499", "standard_price": "399"}) == Decimal("499")
    assert _booking_service_amount({"standard_price": "399"}) == Decimal("399")
    assert _booking_service_amount({"base_price": "350"}) == Decimal("350")


def test_inspection_mode_charges_against_the_visit_fee_only():
    """The repair amount does not exist yet at booking time -- it is charged
    later from the approved quote. The visit fee is the only figure the customer
    has agreed to up front."""
    assert _booking_service_amount({"visit_fee": "299"}) == Decimal("299")


def test_an_unusable_snapshot_yields_zero_rather_than_a_guess():
    """A zero-amount charge row still records the policy and keeps the audit
    trail. Inventing a service amount would compute a real fee against a number
    the customer never saw."""
    assert _booking_service_amount({}) == Decimal("0")
    assert _booking_service_amount(None) == Decimal("0")
    assert _booking_service_amount({"standard_price": 0, "visit_fee": None}) == Decimal("0")


def test_a_malformed_amount_is_skipped_not_crashed_on():
    # A junk value must fall through to the next candidate rather than raising
    # inside a path that is already swallowing exceptions.
    assert _booking_service_amount({"standard_price": "abc", "visit_fee": "299"}) == Decimal("299")
    assert _booking_service_amount({"standard_price": "abc"}) == Decimal("0")


def test_quote_amount_prefers_the_customer_payable_total():
    class Q:
        customer_payable_amount = "2499.50"
        total_amount = "9999"
    assert _quote_payable_amount(Q()) == Decimal("2499.50")


def test_quote_amount_falls_back_and_never_raises_on_junk():
    class Junk:
        customer_payable_amount = "abc"
        total_amount = "1200"
    assert _quote_payable_amount(Junk()) == Decimal("1200")

    class Empty:
        customer_payable_amount = None
        total_amount = None
    assert _quote_payable_amount(Empty()) == Decimal("0")


@pytest.mark.asyncio
async def test_quote_total_includes_platform_charge_but_keeps_provider_base():
    policy = SimpleNamespace(
        id=uuid.uuid4(), version_number=7,
        customer_fee_model="PERCENTAGE", customer_fee_percentage=Decimal("10"),
        customer_fee_fixed_amount_minor=None, customer_fee_min_minor=None,
        customer_fee_max_minor=None, collection_stage="on_completion",
        customer_fee_refund_policy="refundable_if_job_not_started",
    )
    item = SimpleNamespace(item_type="service", line_total=Decimal("500"))
    quote = SimpleNamespace(job_id=uuid.uuid4())
    scalar = MagicMock()
    scalar.scalar_one_or_none.return_value = None
    db = MagicMock()
    db.execute = AsyncMock(return_value=scalar)

    with patch(
        "app.engines.vertical_monetization.calculation_service.get_current_policy_by_vertical_key",
        new=AsyncMock(return_value=policy),
    ), patch(
        "app.engines.vertical_monetization.calculation_service.get_active_job_type_rule",
        new=AsyncMock(return_value=None),
    ):
        totals = await ServiceJobQuoteService()._recalculate_with_platform_charge(db, quote, [item])

    assert totals["total_amount"] == Decimal("500")
    assert totals["customer_payable_amount"] == Decimal("550.00")
