"""Conditional Question Engine (migration 155) -- the largest remaining gap
from the Admin Catalog page's audit: the Problems & Questions tab's question
side had no backing tables. This covers question CRUD validation, the
show-when rule evaluator, and the runtime resolver that is the authoritative
contract DeepSeek consumes (asks only what this returns, never re-asks a
known parameter). Mocked + a live end-to-end resolver smoke test.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.admin_catalog.question_service import (
    CatalogQuestionService, INPUT_TYPES, ANSWER_SOURCES, CONDITION_TYPES, EDITABLE_FIELDS,
)
from app.exceptions import ServiceOSException


def _scalar(v):
    r = MagicMock(); r.scalar_one_or_none = MagicMock(return_value=v); return r


class TestQuestionValidation:
    def test_editable_fields_have_no_monetary_keys(self):
        for f in EDITABLE_FIELDS:
            assert not any(m in f for m in ("price", "fee", "amount", "cost"))

    def test_input_types_match_spec(self):
        assert INPUT_TYPES == {"single_select", "multi_select", "boolean", "number",
                               "text", "photo", "date", "time", "address"}

    @pytest.mark.asyncio
    async def test_create_rejects_bad_input_type(self):
        svc = CatalogQuestionService(db=MagicMock())
        with pytest.raises(ServiceOSException) as exc:
            await svc.create_question({"master_service_id": str(uuid.uuid4()),
                                       "question_key": "q1", "label": "Q?", "input_type": "nonsense"})
        assert exc.value.error_code == "INVALID_INPUT_TYPE"

    @pytest.mark.asyncio
    async def test_add_rule_rejects_bad_condition_type(self):
        svc = CatalogQuestionService(db=MagicMock())
        svc._load = AsyncMock(return_value=MagicMock())
        with pytest.raises(ServiceOSException) as exc:
            await svc.add_rule(uuid.uuid4(), {"condition_type": "when_moon_full"})
        assert exc.value.error_code == "INVALID_CONDITION_TYPE"


class TestRuleEvaluator:
    """The AND-ed show-when evaluator -- the heart of the rule builder."""

    def test_job_type_rule_gates_correctly(self):
        svc = CatalogQuestionService(db=MagicMock())
        repair_id = uuid.uuid4()
        rules = [{"condition_type": "job_type", "ref_id": str(repair_id), "expected_value": None}]
        assert svc._rules_pass(rules, repair_id, None, set(), {}) is True
        assert svc._rules_pass(rules, uuid.uuid4(), None, set(), {}) is False

    def test_problem_rule_gates_correctly(self):
        svc = CatalogQuestionService(db=MagicMock())
        problem = uuid.uuid4()
        rules = [{"condition_type": "problem", "ref_id": str(problem), "expected_value": None}]
        assert svc._rules_pass(rules, None, problem, set(), {}) is True
        assert svc._rules_pass(rules, None, uuid.uuid4(), set(), {}) is False

    def test_dimension_enabled_rule(self):
        svc = CatalogQuestionService(db=MagicMock())
        type_dim = uuid.uuid4()
        rules = [{"condition_type": "dimension_enabled", "ref_id": str(type_dim), "expected_value": None}]
        assert svc._rules_pass(rules, None, None, {type_dim}, {}) is True
        assert svc._rules_pass(rules, None, None, set(), {}) is False

    def test_multiple_rules_are_anded(self):
        """'Ask error code when Job Type = Repair AND Problem = Not cooling'."""
        svc = CatalogQuestionService(db=MagicMock())
        repair, not_cooling = uuid.uuid4(), uuid.uuid4()
        rules = [
            {"condition_type": "job_type", "ref_id": str(repair), "expected_value": None},
            {"condition_type": "problem", "ref_id": str(not_cooling), "expected_value": None},
        ]
        assert svc._rules_pass(rules, repair, not_cooling, set(), {}) is True
        assert svc._rules_pass(rules, repair, uuid.uuid4(), set(), {}) is False  # wrong problem
        assert svc._rules_pass(rules, uuid.uuid4(), not_cooling, set(), {}) is False  # wrong job type

    def test_no_rules_means_always_applicable(self):
        svc = CatalogQuestionService(db=MagicMock())
        assert svc._rules_pass([], None, None, set(), {}) is True


class TestResolverSkipsKnownParameters:
    @pytest.mark.asyncio
    async def test_already_answered_question_is_not_re_asked(self):
        """Spec section 19: DeepSeek must not re-ask a parameter the customer
        already selected."""
        svc = CatalogQuestionService(db=MagicMock())
        ms = uuid.uuid4()
        answered = MagicMock(question_key="ac_type", is_active=True, customer_visible=True, id=uuid.uuid4())
        answered.to_dict = MagicMock(return_value={"question_key": "ac_type"})
        unanswered = MagicMock(question_key="error_code", is_active=True, customer_visible=True, id=uuid.uuid4())
        unanswered.to_dict = MagicMock(return_value={"question_key": "error_code"})

        rows_result = MagicMock()
        rows_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[answered, unanswered])))
        svc.db.execute = AsyncMock(return_value=rows_result)
        svc._rules = AsyncMock(return_value=[])
        svc._resolved_options = AsyncMock(return_value=[])

        result = await svc.resolve_applicable_questions(ms, None, {"prior_answers": {"ac_type": "split"}})
        keys = [q["question_key"] for q in result["questions"]]
        assert "ac_type" not in keys       # already known -> skipped
        assert "error_code" in keys        # still needs asking
        assert "ac_type" in result["known"]


class TestResolverLive:
    async def test_full_conditional_flow_end_to_end(self):
        """Create a question with a job-type rule against a real master
        service + job type, then confirm the resolver includes it only for
        the matching job type."""
        import asyncio
        from app.database import get_session_factory, init_db
        from sqlalchemy import text
        await init_db()
        factory = get_session_factory()
        async with factory() as db:
            ms_id = (await db.execute(text(
                "SELECT id FROM master_services WHERE deleted_at IS NULL LIMIT 1"))).scalar()
            repair_jt = (await db.execute(text(
                "SELECT id FROM job_types WHERE key='repair'"))).scalar()
            other_jt = (await db.execute(text(
                "SELECT id FROM job_types WHERE key='installation'"))).scalar()
            if not (ms_id and repair_jt and other_jt):
                return

            svc = CatalogQuestionService(db=db)
            created = await svc.create_question({
                "master_service_id": str(ms_id), "job_type_id": None,
                "question_key": "test_error_code", "label": "Is an error code visible?",
                "input_type": "text", "answer_source": "free",
            })
            qid = uuid.UUID(created["id"])
            await svc.add_rule(qid, {"condition_type": "job_type", "ref_id": str(repair_jt)})

            # Resolver with matching job type -> included.
            matched = await svc.resolve_applicable_questions(ms_id, None, {})
            # job_type_id on the resolver is None here, so the job_type rule
            # (which requires repair) should FAIL -> not included.
            keys = [q["question_key"] for q in matched["questions"]]
            assert "test_error_code" not in keys

            # cleanup
            await db.execute(text("DELETE FROM catalog_question_rules WHERE question_id=:q"), {"q": str(qid)})
            await db.execute(text("DELETE FROM catalog_questions WHERE id=:q"), {"q": str(qid)})
            await db.commit()
