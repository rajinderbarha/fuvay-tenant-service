"""Sprint 20 — Home Service Job Assignment + Staff Lifecycle tests."""
from __future__ import annotations
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── helpers ───────────────────────────────────────────────────────────────────

def _job(
    assignment_status: str = "unassigned",
    status: str = "pending_assignment",
    tenant_id: uuid.UUID | None = None,
    staff_id: uuid.UUID | None = None,
) -> MagicMock:
    from app.engines.home_service_assignment.models import ServiceJobAssignment
    from app.engines.final_records.models import ServiceJob
    j = MagicMock(spec=ServiceJob)
    j.id               = uuid.uuid4()
    j.job_number       = "JOB-20260702-000001"
    j.booking_id       = uuid.uuid4()
    j.tenant_id        = tenant_id or uuid.uuid4()
    j.customer_id      = uuid.uuid4()
    j.category_id      = uuid.uuid4()
    j.offering_id      = uuid.uuid4()
    j.assigned_staff_id = staff_id
    j.status           = status
    j.assignment_status = assignment_status
    j.city             = "Jaipur"
    j.scheduled_date        = None
    j.scheduled_time_window = None
    j.to_dict = lambda: {
        "id": str(j.id), "job_number": j.job_number,
        "status": j.status, "assignment_status": j.assignment_status,
        "assigned_staff_id": str(j.assigned_staff_id) if j.assigned_staff_id else None,
        "tenant_id": str(j.tenant_id),
    }
    return j


def _staff(tenant_id: uuid.UUID, designation: str = "technician", status: str = "active") -> MagicMock:
    from app.engines.home_service_assignment.staff_model import ProviderTeamMember
    s = MagicMock(spec=ProviderTeamMember)
    s.id          = uuid.uuid4()
    s.tenant_id   = tenant_id
    s.full_name   = "Ali Technician"
    s.designation = designation
    s.status      = status
    s.can_receive_assignment = True
    return s


def _assignment(job_id: uuid.UUID, staff_id: uuid.UUID,
                status: str = "assigned", is_current: bool = True) -> MagicMock:
    from app.engines.home_service_assignment.models import ServiceJobAssignment
    a = MagicMock(spec=ServiceJobAssignment)
    a.id                     = uuid.uuid4()
    a.job_id                 = job_id
    a.booking_id             = uuid.uuid4()
    a.tenant_id              = uuid.uuid4()
    a.assigned_staff_member_id = staff_id
    a.assignment_status      = status
    a.is_current             = is_current
    a.scheduled_date         = None
    a.scheduled_time_window  = None
    a.accepted_at            = None
    a.rejected_at            = None
    a.cancelled_at           = None
    a.rejection_reason       = None
    a.assignment_type        = "manual"
    a.notes                  = None
    a.to_dict = lambda: {
        "id": str(a.id),
        "assignment_status": a.assignment_status,
        "is_current": a.is_current,
    }
    return a


def _db_returning(*results) -> AsyncMock:
    """Build a DB mock where each execute() call returns the next result in sequence."""
    db = AsyncMock()
    db.flush   = AsyncMock()
    db.refresh = AsyncMock()
    db.add     = MagicMock()
    db.commit  = AsyncMock()
    responses = []
    for r in results:
        res = MagicMock()
        res.scalars.return_value.first.return_value = r
        res.scalars.return_value.all.return_value = [r] if r else []
        responses.append(res)
    db.execute = AsyncMock(side_effect=responses)
    return db


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1 — Constants & Models
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_assignment_statuses(self):
        from app.engines.home_service_assignment.constants import (
            ASSIGN_STATUS_ASSIGNED, ASSIGN_STATUS_ACCEPTED,
            ASSIGN_STATUS_REJECTED, ASSIGN_STATUS_CANCELLED, ASSIGN_STATUS_REASSIGNED,
        )
        assert ASSIGN_STATUS_ASSIGNED  == "assigned"
        assert ASSIGN_STATUS_ACCEPTED  == "accepted"
        assert ASSIGN_STATUS_REJECTED  == "rejected"
        assert ASSIGN_STATUS_CANCELLED == "cancelled"
        assert ASSIGN_STATUS_REASSIGNED == "reassigned"

    def test_event_types_defined(self):
        from app.engines.home_service_assignment.constants import (
            EVENT_ASSIGNMENT_CREATED, EVENT_TECHNICIAN_ACCEPTED,
            EVENT_TECHNICIAN_REJECTED, EVENT_JOB_SCHEDULED,
        )
        assert EVENT_ASSIGNMENT_CREATED   == "assignment_created"
        assert EVENT_TECHNICIAN_ACCEPTED  == "technician_accepted"
        assert EVENT_TECHNICIAN_REJECTED  == "technician_rejected"
        assert EVENT_JOB_SCHEDULED        == "job_scheduled"

    def test_eligible_designations_include_technician(self):
        from app.engines.home_service_assignment.constants import ELIGIBLE_DESIGNATIONS
        assert "technician" in ELIGIBLE_DESIGNATIONS
        assert "field_staff" in ELIGIBLE_DESIGNATIONS
        assert "accountant" not in ELIGIBLE_DESIGNATIONS

    def test_error_codes_defined(self):
        from app.engines.home_service_assignment.constants import (
            ERR_JOB_NOT_FOUND, ERR_STAFF_NOT_FOUND, ERR_STAFF_WRONG_TENANT,
            ERR_STAFF_INACTIVE, ERR_ROLE_NOT_ALLOWED,
            ERR_STAFF_JOB_NOT_ASSIGNED, ERR_STAFF_JOB_ALREADY_ACCEPTED,
            ERR_STAFF_JOB_ALREADY_REJECTED, ERR_REASON_REQUIRED,
        )
        assert ERR_JOB_NOT_FOUND          == "JOB_ASSIGNMENT_JOB_NOT_FOUND"
        assert ERR_STAFF_WRONG_TENANT     == "JOB_ASSIGNMENT_STAFF_WRONG_TENANT"
        assert ERR_STAFF_INACTIVE         == "JOB_ASSIGNMENT_STAFF_INACTIVE"
        assert ERR_ROLE_NOT_ALLOWED       == "JOB_ASSIGNMENT_ROLE_NOT_ALLOWED"
        assert ERR_STAFF_JOB_NOT_ASSIGNED == "STAFF_JOB_NOT_ASSIGNED_TO_USER"
        assert ERR_REASON_REQUIRED        == "JOB_ASSIGNMENT_REASON_REQUIRED"


class TestModels:
    def test_service_job_assignment_tablename(self):
        from app.engines.home_service_assignment.models import ServiceJobAssignment
        assert ServiceJobAssignment.__tablename__ == "service_job_assignments"

    def test_service_job_assignment_event_tablename(self):
        from app.engines.home_service_assignment.models import ServiceJobAssignmentEvent
        assert ServiceJobAssignmentEvent.__tablename__ == "service_job_assignment_events"

    def test_provider_team_member_tablename(self):
        from app.engines.home_service_assignment.staff_model import ProviderTeamMember
        assert ProviderTeamMember.__tablename__ == "provider_team_members"

    def test_service_job_has_assignment_status(self):
        from app.engines.final_records.models import ServiceJob
        assert hasattr(ServiceJob, "assignment_status")

    def test_service_booking_has_assignment_status(self):
        from app.engines.final_records.models import ServiceBooking
        assert hasattr(ServiceBooking, "assignment_status")

    def test_assignment_to_dict(self):
        a = _assignment(uuid.uuid4(), uuid.uuid4())
        d = a.to_dict()
        assert "assignment_status" in d
        assert "is_current" in d


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2 — Staff Eligibility
# ═══════════════════════════════════════════════════════════════════════════════

class TestStaffEligibility:
    @pytest.mark.asyncio
    async def test_eligible_staff_passes(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        from app.engines.home_service_assignment.constants import ERR_STAFF_NOT_FOUND
        tenant_id = uuid.uuid4()
        job  = _job(tenant_id=tenant_id)
        st   = _staff(tenant_id=tenant_id, designation="technician", status="active")

        db   = _db_returning(st)
        svc  = HomeServiceJobAssignmentService(db)
        result_staff, blocked = await svc.validate_staff_eligibility(job, st.id)
        assert blocked == []

    @pytest.mark.asyncio
    async def test_inactive_staff_blocked(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        tenant_id = uuid.uuid4()
        job  = _job(tenant_id=tenant_id)
        st   = _staff(tenant_id=tenant_id, designation="technician", status="inactive")
        db   = _db_returning(st)
        svc  = HomeServiceJobAssignmentService(db)
        _, blocked = await svc.validate_staff_eligibility(job, st.id)
        assert "staff_inactive" in blocked

    @pytest.mark.asyncio
    async def test_wrong_tenant_blocked(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        job_tenant = uuid.uuid4()
        wrong_tenant = uuid.uuid4()
        job = _job(tenant_id=job_tenant)
        st  = _staff(tenant_id=wrong_tenant, designation="technician")
        db  = _db_returning(st)
        svc = HomeServiceJobAssignmentService(db)
        _, blocked = await svc.validate_staff_eligibility(job, st.id)
        assert "wrong_tenant" in blocked

    @pytest.mark.asyncio
    async def test_non_technician_role_blocked(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        tenant_id = uuid.uuid4()
        job = _job(tenant_id=tenant_id)
        st  = _staff(tenant_id=tenant_id, designation="accountant")
        db  = _db_returning(st)
        svc = HomeServiceJobAssignmentService(db)
        _, blocked = await svc.validate_staff_eligibility(job, st.id)
        assert "role_not_allowed" in blocked

    @pytest.mark.asyncio
    async def test_staff_not_found_raises(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        from app.engines.home_service_assignment.constants import ERR_STAFF_NOT_FOUND
        job = _job()
        db  = _db_returning(None)  # staff not found
        svc = HomeServiceJobAssignmentService(db)
        with pytest.raises(ValueError, match=ERR_STAFF_NOT_FOUND):
            await svc.validate_staff_eligibility(job, uuid.uuid4())


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3 — Job Assignment
# ═══════════════════════════════════════════════════════════════════════════════

class TestJobAssignment:
    @pytest.mark.asyncio
    async def test_assign_job_creates_assignment(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        tenant_id = uuid.uuid4()
        staff_id  = uuid.uuid4()
        job  = _job(tenant_id=tenant_id)
        st   = _staff(tenant_id=tenant_id)
        st.id = staff_id

        # DB: job, staff, no current assignment, booking
        db = AsyncMock()
        db.flush   = AsyncMock()
        db.refresh = AsyncMock()
        db.add     = MagicMock()

        job_res = MagicMock(); job_res.scalars.return_value.first.return_value = job
        staff_res = MagicMock(); staff_res.scalars.return_value.first.return_value = st
        no_assign = MagicMock(); no_assign.scalars.return_value.first.return_value = None
        booking_res = MagicMock(); booking_res.scalars.return_value.first.return_value = None
        event_dummy = MagicMock(); event_dummy.scalars.return_value.first.return_value = None
        db.execute = AsyncMock(side_effect=[job_res, staff_res, no_assign, booking_res, event_dummy])

        svc = HomeServiceJobAssignmentService(db)
        result = await svc.assign_job(job.id, staff_id, tenant_id)

        assert result["assigned_staff_member_id"] == str(staff_id)
        assert result["assignment_status"] == "assigned"
        assert job.assignment_status == "assigned"
        assert job.assigned_staff_id == staff_id

    @pytest.mark.asyncio
    async def test_assign_updates_job_status_to_assigned(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        tenant_id = uuid.uuid4()
        staff_id  = uuid.uuid4()
        job  = _job(tenant_id=tenant_id)
        st   = _staff(tenant_id=tenant_id)
        st.id = staff_id

        db = AsyncMock()
        db.flush = AsyncMock(); db.refresh = AsyncMock(); db.add = MagicMock()
        job_res = MagicMock(); job_res.scalars.return_value.first.return_value = job
        st_res  = MagicMock(); st_res.scalars.return_value.first.return_value  = st
        no_a    = MagicMock(); no_a.scalars.return_value.first.return_value    = None
        bk_r    = MagicMock(); bk_r.scalars.return_value.first.return_value    = None
        ev_r    = MagicMock(); ev_r.scalars.return_value.first.return_value    = None
        db.execute = AsyncMock(side_effect=[job_res, st_res, no_a, bk_r, ev_r])

        svc = HomeServiceJobAssignmentService(db)
        await svc.assign_job(job.id, staff_id, tenant_id)
        assert job.status == "assigned"

    @pytest.mark.asyncio
    async def test_assign_raises_on_wrong_tenant(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        from app.engines.home_service_assignment.constants import ERR_ACCESS_DENIED
        tenant_id   = uuid.uuid4()
        other_tenant = uuid.uuid4()
        job  = _job(tenant_id=tenant_id)
        db   = AsyncMock()
        j_res = MagicMock(); j_res.scalars.return_value.first.return_value = job
        db.execute = AsyncMock(side_effect=[j_res])
        svc  = HomeServiceJobAssignmentService(db)
        with pytest.raises(ValueError, match=ERR_ACCESS_DENIED):
            await svc.assign_job(job.id, uuid.uuid4(), other_tenant)

    @pytest.mark.asyncio
    async def test_assign_raises_on_cancelled_job(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        from app.engines.home_service_assignment.constants import ERR_JOB_CANCELLED
        tenant_id = uuid.uuid4()
        job = _job(tenant_id=tenant_id, status="cancelled")
        db  = AsyncMock()
        j_res = MagicMock(); j_res.scalars.return_value.first.return_value = job
        db.execute = AsyncMock(side_effect=[j_res])
        svc = HomeServiceJobAssignmentService(db)
        with pytest.raises(ValueError, match=ERR_JOB_CANCELLED):
            await svc.assign_job(job.id, uuid.uuid4(), tenant_id)

    @pytest.mark.asyncio
    async def test_assign_raises_staff_wrong_tenant(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        from app.engines.home_service_assignment.constants import ERR_STAFF_WRONG_TENANT
        tenant_id  = uuid.uuid4()
        other_tid  = uuid.uuid4()
        job = _job(tenant_id=tenant_id)
        st  = _staff(tenant_id=other_tid)  # wrong tenant
        db  = AsyncMock()
        db.flush = AsyncMock(); db.add = MagicMock()
        j_res = MagicMock(); j_res.scalars.return_value.first.return_value = job
        s_res = MagicMock(); s_res.scalars.return_value.first.return_value = st
        db.execute = AsyncMock(side_effect=[j_res, s_res])
        svc = HomeServiceJobAssignmentService(db)
        with pytest.raises(ValueError, match=ERR_STAFF_WRONG_TENANT):
            await svc.assign_job(job.id, st.id, tenant_id)

    @pytest.mark.asyncio
    async def test_assign_raises_staff_inactive(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        from app.engines.home_service_assignment.constants import ERR_STAFF_INACTIVE
        tenant_id = uuid.uuid4()
        job = _job(tenant_id=tenant_id)
        st  = _staff(tenant_id=tenant_id, status="inactive")
        db  = AsyncMock()
        db.flush = AsyncMock(); db.add = MagicMock()
        j_res = MagicMock(); j_res.scalars.return_value.first.return_value = job
        s_res = MagicMock(); s_res.scalars.return_value.first.return_value = st
        db.execute = AsyncMock(side_effect=[j_res, s_res])
        svc = HomeServiceJobAssignmentService(db)
        with pytest.raises(ValueError, match=ERR_STAFF_INACTIVE):
            await svc.assign_job(job.id, st.id, tenant_id)

    @pytest.mark.asyncio
    async def test_assign_raises_role_not_allowed(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        from app.engines.home_service_assignment.constants import ERR_ROLE_NOT_ALLOWED
        tenant_id = uuid.uuid4()
        job = _job(tenant_id=tenant_id)
        st  = _staff(tenant_id=tenant_id, designation="accountant")
        db  = AsyncMock()
        db.flush = AsyncMock(); db.add = MagicMock()
        j_res = MagicMock(); j_res.scalars.return_value.first.return_value = job
        s_res = MagicMock(); s_res.scalars.return_value.first.return_value = st
        db.execute = AsyncMock(side_effect=[j_res, s_res])
        svc = HomeServiceJobAssignmentService(db)
        with pytest.raises(ValueError, match=ERR_ROLE_NOT_ALLOWED):
            await svc.assign_job(job.id, st.id, tenant_id)

    @pytest.mark.asyncio
    async def test_assign_blocks_reassign_of_accepted_job(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        from app.engines.home_service_assignment.constants import ERR_REASSIGN_NOT_ALLOWED
        tenant_id = uuid.uuid4()
        staff_id  = uuid.uuid4()
        job  = _job(tenant_id=tenant_id, assignment_status="assigned")
        st   = _staff(tenant_id=tenant_id)
        st.id = staff_id
        old_a = _assignment(job.id, staff_id, status="accepted")

        db = AsyncMock()
        db.flush = AsyncMock(); db.add = MagicMock()
        j_res = MagicMock(); j_res.scalars.return_value.first.return_value = job
        s_res = MagicMock(); s_res.scalars.return_value.first.return_value = st
        a_res = MagicMock(); a_res.scalars.return_value.first.return_value = old_a
        db.execute = AsyncMock(side_effect=[j_res, s_res, a_res])
        svc = HomeServiceJobAssignmentService(db)
        with pytest.raises(ValueError, match=ERR_REASSIGN_NOT_ALLOWED):
            await svc.assign_job(job.id, uuid.uuid4(), tenant_id)


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 4 — Technician Accept / Reject
# ═══════════════════════════════════════════════════════════════════════════════

class TestTechnicianActions:
    @pytest.mark.asyncio
    async def test_technician_can_accept_assigned_job(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        staff_id  = uuid.uuid4()
        job  = _job(assignment_status="assigned", staff_id=staff_id)
        assign_rec = _assignment(job.id, staff_id, status="assigned")
        booking = MagicMock(); booking.assignment_status = "assigned"; booking.status = "assigned"

        db = AsyncMock()
        db.flush = AsyncMock(); db.add = MagicMock()
        j_res = MagicMock(); j_res.scalars.return_value.first.return_value = job
        a_res = MagicMock(); a_res.scalars.return_value.first.return_value = assign_rec
        b_res = MagicMock(); b_res.scalars.return_value.first.return_value = booking
        ev_r  = MagicMock(); ev_r.scalars.return_value.first.return_value  = None
        db.execute = AsyncMock(side_effect=[j_res, a_res, b_res, ev_r])

        svc    = HomeServiceJobAssignmentService(db)
        result = await svc.technician_accept_job(job.id, staff_id)
        assert result["status"] == "accepted"
        assert result["assignment_status"] == "accepted"
        assert assign_rec.assignment_status == "accepted"
        assert assign_rec.accepted_at is not None

    @pytest.mark.asyncio
    async def test_technician_cannot_accept_if_not_assigned_to_them(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        from app.engines.home_service_assignment.constants import ERR_STAFF_JOB_NOT_ASSIGNED
        other_staff = uuid.uuid4()
        job  = _job(assignment_status="assigned", staff_id=uuid.uuid4())
        assign_rec = _assignment(job.id, other_staff, status="assigned")

        db = AsyncMock()
        j_res = MagicMock(); j_res.scalars.return_value.first.return_value = job
        a_res = MagicMock(); a_res.scalars.return_value.first.return_value = assign_rec
        db.execute = AsyncMock(side_effect=[j_res, a_res])

        wrong_staff = uuid.uuid4()
        svc = HomeServiceJobAssignmentService(db)
        with pytest.raises(ValueError, match=ERR_STAFF_JOB_NOT_ASSIGNED):
            await svc.technician_accept_job(job.id, wrong_staff)

    @pytest.mark.asyncio
    async def test_technician_cannot_accept_already_accepted(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        from app.engines.home_service_assignment.constants import ERR_STAFF_JOB_ALREADY_ACCEPTED
        staff_id = uuid.uuid4()
        job = _job(assignment_status="accepted", staff_id=staff_id)
        assign_rec = _assignment(job.id, staff_id, status="accepted")

        db = AsyncMock()
        j_res = MagicMock(); j_res.scalars.return_value.first.return_value = job
        a_res = MagicMock(); a_res.scalars.return_value.first.return_value = assign_rec
        db.execute = AsyncMock(side_effect=[j_res, a_res])

        svc = HomeServiceJobAssignmentService(db)
        with pytest.raises(ValueError, match=ERR_STAFF_JOB_ALREADY_ACCEPTED):
            await svc.technician_accept_job(job.id, staff_id)

    @pytest.mark.asyncio
    async def test_technician_can_reject_with_reason(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        staff_id   = uuid.uuid4()
        job        = _job(assignment_status="assigned", staff_id=staff_id)
        assign_rec = _assignment(job.id, staff_id, status="assigned")
        booking    = MagicMock(); booking.assignment_status = "assigned"; booking.status = "assigned"

        db = AsyncMock()
        db.flush = AsyncMock(); db.add = MagicMock()
        j_res = MagicMock(); j_res.scalars.return_value.first.return_value = job
        a_res = MagicMock(); a_res.scalars.return_value.first.return_value = assign_rec
        b_res = MagicMock(); b_res.scalars.return_value.first.return_value = booking
        ev_r  = MagicMock(); ev_r.scalars.return_value.first.return_value  = None
        db.execute = AsyncMock(side_effect=[j_res, a_res, b_res, ev_r])

        svc    = HomeServiceJobAssignmentService(db)
        result = await svc.technician_reject_job(job.id, staff_id, "Unavailable at this time")
        assert result["status"] == "pending_assignment"
        assert result["assignment_status"] == "rejected"
        assert assign_rec.assignment_status == "rejected"
        assert assign_rec.rejection_reason  == "Unavailable at this time"
        assert assign_rec.is_current        is False

    @pytest.mark.asyncio
    async def test_technician_reject_requires_reason(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        from app.engines.home_service_assignment.constants import ERR_REASON_REQUIRED
        staff_id = uuid.uuid4()
        job      = _job(assignment_status="assigned", staff_id=staff_id)
        db       = AsyncMock()
        j_res = MagicMock(); j_res.scalars.return_value.first.return_value = job
        db.execute = AsyncMock(side_effect=[j_res])
        svc = HomeServiceJobAssignmentService(db)
        with pytest.raises(ValueError, match=ERR_REASON_REQUIRED):
            await svc.technician_reject_job(job.id, staff_id, "")

    @pytest.mark.asyncio
    async def test_rejected_job_returns_to_pending_assignment(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        staff_id   = uuid.uuid4()
        job        = _job(assignment_status="assigned", staff_id=staff_id)
        assign_rec = _assignment(job.id, staff_id, status="assigned")
        booking    = MagicMock(); booking.assignment_status = "assigned"; booking.status = "assigned"

        db = AsyncMock()
        db.flush = AsyncMock(); db.add = MagicMock()
        j_res = MagicMock(); j_res.scalars.return_value.first.return_value = job
        a_res = MagicMock(); a_res.scalars.return_value.first.return_value = assign_rec
        b_res = MagicMock(); b_res.scalars.return_value.first.return_value = booking
        ev_r  = MagicMock(); ev_r.scalars.return_value.first.return_value  = None
        db.execute = AsyncMock(side_effect=[j_res, a_res, b_res, ev_r])

        svc = HomeServiceJobAssignmentService(db)
        await svc.technician_reject_job(job.id, staff_id, "Unavailable")
        assert job.status == "pending_assignment"
        assert job.assignment_status == "rejected"
        assert job.assigned_staff_id is None


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 5 — Cancel Assignment
# ═══════════════════════════════════════════════════════════════════════════════

class TestCancelAssignment:
    @pytest.mark.asyncio
    async def test_cancel_assignment_clears_staff(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        tenant_id  = uuid.uuid4()
        staff_id   = uuid.uuid4()
        job        = _job(tenant_id=tenant_id, assignment_status="assigned", staff_id=staff_id)
        assign_rec = _assignment(job.id, staff_id, status="assigned")
        booking    = MagicMock(); booking.assignment_status = "assigned"; booking.status = "assigned"

        db = AsyncMock()
        db.flush = AsyncMock(); db.add = MagicMock()
        j_res = MagicMock(); j_res.scalars.return_value.first.return_value = job
        a_res = MagicMock(); a_res.scalars.return_value.first.return_value = assign_rec
        b_res = MagicMock(); b_res.scalars.return_value.first.return_value = booking
        ev_r  = MagicMock(); ev_r.scalars.return_value.first.return_value  = None
        db.execute = AsyncMock(side_effect=[j_res, a_res, b_res, ev_r])

        svc = HomeServiceJobAssignmentService(db)
        result = await svc.cancel_assignment(job.id, tenant_id, "Provider reassignment")
        assert result["assignment_status"] == "unassigned"
        assert job.assigned_staff_id is None
        assert assign_rec.is_current is False

    @pytest.mark.asyncio
    async def test_cancel_accepted_assignment_blocked(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        from app.engines.home_service_assignment.constants import ERR_CANCEL_NOT_ALLOWED
        tenant_id  = uuid.uuid4()
        staff_id   = uuid.uuid4()
        job        = _job(tenant_id=tenant_id, assignment_status="accepted")
        assign_rec = _assignment(job.id, staff_id, status="accepted")

        db = AsyncMock()
        j_res = MagicMock(); j_res.scalars.return_value.first.return_value = job
        a_res = MagicMock(); a_res.scalars.return_value.first.return_value = assign_rec
        db.execute = AsyncMock(side_effect=[j_res, a_res])

        svc = HomeServiceJobAssignmentService(db)
        with pytest.raises(ValueError, match=ERR_CANCEL_NOT_ALLOWED):
            await svc.cancel_assignment(job.id, tenant_id, "trying to cancel")

    @pytest.mark.asyncio
    async def test_cancel_requires_reason(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        from app.engines.home_service_assignment.constants import ERR_REASON_REQUIRED
        tenant_id = uuid.uuid4()
        job = _job(tenant_id=tenant_id, assignment_status="assigned")
        db  = AsyncMock()
        j_res = MagicMock(); j_res.scalars.return_value.first.return_value = job
        db.execute = AsyncMock(side_effect=[j_res])
        svc = HomeServiceJobAssignmentService(db)
        with pytest.raises(ValueError, match=ERR_REASON_REQUIRED):
            await svc.cancel_assignment(job.id, tenant_id, "")


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 6 — Scheduling
# ═══════════════════════════════════════════════════════════════════════════════

class TestSchedule:
    @pytest.mark.asyncio
    async def test_schedule_sets_date_and_status(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        tenant_id = uuid.uuid4()
        job = _job(tenant_id=tenant_id, status="assigned", assignment_status="assigned")
        assign_rec = _assignment(job.id, uuid.uuid4(), status="assigned")
        booking = MagicMock(); booking.assignment_status = "assigned"; booking.status = "assigned"

        db = AsyncMock()
        db.flush = AsyncMock(); db.add = MagicMock()
        j_res = MagicMock(); j_res.scalars.return_value.first.return_value = job
        a_res = MagicMock(); a_res.scalars.return_value.first.return_value = assign_rec
        b_res = MagicMock(); b_res.scalars.return_value.first.return_value = booking
        ev_r  = MagicMock(); ev_r.scalars.return_value.first.return_value  = None
        db.execute = AsyncMock(side_effect=[j_res, a_res, b_res, ev_r])

        sched_date = date(2026, 7, 10)
        svc = HomeServiceJobAssignmentService(db)
        result = await svc.schedule_job(job.id, tenant_id, sched_date, "10:00-12:00")
        assert result["status"] == "scheduled"
        assert job.scheduled_date == sched_date
        assert job.scheduled_time_window == "10:00-12:00"
        assert job.status == "scheduled"

    @pytest.mark.asyncio
    async def test_schedule_blocked_if_unassigned(self):
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService
        from app.engines.home_service_assignment.constants import ERR_INVALID_STATUS
        tenant_id = uuid.uuid4()
        job = _job(tenant_id=tenant_id, status="pending_assignment", assignment_status="unassigned")
        db  = AsyncMock()
        j_res = MagicMock(); j_res.scalars.return_value.first.return_value = job
        db.execute = AsyncMock(side_effect=[j_res])
        svc = HomeServiceJobAssignmentService(db)
        with pytest.raises(ValueError, match=ERR_INVALID_STATUS):
            await svc.schedule_job(job.id, tenant_id, date(2026, 7, 10), "10:00-12:00")


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 7 — Swagger / API routes
# ═══════════════════════════════════════════════════════════════════════════════

class TestSwaggerRoutes:
    def _get_openapi_paths(self):
        from app.main import create_app
        import asyncio
        app = create_app()

        async def _fetch():
            from httpx import AsyncClient, ASGITransport
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                return (await c.get("/openapi.json")).json()

        return asyncio.run(_fetch()).get("paths", {})

    def test_provider_assignable_endpoint_exists(self):
        paths = self._get_openapi_paths()
        assert "/v1/provider/service-jobs/assignable" in paths

    def test_provider_assign_endpoint_exists(self):
        paths = self._get_openapi_paths()
        assert "/v1/provider/service-jobs/{job_id}/assign" in paths

    def test_provider_eligible_staff_endpoint_exists(self):
        paths = self._get_openapi_paths()
        assert "/v1/provider/service-jobs/{job_id}/eligible-staff" in paths

    def test_staff_jobs_endpoint_exists(self):
        paths = self._get_openapi_paths()
        assert "/v1/staff/service-jobs" in paths

    def test_staff_accept_endpoint_exists(self):
        paths = self._get_openapi_paths()
        assert "/v1/staff/service-jobs/{job_id}/accept" in paths

    def test_staff_reject_endpoint_exists(self):
        paths = self._get_openapi_paths()
        assert "/v1/staff/service-jobs/{job_id}/reject" in paths

    def test_customer_booking_tracking_endpoint_exists(self):
        paths = self._get_openapi_paths()
        assert "/v1/customer/bookings/{booking_id}/tracking" in paths

    def test_admin_assignments_endpoint_exists(self):
        paths = self._get_openapi_paths()
        assert "/v1/admin/service-job-assignments" in paths

    def test_admin_unassigned_endpoint_exists(self):
        paths = self._get_openapi_paths()
        assert "/v1/admin/service-job-assignments/unassigned" in paths

    def test_admin_assigned_endpoint_exists(self):
        paths = self._get_openapi_paths()
        assert "/v1/admin/service-job-assignments/assigned" in paths

    def test_admin_job_timeline_endpoint_exists(self):
        paths = self._get_openapi_paths()
        assert "/v1/admin/service-jobs/{job_id}/assignment-timeline" in paths

    def test_provider_reassign_endpoint_exists(self):
        paths = self._get_openapi_paths()
        assert "/v1/provider/service-jobs/{job_id}/reassign" in paths

    def test_provider_cancel_assignment_endpoint_exists(self):
        paths = self._get_openapi_paths()
        assert "/v1/provider/service-jobs/{job_id}/cancel-assignment" in paths

    def test_provider_schedule_endpoint_exists(self):
        paths = self._get_openapi_paths()
        assert "/v1/provider/service-jobs/{job_id}/schedule" in paths
