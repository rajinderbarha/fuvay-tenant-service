"""Admin should be able to delete a job type, a question, a dimension value,
and a custom dimension -- not just create/edit them. All four previously had
no delete path at all (job type + question), or only add/edit (dimension
values, dimensions). Live-verified against a running server + real DB in the
same session these tests were written; these cover the service-layer logic
in isolation."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.admin_catalog.question_service import CatalogQuestionService
from app.engines.admin_catalog.dimension_service import CatalogDimensionService
from app.exceptions import ServiceOSException, NotFoundException


def _db(execute_results=None):
    db = MagicMock(commit=AsyncMock(), flush=AsyncMock(), refresh=AsyncMock(),
                   delete=AsyncMock(), execute=AsyncMock())
    if execute_results is not None:
        db.execute = AsyncMock(side_effect=execute_results)
    return db


def _scalar(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.asyncio
async def test_delete_question_is_a_real_delete_not_the_is_active_toggle():
    """is_active already means "paused, still shown as Inactive" (the
    existing toggle). Delete must not reuse that flag, or a deleted question
    would sit in the list forever looking like a paused one."""
    qid, service_id, job_type_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    question = MagicMock(id=qid, master_service_id=service_id, job_type_id=job_type_id, is_active=True)
    db = _db([_scalar(question), MagicMock(), MagicMock()])
    svc = CatalogQuestionService(db)
    from unittest.mock import patch
    with patch("app.engines.admin_catalog.tenant_setup_revision.bump_tenant_setup_revision",
               AsyncMock(return_value=(1, 0))):
        result = await svc.delete_question(qid)
    assert result == {"deleted": True, "id": str(qid)}
    db.delete.assert_awaited_once_with(question)
    db.commit.assert_awaited_once()
    # Cascades: options and rules have no DB-level FK/cascade on this schema.
    assert db.execute.await_count == 3  # load + delete options + delete rules


@pytest.mark.asyncio
async def test_delete_question_bumps_tenant_setup_revision():
    qid, service_id, job_type_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    question = MagicMock(id=qid, master_service_id=service_id, job_type_id=job_type_id, is_active=True)
    db = _db([_scalar(question), MagicMock(), MagicMock()])
    svc = CatalogQuestionService(db)
    from unittest.mock import patch
    with patch("app.engines.admin_catalog.tenant_setup_revision.bump_tenant_setup_revision",
               AsyncMock(return_value=(1, 0))) as bump:
        await svc.delete_question(qid)
    bump.assert_awaited_once_with(db, service_id, job_type_id)


@pytest.mark.asyncio
async def test_delete_question_missing_raises_not_found():
    db = _db([_scalar(None)])
    svc = CatalogQuestionService(db)
    with pytest.raises(NotFoundException):
        await svc.delete_question(uuid.uuid4())


@pytest.mark.asyncio
async def test_delete_dimension_value_soft_deletes():
    dim_id, value_id = uuid.uuid4(), uuid.uuid4()
    value = MagicMock(id=value_id, dimension_id=dim_id, is_active=True)
    db = _db([_scalar(value)])
    svc = CatalogDimensionService(db)
    result = await svc.delete_value(dim_id, value_id)
    assert result == {"deleted": True, "id": str(value_id)}
    assert value.is_active is False
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_value_already_inactive_is_idempotent():
    dim_id, value_id = uuid.uuid4(), uuid.uuid4()
    value = MagicMock(id=value_id, dimension_id=dim_id, is_active=False)
    db = _db([_scalar(value)])
    svc = CatalogDimensionService(db)
    result = await svc.delete_value(dim_id, value_id)
    assert result == {"deleted": True, "id": str(value_id)}
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_dimension_rejects_legacy_type_or_brand():
    dim_id = uuid.uuid4()
    dim = MagicMock(id=dim_id, legacy_source="service_types", name="Equipment Type", is_active=True)
    db = _db([_scalar(dim)])
    svc = CatalogDimensionService(db)
    with pytest.raises(ServiceOSException) as error:
        await svc.delete_dimension(dim_id)
    assert error.value.error_code == "LEGACY_DIMENSION_NOT_DELETABLE"
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_dimension_soft_deletes_a_custom_dimension():
    dim_id = uuid.uuid4()
    dim = MagicMock(id=dim_id, legacy_source=None, name="Custom Attribute", is_active=True)
    db = _db([_scalar(dim)])
    svc = CatalogDimensionService(db)
    result = await svc.delete_dimension(dim_id)
    assert result == {"deleted": True, "id": str(dim_id)}
    assert dim.is_active is False


def test_question_router_exposes_delete():
    from app.engines.admin_catalog.question_router import router
    paths_and_methods = {(r.path, m) for r in router.routes for m in getattr(r, "methods", set()) or set()}
    assert ("/v1/admin/catalog/questions/{question_id}", "DELETE") in paths_and_methods


def test_dimension_router_exposes_value_and_dimension_delete():
    from app.engines.admin_catalog.dimension_router import router
    paths_and_methods = {(r.path, m) for r in router.routes for m in getattr(r, "methods", set()) or set()}
    assert ("/v1/admin/catalog/dimensions/{dimension_id}", "DELETE") in paths_and_methods
    assert ("/v1/admin/catalog/dimensions/{dimension_id}/values/{value_id}", "DELETE") in paths_and_methods
    assert ("/v1/admin/catalog/dimensions/{dimension_id}/values/{value_id}", "PUT") in paths_and_methods


def test_job_type_link_router_already_exposed_delete():
    """The backend already had this; only the frontend was missing it."""
    from app.engines.admin_catalog.job_type_blueprint_router import router
    paths_and_methods = {(r.path, m) for r in router.routes for m in getattr(r, "methods", set()) or set()}
    assert ("/v1/admin/master-services/{service_id}/job-types/{link_id}", "DELETE") in paths_and_methods


def test_frontend_wires_delete_actions_for_job_type_question_and_dimension_value():
    from pathlib import Path
    page = (Path(__file__).parent.parent /
            "frontend/super-admin/app/admin/catalog-workspace/page.tsx").read_text(encoding="utf-8")
    assert "catalogWorkspaceApi.removeServiceJobType" in page
    assert "catalogWorkspaceApi.deleteQuestion" in page
    assert "catalogWorkspaceApi.deleteDimensionValue" in page
    assert "catalogWorkspaceApi.deleteDimension" in page
