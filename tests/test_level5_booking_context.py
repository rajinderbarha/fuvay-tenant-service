"""CUSTOMER WORKFLOW REGRESSION CLOSURE (2026-08-01) — server-authoritative
booking context tests. Confirmed live that DeepSeek has no persisted memory
of tool-call results across turns; this module is the backend-authoritative
fix (compact context re-injected each turn, not reliant on LLM memory).
"""
import uuid
from datetime import datetime, timedelta, timezone

from app.engines.ai_conversation.booking_context import (
    get_booking_context,
    update_booking_context,
    set_cached,
    get_cached,
    format_context_for_prompt,
    STATIC_CACHE_TTL_SECONDS,
)


def _id():
    return str(uuid.uuid4())


class _FakeSession:
    def __init__(self, context_data=None):
        self.context_data = context_data or {}


class TestBookingContextPersistence:
    def test_empty_context_returns_empty_dict(self):
        session = _FakeSession()
        assert get_booking_context(session) == {}

    def test_update_persists_fields(self):
        session = _FakeSession()
        draft_id = _id()
        ctx = update_booking_context(session, draft_id=draft_id, category_id="cat1")
        assert ctx["draft_id"] == draft_id
        assert session.context_data["booking_context"]["draft_id"] == draft_id

    def test_update_merges_not_replaces(self):
        session = _FakeSession()
        update_booking_context(session, draft_id="d1", category_id="c1", offering_id="o1")
        update_booking_context(session, job_type_id="jt1")
        ctx = get_booking_context(session)
        assert ctx["draft_id"] == "d1"
        assert ctx["job_type_id"] == "jt1"

    def test_none_values_do_not_overwrite_existing(self):
        session = _FakeSession()
        update_booking_context(session, draft_id="d1")
        update_booking_context(session, draft_id=None, job_type_id="jt1")
        ctx = get_booking_context(session)
        assert ctx["draft_id"] == "d1"  # not clobbered by a None update
        assert ctx["job_type_id"] == "jt1"

    def test_explicit_none_zipcode_does_not_change_scope_or_wipe_context(self):
        """CUSTOMER WORKFLOW REGRESSION CLOSURE (2026-08-01): the critical
        bug — a tool that always passes zipcode=None (nothing new to
        report) must not be treated as a scope change that wipes
        draft_id/job_type_id/current_question. Confirmed live: this was
        wiping the entire cached context on almost every tool call."""
        session = _FakeSession()
        update_booking_context(session, category_id="c1", offering_id="o1", zipcode="141001",
                                draft_id="d1", job_type_id="jt1", current_question={"question_id": "q1"})
        # Simulates _tool_update_home_service_draft calling with
        # zipcode=None/city=None because this particular update had nothing
        # new to report for those fields.
        ctx = update_booking_context(session, draft_id="d1", job_type_id=None, zipcode=None, city=None)
        assert ctx["draft_id"] == "d1"
        assert ctx["job_type_id"] == "jt1"
        assert ctx["current_question"] == {"question_id": "q1"}
        assert ctx["zipcode"] == "141001"

    def test_explicit_current_question_none_means_complete_not_unchanged(self):
        """current_question=None is meaningful (question flow complete) and
        must overwrite a previously-cached question, unlike every other
        field where None means 'nothing to report this call'."""
        session = _FakeSession()
        update_booking_context(session, category_id="c1", offering_id="o1", zipcode="141001",
                                current_question={"question_id": "q1"})
        ctx = update_booking_context(session, category_id="c1", offering_id="o1", zipcode="141001",
                                      current_question=None)
        assert ctx["current_question"] is None


class TestScopeInvalidation:
    def test_same_scope_keeps_cached_state(self):
        session = _FakeSession()
        update_booking_context(session, category_id="c1", offering_id="o1", zipcode="141001",
                                draft_id="d1", job_type_id="jt1", current_question={"question_id": "q1"})
        # Same category/offering/zipcode -> no invalidation
        ctx = update_booking_context(session, category_id="c1", offering_id="o1", zipcode="141001")
        assert ctx["draft_id"] == "d1"
        assert ctx["job_type_id"] == "jt1"
        assert ctx["current_question"] == {"question_id": "q1"}

    def test_zipcode_change_invalidates_job_type_and_question(self):
        """Customer moves to a different ZIP mid-conversation — cached
        job-type/question-flow state from the old location must not leak
        into the new one."""
        session = _FakeSession()
        update_booking_context(session, category_id="c1", offering_id="o1", zipcode="141001",
                                draft_id="d1", job_type_id="jt1", current_question={"question_id": "q1"})
        ctx = update_booking_context(session, category_id="c1", offering_id="o1", zipcode="999999")
        assert "draft_id" not in ctx
        assert "job_type_id" not in ctx
        assert "current_question" not in ctx
        assert ctx["zipcode"] == "999999"

    def test_offering_change_invalidates_cached_state(self):
        session = _FakeSession()
        update_booking_context(session, category_id="c1", offering_id="o1", zipcode="141001",
                                draft_id="d1", job_type_id="jt1")
        ctx = update_booking_context(session, category_id="c1", offering_id="o2", zipcode="141001")
        assert "draft_id" not in ctx
        assert "job_type_id" not in ctx


class TestStaticCaching:
    def test_fresh_cache_returned(self):
        ctx = set_cached({}, "job_type_options", [{"job_type_id": "jt1", "label": "Repair"}])
        assert get_cached(ctx, "job_type_options") == [{"job_type_id": "jt1", "label": "Repair"}]

    def test_expired_cache_not_returned(self):
        stale_time = (datetime.now(timezone.utc) - timedelta(seconds=STATIC_CACHE_TTL_SECONDS + 60)).isoformat()
        ctx = {"job_type_options": {"value": [{"job_type_id": "jt1"}], "cached_at": stale_time}}
        assert get_cached(ctx, "job_type_options") is None

    def test_missing_cache_key_returns_none(self):
        assert get_cached({}, "job_type_options") is None


class TestPromptFormatting:
    def test_empty_context_produces_empty_string(self):
        assert format_context_for_prompt({}) == ""

    def test_draft_id_tells_deepseek_not_to_recreate(self):
        prompt = format_context_for_prompt({"draft_id": "d1", "category_slug": "air-conditioning"})
        assert "d1" in prompt
        assert "do NOT call start_home_service_draft again" in prompt

    def test_job_type_id_tells_deepseek_not_to_refetch_options(self):
        prompt = format_context_for_prompt({"job_type_id": "jt1"})
        assert "do NOT call get_home_service_job_type_options again" in prompt

    def test_current_question_included_with_options(self):
        ctx = {
            "current_question": {
                "question_id": "q1", "text": "Which brand?", "question_type": "single_select",
                "required": True, "options": [{"id": "o1", "label": "LG"}],
            }
        }
        prompt = format_context_for_prompt(ctx)
        assert "Which brand?" in prompt
        assert "LG=o1" in prompt
        assert "phrase THIS question next" in prompt

    def test_null_current_question_with_job_type_means_complete(self):
        ctx = {"job_type_id": "jt1", "current_question": None}
        prompt = format_context_for_prompt(ctx)
        assert "question collection complete" in prompt
