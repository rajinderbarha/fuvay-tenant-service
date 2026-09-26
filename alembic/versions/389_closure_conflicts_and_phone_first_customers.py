"""Protect existing jobs on closures and make customer email optional.

Revision ID: 389
Revises: 388
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "389"
down_revision = "388"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Customer authentication is phone/OTP first.  Social-channel customers
    # must not be given an invented email address merely to satisfy storage.
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=True)
    op.execute("""
        UPDATE users
        SET email = NULL
        WHERE role = 'customer'
          AND lower(email) LIKE '%@serviceos.internal'
    """)

    # A closure never rewrites an existing customer commitment.  Persist the
    # operator's explicit policy and the immutable impact seen when it was
    # created so the decision remains auditable even after jobs progress.
    op.add_column(
        "tenant_availability_exceptions",
        sa.Column("existing_jobs_policy", sa.String(32), nullable=False,
                  server_default="honor_existing"),
    )
    op.add_column(
        "tenant_availability_exceptions",
        sa.Column("conflict_snapshot", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
    )
    # Backfill closures that already exist (including the live 28-Sep
    # closure) so operators see the commitments immediately after deploy.
    op.execute("""
        UPDATE tenant_availability_exceptions e
        SET conflict_snapshot = jsonb_build_object(
            'date', e.date::text,
            'total_jobs', (
                SELECT count(*) FROM service_jobs j
                WHERE j.tenant_id=e.tenant_id AND j.scheduled_date=e.date
                  AND j.status NOT IN ('completed','cancelled','closed','failed','expired','no_show')
            ),
            'protected_started_jobs', (
                SELECT count(*) FROM service_jobs j
                WHERE j.tenant_id=e.tenant_id AND j.scheduled_date=e.date
                  AND j.status IN ('reached_site','inspection_started','inspection_done','quote_required',
                    'awaiting_customer_quote_approval','quote_approved','service_started','in_progress',
                    'customer_not_available')
            ),
            'pre_start_jobs', (
                SELECT count(*) FROM service_jobs j
                WHERE j.tenant_id=e.tenant_id AND j.scheduled_date=e.date
                  AND j.status NOT IN ('completed','cancelled','closed','failed','expired','no_show',
                    'reached_site','inspection_started','inspection_done','quote_required',
                    'awaiting_customer_quote_approval','quote_approved','service_started','in_progress',
                    'customer_not_available')
            ),
            'policy', 'honor_existing',
            'requires_acknowledgement', EXISTS (
                SELECT 1 FROM service_jobs j
                WHERE j.tenant_id=e.tenant_id AND j.scheduled_date=e.date
                  AND j.status NOT IN ('completed','cancelled','closed','failed','expired','no_show')
            ),
            'jobs', COALESCE((
                SELECT jsonb_agg(jsonb_build_object(
                    'job_id', j.id::text, 'job_number', j.job_number,
                    'status', j.status, 'time_window', j.scheduled_time_window,
                    'assigned', j.assigned_staff_id IS NOT NULL,
                    'started', j.status IN ('reached_site','inspection_started','inspection_done','quote_required',
                        'awaiting_customer_quote_approval','quote_approved','service_started','in_progress',
                        'customer_not_available'),
                    'sla_breached', j.sla_breached_at IS NOT NULL
                ) ORDER BY j.scheduled_time_window NULLS LAST)
                FROM service_jobs j
                WHERE j.tenant_id=e.tenant_id AND j.scheduled_date=e.date
                  AND j.status NOT IN ('completed','cancelled','closed','failed','expired','no_show')
            ), '[]'::jsonb)
        )
        WHERE e.status='active'
    """)


def downgrade() -> None:
    # A downgrade cannot restore made-up addresses.  Refuse it if phone-only
    # customers now exist instead of silently corrupting their identities.
    op.execute("""
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM users WHERE email IS NULL) THEN
            RAISE EXCEPTION 'Cannot make users.email NOT NULL while phone-only users exist';
          END IF;
        END $$
    """)
    op.drop_column("tenant_availability_exceptions", "conflict_snapshot")
    op.drop_column("tenant_availability_exceptions", "existing_jobs_policy")
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=False)
