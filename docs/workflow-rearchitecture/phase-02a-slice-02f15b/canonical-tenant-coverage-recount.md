# Canonical Tenant Coverage Recount

## History of the figure
| Slice | Reported | Status |
|---|---|---|
| Pre-Booking baseline | 169/210 | Approved |
| 2F-15 | 174/221 (provisional) | Superseded |
| 2F-15A | 179/220 (provisional) | Superseded |
| **2F-15B** | **179/220 (canonical)** | **Final for this mission** |

The numeric figure is unchanged from 2F-15A's report (179/220) — what changes in 2F-15B is that the figure is now backed by an explicit, single-persona-per-route classification (`final-booking-persona-matrix.csv`) rather than a combined "tenant-facing/platform" label, and the `booking_preflight` row is now physically removed from the canonical CSV (not merely relabeled `FALSE_POSITIVE`), closing the ambiguity the mission's Workstream 10 flagged.

## Per-route disposition (all 11 mounted Booking mutation routes)
See `final-booking-persona-matrix.csv` for the full table. Summary:

- **9 routes**: `TENANT_PROVIDER_MUTATION` — included in the tenant-facing denominator, all 9 protected.
- **1 route** (`void_booking`): `PLATFORM_INTERNAL_MUTATION` — excluded from the tenant-facing denominator (platform/internal), protected (unchanged, `require_super_admin`).
- **1 route** (`booking_preflight`): `FALSE_POSITIVE_NON_MUTATION` — excluded entirely (not a mutation at all), physically removed from the canonical CSV.

## Why customer self-service routes are NOT double-counted or excluded incorrectly
Three of the 9 `TENANT_PROVIDER_MUTATION` routes (`create_booking`, `cancel_booking`, `request_reschedule`) are ALSO reachable by the `customer` persona (dual-grant permission). These are:
- Counted ONCE in the tenant-facing numerator/denominator (as `TENANT_PROVIDER_MUTATION`, since the guard genuinely protects the tenant-side call), and
- Counted SEPARATELY in the customer-self-service inventory (see below) — never merged into the X/Y headline.

This resolves the mission's concern: "customer self-service and platform/internal routes may have been included in the tenant denominator." They are not — `void_booking` (platform) and `booking_preflight` (false positive) are excluded from the denominator entirely; the 3 dual routes ARE tenant-facing mutations (their tenant-side guard is real and necessary) and are correctly included once, with their customer-side reachability tracked as a separate, non-overlapping count.

## Final canonical figures
```
179 protected of 220 tenant-facing mutation routes   (headline X/Y)

Separately reported (not merged into X/Y):
  3 protected customer-self-service Booking mutations
    (create_booking, cancel_booking, request_reschedule — dual-reachable,
     already counted once above as TENANT_PROVIDER_MUTATION)
  1 protected platform/internal Booking mutation
    (void_booking)
  1 false-positive Booking route excluded entirely
    (booking_preflight)
```

`field_ops.router` (28/28) and `field_ops.staff_router` (6/6) are unchanged and contribute 34 of the 179 — re-confirmed via runtime tool this slice.

## Both CSVs recount identically
`docs/workflow-rearchitecture/phase-02a-slice-02f/tenant-mutation-endpoint-inventory.csv`: 220 data rows, 179 with `guard_status` in the `VERIFIED` set (enforced by `tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py::TestCanonicalCoverageRecount::test_canonical_totals`, updated this slice).

`docs/workflow-rearchitecture/phase-02a-slice-02f/mutation-enforcement-matrix.csv`: `app.engines.booking.router` row updated (2F-15A) to `10,10,0,0,0,100%` — 10 = 9 tenant-facing + 1 platform, matching this recount (the matrix's per-module total intentionally includes the platform-admin row, since that CSV's convention is "total mounted mutation rows," not "tenant-facing only"; the canonical tenant-facing denominator lives in the endpoint-inventory CSV, which is what `test_canonical_totals` enforces).

## Runtime agreement
`PYTHONPATH=. python scripts/workflow_rearchitecture/inventory_mutation_routes.py --verify-module app.engines.booking.router` reports `persona_breakdown: {TENANT_PROVIDER_MUTATION: 9, PLATFORM_INTERNAL_MUTATION: 1, FALSE_POSITIVE_NON_MUTATION: 1}` — matches this document's 9/1/1 split exactly (see `runtime-verification-report.md`).
