"""Tenant My Status upgrade — provider_visibility_statuses,
provider_offering_bookable_statuses, provider_enabled_offerings tables.

app/engines/provider_portal/router.py's GET /v1/provider/status,
GET /v1/provider/status/offerings, GET/POST/PUT /v1/provider/offerings/enabled*
all reference tables that were genuinely absent from the live database —
confirmed via a live 500 (asyncpg.exceptions.UndefinedTableError) on all three
during TENANT MY STATUS enterprise-upgrade research. This is the actual root
cause of the current page's generic "Unexpected error." Same class of bug as
Phase 7's provider_team_members and Phase 7B's provider_availability_rules
findings. Creating all three here, idempotent-guarded, matching each router's
INSERT/SELECT/UPDATE column list exactly.

Revision ID: 115
Revises: 114
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "115"
down_revision = "114"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "provider_visibility_statuses" not in existing_tables:
        op.create_table(
            "provider_visibility_statuses",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
            sa.Column("category_id", UUID(as_uuid=True), nullable=True),
            sa.Column("is_visible", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("is_bookable", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("visibility_blockers", JSONB, nullable=False, server_default="[]"),
            sa.Column("bookability_blockers", JSONB, nullable=False, server_default="[]"),
            sa.Column("override_is_visible", sa.Boolean(), nullable=True),
            sa.Column("override_is_bookable", sa.Boolean(), nullable=True),
            sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_changed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
        )
        op.create_index("ix_pvs_tenant_id", "provider_visibility_statuses", ["tenant_id"])

    if "provider_enabled_offerings" not in existing_tables:
        op.create_table(
            "provider_enabled_offerings",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
            sa.Column("offering_id", UUID(as_uuid=True), nullable=False),
            sa.Column("category_id", UUID(as_uuid=True), nullable=True),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("status", sa.String(30), nullable=False, server_default="pending_approval"),
            sa.Column("readiness_status", sa.String(30), nullable=True, server_default="pending"),
            sa.Column("provider_display_name", sa.String(200), nullable=True),
            sa.Column("provider_description", sa.Text(), nullable=True),
            sa.Column("supported_type_ids", JSONB, nullable=True),
            sa.Column("supported_brand_ids", JSONB, nullable=True),
            sa.Column("supports_emergency", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("provider_price_override", sa.Numeric(12, 2), nullable=True),
            sa.Column("provider_min_price", sa.Numeric(12, 2), nullable=True),
            sa.Column("provider_max_price", sa.Numeric(12, 2), nullable=True),
            sa.Column("provider_visit_fee", sa.Numeric(12, 2), nullable=True),
            sa.Column("provider_appointment_fee", sa.Numeric(12, 2), nullable=True),
            sa.Column("provider_lead_fee", sa.Numeric(12, 2), nullable=True),
            sa.Column("readiness_blockers", JSONB, nullable=True, server_default="[]"),
            sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("suspension_reason", sa.Text(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
        )
        op.create_index("ix_peo_tenant_id", "provider_enabled_offerings", ["tenant_id"])
        op.create_index("ix_peo_tenant_offering_unique", "provider_enabled_offerings",
                         ["tenant_id", "offering_id"], unique=True,
                         postgresql_where=text("deleted_at IS NULL"))

    if "provider_offering_bookable_statuses" not in existing_tables:
        op.create_table(
            "provider_offering_bookable_statuses",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
            sa.Column("provider_enabled_offering_id", UUID(as_uuid=True), nullable=False),
            sa.Column("offering_id", UUID(as_uuid=True), nullable=True),
            sa.Column("is_bookable", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("blockers", JSONB, nullable=False, server_default="[]"),
            sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
        )
        op.create_index("ix_pobs_tenant_id", "provider_offering_bookable_statuses", ["tenant_id"])
        op.create_index("ix_pobs_offering", "provider_offering_bookable_statuses", ["provider_enabled_offering_id"])


def downgrade() -> None:
    op.drop_table("provider_offering_bookable_statuses")
    op.drop_table("provider_enabled_offerings")
    op.drop_table("provider_visibility_statuses")
