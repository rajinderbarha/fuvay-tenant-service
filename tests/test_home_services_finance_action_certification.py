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
from app.engines.platform_commerce.models import SecurityDeposit, WarrantyClaim
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


async def test_security_deposit_complete_action_lifecycle(tx_db: AsyncSession):
    svc = FinanceHubService(tx_db, request_id="finance-certification")

    payment_tenant = await _tenant(tx_db, "deposit-payment")
    deposit = SecurityDeposit(tenant_id=payment_tenant.id, required_amount=Decimal("100"))
    tx_db.add(deposit)
    await tx_db.flush()

    partial = await svc.record_offline_deposit(deposit.id, Decimal("40"), "cert-ref-1", "partial")
    assert partial["status"] == "partially_paid"
    await tx_db.flush()
    duplicate = await svc.record_offline_deposit(deposit.id, Decimal("40"), "cert-ref-1", "duplicate")
    assert duplicate["idempotent"] is True
    paid = await svc.record_offline_deposit(deposit.id, Decimal("60"), "cert-ref-2", "remainder")
    assert paid["status"] == "paid" and paid["current_balance"] == 100

    adjusted = await svc.adjust_deposit(deposit.id, Decimal("-10"), "approved forfeiture")
    assert adjusted["status"] == "partially_adjusted" and adjusted["current_balance"] == 90
    refunded = await svc.refund_deposit(deposit.id, Decimal("90"), "workspace closed")
    assert refunded["status"] == "refunded" and refunded["current_balance"] == 0
    with pytest.raises(ServiceOSException):
        await svc.refund_deposit(deposit.id, Decimal("1"), "duplicate")

    approval_tenant = await _tenant(tx_db, "deposit-approval")
    pending = SecurityDeposit(
        tenant_id=approval_tenant.id, required_amount=Decimal("100"),
        total_paid=Decimal("100"), status="pending_verification",
    )
    tx_db.add(pending)
    await tx_db.flush()
    approved = await svc.approve_deposit(pending.id, "bank proof verified")
    assert approved["status"] == "paid" and approved["hold_state"] == "held"

    rejection_tenant = await _tenant(tx_db, "deposit-rejection")
    rejected_row = SecurityDeposit(
        tenant_id=rejection_tenant.id, required_amount=Decimal("100"),
        total_paid=Decimal("100"), status="pending_verification",
    )
    tx_db.add(rejected_row)
    await tx_db.flush()
    rejected = await svc.reject_deposit(rejected_row.id, "unverifiable reference")
    assert rejected["status"] == "rejected"


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


async def test_warranty_assign_documents_decide_and_settle_lifecycle(tx_db: AsyncSession):
    tenant = await _tenant(tx_db, "warranty")
    deposit = SecurityDeposit(
        tenant_id=tenant.id, required_amount=Decimal("500"),
        total_paid=Decimal("500"), status="paid", hold_state="held",
    )
    billing = TenantBilling(tenant_id=tenant.id, vertical_key="home_services", credit_balance=Decimal("200"))
    claim = WarrantyClaim(
        tenant_id=tenant.id, job_id=str(uuid.uuid4()), customer_id=uuid.uuid4(),
        claim_type="service_quality", description="Certification claim",
        amount_requested=Decimal("100"), status="admin_review",
    )
    rejected_claim = WarrantyClaim(
        tenant_id=tenant.id, job_id=str(uuid.uuid4()), customer_id=uuid.uuid4(),
        claim_type="service_quality", description="Certification rejection",
        amount_requested=Decimal("50"), status="admin_review",
    )
    tx_db.add_all([deposit, billing, claim, rejected_claim])
    await tx_db.flush()
    svc = FinanceHubService(tx_db, request_id="finance-certification")

    assigned = await svc.assign_reviewer(claim.id, uuid.uuid4())
    assert assigned["status"] == "admin_review"
    documents = await svc.request_documents(claim.id, "Provide diagnostic report")
    assert documents["status"] == "admin_review"
    approved = await svc.approve_claim(claim.id, Decimal("80"), "evidence accepted")
    assert approved["status"] == "credit_issued" and approved["amount_approved"] == 80
    await tx_db.refresh(claim)
    assert claim.settled_amount == Decimal("80")
    with pytest.raises(ServiceOSException):
        await svc.settle_claim(claim.id)

    rejected = await svc.reject_claim(rejected_claim.id, "not covered", "policy exclusion")
    assert rejected["status"] == "rejected"


async def test_refund_approve_record_verify_and_reject_lifecycles(tx_db: AsyncSession):
    tenant = await _tenant(tx_db, "refund")
    customer_id = uuid.uuid4()
    complaint = CustomerComplaint(
        customer_id=customer_id, tenant_id=tenant.id, category_id=uuid.uuid4(),
        record_type="service_job", record_id=uuid.uuid4(), complaint_type="billing",
        status="open", description="Certification complaint",
    )
    rejection_complaint = CustomerComplaint(
        customer_id=customer_id, tenant_id=tenant.id, category_id=uuid.uuid4(),
        record_type="service_job", record_id=uuid.uuid4(), complaint_type="billing",
        status="open", description="Certification rejection complaint",
    )
    tx_db.add_all([complaint, rejection_complaint])
    await tx_db.flush()
    refund = RefundRequest(
        complaint_id=complaint.id, customer_id=customer_id, tenant_id=tenant.id,
            status="admin_review", refund_type="service_quality", requested_amount=Decimal("100"),
        reason="Certification refund",
    )
    rejected_refund = RefundRequest(
        complaint_id=rejection_complaint.id, customer_id=customer_id, tenant_id=tenant.id,
        status="admin_review", refund_type="service_quality", requested_amount=Decimal("50"),
        reason="Certification rejection",
    )
    tx_db.add_all([refund, rejected_refund])
    tx_db.add(TenantBilling(tenant_id=tenant.id, vertical_key="home_services", credit_balance=Decimal("200")))
    await tx_db.flush()
    svc = RefundRequestService()
    actor = uuid.uuid4()

    remedy = await svc.admin_issue_credit_remedy(tx_db, refund.id, actor, Decimal("80"), "provider failed resolution")
    assert remedy.status == "verified" and remedy.approved_amount == Decimal("80")
    assert remedy.resolution_method == "customer_service_credit"
    with pytest.raises(ServiceOSException):
        await svc.admin_approve_refund(tx_db, refund.id, actor, Decimal("80"))

    rejected = await svc.admin_reject_refund(tx_db, rejected_refund.id, actor, "not eligible")
    assert rejected.status == "rejected"


def test_finance_ui_reads_nested_action_status_and_exposes_review_states():
    from pathlib import Path

    src = Path("frontend/super-admin/app/admin/home-services/finance/page.tsx").read_text(encoding="utf-8")
    assert "const topup = (d?.topup ?? d)" in src
    assert "const deposit = (d?.deposit ?? d)" in src
    assert 'status === "partially_refunded"' in src
    assert "const adminAttention = Boolean(refund.admin_attention_required)" in src
    assert "const decisionAllowed = Boolean(claim.admin_attention_required)" in src
    assert "Issue service points" in src
    assert 'value: "pending_verification"' in src
