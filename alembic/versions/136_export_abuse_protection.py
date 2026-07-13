"""FINAL-L5-05AA — Export Rate Limit, Concurrency, Idempotency and Abuse
Protection Certification.

Adds idempotency support to enterprise_export_jobs: a nullable
idempotency_key column, scoped unique to (requested_by_user_id,
idempotency_key) so the same actor's replayed request resolves to the
same logical job, while two different actors (or the same actor without
a key) are never falsely deduplicated.

Revision ID: 136
Revises: 135
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "136"
down_revision = "135"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = {c["name"] for c in inspector.get_columns("enterprise_export_jobs")}

    if "idempotency_key" not in cols:
        op.add_column(
            "enterprise_export_jobs",
            sa.Column("idempotency_key", sa.String(128), nullable=True),
        )

    existing_indexes = {i["name"] for i in inspector.get_indexes("enterprise_export_jobs")}
    existing_constraints = {
        c["name"] for c in inspector.get_unique_constraints("enterprise_export_jobs")
    }
    # Partial unique index (not a table-wide UniqueConstraint) so multiple
    # NULL idempotency_key rows (the overwhelming majority -- the header is
    # optional) never collide; only rows that actually supplied a key are
    # constrained, scoped per-actor so two different users can coincidentally
    # choose the same client-generated key string without conflict.
    if "uq_export_jobs_actor_idempotency_key" not in existing_indexes and \
       "uq_export_jobs_actor_idempotency_key" not in existing_constraints:
        op.execute(
            "CREATE UNIQUE INDEX uq_export_jobs_actor_idempotency_key "
            "ON enterprise_export_jobs (requested_by_user_id, idempotency_key) "
            "WHERE idempotency_key IS NOT NULL"
        )

    if "ix_export_jobs_actor_status" not in existing_indexes:
        op.create_index(
            "ix_export_jobs_actor_status", "enterprise_export_jobs",
            ["requested_by_user_id", "status"],
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    existing_indexes = {i["name"] for i in inspector.get_indexes("enterprise_export_jobs")}
    if "ix_export_jobs_actor_status" in existing_indexes:
        op.drop_index("ix_export_jobs_actor_status", table_name="enterprise_export_jobs")

    op.execute("DROP INDEX IF EXISTS uq_export_jobs_actor_idempotency_key")

    cols = {c["name"] for c in inspector.get_columns("enterprise_export_jobs")}
    if "idempotency_key" in cols:
        op.drop_column("enterprise_export_jobs", "idempotency_key")
