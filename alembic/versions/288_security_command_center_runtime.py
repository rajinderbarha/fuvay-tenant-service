"""Make the Security command center runtime-backed and scale-safe.

Revision ID: 288
Revises: 287
"""
from alembic import op

revision = "288"
down_revision = "287"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Older environments created the policies table conditionally and could
    # therefore miss the seed insert.  The UI must never open to an empty,
    # non-configurable policy screen.
    op.execute("""
        INSERT INTO security_policies
            (id, policy_key, policy_value_json, description, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'mfa_required_super_admin', 'true'::jsonb, 'Require MFA for Super Admin accounts', now(), now()),
            (gen_random_uuid(), 'mfa_required_platform_admin', 'true'::jsonb, 'Require MFA for delegated platform admin accounts', now(), now()),
            (gen_random_uuid(), 'fresh_mfa_for_sensitive_actions', 'true'::jsonb, 'Require a fresh MFA challenge before sensitive actions', now(), now()),
            (gen_random_uuid(), 'failed_login_threshold', '5'::jsonb, 'Failed attempts before temporary account lock', now(), now()),
            (gen_random_uuid(), 'auto_lock_threshold', '10'::jsonb, 'Failed attempts before long-term security lock', now(), now()),
            (gen_random_uuid(), 'session_max_lifetime_minutes', '1440'::jsonb, 'Maximum lifetime applied to every newly issued session', now(), now()),
            (gen_random_uuid(), 'idle_timeout_minutes', '30'::jsonb, 'Inactivity window before refresh is denied', now(), now()),
            (gen_random_uuid(), 'api_key_max_expiry_days', '365'::jsonb, 'Maximum lifetime allowed for tenant API keys', now(), now()),
            (gen_random_uuid(), 'ip_block_auto_expiry_default_days', '30'::jsonb, 'Default lifetime for a temporary network block', now(), now()),
            (gen_random_uuid(), 'export_audit_retention_days', '365'::jsonb, 'Retention period for generated audit export files', now(), now())
        ON CONFLICT (policy_key) DO NOTHING
    """)

    # Sessions written before the policy became runtime-backed had no maximum
    # lifetime and inflated the active-session count forever.
    op.execute("""
        UPDATE user_sessions
        SET expires_at = created_at + interval '24 hours'
        WHERE expires_at IS NULL
    """)

    # Keep one active block for a network/scope owner while preserving revoked
    # history.  The old NULL-sensitive table constraint prevented safe re-blocks
    # for tenants and still allowed duplicate global blocks.
    op.execute("""
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY ip_or_cidr, coalesce(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid)
                       ORDER BY created_at DESC, id DESC
                   ) AS rn
            FROM ip_blocklist
            WHERE status = 'active'
        )
        UPDATE ip_blocklist b
        SET status = 'revoked', is_active = false,
            revoked_at = coalesce(b.revoked_at, now())
        FROM ranked r
        WHERE b.id = r.id AND r.rn > 1
    """)
    op.execute("ALTER TABLE ip_blocklist DROP CONSTRAINT IF EXISTS uq_ibl_ip_tenant")

    with op.get_context().autocommit_block():
        indexes = {
            "uq_ibl_active_network_owner": "ip_blocklist (ip_or_cidr, coalesce(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid)) WHERE status = 'active'",
            "ix_sal_status_created_id": "suspicious_activity_logs (status, created_at DESC, id DESC)",
            "ix_sal_level_status_created": "suspicious_activity_logs (threat_level, status, created_at DESC)",
            "ix_user_sessions_active_last_id": "user_sessions (last_active_at DESC, id DESC) WHERE revoked_at IS NULL",
            "ix_user_sessions_tenant_active_last": "user_sessions (tenant_id, last_active_at DESC, id DESC) WHERE revoked_at IS NULL",
            "ix_ibl_status_created_id": "ip_blocklist (status, created_at DESC, id DESC)",
            "ix_ibl_status_hits": "ip_blocklist (status, hit_count DESC, id DESC)",
            "ix_tenant_api_keys_status_created": "tenant_api_keys (status, created_at DESC, id DESC)",
            "ix_tenant_api_keys_expiry_active": "tenant_api_keys (expires_at, id) WHERE status = 'active' AND expires_at IS NOT NULL",
            "ix_pal_high_risk_created_id": "platform_audit_logs (created_at DESC, id DESC) WHERE is_high_risk",
            "ix_login_events_type_created_id": "login_events (event_type, created_at DESC, id DESC)",
            "ix_ibh_block_hit_desc": "ip_block_hits (block_id, hit_at DESC, id DESC)",
            "ix_akul_key_used_desc": "api_key_usage_logs (api_key_id, used_at DESC, id DESC)",
        }
        for name, definition in indexes.items():
            unique = "UNIQUE " if name.startswith("uq_") else ""
            op.execute(f'CREATE {unique}INDEX CONCURRENTLY IF NOT EXISTS "{name}" ON {definition}')


def downgrade() -> None:
    names = (
        "uq_ibl_active_network_owner", "ix_sal_status_created_id",
        "ix_sal_level_status_created", "ix_user_sessions_active_last_id",
        "ix_user_sessions_tenant_active_last", "ix_ibl_status_created_id",
        "ix_ibl_status_hits", "ix_tenant_api_keys_status_created",
        "ix_tenant_api_keys_expiry_active", "ix_pal_high_risk_created_id",
        "ix_login_events_type_created_id", "ix_ibh_block_hit_desc",
        "ix_akul_key_used_desc",
    )
    with op.get_context().autocommit_block():
        for name in names:
            op.execute(f'DROP INDEX CONCURRENTLY IF EXISTS "{name}"')

