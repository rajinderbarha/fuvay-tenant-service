"""Phase 7 — Data Science Engine (7 tables)
Revision ID: 007
Revises: 006
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("prediction_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("entity_id", sa.String(100), nullable=True),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("prediction_type", sa.String(50), nullable=False),
        sa.Column("model_type", sa.String(80), nullable=False),
        sa.Column("model_version", sa.String(40), nullable=False),
        sa.Column("ds_phase", sa.Integer, nullable=False),
        sa.Column("observation_mode", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("inputs", JSONB, nullable=False, server_default="{}"),
        sa.Column("output", JSONB, nullable=False, server_default="{}"),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_pr_tenant_type","prediction_records",["tenant_id","prediction_type"])
    op.create_index("ix_pr_created","prediction_records",["created_at"])

    op.create_table("churn_signals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("churn_score", sa.Float, nullable=False),
        sa.Column("churn_band", sa.String(20), nullable=False),
        sa.Column("observation_mode", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("ds_phase", sa.Integer, nullable=False, server_default="0"),
        sa.Column("contributing_factors", JSONB, nullable=False, server_default="[]"),
        sa.Column("signal_values", JSONB, nullable=False, server_default="{}"),
        sa.Column("prev_score", sa.Float, nullable=True),
        sa.Column("score_delta", sa.Float, nullable=True),
        sa.Column("model_version", sa.String(40), nullable=False, server_default="rule_based_v1"),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", name="uq_churn_tenant"),
    )

    op.create_table("demand_forecasts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("forecast_date", sa.Date, nullable=False),
        sa.Column("horizon_days", sa.Integer, nullable=False, server_default="14"),
        sa.Column("daily_forecasts", JSONB, nullable=False, server_default="[]"),
        sa.Column("total_predicted", sa.Float, nullable=False, server_default="0"),
        sa.Column("peak_day", sa.String(20), nullable=True),
        sa.Column("observation_mode", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("ds_phase", sa.Integer, nullable=False, server_default="0"),
        sa.Column("model_version", sa.String(40), nullable=False, server_default="rule_based_v1"),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id","forecast_date", name="uq_df_tenant_date"),
    )
    op.create_index("ix_df_tenant","demand_forecasts",["tenant_id"])

    op.create_table("staff_performance_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("staff_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("composite_score", sa.Float, nullable=False),
        sa.Column("rank_in_tenant", sa.Integer, nullable=False, server_default="1"),
        sa.Column("signal_values", JSONB, nullable=False, server_default="{}"),
        sa.Column("jobs_completed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("avg_customer_rating", sa.Float, nullable=False, server_default="0"),
        sa.Column("sla_adherence_rate", sa.Float, nullable=False, server_default="100"),
        sa.Column("observation_mode", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("staff_id","tenant_id", name="uq_sps_staff_tenant"),
    )
    op.create_index("ix_sps_tenant","staff_performance_scores",["tenant_id"])

    op.create_table("customer_ltv_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("predicted_ltv", sa.Numeric(10,2), nullable=False),
        sa.Column("ltv_band", sa.String(20), nullable=False),
        sa.Column("booking_frequency", sa.Float, nullable=False, server_default="0"),
        sa.Column("avg_job_value", sa.Numeric(10,2), nullable=False, server_default="0"),
        sa.Column("churn_probability", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("observation_mode", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("customer_id","tenant_id", name="uq_ltv_customer_tenant"),
    )
    op.create_index("ix_ltv_tenant","customer_ltv_scores",["tenant_id"])

    op.create_table("anomaly_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("anomaly_type", sa.String(60), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("detected_value", sa.Float, nullable=False),
        sa.Column("threshold_value", sa.Float, nullable=False),
        sa.Column("context", JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("acknowledged_by", UUID(as_uuid=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.String(500), nullable=True),
        sa.Column("notification_sent", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ar_tenant_status","anomaly_records",["tenant_id","status"])
    op.create_index("ix_ar_created","anomaly_records",["created_at"])

    op.create_table("model_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("model_type", sa.String(80), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("training_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("training_rows", sa.Integer, nullable=False, server_default="0"),
        sa.Column("metrics", JSONB, nullable=False, server_default="{}"),
        sa.Column("parameters", JSONB, nullable=False, server_default="{}"),
        sa.Column("artifact_path", sa.String(500), nullable=True),
        sa.Column("trained_by", sa.String(50), nullable=False, server_default="celery_beat"),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("model_type","version", name="uq_mv_type_version"),
    )
    op.create_index("ix_mv_type_active","model_versions",["model_type","is_active"])


def downgrade() -> None:
    for t in ["model_versions","anomaly_records","customer_ltv_scores",
              "staff_performance_scores","demand_forecasts","churn_signals","prediction_records"]:
        op.drop_table(t)
