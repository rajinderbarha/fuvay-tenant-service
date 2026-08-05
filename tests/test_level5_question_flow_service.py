"""LEVEL-5 REMEDIATION (2026-08-01, Phase 3) — Deterministic Question Flow tests.

Exercises QuestionFlowService against a mocked CatalogQuestionService
(admin_catalog's resolver is already independently tested elsewhere — these
tests prove the binding/envelope/validation logic on top of it).
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engines.home_service_booking.question_flow_service import (
    QuestionFlowService,
    ERR_DRAFT_ACCESS_DENIED,
    ERR_JOB_TYPE_REQUIRED,
    ERR_QUESTION_NOT_APPLICABLE,
    ERR_INVALID_OPTION,
    ERR_ANSWER_REQUIRED,
    ERR_STALE_VERSION,
)
from app.exceptions import ServiceOSException


def _id():
    return uuid.uuid4()


def make_draft(**overrides):
    d = MagicMock()
    d.id = overrides.get("id", _id())
    d.customer_id = overrides.get("customer_id", _id())
    d.category_id = overrides.get("category_id", _id())
    d.offering_id = overrides.get("offering_id", _id())
    d.job_type_id = overrides.get("job_type_id", _id())
    d.selected_problem_id = overrides.get("selected_problem_id", None)
    d.service_job_workflow_id = overrides.get("service_job_workflow_id", None)
    d.ai_session_id = overrides.get("ai_session_id", None)
    d.catalog_question_answers = overrides.get("catalog_question_answers", {})
    d.question_flow_version = overrides.get("question_flow_version", 1)
    return d


def make_question(question_id=None, question_key="brand", input_type="single_select",
                   required=True, options=None):
    return {
        "id": str(question_id or _id()),
        "question_key": question_key,
        "label": "Which brand is your AC?",
        "input_type": input_type,
        "required": required,
        "help_text": None,
        "validation": None,
        "options": options or [{"id": str(_id()), "label": "LG"}, {"id": str(_id()), "label": "Samsung"}],
    }


def make_db():
    """Shared DB mock supporting the real `db.execute(...)` calls added
    later this phase (QuestionFlowService._require_publisher's
    tenant/issue-mapping existence checks, and _bridge_to_draft_columns'
    Brand/ServiceType lookups on submit_answer) -- `db.execute(...)` needs
    to be awaitable and its `.scalars().first()` chain needs to return a
    truthy sentinel by default so these unrelated checks don't fail
    closed and mask what each test is actually trying to prove. Individual
    tests can still override `db.execute` for scenarios that specifically
    exercise the publisher/problem-mapping gate."""
    db = MagicMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.first.return_value = MagicMock()  # truthy "found" row
    db.execute = AsyncMock(return_value=execute_result)
    return db


def make_service(db=None, resolved=None):
    svc = QuestionFlowService(db=db or MagicMock())
    svc.catalog = MagicMock()
    svc.catalog.resolve_applicable_questions = AsyncMock(
        return_value=resolved or {"questions": [], "known": []}
    )
    return svc


class TestGetCurrentQuestion:
    async def test_returns_first_applicable_question(self):
        draft = make_draft()
        q = make_question()
        db = make_db()
        db.get = AsyncMock(return_value=draft)
        svc = make_service(db=db, resolved={"questions": [q], "known": []})

        result = await svc.get_current_question(draft_id=draft.id, customer_id=draft.customer_id)
        assert result["current_question"]["question_id"] == q["id"]
        assert result["current_question"]["question_type"] == "single_select"
        assert len(result["current_question"]["options"]) == 2
        assert result["progress"]["complete"] is False
        assert result["next_permitted_actions"] == ["submit_answer"]

    async def test_complete_when_no_questions_remain(self):
        draft = make_draft()
        db = make_db()
        db.get = AsyncMock(return_value=draft)
        svc = make_service(db=db, resolved={"questions": [], "known": ["brand"]})

        result = await svc.get_current_question(draft_id=draft.id, customer_id=draft.customer_id)
        assert result["current_question"] is None
        assert result["progress"]["complete"] is True
        assert result["next_permitted_actions"] == ["proceed_to_serviceability"]

    async def test_missing_job_type_fails_closed(self):
        draft = make_draft(job_type_id=None)
        db = make_db()
        db.get = AsyncMock(return_value=draft)
        svc = make_service(db=db)

        with pytest.raises(ServiceOSException) as exc:
            await svc.get_current_question(draft_id=draft.id, customer_id=draft.customer_id)
        assert exc.value.error_code == ERR_JOB_TYPE_REQUIRED

    async def test_wrong_owner_denied(self):
        owner_id = _id()
        attacker_id = _id()
        draft = make_draft(customer_id=owner_id)
        db = make_db()
        db.get = AsyncMock(return_value=draft)
        svc = make_service(db=db)

        with pytest.raises(ServiceOSException) as exc:
            await svc.get_current_question(draft_id=draft.id, customer_id=attacker_id)
        assert exc.value.error_code == ERR_DRAFT_ACCESS_DENIED

    async def test_photo_question_flagged_capable(self):
        draft = make_draft()
        q = make_question(input_type="photo", required=False, options=[])
        db = make_db()
        db.get = AsyncMock(return_value=draft)
        svc = make_service(db=db, resolved={"questions": [q], "known": []})

        result = await svc.get_current_question(draft_id=draft.id, customer_id=draft.customer_id)
        assert result["current_question"]["photo_capable"] is True


class TestSubmitAnswer:
    async def test_valid_single_select_answer_persisted_and_version_bumped(self):
        draft = make_draft(question_flow_version=1)
        opt_id = str(_id())
        q = make_question(input_type="single_select", options=[{"id": opt_id, "label": "LG"}])
        db = make_db()
        db.get = AsyncMock(return_value=draft)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        svc = make_service(db=db, resolved={"questions": [q], "known": []})
        # After the answer, re-resolve returns no more questions (complete).
        svc.catalog.resolve_applicable_questions = AsyncMock(side_effect=[
            {"questions": [q], "known": []},
            {"questions": [], "known": [q["question_key"]]},
        ])

        result = await svc.submit_answer(
            draft_id=draft.id, customer_id=draft.customer_id,
            question_id=q["id"], option_id=opt_id,
        )
        assert draft.catalog_question_answers[q["question_key"]] == opt_id
        assert draft.question_flow_version == 2
        assert result["progress"]["complete"] is True

    async def test_invalid_question_id_rejected(self):
        draft = make_draft()
        q = make_question()
        db = make_db()
        db.get = AsyncMock(return_value=draft)
        svc = make_service(db=db, resolved={"questions": [q], "known": []})

        with pytest.raises(ServiceOSException) as exc:
            await svc.submit_answer(
                draft_id=draft.id, customer_id=draft.customer_id,
                question_id=str(_id()), option_id="whatever",
            )
        assert exc.value.error_code == ERR_QUESTION_NOT_APPLICABLE

    async def test_invalid_option_id_rejected(self):
        draft = make_draft()
        q = make_question(input_type="single_select")
        db = make_db()
        db.get = AsyncMock(return_value=draft)
        svc = make_service(db=db, resolved={"questions": [q], "known": []})

        with pytest.raises(ServiceOSException) as exc:
            await svc.submit_answer(
                draft_id=draft.id, customer_id=draft.customer_id,
                question_id=q["id"], option_id="not-a-real-option-id",
            )
        assert exc.value.error_code == ERR_INVALID_OPTION

    async def test_missing_required_text_answer_rejected(self):
        draft = make_draft()
        q = make_question(input_type="text", required=True, options=[])
        db = make_db()
        db.get = AsyncMock(return_value=draft)
        svc = make_service(db=db, resolved={"questions": [q], "known": []})

        with pytest.raises(ServiceOSException) as exc:
            await svc.submit_answer(
                draft_id=draft.id, customer_id=draft.customer_id,
                question_id=q["id"], value=None,
            )
        assert exc.value.error_code == ERR_ANSWER_REQUIRED

    async def test_stale_expected_version_rejected(self):
        draft = make_draft(question_flow_version=3)
        db = make_db()
        db.get = AsyncMock(return_value=draft)
        svc = make_service(db=db)

        with pytest.raises(ServiceOSException) as exc:
            await svc.submit_answer(
                draft_id=draft.id, customer_id=draft.customer_id,
                question_id=str(_id()), value="x", expected_version=1,
            )
        assert exc.value.error_code == ERR_STALE_VERSION

    async def test_duplicate_answer_submission_is_rejected_once_question_resolved_away(self):
        """A duplicate submission for a question already answered (and thus
        no longer in the applicable set) is rejected the same way as any
        other not-currently-applicable question — not silently re-applied."""
        draft = make_draft(catalog_question_answers={"brand": "LG"})
        q_already_answered_id = str(_id())
        db = make_db()
        db.get = AsyncMock(return_value=draft)
        svc = make_service(db=db, resolved={"questions": [], "known": ["brand"]})

        with pytest.raises(ServiceOSException) as exc:
            await svc.submit_answer(
                draft_id=draft.id, customer_id=draft.customer_id,
                question_id=q_already_answered_id, option_id="LG",
            )
        assert exc.value.error_code == ERR_QUESTION_NOT_APPLICABLE

    async def test_valid_multi_select_answer(self):
        draft = make_draft()
        opt1, opt2 = str(_id()), str(_id())
        q = make_question(input_type="multi_select", options=[
            {"id": opt1, "label": "Fan"}, {"id": opt2, "label": "Compressor"},
        ])
        db = make_db()
        db.get = AsyncMock(return_value=draft)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        svc = make_service(db=db, resolved={"questions": [q], "known": []})
        svc.catalog.resolve_applicable_questions = AsyncMock(side_effect=[
            {"questions": [q], "known": []},
            {"questions": [], "known": [q["question_key"]]},
        ])

        result = await svc.submit_answer(
            draft_id=draft.id, customer_id=draft.customer_id,
            question_id=q["id"], option_id=[opt1, opt2],
        )
        assert draft.catalog_question_answers[q["question_key"]] == [opt1, opt2]
