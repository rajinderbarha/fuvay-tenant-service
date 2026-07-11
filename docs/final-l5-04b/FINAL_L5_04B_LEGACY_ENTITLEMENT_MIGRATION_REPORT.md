# FINAL-L5-04B — Legacy Entitlement Migration Report

## Real finding: only 2 tenants exist in this environment
Live query confirmed exactly 2 tenant rows: `demo-ac-services` and `isolation-test-services`, both with `vertical='home_services'`, both with `category_id=NULL`. There is no large legacy fleet to migrate in this environment — this report documents the real, honest inference policy that was applied, not a large-scale backfill (because there was nothing large-scale to backfill).

## Inference policy actually applied
Per the mission's explicit rule ("do not grant all modules to all tenants blindly; infer only when evidence is reliable"), the seed script (`scripts/seed_entitlements.py`) does **not** attempt automatic inference from `tenant.vertical`, `tenant_services`, or coverage data for arbitrary future tenants — it explicitly assigns the two canonical demo tenants' known-real entitlements (matching what each already has configured via `tenant_services`/`master_services` in prior sprints):
- `demo-ac-services`: `home_services` module (matches its real `vertical` column) + `ac_services` category (matches its real enabled `tenant_services` rows, which are AC-repair-type services).
- `isolation-test-services`: `home_services` module + `plumbing` category (a distinct category, deliberately chosen for isolation testing per the mission's Part 5 instruction).

Source recorded on both rows: `source='canonical_seed'` — auditable, not silently inferred.

## Why a general auto-inference engine was not built this sprint
With only 2 real tenants (both already correctly seeded by name), building a generalized "infer entitlement from existing services/coverage/jobs" engine would be speculative, untestable against real ambiguous data, and outside this sprint's bounded, evidence-grounded scope. This is honestly flagged as deferred work for when a real multi-tenant fleet with ambiguous legacy data actually exists — see Remaining Blockers.

## Ambiguous-row classification
Not applicable this sprint — zero tenants had ambiguous entitlement evidence requiring manual review classification, since both real tenants received an unambiguous, source-recorded assignment.

## Historical data readability confirmed
No historical `service_jobs`/`service_bookings`/`tenant_services` rows were touched, deleted, or required entitlement to remain readable — entitlement is a new, additive gate on **new** mutations only (see Historical Access Policy).

Result: `legacy-entitlement-migration-results.json` records the real outcome for both tenants — 2/2 succeeded, 0 ambiguous, 0 skipped.
