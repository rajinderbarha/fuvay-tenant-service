"""Index canonical service jobs for the platform staff directory.

Revision ID: 250
Revises: 249
"""
from alembic import op


revision = "250"
down_revision = "249"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_sj_staff_status_created",
            "service_jobs",
            ["assigned_staff_id", "status", "created_at"],
            unique=False,
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_sj_staff_status_created",
            table_name="service_jobs",
            postgresql_concurrently=True,
        )
