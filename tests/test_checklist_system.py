"""
Phase 10 — Checklist System. Before this, checklist_required on a catalog
item was just a boolean — there was no actual list of steps anywhere, and
jobs always started with an empty checklist regardless of what was booked.
This verifies: (1) a catalog item can carry a real checklist template with
validation that required-but-empty templates are rejected, and (2) booking
conversion actually seeds the new job's checklist from that template.
"""
import uuid
from decimal import Decimal
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.exceptions import ServiceOSException
from app.engines.field_ops.constants import JobType
from app.engines.service_catalog.constants import PricingModel

AC_ANNUAL_SERVICE_CHECKLIST = [
    "Clean filter", "Check gas pressure", "Clean indoor unit",
    "Clean outdoor unit", "Check cooling", "Final test",
]


def make_db():
    db = MagicMock()
    db.add = MagicMock(side_effect=lambda o: setattr(o, "created_at", datetime.now(timezone.utc)))
    db.flush = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_checklist_required_without_template_is_rejected():
    from app.engines.service_catalog.service import ServiceCatalogService
    db = make_db()
    no_dup = MagicMock(); no_dup.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=no_dup)
    svc = ServiceCatalogService(db=db)

    with pytest.raises(ServiceOSException) as exc:
        await svc.create_item(uuid.uuid4(), dict(
            service_type_id="ac_service", name="AC Service", service_type=JobType.SERVICE,
            pricing_model=PricingModel.FIXED, base_price=999, checklist_required=True,
            checklist_template=[]))
    assert exc.value.error_code == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_checklist_template_persists_and_returns_in_order():
    from app.engines.service_catalog.service import ServiceCatalogService
    db = make_db()
    no_dup = MagicMock(); no_dup.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=no_dup)
    svc = ServiceCatalogService(db=db)

    result = await svc.create_item(uuid.uuid4(), dict(
        service_type_id="ac_annual_service", name="AC Annual Service", service_type=JobType.SERVICE,
        pricing_model=PricingModel.FIXED, base_price=999, checklist_required=True,
        checklist_template=AC_ANNUAL_SERVICE_CHECKLIST))
    assert result["checklist_template"] == AC_ANNUAL_SERVICE_CHECKLIST


@pytest.mark.asyncio
async def test_update_item_cannot_clear_template_while_checklist_required():
    from app.engines.service_catalog.service import ServiceCatalogService
    item = MagicMock(id=uuid.uuid4(), service_type=JobType.SERVICE, pricing_model=PricingModel.FIXED,
                      base_price=Decimal("999"), max_price=None, checklist_required=True,
                      checklist_template=AC_ANNUAL_SERVICE_CHECKLIST)
    result = MagicMock(); result.scalar_one_or_none.return_value = item
    db = make_db()
    db.execute = AsyncMock(return_value=result)
    svc = ServiceCatalogService(db=db)

    with pytest.raises(ServiceOSException):
        await svc.update_item(item.id, {"checklist_template": []})


@pytest.mark.asyncio
async def test_convert_to_job_seeds_checklist_from_catalog_template():
    from app.engines.booking.service import BookingService
    from app.engines.booking.constants import BS

    tid = uuid.uuid4()
    booking = MagicMock(id=uuid.uuid4(), tenant_id=tid, status=BS.CONFIRMED,
                         job_id=None, converted_job_id=None,
                         service_type_id="ac_annual_service", service_category="ac",
                         customer_id=uuid.uuid4(), address={}, pincode=None,
                         scheduled_at=None, quoted_price=Decimal("999"),
                         job_type=None, customer_notes=None, city=None,
                         address_id=None, service_id=None, pincode_zone=None,
                         matched_service_area_id=None,
                         matched_service_area_service_id=None,
                         coverage_match_level=None, estimated_price=None,
                         sla_minutes=None, tags=None, booking_number="BK-001")
    booking_result = MagicMock(); booking_result.scalar_one_or_none.return_value = booking
    no_job_result  = MagicMock(); no_job_result.scalar_one_or_none.return_value  = None
    creator_result = MagicMock(); creator_result.scalar_one_or_none.return_value = "customer"
    db = make_db()
    # 1st execute → fetch booking; 2nd execute → FieldJob duplicate check;
    # 3rd execute → Slice 2F-15A creation-actor check ("customer" skips the
    # independent-relationship-evidence sub-query entirely)
    db.execute = AsyncMock(side_effect=[booking_result, no_job_result, creator_result])

    svc = BookingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                         actor_tenant_id=tid)
    svc._write_history = AsyncMock()
    svc._publish = AsyncMock()

    catalog_item = MagicMock(service_type=JobType.SERVICE, is_active=True,
                              estimated_duration_minutes=90,
                              checklist_template=AC_ANNUAL_SERVICE_CHECKLIST)

    import app.engines.service_catalog.service as catalog_module
    real_lookup = catalog_module.ServiceCatalogService.get_by_service_type_id
    catalog_module.ServiceCatalogService.get_by_service_type_id = AsyncMock(return_value=catalog_item)
    try:
        await svc.convert_to_job(booking.id)
    finally:
        catalog_module.ServiceCatalogService.get_by_service_type_id = real_lookup

    # Service creates FieldJob directly via db.add — inspect the first added object
    assert db.add.called, "db.add was never called"
    added_job = db.add.call_args_list[0].args[0]
    seeded = added_job.checklist
    assert len(seeded) == 6
    assert seeded[0] == {"step": "Clean filter", "completed": False}
    assert all(item["completed"] is False for item in seeded)


@pytest.mark.asyncio
async def test_convert_to_job_no_checklist_key_when_template_empty():
    """A catalog item with no checklist template must seed an empty checklist on the job."""
    from app.engines.booking.service import BookingService
    from app.engines.booking.constants import BS

    tid = uuid.uuid4()
    booking = MagicMock(id=uuid.uuid4(), tenant_id=tid, status=BS.CONFIRMED,
                         job_id=None, converted_job_id=None,
                         service_type_id="ac_repair", service_category="ac",
                         customer_id=uuid.uuid4(), address={}, pincode=None,
                         scheduled_at=None, quoted_price=Decimal("0"),
                         job_type=None, customer_notes=None, city=None,
                         address_id=None, service_id=None, pincode_zone=None,
                         matched_service_area_id=None,
                         matched_service_area_service_id=None,
                         coverage_match_level=None, estimated_price=None,
                         sla_minutes=None, tags=None, booking_number="BK-002")
    booking_result = MagicMock(); booking_result.scalar_one_or_none.return_value = booking
    no_job_result  = MagicMock(); no_job_result.scalar_one_or_none.return_value  = None
    creator_result = MagicMock(); creator_result.scalar_one_or_none.return_value = "customer"
    db = make_db()
    db.execute = AsyncMock(side_effect=[booking_result, no_job_result, creator_result])

    svc = BookingService(db=db, actor_id=uuid.uuid4(), actor_role="tenant_owner",
                         actor_tenant_id=tid)
    svc._write_history = AsyncMock()
    svc._publish = AsyncMock()

    catalog_item = MagicMock(service_type=JobType.REPAIR, is_active=True,
                              estimated_duration_minutes=None, checklist_template=[])

    import app.engines.service_catalog.service as catalog_module
    real_lookup = catalog_module.ServiceCatalogService.get_by_service_type_id
    catalog_module.ServiceCatalogService.get_by_service_type_id = AsyncMock(return_value=catalog_item)
    try:
        await svc.convert_to_job(booking.id)
    finally:
        catalog_module.ServiceCatalogService.get_by_service_type_id = real_lookup

    # With empty template, the seeded checklist on the job should be empty []
    assert db.add.called, "db.add was never called"
    added_job = db.add.call_args_list[0].args[0]
    assert added_job.checklist == []


@pytest.mark.asyncio
async def test_seeded_checklist_blocks_work_complete_until_done():
    """End-to-end: a job seeded from the AC Annual Service template must still
    enforce completion validation before quality check (Phase 7 gate)."""
    from app.engines.field_ops.service import FieldOpsService
    from app.engines.field_ops.constants import JS

    seeded = [{"step": s, "completed": False} for s in AC_ANNUAL_SERVICE_CHECKLIST]
    job = MagicMock(id=uuid.uuid4(), tenant_id=uuid.uuid4(), status=JS.WORK_STARTED,
                     job_type=JobType.SERVICE, assigned_staff_id=uuid.uuid4(), checklist=seeded)
    result = MagicMock(); result.scalar_one_or_none.return_value = job
    db = make_db()
    db.execute = AsyncMock(return_value=result)
    svc = FieldOpsService(db=db, actor_id=job.assigned_staff_id, actor_role="staff")
    svc._write_history = AsyncMock()
    svc._publish = AsyncMock()

    with pytest.raises(ServiceOSException) as exc:
        await svc.update_status(job.id, JS.WORK_COMPLETE, None, None, None)
    assert exc.value.error_code == "CHECKLIST_INCOMPLETE"

    for item in job.checklist:
        item["completed"] = True
    result2 = await svc.update_status(job.id, JS.WORK_COMPLETE, None, None, None)
    assert result2["status"] == JS.WORK_COMPLETE
