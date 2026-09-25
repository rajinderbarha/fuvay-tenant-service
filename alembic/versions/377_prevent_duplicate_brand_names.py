"""Merge the duplicate lowercase LG record and enforce unique live brand names.

Revision ID: 377
Revises: 376
"""
from alembic import op
import sqlalchemy as sa


revision = "377"
down_revision = "376"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Preserve every reference before retiring the lowercase duplicate. The
    # intended canonical record is the explicitly-cased "LG" row. Statements
    # are idempotent so partially repaired installations are safe to migrate.
    conn.execute(sa.text("""
        DO $$
        DECLARE
            v_target_brand_id uuid;
            v_source_brand_id uuid;
        BEGIN
            SELECT id INTO v_target_brand_id
            FROM brands
            WHERE deleted_at IS NULL AND name = 'LG'
            ORDER BY created_at DESC
            LIMIT 1;

            IF v_target_brand_id IS NULL THEN
                RETURN;
            END IF;

            FOR v_source_brand_id IN
                SELECT id FROM brands
                WHERE deleted_at IS NULL
                  AND id <> v_target_brand_id
                  AND lower(btrim(name)) = 'lg'
            LOOP
                DELETE FROM master_service_brands source
                USING master_service_brands target
                WHERE source.brand_id = v_source_brand_id AND target.brand_id = v_target_brand_id
                  AND source.master_service_id = target.master_service_id;
                UPDATE master_service_brands SET brand_id = v_target_brand_id WHERE brand_id = v_source_brand_id;

                DELETE FROM brand_category_mappings source
                USING brand_category_mappings target
                WHERE source.brand_id = v_source_brand_id AND target.brand_id = v_target_brand_id
                  AND source.category_id = target.category_id;
                UPDATE brand_category_mappings SET brand_id = v_target_brand_id WHERE brand_id = v_source_brand_id;

                DELETE FROM brand_service_option_mappings source
                USING brand_service_option_mappings target
                WHERE source.brand_id = v_source_brand_id AND target.brand_id = v_target_brand_id
                  AND source.service_option_id = target.service_option_id;
                UPDATE brand_service_option_mappings SET brand_id = v_target_brand_id WHERE brand_id = v_source_brand_id;

                DELETE FROM tenant_supported_brands source
                USING tenant_supported_brands target
                WHERE source.brand_id = v_source_brand_id AND target.brand_id = v_target_brand_id
                  AND source.tenant_id = target.tenant_id
                  AND source.master_service_id = target.master_service_id;
                UPDATE tenant_supported_brands SET brand_id = v_target_brand_id WHERE brand_id = v_source_brand_id;

                DELETE FROM brand_template_items source
                USING brand_template_items target
                WHERE source.brand_id = v_source_brand_id AND target.brand_id = v_target_brand_id
                  AND source.brand_template_id = target.brand_template_id;
                UPDATE brand_template_items SET brand_id = v_target_brand_id WHERE brand_id = v_source_brand_id;

                DELETE FROM tenant_service_brands source
                USING tenant_service_brands target
                WHERE source.brand_id = v_source_brand_id AND target.brand_id = v_target_brand_id
                  AND source.tenant_service_id = target.tenant_service_id
                  AND source.service_type_id IS NOT DISTINCT FROM target.service_type_id;
                UPDATE tenant_service_brands SET brand_id = v_target_brand_id WHERE brand_id = v_source_brand_id;

                DELETE FROM brand_mappings source
                USING brand_mappings target
                WHERE source.brand_id = v_source_brand_id AND target.brand_id = v_target_brand_id
                  AND source.category_id IS NOT DISTINCT FROM target.category_id
                  AND source.service_group_id IS NOT DISTINCT FROM target.service_group_id
                  AND source.service_id IS NOT DISTINCT FROM target.service_id;
                UPDATE brand_mappings SET brand_id = v_target_brand_id WHERE brand_id = v_source_brand_id;

                UPDATE brand_requests SET matched_brand_id = v_target_brand_id WHERE matched_brand_id = v_source_brand_id;
                UPDATE service_pricing_rules SET brand_id = v_target_brand_id WHERE brand_id = v_source_brand_id;
                UPDATE workflow_service_mappings SET brand_id = v_target_brand_id WHERE brand_id = v_source_brand_id;
                UPDATE customer_booking_drafts SET brand_id = v_target_brand_id WHERE brand_id = v_source_brand_id;
                UPDATE home_service_booking_drafts SET brand_id = v_target_brand_id WHERE brand_id = v_source_brand_id;
                UPDATE tenant_service_area_services SET brand_id = v_target_brand_id WHERE brand_id = v_source_brand_id;
                UPDATE usage_credit_ledger SET brand_id = v_target_brand_id WHERE brand_id = v_source_brand_id;

                UPDATE brands
                SET status = 'archived', is_active = false, deleted_at = now(),
                    replacement_brand_id = v_target_brand_id, updated_at = now()
                WHERE id = v_source_brand_id;
            END LOOP;
        END $$;
    """))

    # Older rows predate normalized_name. The API performs richer
    # punctuation normalization; this backfill guarantees at least trimmed,
    # case-insensitive identity for every existing brand.
    conn.execute(sa.text("""
        UPDATE brands
        SET normalized_name = lower(regexp_replace(btrim(name), '\\s+', ' ', 'g'))
        WHERE normalized_name IS NULL OR btrim(normalized_name) = ''
    """))
    op.create_index(
        "uq_brands_live_normalized_name",
        "brands",
        ["normalized_name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND normalized_name IS NOT NULL"),
    )


def downgrade() -> None:
    # The merged row remains retired intentionally; recreating a duplicate is
    # not a safe or useful rollback. Only remove the enforcement index.
    op.drop_index("uq_brands_live_normalized_name", table_name="brands")
