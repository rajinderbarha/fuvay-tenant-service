"""Post-completion rating requests in Instagram chat; all database and transport
calls are isolated."""
import json
import uuid
from types import SimpleNamespace as NS
from unittest.mock import ANY, AsyncMock

import pytest
from sqlalchemy.dialects import postgresql

from app.engines.customer_reviews.review_service import ReviewService
from app.engines.messaging_gateway import flow, meta_client, pickers, rating_request
from app.engines.messaging_gateway.config_service import messaging_channel_config_service
from app.engines.messaging_gateway.constants import (
    CHANNEL_INSTAGRAM, DURABLE_ACTION_PICKS, PICK_RATING,
)
from app.exceptions import ServiceOSException

IG = {"access_token": "ig-token", "instagram_account_id": "17890001", "api_version": "v26.0"}
BOOKING_ID = str(uuid.uuid4())


def _thread(**kw):
    values = dict(id=uuid.uuid4(), channel=CHANNEL_INSTAGRAM, channel_user_id="igsid-1",
                  customer_id=uuid.uuid4(), last_options=None, last_outbound_at=None,
                  zipcode=None, city=None)
    values.update(kw)
    return NS(**values)


# ── The question ─────────────────────────────────────────────────────────────


def test_five_ratings_worst_to_best_are_durable_taps():
    rows = rating_request.rating_rows(BOOKING_ID)
    assert [row["id"] for row in rows] == [f"rt|{BOOKING_ID}|{n}" for n in range(1, 6)]
    assert [row["title"] for row in rows] == ["1 ⭐", "2 ⭐⭐", "3 ⭐⭐⭐", "4 ⭐⭐⭐⭐", "5 ⭐⭐⭐⭐⭐"]
    assert all(pickers.is_picker_reply(row["id"]) for row in rows)
    # Rated hours later is the normal case, so a tap must never be read as
    # the opener of a new conversation.
    assert PICK_RATING in DURABLE_ACTION_PICKS


@pytest.mark.asyncio
async def test_instagram_shows_the_five_ratings_as_tappable_chips(monkeypatch):
    calls = []

    class Response:
        status_code = 200
        text = json.dumps({"message_id": "m-1"})

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, **kwargs):
            calls.append(kwargs["json"])
            return Response()

    monkeypatch.setattr(meta_client.httpx, "AsyncClient", Client)
    rows = rating_request.rating_rows(BOOKING_ID)
    result = await meta_client.send_options(
        "igsid-1", "How would you rate the service?", rows,
        channel=CHANNEL_INSTAGRAM, config=IG,
        list_button="Rate", section_title="Rate your service",
    )
    message = calls[0]["message"]
    assert calls[0]["recipient"] == {"id": "igsid-1"}
    assert message["text"] == "How would you rate the service?"
    assert [chip["payload"] for chip in message["quick_replies"]] == [row["id"] for row in rows]
    assert message["quick_replies"][-1]["title"] == "5 ⭐⭐⭐⭐⭐"
    assert result["numbered_options"] is False


@pytest.mark.parametrize("text, expected", [
    ("4", f"rt|{BOOKING_ID}|4"), (" 5 ", f"rt|{BOOKING_ID}|5"), ("1", f"rt|{BOOKING_ID}|1"),
    ("0", None), ("6", None), ("45", None), ("four", None), ("", None),
])
def test_a_typed_number_answers_an_open_rating_question(text, expected):
    thread = _thread(last_options=[row["id"] for row in rating_request.rating_rows(BOOKING_ID)])
    assert rating_request.typed_rating(thread, text) == expected


def test_a_typed_number_is_not_a_rating_under_any_other_list():
    categories = _thread(last_options=["cat|ac", "cat|plumbing"])
    assert rating_request.typed_rating(categories, "2") is None
    assert rating_request.typed_rating(_thread(last_options=None), "2") is None


# ── Asking, after the staff app completes the job ────────────────────────────


class _DB:
    def __init__(self, service_name="AC Repair"):
        self.offering = NS(service_name=service_name) if service_name else None
        self.commit = AsyncMock()

    async def get(self, _model, _key):
        return self.offering


@pytest.fixture
def ask(monkeypatch):
    """A completed, unrated booking whose customer has an open Instagram thread."""
    customer_id = uuid.uuid4()
    job = NS(id=uuid.uuid4(), offering_id=uuid.uuid4(), customer_id=customer_id)
    booking = NS(id=uuid.UUID(BOOKING_ID), booking_number="BK-1042", customer_id=customer_id)
    thread = _thread(customer_id=customer_id)
    state = NS(job=job, booking=booking, thread=thread, rated=None, sent=[],
               send_result={"sent": True, "numbered_options": False})

    async def completed(_db, job_id):
        return (state.job, state.booking) if job_id == state.job.id else None

    async def existing(_db, _customer_id, _booking_id):
        return state.rated

    async def reachable(_db, customer_id):
        return state.thread if customer_id == state.booking.customer_id else None

    async def send_options(to, body, rows, **kwargs):
        state.sent.append(NS(to=to, body=body, rows=rows, **kwargs))
        return state.send_result

    monkeypatch.setattr(rating_request, "_completed_booking", completed)
    monkeypatch.setattr(rating_request, "_existing_rating", existing)
    monkeypatch.setattr(rating_request, "_reachable_thread", reachable)
    monkeypatch.setattr(rating_request.meta_client, "send_options", send_options)
    state.warranty = AsyncMock(return_value=True)
    monkeypatch.setattr(rating_request.warranty_delivery, "send_warranty_certificate", state.warranty)
    monkeypatch.setattr(messaging_channel_config_service, "get", AsyncMock(return_value=IG))
    return state


@pytest.mark.asyncio
async def test_completion_asks_on_the_customers_open_instagram_thread(ask):
    assert await rating_request._ask(_DB(), ask.job.id) is True

    [sent] = ask.sent
    assert sent.to == "igsid-1"
    assert sent.channel == CHANNEL_INSTAGRAM and sent.config == IG
    assert sent.body.startswith("Your AC Repair booking BK-1042 is complete.")
    assert "reply with a number from 1 (poor) to 5 (excellent)" in sent.body
    assert sent.rows == rating_request.rating_rows(BOOKING_ID)
    # The typed-number answer only works because the options are remembered.
    assert ask.thread.last_options == [row["id"] for row in sent.rows]
    assert ask.thread.last_outbound_at is not None
    ask.warranty.assert_awaited_once_with(
        ANY, ask.job, ask.thread, config=IG,
    )


@pytest.mark.asyncio
async def test_warranty_follows_the_successful_rating_prompt_without_waiting_for_a_rating(ask):
    async def deliver(db, job, thread, *, config):
        assert len(ask.sent) == 1
        db.commit.assert_awaited_once()
        assert thread.last_options == [row["id"] for row in ask.sent[0].rows]
        assert ask.rated is None
        return True

    ask.warranty.side_effect = deliver
    assert await rating_request._ask(_DB(), ask.job.id) is True
    ask.warranty.assert_awaited_once()


@pytest.mark.asyncio
async def test_warranty_failure_keeps_the_successful_rating_question_open(ask):
    ask.warranty.return_value = False
    assert await rating_request._ask(_DB(), ask.job.id) is True
    assert ask.thread.last_options == [row["id"] for row in ask.sent[0].rows]


@pytest.mark.asyncio
async def test_the_prompt_reads_naturally_without_a_service_name(ask):
    await rating_request._ask(_DB(service_name=None), ask.job.id)
    assert ask.sent[0].body.startswith("Your booking BK-1042 is complete. How would you rate")


@pytest.mark.asyncio
async def test_an_open_numbered_list_is_not_taken_over(ask):
    """A customer halfway through a second booking keeps their typed numbers."""
    ask.thread.last_options = ["sl|2026-09-12|09:00-10:00", "sl|2026-09-12|10:00-11:00"]
    assert await rating_request._ask(_DB(), ask.job.id) is True
    assert ask.thread.last_options == ["sl|2026-09-12|09:00-10:00", "sl|2026-09-12|10:00-11:00"]


@pytest.mark.asyncio
async def test_a_booking_already_rated_in_the_app_gets_warranty_without_another_ask(ask):
    ask.rated = 5
    assert await rating_request._ask(_DB(), ask.job.id) is True
    assert ask.sent == []
    ask.warranty.assert_awaited_once_with(ANY, ask.job, ask.thread, config=IG)


@pytest.mark.asyncio
async def test_an_already_rated_booking_reports_a_failed_warranty_delivery(ask):
    ask.rated = 5
    ask.warranty.return_value = False
    assert await rating_request._ask(_DB(), ask.job.id) is False
    assert ask.sent == []


@pytest.mark.asyncio
async def test_nothing_is_sent_without_an_open_thread_or_a_completed_job(ask):
    ask.thread = None
    assert await rating_request._ask(_DB(), ask.job.id) is False
    assert await rating_request._ask(_DB(), uuid.uuid4()) is False
    assert ask.sent == []


@pytest.mark.asyncio
async def test_nothing_is_sent_while_the_channel_is_switched_off(ask, monkeypatch):
    monkeypatch.setattr(messaging_channel_config_service, "get", AsyncMock(return_value=None))
    assert await rating_request._ask(_DB(), ask.job.id) is False
    assert ask.sent == []


@pytest.mark.asyncio
async def test_a_failed_send_leaves_the_thread_untouched(ask):
    ask.send_result = {"sent": False, "reason": "transport_error"}
    assert await rating_request._ask(_DB(), ask.job.id) is False
    assert ask.thread.last_options is None and ask.thread.last_outbound_at is None
    ask.warranty.assert_not_awaited()


@pytest.mark.asyncio
async def test_asking_never_raises_into_the_completion(monkeypatch):
    """It runs after the staff app's response: a failure is logged, not raised."""
    import app.database

    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr(app.database, "_async_session_factory", lambda: session)

    monkeypatch.setattr(rating_request, "_ask", AsyncMock(return_value=True))
    assert await rating_request.send_rating_request(uuid.uuid4()) is True
    session.commit.assert_awaited_once()

    monkeypatch.setattr(rating_request, "_ask", AsyncMock(side_effect=RuntimeError("graph down")))
    assert await rating_request.send_rating_request(uuid.uuid4()) is False
    session.rollback.assert_awaited_once()

    assert await rating_request.send_rating_request("not-a-uuid") is False


@pytest.mark.asyncio
async def test_only_a_thread_that_can_answer_is_asked():
    """Taps on opted-out, agent-owned and blocked threads go unanswered, and
    Instagram refuses a business message after 24 quiet hours."""
    captured = {}

    class DB:
        async def execute(self, stmt):
            captured["stmt"] = stmt
            return NS(scalars=lambda: NS(first=lambda: None))

    assert await rating_request._reachable_thread(DB(), uuid.uuid4()) is None
    compiled = captured["stmt"].compile(dialect=postgresql.dialect())
    sql = " ".join(str(compiled).split())
    for predicate in (
        "messaging_threads.customer_id =",
        "messaging_threads.opted_out IS false",
        "messaging_threads.human_handoff IS false",
        "messaging_threads.blocked_until IS NULL OR messaging_threads.blocked_until <=",
        "messaging_threads.last_inbound_at >=",
        "ORDER BY messaging_threads.last_inbound_at DESC",
    ):
        assert predicate in sql
    in_lists = [list(v) for v in compiled.params.values() if isinstance(v, (list, tuple))]
    assert ["instagram"] in in_lists


# ── Answering ────────────────────────────────────────────────────────────────


@pytest.fixture
def answer(monkeypatch):
    thread = _thread()
    booking = NS(id=uuid.UUID(BOOKING_ID), tenant_id=uuid.uuid4(), customer_id=thread.customer_id)
    state = NS(thread=thread, booking=booking, rated=None, submitted=[], refusal=None)

    async def owned(_db, customer_id, booking_id):
        match = customer_id == state.booking.customer_id and booking_id == BOOKING_ID
        return state.booking if match else None

    async def existing(_db, _customer_id, _booking_id):
        return state.rated

    async def submit(self, db, **kwargs):
        if state.refusal:
            raise ValueError(state.refusal)
        state.submitted.append(kwargs)

    monkeypatch.setattr(rating_request, "_customer_booking", owned)
    monkeypatch.setattr(rating_request, "_existing_rating", existing)
    monkeypatch.setattr(ReviewService, "submit_review", submit)
    return state


@pytest.mark.asyncio
async def test_a_rating_is_saved_through_the_review_engine_by_booking(answer):
    note = await rating_request.record_rating(None, answer.thread, BOOKING_ID, "4")

    assert note == "Thank you! You rated this service 4/5 ⭐⭐⭐⭐"
    # The same record the customer app's rating screen writes, so one booking
    # can be rated once and the provider sees chat and app ratings alike.
    assert answer.submitted == [{
        "customer_id": answer.thread.customer_id, "tenant_id": answer.booking.tenant_id,
        "record_type": "service_booking", "record_id": answer.booking.id,
        "overall_rating": 4, "request_id": f"chat:{answer.thread.id}:rating",
    }]


@pytest.mark.asyncio
@pytest.mark.parametrize("stars", ["1", "2"])
async def test_a_low_rating_offers_a_person(answer, stars):
    note = await rating_request.record_rating(None, answer.thread, BOOKING_ID, stars)
    assert note.startswith(f"Thank you! You rated this service {stars}/5")
    assert "/human" in note


@pytest.mark.asyncio
async def test_a_good_rating_does_not_offer_a_complaint_route(answer):
    assert "/human" not in await rating_request.record_rating(None, answer.thread, BOOKING_ID, "3")


@pytest.mark.asyncio
async def test_a_second_rating_is_not_submitted(answer):
    answer.rated = 5
    note = await rating_request.record_rating(None, answer.thread, BOOKING_ID, "2")
    assert note == "You have already rated this service 5/5. Thank you!"
    assert answer.submitted == []


@pytest.mark.asyncio
@pytest.mark.parametrize("thread_kw, booking_id, stars", [
    ({"customer_id": None}, BOOKING_ID, "4"),        # unlinked chat
    ({"customer_id": uuid.uuid4()}, BOOKING_ID, "4"),  # someone else's booking
    ({}, str(uuid.uuid4()), "4"),                     # no such booking
    ({}, BOOKING_ID, "7"),                            # not a rating
    ({}, BOOKING_ID, ""),
])
async def test_a_rating_that_is_not_theirs_to_give_is_refused(answer, thread_kw, booking_id, stars):
    thread = answer.thread
    for key, value in thread_kw.items():
        setattr(thread, key, value)
    note = await rating_request.record_rating(None, thread, booking_id, stars)
    assert note == rating_request.RATING_UNAVAILABLE
    assert answer.submitted == []


@pytest.mark.asyncio
async def test_the_review_engine_decides_eligibility(answer):
    answer.refusal = "REVIEW_NOT_ELIGIBLE"
    note = await rating_request.record_rating(None, answer.thread, BOOKING_ID, "5")
    assert note == rating_request.RATING_UNAVAILABLE


@pytest.mark.asyncio
async def test_a_tap_naming_a_malformed_booking_never_queries():
    class DB:
        async def execute(self, _stmt):
            raise AssertionError("must not query")

    assert await rating_request._customer_booking(DB(), uuid.uuid4(), "not-a-uuid") is None


@pytest.mark.asyncio
@pytest.mark.parametrize("draft", [None, {"id": "draft-1", "status": "confirmed"}])
async def test_a_rating_tap_needs_no_pincode_and_survives_a_finished_booking(monkeypatch, draft):
    """After the idle reset there is no pincode, and the chat's own booking is
    long confirmed; neither gate may bounce the rating."""
    seen = []

    async def current(_db, _thread):
        return draft

    async def record(db, thread, booking_id, stars):
        seen.append((booking_id, stars))
        return "Thank you! You rated this service 5/5 ⭐⭐⭐⭐⭐"

    monkeypatch.setattr(flow, "_executor", lambda db, thread: None)
    monkeypatch.setattr(flow, "_draft", current)
    monkeypatch.setattr(rating_request, "record_rating", record)

    turn = await flow.advance(
        None, _thread(zipcode=None), text="5 ⭐⭐⭐⭐⭐",
        reply_id=f"rt|{BOOKING_ID}|5", channel=CHANNEL_INSTAGRAM,
    )
    assert seen == [(BOOKING_ID, "5")]
    assert turn.text.startswith("Thank you! You rated this service 5/5")
    assert [row["id"] for row in turn.picker["rows"]] == ["rs|1"]


# ── The trigger ──────────────────────────────────────────────────────────────


def _staff():
    from app.dependencies.auth import UserContext

    return UserContext(user_id=str(uuid.uuid4()), email="staff@serviceos.local",
                       role="technician", tenant_id=str(uuid.uuid4()),
                       full_name="Demo Staff", is_verified=True)


@pytest.mark.asyncio
async def test_completing_the_job_asks_for_a_rating_after_the_response(monkeypatch):
    from fastapi import BackgroundTasks

    from app.engines.execution import mobile_direct_payment_router as router_mod

    job_id = uuid.uuid4()
    monkeypatch.setattr(router_mod._svc, "finalize_job",
                        AsyncMock(return_value={"id": str(job_id), "status": "completed"}))
    tasks = BackgroundTasks()
    await router_mod.finalize_mobile_direct_payment(
        job_id, NS(state=NS(request_id="rid-1")), tasks, user=_staff(), db=AsyncMock(),
    )
    assert [(task.func, task.args) for task in tasks.tasks] == [
        (rating_request.send_rating_request, (job_id,)),
    ]


@pytest.mark.asyncio
async def test_a_refused_completion_asks_nothing(monkeypatch):
    from fastapi import BackgroundTasks

    from app.engines.execution import mobile_direct_payment_router as router_mod

    monkeypatch.setattr(router_mod._svc, "finalize_job", AsyncMock(side_effect=ServiceOSException(
        "JOB_NOT_READY_TO_FINALIZE", "Every closure requirement must pass.", status_code=409,
    )))
    tasks = BackgroundTasks()
    with pytest.raises(ServiceOSException):
        await router_mod.finalize_mobile_direct_payment(
            uuid.uuid4(), NS(state=NS(request_id="rid-1")), tasks, user=_staff(), db=AsyncMock(),
        )
    assert tasks.tasks == []


@pytest.mark.asyncio
async def test_tenant_portal_completion_schedules_the_same_instagram_followup(monkeypatch):
    from fastapi import BackgroundTasks

    from app.engines.execution import home_service_router as router_mod

    job_id = uuid.uuid4()
    monkeypatch.setattr(router_mod, "_staff_member_id", AsyncMock(return_value=uuid.uuid4()))
    monkeypatch.setattr(router_mod._svc, "complete_job",
                        AsyncMock(return_value={"id": str(job_id), "status": "completed"}))
    tasks = BackgroundTasks()
    db = AsyncMock()
    await router_mod.staff_complete_job(
        job_id,
        router_mod.CompleteJobBody(work_summary="Work completed", collected_amount=100),
        NS(state=NS(request_id="rid-portal")), tasks, user=_staff(), db=db,
    )
    db.commit.assert_awaited_once()
    assert [(task.func, task.args) for task in tasks.tasks] == [
        (rating_request.send_rating_request, (job_id,)),
    ]
