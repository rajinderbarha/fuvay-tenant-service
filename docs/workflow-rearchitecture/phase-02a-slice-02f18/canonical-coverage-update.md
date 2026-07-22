# Canonical Coverage Update

## Starting baseline
190 protected / 226 total tenant-facing mutations (confirmed globally by
Slice 2F-17A's full-application sweep).

## This slice's row-level reconciliation
All 10 rows for `app.engines.platform_notifications.provider_router` in
`tenant-mutation-endpoint-inventory.csv` were previously `UNVERIFIED`
(`get_current_user` only). All 10 are confirmed genuine tenant/provider
mutations (not customer, not platform-admin, not false positive — proven
by the full route inventory in `provider-router-final-route-inventory.csv`)
and are now protected:

| endpoint_name | previous guard_status | new guard_status |
|---|---|---|
| provider_mark_read | UNVERIFIED | TENANT_MUTATION_ROLE_SCOPE_AWARE |
| provider_mark_all_read | UNVERIFIED | TENANT_MUTATION_ROLE_SCOPE_AWARE |
| provider_update_pref | UNVERIFIED | TENANT_MUTATION_ROLE_SCOPE_AWARE |
| provider_create_thread | UNVERIFIED | TENANT_MUTATION_ROLE_SCOPE_AWARE |
| provider_send_message | UNVERIFIED | TENANT_MUTATION_ROLE_SCOPE_AWARE |
| provider_mark_thread_read | UNVERIFIED | TENANT_MUTATION_ROLE_SCOPE_AWARE |
| staff_mark_read | UNVERIFIED | STAFF_EXECUTION_ROLE_SCOPE_AWARE |
| staff_mark_all_read | UNVERIFIED | STAFF_EXECUTION_ROLE_SCOPE_AWARE |
| staff_send_message | UNVERIFIED | STAFF_EXECUTION_ROLE_SCOPE_AWARE |
| staff_mark_thread_read | UNVERIFIED | STAFF_EXECUTION_ROLE_SCOPE_AWARE |

## Final tenant numerator/denominator
**Denominator unchanged: 226.** No row was added, removed, or reclassified
as non-tenant — these 10 were already correctly counted as tenant/provider
mutations in the CSV, only their `guard_status` was stale.

**Numerator: 190 → 200 (+10).**

## Customer/platform exclusions unchanged
`customer_router.py`'s 12 routes remain outside this tenant-only CSV
(Design A) — they were never in the 226 denominator and still aren't; only
their guard dependency changed (`require_customer`), which does not affect
the tenant CSV's row count.

## Both canonical CSVs recount identically
`tenant-mutation-endpoint-inventory.csv`: 226 rows, 200 protected (row-level
count, `test_canonical_totals`).
`mutation-enforcement-matrix.csv`: `app.engines.platform_notifications.provider_router`
row updated to `10 total, 10 fully_protected (100%)` — consistent with the
row-level CSV under its own (whole-router, not tenant-only) convention.

## Remaining module count
36 - 10 = **26 unprotected tenant/provider mutation routes remain**, across
the 10 non-selected modules already ranked in
`docs/workflow-rearchitecture/phase-02a-slice-02f17a/application-wide-module-queue.csv`.
See `remaining-module-queue-update.csv` for the updated queue.
