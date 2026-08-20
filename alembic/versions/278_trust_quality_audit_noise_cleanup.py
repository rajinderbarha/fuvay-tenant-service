"""Remove obsolete Trust & Quality console rows.

Revision ID: 278
Revises: 277

Only rows that cannot resolve to a live configuration/output record, read-only
simulation telemetry, and recalculation fixtures owned by deleted test users are
removed. Real policy changes and current assignments remain auditable.
"""
from alembic import op


revision = "278"
down_revision = "277"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Simulations are read-only previews and do not belong in the policy audit.
    conn.exec_driver_sql("""
        DELETE FROM trust_quality_audit_logs
         WHERE action_type IN ('badge_rule.simulated', 'health_formula.simulated')
    """)

    # Fixed badge definitions are now product-owned. Historical create/update
    # noise from the retired free-form editor has no actionable detail.
    conn.exec_driver_sql("""
        DELETE FROM trust_quality_audit_logs
         WHERE action_type IN ('badge_definition.created', 'badge_definition.updated')
    """)

    # Remove configuration events whose configuration row was removed by the
    # canonical cleanup. UUIDs remain in live audit entries when the entity still
    # exists, preserving useful policy history.
    conn.exec_driver_sql("""
        DELETE FROM trust_quality_audit_logs l
         WHERE l.action_type LIKE 'health_formula.%'
           AND NOT EXISTS (SELECT 1 FROM health_formulas f WHERE f.id = l.target_id)
    """)
    conn.exec_driver_sql("""
        DELETE FROM trust_quality_audit_logs l
         WHERE l.action_type LIKE 'badge_rule.%'
           AND NOT EXISTS (SELECT 1 FROM badge_rules r WHERE r.id = l.target_id)
    """)
    conn.exec_driver_sql("""
        DELETE FROM trust_quality_audit_logs l
         WHERE l.action_type LIKE 'badge_assignment.%'
           AND NULLIF(l.new_value_json->>'id', '') IS NOT NULL
           AND NOT EXISTS (
               SELECT 1 FROM badge_assignments a
                WHERE a.id = (l.new_value_json->>'id')::uuid
           )
    """)

    # Shared-development API tests create temporary admins, run completed
    # recalculations, then remove those users. Those orphaned jobs are not real
    # operational history and dominated the Job History table.
    conn.exec_driver_sql("""
        DELETE FROM trust_quality_recalculation_jobs j
         WHERE j.status IN ('completed', 'failed', 'cancelled', 'completed_with_errors')
           AND j.triggered_by_user_id IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM users u WHERE u.id = j.triggered_by_user_id)
    """)
    conn.exec_driver_sql("""
        DELETE FROM trust_quality_audit_logs l
         WHERE l.target_type = 'recalculation_job'
           AND l.target_id IS NOT NULL
           AND NOT EXISTS (
               SELECT 1 FROM trust_quality_recalculation_jobs j WHERE j.id = l.target_id
           )
    """)


def downgrade() -> None:
    # Audit/test noise cannot be reconstructed; the pre-migration database
    # backup is the recovery path if it is ever needed.
    pass

