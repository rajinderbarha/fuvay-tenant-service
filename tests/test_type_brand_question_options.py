"""Type/brand questions without a dimension still offer the service's library.

The Home Services catalog seed creates `ac_type`, `tv_type` and `brand` as
`free` single-select questions with no dimension and no static answers. Their
options resolved to an empty list, and the Instagram/WhatsApp flow skips a
choice question with nothing to tap, so live bookings stopped asking for the
AC type (Window/Split/Cassette) and brand. Confirmed on staging: both AC
questions resolved with 0 options while 4 types and 11 brands were mapped.
"""
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest

from app.engines.admin_catalog.question_service import (
    CatalogQuestionService, library_for_question_key,
)


def _question(key, answer_source="free", input_type="single_select", dimension_id=None):
    return SimpleNamespace(id=uuid.uuid4(), master_service_id=uuid.uuid4(), question_key=key,
                           answer_source=answer_source, input_type=input_type,
                           dimension_id=dimension_id)


def test_keys_that_name_a_type_or_brand():
    assert library_for_question_key("ac_type") == "service_types"
    assert library_for_question_key("tv_type") == "service_types"
    assert library_for_question_key("equipment_type") == "service_types"
    assert library_for_question_key("brand") == "brands"
    assert library_for_question_key("appliance_brand") == "brands"
    assert library_for_question_key("issue_duration") is None
    assert library_for_question_key(None) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("key,library", [("ac_type", "service_types"), ("brand", "brands")])
async def test_free_type_and_brand_questions_offer_the_mapped_library(key, library):
    svc = CatalogQuestionService(db=None)
    options = [{"id": "t1", "code": "split-ac", "label": "Split AC", "icon_url": None}]
    svc._library_options = AsyncMock(return_value=options)
    qn = _question(key)

    assert await svc._resolved_options(qn) == options
    svc._library_options.assert_awaited_once_with(qn.master_service_id, library)


@pytest.mark.asyncio
async def test_static_answers_still_win_over_the_key():
    svc = CatalogQuestionService(db=None)
    svc._options = AsyncMock(return_value=[{"id": "o1", "code": "wall_mount", "label": "Wall"}])
    svc._library_options = AsyncMock()
    assert await svc._resolved_options(_question("mount_type", answer_source="static")) == [
        {"id": "o1", "code": "wall_mount", "label": "Wall"}]
    svc._library_options.assert_not_awaited()


@pytest.mark.asyncio
async def test_other_free_questions_and_non_choice_inputs_get_no_options():
    svc = CatalogQuestionService(db=None)
    svc._library_options = AsyncMock()
    assert await svc._resolved_options(_question("issue_duration")) == []
    assert await svc._resolved_options(_question("brand", input_type="text")) == []
    svc._library_options.assert_not_awaited()


@pytest.mark.asyncio
async def test_type_library_honours_explicit_slug_allowlist():
    """A newly mapped Type must not leak into an unrelated carousel."""
    result = MagicMock()
    result.all.return_value = []
    db = SimpleNamespace(execute=AsyncMock(return_value=result))
    svc = CatalogQuestionService(db=db)

    await svc._library_options(
        uuid.uuid4(),
        "service_types",
        {
            "type_tree_level": "root",
            "allowed_type_slugs": [
                "plumbing-tap-change",
                "plumbing-wash-basin-installation",
            ],
        },
    )

    statement = db.execute.await_args.args[0]
    compiled = statement.compile()
    assert "service_types.slug IN" in str(compiled)
    assert set(compiled.params["slug_1"]) == {
        "plumbing-tap-change",
        "plumbing-wash-basin-installation",
    }
