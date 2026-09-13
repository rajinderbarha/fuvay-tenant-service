"""Add enterprise authentication policy controls.

Revision ID: 362
Revises: 361
"""
from alembic import op


revision = "362"
down_revision = "361"
branch_labels = None
depends_on = None


POLICY_KEYS = (
    "temporary_lockout_minutes",
    "access_token_lifetime_minutes",
    "refresh_token_lifetime_days",
    "password_min_length",
    "password_history_count",
)


def upgrade() -> None:
    # Preserve the platform's current behaviour at deploy time. Administrators
    # can move to the stronger recommended values deliberately from Security,
    # with validation and an immutable reason-bearing audit event.
    op.execute("""
        INSERT INTO security_policies
            (id, policy_key, policy_value_json, description, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'temporary_lockout_minutes', '15'::jsonb,
             'Temporary lock duration after the failed-login threshold is reached', now(), now()),
            (gen_random_uuid(), 'access_token_lifetime_minutes', '480'::jsonb,
             'Maximum lifetime for newly issued access tokens', now(), now()),
            (gen_random_uuid(), 'refresh_token_lifetime_days', '7'::jsonb,
             'Maximum lifetime for newly issued refresh tokens', now(), now()),
            (gen_random_uuid(), 'password_min_length', '8'::jsonb,
             'Minimum password length for new and changed passwords', now(), now()),
            (gen_random_uuid(), 'password_history_count', '5'::jsonb,
             'Number of previous passwords that cannot be reused', now(), now())
        ON CONFLICT (policy_key) DO NOTHING
    """)


def downgrade() -> None:
    quoted = ", ".join(f"'{key}'" for key in POLICY_KEYS)
    op.execute(f"DELETE FROM security_policies WHERE policy_key IN ({quoted})")
