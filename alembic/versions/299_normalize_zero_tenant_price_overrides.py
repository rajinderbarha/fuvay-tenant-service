"""Normalize invalid zero tenant service prices to inheritance.

Revision ID: 299
Revises: 298

The setup form previously saved an empty sibling field as zero on blur. A
``0-0`` dimension override then outranked a valid service default and exposed a
free customer price. Clearing it restores the documented inheritance chain.
"""
from alembic import op


revision = "299"
down_revision = "298"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE tenant_service_types
           SET tenant_min_price = NULL, tenant_max_price = NULL, updated_at = now()
         WHERE tenant_min_price = 0 AND tenant_max_price = 0
    """)
    op.execute("""
        UPDATE tenant_service_brands
           SET tenant_min_price = NULL, tenant_max_price = NULL, updated_at = now()
         WHERE tenant_min_price = 0 AND tenant_max_price = 0
    """)
    op.execute("""
        UPDATE tenant_services
           SET tenant_min_price = NULL, tenant_max_price = NULL, updated_at = now()
         WHERE tenant_min_price = 0 AND tenant_max_price = 0
    """)


def downgrade() -> None:
    # NULL means "inherit" and cannot be distinguished from a field that was
    # always empty, so recreating invalid zero overrides would be destructive.
    pass
