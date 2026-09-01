"""Scope messaging threads to the configured Meta business identity.

Revision ID: 326
Revises: 325
"""
from alembic import op


revision = "326"
down_revision = "325"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The same Instagram-scoped sender or WhatsApp phone can contact more than
    # one configured business. A channel+sender-only key mixed those tenants'
    # conversations. Legacy nulls get a stable sentinel before the new key.
    op.execute("UPDATE messaging_threads SET channel_business_id = 'legacy' WHERE channel_business_id IS NULL")
    op.execute("ALTER TABLE messaging_threads ALTER COLUMN channel_business_id SET NOT NULL")
    op.execute("ALTER TABLE messaging_threads DROP CONSTRAINT IF EXISTS uq_msg_thread_channel_user")
    op.execute("""
        DO $$ BEGIN
          ALTER TABLE messaging_threads
          ADD CONSTRAINT uq_msg_thread_business_user
          UNIQUE (channel, channel_business_id, channel_user_id);
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE messaging_threads DROP CONSTRAINT IF EXISTS uq_msg_thread_business_user")
    op.execute("ALTER TABLE messaging_threads ALTER COLUMN channel_business_id DROP NOT NULL")
    op.execute("""
        DO $$ BEGIN
          ALTER TABLE messaging_threads
          ADD CONSTRAINT uq_msg_thread_channel_user UNIQUE (channel, channel_user_id);
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)
