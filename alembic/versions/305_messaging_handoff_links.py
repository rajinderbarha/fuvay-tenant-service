"""Messaging gateway — single-use handoff links from chat to the web surface.

Revision ID: 305
Revises: 304
"""
from alembic import op

revision = "305"
down_revision = "304"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Follows the same shape as `media_signed_links`: only the SHA-256 HASH of
    # the token is stored, never the token itself, so a database read cannot be
    # replayed as a login. Single use is enforced by an atomic
    # UPDATE ... WHERE status='active' RETURNING, which two concurrent clicks
    # cannot both win.
    op.execute("""
        CREATE TABLE IF NOT EXISTS messaging_handoff_links (
            id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            token_hash     VARCHAR(64)  NOT NULL,
            thread_id      UUID,
            customer_id    UUID,
            draft_id       UUID,
            reason         VARCHAR(40),
            target_path    VARCHAR(300) NOT NULL,
            status         VARCHAR(20)  NOT NULL DEFAULT 'active',
            expires_at     TIMESTAMPTZ  NOT NULL,
            used_at        TIMESTAMPTZ,
            created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
            deleted_at     TIMESTAMPTZ,
            CONSTRAINT uq_msg_handoff_token UNIQUE (token_hash)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_msg_handoff_thread ON messaging_handoff_links (thread_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_msg_handoff_draft ON messaging_handoff_links (draft_id)")
    # Lets an expiry sweep find stale rows without scanning the table.
    op.execute("CREATE INDEX IF NOT EXISTS ix_msg_handoff_active_expiry ON messaging_handoff_links (expires_at) WHERE status = 'active'")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS messaging_handoff_links")
