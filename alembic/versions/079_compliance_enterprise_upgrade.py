"""Compliance Enterprise Upgrade — DPDP Act 2023
- Create compliance_requests (unified enterprise request table with request_number, subject_type, sla_status, verification_status)
- Create compliance_request_items (data inventory scan items per request)
- Create compliance_exports (enterprise export tracking)

Revision ID: 079
Revises: 078
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "079"
down_revision = "078"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── compliance_requests — unified enterprise request table ────────────────
    op.create_table(
        "compliance_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("request_number", sa.String(30), nullable=False, unique=True),
        sa.Column("subject_type", sa.String(30), nullable=False),
        sa.Column("subject_id", UUID(as_uuid=True), nullable=False),
        sa.Column("subject_email", sa.String(255), nullable=True),
        sa.Column("subject_name", sa.String(200), nullable=True),
        sa.Column("request_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="submitted"),
        sa.Column("sla_status", sa.String(20), nullable=False, server_default="on_track"),
        sa.Column("verification_status", sa.String(20), nullable=False, server_default="not_required"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True,
                  server_default=sa.text("now()")),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_to_admin_id", UUID(as_uuid=True), nullable=True),
        sa.Column("request_source", sa.String(30), nullable=False, server_default="admin_created"),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("admin_notes", sa.Text, nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("metadata_json", JSONB, nullable=True, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_compliance_requests_subject", "compliance_requests", ["subject_id"])
    op.create_index("ix_compliance_requests_status", "compliance_requests", ["status"])
    op.create_index("ix_compliance_requests_type", "compliance_requests", ["request_type"])
    op.create_index("ix_compliance_requests_sla", "compliance_requests", ["sla_status"])
    op.create_index("ix_compliance_requests_due", "compliance_requests", ["due_at"])

    # ── compliance_request_items — data inventory scan results ────────────────
    op.create_table(
        "compliance_request_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("request_id", UUID(as_uuid=True),
                  sa.ForeignKey("compliance_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module_name", sa.String(100), nullable=False),
        sa.Column("record_type", sa.String(100), nullable=False),
        sa.Column("record_id", UUID(as_uuid=True), nullable=True),
        sa.Column("record_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("planned_action", sa.String(20), nullable=False, server_default="manual_review"),
        sa.Column("actual_action", sa.String(20), nullable=True),
        sa.Column("exemption_reason", sa.Text, nullable=True),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_compliance_request_items_request", "compliance_request_items", ["request_id"])
    op.create_index("ix_compliance_request_items_status", "compliance_request_items", ["status"])

    # ── compliance_exports — enterprise export tracking ───────────────────────
    op.create_table(
        "compliance_exports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("request_id", UUID(as_uuid=True),
                  sa.ForeignKey("compliance_requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("subject_type", sa.String(30), nullable=False),
        sa.Column("subject_id", UUID(as_uuid=True), nullable=False),
        sa.Column("export_format", sa.String(10), nullable=False, server_default="json"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("download_url", sa.String(2000), nullable=True),
        sa.Column("file_size_bytes", sa.Integer, nullable=True),
        sa.Column("record_count", sa.Integer, nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_compliance_exports_subject", "compliance_exports", ["subject_id"])
    op.create_index("ix_compliance_exports_request", "compliance_exports", ["request_id"])
    op.create_index("ix_compliance_exports_status", "compliance_exports", ["status"])


def downgrade() -> None:
    op.drop_table("compliance_exports")
    op.drop_table("compliance_request_items")
    op.drop_table("compliance_requests")
