"""LEVEL-5 REMEDIATION (2026-08-01, Phase 3) -- Deterministic Question Flow.
Adds per-question answer storage + an optimistic-concurrency version counter
to HomeServiceBookingDraft, so the new unified structured-question envelope
can bind admin_catalog's CatalogQuestion resolver to the canonical booking
draft deterministically (backend selects every question and allowed
answer; DeepSeek only phrases/interprets).

Revision ID: 220
Revises: 219
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "220"
down_revision = "219"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "home_service_booking_drafts",
        sa.Column("catalog_question_answers", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "home_service_booking_drafts",
        sa.Column("question_flow_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )


def downgrade() -> None:
    op.drop_column("home_service_booking_drafts", "question_flow_version")
    op.drop_column("home_service_booking_drafts", "catalog_question_answers")
