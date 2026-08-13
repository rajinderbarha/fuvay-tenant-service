"""Make vertical module lifecycle explicit and hide unusable admin routes.

Revision ID: 253
Revises: 252
"""
from alembic import op
import sqlalchemy as sa


revision = "253"
down_revision = "252"
branch_labels = None
depends_on = None


RETIRED = {
    "brands": "Consolidated into Types & Brands.",
    "brand_requests": "Consolidated into Types & Brands.",
    "service_options": "Configured per Job Type in Catalog Workspace.",
    "issue_types": "Configured per Job Type in Catalog Workspace.",
    "pricing_tiers": "Retired provider-set pricing model.",
    "location_mapping": "Replaced by tenant service-area approval.",
    "pricing_rules": "Retired provider-set pricing model.",
    "service_setup": "Removed from admin navigation by product decision.",
    "hs_overview": "Removed; the Home Services dashboard is canonical.",
    "hs_provider_matching": "Consolidated into the canonical Provider Matching surface.",
    "hs_matching_diagnostics": "Consolidated into Provider Matching diagnostics.",
    "hs_completed_job_deduction": "Moved to Home Services Finance.",
    "hs_settings": "Moved to Business Verticals capabilities and policies.",
    "hs_bookability": "Consolidated into Provider Matching eligibility.",
}

NOT_IMPLEMENTED = {
    "courses", "batches", "demo_classes", "counselors", "lead_forms", "fee_plans",
    "amenities", "localities", "menu_categories", "menu_items", "item_variants",
    "addons", "cuisine_types", "product_categories", "products", "product_variants",
    "attributes", "inventory_rules", "consultation_types", "document_requirements",
    "appointment_types", "subscription_plans",
}


def upgrade() -> None:
    op.add_column("catalog_module_definitions", sa.Column(
        "navigation_status", sa.String(length=24), nullable=False, server_default="available",
    ))
    op.add_column("catalog_module_definitions", sa.Column(
        "navigation_status_reason", sa.String(length=500), nullable=True,
    ))
    connection = op.get_bind()
    for key, reason in RETIRED.items():
        connection.execute(sa.text("""
            UPDATE catalog_module_definitions
               SET navigation_status = 'retired', navigation_status_reason = :reason
             WHERE key = :key
        """), {"key": key, "reason": reason})
    connection.execute(sa.text("""
        UPDATE catalog_module_definitions
           SET navigation_status = 'not_implemented',
               navigation_status_reason = 'Dedicated functional admin workspace has not been implemented.'
         WHERE key = ANY(:keys)
    """), {"keys": sorted(NOT_IMPLEMENTED)})
    connection.execute(sa.text("""
        UPDATE vertical_catalog_modules
           SET is_enabled = false, is_required = false
         WHERE module_id IN (
             SELECT id FROM catalog_module_definitions WHERE navigation_status <> 'available'
         )
    """))


def downgrade() -> None:
    op.drop_column("catalog_module_definitions", "navigation_status_reason")
    op.drop_column("catalog_module_definitions", "navigation_status")
