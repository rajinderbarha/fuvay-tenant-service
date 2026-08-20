"""Intelligence command-center correctness and scale indexes.

Revision ID: 286
Revises: 285

The risk table represents the current score for an entity.  Earlier code
appended a new row on every run, which inflated dashboard totals and made the
directory slower over time.  Keep the newest score, enforce one current row,
and add the composite indexes used by the admin filters.
"""
from alembic import op

revision = "286"
down_revision = "285"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DELETE FROM intel_risk_scores older
        USING intel_risk_scores newer
        WHERE older.entity_type = newer.entity_type
          AND older.entity_id = newer.entity_id
          AND (older.computed_at, older.id) < (newer.computed_at, newer.id)
    """)

    with op.get_context().autocommit_block():
        op.execute(
            'CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS '
            '"uq_intel_risk_current_entity" '
            'ON intel_risk_scores (entity_type, entity_id)'
        )
        indexes = {
            "ix_intel_risk_level_score": "intel_risk_scores (risk_level, risk_score DESC)",
            "ix_intel_risk_computed": "intel_risk_scores (computed_at DESC)",
            "ix_intel_anomaly_status_detected": "intel_anomalies (status, detected_at DESC)",
            "ix_intel_anomaly_severity_detected": "intel_anomalies (severity, detected_at DESC)",
            "ix_intel_model_status_created": "intel_model_registry (status, created_at DESC)",
            "ix_intel_model_type_created": "intel_model_registry (model_type, created_at DESC)",
            "ix_intel_prediction_status_created": "intel_prediction_jobs (status, created_at DESC)",
            "ix_intel_prediction_type_created": "intel_prediction_jobs (job_type, created_at DESC)",
            "ix_ai_usage_created": "ai_usage_logs (created_at DESC)",
            "ix_ai_usage_status_created": "ai_usage_logs (status, created_at DESC)",
            "ix_ai_usage_feature_created": "ai_usage_logs (feature_key, created_at DESC)",
            "ix_analytics_events_engine_occurred": "analytics_events (engine_id, occurred_at DESC)",
            "ix_analytics_events_type_occurred": "analytics_events (event_type, occurred_at DESC)",
            "ix_platform_audit_engine_created": "platform_audit_logs (engine_id, created_at DESC)",
        }
        for name, definition in indexes.items():
            op.execute(f'CREATE INDEX CONCURRENTLY IF NOT EXISTS "{name}" ON {definition}')


def downgrade() -> None:
    names = [
        "ix_platform_audit_engine_created",
        "ix_analytics_events_type_occurred",
        "ix_analytics_events_engine_occurred",
        "ix_ai_usage_feature_created",
        "ix_ai_usage_status_created",
        "ix_ai_usage_created",
        "ix_intel_prediction_type_created",
        "ix_intel_prediction_status_created",
        "ix_intel_model_type_created",
        "ix_intel_model_status_created",
        "ix_intel_anomaly_severity_detected",
        "ix_intel_anomaly_status_detected",
        "ix_intel_risk_computed",
        "ix_intel_risk_level_score",
        "uq_intel_risk_current_entity",
    ]
    with op.get_context().autocommit_block():
        for name in names:
            op.execute(f'DROP INDEX CONCURRENTLY IF EXISTS "{name}"')
