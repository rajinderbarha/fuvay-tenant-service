"""End-to-end service lifecycle certification for every mutable Finance tab.

The fixture binds a session to an outer database transaction.  Services may
flush or commit exactly as production does, while the outer transaction is
rolled back after each test so certification records never pollute the shared
development database.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import create_test_engine
from app.engines.complaints.models import CustomerComplaint, RefundRequest
from app.engines.complaints.refund_service import RefundRequestService
from app.engines.finance_hub.models import CreditTopupOrder
from app.engines.finance_hub.home_services_finance_service import HomeServicesFinanceService
from app.engines.finance_hub.service import FinanceHubService
from app.engines.platform_commerce.models import WarrantyClaim
from app.engines.platform_commerce.service import CommerceService
from app.engines.tenant_engine.models import Tenant, TenantBilling, UsageCreditLedger
from app.engines.usage_credits.service import UsageCreditService
from app.exceptions import ServiceOSException


pytestmark = pytest.mark.anyio


@pytest_asyncio.fixture
async def tx_db():
    engine = create_test_engine()
    connection = await engine.connect()
    outer = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False, autoflush=False)
    try:
        yield session
    finally:
        await session.close()
        if outer.is_active:
            await outer.rollback()
        await connection.close()
        await engine.dispose()


async def _tenant(db: AsyncSession, suffix: str) -> Tenant:
    marker = f"{suffix}-{uuid.uuid4().hex[:10]}"
    tenant = Tenant(
        tenant_name=f"Finance certification {marker}",
        business_name=f"Finance certification {marker}",
        vertical="home_services",
        status="active",
        slug=f"finance-cert-{marker}",
        tenant_code=f"FC{uuid.uuid4().hex[:12]}",
    )
    db.add(tenant)
    await db.flush()
    return tenant


# The security deposit lifecycle test was removed with the feature itself in
# migration 317/318 (`SecurityDeposit` no longer exists). Its subject --
# money held against a tenant -- is now the credit balance, whose floor and
# warning thresholds are certified by the top-up and refund tests below.


async def test_topup_retry_and_partial_to_full_refund_lifecycle(tx_db: AsyncSession):
    tenant = await _tenant(tx_db, "topup")
    tx_db.add(TenantBilling(tenant_id=tenant.id, vertical_key="home_services", credit_balance=Decimal("0")))
    topup = CreditTopupOrder(
        tenant_id=tenant.id, order_ref=f"CERT-{uuid.uuid4().hex[:8]}",
        credits_purchased=Decimal("100"), bonus_credits=Decimal("10"),
        amount_paid=Decimal("118"), payment_status="paid_pending_credit",
        wallet_credit_status="pending",
    )
    tx_db.add(topup)
    await tx_db.flush()
    svc = FinanceHubService(tx_db, request_id="finance-certification")

    credited = await svc.retry_credit_posting(topup.id)
    assert credited["payment_status"] == "credited"
    billing = (await tx_db.execute(
        select(TenantBilling).where(TenantBilling.tenant_id == tenant.id)
    )).scalar_one()
    assert Decimal(str(billing.credit_balance)) == Decimal("110")
    with pytest.raises(ServiceOSException):
        await svc.retry_credit_posting(topup.id)

    partial = await svc.refund_topup(topup.id, Decimal("50"), "partial customer-approved refund")
    assert partial["payment_status"] == "partially_refunded"
    assert Decimal(str(partial["credits_revoked"])) == Decimal("46.61")
    completed = await svc.refund_topup(topup.id, Decimal("68"), "remaining customer-approved refund")
    assert completed["payment_status"] == "refunded"
    assert Decimal(str(completed["credits_revoked"])) == Decimal("63.39")
    await tx_db.refresh(billing)
    assert Decimal(str(billing.credit_balance)) == Decimal("0")
    reversals = (await tx_db.execute(select(UsageCreditLedger).where(
        UsageCreditLedger.tenant_id == tenant.id,
        UsageCreditLedger.event_type == "topup_credit_refunded",
    ))).scalars().all()
    assert [Decimal(str(row.credit_delta)) for row in reversals] == [Decimal("-46.61"), Decimal("-63.39")]
    with pytest.raises(ServiceOSException):
        await svc.refund_topup(topup.id, Decimal("1"), "over-refund")


async def test_manual_credit_adjustment_and_package_admin_lifecycles(tx_db: AsyncSession):
    tenant = await _tenant(tx_db, "credits")
    svc = HomeServicesFinanceService(tx_db, request_id="finance-certification")

    added = await svc.create_manual_adjustment(
        tenant_id=tenant.id, direction="credit", credit_units=Decimal("25"),
        reason_code="APPROVED_GOODWILL_ADJUSTMENT", detailed_reason="Certification credit",
        supporting_reference="CERT-CREDIT-1",
    )
    assert Decimal(str(added["credit_delta"])) == Decimal("25")
    removed = await svc.create_manual_adjustment(
        tenant_id=tenant.id, direction="debit", credit_units=Decimal("10"),
        reason_code="SERVICE_CREDIT_CORRECTION", detailed_reason="Certification correction",
        supporting_reference="CERT-DEBIT-1",
    )
    assert Decimal(str(removed["balance_after"])) == Decimal("15")
    with pytest.raises(ServiceOSException):
        await svc.create_manual_adjustment(
            tenant_id=tenant.id, direction="debit", credit_units=Decimal("16"),
            reason_code="SERVICE_CREDIT_CORRECTION", detailed_reason="Must not become negative",
        )

    commerce = CommerceService(tx_db)
    package = await commerce.create_package({
        "name": f"Certification {uuid.uuid4().hex[:8]}", "description": "Temporary",
        "credits_amount": "100", "price_inr": "118", "bonus_pct": "10", "sort_order": 999,
    })
    updated = await commerce.update_package(uuid.UUID(package["package_id"]), {"price_inr": Decimal("120")})
    assert Decimal(str(updated["price_inr"])) == Decimal("120")
    archived = await commerce.archive_package(uuid.UUID(package["package_id"]))
    assert archived["archived"] is True
    deleted = await commerce.delete_package_permanently(uuid.UUID(package["package_id"]))
    assert deleted["deleted"] is True


async def test_topup_refund_blocks_when_purchased_credits_were_consumed(tx_db: AsyncSession):
    tenant = await _tenant(tx_db, "spent-topup")
    tx_db.add(TenantBilling(tenant_id=tenant.id, vertical_key="home_services", credit_balance=Decimal("0")))
    topup = CreditTopupOrder(
        tenant_id=tenant.id, order_ref=f"CERT-{uuid.uuid4().hex[:8]}",
        credits_purchased=Decimal("50"), bonus_credits=Decimal("0"),
        amount_paid=Decimal("59"), payment_status="paid_pending_credit",
        wallet_credit_status="pending",
    )
    tx_db.add(topup)
    await tx_db.flush()
    finance = FinanceHubService(tx_db, request_id="finance-certification")
    await finance.retry_credit_posting(topup.id)
    credits = UsageCreditService(tx_db, request_id="finance-certification")
    await credits.adjust_credit(
        tenant_id=tenant.id, direction="debit", amount=Decimal("45"),
        reason_code="correction", reason="Simulate credits already consumed",
        idempotency_key=f"cert-spend:{topup.id}",
    )

    with pytest.raises(ServiceOSException):
        await finance.refund_topup(topup.id, Decimal("59"), "full refund after usage")
    await tx_db.refresh(topup)
    assert topup.payment_status == "credited"
    assert Decimal(str(topup.refunded_amount or 0)) == Decimal("0")
