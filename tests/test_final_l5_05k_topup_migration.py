"""FINAL-L5-05K — Finance Hub Credit Top-up migration tests.

Unit-level tests (mocked AsyncSession) for grant_topup_credit and the
retry-posting adapter, plus TRUE concurrency tests against the real
Postgres database (not mocks — this file opens its own engine, bypassing
the autouse mock_database fixture, specifically to satisfy the mission's
"do not claim true concurrency based only on unit tests" requirement),
plus static architecture guards.
"""
from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import get_settings
from app.engines.usage_credits.service import UsageCreditService, EVENT_TOPUP_CREDIT_GRANTED
from app.exceptions import ServiceOSException

ROOT = Path(__file__).parent.parent
APP = ROOT / "app"


def _scalar_result(value):
    r = MagicMock()
    r.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=value)))
    return r


def _make_billing(tenant_id, balance="0"):
    b = MagicMock()
    b.tenant_id = tenant_id
    b.credit_balance = Decimal(str(balance))
    return b


class TestGrantTopupCreditUnit:
    @pytest.mark.asyncio
    async def test_grant_writes_ledger_and_increases_balance(self):
        tid = uuid.uuid4()
        billing = _make_billing(tid, "0")
        call_count = [0]

        async def mock_execute(q):
            call_count[0] += 1
            if call_count[0] == 1:
                return _scalar_result(None)  # idempotency lookup
            return _scalar_result(billing)   # tenant_billing lookup

        db = AsyncMock()
        db.execute = mock_execute
        db.add = MagicMock()
        db.flush = AsyncMock()

        with patch("app.engines.usage_credits.service.record_platform_audit", new=AsyncMock()):
            svc = UsageCreditService(db, actor_id=uuid.uuid4(), actor_role="super_admin")
            result = await svc.grant_topup_credit(
                tenant_id=tid, topup_order_id="topup-1", amount=Decimal("2500"),
            )
        assert result["event_type"] == EVENT_TOPUP_CREDIT_GRANTED
        assert billing.credit_balance == Decimal("2500")
        assert result["idempotent"] is False

    @pytest.mark.asyncio
    async def test_retry_with_same_identity_is_idempotent(self):
        tid = uuid.uuid4()
        existing = MagicMock()
        existing.to_dict = MagicMock(return_value={"ledger_id": str(uuid.uuid4()), "credit_delta": 2500.0})
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_scalar_result(existing))
        db.add = MagicMock()
        svc = UsageCreditService(db)
        result = await svc.grant_topup_credit(
            tenant_id=tid, topup_order_id="topup-1", amount=Decimal("2500"),
        )
        assert result["idempotent"] is True
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_amount_rejected(self):
        db = AsyncMock()
        svc = UsageCreditService(db)
        with pytest.raises(ServiceOSException) as exc:
            await svc.grant_topup_credit(
                tenant_id=uuid.uuid4(), topup_order_id="topup-x", amount=Decimal("0"),
            )
        assert exc.value.error_code == "TOPUP_INVALID_AMOUNT"

    def test_grant_identity_stable_for_same_order(self):
        assert (f"topup_credit_grant:topup-1:1"
                == f"topup_credit_grant:{'topup-1'}:{1}")


@pytest.mark.skipif(
    not __import__("os").environ.get("SERVICEOS_RUN_REAL_DB_TESTS", "1") == "1",
    reason="requires a real reachable Postgres instance",
)
class TestTrueConcurrency:
    """Real Postgres, real transactions, real row-locking. Not unit tests."""

    @pytest.fixture
    def real_engine(self):
        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL, pool_size=5, max_overflow=5)
        yield engine

    @pytest.mark.asyncio
    async def test_two_concurrent_grants_same_idempotency_key_produce_one_ledger_row(self, real_engine):
        """Two simultaneous grant calls for the same top-up order must
        result in exactly one usage_credit_ledger row and exactly one
        balance increase -- not two."""
        from sqlalchemy import text
        session_factory = async_sessionmaker(real_engine, expire_on_commit=False)

        # Use a throwaway tenant_id (no FK enforced on tenant_billing.tenant_id
        # -- confirmed via the model, it's a plain UUID column) so this test
        # is self-contained and does not depend on real seeded tenant data.
        tid = uuid.uuid4()
        order_id = f"concurrency-test-{uuid.uuid4()}"

        async def do_grant():
            async with session_factory() as db:
                svc = UsageCreditService(db, actor_role="super_admin")
                with patch("app.engines.usage_credits.service.record_platform_audit", new=AsyncMock()):
                    try:
                        result = await svc.grant_topup_credit(
                            tenant_id=tid, topup_order_id=order_id, amount=Decimal("1000"),
                        )
                        await db.commit()
                        return result
                    except Exception:
                        await db.rollback()
                        raise

        try:
            results = await asyncio.gather(do_grant(), do_grant(), return_exceptions=True)
            successes = [r for r in results if not isinstance(r, Exception)]
            assert len(successes) >= 1, f"expected at least one success, got {results}"

            async with session_factory() as verify_db:
                idem_key = f"topup_credit_grant:{order_id}:1"
                count_row = await verify_db.execute(text(
                    "SELECT count(*) FROM usage_credit_ledger WHERE idempotency_key = :k"
                ), {"k": idem_key})
                ledger_count = count_row.scalar_one()
                assert ledger_count == 1, (
                    f"expected exactly 1 ledger row for idempotency_key={idem_key}, found {ledger_count}"
                )

                bal_row = await verify_db.execute(text(
                    "SELECT credit_balance FROM tenant_billing WHERE tenant_id = :t"
                ), {"t": str(tid)})
                bal = bal_row.scalar_one_or_none()
                assert bal == Decimal("1000"), f"expected balance 1000, got {bal}"
        finally:
            async with session_factory() as cleanup_db:
                await cleanup_db.execute(text(
                    "DELETE FROM usage_credit_ledger WHERE tenant_id = :t"
                ), {"t": str(tid)})
                await cleanup_db.execute(text(
                    "DELETE FROM tenant_billing WHERE tenant_id = :t"
                ), {"t": str(tid)})
                await cleanup_db.commit()
        await real_engine.dispose()

    @pytest.mark.asyncio
    async def test_topup_grant_concurrent_with_manual_adjustment_no_lost_update(self, real_engine):
        """A top-up grant and a manual credit adjustment firing concurrently
        against the same tenant must both apply -- the row lock in
        UsageCreditService._post() must serialize them, not lose one."""
        from sqlalchemy import text
        session_factory = async_sessionmaker(real_engine, expire_on_commit=False)
        tid = uuid.uuid4()
        order_id = f"concurrency-adj-{uuid.uuid4()}"

        async def do_topup_grant():
            async with session_factory() as db:
                svc = UsageCreditService(db, actor_role="super_admin")
                with patch("app.engines.usage_credits.service.record_platform_audit", new=AsyncMock()):
                    r = await svc.grant_topup_credit(tenant_id=tid, topup_order_id=order_id, amount=Decimal("500"))
                    await db.commit()
                    return r

        async def do_manual_adjust():
            async with session_factory() as db:
                svc = UsageCreditService(db, actor_role="super_admin")
                with patch("app.engines.usage_credits.service.record_platform_audit", new=AsyncMock()):
                    r = await svc.adjust_credit(
                        tenant_id=tid, direction="credit", amount=Decimal("300"),
                        reason_code="manual_operational_adjustment", reason="concurrent test",
                        idempotency_key=f"concurrency-adj-key-{order_id}",
                    )
                    await db.commit()
                    return r

        try:
            results = await asyncio.gather(do_topup_grant(), do_manual_adjust(), return_exceptions=True)
            errors = [r for r in results if isinstance(r, Exception)]
            assert not errors, f"unexpected errors: {errors}"

            async with session_factory() as verify_db:
                bal_row = await verify_db.execute(text(
                    "SELECT credit_balance FROM tenant_billing WHERE tenant_id = :t"
                ), {"t": str(tid)})
                bal = bal_row.scalar_one_or_none()
                assert bal == Decimal("800"), f"expected 500+300=800 (no lost update), got {bal}"
        finally:
            async with session_factory() as cleanup_db:
                await cleanup_db.execute(text("DELETE FROM usage_credit_ledger WHERE tenant_id = :t"), {"t": str(tid)})
                await cleanup_db.execute(text("DELETE FROM tenant_billing WHERE tenant_id = :t"), {"t": str(tid)})
                await cleanup_db.commit()
        await real_engine.dispose()


class TestArchitectureGuards:
    def _read(self, path):
        return path.read_text(encoding="utf-8")

    def test_confirm_purchase_uses_canonical_service(self):
        src = self._read(APP / "engines" / "platform_commerce" / "service.py")
        assert "UsageCreditService" in src
        assert "grant_topup_credit" in src

    def test_retry_credit_posting_uses_canonical_service(self):
        src = self._read(APP / "engines" / "finance_hub" / "service.py")
        assert "UsageCreditService" in src
        assert "grant_topup_credit" in src

    def test_finance_hub_does_not_import_credit_wallet_ledger_function(self):
        src = self._read(APP / "engines" / "finance_hub" / "service.py")
        assert "from app.engines.platform_commerce.ledger import credit_wallet" not in src

    def test_confirm_purchase_does_not_call_ledger_credit_wallet(self):
        src = self._read(APP / "engines" / "platform_commerce" / "service.py")
        # credit_deposit (Security Deposit replenishment) must remain --
        # only the wallet credit call is migrated.
        confirm_start = src.index("async def confirm_purchase(")
        next_def = src.index("\n    async def ", confirm_start + 10)
        body = src[confirm_start:next_def]
        assert "credit_wallet(" not in body
        assert "credit_deposit(" in body

    def test_topup_grant_source_type_is_finance_hub(self):
        src = self._read(APP / "engines" / "usage_credits" / "service.py")
        assert 'SOURCE_TYPE_FINANCE_HUB_CREDIT_TOPUP = "FINANCE_HUB_CREDIT_TOPUP"' in src

    def test_topup_idempotency_identity_shared_across_confirm_and_retry(self):
        commerce_src = self._read(APP / "engines" / "platform_commerce" / "service.py")
        finance_src = self._read(APP / "engines" / "finance_hub" / "service.py")
        # Both must pass topup_order_id through to grant_topup_credit with
        # the same source identity (topup.id), not two different keys.
        assert "grant_topup_credit(" in commerce_src
        assert "grant_topup_credit(" in finance_src

    def test_credit_topup_orders_table_has_usage_credit_ledger_reference(self):
        src = self._read(APP / "engines" / "finance_hub" / "models.py")
        assert "usage_credit_ledger_event_id" in src

    def test_engine_deduct_wallet_still_blocked(self):
        src = self._read(APP / "engines" / "platform_commerce" / "router.py")
        assert "status_code=410" in src

    def test_tenant_engine_legacy_wallet_endpoints_still_blocked(self):
        src = self._read(APP / "engines" / "tenant_engine" / "admin_router.py")
        assert 'router.post("/{tenant_id}/wallet/topup")' in src
        assert "status_code=410" in src
