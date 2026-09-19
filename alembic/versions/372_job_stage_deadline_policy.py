"""Add configurable job-stage deadlock controls.

Revision ID: 372
Revises: 371
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "372"
down_revision = "371"
branch_labels = None
depends_on = None


_DEFAULTS = (
    "jsonb_build_object("
    "'reached_site',45,'inspection_started',120,"
    "'inspection_done',120,'quote_required',2880,"
    "'service_started',480,'work_done',1440,"
    "'customer_not_available',240)"
)


def upgrade() -> None:
    op.add_column(
        "vertical_monetization_policies",
        sa.Column("job_stall_watchdog_enabled", sa.Boolean(), nullable=False,
                  server_default=sa.text("true")),
    )
    op.add_column(
        "vertical_monetization_policies",
        sa.Column("job_stall_limit_minutes", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default=sa.text(_DEFAULTS)),
    )


def downgrade() -> None:
    op.drop_column("vertical_monetization_policies", "job_stall_limit_minutes")
    op.drop_column("vertical_monetization_policies", "job_stall_watchdog_enabled")
