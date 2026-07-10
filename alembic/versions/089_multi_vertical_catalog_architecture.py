"""Multi-Vertical Catalog Architecture.

- verticals: platform-defined verticals (home_services, coaching, real_estate …)
- catalog_module_definitions: master list of catalog modules (categories, brands, issue_types …)
- vertical_catalog_modules: which modules are enabled per vertical
- vertical_menu_config: per-vertical sidebar menu ordering + labels

Revision ID: 089
Revises: 088
"""
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "089"
down_revision = "088"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── verticals ───────────────────────────────────────────────────────────────
    op.create_table(
        "verticals",
        sa.Column("id",           UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("key",          sa.String(80),  nullable=False, unique=True),
        sa.Column("label",        sa.String(120), nullable=False),
        sa.Column("description",  sa.Text,        nullable=True),
        sa.Column("icon",         sa.String(60),  nullable=True),
        sa.Column("color",        sa.String(20),  nullable=True),
        sa.Column("is_enabled",   sa.Boolean,     nullable=False, server_default="true"),
        sa.Column("is_beta",      sa.Boolean,     nullable=False, server_default="false"),
        sa.Column("sort_order",   sa.Integer,     nullable=False, server_default="0"),
        sa.Column("finance_model",sa.String(40),  nullable=True),   # subscription|commission|hybrid
        sa.Column("meta",         JSONB,          nullable=True),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at",   sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_verticals_key",        "verticals", ["key"])
    op.create_index("ix_verticals_is_enabled", "verticals", ["is_enabled"])

    # ── catalog_module_definitions ───────────────────────────────────────────────
    op.create_table(
        "catalog_module_definitions",
        sa.Column("id",          UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("key",         sa.String(80),  nullable=False, unique=True),
        sa.Column("label",       sa.String(120), nullable=False),
        sa.Column("description", sa.Text,        nullable=True),
        sa.Column("icon",        sa.String(60),  nullable=True),
        sa.Column("admin_path",  sa.String(200), nullable=True),    # /admin/brands
        sa.Column("module_group",sa.String(60),  nullable=True),    # services|qualifiers|pricing|compliance
        sa.Column("is_universal",sa.Boolean,     nullable=False, server_default="false"),
        sa.Column("sort_order",  sa.Integer,     nullable=False, server_default="0"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_cmd_key",          "catalog_module_definitions", ["key"])
    op.create_index("ix_cmd_is_universal", "catalog_module_definitions", ["is_universal"])

    # ── vertical_catalog_modules ─────────────────────────────────────────────────
    op.create_table(
        "vertical_catalog_modules",
        sa.Column("id",            UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("vertical_id",   UUID(as_uuid=True), sa.ForeignKey("verticals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module_id",     UUID(as_uuid=True), sa.ForeignKey("catalog_module_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_enabled",    sa.Boolean,  nullable=False, server_default="true"),
        sa.Column("is_required",   sa.Boolean,  nullable=False, server_default="false"),
        sa.Column("sort_order",    sa.Integer,  nullable=False, server_default="0"),
        sa.Column("custom_label",  sa.String(120), nullable=True),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("vertical_id", "module_id", name="uq_vcm_vertical_module"),
    )
    op.create_index("ix_vcm_vertical_id", "vertical_catalog_modules", ["vertical_id"])
    op.create_index("ix_vcm_module_id",   "vertical_catalog_modules", ["module_id"])

    # ── vertical_menu_config ─────────────────────────────────────────────────────
    op.create_table(
        "vertical_menu_config",
        sa.Column("id",           UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("vertical_id",  UUID(as_uuid=True), sa.ForeignKey("verticals.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("menu_items",   JSONB, nullable=True),   # ordered list [{module_key, label, path, icon}]
        sa.Column("updated_at",   sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_vmc_vertical_id", "vertical_menu_config", ["vertical_id"])

    # ── Seed data ────────────────────────────────────────────────────────────────
    _seed(op)


def _seed(op) -> None:
    from sqlalchemy.sql import text

    conn = op.get_bind()

    # 1. Verticals
    verticals = [
        ("home_services",         "Home Services",         "Wrench",   "#2563eb", True,  False, 1, "commission"),
        ("coaching",              "Coaching / IELTS",      "GraduationCap","#7c3aed",True,False,2,"subscription"),
        ("real_estate",           "Real Estate",           "Home",     "#0891b2", True,  False, 3, "commission"),
        ("beauty",                "Beauty & Wellness",     "Sparkles", "#db2777", True,  False, 4, "commission"),
        ("restaurant",            "Restaurant / Food",     "UtensilsCrossed","#ea580c",False,True,5,"subscription"),
        ("product_marketplace",   "Product Marketplace",   "ShoppingBag","#16a34a",False,True, 6, "hybrid"),
        ("professional_services", "Professional Services", "Briefcase","#64748b", False, True,  7, "commission"),
    ]
    vertical_ids: dict[str, str] = {}
    for key, label, icon, color, enabled, beta, sort, finance in verticals:
        vid = str(uuid.uuid4())
        vertical_ids[key] = vid
        conn.execute(text("""
            INSERT INTO verticals (id, key, label, icon, color, is_enabled, is_beta, sort_order, finance_model)
            VALUES (:id, :key, :label, :icon, :color, :enabled, :beta, :sort, :finance)
        """), {"id": vid, "key": key, "label": label, "icon": icon, "color": color,
               "enabled": enabled, "beta": beta, "sort": sort, "finance": finance})

    # 2. Catalog module definitions
    modules = [
        # key, label, icon, admin_path, group, is_universal, sort
        ("categories",       "Categories",       "Layers",       "/admin/categories",      "services",   True,  1),
        ("service_groups",   "Service Groups",   "FolderTree",   "/admin/service-groups",  "services",   False, 2),
        ("master_services",  "Master Services",  "Wrench",       "/admin/master-services", "services",   False, 3),
        ("types_brands",     "Types & Brands",   "Tag",          "/admin/types-brands",    "qualifiers", False, 4),
        ("brands",           "Brands",           "Tag",          "/admin/brands",          "qualifiers", True,  5),
        ("brand_requests",   "Brand Requests",   "Inbox",        "/admin/brand-requests",  "qualifiers", True,  6),
        ("service_options",  "Service Options",  "Settings2",    "/admin/service-options", "qualifiers", False, 7),
        ("issue_types",      "Issue Types",      "HelpCircle",   "/admin/issue-types",     "qualifiers", False, 8),
        ("pricing_tiers",    "Pricing Tiers",    "LayoutGrid",   "/admin/pricing-tiers",   "pricing",    True,  9),
        ("location_mapping", "City/Zip Mapping", "MapPin",       "/admin/location-mapping","pricing",    True,  10),
        ("pricing_rules",    "Pricing Rules",    "Sliders",      "/admin/pricing-rules",   "pricing",    False, 11),
        ("checklist_templates","Checklists",     "ListChecks",   "/admin/checklist-templates","compliance",False,12),
        ("service_setup",    "Service Setup",    "Package",      "/admin/service-setup",   "compliance", False, 13),
    ]
    module_ids: dict[str, str] = {}
    for key, label, icon, path, group, universal, sort in modules:
        mid = str(uuid.uuid4())
        module_ids[key] = mid
        conn.execute(text("""
            INSERT INTO catalog_module_definitions (id, key, label, icon, admin_path, module_group, is_universal, sort_order)
            VALUES (:id, :key, :label, :icon, :path, :group, :universal, :sort)
        """), {"id": mid, "key": key, "label": label, "icon": icon, "path": path,
               "group": group, "universal": universal, "sort": sort})

    # 3. Vertical → module assignments
    # home_services: all modules
    home_modules = list(module_ids.keys())
    coaching_modules = ["categories", "service_groups", "master_services", "brands",
                        "brand_requests", "pricing_tiers", "location_mapping"]
    real_estate_modules = ["categories", "service_groups", "master_services", "brands",
                           "brand_requests", "pricing_tiers", "location_mapping", "service_options"]
    beauty_modules = ["categories", "service_groups", "master_services", "types_brands",
                      "brands", "brand_requests", "service_options", "issue_types",
                      "pricing_tiers", "location_mapping"]
    restaurant_modules = ["categories", "service_groups", "master_services", "brands",
                          "pricing_tiers", "location_mapping"]
    product_modules = ["categories", "service_groups", "master_services", "brands",
                       "brand_requests", "service_options", "pricing_tiers", "location_mapping"]
    prof_modules = ["categories", "service_groups", "master_services", "brands",
                    "brand_requests", "service_options", "issue_types",
                    "pricing_tiers", "location_mapping", "pricing_rules"]

    assignments = {
        "home_services":         (home_modules, ["categories", "master_services", "issue_types"]),
        "coaching":              (coaching_modules, ["categories", "master_services"]),
        "real_estate":           (real_estate_modules, ["categories", "master_services"]),
        "beauty":                (beauty_modules, ["categories", "master_services"]),
        "restaurant":            (restaurant_modules, ["categories", "master_services"]),
        "product_marketplace":   (product_modules, ["categories", "master_services"]),
        "professional_services": (prof_modules, ["categories", "master_services"]),
    }

    for vkey, (mods, required) in assignments.items():
        vid = vertical_ids[vkey]
        for i, mkey in enumerate(mods):
            mid = module_ids[mkey]
            conn.execute(text("""
                INSERT INTO vertical_catalog_modules (id, vertical_id, module_id, is_enabled, is_required, sort_order)
                VALUES (:id, :vid, :mid, true, :req, :sort)
            """), {"id": str(uuid.uuid4()), "vid": vid, "mid": mid,
                   "req": mkey in required, "sort": i})


def downgrade() -> None:
    op.drop_table("vertical_menu_config")
    op.drop_table("vertical_catalog_modules")
    op.drop_table("catalog_module_definitions")
    op.drop_table("verticals")
