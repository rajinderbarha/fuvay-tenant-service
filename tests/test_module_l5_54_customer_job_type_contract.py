"""HOME-SERVICES-RUNTIME-SAFETY Phase 2A.2 -- Customer Job-Type Contract and
Blueprint Version Snapshot.

Sections:
  1. Problem -> Job Type resolution (ServiceIssueMapping), mocked unit tests.
  2. Offering-change clears stale Job Type/Blueprint context.
  3. Draft readiness gate (build_booking_summary / mark_ready_for_confirmation).
  4. finalize() independent revalidation.
  5. Quote creation blocked against a finally-rejected (terminal) job.
  6. LIVE: Blueprint Version stability -- Booking A stays on the version it
     was created against after an admin publishes a new version; Booking B
     (created after) uses the new version. Proven through the REAL
     HomeServiceChatbotBookingService.update_draft_fields /
     mark_ready_for_confirmation and HomeServiceFinalCreationService.finalize()
     methods (not direct guard calls) against the live database -- the
     actual customer draft -> confirmation -> ServiceBooking -> ServiceJob
     path, matching the standard set by Phase 2A.1's live proof.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.exceptions import ServiceOSException

TENANT_ID = uuid.uuid4()
CUSTOMER_ID = uuid.uuid4()


def _mock_draft(**overrides):
    from app.engines.home_service_booking.models import HomeServiceBookingDraft
    d = MagicMock(spec=HomeServiceBookingDraft)
    d.id = uuid.uuid4()
    d.customer_id = CUSTOMER_ID
    d.offering_id = uuid.uuid4()
    d.job_type_id = None
    d.master_service_job_type_id = None
    d.service_job_workflow_id = None
    d.selected_problem_id = None
    d.status = "collecting_details"
    for k, v in overrides.items():
        setattr(d, k, v)
    return d


def _first(item):
    r = MagicMock()
    r.scalars.return_value.first.return_value = item
    return r


class TestProblemToJobTypeResolution:
    @pytest.mark.asyncio
    async def test_problem_resolves_exact_job_type(self):
        from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
        svc = HomeServiceChatbotBookingService(db=AsyncMock())
        draft = _mock_draft()
        job_type_id = uuid.uuid4()

        mapping = MagicMock()
        mapping.job_type_id = job_type_id
        link = MagicMock()
        link.id = uuid.uuid4()
        workflow = MagicMock()
        workflow.id = uuid.uuid4()

        svc.db.execute = AsyncMock(side_effect=[_first(mapping), _first(link), _first(workflow)])
        with patch.object(svc, "_require_draft", AsyncMock(return_value=draft)):
            with patch.object(svc, "_assert_not_terminal", MagicMock()):
                with patch.object(svc, "_emit_event", AsyncMock()):
                    svc.db.commit = AsyncMock()
                    svc.db.refresh = AsyncMock()
                    with patch.object(svc, "_enrich_draft", AsyncMock(return_value={})):
                        await svc.update_draft_fields(
                            draft_id=draft.id, customer_id=None,
                            payload={"selected_problem_id": str(uuid.uuid4())},
                        )
        assert draft.job_type_id == job_type_id
        assert draft.master_service_job_type_id == link.id
        assert draft.service_job_workflow_id == workflow.id

    @pytest.mark.asyncio
    async def test_problem_from_another_service_rejected(self):
        from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
        svc = HomeServiceChatbotBookingService(db=AsyncMock())
        draft = _mock_draft()
        svc.db.execute = AsyncMock(return_value=_first(None))  # no mapping for this service
        with patch.object(svc, "_require_draft", AsyncMock(return_value=draft)):
            with patch.object(svc, "_assert_not_terminal", MagicMock()):
                with pytest.raises(ServiceOSException) as exc:
                    await svc.update_draft_fields(
                        draft_id=draft.id, customer_id=None,
                        payload={"selected_problem_id": str(uuid.uuid4())},
                    )
        assert exc.value.error_code == "PROBLEM_NOT_AVAILABLE_FOR_SERVICE"

    @pytest.mark.asyncio
    async def test_problem_without_job_type_mapping_leaves_draft_incomplete(self):
        """'Other problem'-style mapping (job_type_id NULL = applies to all)
        must NOT guess an exact Job Type."""
        from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
        svc = HomeServiceChatbotBookingService(db=AsyncMock())
        draft = _mock_draft()
        mapping = MagicMock()
        mapping.job_type_id = None  # "applies to all job types" -- not exact
        svc.db.execute = AsyncMock(return_value=_first(mapping))
        with patch.object(svc, "_require_draft", AsyncMock(return_value=draft)):
            with patch.object(svc, "_assert_not_terminal", MagicMock()):
                with patch.object(svc, "_emit_event", AsyncMock()):
                    svc.db.commit = AsyncMock()
                    svc.db.refresh = AsyncMock()
                    with patch.object(svc, "_enrich_draft", AsyncMock(return_value={})):
                        await svc.update_draft_fields(
                            draft_id=draft.id, customer_id=None,
                            payload={"selected_problem_id": str(uuid.uuid4())},
                        )
        assert draft.job_type_id is None


class TestOfferingChangeClearsStaleContext:
    @pytest.mark.asyncio
    async def test_changing_offering_clears_job_type_and_workflow_snapshot(self):
        from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
        svc = HomeServiceChatbotBookingService(db=AsyncMock())
        old_offering = uuid.uuid4()
        draft = _mock_draft(
            offering_id=old_offering, job_type_id=uuid.uuid4(),
            master_service_job_type_id=uuid.uuid4(), service_job_workflow_id=uuid.uuid4(),
            selected_problem_id=uuid.uuid4(), price_snapshot={"x": 1},
            selected_provider_snapshot={"y": 1}, selected_tenant_id=uuid.uuid4(),
        )
        new_offering = uuid.uuid4()
        svc.db.commit = AsyncMock()
        svc.db.refresh = AsyncMock()
        with patch.object(svc, "_require_draft", AsyncMock(return_value=draft)):
            with patch.object(svc, "_assert_not_terminal", MagicMock()):
                with patch.object(svc, "_emit_event", AsyncMock()):
                    with patch.object(svc, "_enrich_draft", AsyncMock(return_value={})):
                        await svc.update_draft_fields(
                            draft_id=draft.id, customer_id=None,
                            payload={"offering_id": str(new_offering)},
                        )
        assert draft.offering_id == new_offering
        assert draft.job_type_id is None
        assert draft.master_service_job_type_id is None
        assert draft.service_job_workflow_id is None
        assert draft.selected_problem_id is None
        assert draft.price_snapshot is None
        assert draft.selected_tenant_id is None


class TestReadinessGate:
    @pytest.mark.asyncio
    async def test_missing_job_type_reported_in_summary(self):
        from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
        from app.engines.admin_catalog.models import MasterService
        svc = HomeServiceChatbotBookingService(db=AsyncMock())
        draft = _mock_draft(
            issue_summary="x", city="Blr", zipcode="1", preferred_date=None,
            selected_tenant_id=None, selected_provider_snapshot=None,
            price_snapshot=None, booking_summary={},
        )
        offering = MagicMock(spec=MasterService)
        offering.service_name = "AC"
        offering.slug = "ac"
        offering.is_type_required = False
        offering.is_brand_required = False
        offering.requires_schedule = False

        with patch.object(svc, "_require_draft", AsyncMock(return_value=draft)):
            with patch.object(svc, "_get_offering", AsyncMock(return_value=offering)):
                with patch.object(svc, "_emit_event", AsyncMock()):
                    svc.db.commit = AsyncMock()
                    svc.db.refresh = AsyncMock()
                    result = await svc.build_booking_summary(draft_id=draft.id)
        summary = result["booking_summary"]
        assert summary["ready_for_confirmation"] is False
        assert "job_type" in summary["missing"]
        assert summary["errors"][0]["code"] == "JOB_TYPE_REQUIRED"

    @pytest.mark.asyncio
    async def test_mark_ready_blocked_by_unresolved_job_type(self):
        from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
        from app.engines.admin_catalog.models import MasterService
        svc = HomeServiceChatbotBookingService(db=AsyncMock())
        draft = _mock_draft(issue_summary="x", city="Blr")
        offering = MagicMock(spec=MasterService)
        offering.is_type_required = False
        offering.is_brand_required = False
        offering.requires_schedule = False

        with patch.object(svc, "_require_draft", AsyncMock(return_value=draft)):
            with patch.object(svc, "_assert_not_terminal", MagicMock()):
                with patch.object(svc, "_get_offering", AsyncMock(return_value=offering)):
                    with pytest.raises(ServiceOSException) as exc:
                        await svc.mark_ready_for_confirmation(draft_id=draft.id)
        assert exc.value.error_code == "JOB_TYPE_REQUIRED"


class TestFinalizeRevalidation:
    @pytest.mark.asyncio
    async def test_finalize_blocks_when_job_type_context_invalid(self):
        from app.engines.final_records.creation_service import HomeServiceFinalCreationService
        from app.engines.home_service_booking.models import HomeServiceBookingDraft

        draft = MagicMock(spec=HomeServiceBookingDraft)
        draft.id = uuid.uuid4()
        draft.customer_id = None
        draft.status = "ready_for_confirmation"

        svc = HomeServiceFinalCreationService(db=AsyncMock())
        svc.lock.check_and_raise_if_duplicate = AsyncMock(return_value=None)
        svc.db.execute = AsyncMock(return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=draft)))))

        with patch(
            "app.engines.home_service_booking.service.HomeServiceChatbotBookingService._validate_job_type_context",
            AsyncMock(return_value={"code": "JOB_TYPE_REQUIRED", "message": "x"}),
        ):
            with pytest.raises(ValueError, match="JOB_TYPE_REQUIRED"):
                await svc.finalize(draft_id=draft.id)
        # No Booking/Job may have been created.
        assert not svc.db.add.called


class TestFinalRejectionBlocksNewQuote:
    @pytest.mark.asyncio
    async def test_create_quote_blocked_for_closed_estimate_declined_job(self):
        from app.engines.quote_checklist.quote_service import ServiceJobQuoteService
        from app.engines.quote_checklist.constants import ERR_JOB_CLOSED_ESTIMATE_DECLINED
        svc = ServiceJobQuoteService()
        job = MagicMock()
        job.tenant_id = TENANT_ID
        job.status = "closed_estimate_declined"
        db = AsyncMock()
        with patch.object(svc, "_get_job", AsyncMock(return_value=job)):
            with pytest.raises(ValueError, match=ERR_JOB_CLOSED_ESTIMATE_DECLINED):
                await svc.create_quote(
                    db, str(uuid.uuid4()), str(TENANT_ID), "repair_quote",
                    str(uuid.uuid4()), None, None, None,
                )


# ─────────────────────────────────────────────────────────────────────────────
# 6. LIVE: Blueprint Version stability through the real customer path
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_blueprint_version_stability_through_real_finalize_path_live():
    """Booking A confirmed against workflow version 1; admin publishes
    version 2 (job_type_blueprint_service.set_workflow); Booking A's JOB
    keeps resolving version 1's requirements; a NEW booking created after
    resolves version 2. Driven through the REAL update_draft_fields,
    mark_ready_for_confirmation, and finalize() methods (not direct guard
    calls), against the live database."""
    from app.database import get_session_factory, init_db
    from sqlalchemy import text
    from app.engines.home_service_booking.service import HomeServiceChatbotBookingService
    from app.engines.home_service_booking.models import HomeServiceBookingDraft
    from app.engines.final_records.creation_service import HomeServiceFinalCreationService
    from app.engines.admin_catalog.job_type_blueprint_service import JobTypeBlueprintService
    from app.engines.execution.home_service_service import HomeServiceJobExecutionService

    await init_db()
    factory = get_session_factory()
    async with factory() as db:
        cat_id = uuid.uuid4()
        ms_id = uuid.uuid4()
        jt_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        customer_id = uuid.uuid4()

        await db.execute(text(
            "INSERT INTO job_types (id, key, label, is_active, created_at, updated_at) "
            "VALUES (:id, :key, 'Repair', true, now(), now())"
        ), {"id": jt_id, "key": f"repair_{jt_id.hex[:6]}"})
        await db.execute(text(
            "INSERT INTO master_services (id, category_id, service_name, slug, job_type, is_active, "
            "pricing_model, visit_fee, created_at, updated_at) "
            "VALUES (:id, :cat, 'AC', :slug, 'repair', true, 'fixed', 0, now(), now())"
        ), {"id": ms_id, "cat": cat_id, "slug": f"ac-{ms_id.hex[:6]}"})
        await db.execute(text(
            "INSERT INTO master_service_job_types (id, master_service_id, job_type_id, is_active, "
            "display_order, created_at, updated_at) VALUES (:id, :ms, :jt, true, 0, now(), now())"
        ), {"id": uuid.uuid4(), "ms": ms_id, "jt": jt_id})
        await db.commit()

        bp_svc = JobTypeBlueprintService(db)
        v1 = await bp_svc.set_workflow(ms_id, jt_id, {"quote_approval_required": True})
        assert v1["version_number"] == 1

        draft_a_id = uuid.uuid4()
        await db.execute(text(
            "INSERT INTO home_service_booking_drafts (id, category_id, offering_id, status, "
            "issue_summary, city, zipcode, selected_tenant_id, price_snapshot, booking_summary, "
            "customer_id, created_at, updated_at) "
            "VALUES (:id, :cat, :ms, 'collecting_details', 'not cooling', 'Blr', '560001', :tid, "
            "'{}'::jsonb, '{\"selected_price_tier\": \"standard\"}'::jsonb, :cust, now(), now())"
        ), {"id": draft_a_id, "cat": cat_id, "ms": ms_id, "tid": tenant_id, "cust": customer_id})
        await db.commit()

        booking_svc = HomeServiceChatbotBookingService(db=db)
        draft_a = (await db.execute(text(
            "SELECT * FROM home_service_booking_drafts WHERE id = :id"
        ), {"id": draft_a_id})).mappings().first()
        from types import SimpleNamespace
        draft_a_ns = SimpleNamespace(**dict(draft_a))
        await booking_svc._resolve_job_type_snapshot(draft_a_ns, jt_id)
        assert draft_a_ns.service_job_workflow_id == uuid.UUID(v1["id"])
        await db.execute(text(
            "UPDATE home_service_booking_drafts SET job_type_id = :jt, "
            "master_service_job_type_id = :link, service_job_workflow_id = :wf, "
            "status = 'ready_for_confirmation', serviceability_status = 'serviceable' "
            "WHERE id = :id"
        ), {"jt": jt_id, "link": draft_a_ns.master_service_job_type_id,
            "wf": draft_a_ns.service_job_workflow_id, "id": draft_a_id})
        await db.commit()

        final_svc = HomeServiceFinalCreationService(db=db)
        result_a = await final_svc.finalize(draft_id=draft_a_id, customer_id=customer_id)
        job_a_id = uuid.UUID(result_a["booking_id"])  # ServiceBooking.id; job created alongside

        job_a = (await db.execute(text(
            "SELECT * FROM service_jobs WHERE booking_id = :bid"
        ), {"bid": job_a_id})).mappings().first()
        assert job_a is not None
        assert str(job_a["service_job_workflow_id"]) == v1["id"]

        # Admin publishes version 2 -- MORE permissive this time.
        v2 = await bp_svc.set_workflow(ms_id, jt_id, {"quote_approval_required": False})
        assert v2["version_number"] == 2
        assert v2["id"] != v1["id"]

        try:
            exec_svc = HomeServiceJobExecutionService()
            job_a_ns = SimpleNamespace(**dict(job_a))
            workflow_for_a = await exec_svc._resolve_job_type_workflow(db, job_a_ns)
            assert str(workflow_for_a.id) == v1["id"], "Booking A must stay on version 1 forever"
            assert workflow_for_a.quote_approval_required is True

            # New Booking B, created AFTER v2 was published, must resolve v2.
            draft_b_id = uuid.uuid4()
            await db.execute(text(
                "INSERT INTO home_service_booking_drafts (id, category_id, offering_id, status, "
                "issue_summary, city, zipcode, selected_tenant_id, price_snapshot, booking_summary, "
                "customer_id, created_at, updated_at) "
                "VALUES (:id, :cat, :ms, 'collecting_details', 'not cooling', 'Blr', '560001', :tid, "
                "'{}'::jsonb, '{\"selected_price_tier\": \"standard\"}'::jsonb, :cust, now(), now())"
            ), {"id": draft_b_id, "cat": cat_id, "ms": ms_id, "tid": tenant_id, "cust": customer_id})
            await db.commit()
            draft_b = (await db.execute(text(
                "SELECT * FROM home_service_booking_drafts WHERE id = :id"
            ), {"id": draft_b_id})).mappings().first()
            draft_b_ns = SimpleNamespace(**dict(draft_b))
            await booking_svc._resolve_job_type_snapshot(draft_b_ns, jt_id)
            assert draft_b_ns.service_job_workflow_id == uuid.UUID(v2["id"]), "New draft must snapshot CURRENT version"
            await db.execute(text(
                "UPDATE home_service_booking_drafts SET job_type_id = :jt, "
                "master_service_job_type_id = :link, service_job_workflow_id = :wf, "
                "status = 'ready_for_confirmation', serviceability_status = 'serviceable' "
                "WHERE id = :id"
            ), {"jt": jt_id, "link": draft_b_ns.master_service_job_type_id,
                "wf": draft_b_ns.service_job_workflow_id, "id": draft_b_id})
            await db.commit()

            result_b = await final_svc.finalize(draft_id=draft_b_id, customer_id=customer_id)
            job_b = (await db.execute(text(
                "SELECT * FROM service_jobs WHERE booking_id = :bid"
            ), {"bid": uuid.UUID(result_b["booking_id"])})).mappings().first()
            assert str(job_b["service_job_workflow_id"]) == v2["id"]
            job_b_ns = SimpleNamespace(**dict(job_b))
            workflow_for_b = await exec_svc._resolve_job_type_workflow(db, job_b_ns)
            assert str(workflow_for_b.id) == v2["id"]
            assert workflow_for_b.quote_approval_required is False
        finally:
            await db.execute(text("DELETE FROM service_jobs WHERE offering_id = :ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM service_bookings WHERE offering_id = :ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM home_service_booking_drafts WHERE offering_id = :ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM final_creation_audit_logs WHERE result_id IN "
                                   "(SELECT id FROM service_bookings WHERE offering_id = :ms)"), {"ms": ms_id})
            await db.execute(text("DELETE FROM customer_booking_confirmations WHERE draft_id IN "
                                   "(SELECT id FROM home_service_booking_drafts WHERE offering_id = :ms)"), {"ms": ms_id})
            await db.execute(text("DELETE FROM service_job_workflow WHERE master_service_id = :ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM master_service_job_types WHERE master_service_id = :ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM master_services WHERE id = :ms"), {"ms": ms_id})
            await db.execute(text("DELETE FROM job_types WHERE id = :jt"), {"jt": jt_id})
            await db.commit()
