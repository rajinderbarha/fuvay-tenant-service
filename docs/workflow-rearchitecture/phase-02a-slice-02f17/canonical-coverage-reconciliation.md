# Canonical Coverage Reconciliation

## Starting baseline
**186 protected of 227** tenant-facing mutations (approved at Slice 2F-16A).

## Row-level recount of the 41 previously-unprotected rows
See `remaining-tenant-mutation-routes.csv` for the complete row-by-row disposition. Summary:
- **1 false positive** (`preview_matching_inputs`, `app.engines.provider_portal.router`) — already exempted in the runtime tool's `CONFIRMED_FALSE_POSITIVE_ROUTES` since Slice 2F-2, but the canonical CSV row was never removed. Removed this slice.
- **4 already-protected, misclassified rows** (`provider_issue_invoice`, `provider_record_payment`, `staff_create_invoice`, `staff_add_invoice_item` — all `app.engines.invoice_payment.provider_router`) — fixed in Slice 2F-6A, but the CSV `guard_status` was never updated. Reclassified this slice.
- **36 genuinely unprotected rows** across 11 modules — confirmed via fresh runtime introspection (`runtime-route-reconciliation.csv`), unchanged.

## Mathematical reconciliation
```
Previous protected numerator:               186
+ newly discovered already-protected rows:   +4   (invoice_payment.provider_router)
- incorrectly counted protected rows:         -0   (none found -- no row previously counted as
                                                     protected was actually unprotected)
= reconciled numerator:                      190

Previous tenant denominator:                227
+ missing mounted tenant routes:              +0   (none found within the 11 modules audited
                                                     this slice -- see missing-runtime-route-audit.csv
                                                     for the honest scope disclosure on full-app coverage)
- false positives:                            -1   (preview_matching_inputs)
- customer routes:                            -0   (none of the 41 rows were customer-reachable)
- platform routes:                            -0   (none of the 41 rows were platform-only)
- duplicates:                                 -0   (none found)
- disconnected routes:                        -0   (none found)
= reconciled denominator:                    226
```

## Final reconciled figures
**190 protected of 226 tenant-facing mutations.**

| Category | Count |
|---|---|
| Protected tenant routes | 190 |
| Unprotected tenant routes | 36 |
| Customer mutation count (quote_checklist + booking, tracked separately, unchanged) | 3 (booking) + 3 (quote_checklist) = 6 |
| Platform/internal mutation count (booking + quote_checklist, tracked separately, unchanged) | 1 (booking) + 2 (quote_checklist) = 3 |
| Admin-platform mutation count | included in the platform/internal figures above — no separate admin-platform inventory exists distinct from platform/internal in this codebase's current convention |
| False-positive count (this slice) | 1 (removed) |
| Duplicate count | 0 |
| Disconnected count | 0 |
| Unverified count (remaining) | 36 |

## Both canonical CSVs recount identically
`tenant-mutation-endpoint-inventory.csv`: 226 data rows, 190 with `guard_status` in `VERIFIED` — enforced by `test_canonical_totals`, updated this slice, passing.

`mutation-enforcement-matrix.csv`: NOT updated this slice — per its own established convention (2F-15C's `canonical-csv-structure.md`), this file tracks per-module TOTAL mounted mutation counts (a different denominator), and none of the modules touched this slice had their per-module row previously updated to disagree with the new tenant-only figures in a way requiring correction. No row in this file references a stale count that would misrepresent the reconciliation above.

## No headline convention or mixed denominator
The single canonical figure is **190/226** — reported consistently across all Workstream 11 required breakdowns above, with customer/platform figures always reported SEPARATELY, never merged into this headline.
