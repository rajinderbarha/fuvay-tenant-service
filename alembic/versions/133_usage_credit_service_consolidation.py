"""FINAL-L5-05J — Usage Credit Service Consolidation.

Adds idempotency_key, source_type, source_id, reason_code, direction to
usage_credit_ledger so the new canonical UsageCreditService can support
manual adjustments and package credit grants with the same idempotency
guarantee Completed Job Deduction already has (job_id + event_type
uniqueness, added in migration 129). Does not touch tenant_billing,
TenantWallet, or wallet_transactions.

Revision ID: 133
Revises: 132
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "133"
down_revision = "132"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = {c["name"] for c in inspector.get_columns("usage_credit_ledger")}

    if "idempotency_key" not in cols:
        op.add_column("usage_credit_ledger", sa.Column("idempotency_key", sa.String(200), nullable=True))
    if "source_type" not in cols:
        op.add_column("usage_credit_ledger", sa.Column("source_type", sa.String(50), nullable=True))
    if "source_id" not in cols:
        op.add_column("usage_credit_ledger", sa.Column("source_id", sa.String(100), nullable=True))
    if "reason_code" not in cols:
        op.add_column("usage_credit_ledger", sa.Column("reason_code", sa.String(50), nullable=True))
    if "actor_role" not in cols:
        op.add_column("usage_credit_ledger", sa.Column("actor_role", sa.String(30), nullable=True))

    existing_indexes = {ix["name"] for ix in inspector.get_indexes("usage_credit_ledger")}
    # Unique per non-null idempotency key — manual adjustments and package
    # grants both require a caller-stable key; Completed Job Deduction keeps
    # using its own job_id+event_type uniqueness (migration 129) and does
    # not set this column.
    if "uq_ucl_idempotency_key" not in existing_indexes:
        op.create_index(
            "uq_ucl_idempotency_key",
            "usage_credit_ledger",
            ["idempotency_key"],
            unique=True,
            postgresql_where=sa.text("idempotency_key IS NOT NULL"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_indexes = {ix["name"] for ix in inspector.get_indexes("usage_credit_ledger")}
    if "uq_ucl_idempotency_key" in existing_indexes:
        op.drop_index("uq_ucl_idempotency_key", table_name="usage_credit_ledger")
    cols = {c["name"] for c in inspector.get_columns("usage_credit_ledger")}
    for col in ("actor_role", "reason_code", "source_id", "source_type", "idempotency_key"):
        if col in cols:
            op.drop_column("usage_credit_ledger", col)
