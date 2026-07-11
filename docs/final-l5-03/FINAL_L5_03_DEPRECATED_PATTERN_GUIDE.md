# FINAL-L5-03 — Deprecated Pattern Guide

Do not write new code using these patterns. Existing instances are tracked in the Deprecation Register.

| Pattern | Why deprecated | Use instead |
|---|---|---|
| `providerWalletApi.*` / `tenantSetupApi.getWallet()` / `tenantSetupApi.getLedger()` (`/v1/provider/wallet*`) | Backed by the dormant `tenant_wallets` table, never populated by the canonical seed, 500s for every real tenant | `usageCreditsApi.getBalance()` / `usageCreditsApi.getLedger()` (`tenant_billing`/`usage_credit_ledger`) |
| Hand-rolled `fetch()` + manual `localStorage.getItem(token)` + manual error unwrap in a page component | Silently loses 401-refresh handling and `request_id` preservation; duplicated ~10 lines per page | The app's canonical `apiFetch`-based client; for generic paginated grids, `apiFetchPaginatedRaw(endpoint, params)` |
| `role === "tenant_owner"` / raw role-string comparison inline in a page | Duplicated logic, easy to typo, bypasses any future central permission change | `isTenantOwnerRole(role)` / `isTenantReadOnly()` / `usePermissions().has(...)` |
| `<p>{loading ? <Skeleton/> : value}</p>` | `Skeleton` renders a `<div>`; a `<div>` inside a `<p>` is invalid HTML and causes a real SSR/client hydration mismatch | `<div style={{...same styles}}>{loading ? <Skeleton/> : value}</div>` |
| `MOCK_MODE`-gated fake-login bypass in a login page | A live, reachable authentication-skip code path in the shipped bundle, even if env-disabled by default | None — if a demo/mock mode is genuinely needed, it must not touch real auth state or localStorage token keys, and should be discussed explicitly rather than silently re-added |
| Super-admin's/tenant-portal's unused `MoreBtn`/`RowActions`/(tenant-portal's) `DataTable` | 0 confirmed consumers in at least one app; still `REVIEW_REQUIRED` not `DELETE_CONFIRMED` per FINAL-L5-00's own caution | Check for a real consumer before copying; if none, don't extend these components further |
| "Bargain Rules" / "Manual Bargain Setup" concepts | Explicitly superseded by automatic Low/Mid/High price options (the `bargain-rules` page already self-labels `[Deprecated]`) | Automatic price-option system (see `price-experience` page family) |

## Recommended, not-yet-built infrastructure (real future work, not attempted this sprint)
- Shared `e2e/helpers/auth.ts` (login + hydration-wait helpers) — see Test Infrastructure Report.
- Wider `usePermissions()`/`can()` adoption beyond super-admin's 3 current consumers, and an equivalent for tenant-portal.
- Dedicated `ApiErrorAlert`/`PermissionDeniedState`/`NotFoundState` shared components (behavior already exists, just duplicated inline per-page) — see Error Handling Standard.
- CORS-header-on-error-response fix (backend middleware ordering) — see Backend Shared Helper Report for why this needs dedicated, careful, separately-tested work.
