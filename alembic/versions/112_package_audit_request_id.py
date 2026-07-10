"""Phase 4 finance certification — request_id column on package_audit_logs.

Every audit record must carry the request_id of the mutation that produced
it (Phase 4 ticket's explicit audit-record schema requirement). The
existing PackageAuditLog model had no such column, so request_id could
never be surfaced on package/wallet/deposit audit entries even though the
mutating endpoints already generate a real request_id per request.

Revision ID: 112
Revises: 111
"""
from alembic import op
import sqlalchemy as sa

revision = "112"
down_revision = "111"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = {c["name"] for c in inspector.get_columns("package_audit_logs")}
    if "request_id" not in cols:
        op.add_column(
            "package_audit_logs",
            sa.Column("request_id", sa.String(40), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("package_audit_logs", "request_id")
