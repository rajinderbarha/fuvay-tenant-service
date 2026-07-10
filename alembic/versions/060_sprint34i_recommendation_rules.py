"""Sprint 34I — Automation / Recommendation Rules Engine.

Creates:
  recommendation_rules     — admin-defined rules for automatic recommendations
  recommendation_results   — per-evaluation tracking of shown/accepted/rejected results
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "060"
down_revision = "059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendation_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),

        # Identity
        sa.Column("code",        sa.String(100), nullable=False),
        sa.Column("name",        sa.String(200), nullable=False),
        sa.Column("description", sa.Text,        nullable=True),

        # Type and scope
        sa.Column("rule_type",     sa.String(60), nullable=False),
        sa.Column("scope",         sa.String(30), nullable=False, server_default="platform"),
        sa.Column("vertical_type", sa.String(60), nullable=True),
        sa.Column("category_id",   postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("service_id",    postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id",     postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("location_id",   postgresql.UUID(as_uuid=True), nullable=True),

        # Priority + status
        sa.Column("priority", sa.Integer, nullable=False, server_default="100"),
        sa.Column("status",   sa.String(30), nullable=False, server_default="draft"),

        # Rule definition
        sa.Column("condition_json",       postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("recommendation_json",  postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("explanation_template", sa.Text, nullable=True),

        # Audit
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata_json",       postgresql.JSONB, nullable=True),

        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()"), onupdate=sa.text("NOW()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),

        sa.UniqueConstraint("code", name="uq_rr_code"),
    )

    op.create_index("ix_rec_rule_status",    "recommendation_rules", ["status"])
    op.create_index("ix_rec_rule_type",     "recommendation_rules", ["rule_type"])
    op.create_index("ix_rec_rule_scope",    "recommendation_rules", ["scope"])
    op.create_index("ix_rec_rule_category", "recommendation_rules", ["category_id"])
    op.create_index("ix_rec_rule_service",  "recommendation_rules", ["service_id"])
    op.create_index("ix_rec_rule_priority", "recommendation_rules", ["priority"])
    op.create_index("ix_rec_rule_vertical", "recommendation_rules", ["vertical_type"])

    op.create_table(
        "recommendation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),

        # Request context
        sa.Column("request_id",    sa.String(100), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id",     postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("customer_id",   postgresql.UUID(as_uuid=True), nullable=True),

        # Context
        sa.Column("context_type", sa.String(60), nullable=False),
        sa.Column("context_id",   sa.String(200), nullable=True),

        # Rule linkage
        sa.Column("rule_id",   postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rule_type", sa.String(60), nullable=True),

        # Recommendation payload
        sa.Column("input_json",               postgresql.JSONB, nullable=True),
        sa.Column("recommended_entity_type",  sa.String(60),   nullable=True),
        sa.Column("recommended_entity_id",    postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recommended_payload_json", postgresql.JSONB, nullable=True),
        sa.Column("confidence_score",         sa.Numeric(4, 3), nullable=True),
        sa.Column("explanation",              sa.Text, nullable=True),

        # Outcome
        sa.Column("status", sa.String(30), nullable=False, server_default="shown"),

        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()"), onupdate=sa.text("NOW()")),
    )

    op.create_index("ix_res_context_type",   "recommendation_results", ["context_type"])
    op.create_index("ix_res_rule_id",        "recommendation_results", ["rule_id"])
    op.create_index("ix_res_status",         "recommendation_results", ["status"])
    op.create_index("ix_res_tenant",         "recommendation_results", ["tenant_id"])
    op.create_index("ix_res_actor",          "recommendation_results", ["actor_user_id"])
    op.create_index("ix_res_entity_type",    "recommendation_results", ["recommended_entity_type"])


def downgrade() -> None:
    op.drop_table("recommendation_results")
    op.drop_table("recommendation_rules")
