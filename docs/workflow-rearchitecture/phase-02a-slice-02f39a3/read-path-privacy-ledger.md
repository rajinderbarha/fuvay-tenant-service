# Read-Path Privacy Ledger (Separate from the Mutation-Defect Count)

Per explicit instruction: these are `READ_PATH_CROSS_TENANT_PRIVACY_GAP`
items — security debt, not mutation-authorization defects. Never counted
in the 149/261 route-census arithmetic or the canonical mutation
denominator.

| Route | Module | Gap | Status | Recorded by |
|---|---|---|---|---|
| `GET /v1/security/api-keys/tenants/{tenant_id}` (`list_api_keys`) | security.router | Client `tenant_id`, no cross-check against caller's own tenant | `READ_PATH_CROSS_TENANT_PRIVACY_GAP` | Slice 2F-39A2R |
| `GET /v1/security/api-keys/{key_id}` (`get_api_key`) | security.router | Same gap | `READ_PATH_CROSS_TENANT_PRIVACY_GAP` | Slice 2F-39A2R |
| `POST /v1/commerce/bookings/preflight` (`run_preflight`) | platform_commerce.router | Client `tenant_id`, no ownership check; leaks commission rate/health band/wallet buffer | `READ_PATH_CROSS_TENANT_PRIVACY_GAP` | Slice 2F-39A2 |
| `POST /v1/pricing/snapshots/{snapshot_id}/replay` (`replay_snapshot`) | pricing.router | Fetches `PriceSnapshot` by ID with no tenant filter at all | `READ_PATH_CROSS_TENANT_PRIVACY_GAP` | Slice 2F-39A2 |

## Pre-existing standing limitation (unchanged, cited not re-derived)

Pricing GET-by-zone/rule-ID and item/location ownership read-path gaps,
documented since Slice 2F-37's `known-limitations.md` and every slice
since — remain open, out of this program's mutation-only scope.

## This slice's contribution

No new read-path items were added to this ledger this slice (route
classification work this tranche focused on mutation-capable routes per
the auto-classifier's own pre-filter; a systematic read-path scan across
all ~1,134 non-mutation routes was not performed and remains a distinct,
larger, future body of work).
