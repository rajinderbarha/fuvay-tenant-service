from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pathlib
import uuid

import pytest

from app.engines.execution.home_services_dashboard_service import _credit_thresholds
from app.engines.vertical_monetization.policy_service import VerticalMonetizationPolicyService


ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.mark.asyncio
async def test_dashboard_uses_published_credit_thresholds():
    result = MagicMock()
    result.fetchone.return_value = SimpleNamespace(
        credit_warning_threshold=750,
        credit_booking_floor=500,
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    assert await _credit_thresholds(db) == (750.0, 500.0)


@pytest.mark.asyncio
async def test_saving_reuses_latest_draft_and_repairs_older_duplicate():
    vertical = SimpleNamespace(id=uuid.uuid4())
    latest = MagicMock()
    latest.to_dict.side_effect = [
        {"provider_model": "NONE"},
        {"provider_model": "PERCENTAGE_COMMISSION"},
        {"provider_model": "PERCENTAGE_COMMISSION"},
    ]
    stale = SimpleNamespace(status="draft")
    rows = MagicMock()
    rows.scalars.return_value.all.return_value = [latest, stale]
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[MagicMock(), rows])
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()

    service = VerticalMonetizationPolicyService()
    with patch.object(service, "_vertical", new=AsyncMock(return_value=vertical)):
        saved = await service.save_draft(
            db, "home_services",
            {"provider_model": "PERCENTAGE_COMMISSION", "provider_percentage": "10",
             "customer_fee_model": "NONE"},
            actor_id=None,
        )

    assert saved["provider_model"] == "PERCENTAGE_COMMISSION"
    assert latest.provider_model == "PERCENTAGE_COMMISSION"
    assert stale.status == "superseded"
    db.commit.assert_awaited_once()


def test_home_services_admin_exposes_one_direct_payment_platform_charge_flow():
    router = (ROOT / "app/engines/vertical_monetization/home_services_finance_router.py").read_text(encoding="utf-8-sig")
    page = (ROOT / "frontend/super-admin/app/admin/home-services/finance/page.tsx").read_text(encoding="utf-8-sig")
    dashboard = (ROOT / "frontend/tenant-portal/app/(tenant)/dashboard/page.tsx").read_text(encoding="utf-8-sig")

    assert 'body["collection_stage"] = "on_completion"' in router
    assert "When to collect from the customer" not in page
    assert "Customer pays provider" in page
    assert "Platform charge (%)" in page
    assert "This notice remains until your balance is above" in dashboard
    assert "onDismiss" not in dashboard[dashboard.index("finance.low_credit"):dashboard.index("finance.low_credit") + 1400]
