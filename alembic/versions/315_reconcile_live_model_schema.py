"""Reconcile timestamp and metadata columns used by live ORM models.

Revision ID: 315
Revises: 314

Several append-only/event tables predate the shared ``ServiceOSBase`` model.
They were later moved onto that base without a matching database migration,
which made ordinary ORM inserts fail when SQLAlchemy included ``updated_at``.
This migration adds only columns used by active models.  It deliberately does
not recreate retired package, geography, quote, or legacy checklist tables.
"""

from alembic import op


revision = "315"
down_revision = "314"
branch_labels = None
depends_on = None


_UPDATED_AT_TABLES = (
    "admin_bulk_setup_run_items",
    "ai_action_logs",
    "ai_usage_logs",
    "coaching_appointment_draft_events",
    "coaching_appointment_execution_events",
    "rag_kb_versions",
    "rag_query_logs",
    "rag_retrieval_feedback",
    "real_estate_lead_execution_events",
    "service_setup_bulk_preview_items",
    "service_setup_template_run_items",
    "service_setup_template_runs",
)


def upgrade() -> None:
    for table_name in _UPDATED_AT_TABLES:
        op.execute(
            f"ALTER TABLE {table_name} "
            "ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now()"
        )

    op.execute(
        "ALTER TABLE api_keys "
        "ADD COLUMN IF NOT EXISTS meta JSONB NOT NULL DEFAULT '{}'::jsonb"
    )
    op.execute(
        "ALTER TABLE vertical_menu_config "
        "ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now()"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE vertical_menu_config DROP COLUMN IF EXISTS created_at")
    op.execute("ALTER TABLE api_keys DROP COLUMN IF EXISTS meta")
    for table_name in reversed(_UPDATED_AT_TABLES):
        op.execute(
            f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS updated_at"
        )
