"""Publish customer ratings immediately without admin approval.

Revision ID: 360
Revises: 359
"""
from alembic import op


revision = "360"
down_revision = "359"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE review_policies "
        "ALTER COLUMN auto_approve_enabled SET DEFAULT true"
    )
    op.execute(
        "ALTER TABLE review_policies "
        "ALTER COLUMN require_admin_moderation SET DEFAULT false"
    )
    op.execute(
        "UPDATE review_policies SET auto_approve_enabled=true, "
        "require_admin_moderation=false, updated_at=NOW()"
    )

    # Existing ordinary pending reviews were waiting only because the old
    # default required approval.  Publish them and retain an audit event.
    op.execute("""
        WITH promoted AS (
            UPDATE customer_reviews
               SET status = 'approved',
                   visibility = 'public',
                   approved_at = COALESCE(approved_at, submitted_at, created_at, NOW()),
                   updated_at = NOW()
             WHERE status = 'pending'
         RETURNING id, tenant_id
        )
        INSERT INTO review_events (
            id, review_id, tenant_id, actor_type, actor_user_id, event_type,
            old_value, new_value, reason, request_id, created_at
        )
        SELECT gen_random_uuid(), id, tenant_id, 'system', NULL,
               'review_approved', jsonb_build_object('status', 'pending'),
               jsonb_build_object(
                   'status', 'approved', 'automatic', true
               ),
               'Customer reviews now publish automatically',
               'migration:360', NOW()
          FROM promoted
    """)

    # Provider profiles and matching read precomputed summaries. Rebuild them
    # in the same migration so promoted historical reviews appear at once.
    op.execute("""
        INSERT INTO tenant_rating_summaries (
            id, tenant_id, total_reviews, average_rating,
            provider_average_rating, communication_average_rating,
            punctuality_average_rating, quality_average_rating,
            value_average_rating, five_star_count, four_star_count,
            three_star_count, two_star_count, one_star_count,
            last_review_at, updated_at
        )
        SELECT gen_random_uuid(), tenant_id, COUNT(*),
               ROUND(AVG(overall_rating)::numeric, 2),
               COALESCE(ROUND(AVG(provider_rating)::numeric, 2), 0),
               COALESCE(ROUND(AVG(communication_rating)::numeric, 2), 0),
               COALESCE(ROUND(AVG(punctuality_rating)::numeric, 2), 0),
               COALESCE(ROUND(AVG(quality_rating)::numeric, 2), 0),
               COALESCE(ROUND(AVG(value_rating)::numeric, 2), 0),
               COUNT(*) FILTER (WHERE overall_rating = 5),
               COUNT(*) FILTER (WHERE overall_rating = 4),
               COUNT(*) FILTER (WHERE overall_rating = 3),
               COUNT(*) FILTER (WHERE overall_rating = 2),
               COUNT(*) FILTER (WHERE overall_rating = 1),
               MAX(approved_at), NOW()
          FROM customer_reviews
         WHERE status = 'approved'
         GROUP BY tenant_id
        ON CONFLICT (tenant_id) DO UPDATE SET
            total_reviews = EXCLUDED.total_reviews,
            average_rating = EXCLUDED.average_rating,
            provider_average_rating = EXCLUDED.provider_average_rating,
            communication_average_rating = EXCLUDED.communication_average_rating,
            punctuality_average_rating = EXCLUDED.punctuality_average_rating,
            quality_average_rating = EXCLUDED.quality_average_rating,
            value_average_rating = EXCLUDED.value_average_rating,
            five_star_count = EXCLUDED.five_star_count,
            four_star_count = EXCLUDED.four_star_count,
            three_star_count = EXCLUDED.three_star_count,
            two_star_count = EXCLUDED.two_star_count,
            one_star_count = EXCLUDED.one_star_count,
            last_review_at = EXCLUDED.last_review_at,
            updated_at = EXCLUDED.updated_at
    """)

    op.execute("""
        INSERT INTO staff_rating_summaries (
            id, tenant_id, staff_member_id, total_reviews, average_rating,
            communication_average_rating, punctuality_average_rating,
            quality_average_rating, last_review_at, updated_at
        )
        SELECT gen_random_uuid(), tenant_id, staff_member_id, COUNT(*),
               ROUND(AVG(COALESCE(staff_rating, overall_rating))::numeric, 2),
               COALESCE(ROUND(AVG(communication_rating)::numeric, 2), 0),
               COALESCE(ROUND(AVG(punctuality_rating)::numeric, 2), 0),
               COALESCE(ROUND(AVG(quality_rating)::numeric, 2), 0),
               MAX(approved_at), NOW()
          FROM customer_reviews
         WHERE status = 'approved' AND staff_member_id IS NOT NULL
         GROUP BY tenant_id, staff_member_id
        ON CONFLICT (tenant_id, staff_member_id) DO UPDATE SET
            total_reviews = EXCLUDED.total_reviews,
            average_rating = EXCLUDED.average_rating,
            communication_average_rating = EXCLUDED.communication_average_rating,
            punctuality_average_rating = EXCLUDED.punctuality_average_rating,
            quality_average_rating = EXCLUDED.quality_average_rating,
            last_review_at = EXCLUDED.last_review_at,
            updated_at = EXCLUDED.updated_at
    """)


def downgrade() -> None:
    # Published customer content is not made private again on rollback.
    op.execute(
        "ALTER TABLE review_policies "
        "ALTER COLUMN auto_approve_enabled SET DEFAULT false"
    )
    op.execute(
        "ALTER TABLE review_policies "
        "ALTER COLUMN require_admin_moderation SET DEFAULT true"
    )
