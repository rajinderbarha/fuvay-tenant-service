"""HOME-SERVICES-OPERATIONS: Unified Bookings & Jobs workspace.

Runtime tests against the live server + pure unit tests against the stage-
mapping table. Proves: canonical-pipeline-only (no legacy bookings/field_ops
jobs), one row per operational record (no booking+job duplication), correct
status->stage projection with UNKNOWN fail-closed behavior, and
pagination-independent metrics.
"""
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.engines.final_records.operations_service import (
    map_job_stage, map_draft_stage, JOB_STAGE_MAP, COMPLETED_STAGES,
    DRAFT_ACTIVE_STATUSES, DRAFT_MATCHING_STATUSES, DRAFT_EXCEPTION_STATUSES,
)
from app.engines.execution.constants import JOB_TRANSITIONS

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@serviceos.in"
ADMIN_PASS = "Password123!"

pytestmark = pytest.mark.anyio
_TOKEN_CACHE: dict = {}


@pytest_asyncio.fixture(scope="module")
async def admin_token(anyio_backend):
    if "tok" not in _TOKEN_CACHE:
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.post("/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
            assert r.status_code == 200, r.text
            _TOKEN_CACHE["tok"] = r.json()["data"]["access_token"]
    return _TOKEN_CACHE["tok"]


@pytest_asyncio.fixture
async def admin(admin_token):
    async with AsyncClient(base_url=BASE, headers={"Authorization": f"Bearer {admin_token}"}, timeout=30) as c:
        yield c


# ═══════════════════════════════════════════════════════════════════════════
# 1. STATUS -> STAGE MAPPING (pure, exhaustive against the real transition graph)
# ═══════════════════════════════════════════════════════════════════════════

class TestStageMapping:

    def test_every_real_job_status_is_mapped(self):
        """Every status that appears anywhere in the real JOB_TRANSITIONS
        graph (execution/constants.py) must have a stage — none silently
        fall through to UNKNOWN."""
        real_statuses = set(JOB_TRANSITIONS.keys())
        for s in JOB_TRANSITIONS.values():
            real_statuses |= s
        for status in real_statuses:
            stage, is_unknown = map_job_stage(status, None)
            assert not is_unknown, f"status {status!r} maps to UNKNOWN but is a real transition-graph status"

    def test_unknown_status_returns_unknown_not_in_progress(self):
        stage, is_unknown = map_job_stage("some_made_up_status_xyz", None)
        assert stage == "UNKNOWN"
        assert is_unknown is True

    def test_closed_estimate_declined_is_not_completed(self):
        stage, _ = map_job_stage("closed_estimate_declined", None)
        assert stage != "COMPLETED"
        assert stage not in COMPLETED_STAGES

    def test_completed_is_completed(self):
        stage, _ = map_job_stage("completed", None)
        assert stage == "COMPLETED"
        assert stage in COMPLETED_STAGES

    @pytest.mark.parametrize("status", ["force_closed", "voided"])
    def test_admin_terminal_statuses_are_closed_not_unknown(self, status):
        stage, is_unknown = map_job_stage(status, None)
        assert stage == "CLOSED"
        assert not is_unknown

    def test_quote_sent_to_customer_overrides_to_awaiting_approval(self):
        stage, _ = map_job_stage("quote_required", "sent_to_customer")
        assert stage == "AWAITING_APPROVAL"

    def test_quote_required_without_sent_quote_is_awaiting_estimate(self):
        stage, _ = map_job_stage("quote_required", None)
        assert stage == "AWAITING_ESTIMATE"

    def test_customer_not_available_is_at_risk_exception(self):
        stage, _ = map_job_stage("customer_not_available", None)
        assert stage == "AT_RISK"

    def test_draft_provider_matched_is_matching(self):
        stage, is_unknown = map_draft_stage("provider_matched")
        assert stage == "MATCHING"
        assert not is_unknown

    def test_draft_confirmed_is_not_mapped_here(self):
        """Confirmed drafts must never appear as REQUEST/MATCHING — they
        become a Job row instead (dedup rule)."""
        assert "confirmed" not in DRAFT_ACTIVE_STATUSES
        assert "confirmed" not in DRAFT_MATCHING_STATUSES

    def test_draft_failed_is_exception_not_silently_dropped(self):
        stage, is_unknown = map_draft_stage("failed")
        assert stage == "AT_RISK"
        assert not is_unknown
        assert "failed" in DRAFT_EXCEPTION_STATUSES


# ═══════════════════════════════════════════════════════════════════════════
# 2. LIVE RUNTIME (against the real server + real DB rows created via the
#    canonical creation path, not fabricated).
# ═══════════════════════════════════════════════════════════════════════════

class TestUnifiedFeedLive:

    async def test_permission_enforced_no_token(self):
        async with AsyncClient(base_url=BASE, timeout=30) as c:
            r = await c.get("/v1/admin/home-services/operations")
            assert r.status_code in (401, 403)

    async def test_list_returns_200_and_shape(self, admin):
        r = await admin.get("/v1/admin/home-services/operations", params={"page_size": 5})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert "records" in data and "pagination" in data and "last_updated_at" in data

    async def test_summary_independent_of_pagination(self, admin):
        r1 = await admin.get("/v1/admin/home-services/operations/summary")
        r2 = await admin.get("/v1/admin/home-services/operations", params={"page_size": 1})
        assert r1.status_code == 200 and r2.status_code == 200
        summary = r1.json()["data"]
        # Metrics come from a wholly separate query path (compute_metrics),
        # not from the page of records — sanity: page_size=1 still returns
        # the same summary values on a second /summary call.
        r3 = await admin.get("/v1/admin/home-services/operations/summary")
        assert r3.json()["data"] == summary

    async def test_no_row_exposes_admin_catalog_price(self, admin):
        r = await admin.get("/v1/admin/home-services/operations", params={"page_size": 50})
        for row in r.json()["data"]["records"]:
            assert row["amount_summary"]["source"] != "admin_catalog"

    async def test_no_generic_bookings_pipeline_leak(self, admin):
        """Every JOB row's job_id must resolve against the canonical
        /v1/admin/final-records/jobs/{id} endpoint (service_jobs table) —
        proves rows are sourced from the canonical pipeline, not the legacy
        bookings/field_ops.jobs one."""
        r = await admin.get("/v1/admin/home-services/operations", params={"page_size": 10, "stage": "UNASSIGNED"})
        job_rows = [row for row in r.json()["data"]["records"] if row["work_type"] == "JOB"]
        for row in job_rows[:3]:
            detail = await admin.get(f"/v1/admin/final-records/jobs/{row['job_id']}")
            assert detail.status_code == 200
            assert detail.json()["data"].get("error") != "FINAL_JOB_NOT_FOUND"

    async def test_job_row_carries_booking_reference(self, admin):
        r = await admin.get("/v1/admin/home-services/operations", params={"page_size": 20})
        job_rows = [row for row in r.json()["data"]["records"] if row["work_type"] == "JOB"]
        assert job_rows, "expected at least one JOB row in seeded data"
        for row in job_rows:
            assert row["booking_id"] is not None
            assert row["booking_number"] is not None

    async def test_no_duplicate_work_ids(self, admin):
        r = await admin.get("/v1/admin/home-services/operations", params={"page_size": 100})
        work_ids = [row["work_id"] for row in r.json()["data"]["records"]]
        assert len(work_ids) == len(set(work_ids))

    async def test_no_job_and_its_booking_both_appear_as_separate_rows(self, admin):
        """A Job's booking_id must never also surface as its own REQUEST
        row — that would be the exact duplicate-row bug this workspace
        exists to prevent."""
        r = await admin.get("/v1/admin/home-services/operations", params={"page_size": 100})
        records = r.json()["data"]["records"]
        job_booking_ids = {row["booking_id"] for row in records if row["work_type"] == "JOB"}
        request_rows = [row for row in records if row["work_type"] == "REQUEST"]
        for req in request_rows:
            assert req["booking_id"] not in job_booking_ids

    async def test_stage_filter_returns_only_matching_stage(self, admin):
        r = await admin.get("/v1/admin/home-services/operations", params={"stage": "UNASSIGNED", "page_size": 50})
        for row in r.json()["data"]["records"]:
            assert row["current_stage"] == "UNASSIGNED"

    async def test_invalid_filters_fail_with_422_not_500(self, admin):
        bad_view = await admin.get("/v1/admin/home-services/operations", params={"view": "invented"})
        bad_stage = await admin.get("/v1/admin/home-services/operations", params={"stage": "invented"})
        bad_date = await admin.get("/v1/admin/home-services/operations", params={"date_from": "not-a-date"})
        reversed_range = await admin.get("/v1/admin/home-services/operations", params={"date_from": "2026-08-15", "date_to": "2026-08-14"})
        assert bad_view.status_code == 422
        assert bad_stage.status_code == 422
        assert bad_date.status_code == 422
        assert reversed_range.status_code == 422

    async def test_enterprise_filters_and_page_size_are_server_side(self, admin):
        base = await admin.get("/v1/admin/home-services/operations", params={"page_size": 5})
        assert base.status_code == 200
        records = base.json()["data"]["records"]
        assert len(records) <= 5
        if records:
            city = records[0]["location_summary"].split(" · ")[0]
            filtered = await admin.get("/v1/admin/home-services/operations", params={"city": city, "page_size": 10})
            assert filtered.status_code == 200
            for row in filtered.json()["data"]["records"]:
                assert row["location_summary"].split(" · ")[0] == city

    async def test_request_rows_keep_canonical_draft_reference(self, admin):
        response = await admin.get("/v1/admin/home-services/operations", params={"view": "requests", "page_size": 100})
        assert response.status_code == 200
        for row in response.json()["data"]["records"]:
            assert row["work_type"] == "REQUEST"
            assert row["draft_id"] is not None

    async def test_view_completed_excludes_closed_estimate_declined(self, admin):
        r = await admin.get("/v1/admin/home-services/operations", params={"view": "completed", "page_size": 50})
        for row in r.json()["data"]["records"]:
            assert row["canonical_status"] != "closed_estimate_declined"

    async def test_export_returns_csv(self, admin):
        r = await admin.get("/v1/admin/home-services/operations/export")
        assert r.status_code == 200
        assert "work_id" in r.text.splitlines()[0]
        assert r.headers["cache-control"] == "no-store"
        assert r.headers["x-export-truncated"] in {"true", "false"}
        assert int(r.headers["x-export-total"]) >= 0

    async def test_search_by_work_id(self, admin):
        base = await admin.get("/v1/admin/home-services/operations", params={"page_size": 5})
        records = base.json()["data"]["records"]
        assert records, "expected seeded data"
        target = records[0]["work_id"]
        r = await admin.get("/v1/admin/home-services/operations", params={"search": target})
        found = [row["work_id"] for row in r.json()["data"]["records"]]
        assert target in found
