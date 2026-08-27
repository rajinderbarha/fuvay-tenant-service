"""Mark team members suspended automatically for lack of credit.

Revision ID: 320
Revises: 319

A workspace whose credit runs out has its technicians set inactive. Doing that
with `status` alone would be irreversible in practice: on top-up there would be
no way to tell who the system had suspended from who the provider had genuinely
deactivated on purpose, so restoring would either miss people or resurrect
someone who was meant to stay off.

`credit_suspended_at` records that this particular deactivation was automatic.
Only rows carrying it are restored when credit returns; a member the provider
switched off by hand has a NULL here and is left exactly as they set it.
"""
from alembic import op

revision = "320"
down_revision = "319"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE provider_team_members
        ADD COLUMN IF NOT EXISTS credit_suspended_at TIMESTAMPTZ NULL
    """)
    # The restore path asks exactly one question: who did we suspend?
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_ptm_credit_suspended
        ON provider_team_members (tenant_id)
        WHERE credit_suspended_at IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ptm_credit_suspended")
    op.execute("ALTER TABLE provider_team_members DROP COLUMN IF EXISTS credit_suspended_at")
