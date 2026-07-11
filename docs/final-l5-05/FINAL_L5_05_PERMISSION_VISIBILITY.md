# FINAL-L5-05 — Permission Visibility (Part 23)

## Real finding: `usePermissions()` adoption is ~2% (3 of 162 pages)
Confirmed via grep: `usePermissions()` is called only in `service-catalog/page.tsx`, `pricing/bargain-rules/page.tsx`, `pricing/provider-overrides/page.tsx`. The hook itself (`hooks/usePermissions.ts`) is real, backend-sourced (`authApi.me().permissions`), and works correctly where used — this is an adoption gap, not a broken mechanism.

## What this means concretely
The vast majority of Super Admin pages/actions today are gated only by the coarse `require_super_admin`/role-based backend checks (real, backend-enforced — rule 15 "frontend menu hiding must not replace backend authorization" is **not violated**, since the backend never relied on frontend hiding to begin with). What's missing is the **finer-grained** in-app UI adaptation the mission's Part 23 wants: Admin Finance seeing only finance pages, Admin Read Only seeing disabled mutation controls, etc. — because most pages don't check `perm.has(...)` for anything narrower than "are you logged in as an admin at all."

## Real roles that exist in this codebase (re-confirmed, consistent with FINAL-L5-04B's finding)
Backend `Role` literal: `super_admin | tenant_owner | staff | customer | guest`. There is **no distinct `Admin Operations`/`Admin Finance`/`Security Admin`/`Support Admin` role** in the actual auth system — these are permission-key distinctions layered on top of a single `super_admin` role via the `permissions` array, not separate roles. This was not built this sprint (large scope, cuts across the entire admin auth model) — documented as a real, pre-existing architectural gap.

## Required checks — honest status
| # | Check | Result |
|---|---|---|
| 1 | Admin Finance sees intended finance pages | **Not verifiable** — no distinct Admin Finance role/permission-set exists to test against |
| 2 | Admin Operations sees operational pages | Same |
| 3 | Security Admin sees governance/security pages | Same |
| 4 | Admin Read Only sees readable pages only | Partially — `access_scope` claim (`customer_support_limited`) exists as a narrower concept from earlier sprints, not independently re-tested this sprint |
| 5 | Direct routes enforce permission | **Confirmed for the backend layer** — every admin API endpoint checked this sprint (entitlement, catalog, tenant) requires real auth; no frontend-only gate found |
| 6 | LocalStorage role alone cannot grant access | **Confirmed** — every permission check this session traced resolves server-side (JWT-derived), not from client-stored role strings |
| 7 | Permission denial is not shown as empty data | Not independently re-verified this sprint at scale (would require testing all ~70 orphaned + 43 nav pages under multiple restricted tokens — out of bounded scope) |

## Result
Backend authorization is real and was not found to rely on frontend hiding anywhere touched this sprint. The mission's finer-grained multi-role permission *visibility* UX (distinct Finance/Operations/Security admin views) does not exist as a buildable feature this sprint without first introducing new backend permission-set/role distinctions — a substantial, separately-scoped change, not attempted here. Documented honestly as a Remaining Blocker rather than fabricated.
