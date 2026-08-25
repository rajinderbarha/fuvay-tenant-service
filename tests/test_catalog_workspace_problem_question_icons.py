from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.admin_catalog.admin_router import list_service_issue_mappings
from app.engines.admin_catalog.question_service import CatalogQuestionService
from app.engines.admin_catalog.service import AdminCatalogService


@pytest.mark.asyncio
async def test_problem_workspace_route_returns_the_declared_object_contract() -> None:
    """A raw list violates ApiResponse[dict] and used to become an HTTP 500."""
    service_id = uuid.uuid4()
    rows = [{"mapping_id": str(uuid.uuid4()), "name": "Not cooling"}]
    service = SimpleNamespace(list_service_issue_mappings=AsyncMock(return_value=rows))
    request = SimpleNamespace(state=SimpleNamespace(request_id="req_catalog_test"))
    actor = SimpleNamespace()

    response = await list_service_issue_mappings(
        service_id=service_id,
        r=request,
        job_type_id=None,
        u=actor,
        s=service,
    )

    assert response.data == {"issues": rows}
    service.list_service_issue_mappings.assert_awaited_once_with(service_id, None)


@pytest.mark.asyncio
async def test_question_icon_is_retired_from_writes_and_responses() -> None:
    """Questions are text; service artwork is managed on Master Services."""
    question_id = uuid.uuid4()
    question = MagicMock()
    question.icon_url = "https://cdn.example.com/custom-question.png"
    question.to_dict.return_value = {"id": str(question_id), "icon_url": None}
    db = MagicMock()
    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = question
    db.execute = AsyncMock(return_value=query_result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    result = await CatalogQuestionService(db=db).update_question(
        question_id, {"icon_url": "https://cdn.example.com/ignored-question.png"}
    )

    assert question.icon_url == "https://cdn.example.com/custom-question.png"
    assert "icon_url" not in result
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(question)


@pytest.mark.asyncio
async def test_problem_icon_is_retired_from_writes_and_responses() -> None:
    """Problems are text-first booking intents; only Master Services own artwork."""
    issue_id = uuid.uuid4()
    row = MagicMock()
    row.id = issue_id
    row.name = "Not cooling"
    row.code = "NOT_COOLING"
    row.slug = "not-cooling"
    row.description = None
    row.severity = "medium"
    row.is_active = True
    row.display_order = 0
    row.icon_url = "https://cdn.example.com/legacy-problem.png"
    row.to_dict.return_value = {
        "id": str(issue_id),
        "name": row.name,
        "icon_url": row.icon_url,
    }
    service = AdminCatalogService(db=MagicMock())
    service.db.flush = AsyncMock()
    service._load_issue_type = AsyncMock(return_value=row)

    result = await service.update_issue_type(
        issue_id, {"name": "AC not cooling", "icon_url": "https://cdn.example.com/new.png"}
    )

    assert row.icon_url == "https://cdn.example.com/legacy-problem.png"
    assert "icon_url" not in result


@pytest.mark.asyncio
async def test_master_service_icon_can_be_replaced_and_cleared() -> None:
    service_id = uuid.uuid4()
    row = MagicMock()
    row.id = service_id
    row.category_id = uuid.uuid4()
    row.service_group_id = uuid.uuid4()
    row.service_name = "AC Repair"
    row.slug = "ac-repair"
    row.description = None
    row.image_url = None
    row.icon_url = "https://cdn.example.com/old.svg"
    row.job_type = "repair"
    row.pricing_model = "fixed"
    row.base_price = 100
    row.min_price = row.max_price = row.visit_fee = None
    row.pre_approval_limit = row.default_estimate = None
    row.hourly_rate = row.minimum_billable_hours = None
    row.estimated_hours = row.maximum_hours = None
    row.assessment_label = row.customer_note = None
    row.show_estimated_range = False
    row.estimated_duration_minutes = 60
    row.requires_checklist = row.is_brand_required = row.is_type_required = False
    row.requires_issue_type = row.requires_schedule = row.requires_address = False
    row.tenant_override_allowed = row.tenant_custom_name_allowed = True
    row.display_order = 0
    row.is_active = True
    row.created_at = row.updated_at = row.deleted_at = None

    service = AdminCatalogService(db=MagicMock())
    service.db.flush = AsyncMock()
    service._load_master_service = AsyncMock(return_value=row)

    replaced = await service.update_master_service(
        service_id, {"icon_url": "https://cdn.example.com/new.svg"}
    )
    assert replaced["icon_url"] == "https://cdn.example.com/new.svg"

    cleared = await service.update_master_service(service_id, {"icon_url": None})
    assert cleared["icon_url"] is None
    service.db.flush.assert_awaited()
