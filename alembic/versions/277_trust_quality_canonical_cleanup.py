"""Canonicalise Trust & Quality data and remove legacy/test-only rows.

Revision ID: 277
Revises: 276

The admin console previously exposed targets that had no operational source and
test-created rule/formula rows that could be mistaken for production policy.
Provider health is canonicalised to ``tenant`` because that is the target read
by provider matching and the command centre.
"""
from alembic import op


revision = "277"
down_revision = "276"
branch_labels = None
depends_on = None


FIXED_BADGE_KEYS = (
    "verified_provider", "fast_response", "low_complaint_provider", "top_rated_provider",
    "verified_staff", "punctual_staff", "customer_loved_staff", "safety_champion_staff",
    "verified_technician", "precision_technician", "top_technician", "elite_technician",
)


def upgrade() -> None:
    conn = op.get_bind()

    # Free-form badge identities are no longer a supported product concept.
    # Their assignments and rules cascade with the definitions.
    fixed_keys = ", ".join(f"'{key}'" for key in FIXED_BADGE_KEYS)
    conn.exec_driver_sql(
        f"DELETE FROM badge_definitions WHERE badge_key NOT IN ({fixed_keys})"
    )

    # Test suites created unique l5* formula keys in the shared development DB.
    # The other legacy targets duplicated customer health or had no metric source
    # and no downstream consumer. FK cascades remove their components and scores.
    conn.exec_driver_sql("""
        DELETE FROM health_formulas
         WHERE formula_key LIKE 'l5%'
            OR target_type IN (
                'tenant_staff', 'customer_account', 'service_quality', 'category_quality'
            )
    """)

    # Matching reads HealthScore(target_type='tenant'). Align the formula and
    # its existing score rows with that canonical contract.
    conn.exec_driver_sql("""
        UPDATE health_formulas
           SET target_type = 'tenant', updated_at = NOW()
         WHERE target_type = 'tenant_provider'
    """)
    conn.exec_driver_sql("""
        UPDATE health_scores hs
           SET target_type = 'tenant', updated_at = NOW()
          FROM health_formulas hf
         WHERE hs.formula_id = hf.id
           AND hf.target_type = 'tenant'
           AND hs.target_type = 'tenant_provider'
    """)

    # One active formula is authoritative for each target. Keep the most recent
    # and deactivate older peers before adding the database invariant.
    conn.exec_driver_sql("""
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY target_type
                       ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST, id
                   ) AS rn
              FROM health_formulas
             WHERE status = 'active' AND target_type IN ('tenant', 'technician')
        )
        UPDATE health_formulas hf
           SET status = 'inactive', updated_at = NOW()
          FROM ranked r
         WHERE hf.id = r.id AND r.rn > 1
    """)

    # The separate risk-score table had no active rule catalog and no consumer;
    # platform intelligence owns cross-entity risk. Remove misleading output.
    conn.exec_driver_sql("DELETE FROM risk_scores")
    conn.exec_driver_sql("DELETE FROM risk_rules")

    # Per-score and repeated seed events are telemetry, not human audit events.
    # Keeping them made the audit tab mostly machine noise and scales linearly
    # with every full-platform sweep.
    conn.exec_driver_sql("""
        DELETE FROM trust_quality_audit_logs
         WHERE action_type IN (
            'health_score.calculated', 'risk_score.calculated',
            'trust_quality.seed_defaults'
         )
    """)

    with op.get_context().autocommit_block():
        op.execute("""
            CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_hf_one_active_target
                ON health_formulas (target_type)
             WHERE status = 'active' AND target_type IN ('tenant', 'technician')
        """)


def downgrade() -> None:
    # Removed test/legacy rows cannot be reconstructed. The schema invariant can
    # be rolled back safely; restoring deleted data requires a database backup.
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS uq_hf_one_active_target")
