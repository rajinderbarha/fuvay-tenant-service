"""Phase 0C — Profile Edit: add display_name, language, timezone to users.

Revision ID: 051
Revises: 050
"""
from alembic import op
import sqlalchemy as sa

revision = "051"
down_revision = "050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("language",     sa.String(10),  nullable=True, server_default="en"))
    op.add_column("users", sa.Column("timezone",     sa.String(60),  nullable=True, server_default="UTC"))


def downgrade() -> None:
    op.drop_column("users", "timezone")
    op.drop_column("users", "language")
    op.drop_column("users", "display_name")
