"""Scope tenant setup revisions to each master-service job type.

Revision ID: 261
Revises: 260
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "261"
down_revision = "260"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "master_service_job_types",
        sa.Column("setup_rules_revision", sa.Integer(), nullable=False, server_default="1"),
    )
    # Preserve the revision already acknowledged by tenant rows. A link starts
    # at the highest known revision for that exact offering, never backwards.
    op.execute("""
        UPDATE master_service_job_types link
        SET setup_rules_revision = source.revision
        FROM (
            SELECT msjt.id, greatest(
                coalesce(max(ts.setup_rules_revision), 1),
                coalesce(max(ms.setup_rules_revision), 1)
            ) AS revision
            FROM master_service_job_types msjt
            JOIN master_services ms ON ms.id = msjt.master_service_id
            LEFT JOIN tenant_services ts
              ON ts.master_service_id = msjt.master_service_id
             AND ts.job_type_id = msjt.job_type_id
            GROUP BY msjt.id
        ) source
        WHERE link.id = source.id
    """)
    op.create_index(
        "ix_msjt_setup_revision", "master_service_job_types",
        ["master_service_id", "job_type_id", "setup_rules_revision"],
    )


def downgrade() -> None:
    op.drop_index("ix_msjt_setup_revision", table_name="master_service_job_types")
    op.drop_column("master_service_job_types", "setup_rules_revision")
