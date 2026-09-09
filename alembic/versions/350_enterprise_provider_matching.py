"""Install enterprise provider matching quality defaults and fair-share index.

Revision ID: 350
Revises: 349
"""
from alembic import op


revision = "350"
down_revision = "349"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A provider without measured evidence is neutral, not perfect. The
    # canonical allocator does not read this legacy column, but integrations
    # that still display it must not advertise an unearned 100.
    op.alter_column("tenants", "health_score", server_default="65.0")

    # Rebuild only the product-owned default formula. Administrator-created
    # formulas remain untouched and retain their status. Old scores for this
    # formula are invalidated so matching uses its neutral prior until the
    # normal recalculation worker produces evidence under the new definition.
    op.execute("""
        INSERT INTO health_formulas
            (id, formula_key, name, target_type, scope_type, base_score,
             min_score, max_score, status, version, created_at, updated_at)
        SELECT gen_random_uuid(), 'provider_business_health_default',
               'Provider Business Health', 'tenant', 'global',
               100, 0, 100,
               CASE WHEN EXISTS (
                   SELECT 1 FROM health_formulas
                    WHERE target_type = 'tenant' AND status = 'active'
               ) THEN 'draft' ELSE 'active' END,
               1, now(), now()
         WHERE NOT EXISTS (
             SELECT 1 FROM health_formulas
              WHERE formula_key = 'provider_business_health_default'
         )
    """)
    # If the product default already existed but no tenant formula was active,
    # make it the working baseline. Never displace an administrator's active
    # formula merely because this release is deployed.
    op.execute("""
        UPDATE health_formulas f
           SET status = 'active', updated_at = now()
         WHERE f.formula_key = 'provider_business_health_default'
           AND NOT EXISTS (
               SELECT 1 FROM health_formulas other
                WHERE other.target_type = 'tenant'
                  AND other.status = 'active'
                  AND other.id <> f.id
           )
    """)
    op.execute("""
        DELETE FROM health_scores
         WHERE formula_id IN (
             SELECT id FROM health_formulas
              WHERE formula_key = 'provider_business_health_default'
         )
    """)
    op.execute("""
        DELETE FROM health_formula_components
         WHERE formula_id IN (
             SELECT id FROM health_formulas
              WHERE formula_key = 'provider_business_health_default'
         )
    """)
    op.execute("""
        DELETE FROM health_penalty_rules
         WHERE formula_id IN (
             SELECT id FROM health_formulas
              WHERE formula_key = 'provider_business_health_default'
         )
    """)
    op.execute("""
        DELETE FROM health_bonus_rules
         WHERE formula_id IN (
             SELECT id FROM health_formulas
              WHERE formula_key = 'provider_business_health_default'
         )
    """)
    op.execute("""
        DELETE FROM health_band_rules
         WHERE formula_id IN (
             SELECT id FROM health_formulas
              WHERE formula_key = 'provider_business_health_default'
         )
    """)
    op.execute("""
        UPDATE health_formulas
           SET name = 'Provider Business Health',
               base_score = 100, min_score = 0, max_score = 100,
               version = version + 1, updated_at = now()
         WHERE formula_key = 'provider_business_health_default'
    """)
    op.execute("""
        INSERT INTO health_formula_components
            (id, formula_id, metric_key, weight_percent, direction,
             min_value, max_value, normalization_method, is_required,
             created_at, updated_at)
        SELECT gen_random_uuid(), f.id, x.metric_key, x.weight, x.direction,
               0, 100, 'linear', false, now(), now()
          FROM health_formulas f
          CROSS JOIN (VALUES
              ('job_completion_rate', 25.00, 'positive'),
              ('rating_score', 20.00, 'positive'),
              ('complaint_dispute_score', 15.00, 'negative'),
              ('cancellation_rate', 20.00, 'negative'),
              ('response_sla_score', 10.00, 'positive'),
              ('document_verification_score', 10.00, 'positive')
          ) AS x(metric_key, weight, direction)
         WHERE f.formula_key = 'provider_business_health_default'
    """)
    op.execute("""
        INSERT INTO health_penalty_rules
            (id, formula_id, metric_key, operator, value_json,
             penalty_points, hard_override_score, created_at, updated_at)
        SELECT gen_random_uuid(), f.id, x.metric_key, x.operator,
               x.value_json, x.points, x.override_score, now(), now()
          FROM health_formulas f
          CROSS JOIN (VALUES
              ('tenant_status', 'equals', '"suspended"'::jsonb, 0.00, 0.00),
              ('complaint_rate', 'greater_than', '10'::jsonb, 20.00, NULL),
              ('average_rating', 'less_than', '3.5'::jsonb, 20.00, NULL)
          ) AS x(metric_key, operator, value_json, points, override_score)
         WHERE f.formula_key = 'provider_business_health_default'
    """)
    op.execute("""
        INSERT INTO health_bonus_rules
            (id, formula_id, metric_key, operator, value_json,
             bonus_points, created_at, updated_at)
        SELECT gen_random_uuid(), f.id, x.metric_key, x.operator,
               x.value_json, x.points, now(), now()
          FROM health_formulas f
          CROSS JOIN (VALUES
              ('average_rating', 'greater_than_or_equal', '4.7'::jsonb, 5.00),
              ('job_completion_rate', 'greater_than_or_equal', '95'::jsonb, 5.00)
          ) AS x(metric_key, operator, value_json, points)
         WHERE f.formula_key = 'provider_business_health_default'
    """)
    op.execute("""
        INSERT INTO health_band_rules
            (id, formula_id, band_key, band_name, min_score, max_score,
             bookable_allowed, recommended_action, created_at, updated_at)
        SELECT gen_random_uuid(), f.id, x.band_key, x.band_name,
               x.minimum, x.maximum, x.bookable, x.action, now(), now()
          FROM health_formulas f
          CROSS JOIN (VALUES
              ('platinum', 'Platinum', 90.00, 100.00, true, NULL),
              ('gold', 'Gold', 75.00, 89.99, true, NULL),
              ('silver', 'Silver', 60.00, 74.99, true, NULL),
              ('watchlist', 'Watchlist', 50.00, 59.99, true, 'Request improvement plan'),
              ('at_risk', 'At Risk', 20.00, 49.99, false, 'Put under review'),
              ('blocked', 'Blocked', 0.00, 19.99, false, 'Stop new bookings')
          ) AS x(band_key, band_name, minimum, maximum, bookable, action)
         WHERE f.formula_key = 'provider_business_health_default'
    """)

    # Scores were invalidated because their formula changed. Queue one normal
    # batched health sweep so the existing background worker replaces neutral
    # priors with evidence-based scores after deployment. Never duplicate an
    # administrator's queued/running sweep.
    op.execute("""
        INSERT INTO trust_quality_recalculation_jobs
            (id, job_type, scope_type, status, total_count, processed_count,
             failed_count, triggered_by, created_at, updated_at)
        SELECT gen_random_uuid(), 'health', 'all', 'queued', 0, 0, 0,
               'migration_350', now(), now()
         WHERE NOT EXISTS (
             SELECT 1 FROM trust_quality_recalculation_jobs
              WHERE status IN ('queued', 'running', 'cancelling')
         )
    """)

    # Provider allocation history is the fair-share ledger. This partial
    # expression index keeps the seven-day lookup cheap without adding a
    # second mutable counter that could drift from real decisions.
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
    op.execute("""
        DELETE FROM trust_quality_recalculation_jobs
         WHERE triggered_by = 'migration_350' AND status = 'queued'
    """)
    op.execute("DROP INDEX IF EXISTS ix_mdal_matching_provider_created")
    op.alter_column("tenants", "health_score", server_default="100.0")
    # Formula data is intentionally not reconstructed: administrators may
    # have edited it after this migration and downgrade must not erase that.
