"""Persist WhatsApp and Instagram delivery/read webhook callbacks.

Revision ID: 342
Revises: 341
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision = "342"
down_revision = "341"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "messaging_delivery_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("provider_message_id", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("recipient_id", sa.String(120), nullable=True),
        sa.Column("business_id", sa.String(120), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=text("now()")),
        sa.UniqueConstraint("channel", "provider_message_id", "status", "occurred_at", name="uq_msg_delivery_event"),
    )
    op.create_index("ix_msg_delivery_provider_id", "messaging_delivery_events", ["provider_message_id"])
    op.create_index("ix_msg_delivery_created", "messaging_delivery_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("messaging_delivery_events")
