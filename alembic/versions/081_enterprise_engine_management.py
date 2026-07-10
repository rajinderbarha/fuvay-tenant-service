"""Enterprise Engine Management — Platform-level engine registry + governance tables.

Revision ID: 081
Revises: 080
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "081"
down_revision = "080"
branch_labels = None
depends_on = None

# 31 platform engines seeded at migration time
ENGINES = [
    ("auth_iam",            "Auth & IAM Engine",           "core",       "core",       True,  True,  "1.0.0", "Platform Team"),
    ("rag",                 "RAG Engine",                  "ai",         "active",     False, False, "1.0.0", "AI Team"),
    ("notification",        "Notification Engine",         "core",       "active",     True,  False, "1.0.0", "Platform Team"),
    ("payment",             "Payment Engine",              "finance",    "active",     False, False, "1.0.0", "Finance Team"),
    ("analytics",           "Analytics Engine",            "plugin",     "active",     False, False, "1.0.0", "Data Team"),
    ("media_vault",         "Media Vault Engine",          "core",       "active",     True,  False, "1.0.0", "Platform Team"),
    ("review_rating",       "Review & Rating Engine",      "plugin",     "active",     False, False, "1.0.0", "Marketplace Team"),
    ("chat",                "Chat Engine",                 "plugin",     "active",     False, False, "1.0.0", "Platform Team"),
    ("settings_config",     "Settings & Config Engine",    "core",       "core",       True,  True,  "1.0.0", "Platform Team"),
    ("service_catalog",     "Service Catalog Engine",      "core",       "active",     True,  True,  "1.0.0", "Catalog Team"),
    ("field_ops",           "Field Ops Engine",            "ops",        "active",     False, False, "1.0.0", "Ops Team"),
    ("booking",             "Booking Engine",              "vertical",   "active",     False, False, "1.0.0", "Marketplace Team"),
    ("appointment",         "Appointment Engine",          "vertical",   "active",     False, False, "1.0.0", "Marketplace Team"),
    ("leads_crm",           "Leads CRM Engine",            "vertical",   "active",     False, False, "1.0.0", "CRM Team"),
    ("food_menu",           "Food & Menu Engine",          "vertical",   "beta",       False, False, "0.9.0", "Marketplace Team"),
    ("job_dispatch",        "Job Dispatch Engine",         "ops",        "active",     False, False, "1.0.0", "Ops Team"),
    ("inventory",           "Inventory Engine",            "ops",        "active",     False, False, "1.0.0", "Ops Team"),
    ("real_estate",         "Real Estate Engine",          "vertical",   "active",     False, False, "1.0.0", "Marketplace Team"),
    ("loyalty_rewards",     "Loyalty & Rewards Engine",    "plugin",     "beta",       False, False, "0.8.0", "Marketplace Team"),
    ("pricing",             "Pricing Engine",              "finance",    "active",     False, False, "1.0.0", "Finance Team"),
    ("bargain",             "Bargain Engine",              "plugin",     "active",     False, False, "1.0.0", "Marketplace Team"),
    ("finance",             "Finance Engine",              "finance",    "core",       True,  True,  "1.0.0", "Finance Team"),
    ("package_credit",      "Package/Credit Engine",       "finance",    "active",     False, False, "1.0.0", "Finance Team"),
    ("commission",          "Commission Engine",           "finance",    "active",     False, False, "1.0.0", "Finance Team"),
    ("compliance",          "Compliance Engine",           "compliance", "active",     False, False, "1.0.0", "Legal Team"),
    ("marketing",           "Marketing Engine",            "plugin",     "active",     False, False, "1.0.0", "Marketing Team"),
    ("complaint_dispute",   "Complaint & Dispute Engine",  "plugin",     "active",     False, False, "1.0.0", "Support Team"),
    ("customer_svc_credit", "Customer Service Credit Engine", "finance", "active",     False, False, "1.0.0", "Finance Team"),
    ("audit",               "Audit Engine",                "core",       "core",       True,  True,  "1.0.0", "Platform Team"),
    ("security",            "Security Engine",             "core",       "core",       True,  True,  "1.0.0", "Security Team"),
    ("ai_workflow",         "AI Workflow Engine",          "ai",         "active",     False, False, "1.0.0", "AI Team"),
]

# (engine_key, depends_on_key, dep_type)
DEPENDENCIES = [
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
    ("bargain",          "auth_iam",       "required"),
    ("bargain",          "pricing",        "required"),
    ("finance",          "auth_iam",       "required"),
    ("finance",          "payment",        "required"),
    ("package_credit",   "auth_iam",       "required"),
    ("package_credit",   "finance",        "required"),
    ("commission",       "auth_iam",       "required"),
    ("commission",       "finance",        "required"),
    ("compliance",       "auth_iam",       "required"),
    ("compliance",       "audit",          "required"),
    ("marketing",        "auth_iam",       "required"),
    ("marketing",        "notification",   "required"),
    ("complaint_dispute","auth_iam",       "required"),
    ("complaint_dispute","booking",        "optional"),
    ("customer_svc_credit","auth_iam",     "required"),
    ("customer_svc_credit","finance",      "required"),
    ("customer_svc_credit","complaint_dispute","required"),
    ("ai_workflow",      "auth_iam",       "required"),
    ("ai_workflow",      "rag",            "optional"),
]


def upgrade() -> None:
    # ── 1. Platform Engines ────────────────────────────────────────────────────
    op.create_table(
        "platform_engines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("engine_key", sa.String(80), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("engine_type", sa.String(30), nullable=False),
        sa.Column("lifecycle_status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("global_status", sa.String(30), nullable=False, server_default="enabled"),
        sa.Column("is_core", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_locked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_customer_visible", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_tenant_visible", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("version", sa.String(30), nullable=False, server_default="1.0.0"),
        sa.Column("owner_team", sa.String(100)),
        sa.Column("metadata_json", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_pe_engine_key", "platform_engines", ["engine_key"])
    op.create_index("ix_pe_engine_type", "platform_engines", ["engine_type"])
    op.create_index("ix_pe_global_status", "platform_engines", ["global_status"])
    op.create_index("ix_pe_lifecycle", "platform_engines", ["lifecycle_status"])

    # Seed engines
    for (ek, dn, etype, lifecycle, is_core, is_locked, version, team) in ENGINES:
        gstatus = "locked" if is_locked else "enabled"
        op.execute(f"""
            INSERT INTO platform_engines (engine_key, display_name, engine_type, lifecycle_status,
                global_status, is_core, is_locked, version, owner_team)
            VALUES ('{ek}', '{dn}', '{etype}', '{lifecycle}',
                '{gstatus}', {'true' if is_core else 'false'}, {'true' if is_locked else 'false'},
                '{version}', '{team}')
            ON CONFLICT (engine_key) DO NOTHING
        """)

    # ── 2. Engine Dependencies ─────────────────────────────────────────────────
    op.create_table(
        "engine_dependencies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("engine_id", UUID(as_uuid=True), nullable=False),
        sa.Column("engine_key", sa.String(80), nullable=False),
        sa.Column("depends_on_engine_id", UUID(as_uuid=True), nullable=False),
        sa.Column("depends_on_engine_key", sa.String(80), nullable=False),
        sa.Column("dependency_type", sa.String(20), nullable=False, server_default="required"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("engine_id", "depends_on_engine_id", name="uq_engine_dep"),
    )
    op.create_index("ix_edep_engine_id", "engine_dependencies", ["engine_id"])
    op.create_index("ix_edep_depends_on", "engine_dependencies", ["depends_on_engine_id"])

    # Seed dependencies
    for (ek, dep_ek, dtype) in DEPENDENCIES:
        op.execute(f"""
            INSERT INTO engine_dependencies (engine_id, engine_key, depends_on_engine_id, depends_on_engine_key, dependency_type)
            SELECT pe.id, pe.engine_key, dep.id, dep.engine_key, '{dtype}'
            FROM platform_engines pe, platform_engines dep
            WHERE pe.engine_key = '{ek}' AND dep.engine_key = '{dep_ek}'
            ON CONFLICT (engine_id, depends_on_engine_id) DO NOTHING
        """)

    # ── 3. Category Engine Matrix ──────────────────────────────────────────────
    op.create_table(
        "category_engine_matrix",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("category_id", UUID(as_uuid=True), nullable=False),
        sa.Column("engine_id", UUID(as_uuid=True), nullable=False),
        sa.Column("engine_key", sa.String(80), nullable=False),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("config_json", JSONB, server_default="{}"),
        sa.Column("enabled_by_admin_id", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("category_id", "engine_id", name="uq_cat_engine"),
    )
    op.create_index("ix_cem_category", "category_engine_matrix", ["category_id"])
    op.create_index("ix_cem_engine", "category_engine_matrix", ["engine_id"])
    op.create_index("ix_cem_enabled", "category_engine_matrix", ["is_enabled"])

    # ── 4. Package Engine Entitlements ─────────────────────────────────────────
    op.create_table(
        "package_engine_entitlements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("package_id", UUID(as_uuid=True), nullable=False),
        sa.Column("engine_id", UUID(as_uuid=True), nullable=False),
        sa.Column("engine_key", sa.String(80), nullable=False),
        sa.Column("is_included", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("limits_json", JSONB, server_default="{}"),
        sa.Column("feature_flags_json", JSONB, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("added_by_admin_id", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("package_id", "engine_id", name="uq_pkg_engine"),
    )
    op.create_index("ix_pee_package", "package_engine_entitlements", ["package_id"])
    op.create_index("ix_pee_engine", "package_engine_entitlements", ["engine_id"])

    # ── 5. Tenant Engine Overrides ─────────────────────────────────────────────
    op.create_table(
        "tenant_engine_overrides",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("engine_id", UUID(as_uuid=True), nullable=False),
        sa.Column("engine_key", sa.String(80), nullable=False),
        sa.Column("override_type", sa.String(30), nullable=False),
        sa.Column("effective_status", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_by_admin_id", UUID(as_uuid=True)),
        sa.Column("approved_by_admin_id", UUID(as_uuid=True)),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_by_admin_id", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_teo_tenant", "tenant_engine_overrides", ["tenant_id"])
    op.create_index("ix_teo_engine", "tenant_engine_overrides", ["engine_id"])
    op.create_index("ix_teo_status", "tenant_engine_overrides", ["status"])
    op.create_index("ix_teo_tenant_engine", "tenant_engine_overrides", ["tenant_id", "engine_id"])

    # ── 6. Engine Health Checks ────────────────────────────────────────────────
    op.create_table(
        "engine_health_checks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("engine_id", UUID(as_uuid=True), nullable=False),
        sa.Column("engine_key", sa.String(80), nullable=False),
        sa.Column("health_status", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("check_type", sa.String(40), nullable=False, server_default="manual"),
        sa.Column("result_json", JSONB, server_default="{}"),
        sa.Column("error_message", sa.Text),
        sa.Column("response_ms", sa.Integer),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("checked_by_user_id", UUID(as_uuid=True)),
    )
    op.create_index("ix_ehc_engine_id", "engine_health_checks", ["engine_id"])
    op.create_index("ix_ehc_checked_at", "engine_health_checks", ["checked_at"])
    op.create_index("ix_ehc_status", "engine_health_checks", ["health_status"])

    # ── 7. Engine Permissions ──────────────────────────────────────────────────
    op.create_table(
        "engine_permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("engine_id", UUID(as_uuid=True), nullable=False),
        sa.Column("engine_key", sa.String(80), nullable=False),
        sa.Column("permission_key", sa.String(120), nullable=False, unique=True),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("scope", sa.String(30), nullable=False, server_default="platform_admin"),
        sa.Column("is_sensitive", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("requires_mfa", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_eperm_engine", "engine_permissions", ["engine_id"])
    op.create_index("ix_eperm_key", "engine_permissions", ["permission_key"])
    op.create_index("ix_eperm_scope", "engine_permissions", ["scope"])

    # Seed key permissions per engine
    perm_seeds = [
        # auth
        ("auth_iam", "auth:login",          "Login",         "platform_admin", False, False),
        ("auth_iam", "auth:token:refresh",  "Refresh Token", "platform_admin", False, False),
        ("auth_iam", "auth:users:read",     "Read Users",    "platform_admin", False, False),
        # booking
        ("booking", "booking:read",         "Read Bookings",    "tenant_owner", False, False),
        ("booking", "booking:create",       "Create Booking",   "customer",     False, False),
        ("booking", "booking:assign",       "Assign Booking",   "tenant_owner", False, False),
        ("booking", "booking:complete",     "Complete Booking", "tenant_staff", False, False),
        ("booking", "booking:cancel",       "Cancel Booking",   "tenant_owner", False, False),
        ("booking", "booking:audit_read",   "Booking Audit",    "platform_admin", True, False),
        # finance
        ("finance", "finance:read",             "Finance Read",           "platform_admin", False, False),
        ("finance", "finance:settlements:read", "Settlement Read",        "platform_admin", True,  True),
        ("finance", "finance:wallet:adjust",    "Wallet Adjust",          "platform_admin", True,  True),
        # analytics
        ("analytics", "analytics:read",     "Analytics Read",   "tenant_owner", False, False),
        ("analytics", "analytics:export",   "Analytics Export", "platform_admin", False, False),
        # compliance
        ("compliance", "compliance:read",   "Compliance Read",  "platform_admin", False, False),
        ("compliance", "compliance:manage", "Compliance Manage","platform_admin", True, True),
        # security
        ("security", "security:audit_read", "Security Audit",   "platform_admin", True, True),
        ("security", "security:lock",       "Lock Account",     "platform_admin", True, True),
    ]
    for (ek, pk, lbl, scope, sensitive, mfa) in perm_seeds:
        op.execute(f"""
            INSERT INTO engine_permissions (engine_id, engine_key, permission_key, label, scope, is_sensitive, requires_mfa)
            SELECT pe.id, pe.engine_key, '{pk}', '{lbl}', '{scope}',
                {'true' if sensitive else 'false'}, {'true' if mfa else 'false'}
            FROM platform_engines pe
            WHERE pe.engine_key = '{ek}'
            ON CONFLICT (permission_key) DO NOTHING
        """)

    # ── 8. Engine Audit Logs ───────────────────────────────────────────────────
    op.create_table(
        "engine_audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("engine_id", UUID(as_uuid=True)),
        sa.Column("engine_key", sa.String(80)),
        sa.Column("action_type", sa.String(80), nullable=False),
        sa.Column("scope_type", sa.String(30), nullable=False, server_default="global"),
        sa.Column("scope_id", UUID(as_uuid=True)),
        sa.Column("actor_user_id", UUID(as_uuid=True)),
        sa.Column("actor_role", sa.String(40)),
        sa.Column("old_value_json", JSONB),
        sa.Column("new_value_json", JSONB),
        sa.Column("reason", sa.Text),
        sa.Column("request_id", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_eal_engine_id", "engine_audit_logs", ["engine_id"])
    op.create_index("ix_eal_action", "engine_audit_logs", ["action_type"])
    op.create_index("ix_eal_actor", "engine_audit_logs", ["actor_user_id"])
    op.create_index("ix_eal_scope", "engine_audit_logs", ["scope_type", "scope_id"])
    op.create_index("ix_eal_created", "engine_audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("engine_audit_logs")
    op.drop_table("engine_permissions")
    op.drop_table("engine_health_checks")
    op.drop_table("tenant_engine_overrides")
    op.drop_table("package_engine_entitlements")
    op.drop_table("category_engine_matrix")
    op.drop_table("engine_dependencies")
    op.drop_table("platform_engines")
