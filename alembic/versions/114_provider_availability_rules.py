"""Phase 7B staff/technician frontend certification — provider_availability_rules table.

app/engines/provider_portal/router.py's GET/POST/PUT/DELETE /v1/provider/availability*
endpoints reference a `provider_availability_rules` table that is genuinely absent
from the live database — confirmed via \\dt and a live 500 on
GET /v1/provider/availability. This is the backing table for the technician
"Availability" self-service page. Creating it here, idempotent-guarded like every
other migration this session, matching the router's INSERT/SELECT column list exactly.

Revision ID: 114
Revises: 113
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID

revision = "114"
down_revision = "113"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "provider_availability_rules" not in existing_tables:
        op.create_table(
            "provider_availability_rules",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
            sa.Column("scope_type", sa.String(30), nullable=False, server_default="provider"),
            sa.Column("scope_id", UUID(as_uuid=True), nullable=True),
            sa.Column("category_id", UUID(as_uuid=True), nullable=True),
            sa.Column("day_of_week", sa.SmallInteger(), nullable=False),
            sa.Column("start_time", sa.String(8), nullable=False),
            sa.Column("end_time", sa.String(8), nullable=False),
            sa.Column("slot_duration_minutes", sa.Integer(), nullable=True),
            sa.Column("max_bookings_per_slot", sa.Integer(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
        )
        op.create_index("ix_par_tenant_id", "provider_availability_rules", ["tenant_id"])
        op.create_index("ix_par_scope", "provider_availability_rules", ["scope_type", "scope_id"])


def downgrade() -> None:
    op.drop_table("provider_availability_rules")
