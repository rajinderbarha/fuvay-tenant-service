# Canonical Coverage Update

## Starting baseline
**175 protected of 216** tenant-facing mutation routes (approved at Slice 2F-15C).

## Quote-checklist mutation reconciliation
| Route | Genuine mutation? | Persona | Enters X/Y? | Protected (after this slice) |
|---|---|---|---|---|
| `provider_cancel_quote` | yes | TENANT_PROVIDER_QUOTE_ADMIN | yes | yes |
| `staff_create_quote` | yes | TENANT_PROVIDER_QUOTE_ADMIN | yes | yes |
| `staff_add_item` | yes | TENANT_PROVIDER_QUOTE_ADMIN | yes | yes |
| `staff_update_item` | yes | TENANT_PROVIDER_QUOTE_ADMIN | yes | yes |
| `staff_remove_item` | yes | TENANT_PROVIDER_QUOTE_ADMIN | yes | yes |
| `staff_send_to_customer` | yes | TENANT_PROVIDER_QUOTE_ADMIN | yes | yes |
| `staff_mark_revised` | yes | TENANT_PROVIDER_QUOTE_ADMIN | yes | yes |
| `staff_cancel_quote` | yes | TENANT_PROVIDER_QUOTE_ADMIN | yes | yes |
| `staff_create_checklist` | yes | TENANT_PROVIDER_QUOTE_ADMIN | yes | yes |
| `staff_update_checklist_item` | yes | TENANT_PROVIDER_QUOTE_ADMIN | yes | yes |
| `staff_complete_checklist` | yes | TENANT_PROVIDER_QUOTE_ADMIN | yes | yes |
| `customer_approve_quote` | yes | CUSTOMER_QUOTE_APPROVAL | **no** (customer self-service, excluded) | yes (reported separately) |
| `customer_reject_quote` | yes | CUSTOMER_QUOTE_REJECTION | **no** | yes (reported separately) |
| `customer_request_revision` | yes | CUSTOMER_QUOTE_CHANGE_REQUEST | **no** | yes (reported separately) |
| `admin_create_template` | yes | PLATFORM_QUOTE_ADMIN | **no** (platform, excluded) | yes (reported separately) |
| `admin_add_template_item` | yes | PLATFORM_QUOTE_ADMIN | **no** | yes (reported separately) |

## Mathematical reconciliation
```
Previous numerator:              175
+ newly protected tenant routes:  +11  (the 11 TENANT_PROVIDER_QUOTE_ADMIN routes above)
- reclassified/removed rows:      -0   (none previously counted)
= final numerator:                186

Previous denominator:            216
+ newly inventoried tenant routes: +11 (same 11 routes)
- reclassified/removed rows:      -0
= final denominator:              227
```

**Final: 186 protected of 227 tenant-facing mutation routes.**

## Separately reported (never merged into 186/227)
- **3 protected customer-self-service quote-checklist mutations**: `customer_approve_quote`, `customer_reject_quote`, `customer_request_revision` (all protected via `require_customer` + `customer_id` ownership).
- **2 protected platform/internal quote-checklist mutations**: `admin_create_template`, `admin_add_template_item` (both `require_super_admin`, unchanged).
- **0 false positives** in quote_checklist (every mutation-method route in this module performs a genuine mutation — unlike `booking.router`'s `booking_preflight`).

## Both canonical CSVs recount identically
`tenant-mutation-endpoint-inventory.csv`: 227 data rows, 186 with `guard_status` in the `VERIFIED` set (enforced by `test_canonical_totals`, updated this slice). No duplicate `(method, path, module)` keys introduced (enforced by `test_no_duplicate_rows`, unchanged, re-verified passing).

## Runtime agreement
```
PYTHONPATH=. python scripts/workflow_rearchitecture/inventory_mutation_routes.py --verify-module app.engines.quote_checklist.provider_router
{ "total_routes": 11, "unverified_count": 0 }

PYTHONPATH=. python scripts/workflow_rearchitecture/inventory_mutation_routes.py --verify-module app.engines.quote_checklist.customer_router
{ "total_routes": 3, "unverified_count": 0 }

PYTHONPATH=. python scripts/workflow_rearchitecture/inventory_mutation_routes.py --verify-module app.engines.quote_checklist.admin_router
{ "total_routes": 2, "unverified_count": 0 }
```
11 + 3 + 2 = 16 total quote_checklist mutation routes, all protected — matching this document's 11 tenant + 3 customer + 2 platform breakdown exactly.
