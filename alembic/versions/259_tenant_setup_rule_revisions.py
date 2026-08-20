"""Canonical tenant setup rule revisions and legacy relational backfill.

Revision ID: 259
Revises: 258
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "259"
down_revision = "258"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "master_services",
        sa.Column("setup_rules_revision", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "tenant_services",
        sa.Column("setup_rules_revision", sa.Integer(), nullable=False, server_default="1"),
    )

    # Migration 151 added these relational columns, but later-created legacy
    # rows could still leave them NULL. Resolve only exact canonical keys; no
    # fuzzy guesses and no mutation of historical booking/job snapshots.
    op.execute("""
        UPDATE master_services ms SET job_type_id = jt.id
        FROM job_types jt
        WHERE ms.job_type_id IS NULL AND ms.job_type IS NOT NULL
          AND jt.key = ms.job_type
    """)
    op.execute("""
        UPDATE tenant_services ts SET job_type_id = jt.id
        FROM job_types jt
        WHERE ts.job_type_id IS NULL AND ts.job_type IS NOT NULL
          AND jt.key = ts.job_type
    """)

    # Hot-path indexes for the aggregate setup projection and stale-revision
    # checks. Existing tenant/master indexes remain intact.
    op.create_index(
        "ix_msjt_service_active_order",
        "master_service_job_types",
        ["master_service_id", "is_active", "display_order"],
    )
    op.create_index(
        "ix_sjw_service_current_status",
        "service_job_workflow",
        ["master_service_id", "is_current", "status", "job_type_id"],
    )
    op.create_index(
        "ix_ts_service_setup_revision",
        "tenant_services",
        ["master_service_id", "setup_rules_revision", "setup_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_ts_service_setup_revision", table_name="tenant_services")
    op.drop_index("ix_sjw_service_current_status", table_name="service_job_workflow")
    op.drop_index("ix_msjt_service_active_order", table_name="master_service_job_types")
    op.drop_column("tenant_services", "setup_rules_revision")
    op.drop_column("master_services", "setup_rules_revision")
