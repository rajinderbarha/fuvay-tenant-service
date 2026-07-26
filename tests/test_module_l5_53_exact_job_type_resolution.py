"""HOME-SERVICES-RUNTIME-SAFETY Phase 2A.1 -- exact Job-Type workflow
resolution correction.

Covers the specific defect Phase 2A got wrong: one Master Service can
legitimately own multiple active Job Types (Repair, Installation, ...),
each with an independent ServiceJobWorkflow. Resolution must key off the
job's OWN job_type_id, never "how many job types does this service have".

Sections:
  1. Booking-draft Job Type selection validation (update_draft_fields).
  2. Booking/Job propagation at confirmation (finalize()).
  3. Migration 168 backfill reconciliation (unambiguous / ambiguous / invalid),
     against the real dev database.
  4. Live end-to-end proof: one real Master Service with both an active
     Repair Job Type (quote_approval_required=True) and an active
     Installation Job Type (quote_approval_required=False) -- Repair jobs
     are gated, Installation jobs are not, through the real
     HomeServiceJobExecutionService / ServiceJobQuoteService instances
     (not mocks) against the live database.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.exceptions import ServiceOSException


# ─────────────────────────────────────────────────────────────────────────────
# 1. Booking-draft Job Type validation
# ─────────────────────────────────────────────────────────────────────────────

class TestDraftJobTypeValidation:
    @pytest.mark.asyncio
    async def test_valid_active_job_type_for_service_is_stored(self):
        from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
        svc = HomeServiceChatbotBookingService(db=AsyncMock(), request_id=None)
        offering_id = uuid.uuid4()
        job_type_id = uuid.uuid4()
        draft = MagicMock()
        draft.offering_id = offering_id
        draft.status = "draft"

        link = MagicMock()
        link_result = MagicMock()
        link_result.scalars.return_value.first.return_value = link
        svc.db.execute = AsyncMock(return_value=link_result)

        with patch.object(svc, "_require_draft", AsyncMock(return_value=draft)):
            with patch.object(svc, "_assert_not_terminal", MagicMock()):
                with patch.object(svc, "_emit_event", AsyncMock()):
                    svc.db.commit = AsyncMock()
                    svc.db.refresh = AsyncMock()
                    with patch.object(svc, "_enrich_draft", AsyncMock(return_value={})):
                        await svc.update_draft_fields(
                            draft_id=uuid.uuid4(), customer_id=None,
                            payload={"job_type_id": str(job_type_id)},
                        )
        assert draft.job_type_id == job_type_id

    @pytest.mark.asyncio
    async def test_job_type_not_belonging_to_service_is_rejected(self):
        from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
        from app.engines.home_service_booking.constants import ERR_INVALID_JOB_TYPE_FOR_SERVICE
        svc = HomeServiceChatbotBookingService(db=AsyncMock(), request_id=None)
        draft = MagicMock()
        draft.offering_id = uuid.uuid4()
        draft.status = "draft"

        no_link_result = MagicMock()
        no_link_result.scalars.return_value.first.return_value = None
        svc.db.execute = AsyncMock(return_value=no_link_result)

        with patch.object(svc, "_require_draft", AsyncMock(return_value=draft)):
            with patch.object(svc, "_assert_not_terminal", MagicMock()):
                with pytest.raises(ServiceOSException) as exc:
                    await svc.update_draft_fields(
                        draft_id=uuid.uuid4(), customer_id=None,
                        payload={"job_type_id": str(uuid.uuid4())},
                    )
        assert exc.value.error_code == ERR_INVALID_JOB_TYPE_FOR_SERVICE


# ─────────────────────────────────────────────────────────────────────────────
# 2. Booking/Job propagation at confirmation
# ─────────────────────────────────────────────────────────────────────────────

class TestFinalizePropagation:
    @pytest.mark.asyncio
    async def test_finalize_copies_draft_job_type_to_booking_and_job(self):
        from app.engines.final_records.creation_service import HomeServiceFinalCreationService
        from app.engines.home_service_booking.models import HomeServiceBookingDraft

        job_type_id = uuid.uuid4()
        draft = MagicMock(spec=HomeServiceBookingDraft)
        draft.id = uuid.uuid4()
        draft.customer_id = uuid.uuid4()
        draft.selected_tenant_id = uuid.uuid4()
        draft.category_id = uuid.uuid4()
        draft.offering_id = uuid.uuid4()
        draft.job_type_id = job_type_id
        draft.master_service_job_type_id = uuid.uuid4()
        draft.service_job_workflow_id = uuid.uuid4()
        draft.selected_problem_id = None
        draft.ai_session_id = None
        draft.customer_name = "Test"
        draft.customer_phone = "9999999999"
        draft.city = "Blr"
        draft.zipcode = "560001"
        draft.address_snapshot = None
        draft.preferred_date = None
        draft.preferred_time_window = None
        draft.price_snapshot = None
        draft.selected_provider_snapshot = None
        draft.issue_summary = None
        draft.issue_details = None
        draft.booking_summary = {}
        draft.status = "ready_for_confirmation"

        svc = HomeServiceFinalCreationService(db=AsyncMock())
        svc.lock.check_and_raise_if_duplicate = AsyncMock(return_value=None)

        db = svc.db
        db.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(
            return_value=MagicMock(first=MagicMock(return_value=draft)))))
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.commit = AsyncMock()

        # Phase 2A.2: finalize() independently revalidates Job Type context
        # via HomeServiceChatbotBookingService._validate_job_type_context --
        # this test proves PROPAGATION, not revalidation (covered by its own
        # dedicated tests), so short-circuit it to "valid".
        with patch("app.engines.home_service_booking.service.HomeServiceChatbotBookingService._validate_job_type_context",
                   AsyncMock(return_value=None)):
            with patch("app.engines.final_records.creation_service.generate_booking_number", AsyncMock(return_value="B-1")):
                with patch("app.engines.final_records.creation_service.generate_job_number", AsyncMock(return_value="J-1")):
                    with patch.object(svc, "_audit", AsyncMock()):
                        await svc.finalize(draft_id=draft.id)

        added = [c.args[0] for c in db.add.call_args_list]
        booking = next(o for o in added if type(o).__name__ == "ServiceBooking")
        job = next(o for o in added if type(o).__name__ == "ServiceJob")
        assert booking.job_type_id == job_type_id
        assert job.job_type_id == job_type_id
        assert booking.job_type_id == job.job_type_id
        assert booking.service_job_workflow_id == draft.service_job_workflow_id
        assert job.service_job_workflow_id == draft.service_job_workflow_id
        assert booking.master_service_job_type_id == draft.master_service_job_type_id


# ─────────────────────────────────────────────────────────────────────────────
# 3 & 4. Live database: migration reconciliation + Repair-vs-Installation
#         end-to-end proof under one real Master Service.
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_migration_backfill_unambiguous_ambiguous_invalid_live():
    import importlib.util
    from app.database import get_session_factory, init_db
    from sqlalchemy import text

    spec = importlib.util.spec_from_file_location(
        "mig168", "alembic/versions/168_exact_job_type_workflow_resolution.py",
    )
    mig168 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig168)  # type: ignore

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        conn = await db.connection()
        raw = await conn.get_raw_connection()

        cat_id = uuid.uuid4()
        ms_unambiguous = uuid.uuid4()
        ms_ambiguous = uuid.uuid4()
        ms_invalid = uuid.uuid4()
        jt_repair = uuid.uuid4()
        jt_install = uuid.uuid4()

        await db.execute(text(
            "INSERT INTO job_types (id, key, label, is_active, created_at, updated_at) "
            "VALUES (:id, :key, :label, true, now(), now())"
        ), {"id": jt_repair, "key": f"repair_{jt_repair.hex[:6]}", "label": "Repair"})
        await db.execute(text(
            "INSERT INTO job_types (id, key, label, is_active, created_at, updated_at) "
            "VALUES (:id, :key, :label, true, now(), now())"
        ), {"id": jt_install, "key": f"install_{jt_install.hex[:6]}", "label": "Installation"})

        for ms_id, name in [(ms_unambiguous, "Unambig Svc"), (ms_ambiguous, "Ambig Svc"), (ms_invalid, "Invalid Svc")]:
            await db.execute(text(
                "INSERT INTO master_services (id, category_id, service_name, slug, job_type, is_active, "
                "created_at, updated_at) VALUES (:id, :cat, :name, :slug, 'repair', true, now(), now())"
            ), {"id": ms_id, "cat": cat_id, "name": name, "slug": f"{name.lower().replace(' ', '-')}-{ms_id.hex[:6]}"})

        # ms_unambiguous: exactly one active job-type link -> backfillable.
        await db.execute(text(
            "INSERT INTO master_service_job_types (id, master_service_id, job_type_id, is_active, "
            "display_order, created_at, updated_at) VALUES (:id, :ms, :jt, true, 0, now(), now())"
        ), {"id": uuid.uuid4(), "ms": ms_unambiguous, "jt": jt_repair})

        # ms_ambiguous: two active job-type links -> must stay unresolved.
        await db.execute(text(
            "INSERT INTO master_service_job_types (id, master_service_id, job_type_id, is_active, "
            "display_order, created_at, updated_at) VALUES (:id, :ms, :jt, true, 0, now(), now())"
        ), {"id": uuid.uuid4(), "ms": ms_ambiguous, "jt": jt_repair})
        await db.execute(text(
            "INSERT INTO master_service_job_types (id, master_service_id, job_type_id, is_active, "
            "display_order, created_at, updated_at) VALUES (:id, :ms, :jt, true, 0, now(), now())"
        ), {"id": uuid.uuid4(), "ms": ms_ambiguous, "jt": jt_install})

        # ms_invalid: no linked job types at all.

        booking_ids = {}
        for ms_id, label in [(ms_unambiguous, "u"), (ms_ambiguous, "a"), (ms_invalid, "i")]:
            bid = uuid.uuid4()
            booking_ids[label] = bid
            await db.execute(text(
                "INSERT INTO service_bookings (id, booking_number, draft_id, category_id, offering_id, "
                "status, assignment_status, created_at, updated_at) "
                "VALUES (:id, :num, :did, :cat, :off, 'pending_assignment', 'unassigned', now(), now())"
            ), {"id": bid, "num": f"BK-{bid.hex[:8]}", "did": uuid.uuid4(), "cat": cat_id, "off": ms_id})
        await db.commit()

        try:
            conn_sync = raw.driver_connection
            # Run the migration's own backfill function against this same
            # live database, targeting only service_bookings (service_jobs
            # backfill uses identical logic, proven by code path reuse).
            import asyncio

            def _run_backfill():
                import sqlalchemy
                sync_engine = sqlalchemy.create_engine(
                    str(db.bind.url).replace("+asyncpg", ""), )
                with sync_engine.connect() as sync_conn:
                    totals = mig168._backfill_unambiguous(sync_conn, "service_bookings")
                    sync_conn.commit()
                    return totals

            totals = await asyncio.to_thread(_run_backfill)

            unambig_row = (await db.execute(text(
                "SELECT job_type_id FROM service_bookings WHERE id = :id"
            ), {"id": booking_ids["u"]})).scalar()
            ambig_row = (await db.execute(text(
                "SELECT job_type_id FROM service_bookings WHERE id = :id"
            ), {"id": booking_ids["a"]})).scalar()
            invalid_row = (await db.execute(text(
                "SELECT job_type_id FROM service_bookings WHERE id = :id"
            ), {"id": booking_ids["i"]})).scalar()

            assert unambig_row == jt_repair, "unambiguous (exactly one active job type) must be backfilled"
            assert ambig_row is None, "ambiguous (2+ active job types) must NOT be guessed"
            assert invalid_row is None, "no linked job type at all must NOT be guessed"
        finally:
            for bid in booking_ids.values():
                await db.execute(text("DELETE FROM service_bookings WHERE id = :id"), {"id": bid})
            await db.execute(text("DELETE FROM master_service_job_types WHERE master_service_id = ANY(:ms)"),
                              {"ms": [ms_unambiguous, ms_ambiguous, ms_invalid]})
            await db.execute(text("DELETE FROM master_services WHERE id = ANY(:ms)"),
                              {"ms": [ms_unambiguous, ms_ambiguous, ms_invalid]})
            await db.execute(text("DELETE FROM job_types WHERE id = ANY(:jt)"), {"jt": [jt_repair, jt_install]})
            await db.commit()


@pytest.mark.asyncio
async def test_repair_vs_installation_same_master_service_live():
    """The exact scenario this correction slice exists to prove: ONE real
    Master Service with an active Repair Job Type (approval required) and
    an active Installation Job Type (approval not required) -- through the
    real (non-mocked) execution + quote services against the live database."""
    from app.database import get_session_factory, init_db
    from sqlalchemy import text
    from app.engines.execution.home_service_service import HomeServiceJobExecutionService
    from app.engines.quote_checklist.quote_service import ServiceJobQuoteService

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        cat_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        ms_id = uuid.uuid4()
        jt_repair = uuid.uuid4()
        jt_install = uuid.uuid4()

        await db.execute(text(
            "INSERT INTO job_types (id, key, label, is_active, created_at, updated_at) "
            "VALUES (:id, :key, 'Repair', true, now(), now())"
        ), {"id": jt_repair, "key": f"repair_{jt_repair.hex[:6]}"})
        await db.execute(text(
            "INSERT INTO job_types (id, key, label, is_active, created_at, updated_at) "
            "VALUES (:id, :key, 'Installation', true, now(), now())"
        ), {"id": jt_install, "key": f"install_{jt_install.hex[:6]}"})
        await db.execute(text(
            "INSERT INTO master_services (id, category_id, service_name, slug, job_type, is_active, "
            "created_at, updated_at) VALUES (:id, :cat, 'Air Conditioner', :slug, 'repair', true, now(), now())"
        ), {"id": ms_id, "cat": cat_id, "slug": f"ac-{ms_id.hex[:6]}"})
        for jt in (jt_repair, jt_install):
            await db.execute(text(
                "INSERT INTO master_service_job_types (id, master_service_id, job_type_id, is_active, "
                "display_order, created_at, updated_at) VALUES (:id, :ms, :jt, true, 0, now(), now())"
            ), {"id": uuid.uuid4(), "ms": ms_id, "jt": jt})
        await db.execute(text(
            "INSERT INTO service_job_workflow (id, master_service_id, job_type_id, inspection_required, "
            "quote_approval_required, checklist_required, schedule_required, address_required, "
            "technician_required, service_area_required, availability_required, pricing_behavior, "
            "created_at, updated_at) VALUES (:id, :ms, :jt, false, true, false, false, false, false, false, "
            "false, 'custom_quote', now(), now())"
        ), {"id": uuid.uuid4(), "ms": ms_id, "jt": jt_repair})
        await db.execute(text(
            "INSERT INTO service_job_workflow (id, master_service_id, job_type_id, inspection_required, "
            "quote_approval_required, checklist_required, schedule_required, address_required, "
            "technician_required, service_area_required, availability_required, pricing_behavior, "
            "created_at, updated_at) VALUES (:id, :ms, :jt, false, false, false, false, false, false, false, "
            "false, 'fixed', now(), now())"
        ), {"id": uuid.uuid4(), "ms": ms_id, "jt": jt_install})

        staff_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        job_ids = {}
        for label, jt in [("repair", jt_repair), ("install", jt_install)]:
            bid, jid = uuid.uuid4(), uuid.uuid4()
            job_ids[label] = jid
            await db.execute(text(
                "INSERT INTO service_bookings (id, booking_number, draft_id, category_id, offering_id, "
                "job_type_id, customer_id, status, assignment_status, created_at, updated_at) "
                "VALUES (:id, :num, :did, :cat, :off, :jt, :cust, 'pending_assignment', 'unassigned', now(), now())"
            ), {"id": bid, "num": f"BK-{bid.hex[:8]}", "did": uuid.uuid4(), "cat": cat_id, "off": ms_id, "jt": jt,
                "cust": customer_id})
            await db.execute(text(
                "INSERT INTO service_jobs (id, job_number, booking_id, category_id, offering_id, job_type_id, "
                "tenant_id, customer_id, assigned_staff_id, status, assignment_status, created_at, updated_at) "
                "VALUES (:id, :num, :bid, :cat, :off, :jt, :tid, :cust, :staff, 'inspection_done', 'assigned', now(), now())"
            ), {"id": jid, "num": f"J-{jid.hex[:8]}", "bid": bid, "cat": cat_id, "off": ms_id, "jt": jt,
                "tid": tenant_id, "cust": customer_id, "staff": staff_id})
        await db.commit()

        try:
            exec_svc = HomeServiceJobExecutionService()

            # Installation: no estimate exists anywhere, but approval is NOT
            # required for this job type -- must be allowed to start directly.
            install_job = (await db.execute(text(
                "SELECT * FROM service_jobs WHERE id = :id"
            ), {"id": job_ids["install"]})).mappings().first()
            from types import SimpleNamespace
            install_ns = SimpleNamespace(**dict(install_job))
            await exec_svc._assert_quote_approval_satisfied(db, install_ns)  # must not raise

            # Repair: approval IS required and no estimate exists -- must block.
            repair_job = (await db.execute(text(
                "SELECT * FROM service_jobs WHERE id = :id"
            ), {"id": job_ids["repair"]})).mappings().first()
            repair_ns = SimpleNamespace(**dict(repair_job))
            with pytest.raises(ServiceOSException) as exc:
                await exec_svc._assert_quote_approval_satisfied(db, repair_ns)
            assert exc.value.error_code == "ESTIMATE_REQUIRED"

            # Now create + send + approve a real quote for the Repair job via
            # the real (non-mocked) quote service, and prove work start
            # becomes allowed -- while Installation remains unaffected by any
            # of this (it never needed a quote in the first place).
            quote_svc = ServiceJobQuoteService()
            quote = await quote_svc.create_quote(
                db, str(job_ids["repair"]), str(tenant_id), "repair_quote",
                str(uuid.uuid4()), None, None, None,
            )
            await quote_svc.add_item(
                db, quote["id"], str(tenant_id), "labour", "Compressor repair", None,
                1, 1500, True, True, str(uuid.uuid4()), None,
            )
            sent = await quote_svc.send_to_customer(db, quote["id"], str(tenant_id), None, str(uuid.uuid4()), None)
            await quote_svc.customer_approve(
                db, quote["id"], str(customer_id), "idem-key-1", str(customer_id), None,
            )

            repair_job2 = (await db.execute(text(
                "SELECT * FROM service_jobs WHERE id = :id"
            ), {"id": job_ids["repair"]})).mappings().first()
            repair_ns2 = SimpleNamespace(**dict(repair_job2))
            await exec_svc._assert_quote_approval_satisfied(db, repair_ns2)  # must not raise now
        finally:
            await db.execute(text("DELETE FROM service_job_quote_events WHERE job_id = ANY(:jids)"),
                              {"jids": list(job_ids.values())})
            await db.execute(text("DELETE FROM service_job_quote_items WHERE job_id = ANY(:jids)"),
                              {"jids": list(job_ids.values())})
            await db.execute(text("DELETE FROM service_job_quotes WHERE job_id = ANY(:jids)"),
                              {"jids": list(job_ids.values())})
            await db.execute(text("DELETE FROM service_jobs WHERE id = ANY(:jids)"),
                              {"jids": list(job_ids.values())})
            await db.execute(text("DELETE FROM service_bookings WHERE offering_id = :ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM service_job_workflow WHERE master_service_id = :ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM master_service_job_types WHERE master_service_id = :ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM master_services WHERE id = :ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM job_types WHERE id = ANY(:jt)"), {"jt": [jt_repair, jt_install]})
            await db.commit()
