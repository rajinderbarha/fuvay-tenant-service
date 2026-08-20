"""Retire the removed bargain engine from active governance.

Revision ID: 292
Revises: 291
"""
from alembic import op


revision = "292"
down_revision = "291"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM engine_dependencies WHERE engine_key = 'bargain'")
    op.execute("DELETE FROM engine_health_checks WHERE engine_key = 'bargain'")
    op.execute("""
        UPDATE platform_engines
        SET global_status = 'disabled', lifecycle_status = 'retired',
            description = 'Retired: provider-owned pricing replaced the legacy bargain engine.',
            updated_at = now()
        WHERE engine_key = 'bargain'
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE platform_engines
        SET global_status = 'disabled', lifecycle_status = 'deprecated',
            updated_at = now()
        WHERE engine_key = 'bargain'
    """)
