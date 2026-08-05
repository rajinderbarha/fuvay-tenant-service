"""Regression test for a physical-device-confirmed defect: AC Gas
Refilling simultaneously showed a date-selection quick-reply AND the
required "What's happening with the cooling?" catalog question, giving
the customer two competing actionable groups at once.

Root cause: `AIConversationService.send_message`'s date-quick-reply logic
only checked `still_needed` (a static diff of draft columns), completely
blind to whether the deterministic question-flow (QuestionFlowService)
still had an unanswered required question. The exact turn that resolved
`selected_problem_id` (making the cooling question active) also made
`preferred_date` appear in `still_needed`, so both were offered in the
same response.

Fix: `AIConversationService._catalog_questions_complete(draft_id)` -- a
new, deterministic guard that queries the real QuestionFlowService before
ever attaching date quick-replies. This test exercises that guard
directly against the real 140412 AC Gas Refilling data (no DeepSeek call
involved -- send_message itself calls the real DeepSeek API and is not
suitable for a fast, deterministic regression test; the guard function
this bug lived in is fully testable in isolation).
"""
import uuid

import pytest


AC_GAS_REFILLING_ID = uuid.UUID("b54e5517-ec51-4694-899b-04307e7f95bf")
AC_CATEGORY_ID = uuid.UUID("59d8f3aa-932d-429e-93bd-8d4f2ed615c3")
GURAMRIT_TENANT_ID = uuid.UUID("244beeec-fedc-452e-8054-317e45557d4d")
CUSTOMER_ID = uuid.UUID("fa198861-455b-43f2-a426-47da0a8811af")
ZIPCODE_140412 = "140412"


async def _get_db():
    from app.database import get_session_factory, init_db
    await init_db()
    factory = get_session_factory()
    return factory()


async def _resolve_job_type_context(db, master_service_id):
    from sqlalchemy import select
    from app.engines.admin_catalog.models import ServiceJobWorkflow

    workflow = (await db.execute(
        select(ServiceJobWorkflow).where(
            ServiceJobWorkflow.master_service_id == master_service_id,
            ServiceJobWorkflow.is_current.is_(True),
        )
    )).scalars().first()
    assert workflow is not None
    return workflow.job_type_id, workflow.id


async def _make_draft(db, *, with_problem_selected: bool):
    """A fresh AC Gas Refilling draft. With `with_problem_selected=True`,
    resolves job_type_id (mirroring what selecting the problem does) but
    leaves the actual cooling-symptom catalog question unanswered --
    exactly the state the screenshot was taken in."""
    from app.engines.home_service_booking.models import HomeServiceBookingDraft
    from app.engines.admin_catalog.models import MasterIssueType

    job_type_id, workflow_id = await _resolve_job_type_context(db, AC_GAS_REFILLING_ID)
    selected_problem_id = None
    if with_problem_selected:
        from sqlalchemy import select
        issue = (await db.execute(
            select(MasterIssueType).where(MasterIssueType.master_service_id == AC_GAS_REFILLING_ID)
        )).scalars().first()
        assert issue is not None, "AC Gas Refilling has no MasterIssueType -- run setup_140412_home_services.py"
        selected_problem_id = issue.id

    draft = HomeServiceBookingDraft(
        id=uuid.uuid4(),
        customer_id=CUSTOMER_ID,
        category_id=AC_CATEGORY_ID,
        offering_id=AC_GAS_REFILLING_ID,
        job_type_id=job_type_id if with_problem_selected else None,
        service_job_workflow_id=workflow_id if with_problem_selected else None,
        selected_problem_id=selected_problem_id,
        status="draft",
        city="Bassi Pathana",
        zipcode=ZIPCODE_140412,
        issue_summary="Not cooling",
    )
    db.add(draft)
    await db.flush()
    await db.commit()
    return draft


async def _cleanup(db, draft_id):
    from sqlalchemy import text
    await db.rollback()
    async with db.begin():
        await db.execute(text("DELETE FROM home_service_booking_drafts WHERE id = :id"), {"id": draft_id})


@pytest.mark.asyncio
async def test_catalog_questions_not_complete_while_required_question_unanswered():
    """The exact moment the screenshot captured: job_type_id/selected_
    problem_id just resolved, but the real cooling-symptom question has
    not been answered yet -- the guard must report NOT complete, so
    send_message never attaches date quick-replies in this state."""
    from app.engines.ai_conversation.service import AIConversationService

    db = await _get_db()
    draft = None
    try:
        draft = await _make_draft(db, with_problem_selected=True)
        svc = AIConversationService(db=db)
        complete = await svc._catalog_questions_complete(str(draft.id))
        assert complete is False, (
            "Guard reported catalog questions complete while the cooling "
            "question was still unanswered -- this is the exact double-"
            "question defect."
        )
    finally:
        if draft is not None:
            await _cleanup(db, draft.id)
        await db.close()


@pytest.mark.asyncio
async def test_catalog_questions_complete_after_answering_the_required_question():
    """Once the cooling-symptom question is actually answered, the guard
    must report complete -- this is what correctly allows date quick-
    replies to appear on a LATER turn, never the same one."""
    from app.engines.ai_conversation.service import AIConversationService
    from app.engines.home_service_booking.question_flow_service import QuestionFlowService

    db = await _get_db()
    draft = None
    try:
        draft = await _make_draft(db, with_problem_selected=True)

        qf = QuestionFlowService(db=db)
        envelope = await qf.get_current_question(draft_id=draft.id, customer_id=CUSTOMER_ID)
        question = envelope["current_question"]
        assert question is not None, "Expected a real cooling-symptom question to be active."
        option_id = question["options"][0]["id"]
        await qf.submit_answer(
            draft_id=draft.id, customer_id=CUSTOMER_ID,
            question_id=question["question_id"], option_id=option_id,
        )

        svc = AIConversationService(db=db)
        complete = await svc._catalog_questions_complete(str(draft.id))
        assert complete is True
    finally:
        if draft is not None:
            await _cleanup(db, draft.id)
        await db.close()


@pytest.mark.asyncio
async def test_catalog_questions_guard_fails_closed_when_job_type_not_yet_resolved():
    """A draft that hasn't even resolved a problem/job_type yet must also
    report NOT complete (fail closed), never assume readiness on an
    exception."""
    from app.engines.ai_conversation.service import AIConversationService

    db = await _get_db()
    draft = None
    try:
        draft = await _make_draft(db, with_problem_selected=False)
        svc = AIConversationService(db=db)
        complete = await svc._catalog_questions_complete(str(draft.id))
        assert complete is False
    finally:
        if draft is not None:
            await _cleanup(db, draft.id)
        await db.close()
