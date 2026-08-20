"""Align default health formulas with metrics sourced from live tables.

Revision ID: 279
Revises: 278
"""
from alembic import op


revision = "279"
down_revision = "278"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Home Services uses a top-up usage-credit wallet, not legacy packages.
    conn.exec_driver_sql("""
        UPDATE health_formula_components c
           SET metric_key = 'usage_credit_score', updated_at = NOW()
          FROM health_formulas f
         WHERE c.formula_id = f.id
           AND f.formula_key = 'provider_business_health_default'
           AND c.metric_key = 'package_credit_score'
    """)
    conn.exec_driver_sql("""
        UPDATE health_penalty_rules p
           SET metric_key = 'usage_credit_depleted', updated_at = NOW()
          FROM health_formulas f
         WHERE p.formula_id = f.id
           AND f.formula_key = 'provider_business_health_default'
           AND p.metric_key = 'package_expired'
    """)

    # Replace speculative technician metrics with values gathered from jobs,
    # reviews, complaints and staff verification.
    conn.exec_driver_sql("""
        DELETE FROM health_formula_components c
         USING health_formulas f
         WHERE c.formula_id = f.id
           AND f.formula_key = 'technician_performance_health_default'
    """)
    conn.exec_driver_sql("""
        INSERT INTO health_formula_components (
            id, formula_id, metric_key, weight_percent, direction,
            min_value, max_value, normalization_method, is_required,
            created_at, updated_at
        )
        SELECT gen_random_uuid(), f.id, spec.metric_key, spec.weight, spec.direction,
               0, 100, 'linear', false, NOW(), NOW()
          FROM health_formulas f
          CROSS JOIN (VALUES
              ('job_completion_rate', 30.00, 'positive'),
              ('rating_score', 25.00, 'positive'),
              ('on_time_arrival_rate', 20.00, 'positive'),
              ('complaint_dispute_score', 15.00, 'negative'),
              ('document_verification_score', 10.00, 'positive')
          ) AS spec(metric_key, weight, direction)
         WHERE f.formula_key = 'technician_performance_health_default'
    """)


def downgrade() -> None:
    # Restoring speculative/legacy metric keys would reintroduce formulas that
    # cannot be evaluated from operational data, so this data repair is final.
    pass

