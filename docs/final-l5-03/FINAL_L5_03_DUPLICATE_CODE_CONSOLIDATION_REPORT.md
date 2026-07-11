# FINAL-L5-03 — Duplicate Code Consolidation Report

## Consolidated this sprint

| Duplication | Before | After |
|---|---|---|
| API client bypass (5 super-admin grid pages) | Each hand-rolled `URLSearchParams` + `localStorage.getItem(token)` + `fetch()` + `res.json()` + `new Error(...)` — ~10 identical lines × 5 files | One shared `apiFetchPaginatedRaw(endpoint, params)` in `lib/api.ts` |
| `isTenantOwner` role check (2 tenant-portal pages) | Identical inline expression `role === "tenant_owner" \|\| role === undefined` × 2 files | One shared `isTenantOwnerRole(role)` in `lib/api.ts` |
| Dormant wallet fetch (`TenantLayout.tsx`) | Called a broken, dormant-table-backed endpoint via `tenantSetupApi.getWallet()` — not itself duplicated code, but the root cause the consolidation above's `isTenantOwnerRole` review surfaced while auditing the same file | Migrated to `usageCreditsApi.getBalance()`, already the canonical, working source used elsewhere in the app |

## Explicitly NOT consolidated (per the mission's own caution: "do not consolidate unrelated pages merely because they look similar")
- The 3 independent `components/shared/ui.tsx` files (super-admin/tenant-portal/customer-app) — real, structural duplication, but merging them is a cross-app package change, not a same-app code consolidation; see Shared UI Component Report for the full reasoning.
- The 3 independent `apiFetch` client implementations — same reasoning, plus each app has a genuinely different token/tenant model (rule 5's "without reason" carve-out applies).
- `EnterpriseDataGrid` (super-admin vs. tenant-portal copies) — not merged; both are actively, differently used.

## Result
Every consolidation this sprint was of code proven byte-identical (or functionally identical with a documented, preserved edge case) across multiple real call sites — no speculative merging of superficially-similar-but-actually-different code.
