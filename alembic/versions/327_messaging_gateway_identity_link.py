"""Add encrypted pending identity-link state to messaging threads.

Revision ID: 327
Revises: 326
"""
from alembic import op


revision = "327"
down_revision = "326"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS also repairs databases where an unreleased draft of 326
    # already added either column before this forward-only migration landed.
    op.execute("ALTER TABLE messaging_threads ADD COLUMN IF NOT EXISTS pending_customer_id UUID")
    op.execute("ALTER TABLE messaging_threads ADD COLUMN IF NOT EXISTS pending_phone_ciphertext TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE messaging_threads DROP COLUMN IF EXISTS pending_phone_ciphertext")
    op.execute("ALTER TABLE messaging_threads DROP COLUMN IF EXISTS pending_customer_id")
