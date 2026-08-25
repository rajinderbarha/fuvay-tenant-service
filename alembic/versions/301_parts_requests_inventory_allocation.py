"""Link approved job part requests to provider inventory.

Revision ID: 301
Revises: 300
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "301"
down_revision = "300"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("service_job_parts_requests", sa.Column(
        "procurement_source", sa.String(20), nullable=False, server_default="external"))
    op.add_column("service_job_parts_requests", sa.Column(
        "inventory_item_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("service_job_parts_requests", sa.Column(
        "stock_location_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("service_job_parts_requests", sa.Column(
        "stock_reservation_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("service_job_parts_requests", sa.Column(
        "unit_price_snapshot", sa.Numeric(10, 2), nullable=True))
    op.create_index("ix_sjpr_inventory_item", "service_job_parts_requests", ["inventory_item_id"])
    op.create_index("ix_sjpr_stock_reservation", "service_job_parts_requests", ["stock_reservation_id"])


def downgrade() -> None:
    op.drop_index("ix_sjpr_stock_reservation", table_name="service_job_parts_requests")
    op.drop_index("ix_sjpr_inventory_item", table_name="service_job_parts_requests")
    op.drop_column("service_job_parts_requests", "unit_price_snapshot")
    op.drop_column("service_job_parts_requests", "stock_reservation_id")
    op.drop_column("service_job_parts_requests", "stock_location_id")
    op.drop_column("service_job_parts_requests", "inventory_item_id")
    op.drop_column("service_job_parts_requests", "procurement_source")

