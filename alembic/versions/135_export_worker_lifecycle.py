"""FINAL-L5-05S — Export Worker, Secure File Generation, Download
Authorization and Retention Certification.

Adds the columns needed for a real export execution lifecycle (claim,
run, complete-with-metadata, fail, cancel) to enterprise_export_jobs.
All additions are nullable/defaulted so existing rows remain valid.

Revision ID: 135
Revises: 134
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "135"
down_revision = "134"
branch_labels = None
depends_on = None

_NEW_COLUMNS = [
    ("worker_id",       sa.String(64)),
    ("claimed_at",      sa.DateTime(timezone=True)),
    ("started_at",      sa.DateTime(timezone=True)),
    ("completed_at",    sa.DateTime(timezone=True)),
    ("cancelled_at",    sa.DateTime(timezone=True)),
    ("retry_count",     sa.Integer),
    ("storage_key",     sa.Text),
    ("filename",        sa.String(255)),
    ("content_type",    sa.String(128)),
    ("file_size",       sa.Integer),
    ("checksum",        sa.String(128)),
    ("error_code",      sa.String(64)),
    ("error_message",   sa.Text),
    ("progress",        sa.Integer),
]


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = {c["name"] for c in inspector.get_columns("enterprise_export_jobs")}

    for name, coltype in _NEW_COLUMNS:
        if name not in cols:
            op.add_column("enterprise_export_jobs", sa.Column(name, coltype, nullable=True))

    # retry_count/progress default to 0 for new rows going forward; backfill
    # existing NULLs so the non-negative CHECK constraint below is satisfiable.
    op.execute("UPDATE enterprise_export_jobs SET retry_count = 0 WHERE retry_count IS NULL")
    op.execute("UPDATE enterprise_export_jobs SET progress = 0 WHERE progress IS NULL")
    op.alter_column("enterprise_export_jobs", "retry_count", server_default="0", nullable=False)
    op.alter_column("enterprise_export_jobs", "progress", server_default="0", nullable=False)

    existing_constraints = {c["name"] for c in inspector.get_check_constraints("enterprise_export_jobs")}

    if "ck_export_jobs_status" not in existing_constraints:
        op.create_check_constraint(
            "ck_export_jobs_status", "enterprise_export_jobs",
            # Matches the pre-existing EXPORT_* constants in
            # app/engines/enterprise_grid/constants.py ("processing", not
            # "running" -- that constant already existed before this
            # sprint; EXPORT_CANCELLED was added this sprint).
            "status IN ('pending','processing','completed','failed','cancelled','expired')",
        )
    if "ck_export_jobs_nonneg_row_count" not in existing_constraints:
        op.create_check_constraint(
            "ck_export_jobs_nonneg_row_count", "enterprise_export_jobs",
            "row_count IS NULL OR row_count >= 0",
        )
    if "ck_export_jobs_nonneg_file_size" not in existing_constraints:
        op.create_check_constraint(
            "ck_export_jobs_nonneg_file_size", "enterprise_export_jobs",
            "file_size IS NULL OR file_size >= 0",
        )
    if "ck_export_jobs_nonneg_retry_count" not in existing_constraints:
        op.create_check_constraint(
            "ck_export_jobs_nonneg_retry_count", "enterprise_export_jobs",
            "retry_count >= 0",
        )

    existing_indexes = {i["name"] for i in inspector.get_indexes("enterprise_export_jobs")}
    if "ix_export_jobs_status_created" not in existing_indexes:
        op.create_index("ix_export_jobs_status_created", "enterprise_export_jobs",
                         ["status", "created_at"])
    if "ix_export_jobs_tenant_id" not in existing_indexes:
        op.create_index("ix_export_jobs_tenant_id", "enterprise_export_jobs", ["tenant_id"])
    if "ix_export_jobs_requested_by" not in existing_indexes:
        op.create_index("ix_export_jobs_requested_by", "enterprise_export_jobs",
                         ["requested_by_user_id"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    existing_indexes = {i["name"] for i in inspector.get_indexes("enterprise_export_jobs")}
    for idx in ("ix_export_jobs_status_created", "ix_export_jobs_tenant_id", "ix_export_jobs_requested_by"):
        if idx in existing_indexes:
            op.drop_index(idx, table_name="enterprise_export_jobs")

    existing_constraints = {c["name"] for c in inspector.get_check_constraints("enterprise_export_jobs")}
    for ck in ("ck_export_jobs_status", "ck_export_jobs_nonneg_row_count",
               "ck_export_jobs_nonneg_file_size", "ck_export_jobs_nonneg_retry_count"):
        if ck in existing_constraints:
            op.drop_constraint(ck, "enterprise_export_jobs", type_="check")

    cols = {c["name"] for c in inspector.get_columns("enterprise_export_jobs")}
    for name, _ in _NEW_COLUMNS:
        if name in cols:
            op.drop_column("enterprise_export_jobs", name)
