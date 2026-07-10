"""Sprint 28 — Category Analytics + Provider/Admin Reports.

Revision ID: 046
Revises: 045
Creates:
  - analytics_daily_metrics  (summary table for cached aggregates)
  - analytics_report_runs    (tracks report export jobs)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "046"
down_revision = "045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── analytics_daily_metrics ──────────────────────────────────────────────
    op.create_table(
        "analytics_daily_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("metric_date",  sa.Date(),        nullable=False),
        sa.Column("tenant_id",    UUID(as_uuid=True), nullable=True),
        sa.Column("category_id",  UUID(as_uuid=True), nullable=True),
        sa.Column("offering_id",  UUID(as_uuid=True), nullable=True),
        sa.Column("city",         sa.String(100),   nullable=True),
        sa.Column("zone_id",      UUID(as_uuid=True), nullable=True),
        sa.Column("metric_key",   sa.String(120),   nullable=False),
        sa.Column("metric_value", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("metric_metadata", JSONB,          nullable=True),
        sa.Column("created_at",   sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",   sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_adm_date",        "analytics_daily_metrics", ["metric_date"])
    op.create_index("ix_adm_tenant",      "analytics_daily_metrics", ["tenant_id"])
    op.create_index("ix_adm_category",    "analytics_daily_metrics", ["category_id"])
    op.create_index("ix_adm_metric_key",  "analytics_daily_metrics", ["metric_key"])
    op.create_unique_constraint(
        "uq_adm_daily",
        "analytics_daily_metrics",
        ["metric_date", "metric_key", "tenant_id", "category_id", "offering_id"],
    )

    # ── analytics_report_runs ────────────────────────────────────────────────
    op.create_table(
        "analytics_report_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("report_key",          sa.String(100), nullable=False),
        sa.Column("report_name",         sa.String(200), nullable=True),
        sa.Column("scope",               sa.String(20),  nullable=False, server_default="admin"),
        sa.Column("requested_by_user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",           UUID(as_uuid=True), nullable=True),
        sa.Column("status",              sa.String(20),  nullable=False, server_default="pending"),
        sa.Column("filters",             JSONB,          nullable=False, server_default="{}"),
        sa.Column("result_summary",      JSONB,          nullable=True),
        sa.Column("row_count",           sa.Integer(),   nullable=True),
        sa.Column("file_url",            sa.String(1000), nullable=True),
        sa.Column("export_format",       sa.String(10),  nullable=True),
        sa.Column("failure_reason",      sa.Text(),      nullable=True),
        sa.Column("created_at",          sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at",        sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_arr_status",        "analytics_report_runs", ["status"])
    op.create_index("ix_arr_tenant",        "analytics_report_runs", ["tenant_id"])
    op.create_index("ix_arr_requested_by",  "analytics_report_runs", ["requested_by_user_id"])
    op.create_index("ix_arr_report_key",    "analytics_report_runs", ["report_key"])
    op.create_index("ix_arr_created_at",    "analytics_report_runs", ["created_at"])


def downgrade() -> None:
    op.drop_table("analytics_report_runs")
    op.drop_table("analytics_daily_metrics")
