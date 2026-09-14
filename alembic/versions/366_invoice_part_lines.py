"""Link invoice lines to the parts request they bill.

A part the customer approved is billed as its own invoice line. The link
lets the invoice add each approved part exactly once, and lets fee and
commission bases leave those parts out.

Revision ID: 366
Revises: 365
"""
from alembic import op


revision = "366"
down_revision = "365"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE service_invoice_items
        ADD COLUMN IF NOT EXISTS source_parts_request_id UUID NULL
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_sii_invoice_parts_request
        ON service_invoice_items (invoice_id, source_parts_request_id)
        WHERE source_parts_request_id IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_sii_invoice_parts_request")
    op.execute("ALTER TABLE service_invoice_items DROP COLUMN IF EXISTS source_parts_request_id")
