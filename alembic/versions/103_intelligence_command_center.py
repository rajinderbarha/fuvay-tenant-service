"""Intelligence Command Center — 8 tables.

Revision ID: 103
Revises: 102
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "103"
down_revision = "102"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rag_knowledge_bases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("scope_type", sa.Text(), server_default="platform"),
        sa.Column("scope_id", UUID(as_uuid=True), nullable=True),
        sa.Column("vertical_key", sa.Text(), nullable=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default="active"),
        sa.Column("document_count", sa.Integer(), server_default="0"),
        sa.Column("chunk_count", sa.Integer(), server_default="0"),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "rag_query_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("knowledge_base_id", UUID(as_uuid=True), sa.ForeignKey("rag_knowledge_bases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("app_scope", sa.Text(), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=True),
        sa.Column("retrieved_chunks_count", sa.Integer(), server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_in", sa.Integer(), server_default="0"),
        sa.Column("tokens_out", sa.Integer(), server_default="0"),
        sa.Column("cost_amount", sa.Numeric(10, 4), server_default="0"),
        sa.Column("status", sa.Text(), server_default="success"),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "intel_risk_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("risk_score", sa.Numeric(5, 2), server_default="0"),
        sa.Column("risk_level", sa.Text(), server_default="low"),
        sa.Column("top_reasons_json", JSONB, server_default="[]"),
        sa.Column("feature_contributions_json", JSONB, server_default="{}"),
        sa.Column("confidence_score", sa.Numeric(5, 2), server_default="0"),
        sa.Column("model_version", sa.Text(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_intel_risk_entity", "intel_risk_scores", ["entity_type", "entity_id"])

    op.create_table(
        "intel_anomalies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("anomaly_type", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), server_default="medium"),
        sa.Column("entity_type", sa.Text(), nullable=True),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("vertical_key", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Numeric(5, 2), server_default="0"),
        sa.Column("status", sa.Text(), server_default="open"),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "intel_model_registry",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("model_type", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), server_default="1.0.0"),
        sa.Column("status", sa.Text(), server_default="draft"),
        sa.Column("environment", sa.Text(), server_default="production"),
        sa.Column("accuracy_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("avg_latency_ms", sa.Integer(), nullable=True),
        sa.Column("last_trained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config_json", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "intel_prediction_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="queued"),
        sa.Column("scope_json", JSONB, server_default="{}"),
        sa.Column("total_processed", sa.Integer(), server_default="0"),
        sa.Column("total_failed", sa.Integer(), server_default="0"),
        sa.Column("triggered_by", sa.Text(), server_default="manual"),
        sa.Column("started_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_summary_json", JSONB, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "intel_data_quality_checks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("check_key", sa.Text(), nullable=False, unique=True),
        sa.Column("check_name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.Text(), server_default="medium"),
        sa.Column("is_enabled", sa.Boolean(), server_default="true"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.Text(), server_default="not_run"),
        sa.Column("failure_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "ai_usage_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("feature_key", sa.Text(), nullable=True),
        sa.Column("app_scope", sa.Text(), nullable=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("model_name", sa.Text(), nullable=True),
        sa.Column("tokens_in", sa.Integer(), server_default="0"),
        sa.Column("tokens_out", sa.Integer(), server_default="0"),
        sa.Column("cost_amount", sa.Numeric(10, 4), server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), server_default="success"),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("ai_usage_logs")
    op.drop_table("intel_data_quality_checks")
    op.drop_table("intel_prediction_jobs")
    op.drop_table("intel_model_registry")
    op.drop_table("intel_anomalies")
    op.drop_index("ix_intel_risk_entity", "intel_risk_scores")
    op.drop_table("intel_risk_scores")
    op.drop_table("rag_query_logs")
    op.drop_table("rag_knowledge_bases")
