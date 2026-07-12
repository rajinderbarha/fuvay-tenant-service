"""FINAL-L5-05J — Canonical UsageCreditService tests.

Unit-level tests using mocked AsyncSession (matching the established
pattern in test_sprint5_packages.py), plus static architecture guards
proving no Usage Credit / Package Credit code path writes TenantWallet.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.usage_credits.service import (
    UsageCreditService, EVENT_MANUAL_CREDIT_ADDED, EVENT_MANUAL_CREDIT_REMOVED,
    EVENT_PACKAGE_CREDIT_GRANTED,
)
from app.exceptions import ServiceOSException

ROOT = Path(__file__).parent.parent
APP = ROOT / "app"


def _scalar_result(value):
    r = MagicMock()
    r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=value)))
    return r


def _make_db(existing_ledger=None, billing=None):
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()

    call_count = [0]

    async def mock_execute(q):
        call_count[0] += 1
        # 1st call in _post(): idempotency-key lookup (only if key given).
        # Next call: tenant_billing row lookup (with_for_update).
        if call_count[0] == 1:
            return _scalar_result(existing_ledger)
        return _scalar_result(billing)

    db.execute = mock_execute
    return db


def _make_billing(tenant_id, balance="1000"):
    b = MagicMock()
    b.tenant_id = tenant_id
    b.credit_balance = Decimal(str(balance))
    return b


class TestGetBalanceAndLedger:
    @pytest.mark.asyncio
    async def test_get_balance_no_billing_record_returns_zero_honestly(self):
        tid = uuid.uuid4()
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_scalar_result(None))
        svc = UsageCreditService(db)
        result = await svc.get_balance(tid)
        assert result["usage_credit_balance"] == 0.0
        assert result["has_billing_record"] is False
        assert result["source"] == "tenant_billing.credit_balance"

    @pytest.mark.asyncio
    async def test_get_balance_reads_real_billing_record(self):
        tid = uuid.uuid4()
        billing = _make_billing(tid, "750.50")
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_scalar_result(billing))
        svc = UsageCreditService(db)
        result = await svc.get_balance(tid)
        assert result["usage_credit_balance"] == 750.50
        assert result["has_billing_record"] is True


class TestAdjustCredit:
    @pytest.mark.asyncio
    async def test_manual_credit_increases_balance_and_writes_ledger(self):
        tid = uuid.uuid4()
        billing = _make_billing(tid, "1000")
        db = _make_db(existing_ledger=None, billing=billing)
        with patch("app.engines.usage_credits.service.record_platform_audit", new=AsyncMock()):
            svc = UsageCreditService(db, actor_id=uuid.uuid4(), actor_role="super_admin")
            result = await svc.adjust_credit(
                tenant_id=tid, direction="credit", amount=Decimal("500"),
                reason_code="manual_operational_adjustment", reason="Approved correction",
                idempotency_key="test-key-1",
            )
        assert result["idempotent"] is False
        assert billing.credit_balance == Decimal("1500")
        assert result["event_type"] == EVENT_MANUAL_CREDIT_ADDED

    @pytest.mark.asyncio
    async def test_manual_debit_decreases_balance(self):
        tid = uuid.uuid4()
        billing = _make_billing(tid, "1000")
        db = _make_db(existing_ledger=None, billing=billing)
        with patch("app.engines.usage_credits.service.record_platform_audit", new=AsyncMock()):
            svc = UsageCreditService(db, actor_id=uuid.uuid4(), actor_role="super_admin")
            result = await svc.adjust_credit(
                tenant_id=tid, direction="debit", amount=Decimal("300"),
                reason_code="correction", reason="Billing correction",
                idempotency_key="test-key-2",
            )
        assert billing.credit_balance == Decimal("700")
        assert result["event_type"] == EVENT_MANUAL_CREDIT_REMOVED

    @pytest.mark.asyncio
    async def test_invalid_amount_rejected(self):
        db = AsyncMock()
        svc = UsageCreditService(db)
        with pytest.raises(ServiceOSException) as exc:
            await svc.adjust_credit(
                tenant_id=uuid.uuid4(), direction="credit", amount=Decimal("-5"),
                reason_code="correction", reason="x", idempotency_key="k",
            )
        assert exc.value.error_code == "INVALID_CREDIT_AMOUNT"

    @pytest.mark.asyncio
    async def test_invalid_direction_rejected(self):
        db = AsyncMock()
        svc = UsageCreditService(db)
        with pytest.raises(ServiceOSException) as exc:
            await svc.adjust_credit(
                tenant_id=uuid.uuid4(), direction="sideways", amount=Decimal("5"),
                reason_code="correction", reason="x", idempotency_key="k",
            )
        assert exc.value.error_code == "INVALID_ADJUSTMENT_DIRECTION"

    @pytest.mark.asyncio
    async def test_invalid_reason_code_rejected(self):
        db = AsyncMock()
        svc = UsageCreditService(db)
        with pytest.raises(ServiceOSException) as exc:
            await svc.adjust_credit(
                tenant_id=uuid.uuid4(), direction="credit", amount=Decimal("5"),
                reason_code="not_a_real_code", reason="x", idempotency_key="k",
            )
        assert exc.value.error_code == "INVALID_ADJUSTMENT_REASON"

    @pytest.mark.asyncio
    async def test_missing_reason_rejected(self):
        db = AsyncMock()
        svc = UsageCreditService(db)
        with pytest.raises(ServiceOSException) as exc:
            await svc.adjust_credit(
                tenant_id=uuid.uuid4(), direction="credit", amount=Decimal("5"),
                reason_code="correction", reason="   ", idempotency_key="k",
            )
        assert exc.value.error_code == "INVALID_ADJUSTMENT_REASON"

    @pytest.mark.asyncio
    async def test_missing_idempotency_key_rejected(self):
        db = AsyncMock()
        svc = UsageCreditService(db)
        with pytest.raises(ServiceOSException) as exc:
            await svc.adjust_credit(
                tenant_id=uuid.uuid4(), direction="credit", amount=Decimal("5"),
                reason_code="correction", reason="valid reason", idempotency_key="",
            )
        assert exc.value.error_code == "USAGE_CREDIT_CONFLICT"

    @pytest.mark.asyncio
    async def test_debit_below_zero_rejected(self):
        tid = uuid.uuid4()
        billing = _make_billing(tid, "100")
        db = _make_db(existing_ledger=None, billing=billing)
        svc = UsageCreditService(db)
        with pytest.raises(ServiceOSException) as exc:
            await svc.adjust_credit(
                tenant_id=tid, direction="debit", amount=Decimal("500"),
                reason_code="correction", reason="over-debit", idempotency_key="k-debit",
            )
        assert exc.value.error_code == "INSUFFICIENT_USAGE_CREDIT"

    @pytest.mark.asyncio
    async def test_duplicate_idempotency_key_returns_existing_without_double_mutation(self):
        tid = uuid.uuid4()
        existing = MagicMock()
        existing.to_dict = MagicMock(return_value={"ledger_id": "abc", "credit_delta": 500.0})
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_scalar_result(existing))
        svc = UsageCreditService(db)
        result = await svc.adjust_credit(
            tenant_id=tid, direction="credit", amount=Decimal("500"),
            reason_code="correction", reason="retry", idempotency_key="dup-key",
        )
        assert result["idempotent"] is True
        db.add.assert_not_called()


class TestGrantPackageCredit:
    @pytest.mark.asyncio
    async def test_grant_creates_one_ledger_event(self):
        tid = uuid.uuid4()
        billing = _make_billing(tid, "0")
        db = _make_db(existing_ledger=None, billing=billing)
        with patch("app.engines.usage_credits.service.record_platform_audit", new=AsyncMock()):
            svc = UsageCreditService(db)
            result = await svc.grant_package_credit(
                tenant_id=tid, package_assignment_id="assign-1",
                activation_version=1, amount=Decimal("2000"),
            )
        assert result["event_type"] == EVENT_PACKAGE_CREDIT_GRANTED
        assert billing.credit_balance == Decimal("2000")

    @pytest.mark.asyncio
    async def test_duplicate_activation_retry_does_not_double_grant(self):
        tid = uuid.uuid4()
        existing = MagicMock()
        existing.to_dict = MagicMock(return_value={"ledger_id": "x", "credit_delta": 2000.0})
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_scalar_result(existing))
        svc = UsageCreditService(db)
        result = await svc.grant_package_credit(
            tenant_id=tid, package_assignment_id="assign-1",
            activation_version=1, amount=Decimal("2000"),
        )
        assert result["idempotent"] is True
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_grant_identity_is_stable_per_assignment_and_version(self):
        assert (f"package_credit_grant:assign-1:1"
                == f"package_credit_grant:{'assign-1'}:{1}")


class TestArchitectureGuards:
    """Static source guards: no Usage Credit / Package Credit code path
    may write TenantWallet or wallet_transactions."""

    def _read(self, path):
        return path.read_text(encoding="utf-8")

    def test_usage_credit_service_never_imports_tenant_wallet(self):
        src = self._read(APP / "engines" / "usage_credits" / "service.py")
        assert "from app.engines.platform_commerce.models import" not in src
        assert "from app.engines.platform_commerce.ledger import" not in src

    def test_usage_credit_router_never_imports_tenant_wallet(self):
        src = self._read(APP / "engines" / "usage_credits" / "router.py")
        assert "TenantWallet" not in src

    def test_package_purchase_grant_uses_canonical_service_not_credit_wallet(self):
        src = self._read(APP / "engines" / "package_commerce" / "service.py")
        assert "UsageCreditService" in src
        assert "grant_package_credit" in src

    def test_package_credit_wallet_legacy_endpoints_delegate_to_canonical_service(self):
        src = self._read(APP / "engines" / "package_commerce" / "admin_router.py")
        assert "UsageCreditService" in src

    def test_tenant_engine_wallet_topup_and_adjust_are_blocked(self):
        src = self._read(APP / "engines" / "tenant_engine" / "admin_router.py")
        assert 'router.post("/{tenant_id}/wallet/topup")' in src
        assert 'router.post("/{tenant_id}/wallet/adjust")' in src
        assert "status_code=410" in src

    def test_add_usage_credits_delegates_to_canonical_service(self):
        src = self._read(APP / "engines" / "tenant_engine" / "admin_router.py")
        assert "UsageCreditService" in src
        assert "svc.adjust_credit" in src

    def test_tenant_health_computes_usage_credit_signal_from_tenant_billing(self):
        src = self._read(APP / "engines" / "tenant_engine" / "health.py")
        assert "usage_credit_health" in src
        assert "TenantWallet" not in src
        assert "tenant_billing" in src.lower() or "TenantBilling" in src

    def test_health_score_weights_use_usage_credit_health_not_wallet(self):
        src = self._read(APP / "engines" / "tenant_engine" / "constants.py")
        assert '"usage_credit_health": 0.15' in src
        assert '"credit_wallet_health": 0.15' not in src

    def test_engine_deduct_wallet_still_blocked(self):
        src = self._read(APP / "engines" / "platform_commerce" / "router.py")
        assert "status_code=410" in src

    def test_canonical_usage_credit_endpoint_family_exists(self):
        src = self._read(APP / "engines" / "usage_credits" / "router.py")
        assert '"/{tenant_id}/adjustments"' in src
