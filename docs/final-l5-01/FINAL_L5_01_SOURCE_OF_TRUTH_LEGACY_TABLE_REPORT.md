# FINAL-L5-01 — Legacy Table and Source-of-Truth Review

## Required known decisions (confirmed this sprint)

| Decision | Status |
|---|---|
| Usage credits: `tenant_billing` + `usage_credit_ledger` | **CONFIRMED ACTIVE** — canonical seed writes only here; verified `credit_balance` matches ledger `balance_after` |
| Dormant finance: `tenant_wallets` | **CONFIRMED DORMANT** — table exists (12 columns, has its own `credit_balance` column which is a naming collision risk worth flagging), never written to by the canonical seed, and the FINAL-L5-00 DB inventory previously confirmed no active endpoint consumes it for bookability/finance decisions |
| Home Services jobs: `service_jobs` | **CONFIRMED CANONICAL** — all 5 canonical job scenarios seeded here |
| Admin canonical jobs route: `/admin/home-services/service-jobs` | **NOT FOUND** — this route does not exist in the live backend (`openapi.json` confirms 404). The actual admin job-related routes are `/v1/admin/service-job-assignments`, `/v1/admin/service-job-assignments/unassigned`, `/v1/admin/service-job-assignments/assigned`, `/v1/admin/service-jobs/{job_id}/assignment-timeline`. This is a real discrepancy between the mission's assumed route and the live system — documented rather than silently assumed correct. See remaining blockers. |

## Other legacy structures inspected

| Structure | Decision |
|---|---|
| `jobs` (separate from `service_jobs`) | READ_ONLY_LEGACY — exists as a distinct table (Field Ops/legacy operations, per FINAL-L5-00's DB inventory finding of a `jobs` vs `service_jobs` split); not written to or read from by this sprint's seed |
| `tenant_wallets` vs `tenant_billing` | Both confirmed to have independently-named `credit_balance` columns — a genuine naming collision risk for future engineers; `tenant_billing.credit_balance` is authoritative, `tenant_wallets.credit_balance` must never be read as if it were the active balance |
| `notification_templates` vs `notif_event_templates` vs `notification_template_versions` | Multiple notification-template-shaped tables exist (identified via `information_schema` scan: `notification_templates`, `notif_event_templates`, `notification_template_versions`, `notification_template_audit_logs`) — not consolidated or deduplicated this sprint; REVIEW_REQUIRED, carried forward as a duplicate-model finding consistent with FINAL-L5-00's dead-code/duplicate-code scan |
| Old pricing tables | `service_pricing_rules` is the canonical, actively-written table this sprint; no separate legacy pricing table was found or touched |
| Old coverage tables | `tenant_service_areas` used as canonical; `service_areas` (referenced in the mission's own text) does not exist as a table in this schema — confirmed via `information_schema` scan returning 0 columns for that name |
| Old user/role tables | Single `users` table with a free-text `role`/`platform_role` column pair; no separate `roles`/`permissions`/`principals` tables found in this schema despite the mission listing them as things to pay attention to — role modeling in this system is simpler (denormalized) than the mission assumed |

## The ~190-table missing-FK finding (cross-reference)
Not a "legacy table" in the traditional sense, but belongs in this report's spirit: the vast majority of tenant-scoped tables lack FK constraints to `tenants(id)` (see schema inventory report). Classification: **REVIEW_REQUIRED** — this is a schema hardening item for a future migration-authoring sprint, not something to fix via ad-hoc SQL in a data-seeding sprint. No table was dropped or altered this sprint.
