"""Align engine governance with current runtime and scale admin queries.

Revision ID: 291
Revises: 290
"""
from alembic import op


revision = "291"
down_revision = "290"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # These core engines are mounted and part of the current platform, but the
    # legacy seed predated their canonical registry identities.
    op.execute("""
        INSERT INTO platform_engines (
            id, engine_key, display_name, description, engine_type,
            lifecycle_status, global_status, is_core, is_locked,
            is_customer_visible, is_tenant_visible, version, owner_team,
            metadata_json, created_at, updated_at
        ) VALUES
        (gen_random_uuid(), 'tenant', 'Tenant Engine',
         'Tenant lifecycle, onboarding, workspace provisioning and access context.',
         'core', 'active', 'locked', true, true, false, true, '2.4.1',
         'Platform', '{}'::jsonb, now(), now()),
        (gen_random_uuid(), 'serviceability', 'Serviceability Engine',
         'Coverage, ranked provider matching and booking preflight.',
         'core', 'active', 'locked', true, true, false, true, '1.0.0',
         'Home Services', '{}'::jsonb, now(), now()),
        (gen_random_uuid(), 'data_science', 'Data Science Engine',
         'Risk, anomaly and prediction workloads used by Intelligence.',
         'core', 'active', 'locked', true, true, false, false, '1.0.0',
         'Intelligence', '{}'::jsonb, now(), now())
        ON CONFLICT (engine_key) DO NOTHING
    """)

    # Tenant exceptions and audit/health history are the high-cardinality
    # sections of this console.  Composite indexes keep filtered newest-first
    # reads bounded as tenants and events grow.
    op.create_index(
        "ix_teo_tenant_status_created_id", "tenant_engine_overrides",
        ["tenant_id", "status", "created_at", "id"],
    )
    op.create_index(
        "ix_teo_status_created_id", "tenant_engine_overrides",
        ["status", "created_at", "id"],
    )
    op.create_index(
        "ix_eal_engine_created_id", "engine_audit_logs",
        ["engine_key", "created_at", "id"],
    )
    op.create_index(
        "ix_eal_action_created_id", "engine_audit_logs",
        ["action_type", "created_at", "id"],
    )
    op.create_index(
        "ix_ehc_engine_checked_id", "engine_health_checks",
        ["engine_key", "checked_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ehc_engine_checked_id", table_name="engine_health_checks")
    op.drop_index("ix_eal_action_created_id", table_name="engine_audit_logs")
    op.drop_index("ix_eal_engine_created_id", table_name="engine_audit_logs")
    op.drop_index("ix_teo_status_created_id", table_name="tenant_engine_overrides")
    op.drop_index("ix_teo_tenant_status_created_id", table_name="tenant_engine_overrides")
    op.execute("""
        DELETE FROM platform_engines
        WHERE engine_key IN ('tenant', 'serviceability', 'data_science')
          AND owner_team IN ('Platform', 'Home Services', 'Intelligence')
    """)
