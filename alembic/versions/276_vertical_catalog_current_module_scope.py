"""Repair vertical module lifecycle scope for current admin navigation.

Revision ID: 276
Revises: 275
"""
from alembic import op
import sqlalchemy as sa


revision = "276"
down_revision = "275"
branch_labels = None
depends_on = None


RETIRED = {
    "brands": "Consolidated into Types & Brands.",
    "brand_requests": "Consolidated into Types & Brands.",
    "service_options": "Configured per exact Job Type in Catalog Workspace.",
    "issue_types": "Configured per exact Job Type in Catalog Workspace.",
    "pricing_tiers": "Retired provider-set pricing model.",
    "location_mapping": "Replaced by tenant service-area approval.",
    "pricing_rules": "Retired provider-set pricing model.",
    "service_setup": "Removed from admin navigation by product decision.",
    "hs_overview": "Replaced by the Home Services dashboard and vertical capabilities page.",
    "hs_provider_matching": "Unlinked from the current Home Services module list until product scope is re-certified.",
    "hs_matching_diagnostics": "Unlinked from the current Home Services module list until product scope is re-certified.",
    "hs_completed_job_deduction": "Moved to Home Services Finance.",
    "hs_settings": "Moved to Business Verticals capabilities and policies.",
    "hs_bookability": "Consolidated into provider eligibility and matching operations.",
}

NOT_IMPLEMENTED = {
    "courses",
    "batches",
    "demo_classes",
    "counselors",
    "lead_forms",
    "fee_plans",
    "amenities",
    "localities",
    "menu_categories",
    "menu_items",
    "item_variants",
    "addons",
    "cuisine_types",
    "product_categories",
    "products",
    "product_variants",
    "attributes",
    "inventory_rules",
    "consultation_types",
    "document_requirements",
    "appointment_types",
    "subscription_plans",
    "property_types",
    "listing_types",
    "site_visit_workflows",
}

CURRENT_HOME_SERVICES = {
    "categories",
    "service_groups",
    "master_services",
    "types_brands",
    "checklist_templates",
    "hs_service_catalog",
}


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("""
        UPDATE catalog_module_definitions
           SET navigation_status = 'available',
               navigation_status_reason = NULL
         WHERE key = ANY(:keys)
    """), {"keys": sorted(CURRENT_HOME_SERVICES)})

    for key, reason in RETIRED.items():
        conn.execute(sa.text("""
            UPDATE catalog_module_definitions
               SET navigation_status = 'retired',
                   navigation_status_reason = :reason
             WHERE key = :key
        """), {"key": key, "reason": reason})

    conn.execute(sa.text("""
        UPDATE catalog_module_definitions
           SET navigation_status = 'not_implemented',
               navigation_status_reason = 'No production admin workspace is implemented for the current Home Services scope.'
         WHERE key = ANY(:keys)
    """), {"keys": sorted(NOT_IMPLEMENTED)})

    conn.execute(sa.text("""
        UPDATE vertical_catalog_modules
           SET is_enabled = false,
               is_required = false
         WHERE module_id IN (
             SELECT id
               FROM catalog_module_definitions
              WHERE navigation_status <> 'available'
         )
    """))

    conn.execute(sa.text("""
        UPDATE vertical_catalog_modules
           SET is_enabled = true
         WHERE vertical_id = (SELECT id FROM verticals WHERE key = 'home_services')
           AND module_id IN (
             SELECT id
               FROM catalog_module_definitions
              WHERE key = ANY(:keys)
           )
    """), {"keys": sorted(CURRENT_HOME_SERVICES)})


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE catalog_module_definitions
           SET navigation_status = 'available',
               navigation_status_reason = NULL
         WHERE key = ANY(:keys)
    """), {"keys": sorted(set(RETIRED) | NOT_IMPLEMENTED | CURRENT_HOME_SERVICES)})
