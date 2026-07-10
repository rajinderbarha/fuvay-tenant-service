"""Phase 19 — Quote and Approval System: expiry date, parts/labour breakdown,
findings/recommendation snapshots on job_quotes.

Revision ID: 019
Revises: 018
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("job_quotes", sa.Column("parts", JSONB, nullable=False, server_default="[]"))
    op.add_column("job_quotes", sa.Column("labour_estimate", sa.Numeric(10, 2), nullable=True))
    op.add_column("job_quotes", sa.Column("findings_snapshot", sa.Text, nullable=True))
    op.add_column("job_quotes", sa.Column("recommendation_snapshot", sa.Text, nullable=True))
    op.add_column("job_quotes", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("job_quotes", "expires_at")
    op.drop_column("job_quotes", "recommendation_snapshot")
    op.drop_column("job_quotes", "findings_snapshot")
    op.drop_column("job_quotes", "labour_estimate")
    op.drop_column("job_quotes", "parts")
