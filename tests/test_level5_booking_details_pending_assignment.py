"""BOOKING-DETAILS-CONTRACT-FIXES (2026-08-01) — replaces the prior
remediation (which copied `draft.catalog_question_answers` onto the
ALREADY-USED `issue_details` column -- audit found
`execution/mobile_inspection_service.py` reads that column expecting a
DIFFERENT shape (`{"answers": [...], "notes": ...}`, inspection-report
data), so the earlier fix would have silently broken that consumer).

Answers now live in a DEDICATED, versioned, immutable
`ServiceBooking.answer_snapshot` column (migration 222), built ONCE at
finalize() time by `QuestionFlowService.build_answer_snapshot`, resolving
question label/type/order and the answered option's display label from
the live catalog so a later catalog edit can never alter what a
historical, already-confirmed booking shows.
"""
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.final_records.creation_service import HomeServiceFinalCreationService
from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
from app.engines.home_service_booking.question_flow_service import QuestionFlowService


def _scalars(item):
    result = MagicMock()
    result.scalars.return_value.first.return_value = item
    result.scalars.return_value.all.return_value = item if isinstance(item, list) else [item]
    return result


def _draft(**overrides):
    defaults = dict(
        id=uuid.uuid4(), customer_id=uuid.uuid4(), status="ready_for_confirmation",
        job_type_id=uuid.uuid4(), master_service_job_type_id=uuid.uuid4(),
        service_job_workflow_id=uuid.uuid4(), selected_problem_id=None,
        selected_tenant_id=uuid.uuid4(), preferred_date=None, preferred_time_window=None,
        ai_session_id=None, customer_name="Rajinder Singh", customer_phone="9999999999",
        city="Ludhiana", zipcode="141002", address_snapshot={"line1": "Model Town"},
        price_snapshot={"standard_price": 499}, selected_provider_snapshot={"provider_name": "CoolFix"},
        issue_summary="Not cooling", issue_details=None,
        catalog_question_answers={"brand": "LG"},
        photo_urls=[],
        booking_summary={"selected_price_tier": "standard", "customer_offer": 499},
        category_id=uuid.uuid4(), offering_id=uuid.uuid4(),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _question(**overrides):
    defaults = dict(
        id=uuid.uuid4(), question_key="brand", label="What is your AC brand?",
        input_type="single_select", display_order=1,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


async def _run_finalize(draft, db, monkeypatch, booking_number="SB-2026-01", job_number="SJ-2026-01"):
    monkeypatch.setattr(
        "app.engines.final_records.creation_service.generate_booking_number",
        AsyncMock(return_value=booking_number),
    )
    monkeypatch.setattr(
        "app.engines.final_records.creation_service.generate_job_number",
        AsyncMock(return_value=job_number),
    )
    monkeypatch.setattr(
        HomeServiceChatbotBookingService, "_validate_job_type_context", AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "app.engines.vertical_monetization.charge_service.create_charge_for_booking", AsyncMock(),
    )

    svc = HomeServiceFinalCreationService(db=db)
    svc.lock.check_and_raise_if_duplicate = AsyncMock(return_value=None)
    svc.lock.create_lock = AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4()))
    svc._audit = AsyncMock()
    svc._notify_booking_confirmed = AsyncMock()

    await svc.finalize(draft_id=draft.id, customer_id=draft.customer_id, idempotency_key=None, request_id="req-1")

    created_objects = [call.args[0] for call in db.add.call_args_list]
    return next(obj for obj in created_objects if obj.__class__.__name__ == "ServiceBooking")


_SAMPLE_SNAPSHOT = {
    "schema_version": 1,
    "answers": [{
        "question_id": "q-1", "question_key": "brand", "question_label": "What is your AC brand?",
        "question_type": "single_select", "answer_code": "LG", "answer_label": "LG", "sequence": 1,
    }],
}


class TestFinalizeAnswerSnapshot:
    @pytest.mark.asyncio
    async def test_finalize_stores_the_resolved_snapshot_on_the_dedicated_field(self, monkeypatch):
        draft = _draft()
        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalars(draft))
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.commit = AsyncMock()

        monkeypatch.setattr(
            QuestionFlowService, "build_answer_snapshot", AsyncMock(return_value=_SAMPLE_SNAPSHOT),
        )

        booking = await _run_finalize(draft, db, monkeypatch)

        assert booking.answer_snapshot == _SAMPLE_SNAPSHOT

    @pytest.mark.asyncio
    async def test_finalize_preserves_customer_photos_and_free_text_note(self, monkeypatch):
        draft = _draft(photo_urls=["https://res.cloudinary.com/demo/image/upload/problem.jpg"])
        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalars(draft))
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.commit = AsyncMock()
        snapshot = {
            "schema_version": 1,
            "answers": [{
                "question_id": "q-note", "question_key": "additional_note",
                "question_label": "Anything else we should know?", "question_type": "text",
                "answer_code": "Call before arrival", "answer_label": "Call before arrival",
                "sequence": 99,
            }],
        }
        monkeypatch.setattr(QuestionFlowService, "build_answer_snapshot", AsyncMock(return_value=snapshot))

        booking = await _run_finalize(draft, db, monkeypatch)

        assert booking.customer_photo_urls == draft.photo_urls
        assert booking.customer_photo_urls is not draft.photo_urls
        assert booking.customer_note == "Call before arrival"

    @pytest.mark.asyncio
    async def test_finalize_never_writes_answers_into_issue_details(self, monkeypatch):
        """The prior remediation overloaded `issue_details` -- audit found
        execution/mobile_inspection_service.py reads that column expecting
        an unrelated inspection-report shape. This must never regress."""
        draft = _draft(issue_details={"legacy": "inspection report shape, untouched"})
        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalars(draft))
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.commit = AsyncMock()

        monkeypatch.setattr(
            QuestionFlowService, "build_answer_snapshot", AsyncMock(return_value=_SAMPLE_SNAPSHOT),
        )

        booking = await _run_finalize(draft, db, monkeypatch)

        assert booking.issue_details == {"legacy": "inspection report shape, untouched"}
        assert booking.answer_snapshot == _SAMPLE_SNAPSHOT

    @pytest.mark.asyncio
    async def test_finalize_stores_no_snapshot_when_the_draft_has_no_answers(self, monkeypatch):
        draft = _draft(catalog_question_answers=None)
        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalars(draft))
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.commit = AsyncMock()

        monkeypatch.setattr(
            QuestionFlowService, "build_answer_snapshot", AsyncMock(return_value=None),
        )

        booking = await _run_finalize(draft, db, monkeypatch)

        assert booking.answer_snapshot is None


class TestBuildAnswerSnapshot:
    @pytest.mark.asyncio
    async def test_resolves_multi_select_answers_into_a_joined_label(self):
        draft = _draft(catalog_question_answers={"symptoms": ["not_cooling", "noisy"]})
        question = _question(question_key="symptoms", label="What symptoms?", input_type="multi_select")
        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalars([question]))
        svc = QuestionFlowService(db=db)
        svc.catalog = SimpleNamespace(_resolved_options=AsyncMock(return_value=[
            {"code": "not_cooling", "label": "Not cooling"}, {"code": "noisy", "label": "Noisy"},
        ]))

        snapshot = await svc.build_answer_snapshot(draft)

        assert snapshot["answers"][0]["answer_label"] == "Not cooling, Noisy"

    @pytest.mark.asyncio
    async def test_falls_back_to_the_raw_code_when_no_matching_option_label_exists(self):
        draft = _draft(catalog_question_answers={"brand": "UNKNOWN_CODE"})
        question = _question()
        db = MagicMock()
        db.execute = AsyncMock(return_value=_scalars([question]))
        svc = QuestionFlowService(db=db)
        svc.catalog = SimpleNamespace(_resolved_options=AsyncMock(return_value=[{"code": "LG", "label": "LG"}]))

        snapshot = await svc.build_answer_snapshot(draft)

        assert snapshot["answers"][0]["answer_label"] == "UNKNOWN_CODE"

    @pytest.mark.asyncio
    async def test_returns_none_when_the_draft_has_no_catalog_question_answers(self):
        draft = _draft(catalog_question_answers={})
        db = MagicMock()
        svc = QuestionFlowService(db=db)

        assert await svc.build_answer_snapshot(draft) is None
