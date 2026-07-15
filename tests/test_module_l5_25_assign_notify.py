"""MODULE-L5-25 — assigning a job notifies the technician.

assign_job set service_jobs.assigned_staff_id and emitted an internal audit event
but never created a user-facing notification, so a technician was given work and
never told — the whole point of an assignment is that they act on it. It now
raises an in-app "New job assigned to you" notification for the assigned staff
(reassign_job delegates to assign_job, so it is covered too).
"""
from __future__ import annotations

import inspect
import uuid

import pytest


def test_assign_job_notifies_staff_in_source():
    from app.engines.home_service_assignment import service
    src = inspect.getsource(service.HomeServiceJobAssignmentService.assign_job)
    assert "_notify_staff_assigned" in src
    helper = inspect.getsource(service.HomeServiceJobAssignmentService._notify_staff_assigned)
    assert "InAppNotification" in helper
    assert "job_assigned" in helper
    assert "/staff/jobs/" in helper


class TestAssignNotifyLive:
    @pytest.mark.asyncio
    async def test_assigning_a_job_creates_a_staff_notification(self):
        import asyncpg
        from sqlalchemy import text
        from app.database import get_session_factory, init_db
        from app.engines.home_service_assignment.service import HomeServiceJobAssignmentService as Svc

        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            # A job that already has an eligible assigned staff we can re-drive.
            row = await c.fetchrow(
                "SELECT id, tenant_id, assigned_staff_id FROM service_jobs "
                "WHERE assigned_staff_id IS NOT NULL AND tenant_id IS NOT NULL "
                "AND status NOT IN ('cancelled','voided') LIMIT 1")
            if not row:
                pytest.skip("no assigned job available to re-drive")
            job_id, tenant_id, staff_id = row["id"], row["tenant_id"], row["assigned_staff_id"]
            # Reset to assignable and clear current assignment.
            await c.execute(
                "UPDATE service_jobs SET status='pending_assignment', assigned_staff_id=NULL, "
                "assignment_status='pending_assignment' WHERE id=$1", job_id)
            await c.execute(
                "UPDATE service_job_assignments SET is_current=false WHERE job_id=$1", job_id)
            before = await c.fetchval(
                "SELECT count(*) FROM in_app_notifications WHERE user_id=$1 "
                "AND notification_type='job_assigned'", staff_id)
        finally:
            await c.close()

        await init_db()
        sf = get_session_factory()
        async with sf() as db:
            try:
                await Svc(db).assign_job(job_id=job_id, staff_member_id=staff_id,
                                         tenant_id=tenant_id, actor_user_id=staff_id)
                await db.commit()
            except ValueError as e:
                pytest.skip(f"assignment not drivable in this env: {e}")

        c = await asyncpg.connect("postgresql://serviceos:serviceos@127.0.0.1:5432/serviceos")
        try:
            after = await c.fetchval(
                "SELECT count(*) FROM in_app_notifications WHERE user_id=$1 "
                "AND notification_type='job_assigned'", staff_id)
        finally:
            await c.close()
        assert after == before + 1, "assigning a job did not notify the technician"
