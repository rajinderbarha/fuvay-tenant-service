"""TENANT-OPS-01 — Canonical Bookings & Jobs workspace.

Focused tests for the new status -> display-stage mapping
(app.engines.final_records.bookings_jobs_stage_mapping) and for the
home_service_assignment eligibility-gate fix that unblocked live seeding
against tenant 5209ef33-a53e-4fc0-b3f6-006335b8d712 ("Demo AC Services").

Not an exhaustive suite (time-boxed pass) — covers:
  1. Stage mapping for every real JOB_TRANSITIONS status (no invented statuses).
  2. Terminal vs active classification.
  3. next_action / available_actions never populated for terminal jobs.
  4. Regression test for the two real bugs fixed in
     home_service_assignment/service.py this session:
       - _job_requires_technician no longer references the nonexistent
         JobTypeDefinition.technician_required column.
       - list_eligible_staff_for_job compares tenant_services.id (not
         master_services.id) against supported_offering_ids.
"""
from __future__ import annotations
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.engines.execution.constants import (
    JS_PENDING_ASSIGNMENT, JS_ASSIGNED, JS_ACCEPTED, JS_SCHEDULED,
    JS_ON_THE_WAY, JS_REACHED_SITE, JS_INSPECTION_STARTED, JS_INSPECTION_DONE,
    JS_QUOTE_REQUIRED, JS_SERVICE_STARTED, JS_WORK_DONE,
    JS_CUSTOMER_NOT_AVAIL, JS_CANCELLED, JS_FAILED, JS_CLOSED_ESTIMATE_DECLINED,
)
from app.engines.final_records.bookings_jobs_stage_mapping import (
    map_job_status, compute_available_actions, TERMINAL_STATUSES,
)


# ── 1. Every real status maps to a stage, no invented statuses ────────────────

ALL_REAL_STATUSES = [
    JS_PENDING_ASSIGNMENT, JS_ASSIGNED, JS_ACCEPTED, JS_SCHEDULED,
    JS_ON_THE_WAY, JS_REACHED_SITE, JS_INSPECTION_STARTED, JS_INSPECTION_DONE,
    JS_QUOTE_REQUIRED, JS_SERVICE_STARTED, JS_WORK_DONE,
    JS_CUSTOMER_NOT_AVAIL, JS_CANCELLED, JS_FAILED, JS_CLOSED_ESTIMATE_DECLINED,
    "completed",
]


@pytest.mark.parametrize("status", ALL_REAL_STATUSES)
def test_every_real_status_maps_to_a_known_stage(status):
    result = map_job_status(status, assignment_status="assigned")
    assert result["stage"]
    assert result["stage_label"]
    assert isinstance(result["is_active"], bool)
    assert isinstance(result["is_terminal"], bool)


def test_pending_assignment_with_no_assignment_is_new_stage():
    result = map_job_status(JS_PENDING_ASSIGNMENT, assignment_status="unassigned")
    assert result["stage"] == "new"
    assert result["is_active"] is True
    assert result["next_action"]["action_key"] == "assign_technician"


def test_accepted_job_without_a_real_assignee_returns_to_dispatch():
    result = map_job_status(
        JS_ACCEPTED, assignment_status="accepted", has_assignee=False,
    )
    actions = compute_available_actions(
        JS_ACCEPTED, assignment_status="accepted", has_assignee=False,
    )

    assert result["stage"] == "new"
    assert result["next_action"]["action_key"] == "assign_technician"
    assert {action["action_key"] for action in actions} == {"assign_technician"}


def test_closed_estimate_declined_is_terminal_and_not_completed():
    """Spec requirement: closed_estimate_declined must be terminal and must
    NEVER be presented as 'Completed' (would falsely trigger monetization
    assumptions)."""
    result = map_job_status(JS_CLOSED_ESTIMATE_DECLINED, assignment_status="assigned")
    assert result["is_terminal"] is True
    assert result["stage"] != "completed"
    assert result["stage"] == "estimate_declined"
    assert result["next_action"] is None


def test_cancelled_and_completed_remain_distinct():
    completed = map_job_status("completed", assignment_status="assigned")
    cancelled = map_job_status(JS_CANCELLED, assignment_status="assigned")
    assert completed["stage"] != cancelled["stage"]
    assert completed["is_terminal"] and cancelled["is_terminal"]


@pytest.mark.parametrize("status", sorted(TERMINAL_STATUSES))
def test_terminal_statuses_never_expose_a_next_action(status):
    result = map_job_status(status, assignment_status="assigned")
    assert result["next_action"] is None
    assert result["is_active"] is False


def test_compute_available_actions_offers_assignment_when_unassigned():
    actions = compute_available_actions(JS_PENDING_ASSIGNMENT, "unassigned")
    keys = {a["action_key"] for a in actions}
    assert "assign_technician" in keys


def test_compute_available_actions_offers_payment_confirmation_on_work_done():
    actions = compute_available_actions(JS_WORK_DONE, "assigned")
    keys = {a["action_key"] for a in actions}
    assert "confirm_payment" in keys


def test_compute_available_actions_never_offers_cancel_on_terminal_job():
    for status in TERMINAL_STATUSES:
        actions = compute_available_actions(status, "assigned")
        keys = {a["action_key"] for a in actions}
        assert "cancel_assignment" not in keys


# ── 2. Regression tests for the two live-verified assignment-service bugs ─────

def _job(tenant_id: uuid.UUID, offering_id: uuid.UUID, job_type_id=None) -> MagicMock:
    from app.engines.final_records.models import ServiceJob
    j = MagicMock(spec=ServiceJob)
    j.id = uuid.uuid4()
    j.tenant_id = tenant_id
    j.offering_id = offering_id
    j.job_type_id = job_type_id
    j.service_job_workflow_id = None
    j.scheduled_date = None
    return j


@pytest.mark.asyncio
async def test_job_requires_technician_reads_the_canonical_workflow_column():
    """Regression for the live 500: _job_requires_technician used to SELECT
    JobTypeDefinition.technician_required, a column that has never existed
    on that model. It now reads ServiceJobWorkflow.technician_required,
    which is the canonical published blueprint field."""
    from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService

    row = MagicMock()
    row.scalar_one_or_none.return_value = True
    db = MagicMock()
    db.execute = AsyncMock(return_value=row)
    svc = HomeServiceJobAssignmentService(db)
    job = _job(uuid.uuid4(), uuid.uuid4(), job_type_id=uuid.uuid4())

    result = await svc._job_requires_technician(job)

    assert result is True
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_eligible_staff_matches_on_tenant_service_id_not_master_service_id():
    """Regression for the live no_matching_service_skill false-block: a
    technician whose supported_offering_ids contains the job's real
    tenant_services.id must be shown eligible, even though that id is
    nothing like the job's own master_services offering_id."""
    from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
    from app.engines.home_service_assignment.staff_model import ProviderTeamMember

    tenant_id = uuid.uuid4()
    master_service_id = uuid.uuid4()
    tenant_service_id = uuid.uuid4()  # deliberately a DIFFERENT id namespace

    job = _job(tenant_id, master_service_id)

    staff = MagicMock(spec=ProviderTeamMember)
    staff.id = uuid.uuid4()
    staff.tenant_id = tenant_id
    staff.status = "active"
    staff.can_receive_assignment = True
    staff.designation = "technician"
    staff.full_name = "Test Technician"
    staff.supported_offering_ids = [str(tenant_service_id)]
    staff.deleted_at = None

    db = MagicMock()
    db.info = {}
    load_job_result = MagicMock()
    load_job_result.scalar_one_or_none = MagicMock(return_value=job)

    staff_scalars = MagicMock()
    staff_scalars.all.return_value = [staff]
    staff_result = MagicMock()
    staff_result.scalars.return_value = staff_scalars

    tenant_service_row = MagicMock()
    tenant_service_row.__getitem__ = lambda self, i: str(tenant_service_id)

    async def fake_execute(query, *args, **kwargs):
        # naive dispatch by query type — mirrors the two real DB
        # round-trips list_eligible_staff_for_job now makes: staff list,
        # then the tenant_service_id resolution, then availability checks.
        text_query = str(query)
        if "tenant_services" in text_query:
            fetchone_result = MagicMock()
            fetchone_result.fetchone.return_value = tenant_service_row
            return fetchone_result
        if "provider_availability_rules" in text_query:
            r = MagicMock()
            r.fetchone.return_value = None
            return r
        return staff_result

    db.execute = AsyncMock(side_effect=fake_execute)

    svc = HomeServiceJobAssignmentService(db)

    async def fake_load_job(job_id):
        return job
    svc._load_job = fake_load_job

    result = await svc.list_eligible_staff_for_job(job.id, tenant_id)

    blocked_reasons = [r for s in result["blocked_staff"] for r in s["blocked_reasons"]]
    assert "no_matching_service_skill" not in blocked_reasons
