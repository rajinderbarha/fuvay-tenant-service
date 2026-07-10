"""Phase 7 staff/technician app certification — provider_team_members table.

The ProviderTeamMember model (app/engines/home_service_assignment/staff_model.py)
documents this table as "created by Sprint 11 migrations" but no such migration
exists anywhere in this repo and the table is genuinely absent from the live
database — confirmed via \\dt and a live 500 on GET /v1/provider/team-members.
This is the backing table for Phase 7's "Skills & Assigned Services" module
(technician skills/offering/brand/service-area coverage). Creating it here,
idempotent-guarded like every other migration this session.

Revision ID: 113
Revises: 112
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "113"
down_revision = "112"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "provider_team_members" not in existing_tables:
        op.create_table(
            "provider_team_members",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
            sa.Column("category_id", UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", UUID(as_uuid=True), nullable=True),
            sa.Column("member_type", sa.String(50), nullable=False),
            sa.Column("full_name", sa.String(200), nullable=False),
            sa.Column("phone", sa.String(30), nullable=True),
            sa.Column("email", sa.String(200), nullable=True),
            sa.Column("designation", sa.String(100), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="active"),
            sa.Column("can_receive_assignment", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("skills", JSONB, nullable=True),
            sa.Column("supported_offering_ids", JSONB, nullable=True),
            sa.Column("supported_type_ids", JSONB, nullable=True),
            sa.Column("supported_brand_ids", JSONB, nullable=True),
            sa.Column("service_area_ids", JSONB, nullable=True),
            sa.Column("profile_photo_url", sa.String(500), nullable=True),
            sa.Column("username", sa.String(100), nullable=True),
            sa.Column("password_generated", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
        )
        op.create_index("ix_ptm_tenant_id", "provider_team_members", ["tenant_id"])
        op.create_index("ix_ptm_user_id", "provider_team_members", ["user_id"])
        op.create_index("ix_ptm_status", "provider_team_members", ["status"])


def downgrade() -> None:
    op.drop_table("provider_team_members")
