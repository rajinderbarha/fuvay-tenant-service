"""LEVEL-5 REMEDIATION (2026-08-01, Phase 9) -- Chatbot session language.
Language selection belongs only inside the chatbot, never app-wide (per
project direction). Adds a validated language code to
AIConversationSession, reusing the existing app.engines.profile.schemas
ALLOWED_LANGUAGES set rather than inventing a new smaller list.

Revision ID: 221
Revises: 220
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "221"
down_revision = "220"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_conversation_sessions",
        sa.Column("language", sa.String(10), nullable=False, server_default=sa.text("'en'")),
    )


def downgrade() -> None:
    op.drop_column("ai_conversation_sessions", "language")
