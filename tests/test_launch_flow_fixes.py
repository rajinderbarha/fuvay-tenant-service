"""Flow fixes from the pre-launch audit (2026-09-22).

Each test pins one behaviour a real customer or technician ran into:
a job that died on a "no thanks" tap, a chat prompt that filed an unrelated
message as a complaint, a payment dispute nothing could ever unlock, a sweep
that aborted on the first busy provider, and the job updates an Instagram
customer was never sent.
"""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.messaging_gateway import booking_updates
from app.engines.messaging_gateway.service import _text_state_expired, _booking_progress


# ── The estimate that killed a fixed-price job ───────────────────────────────

def test_fixed_price_job_survives_a_declined_extra_estimate():
    """Declining optional extra work must not close the booked job.

    `customer_reject` only sends the job to `closed_estimate_declined` when
    the estimate IS the job's price. On a fixed-price job it is extra work,
    and the booked service (its payment, warranty and complaint window) has
    to carry on.
    """
    source = open(
        "app/engines/quote_checklist/quote_service.py", encoding="utf-8",
    ).read()
    reject = source[source.index("async def customer_reject"):source.index("async def customer_request_revision")]
    assert "quote_gates_work" in reject
    assert "JS_SERVICE_STARTED" in reject
    # The terminal status is reachable only through the gating branch.
    gating_branch = reject[reject.index("quote_gates_work"):reject.index("elif job.status")]
    assert "JS_CLOSED_ESTIMATE_DECLINED" in gating_branch


def test_reached_site_can_reach_quote_required():
    """A custom-quote job type is estimated on site, with no inspection step."""
    from app.engines.execution.constants import (
        JOB_TRANSITIONS, JS_QUOTE_REQUIRED, JS_REACHED_SITE,
    )
    assert JS_QUOTE_REQUIRED in JOB_TRANSITIONS[JS_REACHED_SITE]


def test_stuck_statuses_can_be_cancelled():
    """quote_required and customer_not_available were dead ends."""
    from app.engines.execution.constants import (
        JOB_TRANSITIONS, JS_CANCELLED, JS_CUSTOMER_NOT_AVAIL, JS_QUOTE_REQUIRED,
    )
    assert JS_CANCELLED in JOB_TRANSITIONS[JS_QUOTE_REQUIRED]
    assert JS_CANCELLED in JOB_TRANSITIONS[JS_CUSTOMER_NOT_AVAIL]


# ── Chat prompts that captured the wrong message ─────────────────────────────

def test_a_stale_describe_your_problem_prompt_expires():
    fresh = {"mode": "new", "since": datetime.now(timezone.utc).isoformat()}
    stale = {"mode": "new", "since": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()}
    assert _text_state_expired(fresh) is False
    assert _text_state_expired(stale) is True
    # Written before timestamps existed: never arm an unbounded prompt.
    assert _text_state_expired({"mode": "new"}) is True


@pytest.mark.asyncio
async def test_tapping_something_else_disarms_the_complaint_prompt():
    """The customer chose a complaint type, then tapped Confirm handover.

    Their next message ("thanks, all good") used to be filed as the complaint.
    """
    from app.engines.messaging_gateway import flow

    identity = AsyncMock()
    identity.clear_social_text_states = AsyncMock()
    identity.acknowledge_handover = AsyncMock(return_value="Handover confirmed.")
    thread = NS(id=uuid.uuid4(), zipcode="140412", customer_id=uuid.uuid4(),
                channel="instagram", ai_session_id=uuid.uuid4(),
                channel_user_id="igsid-1", channel_username=None, display_name=None,
                city="Kharar", last_options=None)
    db = AsyncMock()

    async def fake_draft(_db, _thread):
        return {"id": uuid.uuid4(), "status": "confirmed"}

    flow._draft = fake_draft  # type: ignore[assignment]
    await flow.advance(
        db, thread, text="", reply_id=f"ho{flow.PICKER_SEP}{uuid.uuid4()}{flow.PICKER_SEP}acknowledge",
        channel="instagram", identity=identity,
    )
    identity.clear_social_text_states.assert_awaited()


# ── The payment dispute that never ended ─────────────────────────────────────

def test_a_resolved_dispute_reconciles_the_payment():
    from app.engines.invoice_payment.direct_payments_constants import RS_CONFIRMED, RS_DISPUTED
    from app.engines.invoice_payment.direct_payments_service import (
        DirectPaymentsService, PAYMENT_DISPUTE_RESOLVED, dispute_is_open,
    )
    open_dispute = NS(dispute_complaint_id=uuid.uuid4(), payment_status="disputed",
                      customer_confirmed=False, customer_confirmation_action=None,
                      collected_amount=500, expected_amount=500, provider_confirmed_at=None,
                      customer_reported_amount=None)
    assert dispute_is_open(open_dispute) is True
    assert DirectPaymentsService.derive_status(open_dispute) == RS_DISPUTED

    open_dispute.payment_status = PAYMENT_DISPUTE_RESOLVED
    assert dispute_is_open(open_dispute) is False
    assert DirectPaymentsService.derive_status(open_dispute) == RS_CONFIRMED


@pytest.mark.asyncio
async def test_ending_a_payment_dispute_case_unlocks_the_record():
    from app.engines.invoice_payment import direct_payments_service as dps

    complaint = NS(id=uuid.uuid4(), complaint_type="payment_issue")
    pay = NS(dispute_complaint_id=complaint.id, payment_status="disputed",
             reconciliation_status="disputed", updated_at=None, customer_confirmed=False,
             customer_confirmation_action=None, collected_amount=500, expected_amount=500,
             provider_confirmed_at=None, customer_reported_amount=None)
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = pay
    db.execute.return_value = result
    db.add = MagicMock()

    await dps.release_payment_dispute(db, complaint, "resolved")
    assert pay.payment_status == dps.PAYMENT_DISPUTE_RESOLVED
    assert dps.dispute_is_open(pay) is False


def test_closure_accepts_the_technicians_customer_unavailable_handover():
    source = open(
        "app/engines/execution/mobile_direct_payment_service.py", encoding="utf-8",
    ).read()
    assert 'handover_status in ("acknowledged", "customer_unavailable")' in source


# ── The sweep that aborted on the first busy provider ────────────────────────

def test_auto_assignment_survives_a_provider_at_capacity():
    """`assert_wip_capacity` raises ServiceOSException, not ValueError.

    Catching only ValueError let one unscheduled job abort the whole sweep
    and roll back every other job's escalation event with it.
    """
    source = open("app/jobs/provider_assignment_timeout.py", encoding="utf-8").read()
    assert "except (ValueError, ServiceOSException) as exc:" in source
    assert "TERMINAL_JOB_STATUSES" in source  # workload counted on real statuses


# ── The updates an Instagram customer never received ─────────────────────────

@pytest.mark.asyncio
async def test_handover_request_reaches_the_bookings_own_chat(monkeypatch):
    customer_id, booking_id = uuid.uuid4(), uuid.uuid4()
    job = NS(id=uuid.uuid4(), booking_id=booking_id, assigned_staff_id=None)
    booking = NS(id=booking_id, customer_id=customer_id, booking_number="BK-77",
                 source_channel="instagram", source_actor_id="igsid-booker")
    thread = NS(id=uuid.uuid4(), channel="instagram", channel_user_id="igsid-booker",
                customer_id=customer_id, blocked_until=None, last_outbound_at=None,
                last_options=None)
    db = AsyncMock()
    db.get.return_value = booking
    result = MagicMock()
    result.scalars.return_value.first.return_value = thread
    db.execute.return_value = result
    monkeypatch.setattr(booking_updates.messaging_channel_config_service, "get",
                        AsyncMock(return_value={"access_token": "t"}))
    send = AsyncMock(return_value={"sent": True})
    monkeypatch.setattr(booking_updates.meta_client, "send_options", send)

    assert await booking_updates.send_handover_request(db, job) is True
    rows = send.call_args.args[2]
    assert any(str(job.id) in row["id"] for row in rows)
    # Confirming was the only move before; a problem must be reportable too.
    assert any(row["id"].startswith("cmp|") for row in rows)


@pytest.mark.asyncio
async def test_no_update_is_sent_outside_the_messaging_window(monkeypatch):
    booking = NS(id=uuid.uuid4(), customer_id=uuid.uuid4(), booking_number="BK-78",
                 source_channel="instagram", source_actor_id="igsid-booker")
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = None  # window closed
    db.execute.return_value = result
    send = AsyncMock()
    monkeypatch.setattr(booking_updates.meta_client, "send_text", send)

    assert await booking_updates.notify_booking_customer(db, booking, "hello") is False
    send.assert_not_awaited()


# ── Smaller promises the chat made and broke ─────────────────────────────────

def test_provider_accepted_is_not_shown_as_technician_assigned():
    assert _booking_progress("accepted", technician_assigned=False)[1] == "Step 1 of 4"
    assert _booking_progress("accepted", technician_assigned=True)[1] == "Step 2 of 4"


def test_a_price_range_is_never_called_a_total():
    from app.engines.messaging_gateway.flow import _is_price_range

    assert _is_price_range({"customer_min_price": 400, "customer_max_price": 900}) is True
    assert _is_price_range({"customer_min_price": 400, "customer_max_price": 400}) is False


def test_deadlines_are_shown_in_local_time():
    from app.engines.messaging_gateway.flow import _local_time

    assert _local_time("2026-09-22T09:16:00+00:00") == "22 Sep 2026, 02:46 PM IST"


def test_work_done_is_not_treated_as_completed_for_complaints():
    """Warranty only opens at `completed`; both refusing left no path."""
    from app.engines.complaints.constants import HOME_SERVICE_COMPLETED_STATUSES

    assert "work_done" not in HOME_SERVICE_COMPLETED_STATUSES
    assert "completed" in HOME_SERVICE_COMPLETED_STATUSES


def test_a_declined_estimate_job_can_still_be_complained_about():
    from app.engines.complaints.constants import ELIGIBLE_STATUSES, RECORD_SERVICE_JOB

    assert "closed_estimate_declined" in ELIGIBLE_STATUSES[RECORD_SERVICE_JOB]


def test_a_short_refund_cannot_close_the_case():
    source = open("app/engines/complaints/refund_service.py", encoding="utf-8").read()
    assert "recorded_amount < approved_cap" in source
