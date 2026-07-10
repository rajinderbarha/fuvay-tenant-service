# FRONTEND_CONNECT_01 — Remaining Blockers

This sprint was scoped as **foundation only**. The following are honestly-documented gaps, not silently skipped:

1. **Real browser DOM/JS verification not possible in this environment.** Only `curl.exe` against the live dev servers was available — this confirms HTTP 200 + expected static text + absence of literal NaN/null/undefined in the SSR shell, but cannot confirm client-side hydration, `useApi()` fetch execution, or loading→data/error state transitions actually firing in a real browser. See `FRONTEND_CONNECT_01_BROWSER_SMOKE_REPORT.md`.

2. **Tenant-context-missing UI path is unexercised.** `TenantContextMissingError` / `requireTenantContext()` exist and throw the exact required copy, but no page in this sprint actually triggers and renders that path through `ApiErrorState` — both smoke pages always have tenant/admin context by the time they render post-login.

3. **15 pre-existing pages still call `fetch()` directly** instead of the central `apiFetch()` client (7 tenant-portal, 8 super-admin — mostly CSV/export flows). Not migrated this sprint per explicit scope ("do not rewrite every file yet unless safe"). Full list in `FRONTEND_CONNECT_01_DIRECT_FETCH_SCAN.md`.

4. **`super-admin/lib/mock.ts`** exists and was not inspected in depth — unknown how many (if any) live admin pages still import from it. Flagged for the next connectivity sprint.

5. **Legacy `/provider/wallet` page + `providerWalletApi`** pre-date this sprint and use "Wallet" terminology that conflicts with the confirmed direct-payment architecture. Out of scope to rename this sprint (would be new business-logic-adjacent UI work, not foundation).

6. **Live authenticated smoke test used pre-seeded demo credentials found in the repo's existing conventions**, not credentials newly created for this sprint — full tenant-A-vs-tenant-B isolation was verified by code inspection (JWT-scoped backend, no ambient tenant_id override in new frontend code) rather than by an end-to-end two-tenant differential curl test, since that requires two distinct provisioned tenant accounts with known passwords which were not confirmed available in this session.

7. **Only 1 of the spec's 18 admin/tenant API module functions per side (`getAdminServiceCatalog`, `getAdminPricingRules`, etc.) were smoke-tested live** (the two used by the overview page). The remaining stub functions (Parts 9/10) are wired to real endpoints and type-check, but were not individually curled this sprint.

8. **`npm run build` fails in BOTH frontends** at the static-export/prerender stage — pre-existing, unrelated to this sprint. Root cause: the shared `components/enterprise/EnterpriseDataGrid.tsx` component calls `useSearchParams()` without a `<Suspense>` boundary; Next.js's static-export pass fails on any page that renders it (`/admin/refund-requests` in super-admin, `/service-jobs` in tenant-portal — confirmed same stack trace shape in both). `✓ Compiled successfully` and `Finished TypeScript` (0 errors) both pass before this failure — i.e. this sprint's code changes are not implicated. Fixing it requires wrapping `EnterpriseDataGrid`'s `useSearchParams()` usage in `<Suspense>`, a change touching a shared component used by ~40+ pages platform-wide — judged out of scope for this foundation-only sprint but flagged as a genuine production-build blocker worth a dedicated follow-up sprint.

None of the above block the foundation itself from being usable by future page-connectivity sprints — they are the reason this sprint's verdict is PARTIAL_READY rather than fully READY, per the spec's own rule that curl-only browser verification caps the ceiling.
