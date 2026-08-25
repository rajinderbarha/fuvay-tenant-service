"""MODULE-L5-27 — confirming a booking notifies the customer and the provider.

Finalizing a booking created the booking + job and emitted internal events, but
raised no user-facing notification: the customer got no bell confirmation and,
more importantly, the PROVIDER was never told a new booking had arrived — so they
had to poll to discover new work to assign. finalize now notifies both, as a
best-effort side-effect that can never break confirmation.
"""
from __future__ import annotations

import inspect
import uuid

import pytest


def test_finalize_notifies_both_parties_in_source():
    from app.engines.final_records import creation_service
    svc = creation_service.HomeServiceFinalCreationService
    finalize = inspect.getsource(svc.finalize)
    assert "_notify_booking_confirmed" in finalize, "finalize must notify on confirmation"

    helper = inspect.getsource(svc._notify_booking_confirmed)
    # Customer confirmation + provider "new booking".
    assert "booking.confirmed" in helper
    assert "booking.new" in helper
    assert "/customer/bookings/" in helper
    assert "owner_user_id" in helper  # resolves the provider recipient
    assert "InAppNotification" in helper


def test_notify_is_best_effort():
    """A notification failure must never break booking confirmation."""
    helper = inspect.getsource(
        __import__("app.engines.final_records.creation_service", fromlist=["x"])
        .HomeServiceFinalCreationService._notify_booking_confirmed)
    assert "except Exception" in helper and "pass" in helper


class TestBookingConfirmNotifyLive:
    @pytest.mark.asyncio
    async def test_finalizing_a_booking_notifies_customer_and_provider(self):
        import json
        import asyncpg
        from sqlalchemy import text
        from app.database import get_session_factory, init_db
        from app.engines.final_records.creation_service import HomeServiceFinalCreationService as Svc

        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            tmpl = await c.fetchrow(
                "SELECT sb.category_id, sb.offering_id, sb.tenant_id, sb.customer_id, t.owner_user_id, "
                "msjt.job_type_id, sjw.id AS workflow_id "
                "FROM service_bookings sb JOIN tenants t ON t.id = sb.tenant_id "
                "JOIN master_service_job_types msjt ON msjt.master_service_id=sb.offering_id AND msjt.is_active=true "
                "JOIN service_job_workflow sjw ON sjw.master_service_id=sb.offering_id "
                "AND sjw.job_type_id=msjt.job_type_id AND sjw.is_current=true AND sjw.status='published' "
                "WHERE sb.customer_id IS NOT NULL AND t.owner_user_id IS NOT NULL LIMIT 1")
            if not tmpl:
                pytest.skip("no booking template with an owner")
            did = uuid.uuid4()
            await c.execute(
                """INSERT INTO home_service_booking_drafts
                   (id, customer_id, category_id, offering_id, selected_tenant_id, job_type_id,
                    service_job_workflow_id, status,
                    booking_summary, price_snapshot, created_at, updated_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,'ready_for_confirmation',$8::jsonb,'{}'::jsonb,now(),now())""",
                did, tmpl["customer_id"], tmpl["category_id"], tmpl["offering_id"], tmpl["tenant_id"],
                tmpl["job_type_id"], tmpl["workflow_id"],
                json.dumps({"selected_price_tier": "standard", "customer_offer": 500}))
            cb = await c.fetchval(
                "SELECT count(*) FROM in_app_notifications WHERE user_id=$1 "
                "AND notification_type='booking.confirmed'", tmpl["customer_id"])
            pb = await c.fetchval(
                "SELECT count(*) FROM in_app_notifications WHERE user_id=$1 "
                "AND notification_type='booking.new'", tmpl["owner_user_id"])
        finally:
            await c.close()

        await init_db()
        async with get_session_factory()() as db:
            await Svc(db).finalize(draft_id=did, customer_id=tmpl["customer_id"], request_id="rid")
            await db.commit()

        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            ca = await c.fetchval(
                "SELECT count(*) FROM in_app_notifications WHERE user_id=$1 "
                "AND notification_type='booking.confirmed'", tmpl["customer_id"])
            pa = await c.fetchval(
                "SELECT count(*) FROM in_app_notifications WHERE user_id=$1 "
                "AND notification_type='booking.new'", tmpl["owner_user_id"])
        finally:
            await c.close()
        assert ca == cb + 1, "customer was not notified their booking is confirmed"
        assert pa == pb + 1, "provider was not notified of the new booking"
