"""Add event-aware Home Services Job Type monetization rules.

Revision ID: 265
Revises: 264

Repair/fixed-price work is charged when the job completes. Consultation can
carry its own fixed-credit rule and is charged when that consultation is
completed. The event belongs to the versioned monetization rule, not the Job
Type catalog definition (which remains non-monetary).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "265"
down_revision = "264"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "monetization_job_type_rules",
        sa.Column("provider_chargeable_event", sa.String(length=40), nullable=False,
                  server_default="job_completed"),
    )
    op.execute(
        """
        UPDATE monetization_job_type_rules r
        SET provider_chargeable_event = 'consultation_completed'
        FROM job_types jt
        WHERE jt.id = r.job_type_id AND jt.key = 'consultation'
        """
    )
    op.create_check_constraint(
        "ck_mjtr_provider_chargeable_event",
        "monetization_job_type_rules",
        "provider_chargeable_event IN ('job_completed', 'consultation_completed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_mjtr_provider_chargeable_event", "monetization_job_type_rules", type_="check")
    op.drop_column("monetization_job_type_rules", "provider_chargeable_event")
