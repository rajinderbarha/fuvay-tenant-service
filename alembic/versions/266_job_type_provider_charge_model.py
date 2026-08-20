"""Allow a Job Type to override the provider charge model.

Revision ID: 266
Revises: 265

This supports a mixed Home Services policy: repair may inherit the vertical
percentage commission while consultation uses a fixed credit price when the
consultation is completed.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "266"
down_revision = "265"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "monetization_job_type_rules",
        sa.Column("provider_charge_model", sa.String(length=30), nullable=False,
                  server_default="INHERIT"),
    )
    op.create_check_constraint(
        "ck_mjtr_provider_charge_model",
        "monetization_job_type_rules",
        "provider_charge_model IN ('INHERIT', 'FIXED_CREDITS')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_mjtr_provider_charge_model", "monetization_job_type_rules", type_="check")
    op.drop_column("monetization_job_type_rules", "provider_charge_model")
