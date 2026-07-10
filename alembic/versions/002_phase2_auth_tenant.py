"""Phase 2: Auth Engine + Tenant Engine tables

Revision ID: 002
Revises: 001
Create Date: 2024-12-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── USERS ─────────────────────────────────────────────────────────────────
    op.create_table("users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_mfa_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("mfa_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("force_password_change", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("failed_login_attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_history", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("onboarding_complete", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("meta", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_role", "users", ["role"])

    # ── USER SESSIONS ─────────────────────────────────────────────────────────
    op.create_table("user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("device_id", sa.String(255), nullable=False),
        sa.Column("device_name", sa.String(255), nullable=False),
        sa.Column("device_type", sa.String(50), nullable=False, server_default="unknown"),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("is_trusted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_approved", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])

    # ── REFRESH TOKEN FAMILIES ────────────────────────────────────────────────
    op.create_table("refresh_token_families",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_invalidated", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidation_reason", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_rtf_user_id", "refresh_token_families", ["user_id"])

    # ── REFRESH TOKENS ────────────────────────────────────────────────────────
    op.create_table("refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("jti", sa.String(100), nullable=False, unique=True),
        sa.Column("hashed_token", sa.String(255), nullable=False),
        sa.Column("is_used", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])
    op.create_index("ix_refresh_tokens_jti", "refresh_tokens", ["jti"])

    # ── MFA ───────────────────────────────────────────────────────────────────
    op.create_table("mfa_secrets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("encrypted_secret", sa.String(500), nullable=False),
        sa.Column("is_confirmed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_table("mfa_backup_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hashed_code", sa.String(255), nullable=False),
        sa.Column("is_used", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_mfa_backup_user_id", "mfa_backup_codes", ["user_id"])

    # ── STAFF PERMISSIONS ─────────────────────────────────────────────────────
    op.create_table("staff_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_key", sa.String(100), nullable=False),
        sa.Column("is_granted", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("granted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("user_id", "permission_key", name="uq_staff_permission"),
    )
    op.create_index("ix_staff_perms_user_id", "staff_permissions", ["user_id"])

    # ── API KEYS ──────────────────────────────────────────────────────────────
    op.create_table("api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key_prefix", sa.String(20), nullable=False),
        sa.Column("hashed_key", sa.String(255), nullable=False),
        sa.Column("scopes", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("is_test_mode", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calls_today", sa.Integer, nullable=False, server_default="0"),
        sa.Column("calls_total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_api_keys_tenant_id", "api_keys", ["tenant_id"])
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"])

    # ── OTP RECORDS ───────────────────────────────────────────────────────────
    op.create_table("otp_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("purpose", sa.String(50), nullable=False),
        sa.Column("recipient_hash", sa.String(255), nullable=False),
        sa.Column("hashed_otp", sa.String(255), nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_used", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_otp_records_recipient", "otp_records", ["recipient_hash"])

    # ── AUTH AUDIT LOGS ───────────────────────────────────────────────────────
    op.create_table("auth_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role", sa.String(30), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_type", sa.String(50), nullable=True),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("failure_reason", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("device_id", sa.String(255), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_auth_audit_actor_id", "auth_audit_logs", ["actor_id"])
    op.create_index("ix_auth_audit_tenant_id", "auth_audit_logs", ["tenant_id"])
    op.create_index("ix_auth_audit_action", "auth_audit_logs", ["action_type"])

    # ── TENANTS ───────────────────────────────────────────────────────────────
    op.create_table("tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_name", sa.String(255), nullable=False),
        sa.Column("subdomain", sa.String(100), nullable=True, unique=True),
        sa.Column("vertical", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="onboarding_pending"),
        sa.Column("plan_type", sa.String(30), nullable=False, server_default="starter"),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("country", sa.String(50), nullable=False, server_default="India"),
        sa.Column("health_score", sa.Numeric(5, 2), nullable=False, server_default="100.0"),
        sa.Column("health_band", sa.String(20), nullable=False, server_default="gold"),
        sa.Column("is_discoverable", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("meta", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspension_reason", sa.String(100), nullable=True),
        sa.Column("terminated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_tenants_status", "tenants", ["status"])
    op.create_index("ix_tenants_vertical", "tenants", ["vertical"])
    op.create_index("ix_tenants_plan_type", "tenants", ["plan_type"])

    # ── TENANT SUPPORTING TABLES ──────────────────────────────────────────────
    for table_name, cols in [
        ("tenant_business_profiles", [
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
            sa.Column("trade_name", sa.String(255), nullable=True),
            sa.Column("gstin", sa.String(20), nullable=True),
            sa.Column("gstin_verified", sa.Boolean, nullable=False, server_default="false"),
            sa.Column("cin", sa.String(25), nullable=True),
            sa.Column("cin_verified", sa.Boolean, nullable=False, server_default="false"),
            sa.Column("pan", sa.String(10), nullable=True),
            sa.Column("registered_address", postgresql.JSONB, nullable=False, server_default="{}"),
            sa.Column("year_established", sa.Integer, nullable=True),
            sa.Column("employee_count", sa.Integer, nullable=True),
            sa.Column("website_url", sa.String(255), nullable=True),
            sa.Column("description", sa.Text, nullable=True),
        ]),
        ("tenant_branding", [
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
            sa.Column("logo_url", sa.String(500), nullable=True),
            sa.Column("primary_color", sa.String(7), nullable=False, server_default="#3D7BFF"),
            sa.Column("secondary_color", sa.String(7), nullable=False, server_default="#10B981"),
            sa.Column("font_preference", sa.String(50), nullable=False, server_default="Inter"),
            sa.Column("custom_terms_url", sa.String(500), nullable=True),
            sa.Column("favicon_url", sa.String(500), nullable=True),
        ]),
        ("tenant_billing", [
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
            sa.Column("billing_email", sa.String(255), nullable=True),
            sa.Column("billing_cycle", sa.String(20), nullable=False, server_default="monthly"),
            sa.Column("razorpay_customer_id", sa.String(100), nullable=True),
            sa.Column("stripe_customer_id", sa.String(100), nullable=True),
            sa.Column("next_billing_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("subscription_status", sa.String(30), nullable=False, server_default="active"),
            sa.Column("credit_balance", sa.Numeric(12, 2), nullable=False, server_default="0.0"),
            sa.Column("security_deposit_paid", sa.Boolean, nullable=False, server_default="false"),
            sa.Column("security_deposit_amount", sa.Numeric(10, 2), nullable=False, server_default="0.0"),
        ]),
        ("tenant_limits", [
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
            sa.Column("max_staff", sa.Integer, nullable=False, server_default="10"),
            sa.Column("max_active_jobs", sa.Integer, nullable=False, server_default="20"),
            sa.Column("max_storage_gb", sa.Integer, nullable=False, server_default="10"),
            sa.Column("max_api_calls_per_day", sa.Integer, nullable=False, server_default="5000"),
            sa.Column("max_engines", sa.Integer, nullable=False, server_default="8"),
            sa.Column("max_customers", sa.Integer, nullable=False, server_default="500"),
            sa.Column("current_staff_count", sa.Integer, nullable=False, server_default="0"),
            sa.Column("current_active_jobs", sa.Integer, nullable=False, server_default="0"),
            sa.Column("current_api_calls_today", sa.Integer, nullable=False, server_default="0"),
        ]),
    ]:
        op.create_table(
            table_name,
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            *cols,
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        )

    # Onboarding requests
    op.create_table("onboarding_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("business_name", sa.String(255), nullable=False),
        sa.Column("vertical", sa.String(50), nullable=False),
        sa.Column("owner_name", sa.String(255), nullable=False),
        sa.Column("owner_email", sa.String(255), nullable=False),
        sa.Column("owner_phone", sa.String(20), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("state", sa.String(100), nullable=False),
        sa.Column("gstin", sa.String(20), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="submitted"),
        sa.Column("assigned_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("checklist", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("plan_type", sa.String(30), nullable=True),
        sa.Column("engines_to_enable", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("engine_configs", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("admin_notes", sa.Text, nullable=True),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
        sa.Column("review_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(30), nullable=False, server_default="self_signup"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_onboarding_status", "onboarding_requests", ["status"])

    # Tenant audit logs
    op.create_table("tenant_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role", sa.String(30), nullable=True),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", sa.String(100), nullable=True),
        sa.Column("before_state", postgresql.JSONB, nullable=True),
        sa.Column("after_state", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_tal_tenant_id", "tenant_audit_logs", ["tenant_id"])

    # Tenant feature flags
    op.create_table("tenant_feature_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("flag_key", sa.String(100), nullable=False),
        sa.Column("flag_value", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("set_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("tenant_id", "flag_key", name="uq_tff_tenant_key"),
    )

    # Seed a super admin user
    op.execute("""
        INSERT INTO users (id, email, full_name, role, hashed_password, is_active, is_verified, onboarding_complete)
        VALUES (
            gen_random_uuid(),
            'admin@serviceos.io',
            'Platform Admin',
            'super_admin',
            '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewGqQRRvqJ.6hF8G',
            true, true, true
        ) ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    for table in ["tenant_feature_flags","tenant_audit_logs","onboarding_requests",
                  "tenant_limits","tenant_billing","tenant_branding","tenant_business_profiles",
                  "tenants","auth_audit_logs","otp_records","api_keys","staff_permissions",
                  "mfa_backup_codes","mfa_secrets","refresh_tokens","refresh_token_families",
                  "user_sessions","users"]:
        op.drop_table(table)
