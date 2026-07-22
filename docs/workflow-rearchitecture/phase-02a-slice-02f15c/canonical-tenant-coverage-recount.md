# Canonical Tenant Coverage Recount

## Starting point
The last APPROVED canonical baseline, per this slice's mission: **169 protected of 210 tenant-facing mutation routes** (the baseline before any `booking.router` row was ever tracked in the canonical CSV).

## Row-by-row reconciliation of the 11 Booking mutation-method routes
| Route | In 169/210 baseline? | New? | Duplicate? | Persona | Protected? | Enters X/Y? |
|---|---|---|---|---|---|---|
| `booking_preflight` | No | New | No | `FALSE_POSITIVE_NON_MUTATION` | n/a | **No** — excluded entirely, not a mutation |
| `create_booking` | No | New | No | `CUSTOMER_SELF_SERVICE_MUTATION` | Yes | **No** — customer route, excluded from tenant denominator |
| `cancel_booking` | No | New | No | `CUSTOMER_SELF_SERVICE_MUTATION` | Yes | **No** |
| `confirm_booking` | No | New | No | `TENANT_PROVIDER_MUTATION` | Yes | **Yes** |
| `reject_booking` | No | New | No | `TENANT_PROVIDER_MUTATION` | Yes | **Yes** |
| `convert_to_job` | No | New | No | `TENANT_PROVIDER_MUTATION` | Yes | **Yes** |
| `request_reschedule` | No | New | No | `CUSTOMER_SELF_SERVICE_MUTATION` | Yes | **No** |
| `accept_reschedule` | No | New | No | `TENANT_PROVIDER_MUTATION` | Yes | **Yes** |
| `reject_reschedule` | No | New | No | `TENANT_PROVIDER_MUTATION` | Yes | **Yes** |
| `add_note` | No | New | No | `TENANT_PROVIDER_MUTATION` | Yes | **Yes** |
| `void_booking` | No | New | No | `PLATFORM_INTERNAL_MUTATION` | Yes | **No** — platform route, excluded |

No duplicate method/path/source keys exist among these 11 (each is a distinct route; confirmed via `test_no_duplicate_rows` in `tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py`, unchanged, passing).

## Mathematical reconciliation

```
Previous numerator:              169
+ newly protected tenant routes:  +6   (confirm_booking, reject_booking, convert_to_job,
                                        accept_reschedule, reject_reschedule, add_note --
                                        all 6 protected)
- removed/reclassified rows:      -0   (none of these 6 were previously counted anywhere)
= final numerator:                175

Previous denominator:            210
+ newly inventoried tenant routes: +6  (same 6 routes above)
- removed/reclassified rows:      -0
= final denominator:              216
```

**Final: 175 protected of 216 tenant-facing mutation routes.**

## Why only 6, not 9 or 11
This corrects 2F-15B's error: 2F-15B classified 9 of the 11 routes `TENANT_PROVIDER_MUTATION` (including the 3 dual-reachable routes: `create_booking`, `cancel_booking`, `request_reschedule`) while ALSO reporting those same 3 as a "customer self-service subset" — a contradiction the mission explicitly flagged (unapproved item #6). This slice resolves the contradiction by giving each route exactly ONE persona: the 3 dual-reachable routes are now `CUSTOMER_SELF_SERVICE_MUTATION` (their tenant-side reachability is tracked separately, in `BOOKING_ALSO_TENANT_REACHABLE_CUSTOMER_ROUTES`, but never used to re-include them in X/Y). Only the 6 routes with NO customer-reachable path at all (`confirm_booking`, `reject_booking`, `convert_to_job`, `accept_reschedule`, `reject_reschedule`, `add_note`) are genuinely tenant/provider-only and enter the denominator.

## Separately reported (never merged into 175/216)
- **3 protected customer-self-service Booking mutations**: `create_booking`, `cancel_booking`, `request_reschedule` (all protected via `require_tenant_mutation_permission`, which also correctly gates their tenant-side reachability — see `customer-dependency-regression.md`).
- **1 protected platform/internal Booking mutation**: `void_booking` (`require_super_admin`, unchanged).
- **1 Booking false positive**: `booking_preflight` (excluded entirely, no persistence).

## Both canonical CSVs recount identically
`docs/workflow-rearchitecture/phase-02a-slice-02f/tenant-mutation-endpoint-inventory.csv`: 216 data rows, 175 with `guard_status` in the `VERIFIED` set (enforced by `test_canonical_totals`, updated this slice). The 4 non-tenant rows (`create_booking`, `cancel_booking`, `request_reschedule`, `void_booking`) were physically removed from this CSV (Design A — see `canonical-csv-structure.md`), not merely relabeled.

`docs/workflow-rearchitecture/phase-02a-slice-02f/mutation-enforcement-matrix.csv`: `app.engines.booking.router`'s row (updated 2F-15A/B, `10,10,0,0,0,100%`) reflects that CSV's OWN convention — total MOUNTED mutation rows in the module (9 tenant-facing... wait, see below), which is a different denominator than the canonical tenant-facing CSV. See `canonical-csv-structure.md` for why these two CSVs intentionally use different conventions and how each remains internally consistent.

## Runtime agreement
```
PYTHONPATH=. python scripts/workflow_rearchitecture/inventory_mutation_routes.py --verify-module app.engines.booking.router
```
```json
"persona_breakdown": {
    "CUSTOMER_SELF_SERVICE_MUTATION": 3,
    "FALSE_POSITIVE_NON_MUTATION": 1,
    "TENANT_PROVIDER_MUTATION": 6,
    "PLATFORM_INTERNAL_MUTATION": 1
},
"tenant_denominator_count": 6
```
Matches this document's row-by-row reconciliation exactly: 6 tenant/provider (all counted), 3 customer (excluded), 1 platform (excluded), 1 false positive (excluded).
