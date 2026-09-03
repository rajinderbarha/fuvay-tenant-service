"""Drop the never-used Sprint 34I recommendation rules engine.

Deleted at explicit product request: the engine had zero rules and zero
results, no backend caller outside its own router, and none of its four
context endpoints (bulk setup / provider setup / customer booking / AI) was
ever wired to a UI. Router, service, models, admin pages and both tables are
removed.

Revision ID: 346
Revises: 345
"""
from alembic import op
import sqlalchemy as sa


revision = "346"
down_revision = "345"
branch_labels = None
depends_on = None

TABLES = ("recommendation_results", "recommendation_rules")


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    for table in TABLES:
        if table in existing:
            op.drop_table(table)


def downgrade() -> None:
    # Intentionally irreversible: the model, service, router and admin pages
    # were deleted from the repo, so empty tables would serve no purpose.
    pass
