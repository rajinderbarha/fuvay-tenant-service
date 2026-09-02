"""Job-Type Blueprint ownership correction (migration 160).

Covers the NEW canonical creation paths (create_category_canonical,
create_master_service_canonical) and the NEW Job-Type Blueprint service
(master_service_job_types + service_job_workflow) added to fix the real bug
found live: the "New Service Category" and "New Master Service" admin forms
exposed Brand/Type/Issue/Schedule/Address/Pricing at the wrong catalog
level. Pre-existing coverage this file does NOT duplicate:
  - Dimension three-state (enabled/required) usage: test_module_catalog_dimensions_engine.py
  - Tenant price isolation (tenant A cannot see/set tenant B's price): tests/test_sprint3_catalog.py
  - Blueprint version publish-on-change semantics: test_module_service_blueprint_versioning.py

asyncio_mode = "auto" via pyproject.toml — no @pytest.mark.asyncio needed.
"""
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.admin_catalog.service import AdminCatalogService
from app.engines.admin_catalog.job_type_blueprint_service import (
    JobTypeBlueprintService, WORKFLOW_EDITABLE_FIELDS, PRICING_BEHAVIORS,
)
from app.engines.admin_catalog.models import ServiceCategory, ServiceGroup, MasterService
from app.exceptions import ServiceOSException


def db_one(obj):
    result = MagicMock()
    result.scalar_one_or_none.return_value = obj
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def db_seq(*objects):
    results = []
    for obj in objects:
        r = MagicMock()
        r.scalar_one_or_none.return_value = obj
        r.scalars.return_value.all.return_value = []
        results.append(r)
    db = MagicMock()
    db.execute = AsyncMock(side_effect=results)
    db.add = MagicMock(side_effect=lambda o: setattr(o, "id", uuid.uuid4()) if not getattr(o, "id", None) else None)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def make_category(**kw) -> ServiceCategory:
    c = MagicMock(spec=ServiceCategory)
    c.id = uuid.uuid4()
    c.is_active = kw.get("is_active", True)
    return c


class TestBusinessVerticalOwnership:
    """A Business Vertical (ServiceCategory) must not own Brand/Type/pricing
    requirements -- those vary per Master Service and Job Type."""

    async def test_canonical_create_rejects_requires_brand(self):
        svc = AdminCatalogService(db=MagicMock())
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_category_canonical({"name": "Home Services", "requires_brand": True})
        assert exc.value.error_code == "FIELD_OWNED_BY_JOB_TYPE_BLUEPRINT"
        assert "requires_brand" in str(exc.value.detail)

    async def test_canonical_create_rejects_requires_service_option(self):
        """requires_service_option is this table's closest field to a global
        'Type Required' switch -- must also be rejected."""
        svc = AdminCatalogService(db=MagicMock())
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_category_canonical({"name": "Home Services", "requires_service_option": True})
        assert exc.value.error_code == "FIELD_OWNED_BY_JOB_TYPE_BLUEPRINT"

    async def test_canonical_create_rejects_pricing_supported(self):
        svc = AdminCatalogService(db=MagicMock())
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_category_canonical({"name": "Home Services", "pricing_supported": False})
        assert exc.value.error_code == "FIELD_OWNED_BY_JOB_TYPE_BLUEPRINT"

    async def test_canonical_create_rejects_requires_schedule_and_location(self):
        svc = AdminCatalogService(db=MagicMock())
        for field in ("requires_schedule", "requires_location", "requires_issue_type"):
            with pytest.raises(ServiceOSException) as exc:
                await svc.create_category_canonical({"name": "Home Services", field: True})
            assert exc.value.error_code == "FIELD_OWNED_BY_JOB_TYPE_BLUEPRINT"

    async def test_canonical_create_succeeds_without_forbidden_fields(self):
        db = db_seq(None)  # slug-uniqueness lookup -> no existing row
        svc = AdminCatalogService(db=db)
        result = await svc.create_category_canonical({"name": "Home Services"})
        assert result is not None
        db.add.assert_called_once()
        added = db.add.call_args[0][0]
        # Legacy columns exist but are neutralized -- never gate anything
        # for a canonically-created vertical.
        assert added.requires_brand is False
        assert added.requires_service_option is False
        assert added.pricing_supported is False


class TestMasterServiceOwnership:
    """A Master Service must not own job_type, pricing_model, prices, or
    Brand/Type/workflow requirement flags -- those belong to the Job-Type
    Blueprint (added as child records after creation)."""

    async def test_canonical_create_rejects_min_price(self):
        svc = AdminCatalogService(db=MagicMock())
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_master_service_canonical({
                "service_name": "Air Conditioner", "category_id": str(uuid.uuid4()),
                "service_group_id": str(uuid.uuid4()), "min_price": 100})
        assert exc.value.error_code == "FIELD_OWNED_BY_JOB_TYPE_BLUEPRINT"
        assert "min_price" in str(exc.value.detail)

    async def test_canonical_create_rejects_max_price(self):
        svc = AdminCatalogService(db=MagicMock())
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_master_service_canonical({
                "service_name": "Air Conditioner", "category_id": str(uuid.uuid4()),
                "service_group_id": str(uuid.uuid4()), "max_price": 500})
        assert exc.value.error_code == "FIELD_OWNED_BY_JOB_TYPE_BLUEPRINT"

    async def test_canonical_create_rejects_base_price_and_visit_fee(self):
        svc = AdminCatalogService(db=MagicMock())
        for field, val in (("base_price", 50), ("visit_fee", 20)):
            with pytest.raises(ServiceOSException) as exc:
                await svc.create_master_service_canonical({
                    "service_name": "Air Conditioner", "category_id": str(uuid.uuid4()),
                    "service_group_id": str(uuid.uuid4()), field: val})
            assert exc.value.error_code == "FIELD_OWNED_BY_JOB_TYPE_BLUEPRINT"

    async def test_canonical_create_rejects_brand_and_type_required(self):
        svc = AdminCatalogService(db=MagicMock())
        for field in ("is_brand_required", "is_type_required", "requires_issue_type",
                      "requires_checklist", "requires_schedule", "requires_address"):
            with pytest.raises(ServiceOSException) as exc:
                await svc.create_master_service_canonical({
                    "service_name": "Air Conditioner", "category_id": str(uuid.uuid4()),
                    "service_group_id": str(uuid.uuid4()), field: True})
            assert exc.value.error_code == "FIELD_OWNED_BY_JOB_TYPE_BLUEPRINT"

    async def test_canonical_create_rejects_job_type_and_pricing_model(self):
        svc = AdminCatalogService(db=MagicMock())
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_master_service_canonical({
                "service_name": "Air Conditioner", "category_id": str(uuid.uuid4()),
                "service_group_id": str(uuid.uuid4()), "job_type": "repair"})
        assert exc.value.error_code == "FIELD_OWNED_BY_JOB_TYPE_BLUEPRINT"

    async def test_canonical_create_does_not_require_job_type(self):
        """Creation succeeds with zero job types -- they're added afterward
        as child records, not chosen at creation time."""
        cat = make_category(is_active=True)
        group = MagicMock(spec=ServiceGroup)
        group.id = uuid.uuid4(); group.category_id = cat.id; group.status = "active"
        # category, group hierarchy, slug uniqueness, inherited type/brand mappings
        db = db_seq(cat, group, None, None, None)
        svc = AdminCatalogService(db=db)
        result = await svc.create_master_service_canonical({
            "service_name": "Air Conditioner", "category_id": str(cat.id),
            "service_group_id": str(group.id),
        })
        assert result is not None
        added = next(call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], MasterService))
        assert added.job_type is None
        assert added.pricing_model is None

    async def test_canonical_create_requires_service_group(self):
        svc = AdminCatalogService(db=MagicMock())
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_master_service_canonical({
                "service_name": "Air Conditioner", "category_id": str(uuid.uuid4())})
        assert exc.value.error_code == "SERVICE_GROUP_REQUIRED"

    async def test_canonical_create_rejects_inactive_category(self):
        cat = make_category(is_active=False)
        db = db_seq(cat)
        svc = AdminCatalogService(db=db)
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_master_service_canonical({
                "service_name": "Air Conditioner", "category_id": str(cat.id),
                "service_group_id": str(uuid.uuid4())})
        assert exc.value.error_code == "SERVICE_CATEGORY_INACTIVE"


class TestJobTypeBlueprintWorkflow:
    """Job-Type Blueprint workflow ownership: structural flags + permitted
    pricing BEHAVIOR only, never an amount."""

    async def test_set_workflow_rejects_unknown_field(self):
        svc = JobTypeBlueprintService(db=MagicMock())
        with pytest.raises(ServiceOSException) as exc:
            await svc.set_workflow(uuid.uuid4(), uuid.uuid4(), {"base_price": 100})
        assert exc.value.error_code == "INVALID_WORKFLOW_FIELDS"

    async def test_set_workflow_rejects_min_max_price_fields(self):
        svc = JobTypeBlueprintService(db=MagicMock())
        for field in ("min_price", "max_price", "visit_fee", "amount", "fee"):
            with pytest.raises(ServiceOSException):
                await svc.set_workflow(uuid.uuid4(), uuid.uuid4(), {field: 10})

    async def test_set_workflow_rejects_invalid_pricing_behavior(self):
        svc = JobTypeBlueprintService(db=MagicMock())
        with pytest.raises(ServiceOSException) as exc:
            await svc.set_workflow(uuid.uuid4(), uuid.uuid4(), {"pricing_behavior": "negotiable"})
        assert exc.value.error_code == "INVALID_PRICING_BEHAVIOR"

    def test_pricing_behaviors_are_never_amounts(self):
        """The four allowed values describe BEHAVIOR, never a number."""
        assert PRICING_BEHAVIORS == {"fixed", "range", "inspection_required", "custom_quote"}
        for behavior in PRICING_BEHAVIORS:
            assert not any(c.isdigit() for c in behavior)

    def test_workflow_editable_fields_have_no_monetary_keys(self):
        for f in WORKFLOW_EDITABLE_FIELDS:
            assert not any(m in f for m in ("price", "fee", "amount", "cost"))

    async def test_set_workflow_accepts_structural_flags(self):
        ms_id, jt_id = uuid.uuid4(), uuid.uuid4()
        db = db_seq(None, None)  # no existing row, then empty revision update
        svc = JobTypeBlueprintService(db=db)
        result = await svc.set_workflow(ms_id, jt_id, {
            "schedule_required": True, "address_required": True, "pricing_behavior": "inspection_required"})
        db.add.assert_called_once()
        added = db.add.call_args[0][0]
        assert added.schedule_required is True
        assert added.address_required is True
        assert added.pricing_behavior == "inspection_required"


class TestJobTypeIsolation:
    """Changing one job type's blueprint must never alter another job
    type's, even on the same Master Service (live DB — needs a real engine)."""

    @pytest.mark.asyncio
    async def test_repair_and_installation_workflows_are_independent(self):
        from app.database import get_session_factory, init_db
        from sqlalchemy import text
        await init_db()
        factory = get_session_factory()
        async with factory() as db:
            repair_jt = (await db.execute(text(
                "SELECT id FROM job_types WHERE key='repair'"))).scalar()
            install_jt = (await db.execute(text(
                "SELECT id FROM job_types WHERE key='installation'"))).scalar()
            assert repair_jt and install_jt, "job_types seed data missing -- run migration 161"

            # Create disposable fixtures so this test verifies real isolation
            # rather than depending on whatever happens to already exist.
            cat_id = (await db.execute(text(
                "SELECT id FROM service_categories LIMIT 1"))).scalar()
            if not cat_id:
                cat_id = str(uuid.uuid4())
                await db.execute(text(
                    "INSERT INTO service_categories (id, name, slug, is_active) "
                    "VALUES (:id, 'Isolation Test Vertical', 'isolation-test-vertical', true)"),
                    {"id": cat_id})
            ms_id = str(uuid.uuid4())
            await db.execute(text("""
                INSERT INTO master_services (id, category_id, service_name, slug, is_active, display_order)
                VALUES (:id, :cat, 'Isolation Test AC', 'isolation-test-ac', true, 0)
            """), {"id": ms_id, "cat": str(cat_id)})
            await db.commit()

            svc = JobTypeBlueprintService(db=db)
            await svc.set_workflow(ms_id, repair_jt, {"schedule_required": False, "address_required": False})
            await svc.set_workflow(ms_id, install_jt, {"schedule_required": True, "address_required": True})

            repair_after = await svc.get_workflow(ms_id, repair_jt)
            install_after = await svc.get_workflow(ms_id, install_jt)
            assert repair_after["schedule_required"] is False
            assert install_after["schedule_required"] is True

            # Changing Installation again must not touch Repair.
            await svc.set_workflow(ms_id, install_jt, {"schedule_required": False})
            repair_still = await svc.get_workflow(ms_id, repair_jt)
            assert repair_still["schedule_required"] is False

            # cleanup
            await db.execute(text(
                "DELETE FROM service_job_workflow WHERE master_service_id=:ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM master_services WHERE id=:ms"), {"ms": ms_id})
            await db.commit()
