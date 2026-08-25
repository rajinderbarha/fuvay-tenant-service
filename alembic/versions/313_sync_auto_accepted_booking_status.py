"""Synchronize auto-accepted booking and job status projections.

Revision ID: 313
Revises: 312

Finalization auto-accepted eligible providers on ``service_jobs`` but left
``service_bookings`` and the job assignment status unassigned. Customer list
and detail screens consequently reported contradictory states. The execution
event metadata precisely identifies system auto-acceptance, so legacy repair
does not touch manually managed jobs.
"""
from alembic import op


revision = "313"
down_revision = "312"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE service_jobs AS job
           SET assignment_status = 'accepted'
         WHERE job.status = 'accepted'
           AND COALESCE(job.assignment_status, 'unassigned') = 'unassigned'
           AND EXISTS (
               SELECT 1
                 FROM service_job_execution_events AS event
                WHERE event.job_id = job.id
                  AND event.event_type = 'job_accepted'
                  AND COALESCE((event.metadata->>'auto_accepted')::boolean, false)
           )
        """
    )
    op.execute(
        """
        UPDATE service_bookings AS booking
           SET status = 'accepted', assignment_status = 'accepted'
          FROM service_jobs AS job
         WHERE job.booking_id = booking.id
           AND job.status = 'accepted'
           AND job.assignment_status = 'accepted'
           AND booking.status = 'pending_assignment'
           AND COALESCE(booking.assignment_status, 'unassigned') = 'unassigned'
           AND EXISTS (
               SELECT 1
                 FROM service_job_execution_events AS event
                WHERE event.job_id = job.id
                  AND event.event_type = 'job_accepted'
                  AND COALESCE((event.metadata->>'auto_accepted')::boolean, false)
           )
        """
    )


def downgrade() -> None:
    # Restoring the contradictory state would be destructive and incorrect.
    pass
