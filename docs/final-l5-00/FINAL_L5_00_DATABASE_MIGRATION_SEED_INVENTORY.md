# FINAL-L5-00 Part 8 — Database Migration & Seed Inventory

Read-only investigation. No migration, seed script, or data was modified, run, or reset.

## 1. Migration Sequence

**Method:** Alembic was not run in this environment (no live DB connection assumed safe for a
read-only audit); instead every file in `alembic/versions/*.py` was parsed for its
`revision` / `down_revision` string literals and the chain was reconstructed programmatically.

- **Total migration files:** 124 (`alembic/versions/*.py`, excluding `__pycache__`)
- **Filename numeric range:** `001_initial_schema.py` → `131_admin_e2e06_report_runs_updated_at.py`
- **Revision chain root** (`down_revision = None`): `001` — single root, confirmed.
- **Revision chain head** (revision not referenced as anyone's `down_revision`): `131` — single head, confirmed.
- **Branches / multiple heads:** None detected. Every `down_revision` value resolves to an
  existing `revision` in the file set (0 missing/dangling references).
- **Numbering gap:** Filenames `024`–`030` do not exist as separate files. This is explained
  by `031_sprint_stub.py`, whose docstring states: *"Sprint 9-13 bridge — creates all catalog
  tables missing from migrations 024-030."* In other words, those seven numbers were reserved/
  planned but their table changes were consolidated into the `031` stub rather than being
  gap-filled after the fact. The `revision`/`down_revision` chain itself has no gap (031's
  `down_revision` points at the true prior head), so this is a **filename numbering gap only**,
  not a broken migration chain.
- **Other numbering irregularities:** Several "fix" migrations were inserted later out of
  strict topic order to patch missing `updated_at` columns or ORM/DB drift (e.g. `052`, `062`–
  `069`, `087`, `091`, `099`, `101`, `108`, `122`–`127`, `131`). These are legitimate, individually
  chained corrective migrations, not orphaned branches.

Per-file summary (chronological by filename, which matches the reconstructed revision chain):

| # | File | Purpose (from docstring / filename) |
|---|------|--------------------------------------|
| 001 | 001_initial_schema.py | Initial schema: extensions + tenant_engines table |
| 002 | 002_phase2_auth_tenant.py | Auth Engine + Tenant Engine tables |
| 003 | 003_phase3_platform_commerce.py | Platform Commerce Engine (12 tables) |
| 004 | 004_phase4_pricing.py | Pricing Engine (6 tables) |
| 005 | 005_phase5_support_engines.py | Settings + Notification + Media + Analytics (11 tables) |
| 006 | 006_phase6_rag.py | RAG Engine (4 tables + pgvector extension) |
| 007 | 007_phase7_data_science.py | Data Science Engine (7 tables) |
| 008 | 008_phase8_geo_dispatch_fieldops.py | Geo + Dispatch + Field Ops (9 tables) — origin of legacy `jobs` table |
| 009 | 009_phase9_booking_appointment.py | Booking + Appointment (8 tables) |
| 010 | 010_phase10_payment_inventory_subscription_document.py | Payment + Inventory + Subscription + Document (15 tables) |
| 011 | 011_phase11_review_chat_webhook.py | Review + Chat + Webhook (8 tables) |
| 012 | 012_phase12_security.py | Security Engine (5 tables) |
| 013 | 013_phase13_compliance.py | Compliance Engine (5 tables) |
| 014 | 014_phase14_billing_router.py | Billing Router (3 tables inside Platform Commerce) — origin of `tenant_billing.credit_balance` |
| 015 | 015_phase15_marketing.py | Marketing Automation Engine (5 tables) |
| 016 | 016_phase16_notification_templates.py | Seeds platform-default `notification_templates` (in_app channel); contains scoped `DELETE FROM notification_templates WHERE tenant_id IS NULL AND channel='in_app'` re-seed guard |
| 017 | 017_phase17_universal_service_phases.py | Universal Service Phase Logic (repair/service/consultation) |
| 018 | 018_phase18_service_catalog.py | Service Catalog Engine (tenant-defined services) |
| 019 | 019_phase19_quote_expiry_parts.py | Quote/Approval: expiry date, parts/labour breakdown |
| 020 | 020_phase20_checklist_templates.py | Checklist system on service_catalog_items |
| 021 | 021_phase21_serviceability_engine.py | Serviceability Engine: addresses, service areas |
| 022 | 022_phase22_tenant_address_fields.py | Tenant address fields (zipcode) |
| 023 | 023_phase23_serviceability_hardening.py | Serviceability hardening: partial unique indexes |
| — | *(024–030 — no files; see gap note above)* | |
| 031 | 031_sprint_stub.py | Sprint 9–13 bridge; creates catalog tables missing from 024–030; contains scoped `DROP TABLE IF EXISTS ... CASCADE` for its own stub tables only |
| 032 | 032_sprint14_customer_category_flow.py | Customer Category Flow Routing |
| 033 | 033_sprint15_ai_conversation_engine.py | AI Conversation Engine + DeepSeek Orchestrator |
| 034 | 034_sprint16_home_service_booking.py | Home Service Chatbot Booking Flow |
| 035 | 035_sprint17_coaching_appointment.py | Coaching/IELTS Chatbot Appointment Flow |
| 036 | 036_sprint18_real_estate_lead.py | Real Estate Chatbot Lead Flow |
| 037 | 037_sprint19_final_records.py | Booking Confirmation → Final Record Creation; origin of canonical `service_jobs` table |
| 038 | 038_sprint20_job_assignment.py | Home Service Job Assignment + Staff Lifecycle |
| 039 | 039_sprint21_execution_lifecycle.py | Repair/Service/Consultation Execution Flow |
| 040 | 040_sprint22_quote_checklist.py | Quote Approval + Checklist Engine for `service_jobs` |
| 041 | 041_sprint23_invoice_payment.py | Invoice/Payment/Commission/Subscription Status |
| 042 | 042_sprint24_customer_reviews.py | Customer Reviews + Rating Engine |
| 043 | 043_sprint25_complaints_disputes.py | Complaints/Disputes/Refund/Rework |
| 044 | 044_sprint26_enterprise_grid.py | Enterprise Filters + Data Grid System |
| 045 | 045_sprint27_notifications_chat_audit.py | Notification + Chat + Audit Integration |
| 046 | 046_sprint28_analytics.py | Category Analytics + Provider/Admin Reports |
| 047 | 047_sprint29_ai_marketing.py | AI Hardening + Marketing Automation tables |
| 048 | 048_sprint33_performance_indexes.py | Performance indexes for high-query tables |
| 049 | 049_phase0a_media_assets.py | Media Engine Hardening: media_assets table |
| 050 | 050_phase0b_profile_photo_linking.py | Profile Photo Linking columns on tenants |
| 051 | 051_phase0c_profile_edit.py | display_name, language, timezone on users |
| 052 | 052_fix_tenants_orm_mismatch.py | Fix: tenants columns missing vs ORM |
| 053 | 053_phase0d_password_security.py | Force Password Change + Admin Reset |
| 054 | 054_phase0e_account_security.py | Account Security + Admin User Controls |
| 055 | 055_sprint34c_master_data.py | Centralized Master Data Foundation |
| 056 | 056_sprint34d_brand_management.py | Enterprise Brand Management |
| 057 | 057_sprint34e_service_options_issue_catalog.py | Service Options + Issue Catalog |
| 058 | 058_sprint34f_service_setup_templates.py | Service Setup Templates |
| 059 | 059_sprint34h_bulk_setup_wizard.py | Admin Bulk Setup Wizard |
| 060 | 060_sprint34i_recommendation_rules.py | Automation/Recommendation Rules Engine |
| 061 | 061_sprint34j_customer_booking_drafts.py | Customer Booking Drafts (unified cross-flow) |
| 062 | 062_fix_schema_gaps.py | Fix: brands.description + service_packages table |
| 063 | 063_fix_commerce_schema_gaps.py | Fix: wallet/deposit/commission columns |
| 064 | 064_fix_jobs_bookings_invoices_schema_gaps.py | Fix: jobs/bookings/invoice_records columns (sprints 6-9) |
| 065 | 065_fix_catalog_schema_gaps.py | Fix: master_services/pricing_tiers/service_types columns |
| 066 | 066_dynamic_pricing_fields.py | Dynamic pricing fields on master_services |
| 067 | 067_pricing_service_fields.py | Service-level fields on city_tier_configs |
| 068 | 068_universal_category_service_groups.py | Universal Category Foundation: service_groups table |
| 069 | 069_fix_users_missing_columns.py | Fix: users columns missing vs ORM |
| 070 | 070_package_signup_fields.py | Signup/public fields on service_packages |
| 071 | 071_package_features_limits.py | package_features + package_limits tables |
| 072 | 072_tenant_package_assignments.py | tenant_package_assignments (admin-approval gating) |
| 073 | 073_package_audit_logs.py | package_audit_logs table |
| 074 | 074_issue_type_mapping_enhancements.py | customer_visible + severity_override on service_issue_mappings |
| 075 | 075_dispute_settlement_engine.py | Dispute/Settlement Engine SLA columns |
| 076 | 076_types_brands_enterprise.py | Types & Brands Enterprise Upgrade |
| 077 | 077_pricing_enterprise_upgrade.py | Pricing Enterprise Upgrade |
| 078 | 078_finance_enterprise_upgrade.py | Finance Hub Enterprise Upgrade |
| 079 | 079_compliance_enterprise_upgrade.py | Compliance Enterprise Upgrade (DPDP Act 2023) |
| 080 | 080_customer_service_credit_dispute_settlement.py | Customer Service Credit + Dispute Settlement Engine |
| 081 | 081_enterprise_engine_management.py | Platform-level engine registry + governance tables |
| 082 | 082_category_engine_matrix_governance.py | Category Engine Matrix Governance |
| 083 | 083_platform_users_governance.py | platform_role, access_scope, invited_by on users |
| 084 | 084_security_enterprise_upgrade.py | Threats/Sessions/IP Blocklist/API Keys/Audit/Policies |
| 085 | 085_media_library_enterprise.py | Media Library Enterprise Upgrade |
| 086 | 086_workflow_templates_enterprise.py | Workflow Templates Enterprise Upgrade |
| 087 | 087_fix_master_data_audit_log_updated_at.py | Fix: missing updated_at on master_data_audit_log |
| 088 | 088_settings_enterprise_upgrade.py | Platform Settings Enterprise Upgrade + feature_flags |
| 089 | 089_multi_vertical_catalog_architecture.py | Multi-Vertical Catalog Architecture (4 tables, 7 verticals) |
| 090 | 090_vertical_catalog_module_fix.py | Vertical-specific catalog modules + engine mappings; scoped `DELETE FROM vertical_catalog_modules`/`catalog_module_definitions` re-seed guards |
| 091 | 091_fix_vertical_catalog_updated_at.py | Fix: updated_at on catalog_module_definitions / vertical_catalog_modules |
| 092 | 092_booking_credit_applied_fields.py | Fix: customer-credit-to-booking integration |
| 093 | 093_job_credit_applied_fields.py | Job Completion + Usage Credit Deduction Verification |
| 094 | 094_payment_records_job_fields.py | Fix: missing job-payment columns on payment_records |
| 095 | 095_trust_quality_engine.py | P0 Trust & Quality Engine data model; scoped `DELETE FROM engine_dependencies/platform_engines WHERE engine_key IN (...)` re-seed guard |
| 096 | 096_navigation_duplicate_cleanup.py | Sidebar dedupe: Home Services vertical catalog modules |
| 097 | 097_service_setup_templates_enterprise.py | Service Setup Templates Enterprise |
| 098 | 098_service_setup_bulk_wizard.py | Service Setup Bulk Wizard |
| 099 | 099_admin_bulk_setup_runs_updated_at.py | Fix: updated_at on bulk setup run tables |
| 100 | 100_marketing_command_center.py | Marketing Automation Command Center |
| 101 | 101_fix_template_versions_updated_at.py | Fix: updated_at on template version/usage tables |
| 102 | 102_notification_template_center.py | P0 Enterprise Notification Template Center |
| 103 | 103_intelligence_command_center.py | Intelligence Command Center (8 tables) |
| 104 | 104_kb_enterprise.py | Knowledge Base Enterprise (8 tables) |
| 105 | 105_dashboard_command_center.py | Platform Command Center Dashboard |
| 106 | 106_workflow_templates_enterprise.py | Workflow Templates Enterprise (standalone tables); downgrade drops workflow_* tables |
| 107 | 107_dpdp_compliance_command_center.py | P0 DPDP Compliance Command Center |
| 108 | 108_fix_bulk_validation_updated_at.py | Fix: updated_at on service_setup_bulk_validation_results |
| 109 | 109_master_checklist_items.py | master_checklist_items table |
| 110 | 110_fix_checklist_module_admin_path.py | Fix: checklist_templates module admin_path |
| 111 | 111_pricing_completed_job_deduction.py | completed_job_deduction_credits column |
| 112 | 112_package_audit_request_id.py | request_id column on package_audit_logs |
| 113 | 113_provider_team_members.py | provider_team_members table |
| 114 | 114_provider_availability_rules.py | provider_availability_rules table |
| 115 | 115_provider_status_offerings_tables.py | provider_visibility_statuses etc. |
| 116 | 116_bargain_customer_range_platform_fee.py | Bargain Module: Customer Range + Platform Fee Floor |
| 117 | 117_service_coverage_primary_area_plan_limit.py | Service Coverage: Primary Area + Plan limit |
| 118 | 118_home_services_catalog_console_brand_behavior.py | Admin Catalog Setup Console: brand pricing behavior |
| 119 | 119_tenant_home_services_setup_pricing.py | Tenant Setup Wizard: per-type/brand price range |
| 120 | 120_type_dependent_brand_pricing.py | Type-Dependent Brand Pricing |
| 121 | 121_hs5b_availability_exceptions_booking_window.py | Availability break/lunch + exceptions/holidays |
| 122 | 122_hs7_fix_draft_event_updated_at.py | Fix: updated_at on home_service_booking_draft_events |
| 123 | 123_hs7_fix_confirmation_updated_at.py | Fix: updated_at on customer_booking_confirmations |
| 124 | 124_hs7_fix_audit_log_updated_at.py | Fix: updated_at on final_creation_audit_log |
| 125 | 125_hs7_fix_assignment_events_updated_at.py | Fix: updated_at on service_job_assignment_events |
| 126 | 126_hs8_fix_execution_events_updated_at.py | Fix: updated_at on service_job_execution_events |
| 127 | 127_hs8_fix_media_uploads_updated_at.py | Fix: updated_at on service_job_media_uploads |
| 128 | 128_hs8b_parts_requests_completion_data.py | Parts Approval + Completion Proof |
| 129 | 129_hs9_usage_credit_ledger.py | Usage Credit Ledger + Completed Job Deduction |
| 130 | 130_bookability_audit_logs.py | bookability_audit_logs table |
| 131 | 131_admin_e2e06_report_runs_updated_at.py | Fix: updated_at on report_runs table (latest / HEAD) |

**Risk flags:** None of the 124 migrations contain unscoped destructive SQL. The five files
matching `DELETE FROM` / `DROP TABLE` patterns (016, 031, 090, 095, 106) all scope the
statement to specific rows (`WHERE tenant_id IS NULL AND channel=...`, `WHERE engine_key IN
(...)`, `WHERE key = ANY(:keys)`) or to tables the same migration itself created (idempotent
re-run guards / `downgrade()` drops), not to production data at large.

## 2. Seed Scripts

`scripts/seed_*.py` (15 files) plus one non-`seed_`-prefixed reset script found in `scripts/`:

| Script | Classification | Notes |
|--------|-----------------|-------|
| scripts/seed_ac_repair_baseline_mappings.py | CANONICAL_SEED | AC/repair baseline issue-type mappings |
| scripts/seed_ai_prompt_templates.py | CANONICAL_SEED | AI prompt template defaults |
| scripts/seed_brands.py | CANONICAL_SEED | 25 starter brands (per Sprint 34D memory) |
| scripts/seed_checklists.py | CANONICAL_SEED | Checklist templates |
| scripts/seed_customer_flows.py | CANONICAL_SEED | Customer flow configs (Sprint 14) |
| scripts/seed_demo_packages.py | E2E_SEED | "demo" in name — package data for demo/test tenants |
| scripts/seed_demo_users.py | E2E_SEED | "demo" in name — demo login users (referenced in project_login_fix memory) |
| scripts/seed_issue_types.py | CANONICAL_SEED | 36 issue-type seeds (P0 Issue Types fix) |
| scripts/seed_master_services.py | CANONICAL_SEED | Master service catalog |
| scripts/seed_phase0_baseline.py | ONE_TIME_REPAIR | "phase0_baseline" — one-time baseline bootstrap, not part of ongoing catalog seeding |
| scripts/seed_recommendation_rules.py | CANONICAL_SEED | 10 seeded automation rules (Sprint 34I) |
| scripts/seed_service_groups.py | CANONICAL_SEED | Service groups |
| scripts/seed_service_options_issues.py | CANONICAL_SEED | 8 groups / 21 options / 29 issues (Sprint 34E) |
| scripts/seed_service_setup_templates.py | CANONICAL_SEED | 6 starter setup templates (Sprint 34F) |
| scripts/seed_universal_categories.py | CANONICAL_SEED | 7 verticals + categories |
| scripts/serviceos_reset_dev_data.py | **DANGEROUS_RESET** | Name explicitly says "reset_dev_data" — intended for dev-environment data reset. Not run by this audit. |
| scripts/cleanup_emergency_availability_preset.py | ONE_TIME_REPAIR | Targeted cleanup of one preset, not a general reset |
| scripts/cleanup_home_services_test_state.py | TEST_FIXTURE | Cleans test-only state for Home Services flows |
| scripts/cleanup_test_data.py | TEST_FIXTURE | Generic test-data cleanup helper |
| scripts/migrate_type_dependent_brand_pricing.py | ONE_TIME_REPAIR | One-off data migration companion to migration 120 |

**Embedded seed logic inside migrations** (grepped for `INSERT INTO` / `bulk_insert` /
`op.execute(...INSERT...)` across `alembic/versions/`): 13 files contain in-migration inserts —
002, 014, 016, 042, 043, 045, 080, 081, 084, 089, 090, 095, 100. These are all CANONICAL_SEED-
style bootstrap data tied to the schema they create (e.g. default notification templates in
016, default engines in 081/095, default verticals in 089) and are the standard pattern used
throughout this codebase (seed-at-migration-time for reference/lookup data). None contain
unscoped deletes of pre-existing rows beyond the guarded cases noted in Section 1.

**No DANGEROUS_RESET scripts found under the `scripts/seed_*.py` naming convention itself** —
the one DANGEROUS_RESET item (`serviceos_reset_dev_data.py`) is a separate, clearly-named
top-level script, not disguised as a seed script.

## 3. Known Legacy Drift

### `tenant_billing.credit_balance` vs `TenantWallet`/`customer_credit_balances`
- `tenant_billing.credit_balance` (Numeric(12,2)) was introduced in migration `014_phase14_billing_router.py`
  and lives in `app/engines/tenant_engine/models.py`. A docstring on the co-located
  `UsageCreditLedger` model (HS9, migration 129) explicitly states:
  *"credit_balance (the pre-existing, real canonical balance field) must create one of these
  rows. Not money — internal platform credits only."* This confirms `tenant_billing.credit_balance`
  is the **intentional, still-canonical** field for internal usage credits — not legacy drift,
  but it is easy to confuse with the money-bearing `tenant_wallets.credit_balance` below.
- `TenantWallet` (`app/engines/platform_commerce/models.py`, table `tenant_wallets`, from
  migration 003) has its own `credit_balance` (Numeric(14,4), real money, wallet ledger backed
  by `WalletTransaction`). `wallet_service.py`'s docstring calls it "the existing
  tenant_wallets/wallet_transactions" system, confirming this is the money wallet, separate in
  purpose from `tenant_billing.credit_balance`'s internal platform credits.
- A third, distinct field `customer_credit_balances.credit_balance` (also in
  `platform_commerce/models.py`, from Sprint P0 Customer Service Credit migration 080) tracks
  customer-facing (not tenant-facing) credit for dispute/refund settlements.
- **Conclusion:** three same-named `credit_balance` columns exist across three tables
  (`tenant_billing`, `tenant_wallets`, `customer_credit_balances`) with different owners, units,
  and purposes. None appear to be dead/superseded — each has an active, distinct consumer
  service (tenant billing, provider wallet payouts, customer refunds) — but the naming
  collision is a real drift/confusion risk for future maintainers and should be flagged for a
  documentation or naming pass, not a schema fix.

### `jobs` (Field Ops / legacy) vs `service_jobs` (canonical Home Services)
- `app/engines/field_ops/models.py` defines `class Job` → table `jobs`, introduced in migration
  `008_phase8_geo_dispatch_fieldops.py` (Phase 8, very early in the schema's history).
- `app/engines/final_records/models.py` defines `class ServiceJob` → table `service_jobs`,
  introduced in migration `037_sprint19_final_records.py` (Sprint 19, "Booking Confirmation →
  Final Record Creation") — this is the modern, actively used Home Services job record, and is
  the table extended by nearly every subsequent HS-prefixed migration (093, 111, 121–130).
- This exact duplication is independently confirmed by
  `G:\serviceos\ADMIN_TENANT_E2E_04B_LEGACY_OPERATIONS_BRIDGE_REPORT.md` at the repo root, which
  documents that `/admin/operations` (the legacy Field Ops board, backed by table `jobs`) was
  found empty and confusing to admins, and was fixed by adding a persistent UI banner
  explaining: *"This board shows Field Ops (legacy) jobs, a separate lifecycle from Home
  Services bookings... View real Home Services Jobs →"* linking to
  `/admin/home-services/service-jobs` (backed by `service_jobs`).
- **Conclusion:** `jobs` (Field Ops) is a real, still-mounted legacy module — not deleted, not
  migrated — that has been superseded in practice by `service_jobs` for all Home Services
  vertical activity. The bridge report treats this as an intentional, accepted state (kept
  visible with an explanatory banner) rather than something requiring a migration/backfill.
  No further schema action was taken or is recommended here; this section only records the
  finding for the inventory.

### Notification template models
- `app/engines/notification/models.py` defines three related classes: `NotificationTemplate`,
  `NotificationTemplateVersion`, `NotificationTemplateAuditLog` — all introduced/extended across
  migrations `005` (Phase 5, initial notification tables), `016` (Phase 16, platform-default
  in_app template seed), and `102_notification_template_center.py` (P0 Enterprise Notification
  Template Center, which added versioning/audit-log tables). No duplicate/competing
  `notification_templates`-like table was found elsewhere in `app/engines/*/models.py` — this
  is a single, cleanly-evolved lineage (base table → versioning → audit log), not drift.

### `tenant_wallets`
- Single canonical definition in `platform_commerce/models.py` (table `tenant_wallets`,
  migration 003), consumed by `wallet_service.py` (Sprint 23) with no competing table found.
  Not drift.

## Summary Table

| Metric | Value |
|---|---|
| Total migrations | 124 |
| Migration chain | Single root (001) → single head (131), no branches, no dangling references |
| Filename gap | 024–030 (absorbed into 031 stub; chain itself is unbroken) |
| Seed scripts (scripts/seed_*.py) | 15 (12 CANONICAL_SEED, 2 E2E_SEED, 1 ONE_TIME_REPAIR) |
| Other scripts/*.py reviewed | 5 (1 DANGEROUS_RESET, 2 TEST_FIXTURE, 2 ONE_TIME_REPAIR) |
| Migrations with embedded INSERT/seed logic | 13 |
| Migrations with scoped DELETE/DROP (non-destructive to prod data) | 5 |
| DANGEROUS_RESET scripts found | 1 — `scripts/serviceos_reset_dev_data.py` (not executed) |
| Legacy drift items documented | 3 credit_balance columns (distinct, active, name-collision risk); `jobs` vs `service_jobs` (documented, intentional legacy retention); notification templates (clean lineage, no drift) |
