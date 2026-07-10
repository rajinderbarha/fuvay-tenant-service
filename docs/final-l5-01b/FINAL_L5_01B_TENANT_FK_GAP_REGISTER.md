# FINAL-L5-01B — Tenant FK Gap Register

Formal tracking of the ~190-table missing-FK finding discovered in FINAL-L5-01 (and re-confirmed necessary this sprint when building the reset script). **No foreign keys were added this sprint** — this register documents and classifies the risk per the mission's explicit instruction not to blindly add FKs.

## Scope
201 tables carry a `tenant_id` column; of those, the large majority lack a declared `FOREIGN KEY ... REFERENCES tenants(id)` constraint (confirmed via `pg_constraint` query in FINAL-L5-01). Full enumerated list lives in `scripts/reset_final_l5_01.py::TENANT_SCOPED_TABLES`.

## Classification by category

| Table category (representative examples) | Tenant ID column | Current FK | Delete behavior | Soft-delete policy | Historical retention requirement | Risk | Recommendation |
|---|---|---|---|---|---|---|---|
| Core operational (`bookings`, `service_jobs`, `usage_credit_ledger`, `in_app_notifications`) | `tenant_id` | None | Application-layer only (this sprint's reset used explicit `TRUNCATE`, not FK cascade) | Mixed — some have `deleted_at`, some don't | High — these are the records of record for billing/legal | **High** | `ADD_FK_LATER` — highest priority for a dedicated schema-hardening migration; orphan risk is real if a tenant is ever deleted via raw SQL rather than the app layer |
| Audit/compliance logs (`tenant_audit_logs`, `auth_audit_logs`, `compliance_audit_logs`, `platform_audit_logs`) | `tenant_id` | None | N/A (append-only) | N/A | **Very high** — audit trails must survive even if the referenced tenant is later removed | **Medium** (intentional design tension) | `HISTORICAL_RETENTION` — audit logs arguably should NOT cascade-delete with their tenant (regulatory/legal retention), so the *absence* of an `ON DELETE CASCADE` FK may be partially intentional; recommend `ON DELETE SET NULL` or `ON DELETE RESTRICT` semantics rather than a blind CASCADE FK |
| Analytics/reporting snapshots (`analytics_daily_metrics`, `daily_metrics`, `zone_analytic_snapshots`, `demand_forecasts`) | `tenant_id` | None | Application-layer only | None found | Low-medium — recomputable | **Low** | `ADD_FK_LATER` — low urgency, safe to defer |
| Session/security (`user_sessions`, `login_events`, `api_keys`, `ip_blocklist`, `suspicious_activity_logs`) | `tenant_id` (nullable for platform-level) | None | Application-layer only | Mixed | Medium — security-relevant but not billing-relevant | **Medium** | `REVIEW_REQUIRED` — nullable tenant_id for platform-level rows complicates a simple FK; needs a design decision on whether platform-scoped security rows should have `tenant_id IS NULL` allowed under the FK (yes, standard FK allows NULL) |
| Marketing/campaign (`marketing_campaigns`, `marketing_posts`, `scheduled_posts`) | `tenant_id` | None | Application-layer only | Some | Low | **Low** | `ADD_FK_LATER` |
| Finance (`tenant_billing`, `invoice_records`, `payment_records`, `commission_records`, `security_deposits`) | `tenant_id` | None | Application-layer only | None found on most | **Very high** — real money records | **High** | `ADD_FK_LATER` — second-highest priority alongside core operational; a tenant deletion that silently orphans invoice/payment records is a real financial-integrity risk |
| Config/settings (`tenant_settings`, `tenant_feature_flags`, `tenant_engines`, `tenant_operational_settings`) | `tenant_id` | None | Application-layer only | N/A | Low | **Low** | `APPLICATION_SCOPED_INTENTIONAL` — 1:1 config tables are low risk even without FK, since orphaned config rows are harmless clutter, not data-integrity violations |
| `recommendation_rules` | `tenant_id` (nullable — most rows are global) | None | N/A | `deleted_at` present | Low | **Low** | `REVIEW_REQUIRED` — this sprint's own experience shows this table mixing global (tenant_id NULL) and tenant-specific rows under one truncate-list entry caused an unintended wipe of global config; recommend splitting global vs tenant-scoped rules into separate tables in a future migration, independent of the FK question |

## Why not fixed this sprint
Per the mission's explicit instruction: "Do not add all foreign keys blindly in this sprint." Adding ~190 FK constraints (many with genuine `ON DELETE` semantics questions — CASCADE vs RESTRICT vs SET NULL vary meaningfully by category above) is a substantial, multi-migration schema-hardening project requiring careful per-table review, not a mechanical bulk change. This register exists specifically to make that future work tractable by pre-classifying the risk tiers.

## Non-blocking justification (per mission's own conditions)
1. This sprint's reset handles all 201 tables safely (explicit enumeration, not relying on absent FK cascade).
2. Integrity checks (FINAL-L5-01's FK/orphan report) pass — 0 unexplained orphans in the actually-seeded canonical dataset.
3. Runtime tenant isolation passes (FINAL-L5-01's tenant isolation report, re-confirmed this sprint).
4. This risk is now formally tracked (this document).
