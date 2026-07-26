"""Reseed verticals + platform engine registry.

An out-of-band full data wipe (requested by the user, executed manually
outside alembic — TRUNCATE of every table except `users`/`tenants`, keeping
exactly 2 login rows) emptied several tables that are platform SEED/CONFIG
data, not tenant business data: `verticals`, `catalog_module_definitions`,
`vertical_catalog_modules`, `platform_engines`, `engine_dependencies`,
`vertical_engine_mappings`, and the `tenant_vertical_enrollments` /
`verticals.slug` backfills. Nothing about the wipe was migration-tracked, so
`alembic_version` still reads "158" even though this seed data is gone --
this migration exists purely to restore it, reusing the EXACT same seed data
and idempotent (ON CONFLICT DO NOTHING) logic originally written in
migrations 081, 089, 090, 095, and 148, rather than inventing new data.

Purely additive / idempotent -- safe to run even if some of this data
already exists (e.g. on a fresh install that never had the manual wipe).

Revision ID: 159
Revises: 158
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "159"
down_revision = "158"
branch_labels = None
depends_on = None


# ── From migration 081 (platform_engines + engine_dependencies) ────────────
_ENGINES = [
    ("auth_iam",            "Auth & IAM Engine",           "core",       "core",       True,  True,  "1.0.0", "Platform Team"),
    ("rag",                 "RAG Engine",                  "ai",         "active",     False, False, "1.0.0", "AI Team"),
    ("notification",        "Notification Engine",         "core",       "active",     True,  False, "1.0.0", "Platform Team"),
    ("payment",              "Payment Engine",              "finance",    "active",     False, False, "1.0.0", "Finance Team"),
    ("analytics",           "Analytics Engine",            "plugin",     "active",     False, False, "1.0.0", "Data Team"),
    ("media_vault",         "Media Vault Engine",          "core",       "active",     True,  False, "1.0.0", "Platform Team"),
    ("review_rating",       "Review & Rating Engine",      "plugin",     "active",     False, False, "1.0.0", "Marketplace Team"),
    ("chat",                "Chat Engine",                 "plugin",     "active",     False, False, "1.0.0", "Platform Team"),
    ("settings_config",     "Settings & Config Engine",    "core",       "core",       True,  True,  "1.0.0", "Platform Team"),
    ("service_catalog",     "Service Catalog Engine",      "core",       "active",     True,  True,  "1.0.0", "Catalog Team"),
    ("field_ops",           "Field Ops Engine",            "ops",        "active",     False, False, "1.0.0", "Ops Team"),
    ("booking",              "Booking Engine",              "vertical",   "active",     False, False, "1.0.0", "Marketplace Team"),
    ("appointment",         "Appointment Engine",          "vertical",   "active",     False, False, "1.0.0", "Marketplace Team"),
    ("leads_crm",            "Leads CRM Engine",            "vertical",   "active",     False, False, "1.0.0", "CRM Team"),
    ("food_menu",            "Food & Menu Engine",          "vertical",   "beta",       False, False, "0.9.0", "Marketplace Team"),
    ("job_dispatch",         "Job Dispatch Engine",         "ops",        "active",     False, False, "1.0.0", "Ops Team"),
    ("inventory",            "Inventory Engine",            "ops",        "active",     False, False, "1.0.0", "Ops Team"),
    ("real_estate",          "Real Estate Engine",          "vertical",   "active",     False, False, "1.0.0", "Marketplace Team"),
    ("loyalty_rewards",      "Loyalty & Rewards Engine",    "plugin",     "beta",       False, False, "0.8.0", "Marketplace Team"),
    ("pricing",               "Pricing Engine",              "finance",    "active",     False, False, "1.0.0", "Finance Team"),
    ("bargain",               "Bargain Engine",              "plugin",     "active",     False, False, "1.0.0", "Marketplace Team"),
    ("finance",               "Finance Engine",              "finance",    "core",       True,  True,  "1.0.0", "Finance Team"),
    ("package_credit",       "Package/Credit Engine",       "finance",    "active",     False, False, "1.0.0", "Finance Team"),
    ("commission",            "Commission Engine",           "finance",    "active",     False, False, "1.0.0", "Finance Team"),
    ("compliance",            "Compliance Engine",           "compliance", "active",     False, False, "1.0.0", "Legal Team"),
    ("marketing",             "Marketing Engine",            "plugin",     "active",     False, False, "1.0.0", "Marketing Team"),
    ("complaint_dispute",     "Complaint & Dispute Engine",  "plugin",     "active",     False, False, "1.0.0", "Support Team"),
    ("customer_svc_credit",  "Customer Service Credit Engine", "finance", "active",     False, False, "1.0.0", "Finance Team"),
    ("audit",                 "Audit Engine",                "core",       "core",       True,  True,  "1.0.0", "Platform Team"),
    ("security",              "Security Engine",             "core",       "core",       True,  True,  "1.0.0", "Security Team"),
    ("ai_workflow",           "AI Workflow Engine",          "ai",         "active",     False, False, "1.0.0", "AI Team"),
]

_DEPENDENCIES = [
    ("rag",              "auth_iam",       "required"),
    ("rag",              "media_vault",    "required"),
    ("notification",     "auth_iam",       "required"),
    ("payment",          "auth_iam",       "required"),
    ("analytics",        "auth_iam",       "required"),
    ("media_vault",      "auth_iam",       "required"),
    ("review_rating",    "auth_iam",       "required"),
    ("review_rating",    "booking",        "required"),
    ("chat",             "auth_iam",       "required"),
    ("chat",             "notification",   "optional"),
    ("field_ops",        "auth_iam",       "required"),
    ("field_ops",        "booking",        "required"),
    ("booking",          "auth_iam",       "required"),
    ("booking",          "service_catalog","required"),
    ("booking",          "pricing",        "required"),
    ("booking",          "notification",   "required"),
    ("appointment",      "auth_iam",       "required"),
    ("appointment",      "notification",   "required"),
    ("leads_crm",        "auth_iam",       "required"),
    ("food_menu",        "auth_iam",       "required"),
    ("food_menu",        "inventory",      "optional"),
    ("job_dispatch",     "auth_iam",       "required"),
    ("job_dispatch",     "booking",        "required"),
    ("inventory",        "auth_iam",       "required"),
    ("real_estate",      "auth_iam",       "required"),
    ("real_estate",      "leads_crm",      "required"),
    ("loyalty_rewards",  "auth_iam",       "required"),
    ("loyalty_rewards",  "booking",        "required"),
    ("pricing",          "auth_iam",       "required"),
    ("pricing",          "service_catalog","required"),
    ("bargain",           "auth_iam",       "required"),
    ("bargain",           "pricing",        "required"),
    ("finance",           "auth_iam",       "required"),
    ("finance",           "payment",        "required"),
    ("package_credit",   "auth_iam",       "required"),
    ("package_credit",   "finance",        "required"),
    ("commission",        "auth_iam",       "required"),
    ("commission",        "finance",        "required"),
    ("compliance",        "auth_iam",       "required"),
    ("compliance",        "audit",          "required"),
    ("marketing",          "auth_iam",       "required"),
    ("marketing",          "notification",   "required"),
    ("complaint_dispute", "auth_iam",       "required"),
    ("complaint_dispute", "booking",        "optional"),
    ("customer_svc_credit", "auth_iam",     "required"),
    ("customer_svc_credit", "finance",      "required"),
    ("customer_svc_credit", "complaint_dispute", "required"),
    ("ai_workflow",       "auth_iam",       "required"),
    ("ai_workflow",       "rag",            "optional"),
]

# ── From migration 095 (Trust & Quality engine registration) ───────────────
_TQ_ENGINES = [
    ("trust_quality_engine", "Trust & Quality Engine",
     "Umbrella engine coordinating badges, health, and risk scoring.", "core"),
    ("badge_engine", "Badge Engine", "Runtime badge assignment/revocation.", "core"),
    ("badge_rule_engine", "Badge Rule Engine", "Configurable badge award/removal criteria.", "core"),
    ("health_engine", "Health Engine", "Runtime provider/staff/customer/service health scoring.", "core"),
    ("health_rule_engine", "Health Rule Engine", "Configurable health formulas, penalties, bonuses, bands.", "core"),
    ("risk_scoring_engine", "Risk Scoring Engine", "Converts health/rule signals into risk levels and actions.", "core"),
    ("rule_simulator_engine", "Rule Simulator Engine", "Previews badge/health rule outcomes before activation.", "plugin"),
    ("recalculation_job_engine", "Recalculation Job Engine", "Runs badge/health/risk recalculation jobs.", "plugin"),
]
_TQ_DEPS = [
    ("trust_quality_engine", "badge_engine"),
    ("trust_quality_engine", "health_engine"),
    ("trust_quality_engine", "risk_scoring_engine"),
    ("badge_engine", "badge_rule_engine"),
    ("health_engine", "health_rule_engine"),
    ("risk_scoring_engine", "health_engine"),
    ("rule_simulator_engine", "badge_rule_engine"),
    ("rule_simulator_engine", "health_rule_engine"),
    ("recalculation_job_engine", "badge_engine"),
    ("recalculation_job_engine", "health_engine"),
]

# ── From migration 089 (verticals + catalog modules) ───────────────────────
_VERTICALS = [
    ("home_services",         "Home Services",         "Wrench",   "#2563eb", True,  False, 1, "commission"),
    ("coaching",              "Coaching / IELTS",      "GraduationCap", "#7c3aed", True, False, 2, "subscription"),
    ("real_estate",           "Real Estate",           "Home",     "#0891b2", True,  False, 3, "commission"),
    ("beauty",                "Beauty & Wellness",     "Sparkles", "#db2777", True,  False, 4, "commission"),
    ("restaurant",            "Restaurant / Food",     "UtensilsCrossed", "#ea580c", False, True, 5, "subscription"),
    ("product_marketplace",   "Product Marketplace",   "ShoppingBag", "#16a34a", False, True, 6, "hybrid"),
    ("professional_services", "Professional Services", "Briefcase", "#64748b", False, True, 7, "commission"),
]

_MODULES = [
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
    ("checklist_templates", "Checklists",    "ListChecks",   "/admin/checklist-templates", "compliance", False, 12),
    ("service_setup",    "Service Setup",    "Package",      "/admin/service-setup",   "compliance", False, 13),
]

_HOME_MODULES = [m[0] for m in _MODULES]
_ASSIGNMENTS = {
    "home_services": (_HOME_MODULES, ["categories", "master_services", "issue_types"]),
}

# ── From migration 090 (vertical-specific modules + reassignment) ──────────
_NEW_MODULES = [
    ("courses", "Courses", "BookOpen", "coaching", 1),
    ("batches", "Batches", "Users", "coaching", 2),
    ("demo_classes", "Demo Classes", "PlayCircle", "coaching", 3),
    ("counselors", "Counselors", "UserCheck", "coaching", 4),
    ("lead_forms", "Lead Forms", "FileText", "coaching", 5),
    ("fee_plans", "Fee Plans", "Banknote", "coaching", 6),
    ("property_types", "Property Types", "Home", "real_estate", 1),
    ("listing_types", "Listing Types", "Tag", "real_estate", 2),
    ("amenities", "Amenities", "Sparkles", "real_estate", 3),
    ("localities", "Localities", "MapPin", "real_estate", 4),
    ("site_visit_workflows", "Site Visit Workflows", "CalendarCheck", "real_estate", 5),
    ("menu_categories", "Menu Categories", "LayoutGrid", "restaurant", 1),
    ("menu_items", "Menu Items", "UtensilsCrossed", "restaurant", 2),
    ("item_variants", "Variants", "Layers", "restaurant", 3),
    ("addons", "Add-ons", "PlusCircle", "restaurant", 4),
    ("cuisine_types", "Cuisine Types", "Tag", "restaurant", 5),
    ("product_categories", "Product Categories", "Layers", "product_marketplace", 1),
    ("products", "Products", "ShoppingBag", "product_marketplace", 2),
    ("product_variants", "Variants", "Package", "product_marketplace", 3),
    ("attributes", "Attributes", "Settings2", "product_marketplace", 4),
    ("inventory_rules", "Inventory Rules", "Boxes", "product_marketplace", 5),
    ("consultation_types", "Consultation Types", "MessageSquare", "professional_services", 1),
    ("document_requirements", "Document Requirements", "FileText", "professional_services", 2),
    ("appointment_types", "Appointment Types", "Calendar", "professional_services", 3),
    ("subscription_plans", "Subscription Plans", "Repeat", "professional_services", 4),
]
_NEW_ASSIGNMENTS = {
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
_REQUIRED_MODULES = {
    "coaching": ["categories", "courses"],
    "real_estate": ["categories", "property_types"],
    "beauty": ["categories", "master_services"],
    "restaurant": ["categories", "menu_categories"],
    "product_marketplace": ["categories", "products"],
    "professional_services": ["categories", "consultation_types"],
}


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. platform_engines + engine_dependencies (migration 081) ──────────
    for (ek, dn, etype, lifecycle, is_core, is_locked, version, team) in _ENGINES:
        gstatus = "locked" if is_locked else "enabled"
        conn.execute(sa.text("""
            INSERT INTO platform_engines (engine_key, display_name, engine_type, lifecycle_status,
                global_status, is_core, is_locked, version, owner_team)
            VALUES (:ek, :dn, :etype, :lifecycle, :gstatus, :is_core, :is_locked, :version, :team)
            ON CONFLICT (engine_key) DO NOTHING
        """), {"ek": ek, "dn": dn, "etype": etype, "lifecycle": lifecycle, "gstatus": gstatus,
               "is_core": is_core, "is_locked": is_locked, "version": version, "team": team})

    for (ek, dep_ek, dtype) in _DEPENDENCIES:
        conn.execute(sa.text("""
            INSERT INTO engine_dependencies (engine_id, engine_key, depends_on_engine_id, depends_on_engine_key, dependency_type)
            SELECT pe.id, pe.engine_key, dep.id, dep.engine_key, :dtype
            FROM platform_engines pe, platform_engines dep
            WHERE pe.engine_key = :ek AND dep.engine_key = :dep_ek
            ON CONFLICT (engine_id, depends_on_engine_id) DO NOTHING
        """), {"ek": ek, "dep_ek": dep_ek, "dtype": dtype})

    # ── 2. Trust & Quality engines (migration 095) ──────────────────────────
    for key, name, desc, etype in _TQ_ENGINES:
        conn.execute(sa.text("""
            INSERT INTO platform_engines
                (id, engine_key, display_name, description, engine_type,
                 lifecycle_status, global_status, is_core, is_locked,
                 is_customer_visible, is_tenant_visible, version, metadata_json,
                 created_at, updated_at)
            VALUES
                (gen_random_uuid(), :key, :name, :desc, :etype,
                 'active', 'enabled', :is_core, false,
                 false, true, '1.0.0', '{}'::jsonb,
                 now(), now())
            ON CONFLICT (engine_key) DO NOTHING
        """), {"key": key, "name": name, "desc": desc, "etype": etype, "is_core": etype == "core"})

    for (ek, dep_ek) in _TQ_DEPS:
        conn.execute(sa.text("""
            INSERT INTO engine_dependencies (engine_id, engine_key, depends_on_engine_id, depends_on_engine_key, dependency_type)
            SELECT pe.id, pe.engine_key, dep.id, dep.engine_key, 'required'
            FROM platform_engines pe, platform_engines dep
            WHERE pe.engine_key = :ek AND dep.engine_key = :dep_ek
            ON CONFLICT (engine_id, depends_on_engine_id) DO NOTHING
        """), {"ek": ek, "dep_ek": dep_ek})

    # ── 3. verticals + catalog_module_definitions + vertical_catalog_modules
    #        (migration 089, home_services scope) ───────────────────────────
    vertical_ids: dict[str, str] = {}
    for key, label, icon, color, enabled, beta, sort, finance in _VERTICALS:
        existing = conn.execute(sa.text(
            "SELECT id FROM verticals WHERE key = :key"), {"key": key}).fetchone()
        if existing:
            vertical_ids[key] = str(existing[0])
            continue
        vid = str(uuid.uuid4())
        vertical_ids[key] = vid
        conn.execute(sa.text("""
            INSERT INTO verticals (id, key, label, icon, color, is_enabled, is_beta, sort_order, finance_model)
            VALUES (:id, :key, :label, :icon, :color, :enabled, :beta, :sort, :finance)
        """), {"id": vid, "key": key, "label": label, "icon": icon, "color": color,
               "enabled": enabled, "beta": beta, "sort": sort, "finance": finance})

    module_ids: dict[str, str] = {}
    for key, label, icon, path, group, universal, sort in _MODULES:
        existing = conn.execute(sa.text(
            "SELECT id FROM catalog_module_definitions WHERE key = :key"), {"key": key}).fetchone()
        if existing:
            module_ids[key] = str(existing[0])
            continue
        mid = str(uuid.uuid4())
        module_ids[key] = mid
        conn.execute(sa.text("""
            INSERT INTO catalog_module_definitions (id, key, label, icon, admin_path, module_group, is_universal, sort_order)
            VALUES (:id, :key, :label, :icon, :path, :group, :universal, :sort)
        """), {"id": mid, "key": key, "label": label, "icon": icon, "path": path,
               "group": group, "universal": universal, "sort": sort})

    for vkey, (mods, required) in _ASSIGNMENTS.items():
        vid = vertical_ids[vkey]
        for i, mkey in enumerate(mods):
            mid = module_ids[mkey]
            conn.execute(sa.text("""
                INSERT INTO vertical_catalog_modules (id, vertical_id, module_id, is_enabled, is_required, sort_order)
                VALUES (:id, :vid, :mid, true, :req, :sort)
                ON CONFLICT (vertical_id, module_id) DO NOTHING
            """), {"id": str(uuid.uuid4()), "vid": vid, "mid": mid,
                   "req": mkey in required, "sort": i})

    # ── 4. vertical-specific modules + reassignment (migration 090) ────────
    for key, label, icon, group, sort in _NEW_MODULES:
        existing = conn.execute(sa.text(
            "SELECT id FROM catalog_module_definitions WHERE key = :key"), {"key": key}).fetchone()
        if existing:
            module_ids[key] = str(existing[0])
            continue
        mid = str(uuid.uuid4())
        module_ids[key] = mid
        conn.execute(sa.text("""
            INSERT INTO catalog_module_definitions
                (id, key, label, icon, admin_path, module_group, is_universal, sort_order)
            VALUES (:id, :key, :label, :icon, :path, :group, false, :sort)
        """), {"id": mid, "key": key, "label": label, "icon": icon,
               "path": f"/admin/catalog-module/{key}", "group": group, "sort": sort})

    for vkey, mod_keys in _NEW_ASSIGNMENTS.items():
        vid = vertical_ids.get(vkey)
        if not vid:
            continue
        conn.execute(sa.text(
            "DELETE FROM vertical_catalog_modules WHERE vertical_id = :vid"), {"vid": vid})
        required = _REQUIRED_MODULES.get(vkey, [])
        for i, mkey in enumerate(mod_keys):
            mid = module_ids.get(mkey)
            if not mid:
                continue
            conn.execute(sa.text("""
                INSERT INTO vertical_catalog_modules (id, vertical_id, module_id, is_enabled, is_required, sort_order)
                VALUES (:id, :vid, :mid, true, :req, :sort)
                ON CONFLICT (vertical_id, module_id) DO NOTHING
            """), {"id": str(uuid.uuid4()), "vid": vid, "mid": mid,
                   "req": mkey in required, "sort": i})

    # ── 5. verticals.slug backfill (migration 148) ──────────────────────────
    conn.execute(sa.text("UPDATE verticals SET slug = key WHERE slug IS NULL"))

    # ── 6. tenant_vertical_enrollments backfill for surviving tenants
    #        (migration 148 logic, reruns safely for any tenant missing one) ─
    conn.execute(sa.text("""
        INSERT INTO tenant_vertical_enrollments
            (tenant_id, vertical_id, status, requested_at, activated_at, suspended_at, suspend_reason)
        SELECT
            t.id, v.id,
            CASE t.status
                WHEN 'active'    THEN 'active'
                WHEN 'suspended' THEN 'suspended'
                WHEN 'trial'     THEN 'active'
                ELSE 'submitted'
            END,
            t.created_at,
            CASE WHEN t.status IN ('active', 'trial') THEN COALESCE(t.activated_at, t.created_at) ELSE NULL END,
            CASE WHEN t.status = 'suspended' THEN COALESCE(t.suspended_at, t.created_at) ELSE NULL END,
            CASE WHEN t.status = 'suspended' THEN t.suspension_reason ELSE NULL END
        FROM tenants t
        JOIN verticals v ON v.key = t.vertical
        ON CONFLICT (tenant_id, vertical_id) DO NOTHING
    """))


def downgrade() -> None:
    # Data-only reseed; not reversible (would risk deleting legitimately
    # created rows created after this migration ran).
    pass
