"""Inventory item GST + warranty fields.

USER REQ: draft-review / create-item forms need GST % and warranty for each
inventory item. Neither existed on InventoryItem before this migration.
gst is a plain numeric percentage (e.g. 0/5/12/18/28 India GST slabs are
common values but the column is not constrained to an enum). warranty is a
free-text field (e.g. "12 months") since no other real warranty pattern
exists elsewhere in the codebase to follow.

Revision ID: 146
Revises: 145
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "146"
down_revision = "145"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "inventory_items",
        sa.Column("gst", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "inventory_items",
        sa.Column("warranty", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("inventory_items", "warranty")
    op.drop_column("inventory_items", "gst")
