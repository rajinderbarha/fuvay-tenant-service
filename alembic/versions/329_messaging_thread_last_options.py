"""Remember the option ids of the last list a thread was sent.

Instagram has no list message, so options are sent as a numbered text list and
answered with a number. Resolving that number by rebuilding the current step
is not sound: several lists are reachable only through an earlier choice (a
category's offerings), and a "Show more" page cannot be rebuilt from the step
alone either — both mismap silently. The ids actually sent are the only honest
thing to resolve against.

Revision ID: 329
Revises: 328
"""
from alembic import op


revision = "329"
down_revision = "328"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE messaging_threads ADD COLUMN IF NOT EXISTS last_options JSONB")


def downgrade() -> None:
    op.execute("ALTER TABLE messaging_threads DROP COLUMN IF EXISTS last_options")
