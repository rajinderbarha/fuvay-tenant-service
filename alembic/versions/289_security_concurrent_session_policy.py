"""Add the enforced concurrent-session policy.

Revision ID: 289
Revises: 288
"""
from alembic import op

revision = "289"
down_revision = "288"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The original seed exposed MFA toggles before login enforcement existed.
    # Keep upgrades safe: only reset untouched defaults, never an operator's
    # explicitly audited choice.
    op.execute("""
        UPDATE security_policies
        SET policy_value_json = 'false'::jsonb, updated_at = now()
        WHERE policy_key IN ('mfa_required_super_admin', 'mfa_required_platform_admin')
          AND updated_by_user_id IS NULL
    """)
    op.execute("DELETE FROM security_policies WHERE policy_key = 'fresh_mfa_for_sensitive_actions'")
    op.execute("""
        INSERT INTO security_policies
            (id, policy_key, policy_value_json, description, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'max_concurrent_sessions', '10'::jsonb,
             'Maximum active sessions retained per user after sign-in', now(), now())
        ON CONFLICT (policy_key) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM security_policies WHERE policy_key = 'max_concurrent_sessions'")
