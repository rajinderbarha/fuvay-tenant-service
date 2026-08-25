"""Messaging gateway — WhatsApp/Instagram thread mapping and inbound de-duplication.

Revision ID: 304
Revises: 303
"""
from alembic import op

revision = "304"
down_revision = "303"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Thread <-> customer <-> live agent session. Without this every inbound
    # message would open a new conversation and the agent would lose the
    # booking draft it is part-way through building.
    op.execute("""
        CREATE TABLE IF NOT EXISTS messaging_threads (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            channel              VARCHAR(20)  NOT NULL,
            channel_user_id      VARCHAR(120) NOT NULL,
            channel_business_id  VARCHAR(120),
            display_name         VARCHAR(160),
            customer_id          UUID,
            tenant_id            UUID,
            ai_session_id        UUID,
            opted_out            BOOLEAN NOT NULL DEFAULT FALSE,
            human_handoff        BOOLEAN NOT NULL DEFAULT FALSE,
            last_inbound_at      TIMESTAMPTZ,
            last_outbound_at     TIMESTAMPTZ,
            session_count        INTEGER NOT NULL DEFAULT 0,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at           TIMESTAMPTZ,
            CONSTRAINT uq_msg_thread_channel_user UNIQUE (channel, channel_user_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_msg_thread_customer ON messaging_threads (customer_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_msg_thread_session ON messaging_threads (ai_session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_msg_thread_last_inbound ON messaging_threads (last_inbound_at)")

    # Idempotency. Meta redelivers a webhook until it receives a 200, so the
    # SAME customer message arrives repeatedly on any slow or failed response.
    # The unique constraint below is what stops one message being replayed into
    # the agent -- re-running its tool calls and potentially creating duplicate
    # booking drafts.
    op.execute("""
        CREATE TABLE IF NOT EXISTS messaging_inbound_messages (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            channel              VARCHAR(20)  NOT NULL,
            provider_message_id  VARCHAR(200) NOT NULL,
            thread_id            UUID,
            from_id              VARCHAR(120),
            message_type         VARCHAR(40),
            body                 TEXT,
            status               VARCHAR(20) NOT NULL DEFAULT 'received',
            failure_reason       TEXT,
            raw_payload          JSONB,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at           TIMESTAMPTZ,
            CONSTRAINT uq_msg_inbound_provider_id UNIQUE (channel, provider_message_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_msg_inbound_thread ON messaging_inbound_messages (thread_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_msg_inbound_created ON messaging_inbound_messages (created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS messaging_inbound_messages")
    op.execute("DROP TABLE IF EXISTS messaging_threads")
