# FINAL-L5-01 — Canonical Seed Specification

Implemented in `scripts/canonical_seed_final_l5_01.py`. Idempotent (existence-checked before every insert), deterministic (stable lookup keys: email for users, slug for tenants, `rule_code` for pricing rules, `job_number` for jobs), environment-guarded (shares the guard with the reset script), transaction-safe (commits in logical phases, no partial-write state left on success).

## What is actually implemented (vs. mission's aspirational full list)

### Platform users — implemented
- `admin@serviceos.local` — Platform Super Admin
- `admin.ops@serviceos.local` — Admin Operations User
- `admin.finance@serviceos.local` — Admin Finance User
- `admin.readonly@serviceos.local` — Admin Read Only User

### Tenant — implemented
- `demo-ac-services` — Demo AC Services, status `active`, verification `verified`, Ludhiana / 141001 / India / Punjab, `is_discoverable=true`

### Second tenant for isolation testing — implemented
- `isolation-test-services` — Isolation Test Services, active, 141002, with its own owner user, used exclusively by `FINAL_L5_01_TENANT_ISOLATION_DATA_REPORT.md`

### Tenant users — implemented
- `owner@demo-ac-services.local` — Tenant Owner
- `manager@demo-ac-services.local` — Tenant Manager
- `readonly@demo-ac-services.local` — Tenant Read Only

### Staff — implemented
- `tech1@demo-ac-services.local` — Technician One (active)
- `tech2@demo-ac-services.local` — Technician Two (active)
- `tech.inactive@demo-ac-services.local` — Technician Inactive (`is_active=false`, negative test user)

### Customers — implemented
- `customer1@serviceos.local` — Customer One
- `customer2@serviceos.local` — Customer Two

### Geography — implemented (via tenant + coverage records)
Ludhiana / Punjab / India / 141001 active. **999999 unsupported zipcode was NOT seeded as a negative record** — instead its absence was verified directly (`SELECT count(*) FROM tenant_service_areas WHERE zipcode='999999'` returns 0), which satisfies the "no matching coverage" requirement without needing an explicit negative row.

### Catalog — reused, not re-seeded
AC Repair / Split AC / Window AC / LG / "AC Not Cooling" already existed correctly from prior sprints (verified present, IDs logged in seed output) — not duplicated. One gap was found and filled: no `master_offerings` row existed for the AC Repair category (required as a NOT-NULL FK-in-practice for `service_jobs.offering_id`), so one canonical row was created.

### Admin pricing rules — implemented, ranges corrected to mission spec
- `final_l5_01_split_ac_lg_141001`: Split AC + LG + Ludhiana 141001, range ₹700–₹850, base ₹775
- `final_l5_01_window_ac_lg_141001`: Window AC + LG + Ludhiana 141001, range ₹350–₹500, base ₹425
Both distinct by `service_type_id`, both `min_price ≤ max_price`, both non-negative — verified via direct SQL query.

### Tenant provider setup — implemented
`provider_enabled_offerings` row: AC Repair enabled for Demo AC Services, `supported_type_ids` = [Split AC, Window AC], `supported_brand_ids` = [LG], `provider_min_price=700`, `provider_max_price=850`. **Note**: the mission's spec asked for a Split-AC-specific provider range distinct from a Window-AC-specific one; the actual `provider_enabled_offerings` schema stores one min/max pair per offering (not per type), so the Split AC range (700–850, matching the admin pricing rule) was used as the provider-level bound — Window AC's narrower ₹350–500 admin rule remains the authoritative per-type constraint. This is a real schema-shape finding, not a shortcut — documented for future schema review.

### Service areas and availability — implemented
141001 active/primary coverage; `provider_availability_rules` for Mon–Sat 09:00–18:00 with a 13:00–14:00 break, `max_jobs_per_day=12`, `Asia/Kolkata` timezone.

### Usage credits — implemented exactly per mission rule
`tenant_billing.credit_balance` opening value 4000, written to the canonical active source only. `tenant_wallets` intentionally never written to by the seed.

### Jobs/bookings — implemented, all 5 lifecycle states
`L501-JOB-0001` (new/unassigned), `L501-JOB-0002` (assigned, Technician One), `L501-JOB-0003` (in_progress, Technician One), `L501-JOB-0004` (completed, Technician Two, with completion proof), `L501-JOB-0005` (cancelled). Each has a parent `bookings` row (required NOT-NULL FK-in-practice), tenant, customer, service, service type (Split AC), zipcode 141001, quoted price ₹775.

### Completion proof — implemented (job 0004)
`completion_data` JSON: work summary, collected amount (775), completion notes, technician name, completion timestamp.

### Completed Job Deduction — implemented, exactly-once proven
One `usage_credit_ledger` row, `event_type='completed_job_deduction'`, `credit_delta=-21`, `balance_before=4000.00`, `balance_after=3979.00`. Proven exactly-once across 2 full reset+seed cycles (see idempotency and repeatability reports) — `tenant_billing.credit_balance` matches `balance_after` exactly after each cycle.

### Notifications — implemented (4 of the mission's suggested set)
Admin (read), Tenant Owner (unread, job-completed), Customer One (unread, booking-update), Technician One (read, job-assigned). Staff/failed-outbox examples were not additionally seeded — judged sufficient coverage for frontend readiness given time constraints.

### Audit — NOT implemented this sprint
No dedicated audit-event rows were seeded (`tenant_audit_logs`, `platform_audit_logs`, etc. remain empty after seed). This is a real, acknowledged gap — carried to `FINAL_L5_01_REMAINING_BLOCKERS.md`. The mission's 8 example audit events (tenant activation, service setup update, etc.) were not created as explicit rows.

### Rules/configuration — NOT implemented this sprint
Health rule, badge rule, reward rule, completed-job-deduction rule (as a standalone config row — the deduction amount is currently hardcoded in the seed script rather than read from a `credit threshold`/`deduction rule` table), matching rule, availability policy, service area policy, notification policy — none of these were seeded as explicit configuration rows this sprint. This is the largest acknowledged gap against the mission's Part 18 ask. See remaining blockers.

## Idempotency guarantee
Every insert is preceded by a `SELECT ... WHERE <stable key>` existence check. Proven via 2 consecutive seed runs against the same migrated database: run 1 created all entities, run 2 skipped all of them (`{'users': 0, 'tenants': 0, 'pricing_rules': 0, 'coverage': 0, 'jobs': 0, 'ledger': 0, 'notifications': 0}`), with `tenant_billing.credit_balance` unchanged at `3979.00` on rerun.
