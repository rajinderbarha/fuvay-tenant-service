"""FINAL-L5-01 — Safe local/test/E2E database reset (Option C: FK-safe targeted delete).

Truncates tenant- and user-scoped runtime data via TRUNCATE ... CASCADE on
the two root tables (tenants, users). Catalog/config tables (categories,
master_services, service_types, brands, master_issue_types, master_offerings,
pricing_tiers, tier_locations) are NOT tenant-linked and are preserved,
since they hold correct canonical catalog data already validated in prior
sprints — re-truncating them would just require re-seeding identical data.

Refuses to run unless the same environment guard as canonical_seed_final_l5_01.py
passes. Requires --confirm to actually execute (default: dry-run/plan only).

Run: python scripts/reset_final_l5_01.py --confirm
"""
from __future__ import annotations
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

ALLOWED_ENVIRONMENTS = {"local", "development", "dev", "test", "e2e", "certification"}
FORBIDDEN_ENVIRONMENTS = {"production", "prod", "staging-live", "live"}
FORBIDDEN_HOST_MARKERS = (".amazonaws.com", ".azure.com", ".gcp.com", "prod-", ".rds.")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://serviceos:serviceos@localhost:5432/serviceos")
ALLOWED_DB_NAMES = {"serviceos"}

# All tables carrying a tenant_id column, most of which (~190 of them, see
# FINAL_L5_01_SCHEMA_TABLE_INVENTORY.md) have NO foreign-key constraint back
# to tenants(id) — a real schema gap discovered during this sprint. Because
# of that, plain `TRUNCATE tenants CASCADE` does NOT reach them, so every
# tenant/user-scoped runtime table is truncated explicitly and unconditionally
# here rather than relying on FK cascade. Catalog/master/config tables
# (categories, master_services, service_types, brands, master_issue_types,
# master_offerings, pricing_tiers, tier_locations) are deliberately excluded
# — they carry no tenant_id and hold already-canonical reference data.
TENANT_SCOPED_TABLES = [
    "ai_settlement_sessions", "ai_usage_logs", "analytics_daily_metrics", "analytics_events",
    "analytics_report_runs", "anomaly_records", "api_keys", "appointment_status_history",
    "appointments", "auth_audit_logs", "billing_router_logs", "bookability_audit_logs",
    "booking_notes", "booking_reschedule_requests", "booking_status_history", "bookings",
    "brand_adjustments", "brand_requests", "chat_thread_participants", "chat_threads",
    "churn_signals", "coaching_appointment_execution_events", "coaching_appointment_notes",
    "coaching_appointment_slot_holds", "coaching_appointments", "commission_records",
    "complaint_events", "complaint_messages", "complaint_policies", "complaint_resolutions",
    "compliance_audit_logs", "consent_records", "conversations", "credit_reservations",
    "credit_topup_orders", "customer_addresses", "customer_complaints", "customer_credit_balances",
    "customer_health_scores", "customer_ltv_scores", "customer_reviews", "customer_service_credits",
    "customer_transactions", "daily_metrics", "data_deletion_requests", "data_portability_requests",
    "data_retention_policies", "demand_forecasts", "dispatch_escalation_logs", "dispatch_records",
    "dispute_settlements", "document_chunks", "document_events", "document_templates", "documents",
    "dynamic_pricing_rules", "enterprise_column_preferences", "enterprise_export_jobs",
    "enterprise_saved_views", "final_creation_audit_logs", "finance_audit_logs", "financial_events",
    "in_app_notifications", "inventory_items", "invoice_records", "ip_blocklist", "job_media",
    "job_notes", "job_quotes", "job_status_history", "jobs", "kb_documents", "knowledge_bases",
    "login_events", "marketing_campaign_events", "marketing_campaigns", "marketing_posts",
    "media_assets", "media_audit_logs", "media_files", "media_upload_sessions", "messages",
    "notification_channel_configs", "notification_events", "notification_outbox",
    "notification_preferences", "notification_records", "notification_templates",
    "onboarding_requests", "package_audit_logs", "payment_records", "payout_records",
    "platform_audit_logs", "prediction_records", "price_snapshots", "provider_availability_rules",
    "provider_enabled_offerings", "provider_offering_bookable_statuses", "provider_pricing_overrides",
    "provider_team_members", "provider_visibility_statuses", "rag_queries", "rag_query_logs",
    "real_estate_lead_execution_events", "real_estate_lead_notes", "real_estate_leads",
    "recommendation_results", "recommendation_rules", "refund_records", "refund_requests",
    "review_aggregates", "review_events", "review_flags", "review_policies", "review_replies",
    "review_requests", "review_status_history", "reviews", "scheduled_posts",
    "security_deposit_adjustments", "security_deposit_transactions", "security_deposits",
    "service_bookings", "service_catalog_items", "service_invoice_items", "service_invoices",
    "service_job_assignment_events", "service_job_assignments", "service_job_checklist_items",
    "service_job_checklists", "service_job_execution_events", "service_job_execution_notes",
    "service_job_media_uploads", "service_job_parts_requests", "service_job_quote_events",
    "service_job_quote_items", "service_job_quotes", "service_jobs", "service_payment_records",
    "service_rework_requests", "service_setup_template_usage", "service_type_prices",
    "service_zones", "session_inventory", "setting_audit_logs", "settlement_proposals",
    "sj_checklist_templates", "staff_calendar_blocks", "staff_locations",
    "staff_performance_scores", "staff_permissions", "staff_rating_summaries",
    "staff_working_hours", "stock_balances", "stock_locations", "stock_reservations",
    "stock_transactions", "subscription_events", "subscription_periods", "subscriptions",
    "suspicious_activity_logs", "svc_commission_records", "tenant_api_keys", "tenant_audit_logs",
    "tenant_availability_exceptions", "tenant_badges", "tenant_billing", "tenant_billing_profiles",
    "tenant_booking_window_settings", "tenant_branding", "tenant_business_profiles",
    "tenant_engine_overrides", "tenant_engines", "tenant_feature_flags", "tenant_limits",
    "tenant_operational_settings", "tenant_penalties", "tenant_rating_summaries",
    "tenant_service_area_services", "tenant_service_areas", "tenant_service_brands",
    "tenant_service_types", "tenant_services", "tenant_settings", "tenant_supported_brands",
    "tenant_supported_service_options", "tenant_wallets", "usage_credit_ledger", "user_sessions",
    "wallet_transactions", "warranty_claims", "webhook_deliveries", "webhook_endpoints",
    "workflow_runtime_events", "workflow_service_mappings", "zone_analytic_snapshots",
    "zone_surcharges", "tenant_package_assignments",
]
TRUNCATE_ROOTS = ["tenants", "users", "service_pricing_rules"] + TENANT_SCOPED_TABLES


def _safety_guard() -> str:
    env = os.getenv("APP_ENV", "development").lower()
    allow = os.getenv("ALLOW_DATABASE_RESET", "false").lower() == "true"
    if env in FORBIDDEN_ENVIRONMENTS:
        print(f"[REFUSED] APP_ENV={env} is forbidden. Aborting."); sys.exit(1)
    if env not in ALLOWED_ENVIRONMENTS:
        print(f"[REFUSED] APP_ENV={env} not in allow-list {ALLOWED_ENVIRONMENTS}. Aborting."); sys.exit(1)
    if not allow:
        print("[REFUSED] ALLOW_DATABASE_RESET != true. Aborting."); sys.exit(1)
    if any(m in DATABASE_URL for m in FORBIDDEN_HOST_MARKERS):
        print("[REFUSED] DATABASE_URL host looks managed/cloud/production. Aborting."); sys.exit(1)
    db_name = DATABASE_URL.rsplit("/", 1)[-1].split("?")[0]
    if db_name not in ALLOWED_DB_NAMES:
        print(f"[REFUSED] Database name '{db_name}' not in allow-list {ALLOWED_DB_NAMES}. Aborting."); sys.exit(1)
    masked = DATABASE_URL.split("@")[-1]
    print(f"[OK] Safety guard passed. APP_ENV={env}, ALLOW_DATABASE_RESET=true, target=...@{masked}")
    return db_name


async def run(confirm: bool) -> None:
    db_name = _safety_guard()
    print(f"[TARGET] host+db = ...@{DATABASE_URL.split('@')[-1]} (db_name={db_name})")
    print(f"[PLAN] TRUNCATE ... CASCADE on root tables: {TRUNCATE_ROOTS}")
    print("[PLAN] Catalog/master tables (categories, master_services, service_types, brands, "
          "master_issue_types, master_offerings, pricing_tiers, tier_locations) are preserved.")

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        r = await db.execute(text("SELECT count(*) FROM tenants"))
        pre_tenants = r.scalar()
        r = await db.execute(text("SELECT count(*) FROM users"))
        pre_users = r.scalar()
        print(f"[PRE-COUNT] tenants={pre_tenants}, users={pre_users}")

        if not confirm:
            print("\n[DRY RUN] No changes made. Re-run with --confirm to execute.")
            await engine.dispose()
            return

        table_list = ", ".join(TRUNCATE_ROOTS)
        await db.execute(text(f"TRUNCATE TABLE {table_list} CASCADE"))
        print(f"[TRUNCATE] {len(TRUNCATE_ROOTS)} tables in one statement (incl. CASCADE for any real FK-linked tables not in the explicit list)")
        await db.commit()

        r = await db.execute(text("SELECT count(*) FROM tenants"))
        post_tenants = r.scalar()
        r = await db.execute(text("SELECT count(*) FROM users"))
        post_users = r.scalar()
        print(f"[POST-COUNT] tenants={post_tenants}, users={post_users}")
        print("\n[RESET COMPLETE]")

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true", help="Actually execute (default: dry run)")
    args = parser.parse_args()
    asyncio.run(run(args.confirm))
