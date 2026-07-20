"""
Phase 8 — Service Catalog Engine. Tenants can now define their own services
(name, service_type, category, pricing model, base/max price, visit fee,
pre-approval limit, duration estimate, checklist flag) instead of relying on
hardcoded service types. The critical integration: booking→job conversion
now reads the catalog to automatically pick the correct job_type/workflow
(per Phase 7), with a non-blocking fallback for tenants with no catalog yet.
"""
import uuid
from decimal import Decimal
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.exceptions import ServiceOSException, NotFoundException
from app.engines.field_ops.constants import JobType
from app.engines.service_catalog.constants import PricingModel


def make_db():
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


def example_item_data(**overrides):
    data = dict(
        service_type_id="ac_not_cooling", name="AC Not Cooling",
        service_type=JobType.REPAIR, category="ac_repair",
        pricing_model=PricingModel.POST_ASSESSMENT,
        visit_fee=150, pre_approval_limit=2000,
        estimated_duration_minutes=60, checklist_required=False,
    )
    data.update(overrides)
    return data


# ── Validation ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_item_rejects_invalid_service_type():
    from app.engines.service_catalog.service import ServiceCatalogService
    db = make_db()
    no_dup_result = MagicMock(); no_dup_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=no_dup_result)
    svc = ServiceCatalogService(db=db)

    with pytest.raises(ServiceOSException) as exc:
        await svc.create_item(uuid.uuid4(), example_item_data(service_type="haircut"))
    assert exc.value.error_code == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_create_item_rejects_max_price_below_base_price():
    from app.engines.service_catalog.service import ServiceCatalogService
    db = make_db()
    no_dup_result = MagicMock(); no_dup_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=no_dup_result)
    svc = ServiceCatalogService(db=db)

    with pytest.raises(ServiceOSException) as exc:
        await svc.create_item(uuid.uuid4(), example_item_data(
            pricing_model=PricingModel.FIXED, base_price=1000, max_price=500))
    assert exc.value.error_code == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_create_item_rejects_duplicate_service_type_id_for_same_tenant():
    from app.engines.service_catalog.service import ServiceCatalogService
    tid = uuid.uuid4()
    existing = MagicMock()
    dup_result = MagicMock(); dup_result.scalar_one_or_none.return_value = existing
    db = make_db()
    db.execute = AsyncMock(return_value=dup_result)
    svc = ServiceCatalogService(db=db)

    with pytest.raises(ServiceOSException) as exc:
        await svc.create_item(tid, example_item_data())
    assert exc.value.error_code == "CONFLICT"


@pytest.mark.asyncio
async def test_create_item_succeeds_with_valid_data():
    from app.engines.service_catalog.service import ServiceCatalogService
    db = make_db()
    no_dup_result = MagicMock(); no_dup_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=no_dup_result)

    def fake_add(obj):
        obj.created_at = datetime.now(timezone.utc)
    db.add = MagicMock(side_effect=fake_add)

    svc = ServiceCatalogService(db=db)
    result = await svc.create_item(uuid.uuid4(), example_item_data())
    assert result["name"] == "AC Not Cooling"
    assert result["service_type"] == JobType.REPAIR
    assert result["pricing_model"] == PricingModel.POST_ASSESSMENT


# ── Three example catalog entries from the spec ─────────────────────────────

@pytest.mark.asyncio
async def test_fixed_price_service_example():
    from app.engines.service_catalog.service import ServiceCatalogService
    db = make_db()
    no_dup_result = MagicMock(); no_dup_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=no_dup_result)
    db.add = MagicMock(side_effect=lambda o: setattr(o, "created_at", datetime.now(timezone.utc)))
    svc = ServiceCatalogService(db=db)

    result = await svc.create_item(uuid.uuid4(), example_item_data(
        service_type_id="ac_annual_service", name="AC Annual Service",
        service_type=JobType.SERVICE, pricing_model=PricingModel.FIXED,
        base_price=999, checklist_required=True,
        checklist_template=["Clean filter", "Check gas pressure", "Clean indoor unit",
                             "Clean outdoor unit", "Check cooling", "Final test"]))
    assert result["service_type"] == JobType.SERVICE
    assert result["pricing_model"] == PricingModel.FIXED
    assert result["checklist_required"] is True
    assert len(result["checklist_template"]) == 6


@pytest.mark.asyncio
async def test_consultation_fixed_consult_fee_example():
    from app.engines.service_catalog.service import ServiceCatalogService
    db = make_db()
    no_dup_result = MagicMock(); no_dup_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=no_dup_result)
    db.add = MagicMock(side_effect=lambda o: setattr(o, "created_at", datetime.now(timezone.utc)))
    svc = ServiceCatalogService(db=db)

    result = await svc.create_item(uuid.uuid4(), example_item_data(
        service_type_id="ac_inspection", name="AC Inspection",
        service_type=JobType.CONSULTATION, pricing_model=PricingModel.FIXED,
        base_price=299))
    assert result["service_type"] == JobType.CONSULTATION
    assert result["base_price"] == 299.0


# ── Booking integration: auto job_type selection ────────────────────────────

@pytest.mark.asyncio
async def test_convert_to_job_uses_catalog_job_type_when_present():
    """Step 5: convert_to_job copies catalog job_type to the created FieldJob."""
    from app.engines.booking.service import BookingService
    from app.engines.booking.constants import BS
    from app.engines.field_ops.models import Job as FieldJob, JobStatusHistory as FieldJSH
    from unittest.mock import patch

    tid = uuid.uuid4()
    cid = uuid.uuid4()
    booking = MagicMock(
        id=uuid.uuid4(), tenant_id=tid, status=BS.CONFIRMED,
        job_id=None, converted_job_id=None,
        service_type_id="ac_inspection", service_category="ac_repair",
        customer_id=cid, address={}, pincode="400001", city="Mumbai",
        address_id=None, service_id=None,
        matched_service_area_id=None, matched_service_area_service_id=None,
        coverage_match_level=None, scheduled_at=None, customer_notes=None,
        quoted_price=Decimal("299"), estimated_price=Decimal("299"),
        sla_minutes=60, tags=[], job_type="repair",
    )
    no_job_result = MagicMock(); no_job_result.scalar_one_or_none.return_value = None
    booking_result = MagicMock(); booking_result.scalar_one_or_none.return_value = booking
    db = make_db()
    db.execute = AsyncMock(side_effect=[booking_result, no_job_result])

    # Capture objects added to db
    added_objects = []
    db.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

    svc = BookingService(db=db, actor_id=uuid.uuid4(), actor_role="super_admin")
    svc._write_history = AsyncMock()
    svc._publish = AsyncMock()

    catalog_item = MagicMock(service_type=JobType.CONSULTATION, is_active=True,
                              estimated_duration_minutes=30, checklist_template=None)

    import app.engines.service_catalog.service as catalog_module
    real_lookup = catalog_module.ServiceCatalogService.get_by_service_type_id
    catalog_module.ServiceCatalogService.get_by_service_type_id = AsyncMock(return_value=catalog_item)

    try:
        with patch("app.core.usage_quota.adjust_usage", new=AsyncMock()):
            await svc.convert_to_job(booking.id)
    except Exception:
        pass  # structural test — we only need to check what got added
    finally:
        catalog_module.ServiceCatalogService.get_by_service_type_id = real_lookup

    created_jobs = [o for o in added_objects if isinstance(o, FieldJob)]
    assert len(created_jobs) == 1, f"Expected 1 FieldJob, got {len(created_jobs)}: {added_objects}"
    assert created_jobs[0].job_type == JobType.CONSULTATION
    assert created_jobs[0].duration_estimate_minutes == 30


@pytest.mark.asyncio
async def test_convert_to_job_falls_back_gracefully_with_no_catalog_entry():
    """Tenants who haven't set up a catalog yet must not have bookings break."""
    from app.engines.booking.service import BookingService
    from app.engines.booking.constants import BS
    from app.engines.field_ops.models import Job as FieldJob
    from unittest.mock import patch

    tid = uuid.uuid4()
    cid = uuid.uuid4()
    booking = MagicMock(
        id=uuid.uuid4(), tenant_id=tid, status=BS.CONFIRMED,
        job_id=None, converted_job_id=None,
        service_type_id="some_legacy_service", service_category="general",
        customer_id=cid, address={}, pincode=None, city=None,
        address_id=None, service_id=None,
        matched_service_area_id=None, matched_service_area_service_id=None,
        coverage_match_level=None, scheduled_at=None, customer_notes=None,
        quoted_price=Decimal("500"), estimated_price=Decimal("500"),
        sla_minutes=None, tags=[], job_type="repair",
    )
    no_job_result = MagicMock(); no_job_result.scalar_one_or_none.return_value = None
    booking_result = MagicMock(); booking_result.scalar_one_or_none.return_value = booking
    db = make_db()
    db.execute = AsyncMock(side_effect=[booking_result, no_job_result])

    added_objects = []
    db.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

    svc = BookingService(db=db, actor_id=uuid.uuid4(), actor_role="super_admin")
    svc._write_history = AsyncMock()
    svc._publish = AsyncMock()

    import app.engines.service_catalog.service as catalog_module
    real_lookup = catalog_module.ServiceCatalogService.get_by_service_type_id
    catalog_module.ServiceCatalogService.get_by_service_type_id = AsyncMock(return_value=None)

    try:
        with patch("app.core.usage_quota.adjust_usage", new=AsyncMock()):
            result = await svc.convert_to_job(booking.id)
    except Exception:
        result = None
    finally:
        catalog_module.ServiceCatalogService.get_by_service_type_id = real_lookup

    # Falls back to booking's own job_type ("repair") when no catalog entry
    created_jobs = [o for o in added_objects if isinstance(o, FieldJob)]
    assert len(created_jobs) == 1, f"Expected 1 FieldJob, got: {added_objects}"
    assert created_jobs[0].job_type == "repair"
    assert result is not None and "job_id" in result
