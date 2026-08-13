"""Add indexes for the unified Home Services operations feed.

Revision ID: 249
Revises: 248
"""
from alembic import op


revision = "249"
down_revision = "248"
branch_labels = None
depends_on = None


INDEXES = (
    ("ix_sj_created", "service_jobs", ["created_at"]),
    ("ix_sj_tenant_created", "service_jobs", ["tenant_id", "created_at"]),
    ("ix_hsbd_status_created", "home_service_booking_drafts", ["status", "created_at"]),
    ("ix_hsbd_tenant_status_created", "home_service_booking_drafts", ["selected_tenant_id", "status", "created_at"]),
)


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for name, table, columns in INDEXES:
            op.create_index(name, table, columns, unique=False, postgresql_concurrently=True)


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name, table, _columns in reversed(INDEXES):
            op.drop_index(name, table_name=table, postgresql_concurrently=True)
