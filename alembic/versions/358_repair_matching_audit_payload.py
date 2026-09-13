"""Repair matching audit payload columns on drifted databases.

Revision ID: 358
Revises: 357

Some long-lived installations have ``master_data_audit_log`` but are missing
the JSON payload columns originally created by migration 055. Provider
fair-share matching reads ``new_value`` and therefore loses its recent
allocation history on those installations. Keep this repair idempotent so it
is harmless on databases whose schema is already correct.
"""
from alembic import op


revision = "358"
down_revision = "357"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE master_data_audit_log "
        "ADD COLUMN IF NOT EXISTS old_value JSONB"
    )
    op.execute(
        "ALTER TABLE master_data_audit_log "
        "ADD COLUMN IF NOT EXISTS new_value JSONB"
    )
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_mdal_matching_provider_created
            ON master_data_audit_log
            ((new_value->>'master_service_id'),
             (new_value->>'zipcode'),
             (new_value->>'selected_provider_id'), created_at DESC)
         WHERE entity_type = 'matching_decision'
           AND action = 'production_match'
    """)


def downgrade() -> None:
    # Repair migrations do not remove shared audit columns on downgrade: they
    # may have existed since migration 055 and contain unrelated audit data.
    pass
