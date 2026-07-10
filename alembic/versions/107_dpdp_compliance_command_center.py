"""P0 DPDP Compliance Command Center — legal holds, evidence packs, action states.

Additive upgrade to the existing compliance engine (migration 079 enterprise
tables + migration 013 phase-13 tables). Does not touch existing tables.

Revision ID: 107
Revises: 106
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "107"
down_revision = "106"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = set(inspector.get_table_names())

    if "dpdp_legal_holds" not in existing:
        op.create_table(
            "dpdp_legal_holds",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("hold_code", sa.String(30), nullable=False, unique=True),
            sa.Column("entity_type", sa.String(30), nullable=False),
            sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("evidence_json", postgresql.JSONB(), nullable=False, server_default="{}"),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("applied_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("released_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("release_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
        )
        op.create_index("ix_dpdp_legal_holds_entity", "dpdp_legal_holds",
                         ["entity_type", "entity_id"])
        op.create_index("ix_dpdp_legal_holds_status", "dpdp_legal_holds", ["status"])

    if "dpdp_evidence_packs" not in existing:
        op.create_table(
            "dpdp_evidence_packs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("request_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("compliance_requests.id", ondelete="CASCADE"), nullable=False),
            sa.Column("pack_json", postgresql.JSONB(), nullable=False, server_default="{}"),
            sa.Column("generated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
        )
        op.create_index("ix_dpdp_evidence_packs_request", "dpdp_evidence_packs", ["request_id"])

    if "dpdp_action_states" not in existing:
        op.create_table(
            "dpdp_action_states",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("request_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("compliance_requests.id", ondelete="CASCADE"),
                      nullable=False, unique=True),
            sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
            sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("escalated", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("escalated_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("now()")),
        )


def downgrade() -> None:
    op.drop_table("dpdp_action_states")
    op.drop_table("dpdp_evidence_packs")
    op.drop_table("dpdp_legal_holds")
