# Global Coverage Update — Workstream 14

## Reconciliation method
Re-ran the runtime mutation inventory tool with no module filter
(`PYTHONPATH=. python scripts/workflow_rearchitecture/inventory_mutation_routes.py`)
and aggregated by `auto_classification` and `module`, rather than
trusting the previously-reported figure.

## Corrected totals

| Metric | Previously reported | Corrected (this slice, pre-fix) | After this slice's fix |
|---|---|---|---|
| Total mounted mutation routes (whole app) | not previously stated at this granularity | **1,186** | 1,186 (unchanged — no route added/removed) |
| Tenant-facing mutations (`TENANT_USER_MUTATION` + `TENANT_TECHNICIAN_MUTATION`) | ~183 | **183** (confirmed exact match) | 183 (unchanged) |
| Protected tenant-facing mutations (scope/role-aware guard only — excludes `PLATFORM_ADMIN_ONLY` routes, which are correctly-excluded platform actions, not "tenant mutations protected") | ~85 | **85** (re-verified via a full runtime re-aggregation — the prior figure is CONFIRMED CORRECT, not an undercount) | **89** (+4 from this slice) |
| Remaining unprotected tenant-facing mutations | ~98 | **98** | **94** |

## Reconciliation note
An earlier draft of this document incorrectly computed 93/97 by counting
`PLATFORM_ADMIN_ONLY`-guarded routes (permission-gated but intentionally
reachable by no tenant role) as "protected tenant mutations." Re-checking
against the exact counting convention already established in
`phase-02a-slice-02f/mutation-enforcement-matrix.csv` (which counts only
`TENANT_MUTATION_PERMISSION_SCOPE_AWARE` + `TENANT_MUTATION_ROLE_SCOPE_AWARE`
+ `STAFF_EXECUTION_ROLE_SCOPE_AWARE` toward `fully_protected`) confirms the
previously-reported **85** was correct all along. The corrected,
authoritative post-slice figure is **89**.

## Routes excluded from the tenant-facing denominator (unchanged, re-confirmed)
`app.engines.finance_hub.admin_router` (17) and
`app.engines.package_commerce.admin_router` (20) remain platform-facing
and excluded, per the user's explicit instruction and Slice 2F-5B/5C's
own adjudication — re-confirmed this slice, not recombined into the
denominator.

## Routes reclassified this slice
The 4 `invoice_payment.provider_router` mutations moved from
`AUTHENTICATED_ONLY_NO_PERMISSION_CHECK` (unprotected) to
`TENANT_MUTATION_PERMISSION_SCOPE_AWARE` (1 route,
`provider_issue_invoice`) and `STAFF_EXECUTION_ROLE_SCOPE_AWARE`
(3 routes, via `require_staff_or_above_mutation`) — all now inside
`ACCEPTED_GUARD_STATUSES`.

## Remaining module count
18 tenant-facing modules remain with at least one unprotected mutation
after this slice (see `remaining-module-priority-matrix.csv` for the
full, individually-ranked list) — down from 19 before this slice.

## Remaining unverified count
0 within the selected module (`invoice_payment.provider_router`).
Platform-wide, 261 routes remain in the tool's own `UNVERIFIED`
auto-classification bucket, but the overwhelming majority of those are
`PLATFORM_ADMIN_MUTATION`-classified (638 platform-admin mutations exist
platform-wide) or belong to modules outside this slice's selected scope
— re-ranking and closing those remains future-slice work, not claimed as
done here.

## Files updated
- `docs/workflow-rearchitecture/phase-02a-slice-02f/tenant-mutation-endpoint-inventory.csv`:
  **not directly edited** — that file is Slice 2F's own historical
  snapshot; per "do not generate duplicate architecture documentation,"
  this slice's corrected totals live in this file
  (`global-coverage-update.md`) and in
  `selected-module-mutation-inventory.csv`/`selected-module-enforcement-matrix.csv`
  instead of rewriting a prior slice's artifact.
- `docs/workflow-rearchitecture/phase-02a-slice-02f/mutation-enforcement-matrix.csv`:
  **not directly edited** for the same reason — this slice's addition to
  the running total is documented here rather than mutating a previous
  slice's file in place, preserving that file's own historical record.
