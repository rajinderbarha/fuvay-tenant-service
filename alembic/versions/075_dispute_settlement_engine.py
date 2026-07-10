"""Dispute/Settlement Engine: SLA columns on customer_complaints,
   settlement_proposals table, ai_settlement_sessions table.

Revision ID: 075
Revises: 074
Create Date: 2026-07-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "075"
down_revision = "074"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── SLA + severity columns on customer_complaints ─────────────────────────
    op.add_column("customer_complaints", sa.Column("severity",                    sa.String(20),  nullable=True))
    op.add_column("customer_complaints", sa.Column("sla_status",                  sa.String(30),  nullable=True))
    op.add_column("customer_complaints", sa.Column("tenant_first_response_due_at",sa.DateTime(timezone=True), nullable=True))
    op.add_column("customer_complaints", sa.Column("ai_escalation_at",            sa.DateTime(timezone=True), nullable=True))
    op.add_column("customer_complaints", sa.Column("admin_escalation_at",         sa.DateTime(timezone=True), nullable=True))
    op.add_column("customer_complaints", sa.Column("settlement_status",           sa.String(40),  nullable=True))
    op.add_column("customer_complaints", sa.Column("ai_session_id",               postgresql.UUID(as_uuid=True), nullable=True))

    # ── settlement_proposals ──────────────────────────────────────────────────
    op.create_table(
        "settlement_proposals",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("complaint_id",        postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",           postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("proposal_number",     sa.String(40),  nullable=False),
        sa.Column("proposed_by",         sa.String(20),  nullable=False),
        sa.Column("proposed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("proposal_type",       sa.String(40),  nullable=False),
        sa.Column("proposal_amount",     sa.Numeric(12,2), nullable=True),
        sa.Column("currency",            sa.String(10),  nullable=False, server_default="INR"),
        sa.Column("description",         sa.Text,        nullable=False),
        sa.Column("conditions",          sa.Text,        nullable=True),
        sa.Column("status",              sa.String(30),  nullable=False, server_default="proposed"),
        sa.Column("customer_response",   sa.String(20),  nullable=True),
        sa.Column("tenant_response",     sa.String(20),  nullable=True),
        sa.Column("customer_responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_responded_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("admin_approved_by",   postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("admin_approved_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at",          sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_generated",        sa.Boolean, nullable=False, server_default="false"),
        sa.Column("ai_confidence_score", sa.Numeric(5,4), nullable=True),
        sa.Column("created_at",          sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",          sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sp_complaint_id", "settlement_proposals", ["complaint_id"], if_not_exists=True)
    op.create_index("ix_sp_status",       "settlement_proposals", ["status"],      if_not_exists=True)
    op.create_unique_constraint("uq_sp_number", "settlement_proposals", ["proposal_number"])

    # ── ai_settlement_sessions ────────────────────────────────────────────────
    op.create_table(
        "ai_settlement_sessions",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("complaint_id",        postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",           postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status",              sa.String(30),  nullable=False, server_default="started"),
        sa.Column("customer_questions",  postgresql.JSONB, nullable=True),
        sa.Column("customer_answers",    postgresql.JSONB, nullable=True),
        sa.Column("tenant_questions",    postgresql.JSONB, nullable=True),
        sa.Column("tenant_answers",      postgresql.JSONB, nullable=True),
        sa.Column("evidence_summary",    sa.Text, nullable=True),
        sa.Column("ai_recommendation",   sa.Text, nullable=True),
        sa.Column("risk_flags",          postgresql.JSONB, nullable=True),
        sa.Column("confidence_score",    sa.Numeric(5,4), nullable=True),
        sa.Column("model_used",          sa.String(100), nullable=True),
        sa.Column("prompt_tokens",       sa.Integer, nullable=True),
        sa.Column("completion_tokens",   sa.Integer, nullable=True),
        sa.Column("started_at",          sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at",        sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",          sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at",          sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ais_complaint_id", "ai_settlement_sessions", ["complaint_id"], if_not_exists=True)
    op.create_index("ix_ais_status",       "ai_settlement_sessions", ["status"],      if_not_exists=True)


def downgrade() -> None:
    op.drop_table("ai_settlement_sessions")
    op.drop_table("settlement_proposals")
    op.drop_column("customer_complaints", "ai_session_id")
    op.drop_column("customer_complaints", "settlement_status")
    op.drop_column("customer_complaints", "admin_escalation_at")
    op.drop_column("customer_complaints", "ai_escalation_at")
    op.drop_column("customer_complaints", "tenant_first_response_due_at")
    op.drop_column("customer_complaints", "sla_status")
    op.drop_column("customer_complaints", "severity")
