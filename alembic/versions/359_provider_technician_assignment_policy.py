"""Keep provider ownership and configure technician assignment escalation.

Revision ID: 359
Revises: 358
"""
from alembic import op


revision = "359"
down_revision = "358"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE vertical_monetization_policies ALTER COLUMN assignment_timeout_minutes SET DEFAULT 30")
    op.execute("ALTER TABLE vertical_monetization_policies ADD COLUMN IF NOT EXISTS urgent_assignment_timeout_minutes INTEGER NOT NULL DEFAULT 10")
    op.execute("ALTER TABLE vertical_monetization_policies ADD COLUMN IF NOT EXISTS urgent_assignment_threshold_minutes INTEGER NOT NULL DEFAULT 120")
    op.execute("ALTER TABLE vertical_monetization_policies ADD COLUMN IF NOT EXISTS assignment_auto_assign_enabled BOOLEAN NOT NULL DEFAULT true")
    op.execute("UPDATE vertical_monetization_policies SET assignment_timeout_minutes=30 WHERE assignment_timeout_minutes=15")


def downgrade() -> None:
    op.execute("ALTER TABLE vertical_monetization_policies DROP COLUMN IF EXISTS assignment_auto_assign_enabled")
    op.execute("ALTER TABLE vertical_monetization_policies DROP COLUMN IF EXISTS urgent_assignment_threshold_minutes")
    op.execute("ALTER TABLE vertical_monetization_policies DROP COLUMN IF EXISTS urgent_assignment_timeout_minutes")
    op.execute("ALTER TABLE vertical_monetization_policies ALTER COLUMN assignment_timeout_minutes SET DEFAULT 15")
