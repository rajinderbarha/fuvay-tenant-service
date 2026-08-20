"""Provider commission rate resolution — the single live authority.

Fixes a real bug found in the Home Services finance audit: Super Admin's
Monetization workspace (VerticalMonetizationPolicy.provider_percentage) let
an admin configure and "publish" a PERCENTAGE_COMMISSION policy that had
ZERO runtime effect, because ServiceCommissionService._resolve_rate only
ever read ServiceCategory.commission_pct. resolve_provider_commission_rate
is now the one function both the live invoice pipeline and the tenant
Finance Readiness onboarding step call, so they can never disagree.
"""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.invoice_payment.commission_service import resolve_provider_commission_rate
from app.engines.invoice_payment.constants import DEFAULT_COMMISSION_RATE


def _result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


class _Category:
    def __init__(self, commission_pct=None, vertical_type="home_services"):
        self.commission_pct = commission_pct
        self.vertical_type = vertical_type


class _Vertical:
    def __init__(self, id="vert-1"):
        self.id = id


class _Policy:
    def __init__(self, provider_model, provider_percentage):
        self.provider_model = provider_model
        self.provider_percentage = provider_percentage


@pytest.mark.asyncio
class TestCommissionRateResolution:
    async def test_no_category_id_falls_back_to_platform_default(self):
        db = AsyncMock()
        rate = await resolve_provider_commission_rate(db, None)
        assert rate == Decimal(str(DEFAULT_COMMISSION_RATE))
        db.execute.assert_not_called()

    async def test_unknown_category_falls_back_to_platform_default(self):
        db = AsyncMock()
        db.execute.return_value = _result(None)
        rate = await resolve_provider_commission_rate(db, "cat-missing")
        assert rate == Decimal(str(DEFAULT_COMMISSION_RATE))

    async def test_category_override_takes_precedence_over_published_default(self):
        db = AsyncMock()
        db.execute.side_effect = [
            _result(_Category(commission_pct=Decimal("12.00"), vertical_type="coaching")),
            _result(_Vertical()),
            _result(_Policy("PERCENTAGE_COMMISSION", Decimal("18.500"))),
        ]
        rate = await resolve_provider_commission_rate(db, "cat-1")
        assert rate == Decimal("12.00")

    async def test_other_published_provider_model_disables_percentage_commission(self):
        db = AsyncMock()
        db.execute.side_effect = [
            _result(_Category(commission_pct=Decimal("12.00"))),
            _result(_Vertical()),
            _result(_Policy("COMPLETION_CREDITS", None)),
        ]
        rate = await resolve_provider_commission_rate(db, "cat-1")
        assert rate == Decimal("0")

    async def test_published_percentage_default_applies_when_category_has_no_override(self):
        db = AsyncMock()
        db.execute.side_effect = [
            _result(_Category(commission_pct=None)),
            _result(_Vertical()),
            _result(_Policy("PERCENTAGE_COMMISSION", Decimal("18.500"))),
        ]
        rate = await resolve_provider_commission_rate(db, "cat-1")
        assert rate == Decimal("18.500")

    async def test_no_current_policy_falls_back_to_category_override(self):
        db = AsyncMock()
        db.execute.side_effect = [
            _result(_Category(commission_pct=Decimal("7.50"), vertical_type="coaching")),
            _result(_Vertical()),
            _result(None),
        ]
        rate = await resolve_provider_commission_rate(db, "cat-1")
        assert rate == Decimal("7.50")

    async def test_no_category_override_and_no_policy_falls_back_to_platform_default(self):
        db = AsyncMock()
        db.execute.side_effect = [
            _result(_Category(commission_pct=None, vertical_type="coaching")),
            _result(_Vertical()),
            _result(None),
        ]
        rate = await resolve_provider_commission_rate(db, "cat-1")
        assert rate == Decimal(str(DEFAULT_COMMISSION_RATE))

    async def test_home_services_ignores_category_override(self):
        db = AsyncMock()
        db.execute.side_effect = [
            _result(_Category(commission_pct=Decimal("99.00"), vertical_type="home_services")),
            _result(_Vertical()),
            _result(_Policy("PERCENTAGE_COMMISSION", Decimal("8.50"))),
        ]
        rate = await resolve_provider_commission_rate(db, "cat-1")
        assert rate == Decimal("8.50")

    async def test_home_services_without_published_policy_charges_zero(self):
        db = AsyncMock()
        db.execute.side_effect = [
            _result(_Category(commission_pct=Decimal("99.00"), vertical_type="home_services")),
            _result(_Vertical()),
            _result(None),
        ]
        rate = await resolve_provider_commission_rate(db, "cat-1")
        assert rate == Decimal("0")

    async def test_category_without_vertical_type_skips_policy_lookup(self):
        db = AsyncMock()
        db.execute.side_effect = [
            _result(_Category(commission_pct=Decimal("9.00"), vertical_type=None)),
        ]
        rate = await resolve_provider_commission_rate(db, "cat-1")
        assert rate == Decimal("9.00")
        assert db.execute.call_count == 1
