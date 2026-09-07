"""Checklist authoring/tenant regression tests, isolated from .env and live databases."""
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from sqlalchemy import JSON, MetaData, create_engine, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.engines.admin_catalog.models import MasterServiceJobType, MasterDataAuditLog, MasterService, TenantService
from app.engines.checklist_catalog import constants as c, service as svc, admin_router as routes
from app.engines.checklist_catalog.models import (
    ChecklistTemplate, ChecklistTemplateVersion, ChecklistSection, ChecklistItem,
    JobTypeChecklistMapping, JobChecklistInstance, JobChecklistResponse, TenantServiceChecklistItem,
)
from app.exceptions import ServiceOSException


class AsyncSessionAdapter:
    """Async interface around a private synchronous SQLite session."""
    def __init__(self, session): self.session = session
    def add(self, value): self.session.add(value)
    async def flush(self): self.session.flush()
    async def commit(self): self.session.commit()
    async def rollback(self): self.session.rollback()
    async def execute(self, *args, **kwargs): return self.session.execute(*args, **kwargs)
    async def scalar(self, *args, **kwargs): return self.session.scalar(*args, **kwargs)
    async def get(self, *args, **kwargs): return self.session.get(*args, **kwargs)
    async def delete(self, value): self.session.delete(value)
    @asynccontextmanager
    async def begin_nested(self):
        with self.session.begin_nested():
            yield


@pytest.fixture
def checklist_db():
    engine = create_engine("sqlite://")
    metadata = MetaData()
    for model in (ChecklistTemplate, ChecklistTemplateVersion, ChecklistSection, ChecklistItem,
                  JobTypeChecklistMapping, JobChecklistInstance, JobChecklistResponse,
                  TenantServiceChecklistItem, MasterServiceJobType, MasterDataAuditLog, MasterService, TenantService):
        table = model.__table__.to_metadata(metadata)
        for column in table.columns:
            if isinstance(column.type, JSONB): column.type = JSON(none_as_null=True)
    metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        session.execute(text("CREATE TABLE service_jobs (id TEXT, tenant_id TEXT, offering_id TEXT)"))
        db = AsyncSessionAdapter(session)
        link = MasterServiceJobType(master_service_id=uuid.uuid4(), job_type_id=uuid.uuid4(), is_active=True)
        session.add(link)
        session.commit()
        yield db, link, uuid.uuid4()
    engine.dispose()


async def authored(db, link, count=7):
    template = await svc.create_template(db, name="Field checks", code="FIELD_" + uuid.uuid4().hex,
        description=None, purpose="INSPECTION", owner_scope="PLATFORM", tenant_id=None, created_by_user_id=None)
    draft = await svc.get_draft_version(db, template.id)
    section = await svc.add_section(db, draft, "Inspection")
    items = [await svc.add_item(db, section, draft, item_type="CHECKBOX", label=f"Check {index}", display_order=index)
             for index in range(count)]
    await svc.publish_version(db, draft, published_by=None)
    mapping = await svc.create_mapping(db, master_service_job_type_id=link.id, service_job_workflow_id=None,
        checklist_template_version_id=draft.id, phase="inspection", usage="REQUIRED", actor="TECHNICIAN",
        completion_gate="NONE", condition_rules=None, display_order=0, created_by=None)
    return template, draft, section, items, mapping


def request():
    return Request({"type": "http", "method": "POST", "path": "/", "headers": []})


@pytest.mark.asyncio
async def test_tenant_requirements_show_exact_published_content_and_enforce_scope(checklist_db, monkeypatch):
    from unittest.mock import AsyncMock
    from app.engines.admin_catalog.tenant_service import TenantCatalogService
    from app.engines.admin_catalog.service_option_service import ServiceOptionService
    from app.engines.admin_catalog.question_service import CatalogQuestionService
    db, link, tenant = checklist_db
    _, version, _, items, mapping = await authored(db, link)
    category_id = uuid.uuid4()
    db.add(MasterService(id=link.master_service_id, category_id=category_id, service_name="AC repair",
                         slug="ac-repair", job_type="repair", pricing_model="FIXED"))
    db.add(TenantService(tenant_id=tenant, master_service_id=link.master_service_id,
                         category_id=category_id, job_type="repair", job_type_id=link.job_type_id))
    other_link = MasterServiceJobType(master_service_id=link.master_service_id, job_type_id=uuid.uuid4(), is_active=True)
    db.add(other_link)
    await db.flush()
    await authored(db, other_link)
    monkeypatch.setattr(ServiceOptionService, "list_service_issue_mappings", AsyncMock(return_value=[]))
    monkeypatch.setattr(ServiceOptionService, "list_service_option_mappings", AsyncMock(return_value=[]))
    monkeypatch.setattr(CatalogQuestionService, "list_questions", AsyncMock(return_value={"questions": []}))
    catalog = TenantCatalogService(db, actor_tenant_id=tenant, actor_role="TENANT_ADMIN")
    result = await catalog.get_service_requirements(link.master_service_id, tenant, link.job_type_id)
    assert len(result["checklists"]) == 1
    checklist = result["checklists"][0]
    assert checklist["mapping_id"] == str(mapping.id)
    assert checklist["version_number"] == version.version_number
    assert [row["label"] for row in checklist["items"]] == [item.label for item in items]
    assert checklist["actor"] == "TECHNICIAN" and checklist["usage"] == "REQUIRED"
    assert checklist["items"][0]["section_title"] == "Inspection"
    for tenant_id, job_type in [(uuid.uuid4(), link.job_type_id), (tenant, other_link.job_type_id)]:
        with pytest.raises(ServiceOSException) as error:
            await catalog.get_service_requirements(link.master_service_id, tenant_id, job_type)
        assert error.value.status_code == 403
    mapping.usage = "DISABLED"
    await db.flush()
    result = await catalog.get_service_requirements(link.master_service_id, tenant, link.job_type_id)
    assert result["checklists"] == []


def test_the_minimum_is_the_product_specified_five():
    assert c.MIN_TENANT_CHECKLIST_ITEMS_PER_SERVICE == 5


def test_all_authoring_mutations_require_platform_admin():
    from app.dependencies.auth import require_super_admin
    mutations = [route for route in routes.router.routes if route.methods & {"POST", "PUT", "DELETE", "PATCH"}]
    assert mutations
    for route in mutations:
        assert require_super_admin in [dependency.call for dependency in route.dependant.dependencies], route.path


@pytest.mark.asyncio
async def test_library_creation_starts_editable_unmapped_and_duplicate_code_is_actionable(checklist_db):
    db, _, _ = checklist_db
    user = SimpleNamespace(user_id=uuid.uuid4())
    body = {"name": " Before work ", "code": " pre_work ", "purpose": "PRE_WORK"}
    await routes.create_template(body, request(), user, db)
    template = (await db.execute(select(ChecklistTemplate))).scalars().one()
    assert template.name == "Before work" and template.code == "PRE_WORK"
    assert template.created_by_user_id == user.user_id
    latest = await routes.get_latest_version(str(template.id), request(), user, db)
    assert latest.data["status"] == "DRAFT" and latest.data["sections"] == []
    assert not (await db.execute(select(JobTypeChecklistMapping))).scalars().all()
    with pytest.raises(ServiceOSException) as error:
        await routes.create_template(body, request(), user, db)
    assert error.value.status_code == 409
    assert "different code" in error.value.detail


@pytest.mark.asyncio
async def test_no_authored_points_reports_admin_gap(checklist_db):
    db, link, tenant = checklist_db
    result = await svc.tenant_selection_readiness(db, tenant, link.master_service_id)
    assert result["nothing_authored"] and not result["satisfied"]


@pytest.mark.asyncio
async def test_selection_roundtrip_and_tenant_isolation(checklist_db):
    db, link, tenant = checklist_db
    _, _, _, items, _ = await authored(db, link)
    for ids in ([row.id for row in items[:4]], [items[0].id] * 5):
        with pytest.raises(ServiceOSException):
            await svc.set_tenant_selection(db, tenant, link.master_service_id, ids, selected_by_user_id=None)
    with pytest.raises(ServiceOSException):
        await svc.set_tenant_selection(db, tenant, link.master_service_id, [row.id for row in items[:4]] + [uuid.uuid4()], selected_by_user_id=None)
    result = await svc.set_tenant_selection(db, tenant, link.master_service_id, [row.id for row in items[:5]], selected_by_user_id=None)
    assert result["satisfied"] and result["selected_count"] == 5
    assert (await svc.tenant_selection_readiness(db, uuid.uuid4(), link.master_service_id))["selected_count"] == 0
    await svc.set_tenant_selection(db, tenant, link.master_service_id, [row.id for row in items[2:]], selected_by_user_id=None)
    rows = (await db.execute(select(TenantServiceChecklistItem))).scalars().all()
    assert len(rows) == 7 and sum(row.is_active for row in rows) == 5


@pytest.mark.asyncio
@pytest.mark.parametrize("retirement", ["mapping", "usage", "template", "version", "job_type"])
async def test_retired_content_does_not_count_as_ready(checklist_db, retirement):
    db, link, tenant = checklist_db
    template, version, _, items, mapping = await authored(db, link)
    await svc.set_tenant_selection(db, tenant, link.master_service_id, [row.id for row in items[:5]], selected_by_user_id=None)
    if retirement == "mapping": mapping.status = "disabled"
    if retirement == "usage": mapping.usage = "DISABLED"
    if retirement == "template": template.status = "archived"
    if retirement == "version": version.status = "DRAFT"
    if retirement == "job_type": link.is_active = False
    await db.flush()
    result = await svc.tenant_selection_readiness(db, tenant, link.master_service_id)
    assert result["selected_count"] == 0 and not result["satisfied"]


@pytest.mark.asyncio
async def test_draft_edits_do_not_change_published_content_or_job_snapshot(checklist_db):
    db, link, tenant = checklist_db
    template, published, _, items, mapping = await authored(db, link)
    job = SimpleNamespace(id=uuid.uuid4(), tenant_id=tenant)
    instance = await svc.ensure_instance(db, job, mapping)
    draft = await svc.get_draft_version(db, template.id)
    assert draft.id != published.id and draft.status == "DRAFT"
    section = (await db.execute(select(ChecklistSection).where(ChecklistSection.checklist_template_version_id == draft.id))).scalars().one()
    edited = (await db.execute(select(ChecklistItem).where(ChecklistItem.checklist_section_id == section.id))).scalars().first()
    await svc.update_item(db, edited, draft, {"label": "Updated draft check"})
    assert items[0].label == "Check 0"
    with pytest.raises(ServiceOSException):
        await svc.update_item(db, items[0], published, {"label": "Forbidden"})
    await svc.publish_version(db, draft, published_by=None)
    assert instance.checklist_template_version_id == published.id


@pytest.mark.asyncio
async def test_quick_create_is_atomic_when_mapping_fails(checklist_db):
    db, link, _ = checklist_db
    payload = {"name": "Atomic", "code": "ATOMIC", "items": ["Check power"], "purpose": "INSPECTION",
               "master_service_job_type_id": str(link.id), "completion_gate": "REQUIRE_BEFORE_HANDOVER"}
    with pytest.raises(ServiceOSException):
        await routes.quick_create_mapping(payload, request(), user=SimpleNamespace(user_id=uuid.uuid4()), db=db)
    assert (await db.execute(select(ChecklistTemplate))).scalars().all() == []
    assert (await db.execute(select(JobTypeChecklistMapping))).scalars().all() == []
    payload["completion_gate"] = "NONE"
    await routes.quick_create_mapping(payload, request(), user=SimpleNamespace(user_id=uuid.uuid4()), db=db)
    assert len((await db.execute(select(ChecklistTemplate))).scalars().all()) == 1
    assert len((await db.execute(select(JobTypeChecklistMapping))).scalars().all()) == 1


@pytest.mark.asyncio
async def test_draft_item_and_section_endpoints_reject_published_edits(checklist_db):
    db, link, _ = checklist_db
    template, published, section, items, _ = await authored(db, link)
    user = SimpleNamespace(user_id=uuid.uuid4())
    with pytest.raises(ServiceOSException): await routes.delete_item(items[0].id, request(), user=user, db=db)
    with pytest.raises(ServiceOSException): await routes.delete_section(section.id, request(), user=user, db=db)
    draft = await svc.get_draft_version(db, template.id)
    section = (await db.execute(select(ChecklistSection).where(ChecklistSection.checklist_template_version_id == draft.id))).scalars().one()
    item = (await db.execute(select(ChecklistItem).where(ChecklistItem.checklist_section_id == section.id))).scalars().first()
    await routes.update_item(item.id, {"label": "Changed"}, request(), user=user, db=db)
    assert item.label == "Changed"
    await routes.update_section(section.id, {"title": "Renamed"}, request(), user=user, db=db)
    await routes.delete_item(item.id, request(), user=user, db=db)
    await routes.delete_section(section.id, request(), user=user, db=db)
    assert (await db.execute(select(ChecklistItem).where(ChecklistItem.checklist_section_id == section.id))).scalars().all() == []


@pytest.mark.parametrize("fields", [
    {"item_type": "CHECKBOX", "label": " "},
    {"item_type": "CHECKBOX", "label": "Power", "evidence_required": True},
    {"item_type": "SINGLE_SELECT", "label": "Status"},
    {"item_type": "MULTI_SELECT", "label": "Status", "select_options": [{"value": "same", "label": "A"}, {"value": "same", "label": "B"}]},
    {"item_type": "PHOTO", "label": "Photo", "min_evidence_count": 3, "max_evidence_count": 1},
])
def test_invalid_item_definitions_are_rejected(fields):
    with pytest.raises(ServiceOSException): svc.validate_item_fields(fields)
