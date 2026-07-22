# Slice 2F-17 — Implementation Summary

## Mission
Reconcile the remaining canonical tenant-facing mutation inventory after the approved 186/227 baseline, and select exactly one module for the next implementation slice (2F-18). This is a DISCOVERY slice — no application authorization code was modified.

## What was found
Row-level runtime recount of the 41 previously-unprotected rows found:
- **1 confirmed false positive** (`preview_matching_inputs`) — already exempted in the runtime tool since Slice 2F-2, but the canonical CSV row was stale. Removed.
- **4 already-protected rows** (`invoice_payment.provider_router`'s 4 invoice routes) — fixed in Slice 2F-6A, but the canonical CSV `guard_status` was never updated. Reclassified.
- **36 genuinely unprotected rows** across 11 modules — confirmed via fresh `--verify-module` runtime introspection, unchanged.

## Coverage reconciliation
```
Previous: 186 protected of 227
+4 (invoice_payment reclassified) -1 (false positive removed)
Reconciled: 190 protected of 226
```
36 remaining unprotected tenant-facing mutation routes, grouped into 11 coherent modules.

## Module selection
**Selected: `app.engines.platform_notifications.provider_router`** (10 mutation routes — provider + staff chat/notifications). Selected as the sole `CRITICAL`-severity remaining module: zero authorization (`get_current_user` only, no role/permission/ownership check) across all 10 routes, admitting literally any authenticated account regardless of role or tenant, on a core always-on business-communication surface. Manageable scope (one file, one engine), no blocking product decision, directly transferable fix pattern from `quote_checklist`'s identical structural precedent (Slice 2F-16).

The remaining 10 modules (26 routes) are ranked in `non-selected-module-queue.csv`, every route accounted for exactly once.

## Test results
- 1 test updated (`test_canonical_totals` → 226/190), passing.
- Full regression sweep: 1032 passed, 3 skipped, 0 failed (live-environment tests excluded, reported separately).
- 11 genuinely-unprotected modules confirmed exit 1 at runtime (expected); 2 reclassified modules confirmed exit 0.
- `field_ops.router` (28/28), `field_ops.staff_router` (6/6), `booking.router`, and `quote_checklist`'s 3 routers all unaffected, re-confirmed.

## Final status
`NEXT_MODULE_SELECTED_COVERAGE_RECONCILED` — see `approval-gate.md`.
