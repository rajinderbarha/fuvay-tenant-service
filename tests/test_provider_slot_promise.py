"""Provider-owned slot capacity + the promise the customer sees before confirming.

The PROVIDER configures their own business hours, slot length and how many
jobs they accept per slot (`provider_availability_rules`, scope_type=
'provider'). Technician allocation is entirely the provider's downstream
responsibility, so nothing here consults individual technicians.

Real gap these cover: providers could already configure slot length and
per-slot capacity through the provider portal, but NOTHING in the booking
pipeline read it -- bookings were accepted regardless of capacity and the
customer was never told when the service would actually happen. Jobs were
also created with NO schedule at all for the whole assistant flow, because
that flow never sets `preferred_date`.

Exercised against real live 140412/Guramrit data (no mocks).
"""
import datetime as dt
import uuid

import pytest

from app.engines.home_service_booking.provider_slot_service import (
    find_earliest_available_slot, list_available_slots, slot_has_capacity, _slots_from_rule,
    _window_label, FALLBACK_MAX_PER_SLOT, FALLBACK_SLOT_MINUTES,
    DEFAULT_MIN_LEAD_HOURS, EMERGENCY_MIN_LEAD_HOURS,
)

GURAMRIT_TENANT_ID = uuid.UUID("244beeec-fedc-452e-8054-317e45557d4d")


async def _get_db():
    from app.database import get_session_factory, init_db
    await init_db()
    return get_session_factory()()


async def _insert_live_job(db, tenant_id, day, window) -> uuid.UUID:
    """A capacity-consuming job in a specific slot."""
    from sqlalchemy import text
    jid = uuid.uuid4()
    await db.execute(text(
        "INSERT INTO service_jobs (id, job_number, booking_id, tenant_id, category_id, offering_id,"
        " scheduled_date, scheduled_time_window, status, assignment_status, created_at, updated_at)"
        " VALUES (:i,:n,:b,:t,"
        " (SELECT id FROM service_categories LIMIT 1),(SELECT id FROM master_services LIMIT 1),"
        " :d,:w,'pending_assignment','unassigned',now(),now())"),
        {"i": jid, "n": f"SLOTTEST-{str(jid)[:8]}", "b": uuid.uuid4(),
         "t": tenant_id, "d": day, "w": window})
    return jid


async def _cleanup_jobs(db, ids):
    from sqlalchemy import text
    if not ids:
        return
    await db.rollback()
    async with db.begin():
        await db.execute(text("DELETE FROM service_jobs WHERE id = ANY(:ids)"), {"ids": ids})


# ── Pure slot maths ─────────────────────────────────────────────────────────

def test_slots_are_generated_at_the_providers_configured_length():
    rule = {"start_time": "09:00", "end_time": "13:00",
            "slot_duration_minutes": 120, "max_bookings_per_slot": 2}
    assert [(_window_label(a, b)) for a, b in _slots_from_rule(rule)] == [
        "09:00-11:00", "11:00-13:00",
    ]


def test_a_partial_trailing_slot_is_never_offered():
    """09:00-12:30 at 60min yields 3 full hours -- never a 30-minute stub the
    provider did not agree to."""
    rule = {"start_time": "09:00", "end_time": "12:30", "slot_duration_minutes": 60}
    assert [_window_label(a, b) for a, b in _slots_from_rule(rule)] == [
        "09:00-10:00", "10:00-11:00", "11:00-12:00",
    ]


def test_unset_slot_length_falls_back_rather_than_producing_zero_slots():
    rule = {"start_time": "09:00", "end_time": "11:00", "slot_duration_minutes": None}
    slots = _slots_from_rule(rule)
    assert len(slots) == 120 // FALLBACK_SLOT_MINUTES


def test_an_inverted_or_empty_window_yields_no_slots():
    assert _slots_from_rule({"start_time": "18:00", "end_time": "09:00"}) == []
    assert _slots_from_rule({"start_time": None, "end_time": "09:00"}) == []


def test_unconfigured_capacity_defaults_to_one_never_unlimited():
    """An unset `max_bookings_per_slot` must never be read as "no limit" --
    that would silently overbook a provider who simply never filled it in."""
    assert FALLBACK_MAX_PER_SLOT == 1


# ── Live capacity behaviour ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_earliest_slot_is_resolved_for_a_real_provider():
    db = await _get_db()
    try:
        slot = await find_earliest_available_slot(db, tenant_id=GURAMRIT_TENANT_ID)
        assert slot is not None, "Guramrit has real availability rules configured"
        assert slot["capacity"] >= 1
        assert slot["already_booked"] < slot["capacity"]
        # Never offers a window that has already started.
        assert dt.datetime.fromisoformat(slot["starts_at"]) > dt.datetime.now()
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_a_full_slot_rolls_forward_to_the_next_one():
    """The core promise: once the provider's own per-slot limit is reached,
    the next customer is offered a LATER slot -- never the full one."""
    db = await _get_db()
    made = []
    try:
        first = await find_earliest_available_slot(db, tenant_id=GURAMRIT_TENANT_ID)
        assert first is not None
        day = dt.date.fromisoformat(first["date"])
        window = first["time_window"]

        for _ in range(first["capacity"] - first["already_booked"]):
            made.append(await _insert_live_job(db, GURAMRIT_TENANT_ID, day, window))
        await db.commit()

        assert await slot_has_capacity(
            db, tenant_id=GURAMRIT_TENANT_ID, day=day, time_window=window,
        ) is False

        nxt = await find_earliest_available_slot(db, tenant_id=GURAMRIT_TENANT_ID)
        assert nxt is not None
        assert (nxt["date"], nxt["time_window"]) != (first["date"], window)
    finally:
        await _cleanup_jobs(db, made)
        await db.close()


@pytest.mark.asyncio
async def test_cancelled_jobs_do_not_consume_capacity():
    """A day of cancellations must not permanently block a provider."""
    from sqlalchemy import text
    db = await _get_db()
    made = []
    try:
        first = await find_earliest_available_slot(db, tenant_id=GURAMRIT_TENANT_ID)
        day = dt.date.fromisoformat(first["date"])
        window = first["time_window"]
        for _ in range(first["capacity"]):
            made.append(await _insert_live_job(db, GURAMRIT_TENANT_ID, day, window))
        await db.execute(text(
            "UPDATE service_jobs SET status='cancelled' WHERE id = ANY(:ids)"), {"ids": made})
        await db.commit()

        assert await slot_has_capacity(
            db, tenant_id=GURAMRIT_TENANT_ID, day=day, time_window=window,
        ) is True
    finally:
        await _cleanup_jobs(db, made)
        await db.close()


@pytest.mark.asyncio
async def test_a_provider_with_no_availability_rules_gets_no_promise():
    """No configured availability must mean "we cannot promise a time",
    never a fabricated date the provider never agreed to."""
    db = await _get_db()
    try:
        slot = await find_earliest_available_slot(db, tenant_id=uuid.uuid4())
        assert slot is None
    finally:
        await db.close()


# ── Minimum lead time (6h normal / 2h emergency), on top of real hours ─────

def test_lead_time_defaults_are_the_product_specified_values():
    assert DEFAULT_MIN_LEAD_HOURS == 6.0
    assert EMERGENCY_MIN_LEAD_HOURS == 2.0


@pytest.mark.asyncio
async def test_a_slot_inside_the_lead_time_is_never_offered_even_if_technically_unstarted():
    """A slot 1 hour from now has not started, but 6 hours of lead time is
    required by default -- it must not be offered."""
    db = await _get_db()
    try:
        now = dt.datetime.now()
        soon = await find_earliest_available_slot(
            db, tenant_id=GURAMRIT_TENANT_ID, from_datetime=now, min_lead_hours=6.0,
        )
        if soon is not None:
            assert dt.datetime.fromisoformat(soon["starts_at"]) >= now + dt.timedelta(hours=6)
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_emergency_lead_time_can_surface_an_earlier_slot_than_the_default():
    """2 hours of lead time can only ever admit the SAME slots the 6-hour
    walk admits, or earlier ones -- never later, never a slot outside the
    provider's real configured hours."""
    db = await _get_db()
    try:
        now = dt.datetime.now()
        normal = await find_earliest_available_slot(db, tenant_id=GURAMRIT_TENANT_ID, from_datetime=now, min_lead_hours=6.0)
        emergency = await find_earliest_available_slot(db, tenant_id=GURAMRIT_TENANT_ID, from_datetime=now, min_lead_hours=2.0)
        assert emergency is not None, "Guramrit has real availability rules configured"
        assert dt.datetime.fromisoformat(emergency["starts_at"]) >= now + dt.timedelta(hours=2)
        if normal is not None:
            assert dt.datetime.fromisoformat(emergency["starts_at"]) <= dt.datetime.fromisoformat(normal["starts_at"])
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_list_available_slots_respects_the_same_lead_time_as_the_single_slot_resolver():
    db = await _get_db()
    try:
        now = dt.datetime.now()
        slots = await list_available_slots(db, tenant_id=GURAMRIT_TENANT_ID, from_datetime=now, min_lead_hours=6.0)
        for s in slots:
            assert dt.datetime.fromisoformat(s["starts_at"]) >= now + dt.timedelta(hours=6)
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_lead_time_never_bypasses_the_providers_real_working_hours():
    """Emergency shortens the LEAD TIME, not the provider's actual hours --
    a slot outside the provider's configured business hours must never
    appear, emergency or not."""
    db = await _get_db()
    try:
        now = dt.datetime.now()
        emergency_slots = await list_available_slots(db, tenant_id=GURAMRIT_TENANT_ID, from_datetime=now, min_lead_hours=2.0, max_results=20)
        for s in emergency_slots:
            day = dt.date.fromisoformat(s["date"])
            dow = day.isoweekday() % 7
            rules = await _provider_rules_for_day_helper(db, dow)
            windows = {_window_label(a, b) for r in rules for a, b in _slots_from_rule(r)}
            assert s["time_window"] in windows, "an emergency slot must still be one of the provider's real configured windows"
    finally:
        await db.close()


async def _provider_rules_for_day_helper(db, dow: int) -> list[dict]:
    from app.engines.home_service_booking.provider_slot_service import _provider_rules_for_day
    return await _provider_rules_for_day(db, GURAMRIT_TENANT_ID, dow)


# ── Letting the customer choose, instead of only seeing the system's pick ──

@pytest.mark.asyncio
async def test_list_available_slots_returns_the_same_earliest_slot_first():
    """The list and the single-slot resolver must agree on what "earliest"
    means -- they share the exact same walk and capacity rules."""
    db = await _get_db()
    try:
        earliest = await find_earliest_available_slot(db, tenant_id=GURAMRIT_TENANT_ID)
        slots = await list_available_slots(db, tenant_id=GURAMRIT_TENANT_ID)
        assert earliest is not None
        assert len(slots) >= 1
        assert (slots[0]["date"], slots[0]["time_window"]) == (earliest["date"], earliest["time_window"])
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_list_available_slots_respects_max_results():
    db = await _get_db()
    try:
        slots = await list_available_slots(db, tenant_id=GURAMRIT_TENANT_ID, max_results=3)
        assert 1 <= len(slots) <= 3
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_list_available_slots_never_offers_a_full_one():
    """Filling the first slot to capacity must remove it from the list, not
    just from the single-slot resolver."""
    db = await _get_db()
    made = []
    try:
        first = await find_earliest_available_slot(db, tenant_id=GURAMRIT_TENANT_ID)
        assert first is not None
        day = dt.date.fromisoformat(first["date"])
        window = first["time_window"]
        for _ in range(first["capacity"] - first["already_booked"]):
            made.append(await _insert_live_job(db, GURAMRIT_TENANT_ID, day, window))
        await db.commit()

        slots = await list_available_slots(db, tenant_id=GURAMRIT_TENANT_ID)
        assert not any((s["date"], s["time_window"]) == (first["date"], window) for s in slots)
    finally:
        await _cleanup_jobs(db, made)
        await db.close()


@pytest.mark.asyncio
async def test_list_available_slots_empty_for_a_provider_with_no_rules():
    db = await _get_db()
    try:
        assert await list_available_slots(db, tenant_id=uuid.uuid4()) == []
    finally:
        await db.close()


# ── The promise reaches the customer, and then the job ──────────────────────

@pytest.mark.asyncio
async def test_booking_summary_carries_the_promised_slot_and_sla():
    """The customer sees a real, capacity-checked slot BEFORE confirming."""
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
    from app.engines.home_service_booking.question_flow_service import QuestionFlowService
    from app.engines.home_service_booking.offering_catalog_service import list_serviceable_issues
    from sqlalchemy import text

    CUSTOMER_ID = uuid.UUID("fa198861-455b-43f2-a426-47da0a8811af")
    db = await _get_db()
    draft_id = None
    try:
        svc = HomeServiceChatbotBookingService(db=db)
        qf = QuestionFlowService(db=db)
        issues = (await list_serviceable_issues(db, "air-conditioning", "140412"))["issues"]
        cooling = next(i for i in issues if i["label"] == "AC Not Cooling")
        r = await svc.select_issue(
            customer_id=CUSTOMER_ID, ai_session_id=None,
            category_slug="air-conditioning", zipcode="140412", issue_id=cooling["id"],
        )
        draft_id = uuid.UUID(r["draft_id"])
        for _ in range(10):
            env = await qf.get_current_question(draft_id=draft_id, customer_id=CUSTOMER_ID)
            q = env.get("current_question")
            if not q:
                break
            opts = q.get("options") or []
            kw = {"option_id": opts[0]["id"]} if opts else {"value": "not cooling"}
            await qf.submit_answer(
                draft_id=draft_id, customer_id=CUSTOMER_ID, question_id=q["question_id"],
                expected_version=env.get("question_flow_version"), **kw,
            )
        await svc.check_serviceability(draft_id=draft_id, customer_id=CUSTOMER_ID)
        await svc.resolve_price_estimate(draft_id=draft_id, customer_id=CUSTOMER_ID)
        d = await svc.get_booking_draft(draft_id=draft_id, customer_id=CUSTOMER_ID)
        await svc.match_provider_and_price(
            category_id=uuid.UUID(d["category_id"]), master_service_id=uuid.UUID(d["offering_id"]),
            city=d["city"], zipcode=d.get("zipcode"),
            job_type_id=uuid.UUID(d["job_type_id"]) if d.get("job_type_id") else None,
            draft_id=draft_id, customer_id=CUSTOMER_ID, reveal_internal_score=False,
        )
        summary = (await svc.build_booking_summary(
            draft_id=draft_id, customer_id=CUSTOMER_ID,
        ))["booking_summary"]

        slot = summary["promised_slot"]
        assert slot is not None, "customer must be told when the service will happen"
        assert slot["time_window"] and slot["date"]
        # The commitment the provider is held to, and when it is due.
        assert summary["service_sla_minutes"] > 0
        assert summary["service_due_at"] == slot["ends_at"]
    finally:
        if draft_id:
            await db.rollback()
            async with db.begin():
                await db.execute(
                    text("DELETE FROM home_service_booking_drafts WHERE id=:i"), {"i": draft_id})
        await db.close()


@pytest.mark.asyncio
async def test_customer_can_choose_a_later_slot_than_the_system_pick():
    """The whole point: Review no longer has to accept the single
    system-chosen slot. Selecting a different, still-real slot overwrites
    `promised_slot` and the dependent SLA/due-at fields consistently."""
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
    from app.engines.home_service_booking.question_flow_service import QuestionFlowService
    from app.engines.home_service_booking.offering_catalog_service import list_serviceable_issues
    from sqlalchemy import text

    CUSTOMER_ID = uuid.UUID("fa198861-455b-43f2-a426-47da0a8811af")
    db = await _get_db()
    draft_id = None
    try:
        svc = HomeServiceChatbotBookingService(db=db)
        qf = QuestionFlowService(db=db)
        issues = (await list_serviceable_issues(db, "air-conditioning", "140412"))["issues"]
        cooling = next(i for i in issues if i["label"] == "AC Not Cooling")
        r = await svc.select_issue(
            customer_id=CUSTOMER_ID, ai_session_id=None,
            category_slug="air-conditioning", zipcode="140412", issue_id=cooling["id"],
        )
        draft_id = uuid.UUID(r["draft_id"])
        for _ in range(10):
            env = await qf.get_current_question(draft_id=draft_id, customer_id=CUSTOMER_ID)
            q = env.get("current_question")
            if not q:
                break
            opts = q.get("options") or []
            kw = {"option_id": opts[0]["id"]} if opts else {"value": "not cooling"}
            await qf.submit_answer(
                draft_id=draft_id, customer_id=CUSTOMER_ID, question_id=q["question_id"],
                expected_version=env.get("question_flow_version"), **kw,
            )
        await svc.check_serviceability(draft_id=draft_id, customer_id=CUSTOMER_ID)
        await svc.resolve_price_estimate(draft_id=draft_id, customer_id=CUSTOMER_ID)
        d = await svc.get_booking_draft(draft_id=draft_id, customer_id=CUSTOMER_ID)
        await svc.match_provider_and_price(
            category_id=uuid.UUID(d["category_id"]), master_service_id=uuid.UUID(d["offering_id"]),
            city=d["city"], zipcode=d.get("zipcode"),
            job_type_id=uuid.UUID(d["job_type_id"]) if d.get("job_type_id") else None,
            draft_id=draft_id, customer_id=CUSTOMER_ID, reveal_internal_score=False,
        )
        await svc.build_booking_summary(draft_id=draft_id, customer_id=CUSTOMER_ID)

        slots = (await svc.list_available_slots(draft_id=draft_id, customer_id=CUSTOMER_ID))["slots"]
        assert len(slots) >= 1
        chosen = slots[-1]  # pick something other than the system default (index 0)

        result = await svc.select_promised_slot(
            draft_id=draft_id, customer_id=CUSTOMER_ID,
            date_iso=chosen["date"], time_window=chosen["time_window"],
        )
        summary = result["booking_summary"]
        assert summary["promised_slot"]["date"] == chosen["date"]
        assert summary["promised_slot"]["time_window"] == chosen["time_window"]
        assert summary["service_due_at"] == summary["promised_slot"]["ends_at"]
    finally:
        if draft_id:
            await db.rollback()
            async with db.begin():
                await db.execute(
                    text("DELETE FROM home_service_booking_drafts WHERE id=:i"), {"i": draft_id})
        await db.close()


@pytest.mark.asyncio
async def test_selecting_a_slot_that_lost_capacity_is_rejected_not_silently_booked():
    """Re-validated at selection time, not trusted from the list response --
    another customer may have taken the last place in between."""
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
    from app.engines.home_service_booking.question_flow_service import QuestionFlowService
    from app.engines.home_service_booking.offering_catalog_service import list_serviceable_issues
    from sqlalchemy import text

    CUSTOMER_ID = uuid.UUID("fa198861-455b-43f2-a426-47da0a8811af")
    db = await _get_db()
    draft_id = None
    made = []
    try:
        svc = HomeServiceChatbotBookingService(db=db)
        qf = QuestionFlowService(db=db)
        issues = (await list_serviceable_issues(db, "air-conditioning", "140412"))["issues"]
        cooling = next(i for i in issues if i["label"] == "AC Not Cooling")
        r = await svc.select_issue(
            customer_id=CUSTOMER_ID, ai_session_id=None,
            category_slug="air-conditioning", zipcode="140412", issue_id=cooling["id"],
        )
        draft_id = uuid.UUID(r["draft_id"])
        for _ in range(10):
            env = await qf.get_current_question(draft_id=draft_id, customer_id=CUSTOMER_ID)
            q = env.get("current_question")
            if not q:
                break
            opts = q.get("options") or []
            kw = {"option_id": opts[0]["id"]} if opts else {"value": "not cooling"}
            await qf.submit_answer(
                draft_id=draft_id, customer_id=CUSTOMER_ID, question_id=q["question_id"],
                expected_version=env.get("question_flow_version"), **kw,
            )
        await svc.check_serviceability(draft_id=draft_id, customer_id=CUSTOMER_ID)
        await svc.resolve_price_estimate(draft_id=draft_id, customer_id=CUSTOMER_ID)
        d = await svc.get_booking_draft(draft_id=draft_id, customer_id=CUSTOMER_ID)
        await svc.match_provider_and_price(
            category_id=uuid.UUID(d["category_id"]), master_service_id=uuid.UUID(d["offering_id"]),
            city=d["city"], zipcode=d.get("zipcode"),
            job_type_id=uuid.UUID(d["job_type_id"]) if d.get("job_type_id") else None,
            draft_id=draft_id, customer_id=CUSTOMER_ID, reveal_internal_score=False,
        )
        summary = (await svc.build_booking_summary(draft_id=draft_id, customer_id=CUSTOMER_ID))["booking_summary"]
        slot = summary["promised_slot"]
        day = dt.date.fromisoformat(slot["date"])
        window = slot["time_window"]

        # Fill the slot to capacity behind the customer's back.
        for _ in range(slot.get("capacity", FALLBACK_MAX_PER_SLOT) or FALLBACK_MAX_PER_SLOT):
            made.append(await _insert_live_job(db, GURAMRIT_TENANT_ID, day, window))
        await db.commit()

        with pytest.raises(ValueError):
            await svc.select_promised_slot(
                draft_id=draft_id, customer_id=CUSTOMER_ID, date_iso=slot["date"], time_window=window,
            )
    finally:
        await _cleanup_jobs(db, made)
        if draft_id:
            await db.rollback()
            async with db.begin():
                await db.execute(
                    text("DELETE FROM home_service_booking_drafts WHERE id=:i"), {"i": draft_id})
        await db.close()


# ── The provider's own queue: what they are held to ─────────────────────────

@pytest.mark.asyncio
async def test_assignable_queue_exposes_the_deadline_the_provider_is_held_to():
    """"Assign technician" is the provider's next task, and the queue must be
    orderable by when each job is actually DUE -- derived from the slot the
    customer was promised, not from when the job happened to be created."""
    from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService

    db = await _get_db()
    made = []
    try:
        slot = await find_earliest_available_slot(db, tenant_id=GURAMRIT_TENANT_ID)
        assert slot is not None
        day = dt.date.fromisoformat(slot["date"])
        window = slot["time_window"]
        made.append(await _insert_live_job(db, GURAMRIT_TENANT_ID, day, window))
        await db.commit()

        svc = HomeServiceJobAssignmentService(db=db)
        jobs = await svc.list_assignable_jobs(
            tenant_id=GURAMRIT_TENANT_ID, assignment_status="unassigned", limit=50,
        )
        row = next(j for j in jobs if uuid.UUID(j["id"]) in made)

        # Deadline is the END of the promised window.
        assert row["service_due_at"] == dt.datetime.combine(
            day, dt.datetime.strptime(window.split("-")[-1], "%H:%M").time(),
        ).isoformat()
        assert row["minutes_until_due"] > 0
        assert row["is_overdue"] is False
    finally:
        await _cleanup_jobs(db, made)
        await db.close()


@pytest.mark.asyncio
async def test_a_job_with_no_slot_reports_no_deadline_rather_than_being_overdue():
    """A legacy job that never carried a slot has no recorded commitment --
    it must never be rendered as "overdue", which would be a fabricated
    breach the provider never agreed to."""
    from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
    from sqlalchemy import text

    db = await _get_db()
    made = []
    try:
        jid = uuid.uuid4()
        made.append(jid)
        await db.execute(text(
            "INSERT INTO service_jobs (id, job_number, booking_id, tenant_id, category_id, offering_id,"
            " status, assignment_status, created_at, updated_at)"
            " VALUES (:i,:n,:b,:t,"
            " (SELECT id FROM service_categories LIMIT 1),(SELECT id FROM master_services LIMIT 1),"
            " 'pending_assignment','unassigned',now(),now())"),
            {"i": jid, "n": f"NOSLOT-{str(jid)[:8]}", "b": uuid.uuid4(), "t": GURAMRIT_TENANT_ID})
        await db.commit()

        svc = HomeServiceJobAssignmentService(db=db)
        jobs = await svc.list_assignable_jobs(
            tenant_id=GURAMRIT_TENANT_ID, assignment_status="unassigned", limit=50,
        )
        row = next(j for j in jobs if uuid.UUID(j["id"]) == jid)
        assert row["service_due_at"] is None
        assert row["minutes_until_due"] is None
        assert row["is_overdue"] is False
    finally:
        await _cleanup_jobs(db, made)
        await db.close()
