"""Real-DB integration tests proving `HomeServiceFinalCreationService.
finalize()` produces correct ServiceBooking/ServiceJob lineage for the two
real, Guramrit-published, 140412-covered AC offerings this session's work
established: AC Gas Refilling (inspection/visit-fee pricing) and AC
Installation (fixed-price, tenant-priced).

Follows the same real-DB convention as
tests/test_140412_zipcode_offering_isolation.py (app.database.init_db() +
get_session_factory() against the actual configured DATABASE_URL) rather
than the fully-mocked convention in tests/test_sprint19_final_records.py
-- this is deliberately the stronger, real-foreign-key-holding version of
that existing mocked test, scoped to the two offerings this continuation's
mission calls out by name.

Each test constructs a real HomeServiceBookingDraft row already in
`ready_for_confirmation` status (mirroring exactly what the real
serviceability -> match-and-price -> confirm-price-choice ->
mark-ready-for-confirmation pipeline would have produced -- that live
pipeline itself is not re-exercised here, since it depends on real
technician/availability data not verified to exist in every dev DB; see
final report), then calls the real, unmocked `finalize()` and asserts on
the real ServiceBooking/ServiceJob rows it creates. Test data is cleaned
up in a `finally` block so this is safe to re-run against a real dev
database without leaving artifacts behind.
"""
import os
import uuid
from datetime import date, timedelta, timezone
from decimal import Decimal

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_INTEGRATION_TESTS") != "1",
    reason="requires PostgreSQL integration database",
)


ZIPCODE_140412 = "140412"


async def _get_db():
    from app.database import get_session_factory, init_db
    await init_db()
    factory = get_session_factory()
    return factory()


async def _live_context(db):
    """Resolve current catalog/provider/customer rows by stable business keys.

    Provider reset is a supported development workflow, so UUID constants in
    this certification test are invalid by design after a reset.
    """
    from sqlalchemy import select
    from app.engines.admin_catalog.models import MasterService, TenantService, TenantServiceType
    from app.engines.serviceability.models import CustomerAddress

    gas = (await db.execute(select(MasterService).where(
        MasterService.slug == "ac_gas_refill", MasterService.is_active.is_(True),
        MasterService.deleted_at.is_(None),
    ))).scalars().one()
    installation = (await db.execute(select(MasterService).where(
        MasterService.slug == "ac_installation", MasterService.is_active.is_(True),
        MasterService.deleted_at.is_(None),
    ))).scalars().one()
    gas_offering = (await db.execute(select(TenantService).where(
        TenantService.master_service_id == gas.id,
        TenantService.setup_status == "published",
        TenantService.is_active.is_(True), TenantService.is_enabled.is_(True),
        TenantService.deleted_at.is_(None),
    ))).scalars().one()
    installation_offering = (await db.execute(select(TenantService).where(
        TenantService.tenant_id == gas_offering.tenant_id,
        TenantService.master_service_id == installation.id,
        TenantService.setup_status == "published",
        TenantService.is_active.is_(True), TenantService.is_enabled.is_(True),
        TenantService.deleted_at.is_(None),
    ))).scalars().one()
    priced_type = (await db.execute(select(TenantServiceType).where(
        TenantServiceType.tenant_service_id == installation_offering.id,
        TenantServiceType.is_enabled.is_(True),
        TenantServiceType.tenant_min_price.is_not(None),
        TenantServiceType.tenant_max_price.is_not(None),
    ))).scalars().first()
    assert priced_type is not None
    address = (await db.execute(select(CustomerAddress).where(
        CustomerAddress.zipcode == ZIPCODE_140412,
        CustomerAddress.is_active.is_(True),
    ).order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at.desc()))).scalars().first()
    assert address is not None
    return {
        "customer_id": address.customer_id,
        "tenant_id": gas_offering.tenant_id,
        "category_id": gas.category_id,
        "gas_id": gas.id,
        "installation_id": installation.id,
        "installation_type_id": priced_type.service_type_id,
        "installation_price": float(priced_type.tenant_min_price),
    }


async def _resolve_job_type_context(db, master_service_id):
    from sqlalchemy import select
    from app.engines.admin_catalog.models import ServiceJobWorkflow

    workflow = (await db.execute(
        select(ServiceJobWorkflow).where(
            ServiceJobWorkflow.master_service_id == master_service_id,
            ServiceJobWorkflow.is_current.is_(True),
        )
    )).scalars().first()
    assert workflow is not None, (
        f"No current ServiceJobWorkflow for master_service {master_service_id} -- "
        "run scripts/setup_140412_home_services.py first."
    )
    return workflow.job_type_id, workflow.id


async def _make_ready_draft(db, context, *, offering_id, price_snapshot,
                            offering_type_id=None, address_snapshot=None):
    from app.engines.home_service_booking.models import HomeServiceBookingDraft

    job_type_id, workflow_id = await _resolve_job_type_context(db, offering_id)

    draft = HomeServiceBookingDraft(
        id=uuid.uuid4(),
        customer_id=context["customer_id"],
        category_id=context["category_id"],
        offering_id=offering_id,
        offering_type_id=offering_type_id,
        job_type_id=job_type_id,
        master_service_job_type_id=None,  # not read by finalize()/_validate_job_type_context
        service_job_workflow_id=workflow_id,
        selected_tenant_id=context["tenant_id"],
        status="ready_for_confirmation",
        customer_name="Test Customer",
        customer_phone="+918427744877",
        city="Bassi Pathana",
        zipcode=ZIPCODE_140412,
        address_snapshot=address_snapshot or {"address_line_1": "House 12", "city": "Bassi Pathana", "zipcode": ZIPCODE_140412},
        preferred_date=date.today() + timedelta(days=3),
        preferred_time_window="morning",
        price_snapshot=price_snapshot,
        issue_summary="Test finalization scenario",
    )
    db.add(draft)
    await db.flush()
    return draft


async def _cleanup(db, draft_id):
    """Delete every row this test created, in FK-safe order, so a real dev
    DB is left exactly as it was -- safe to re-run any number of times."""
    from sqlalchemy import text
    await db.rollback()  # discard anything not yet committed
    async with db.begin():
        await db.execute(text("DELETE FROM home_service_booking_draft_events WHERE draft_id = :id"), {"id": draft_id})
        await db.execute(text("DELETE FROM final_creation_audit_logs WHERE draft_id = :id"), {"id": draft_id})
        await db.execute(text("DELETE FROM customer_booking_confirmations WHERE draft_id = :id"), {"id": draft_id})
        booking_ids = (await db.execute(
            text("SELECT id FROM service_bookings WHERE draft_id = :id"), {"id": draft_id}
        )).scalars().all()
        for bid in booking_ids:
            await db.execute(text("DELETE FROM service_jobs WHERE booking_id = :bid"), {"bid": bid})
        await db.execute(text("DELETE FROM service_bookings WHERE draft_id = :id"), {"id": draft_id})
        await db.execute(text("DELETE FROM home_service_booking_drafts WHERE id = :id"), {"id": draft_id})


@pytest.mark.asyncio
async def test_ac_gas_refilling_finalization_lineage_and_inspection_pricing():
    """Repair/inspection-style offering: verifies real ServiceBooking +
    ServiceJob creation with correct lineage, AND that the price snapshot
    is inspection-only (a visit fee, never a predicted repair total) --
    the exact rule this mission's Phase 7 requires."""
    from app.engines.final_records.creation_service import HomeServiceFinalCreationService
    from app.engines.final_records.models import ServiceBooking, ServiceJob

    db = await _get_db()
    draft = None
    try:
        context = await _live_context(db)
        price_snapshot = {
            "pricing_model": "visit_fee_plus_quote",
            "visit_fee": 299.0,
            "requires_inspection_estimate": True,
            "note": "The technician will contact you and inspect the issue before providing a cost estimate.",
        }
        draft = await _make_ready_draft(db, context, offering_id=context["gas_id"], price_snapshot=price_snapshot)
        await db.commit()

        svc = HomeServiceFinalCreationService(db=db)
        result = await svc.finalize(draft_id=draft.id, customer_id=context["customer_id"])
        await db.commit()

        assert result["idempotent"] is False
        assert result["booking_number"].startswith("BK")
        assert result["job_number"].startswith("JOB")

        booking = await db.get(ServiceBooking, uuid.UUID(result["booking_id"]))
        assert booking is not None
        assert booking.customer_id == context["customer_id"]
        assert booking.tenant_id == context["tenant_id"]
        assert booking.category_id == context["category_id"]
        assert booking.offering_id == context["gas_id"]
        assert booking.zipcode == ZIPCODE_140412
        assert booking.draft_id == draft.id
        # Inspection pricing rule: a real visit fee, no predicted repair total.
        assert booking.price_snapshot["visit_fee"] == 299.0
        assert booking.price_snapshot["requires_inspection_estimate"] is True
        assert "predicted_total" not in booking.price_snapshot
        assert "repair_total" not in booking.price_snapshot

        job = await db.get(ServiceJob, uuid.UUID(result["job_id"]))
        assert job is not None
        assert job.booking_id == booking.id
        assert job.tenant_id == context["tenant_id"]
        assert job.offering_id == context["gas_id"]
        assert job.zipcode == ZIPCODE_140412
        assert job.job_type_id == booking.job_type_id

        # Duplicate confirmation: idempotent, no second booking/job.
        result2 = await svc.finalize(draft_id=draft.id, customer_id=context["customer_id"])
        assert result2["idempotent"] is True
        assert result2["booking_number"] == result["booking_number"]

        from sqlalchemy import select, func
        booking_count = (await db.execute(
            select(func.count()).select_from(ServiceBooking).where(ServiceBooking.draft_id == draft.id)
        )).scalar_one()
        assert booking_count == 1, "Duplicate confirmation must never create a second ServiceBooking."
    finally:
        if draft is not None:
            await _cleanup(db, draft.id)
        await db.close()


@pytest.mark.asyncio
async def test_ac_installation_finalization_lineage_and_tenant_pricing():
    """Fixed-price offering: verifies real ServiceBooking + ServiceJob
    creation with correct lineage, AND that the price snapshot reflects
    Guramrit's own tenant pricing (never an admin catalog price or a
    fabricated LLM price)."""
    from app.engines.final_records.creation_service import HomeServiceFinalCreationService
    from app.engines.final_records.models import ServiceBooking, ServiceJob

    db = await _get_db()
    draft = None
    try:
        context = await _live_context(db)
        tenant_price = context["installation_price"]

        price_snapshot = {
            "pricing_model": "fixed",
            "standard_price": tenant_price,
            "note": f"Tenant-set price (guramrit_tenant_service).",
            "selected_price_option": "standard",
            "selected_price_amount": tenant_price,
        }
        draft = await _make_ready_draft(
            db, context, offering_id=context["installation_id"],
            offering_type_id=context["installation_type_id"], price_snapshot=price_snapshot,
        )
        # finalize() reads selected_price_tier/customer_offer from
        # draft.booking_summary (set by the real confirm_price_choice step)
        # to build the booking's own price_snapshot -- must mirror that
        # here or it silently overwrites with None.
        draft.booking_summary = {"selected_price_tier": "standard", "customer_offer": tenant_price}
        await db.commit()

        svc = HomeServiceFinalCreationService(db=db)
        result = await svc.finalize(draft_id=draft.id, customer_id=context["customer_id"])
        await db.commit()

        assert result["idempotent"] is False

        booking = await db.get(ServiceBooking, uuid.UUID(result["booking_id"]))
        assert booking is not None
        assert booking.tenant_id == context["tenant_id"]
        assert booking.offering_id == context["installation_id"]
        assert booking.zipcode == ZIPCODE_140412
        # Price comes from the tenant's own price record, not an admin
        # catalog default or a fabricated number.
        assert booking.price_snapshot["standard_price"] == tenant_price
        assert booking.price_snapshot["selected_price_amount"] == tenant_price

        job = await db.get(ServiceJob, uuid.UUID(result["job_id"]))
        assert job is not None
        assert job.booking_id == booking.id
        assert job.offering_id == context["installation_id"]

        # Duplicate confirmation stays idempotent for this offering too.
        result2 = await svc.finalize(draft_id=draft.id, customer_id=context["customer_id"])
        assert result2["idempotent"] is True
        assert result2["booking_id"] == result["booking_id"]

        from sqlalchemy import func, select
        job_count = (await db.execute(
            select(func.count()).select_from(ServiceJob).where(ServiceJob.booking_id == booking.id)
        )).scalar_one()
        assert job_count == 1, "Duplicate confirmation must never create a second ServiceJob."
    finally:
        if draft is not None:
            await _cleanup(db, draft.id)
        await db.close()
