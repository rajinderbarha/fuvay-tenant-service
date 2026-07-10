"""Admin Home Services Catalog Setup Console — brand pricing behavior.

Adds can_override_price / is_routing_only to master_service_brands so the
admin console can configure whether a brand affects pricing at all
(routing-only) or can carry a tenant-settable brand-specific price range
(can_override_price). Both new columns default to today's implicit
behavior (every mapped brand can be selected for tenant price override,
none are routing-only) so no existing data changes meaning.

Revision ID: 118
Revises: 117
"""
from alembic import op
import sqlalchemy as sa

revision = "118"
down_revision = "117"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = {c["name"] for c in inspector.get_columns("master_service_brands")}

    if "can_override_price" not in existing_columns:
        op.add_column(
            "master_service_brands",
            sa.Column("can_override_price", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
    if "is_routing_only" not in existing_columns:
        op.add_column(
            "master_service_brands",
            sa.Column("is_routing_only", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    op.drop_column("master_service_brands", "is_routing_only")
    op.drop_column("master_service_brands", "can_override_price")
