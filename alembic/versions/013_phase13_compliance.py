"""Phase 13 — Compliance Engine (5 tables)
Revision ID: 013
Revises: 012
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("consent_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",        UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",      UUID(as_uuid=True), nullable=True),
        sa.Column("consent_type",   sa.String(50),  nullable=False),
        sa.Column("action",         sa.String(20),  nullable=False),
        sa.Column("policy_version", sa.String(20),  nullable=False),
        sa.Column("granted_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address",     sa.String(50),  nullable=True),
        sa.Column("user_agent",     sa.String(500), nullable=True),
        sa.Column("source",         sa.String(50),  nullable=True),
        sa.Column("meta",           JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_cr_user",        "consent_records", ["user_id"])
    op.create_index("ix_cr_tenant",      "consent_records", ["tenant_id"])
    op.create_index("ix_cr_type_action", "consent_records", ["consent_type","action"])

    op.create_table("data_deletion_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",            UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",          UUID(as_uuid=True), nullable=True),
        sa.Column("request_reason",     sa.String(500),  nullable=True),
        sa.Column("status",             sa.String(20),   nullable=False, server_default="pending"),
        sa.Column("sla_deadline",       sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("tables_erased",      JSONB, nullable=False, server_default="[]"),
        sa.Column("tables_exempted",    JSONB, nullable=False, server_default="[]"),
        sa.Column("exemption_reasons",  JSONB, nullable=False, server_default="{}"),
        sa.Column("rejection_reason",   sa.String(500),  nullable=True),
        sa.Column("processed_by",       sa.String(20),   nullable=True),
        sa.Column("idempotency_key",    sa.String(64),   nullable=True, unique=True),
        sa.Column("verification_token", sa.String(64),   nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_ddr_idem"),
    )
    op.create_index("ix_ddr_user",   "data_deletion_requests", ["user_id"])
    op.create_index("ix_ddr_status", "data_deletion_requests", ["status"])
    op.create_index("ix_ddr_sla",    "data_deletion_requests", ["sla_deadline"])

    op.create_table("data_portability_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",             UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id",           UUID(as_uuid=True), nullable=True),
        sa.Column("status",              sa.String(20), nullable=False, server_default="queued"),
        sa.Column("sla_deadline",        sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_categories",     JSONB, nullable=False, server_default="[]"),
        sa.Column("export_format",       sa.String(10), nullable=False, server_default="json"),
        sa.Column("storage_key",         sa.String(500), nullable=True),
        sa.Column("download_url",        sa.String(2000), nullable=True),
        sa.Column("download_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("downloaded_at",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("record_count",        sa.Integer, nullable=False, server_default="0"),
        sa.Column("size_bytes",          sa.Integer, nullable=False, server_default="0"),
        sa.Column("completed_at",        sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key",     sa.String(64), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_dpr_idem"),
    )
    op.create_index("ix_dpr_user",   "data_portability_requests", ["user_id"])
    op.create_index("ix_dpr_status", "data_portability_requests", ["status"])

    op.create_table("data_retention_policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("table_name",       sa.String(100),     nullable=False),
        sa.Column("tenant_id",        UUID(as_uuid=True), nullable=True),
        sa.Column("retention_days",   sa.Integer,         nullable=False),
        sa.Column("is_exempt",        sa.Boolean,         nullable=False, server_default="false"),
        sa.Column("exemption_reason", sa.String(500),     nullable=True),
        sa.Column("legal_basis",      sa.String(200),     nullable=True),
        sa.Column("last_purge_at",    sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_purge_at",    sa.DateTime(timezone=True), nullable=True),
        sa.Column("set_by",           UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("table_name","tenant_id", name="uq_drp_table_tenant"),
    )
    op.create_index("ix_drp_table", "data_retention_policies", ["table_name"])

    op.create_table("compliance_audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",        UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id",      UUID(as_uuid=True), nullable=True),
        sa.Column("action",         sa.String(100),     nullable=False),
        sa.Column("table_accessed", sa.String(100),     nullable=True),
        sa.Column("purpose",        sa.String(200),     nullable=True),
        sa.Column("legal_basis",    sa.String(100),     nullable=True),
        sa.Column("actor_id",       UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role",     sa.String(30),      nullable=True),
        sa.Column("actor_ip",       sa.String(50),      nullable=True),
        sa.Column("reference_id",   sa.String(100),     nullable=True),
        sa.Column("meta",           JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_cal_user",    "compliance_audit_logs", ["user_id"])
    op.create_index("ix_cal_action",  "compliance_audit_logs", ["action"])
    op.create_index("ix_cal_created", "compliance_audit_logs", ["created_at"])
    op.create_index("ix_cal_tenant",  "compliance_audit_logs", ["tenant_id"])

def downgrade() -> None:
    for t in ["compliance_audit_logs","data_retention_policies",
              "data_portability_requests","data_deletion_requests","consent_records"]:
        op.drop_table(t)
