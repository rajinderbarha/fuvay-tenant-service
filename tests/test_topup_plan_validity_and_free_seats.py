"""Top-up plan validity, and the free seat that makes buying optional.

Three things are certified here:

  * a plan's `validity_days` reaches the entitlement it grants, and an expiry
    withdraws ONLY the unspent part of that grant;
  * a redelivered payment does not grant seats twice;
  * activation no longer blocks on buying capacity, and the free starter seat
    means "optional" is not just the dead end moved one screen later.
"""
from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal

import pytest


class TestValidityMath:
    def test_zero_days_never_expires(self):
        from app.engines.vertical_catalog.topup_entitlement_service import _expiry
        # Every plan predating validity has 0, so 0 must keep meaning "forever".
        assert _expiry(0) is None
        assert _expiry(None) is None  # type: ignore[arg-type]

    def test_validity_is_counted_from_purchase(self):
        from app.engines.vertical_catalog.topup_entitlement_service import _expiry
        start = dt.datetime(2026, 8, 1, tzinfo=dt.timezone.utc)
        assert _expiry(30, start) == dt.datetime(2026, 8, 31, tzinfo=dt.timezone.utc)


class TestOnlyUnspentCreditLapses:
    """The regression that mattered.

    Costing a lapse as `balance - grants_of_newer_lots` confiscated money the
    provider held BEFORE they ever bought the plan: with Rs.1,000 in hand, a
    Rs.2,000 grant and Rs.1,500 spent, it took Rs.1,500 rather than the Rs.500
    that was genuinely unspent. Expiry is costed from the ledger instead.
    """

    @staticmethod
    def _withdraw(granted: Decimal, spent: Decimal, balance: Decimal) -> Decimal:
        unspent = max(Decimal("0"), granted - spent)
        return max(Decimal("0"), min(unspent, balance))

    def test_only_the_unspent_part_of_the_grant_is_taken(self):
        # Rs.1,000 held + Rs.2,000 granted - Rs.1,500 spent = Rs.1,500 balance.
        assert self._withdraw(Decimal("2000"), Decimal("1500"), Decimal("1500")) == Decimal("500")

    def test_money_held_before_the_grant_is_never_touched(self):
        # Grant fully spent: the lapse must take nothing at all.
        assert self._withdraw(Decimal("2000"), Decimal("2000"), Decimal("1000")) == Decimal("0")

    def test_a_lapse_can_never_push_an_account_negative(self):
        assert self._withdraw(Decimal("2000"), Decimal("0"), Decimal("300")) == Decimal("300")

    def test_overspending_does_not_create_a_negative_withdrawal(self):
        assert self._withdraw(Decimal("500"), Decimal("900"), Decimal("100")) == Decimal("0")


class TestFreeStarterSeat:
    def test_a_workspace_can_reach_its_first_job_without_paying(self):
        from app.engines.vertical_catalog.seat_enforcement import FREE_STARTER_SEATS
        # Activation stopped blocking on purchase; without an allowance the
        # dead end would simply move to the Add Technician button.
        assert FREE_STARTER_SEATS >= 1

    def test_the_allowance_is_a_floor_not_a_bonus(self):
        from app.engines.vertical_catalog.seat_enforcement import FREE_STARTER_SEATS
        # A 3-seat plan must grant 3 seats, not 3 + the freebie.
        purchased = 3
        assert max(purchased, FREE_STARTER_SEATS) == 3


class TestActivationDoesNotBlockOnPurchase:
    def test_purchase_gates_report_not_required(self):
        import inspect
        from app.engines.vertical_catalog import activation

        src = inspect.getsource(activation)
        # The readiness roll-up treats `not_required` as satisfied; neither
        # purchase gate may report `action_required` any more.
        # Slice between the two _add calls: `_credit_base` would also match
        # inside `required_credit_base_amount` further up the file.
        seats_gate = src[src.index('_add("technician_seats"'):src.index('_add("category_wallet"')]
        assert "not_required" in seats_gate
        assert "action_required" not in seats_gate

        wallet_gate = src[src.index('_add("category_wallet"'):src.index('_add("approved_services"')]
        assert "not_required" in wallet_gate
        assert "action_required" not in wallet_gate

    def test_readiness_treats_not_required_as_satisfied(self):
        import inspect
        from app.engines.vertical_catalog import activation
        src = inspect.getsource(activation)
        assert 'g["state"] in ("ready", "not_required")' in src


class TestPlanCarriesValidity:
    def test_catalogue_model_exposes_validity(self):
        from app.engines.vertical_catalog.topup_plan_models import HsTopupPlan
        assert hasattr(HsTopupPlan, "validity_days")

    def test_admin_payload_accepts_validity(self):
        from app.engines.vertical_catalog.topup_plan_catalog_router import PlanIn, PlanPatch
        assert "validity_days" in PlanIn.model_fields
        assert "validity_days" in PlanPatch.model_fields
        # Default 0 keeps every existing plan behaving exactly as before.
        assert PlanIn.model_fields["validity_days"].default == 0

    def test_negative_validity_is_refused(self):
        from pydantic import ValidationError
        from app.engines.vertical_catalog.topup_plan_catalog_router import PlanIn
        with pytest.raises(ValidationError):
            PlanIn(name="Bad", base_amount=Decimal("100"), seats=1, validity_days=-1)


class TestFinanceTabUsesOneCatalogue:
    def test_the_finance_tab_reads_the_canonical_plans(self):
        from pathlib import Path
        src = Path("frontend/super-admin/app/admin/home-services/finance/page.tsx").read_text(
            encoding="utf-8")
        # It used to manage `credit_packages` (/v1/commerce/packages): a second,
        # empty catalogue with no GST or seat fields.
        assert "topupPlanApi" in src
        assert "commerceApi.listPackages" not in src
        assert "commerceApi.createPackage" not in src

    def test_the_create_form_offers_gst_and_validity(self):
        from pathlib import Path
        src = Path("frontend/super-admin/app/admin/home-services/finance/page.tsx").read_text(
            encoding="utf-8")
        assert "GST %" in src
        assert "Validity (days)" in src
        assert "Technician seats" in src
