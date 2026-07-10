"""Vertical Catalog Module Fix — vertical-specific catalog modules + engine mappings.

Migration 089 seeded coaching/real_estate/beauty/restaurant/product_marketplace/
professional_services with Home-Services-flavored modules (brands, issue_types,
service_options, types_brands, brand_requests) — exactly the bug this P0 fixes.
This migration adds real vertical-specific module definitions and re-assigns each
non-home_services vertical to its correct modules. home_services is untouched.

Also creates vertical_engine_mappings (requested by the ticket, previously absent).

Revision ID: 090
Revises: 089
"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import text

revision = "090"
down_revision = "089"
branch_labels = None
depends_on = None


NEW_MODULES = [
    # key, label, icon, admin_path, module_group, sort
    # Coaching / Education
    ("courses",        "Courses",         "BookOpen",      "coaching",   1),
    ("batches",        "Batches",         "Users",         "coaching",   2),
    ("demo_classes",   "Demo Classes",    "PlayCircle",    "coaching",   3),
    ("counselors",     "Counselors",      "UserCheck",     "coaching",   4),
    ("lead_forms",     "Lead Forms",      "FileText",      "coaching",   5),
    ("fee_plans",      "Fee Plans",       "Banknote",      "coaching",   6),
    # Real Estate
    ("property_types",       "Property Types",       "Home",       "real_estate", 1),
    ("listing_types",        "Listing Types",         "Tag",        "real_estate", 2),
    ("amenities",             "Amenities",             "Sparkles",   "real_estate", 3),
    ("localities",            "Localities",            "MapPin",     "real_estate", 4),
    ("site_visit_workflows", "Site Visit Workflows",  "CalendarCheck","real_estate", 5),
    # Restaurant / Food
    ("menu_categories", "Menu Categories", "LayoutGrid",  "restaurant", 1),
    ("menu_items",      "Menu Items",      "UtensilsCrossed","restaurant", 2),
    ("item_variants",   "Variants",        "Layers",      "restaurant", 3),
    ("addons",          "Add-ons",         "PlusCircle",  "restaurant", 4),
    ("cuisine_types",   "Cuisine Types",   "Tag",         "restaurant", 5),
    # Product Marketplace
    ("product_categories", "Product Categories", "Layers",      "product_marketplace", 1),
    ("products",            "Products",            "ShoppingBag", "product_marketplace", 2),
    ("product_variants",    "Variants",            "Package",     "product_marketplace", 3),
    ("attributes",           "Attributes",          "Settings2",   "product_marketplace", 4),
    ("inventory_rules",      "Inventory Rules",     "Boxes",       "product_marketplace", 5),
    # Professional Services
    ("consultation_types",    "Consultation Types",     "MessageSquare", "professional_services", 1),
    ("document_requirements", "Document Requirements",  "FileText",      "professional_services", 2),
    ("appointment_types",     "Appointment Types",      "Calendar",      "professional_services", 3),
    ("subscription_plans",    "Subscription Plans",     "Repeat",        "professional_services", 4),
]

# vertical_key -> ordered list of module keys (universal ones + its own new modules)
NEW_ASSIGNMENTS = {
    "coaching": ["categories", "courses", "batches", "demo_classes", "counselors",
                 "lead_forms", "fee_plans", "pricing_tiers", "location_mapping"],
    "real_estate": ["categories", "property_types", "listing_types", "amenities",
                     "localities", "site_visit_workflows", "pricing_tiers", "location_mapping"],
    "beauty": ["categories", "service_groups", "master_services", "service_options",
               "pricing_tiers", "location_mapping"],
    "restaurant": ["categories", "menu_categories", "menu_items", "item_variants",
                   "addons", "cuisine_types", "pricing_tiers", "location_mapping"],
    "product_marketplace": ["categories", "product_categories", "products",
                             "product_variants", "attributes", "inventory_rules",
                             "pricing_tiers", "location_mapping"],
    "professional_services": ["categories", "consultation_types", "document_requirements",
                               "appointment_types", "subscription_plans",
                               "pricing_tiers", "location_mapping"],
}
REQUIRED_MODULES = {
    "coaching": ["categories", "courses"],
    "real_estate": ["categories", "property_types"],
    "beauty": ["categories", "master_services"],
    "restaurant": ["categories", "menu_categories"],
    "product_marketplace": ["categories", "products"],
    "professional_services": ["categories", "consultation_types"],
}


def upgrade() -> None:
    conn = op.get_bind()

    def _table_exists(t: str) -> bool:
        r = conn.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name=:t"), {"t": t})
        return bool(r.fetchone())

    def _module_exists(key: str) -> bool:
        r = conn.execute(text(
            "SELECT 1 FROM catalog_module_definitions WHERE key=:k"), {"k": key})
        return bool(r.fetchone())

    # ── New module definitions (admin_path points at the shared placeholder
    #    page /admin/catalog-module/{key} — dedicated CRUD engines are a
    #    separate, larger scope than this menu-architecture fix) ────────────
    module_ids: dict[str, str] = {}
    for key, label, icon, group, sort in NEW_MODULES:
        if _module_exists(key):
            row = conn.execute(text(
                "SELECT id FROM catalog_module_definitions WHERE key=:k"), {"k": key}).fetchone()
            module_ids[key] = str(row[0])
            continue
        mid = str(uuid.uuid4())
        module_ids[key] = mid
        conn.execute(text("""
            INSERT INTO catalog_module_definitions
                (id, key, label, icon, admin_path, module_group, is_universal, sort_order)
            VALUES (:id, :key, :label, :icon, :path, :group, false, :sort)
        """), {"id": mid, "key": key, "label": label, "icon": icon,
               "path": f"/admin/catalog-module/{key}", "group": group, "sort": sort})

    # Load existing universal/home-services module ids we reuse (categories,
    # pricing_tiers, location_mapping, service_groups, master_services, service_options)
    existing = conn.execute(text(
        "SELECT key, id FROM catalog_module_definitions")).fetchall()
    all_module_ids = {row[0]: str(row[1]) for row in existing}
    all_module_ids.update(module_ids)

    verticals = conn.execute(text("SELECT key, id FROM verticals")).fetchall()
    vertical_ids = {row[0]: str(row[1]) for row in verticals}

    # ── Re-assign non-home_services verticals to their correct modules ──────
    for vkey, mod_keys in NEW_ASSIGNMENTS.items():
        vid = vertical_ids.get(vkey)
        if not vid:
            continue
        # Remove the old (incorrect, Home-Services-flavored) assignments for this vertical
        conn.execute(text(
            "DELETE FROM vertical_catalog_modules WHERE vertical_id = :vid"), {"vid": vid})
        required = REQUIRED_MODULES.get(vkey, [])
        for i, mkey in enumerate(mod_keys):
            mid = all_module_ids.get(mkey)
            if not mid:
                continue
            conn.execute(text("""
                INSERT INTO vertical_catalog_modules (id, vertical_id, module_id, is_enabled, is_required, sort_order)
                VALUES (:id, :vid, :mid, true, :req, :sort)
            """), {"id": str(uuid.uuid4()), "vid": vid, "mid": mid,
                   "req": mkey in required, "sort": i})

    # ── vertical_engine_mappings ─────────────────────────────────────────────
    if not _table_exists("vertical_engine_mappings"):
        op.create_table(
            "vertical_engine_mappings",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("vertical_id", UUID(as_uuid=True), sa.ForeignKey("verticals.id", ondelete="CASCADE"), nullable=False),
            sa.Column("engine_key", sa.String(80), nullable=False),
            sa.Column("is_required", sa.Boolean, server_default="false", nullable=False),
            sa.Column("sort_order", sa.Integer, server_default="0", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("vertical_id", "engine_key", name="uq_vem_vertical_engine"),
        )
        op.create_index("ix_vem_vertical_id", "vertical_engine_mappings", ["vertical_id"])


def downgrade() -> None:
    op.drop_table("vertical_engine_mappings")
    new_keys = [m[0] for m in NEW_MODULES]
    conn = op.get_bind()
    conn.execute(text(
        "DELETE FROM vertical_catalog_modules WHERE module_id IN "
        "(SELECT id FROM catalog_module_definitions WHERE key = ANY(:keys))"
    ), {"keys": new_keys})
    conn.execute(text(
        "DELETE FROM catalog_module_definitions WHERE key = ANY(:keys)"), {"keys": new_keys})
