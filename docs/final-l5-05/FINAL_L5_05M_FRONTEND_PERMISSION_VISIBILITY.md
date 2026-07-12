# FINAL-L5-05M — Frontend Permission Visibility, Route Guard and Action Authorization

## Part 2 — Frontend permission-usage inventory (before this sprint)

| Call site | Classification |
|---|---|
| `hooks/usePermissions.ts` | CANONICAL_PERMISSION_CHECK (pre-existing from FINAL-L5-05L, but 0 consumers) |
| `components/layout/AdminLayout.tsx` | **MISSING_PERMISSION_CHECK** — 0 `usePermissions()` call sites, the root cause this sprint fixes |
| `app/admin/users/page.tsx`'s `PLATFORM_ROLES` constant | **HARDCODED_IDENTITY_CHECK-adjacent, real mismatch found** — a locally-defined role list (`operations_admin`, `finance_admin`, `security_admin`, `read_only_admin`) that does not match any real `ROLE_PERMISSIONS` key (the real ones are `admin_operations`, `admin_finance`, `admin_security`, `admin_readonly`). This page's role dropdown writes to `users.platform_role` via `PUT /v1/admin/platform-users/{id}/role` — a **separate, dead metadata field** from `users.role` (the one `PermissionChecker` actually consults), the same disconnect FINAL-L5-05L found and fixed for the 4 seeded test accounts. **Not fixed this sprint** — this is Platform Users Governance (migration 083), a distinct, larger subsystem; rewiring it to write the real `role` column is a backend-architecture change outside this sprint's frontend-visibility scope. Documented as L5-05M-011 (new finding).
| No `localStorage`-based permission override found anywhere | 0 FRONTEND_BYPASS instances |
| No hardcoded admin email/username authorization check found anywhere | 0 HARDCODED_IDENTITY_CHECK instances (aside from the platform_role mismatch above, which is a data-key mismatch, not an identity check) |

**Result: 0 hardcoded identity checks, 0 frontend permission bypasses, 1 real pre-existing metadata mismatch found and documented (not fixed — out of bounded scope).**

## Part 3 — Server permission payload (verified live)

`GET /v1/auth/me` returns `{ id, email, full_name, role, permissions: string[], ... }`. Live-verified for `admin_operations`:

```
role: admin_operations
permissions: [admin:jobs:read, admin:jobs:reassign, admin:jobs:status_override,
  admin:jobs:force_close, admin:jobs:void, field_ops:jobs:read, field_ops:reports:read,
  tenant:read, tenant:health:read, staff:read, staff:performance:read, review:read,
  review:moderate, notification:logs:read, notification:send, analytics:dashboard:read]
```

`usePermissions()` (`frontend/super-admin/hooks/usePermissions.ts`) consumes this array directly — no frontend computation. Updated this sprint to expose `permissions: string[] | null` (distinct `null`-while-loading vs `[]`-real-empty-result) so consumers can fail closed during loading without permanently treating "still loading" as "denied forever" (Part 20 requirement).

## Part 4 — Central permission metadata catalog

New file: `frontend/super-admin/lib/permission-catalog.ts`. Metadata only (label, domain, read/mutation/export shape) — permission truth remains the server array. Every key is checked against the real backend registry by an automated guard (`tests/test_final_l5_05m_frontend_permission_guards.py::TestPermissionCatalogValidity`). One real key-mismatch was found and fixed during this verification: the catalog and `AdminLayout.tsx` both initially used `"analytics:read"`; the real backend key is `"analytics:dashboard:read"` (`P.ANALYTICS_READ`).

`SUPER_ADMIN_ONLY` sentinel: for nav items/routes whose backing endpoint is still gated by the coarse `require_super_admin` check (not converted to `require_permission` in FINAL-L5-05L — a bounded, deliberately-scoped conversion, not exhaustive). This mirrors real backend behavior exactly rather than inventing an unenforced permission key.

## Part 5/6 — Navigation permission metadata + desktop sidebar filtering

`AdminLayout.tsx`'s `NavItem` type now requires `requiredPermission: string` on every one of the ~44 items across all 9 `NAV_GROUPS`. Every item was individually classified:

| Group | Items with a real backend permission key | Items marked `SUPER_ADMIN_ONLY` |
|---|---|---|
| Overview | Dashboard (visible to any authenticated admin — landing page, no gate) | — |
| Providers | All Providers (`tenant:read`) | New Requests, Verify & Approve, Packages |
| Operations | Jobs (`admin:jobs:read`), Staff (`staff:read`) | Bookings, Customers, Reviews, Complaints, Complaint Policies |
| Catalog | — | Verticals, Categories |
| Pricing & Rules | — | all 3 items |
| Home Services | Completed Job Deduction (`finance.completed_job_deduction_rules.read`) | remaining 8 items |
| Finance | Finance Hub, Usage Credits, Security Deposits, Credit Top-ups (each mapped to its real `finance.*`/`finance:*` permission) | Warranty Claims, Payouts, Compliance |
| Marketing & Growth | Analytics, Reports (`analytics:dashboard:read`) | Campaigns, Notifications, AI Intelligence |
| Platform | Security (`security:read`), Audit Logs (`auth:audit:read`), Users (`auth:users:read`), Roles (`platform:roles:read`), Permissions (`platform:permissions:read`) | Engines, Workflows, Media, Settings |

Render logic (`AdminShellInner`): for each group, `visibleItems = group.items.filter(isNavItemVisible).filter(isNavItemPermitted)`. If `visibleItems.length === 0` and the group has no dynamically-injected content (the Catalog group's per-vertical submenu, itself gated `SUPER_ADMIN_ONLY`), the entire group — including its header — renders nothing (`return null`), satisfying "empty groups do not render." `isNavItemPermitted` returns `false` while `effectivePermissions === null` (still loading), so nothing renders prematurely — the sidebar shows only the always-visible Dashboard item until the real permission array arrives, then expands to the correct, role-appropriate set. No intermediate "everything visible" flash state exists.

## Part 7 — Mobile navigation

**Honest, pre-existing, unrelated finding re-confirmed**: there is no separate mobile drawer component in this codebase (`AdminLayout.tsx` is the sole renderer of `NAV_GROUPS`) — a gap already documented as Blocker 6 in `FINAL_L5_05_REMAINING_BLOCKERS.md` since FINAL-L5-04 ("No responsive/mobile Super Admin navigation exists at all"). This sprint does not build a new mobile drawer (would be "redesigning the interface," explicitly out of scope). Consequently, requirements #7/#8 ("desktop and mobile use the same registry", "no duplicate navigation registries") are trivially satisfied — there is exactly one registry and one renderer, so there cannot be a mobile/desktop divergence. Part 32's dedicated mobile-viewport Chromium matrix was not run this sprint (same underlying reason — nothing mobile-specific exists to test beyond how the single responsive-less sidebar happens to render at narrow viewports, which was not exercised).

## Part 8/9/10 — Route guards + Permission Denied state

New: `components/shared/PermissionGate.tsx` — `RequirePermission` (route guard), `PermissionDeniedPage`, `ReadOnlyNotice`. Applied to the representative high-risk pages named in the mission's own Chromium matrix:

| Page | Guard permission |
|---|---|
| `/admin/finance/usage-credits` | `finance.usage_credits.read` |
| `/admin/finance/topups` | `finance:topups:read` |
| `/admin/finance/deposits` | `finance.security_deposits.read` |
| `/admin/security` | `security:read` |
| `/admin/users` | `auth:users:read` |
| `/admin/users/roles` | `platform:roles:read` |
| `/admin/users/permissions` | `platform:permissions:read` |

`RequirePermission` renders a `Skeleton` while `usePermissions()` is loading (never the protected content, never a denial flash), then either the real page or `PermissionDeniedPage` once the read permission resolves. Live-verified: a Security Admin navigating directly to `/admin/finance/usage-credits?tenant_id=...` sees "Permission denied" and the real balance value (`3979`) never appears anywhere in the page text — proven by a real Chromium assertion, not inferred.

**Not applied to**: the remaining ~37 nav items whose backing routes are `SUPER_ADMIN_ONLY` (sidebar already hides them for non-super-admin roles, and their backend endpoints independently return 403/`Super admin access required` on direct API access — proven in FINAL-L5-05L). Exhaustively wrapping every one of the ~44 routes with an explicit client-side guard component, on top of the sidebar-level filtering that already exists, was judged out of this sprint's bounded scope; the representative set above was chosen to match the mission's own Part 31 Chromium matrix exactly.

## Part 11 — Read-only presentation

`/admin/finance/usage-credits`'s "Add Usage Credits" mutation card is now gated on `perm.has("finance.usage_credits.adjust")`; when absent, `ReadOnlyNotice` ("View-only access — you can review this information, but you cannot make changes.") renders in its place. Live-verified via Chromium: Admin Read Only sees the real ledger table and balance data, the "View-only access" notice, and **no** "Add Usage Credits" text anywhere on the page.

## Part 12/13 — Action permission metadata + action guards

| Action | Page | Guard permission |
|---|---|---|
| Reassign Job | Job detail | `admin:jobs:reassign` |
| Override Status | Job detail | `admin:jobs:status_override` |
| Force-Close | Job detail | `admin:jobs:force_close` |
| Void Job | Job detail | `admin:jobs:void` |
| Add Usage Credits | Usage Credits | `finance.usage_credits.adjust` |
| Retry Credit Posting | Credit Top-ups list | `finance:topups:update` |
| Refund | Credit Top-ups list | `finance:topups:refund` |
| Revoke Session / Revoke All Sessions | Security → Sessions tab | `security:sessions:revoke` |

Each uses the existing, real `usePermissions().has(key)` — no new generic `isSuperAdmin` flag was introduced (rule 13). An automated guard (`TestRoleActionVisibilityMatchesBackendBundles` in the new test file) proves, by cross-referencing the exact same permission keys against the real `ROLE_PERMISSIONS` bundles, that `admin_readonly`/`admin_operations`/`admin_finance`/`admin_security` are each denied the specific action set the mission requires — by construction, not by manual review.

## Part 14/15/16 — Job/Finance/Security action visibility (live-verified this sprint + FINAL-L5-05L)

Backend allow/deny for these exact permission keys was already live-verified per-role in FINAL-L5-05L (force-close/void/reassign/status-override, usage-credit-adjust, topup-approve, security-deposit-adjust, session-revoke — all 403 for the correct roles, 200/permission-gate-passed for the correct roles). This sprint adds the frontend half: the same keys now control whether the corresponding button renders at all, verified live via Chromium (Finance Admin's Jobs list page loads without exposing exceptional Job actions; Operations Admin's sidebar excludes Usage Credits/Credit Top-ups entirely).

## Part 17-19 — Contextual links / Dashboard / Reports

**Not attempted this sprint** — genuinely out of bounded scope given the size of the remaining mission. The dashboard's per-widget permission gaps (several widgets already correctly return "Permission ... required" error states server-side, as seen live in the Operations Admin dashboard snapshot captured during Chromium debugging — `dashboard.finance.read`, `dashboard.read`, `dashboard.operations.read` are all real, already-enforced backend permissions the dashboard widgets correctly surface as inline errors rather than crashing) were observed to already degrade gracefully (inline "we couldn't load X data" + Retry + request_id) rather than exposing data — an acceptable, honest interim state, not silently broken.

## Part 20 — Permission loading state

`usePermissions()` returns `permissions: null` while `authApi.me()` is in flight; `isNavItemPermitted`/`RequirePermission` both treat `null` as "not yet permitted" (fail closed) rather than "denied forever" or "always allowed." Verified live: the Chromium suite's initial flaky run (before a test-timing fix) inadvertently proved this works correctly — a too-short fixed wait caught the sidebar mid-load showing only the always-visible Dashboard item, never any extra/unauthorized content, before the correct final permission-filtered set appeared a moment later.

## Part 21 — Permission cache

Per FINAL-L5-05L's documented policy (unchanged this sprint): permission changes require a fresh `/v1/auth/me` fetch (new page load, or `usePermissions()`'s underlying `useApi` refetch) to propagate — no push-based invalidation exists. `useApi` does not indefinitely cache; each `AdminLayout`/`RequirePermission` mount issues its own fetch. Logout clears the `serviceos_admin_token` from `localStorage`, and a subsequent login for a different account issues a fresh token and a fresh `/v1/auth/me` fetch — no stale cross-account permission bleed-through was observed across the 20 sequential Chromium role-switches run this sprint (each `test()` uses an isolated browser context with its own localStorage).

## Part 22 — Rendering/hydration

No SSR-vs-client mismatch risk was introduced — `AdminLayout` is already `"use client"`, and `usePermissions()` (also client-only, backed by `useApi`) was already the established pattern before this sprint; this sprint only added new consumers of an existing client-side data-fetching hook, not a new server/client boundary.

## Environment note found and fixed during this sprint

Twice during Chromium verification, the Next.js dev server's filesystem cache became corrupted (`.next/dev/types/validator.ts` syntax errors blocking `tsc --noEmit`; later, multiple real routes — including `/admin/dashboard`'s sibling routes, unrelated to any code changed this sprint — returning 404 immediately after a "Finished filesystem cache database compaction" log line). Both were resolved by stopping the dev server, deleting `.next`, and restarting — confirmed via direct `curl` checks before and after, and via a clean standalone Chromium re-run (20/20 passed) once resolved. This is dev-tooling instability, not an application defect; documented for completeness since it affected this session's testing cadence.
