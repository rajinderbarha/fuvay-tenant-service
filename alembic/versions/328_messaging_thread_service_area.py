"""Remember a chat's pincode and city on the thread.

The scripted booking flow asks for the service area BEFORE anything else, so
that a customer is never walked through picking a service, a problem and half a
dozen catalog questions only to be told at the end that nobody covers them.
That answer arrives before a booking draft exists, so it belongs to the thread
rather than the draft — and keeping it there also means a returning customer is
not asked for the same pincode twice.

Revision ID: 328
Revises: 327
"""
from alembic import op


revision = "328"
down_revision = "327"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE messaging_threads ADD COLUMN IF NOT EXISTS zipcode VARCHAR(12)")
    op.execute("ALTER TABLE messaging_threads ADD COLUMN IF NOT EXISTS city VARCHAR(120)")


def downgrade() -> None:
    op.execute("ALTER TABLE messaging_threads DROP COLUMN IF EXISTS city")
    op.execute("ALTER TABLE messaging_threads DROP COLUMN IF EXISTS zipcode")
