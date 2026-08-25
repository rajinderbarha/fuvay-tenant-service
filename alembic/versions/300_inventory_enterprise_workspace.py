"""Enterprise inventory catalogue, pricing, and engine provisioning.

Revision ID: 300
Revises: 299

Inventory categories were stored only as display text, which could drift from
the admin-owned service-group catalogue.  Customer part pricing was also
conflated with provider acquisition cost.  This migration gives both concepts
stable, explicit columns and adds the indexes used by the provider workspace.

It also repairs active Home Services tenants created with an empty engine list:
the canonical defaults are inserted explicitly, preserving later admin disable
controls while making inventory available to already-approved providers.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "300"
down_revision = "299"
branch_labels = None
depends_on = None


HOME_SERVICES_DEFAULT_ENGINES = (
    "auth", "tenant", "platform_commerce", "pricing", "notification",
    "settings", "analytics", "media", "chat", "review", "field_ops",
    "booking", "appointment", "dispatch", "geo", "inventory", "payment",
    "subscription", "document", "webhook", "data_science",
)


def upgrade() -> None:
    op.add_column(
        "inventory_items",
        sa.Column("service_group_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "inventory_items",
        sa.Column("selling_price", sa.Numeric(10, 2), nullable=True),
    )
    op.create_index(
        "ix_inventory_items_tenant_status_name",
        "inventory_items",
        ["tenant_id", "is_active", "status", "name"],
    )
    op.create_index(
        "ix_inventory_items_service_group",
        "inventory_items",
        ["service_group_id"],
    )
    op.create_index(
        "ix_stock_balances_tenant_item",
        "stock_balances",
        ["tenant_id", "item_id"],
    )
    op.create_index(
        "ix_stock_transactions_tenant_created",
        "stock_transactions",
        ["tenant_id", "created_at"],
    )

    # Existing unit_cost values were the only price shown to providers.  Treat
    # them as the initial customer price so the migration never makes a live
    # item unpriced; providers can then separate acquisition cost and margin.
    op.execute("UPDATE inventory_items SET selling_price = unit_cost WHERE selling_price IS NULL")
    op.execute("""
        UPDATE inventory_items AS ii
           SET service_group_id = sg.id
          FROM service_groups AS sg
         WHERE ii.service_group_id IS NULL
           AND ii.category IS NOT NULL
           AND lower(trim(ii.category)) IN (lower(trim(sg.name)), lower(trim(sg.slug)))
    """)

    values = ",\n".join(
        f"(t.id, '{engine}', true, '{{}}'::jsonb, now(), now(), now())"
        for engine in HOME_SERVICES_DEFAULT_ENGINES
    )
    op.execute(f"""
        INSERT INTO tenant_engines
            (tenant_id, engine_id, is_enabled, config, activated_at, created_at, updated_at)
        SELECT v.tenant_id, v.engine_id, v.is_enabled, v.config,
               v.activated_at, v.created_at, v.updated_at
          FROM tenants t
          CROSS JOIN LATERAL (
              VALUES {values}
          ) AS v(tenant_id, engine_id, is_enabled, config, activated_at, created_at, updated_at)
         WHERE t.vertical = 'home_services'
           AND t.status IN ('active', 'trial', 'pending_activation')
        ON CONFLICT (tenant_id, engine_id) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_index("ix_stock_transactions_tenant_created", table_name="stock_transactions")
    op.drop_index("ix_stock_balances_tenant_item", table_name="stock_balances")
    op.drop_index("ix_inventory_items_service_group", table_name="inventory_items")
    op.drop_index("ix_inventory_items_tenant_status_name", table_name="inventory_items")
    op.drop_column("inventory_items", "selling_price")
    op.drop_column("inventory_items", "service_group_id")

