"""Add rolling-window provider health and reschedule grace scoring.

Revision ID: 386
Revises: 385
"""
from alembic import op


revision = "386"
down_revision = "385"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Only the platform default formula is revised. Any separately authored
    # admin formula remains untouched. The default still totals exactly 100%.
    op.execute("""
        UPDATE health_formula_components AS component
           SET weight_percent = CASE component.metric_key
               WHEN 'job_completion_rate' THEN 20.00
               WHEN 'cancellation_rate' THEN 15.00
               ELSE component.weight_percent
           END,
               updated_at = now()
          FROM health_formulas AS formula
         WHERE component.formula_id = formula.id
           AND formula.formula_key = 'provider_business_health_default'
           AND component.metric_key IN ('job_completion_rate', 'cancellation_rate')
    """)
    op.execute("""
        INSERT INTO health_formula_components (
            id, formula_id, metric_key, weight_percent, direction,
            min_value, max_value, normalization_method, is_required,
            created_at, updated_at
        )
        SELECT gen_random_uuid(), formula.id, 'provider_reschedule_score',
               10.00, 'positive', 0, 100, 'linear', false, now(), now()
          FROM health_formulas AS formula
         WHERE formula.formula_key = 'provider_business_health_default'
           AND NOT EXISTS (
               SELECT 1 FROM health_formula_components AS component
                WHERE component.formula_id = formula.id
                  AND component.metric_key = 'provider_reschedule_score'
           )
    """)
    # Raw one-review thresholds bypass confidence smoothing. Point penalties
    # and bonuses at the smoothed 0-100 rating signal instead.
    op.execute("""
        UPDATE health_penalty_rules AS rule
           SET metric_key = 'rating_score', value_json = '70'::jsonb,
               updated_at = now()
          FROM health_formulas AS formula
         WHERE rule.formula_id = formula.id
           AND formula.formula_key = 'provider_business_health_default'
           AND rule.metric_key = 'average_rating'
           AND rule.operator = 'less_than'
    """)
    op.execute("""
        UPDATE health_penalty_rules AS rule
           SET value_json = '25'::jsonb, updated_at = now()
          FROM health_formulas AS formula
         WHERE rule.formula_id = formula.id
           AND formula.formula_key = 'provider_business_health_default'
           AND rule.metric_key = 'complaint_rate'
           AND rule.operator = 'greater_than'
           AND rule.value_json = '10'::jsonb
    """)
    op.execute("""
        UPDATE health_bonus_rules AS rule
           SET metric_key = 'rating_score', value_json = '94'::jsonb,
               updated_at = now()
          FROM health_formulas AS formula
         WHERE rule.formula_id = formula.id
           AND formula.formula_key = 'provider_business_health_default'
           AND rule.metric_key = 'average_rating'
           AND rule.operator = 'greater_than_or_equal'
    """)
    op.execute("""
        UPDATE health_formulas
           SET version = version + 1, updated_at = now()
         WHERE formula_key = 'provider_business_health_default'
    """)
    # Old scores were computed from lifetime evidence and the old formula.
    # Removing only this formula's projection forces the worker/runtime to
    # publish a fresh, explainable six-month score instead of serving stale.
    op.execute("""
        DELETE FROM health_scores
         WHERE formula_id IN (
             SELECT id FROM health_formulas
              WHERE formula_key = 'provider_business_health_default'
         )
    """)
    # Do not wait up to the normal six-hour refresh interval after removing the
    # lifetime projections.  The background worker claims this durable job and
    # publishes rolling scores; the NOT EXISTS guard respects a sweep already
    # queued or in progress during deployment.
    op.execute("""
        INSERT INTO trust_quality_recalculation_jobs (
            id, job_type, scope_type, scope_id, status,
            total_count, processed_count, failed_count,
            triggered_by, created_at, updated_at
        )
        SELECT gen_random_uuid(), 'health', 'all', NULL, 'queued',
               0, 0, 0, 'migration_386', now(), now()
         WHERE NOT EXISTS (
             SELECT 1 FROM trust_quality_recalculation_jobs
              WHERE status IN ('queued', 'running', 'cancelling')
         )
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM health_formula_components AS component
         USING health_formulas AS formula
         WHERE component.formula_id = formula.id
           AND formula.formula_key = 'provider_business_health_default'
           AND component.metric_key = 'provider_reschedule_score'
    """)
    op.execute("""
        UPDATE health_formula_components AS component
           SET weight_percent = CASE component.metric_key
               WHEN 'job_completion_rate' THEN 25.00
               WHEN 'cancellation_rate' THEN 20.00
               ELSE component.weight_percent
           END,
               updated_at = now()
          FROM health_formulas AS formula
         WHERE component.formula_id = formula.id
           AND formula.formula_key = 'provider_business_health_default'
           AND component.metric_key IN ('job_completion_rate', 'cancellation_rate')
    """)
    op.execute("""
        UPDATE health_penalty_rules AS rule
           SET metric_key = 'average_rating', value_json = '3.5'::jsonb,
               updated_at = now()
          FROM health_formulas AS formula
         WHERE rule.formula_id = formula.id
           AND formula.formula_key = 'provider_business_health_default'
           AND rule.metric_key = 'rating_score'
           AND rule.operator = 'less_than'
           AND rule.value_json = '70'::jsonb
    """)
    op.execute("""
        UPDATE health_penalty_rules AS rule
           SET value_json = '10'::jsonb, updated_at = now()
          FROM health_formulas AS formula
         WHERE rule.formula_id = formula.id
           AND formula.formula_key = 'provider_business_health_default'
           AND rule.metric_key = 'complaint_rate'
           AND rule.operator = 'greater_than'
           AND rule.value_json = '25'::jsonb
    """)
    op.execute("""
        UPDATE health_bonus_rules AS rule
           SET metric_key = 'average_rating', value_json = '4.7'::jsonb,
               updated_at = now()
          FROM health_formulas AS formula
         WHERE rule.formula_id = formula.id
           AND formula.formula_key = 'provider_business_health_default'
           AND rule.metric_key = 'rating_score'
           AND rule.operator = 'greater_than_or_equal'
           AND rule.value_json = '94'::jsonb
    """)
    op.execute("""
        DELETE FROM health_scores
         WHERE formula_id IN (
             SELECT id FROM health_formulas
              WHERE formula_key = 'provider_business_health_default'
         )
    """)
