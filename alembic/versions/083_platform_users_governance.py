"""Platform Users Governance — platform_role, access_scope, invited_by columns on users.

Revision ID: 083
Revises: 082
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "083"
down_revision = "082"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("platform_role", sa.String(50), nullable=True))
    op.add_column("users", sa.Column("access_scope", sa.String(50), nullable=True))
    op.add_column("users", sa.Column("invited_by_user_id", UUID(as_uuid=True), nullable=True))

    op.create_index("ix_users_platform_role", "users", ["platform_role"])
    op.create_index("ix_users_access_scope", "users", ["access_scope"])

    # Backfill existing super_admin accounts as the top-level platform role/scope
    op.execute("""
        UPDATE users
        SET platform_role = 'super_admin', access_scope = 'global'
        WHERE role = 'super_admin' AND platform_role IS NULL
    """)


def downgrade() -> None:
    op.drop_index("ix_users_access_scope", table_name="users")
    op.drop_index("ix_users_platform_role", table_name="users")
    op.drop_column("users", "invited_by_user_id")
    op.drop_column("users", "access_scope")
    op.drop_column("users", "platform_role")
