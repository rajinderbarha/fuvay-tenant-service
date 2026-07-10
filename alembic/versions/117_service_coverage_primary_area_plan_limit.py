"""Service Coverage Areas — Primary Area + Plan Service-Area Limit.

Adds is_primary to tenant_service_areas (no such concept existed before —
the tenant portal's Service Areas page referenced it but nothing persisted
it) and max_service_areas to tenant_limits (PLAN_LIMITS previously had no
service-area cap at all; the frontend used a hardcoded AREA_LIMIT=5).

Revision ID: 117
Revises: 116
"""
from alembic import op
import sqlalchemy as sa

revision = "117"
down_revision = "116"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    tsa_columns = {c["name"] for c in inspector.get_columns("tenant_service_areas")}
    if "is_primary" not in tsa_columns:
        op.add_column(
            "tenant_service_areas",
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    tlim_columns = {c["name"] for c in inspector.get_columns("tenant_limits")}
    if "max_service_areas" not in tlim_columns:
        op.add_column(
            "tenant_limits",
            sa.Column("max_service_areas", sa.Integer(), nullable=False, server_default="5"),
        )


def downgrade() -> None:
    op.drop_column("tenant_limits", "max_service_areas")
    op.drop_column("tenant_service_areas", "is_primary")
