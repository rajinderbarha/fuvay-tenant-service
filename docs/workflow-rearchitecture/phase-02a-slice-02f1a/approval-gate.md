# Phase 2A Slice 2F-1A — Approval Gate

**No other router module touched. `readonly@` untouched. Migration 144 not
applied. No permission granted to any role. No visual redesign. Stopping
here for review.**

## Disposition: SECURITY_CLOSED_PRODUCT_POLICY_BLOCKED (for `tenant_engine.router`)

## Files changed
- **Code: none.** This is a policy-closure and verification slice — no
  guard, permission, or endpoint behavior changed.
- **Docs (new):** `docs/workflow-rearchitecture/phase-02a-slice-02f1a/` (10
  files).
- **Docs (updated, classification/annotation only):**
  `phase-02a-slice-02f1/tenant-engine-mutation-inventory.csv` (8 rows
  corrected), `tenant-engine-enforcement-matrix.csv` (tested-column
  updated), `tenant-engine-alternate-routes.md` (addendum),
  `deferred-items.md` (2 items resolved), `approval-gate.md` (amendment
  banner); `phase-02a-slice-02f/tenant-mutation-endpoint-inventory.csv` (8
  global rows corrected), `mutation-enforcement-matrix.csv` (summary row
  annotated).
- **Tests:** `tests/test_phase2f1_tenant_engine_mutation_enforcement.py` —
  48 new tests (40 → 88 total).

## Final classification totals (27 endpoints)
- **11** `TENANT_OWNER_SELF_SERVICE`
- **15** `PLATFORM_ADMIN_ONLY` (7 unchanged `require_super_admin`-gated + 8
  corrected from `TENANT_OWNER_MUTATION`)
- **1** `PUBLIC_SIGNUP`

## The 8 unassigned-permission endpoints — disposition
All 8 → **`PLATFORM_ADMIN_ONLY`**, evidence-based (not name-based):

| Endpoint | Permission | Evidence |
|---|---|---|
| `suspend_tenant` | `tenant:suspend` | super-admin app sole caller; granted to no role |
| `reinstate_tenant` | `tenant:reinstate` | super-admin app sole caller; granted to no role |
| `begin_termination` | `tenant:terminate` | super-admin app sole caller; granted to no role |
| `confirm_termination` | `tenant:terminate` | super-admin app sole caller; granted to no role; claimed 90-day deletion job missing |
| `upgrade_plan` | `tenant:plan:manage` | super-admin app sole caller; granted to no role; distinct from provider package purchase |
| `downgrade_plan` | `tenant:plan:manage` | super-admin app sole caller; granted to no role |
| `convert_trial` | `tenant:plan:manage` | super-admin app sole caller; granted to no role |
| `gdpr_deletion` | `tenant:data:delete` | super-admin app sole caller; granted to no role; claimed anonymization execution missing |

No permission was granted to any role for any of the 8.

## Tenant-owner self-service actions (11)
`update_tenant`, `update_payment_method`, `request_data_export`,
`bulk_enable`, `bulk_disable`, `enable_engine`, `disable_engine`,
`update_engine_config`, `validate_engine_config`, `set_feature_flag`,
`delete_feature_flag`.

## Platform-admin-only actions (15)
The 8 above, plus the 7 pre-existing `require_super_admin`-gated onboarding
review workflow + dunning trigger endpoints (unchanged from Slice 2F-1).

## Blocked product decisions (2)
1. Voluntary tenant self-pause as a distinct feature.
2. True subscription-cancellation capability distinct from `downgrade_plan`.
Plus 2 engineering gaps flagged as needing product/compliance input before
any fix: the missing 90-day termination-deletion job, the missing GDPR
erasure execution mechanism.

## Frontend actions hidden or already absent
None needed to be hidden — all 8 platform-only endpoints were already
absent from `frontend/tenant-portal` (confirmed via direct grep, zero
matches). No frontend code was changed. 2 new regression tests guard
against future accidental exposure.

## All-19 read-only test result
19/19 pass (403 `PERMISSION_DENIED`, including with an explicit
`permission_overrides` grant included, proving access-scope denial is not
overridden by a permission grant) — unchanged from Slice 2F-1, re-confirmed
passing this slice.

## All-19 tenant-owner result
19/19 tested directly via HTTP:
- 11 `OWNER_ACCESSIBLE`: auth layer cleared (not 401/403).
- 8 `PLATFORM_ONLY`: 403 `PERMISSION_DENIED` (expected, correct outcome per
  the corrected classification, not a regression).

## All-19 cross-tenant result
19/19 tested directly via HTTP: all 403.
- 11: rejected by `_assert_own_tenant_or_super_admin`.
- 8: rejected earlier, by the `require_permission` layer (tenant_owner
  lacks the permission regardless of tenant).

## Super-admin test result
8/8 `PLATFORM_ADMIN_ONLY` endpoints directly tested: super_admin retains
access (not 401/403) for all 8 — confirms the classification correction did
not lock out the actual, legitimate caller persona.

## Security-closure status
**SECURITY_CLOSED.** All 19 tenant-reachable mutations remain access-scope
protected; permissions and tenant-ownership checks remain enforced;
cross-tenant access is blocked (now proven for all 19, not just 4); no
weaker alternate route exists.

## Product-policy-closure status
**PRODUCT_POLICY_BLOCKED.** Every endpoint has an explicit, evidence-based
persona now (no ambiguity remains about who *currently* uses each
endpoint), but 2 genuine product decisions and 2 engineering gaps remain
open and are not silently glossed over.

## Tests run / passed / failed
Targeted combined suite: 430 / 430 / 0. Broader partition: 364 / 364 / 0 (5
pre-existing, unrelated skips).

## Route count
Unchanged (no route added, removed, or modified this slice).

## Route collisions
0.

## Remaining decisions
The 4 items in `product-decisions-required.md` (2 product, 2 engineering) —
none require a code change to close *this* slice, but block full
`PRODUCT_POLICY_CLOSED` status for the module.

## Whether every quality gate passed
**Yes, all 21 gates.** Notably: gate 4 (no sensitive permission granted
without product evidence) — none was granted. Gate 6 (blocked product
decisions clearly identified) — 2 identified, not glossed over. Gate 21
(final status distinguishes security from product-policy closure) — done
explicitly above.

---
**Stopping here. Not starting `provider_portal.router`. Not remediating
`readonly@`. Not applying migration 144. Not granting any new permission.
Awaiting approval before any further slice.**
