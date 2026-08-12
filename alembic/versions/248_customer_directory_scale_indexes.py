"""Add composite indexes for large customer and job histories.

Revision ID: 248
Revises: 247
"""
from alembic import op


revision = "248"
down_revision = "247"
branch_labels = None
depends_on = None


INDEXES = (
    ("ix_sb_customer_created", "service_bookings", ["customer_id", "created_at"]),
    ("ix_sb_tenant_customer_created", "service_bookings", ["tenant_id", "customer_id", "created_at"]),
    ("ix_sj_customer_status_updated", "service_jobs", ["customer_id", "status", "updated_at"]),
    ("ix_sj_tenant_customer_status_updated", "service_jobs", ["tenant_id", "customer_id", "status", "updated_at"]),
)


def upgrade() -> None:
    # Concurrent creation keeps writes available when this migration is run
    # against a production-sized booking/job history.
    with op.get_context().autocommit_block():
        for name, table, columns in INDEXES:
            op.create_index(
                name, table, columns, unique=False, postgresql_concurrently=True,
            )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name, table, _columns in reversed(INDEXES):
            op.drop_index(name, table_name=table, postgresql_concurrently=True)
