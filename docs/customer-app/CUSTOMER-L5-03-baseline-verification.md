# CUSTOMER-L5-03 — Baseline Verification (Deepened Pass)

Supersedes the earlier, lighter `CUSTOMER-L5-03-baseline-verification.md`
written in this same session's first L5-03 pass. Re-ran `npx tsc --noEmit`,
`npx eslint`, `npx prettier --check`, `npx jest` before starting this pass.

## CUSTOMER-L5-00 Status

PARTIAL (unchanged — architecture/design-system baseline; device-level a11y
and native builds not possible in this environment).

## CUSTOMER-L5-01 Status

Complete. Re-confirmed passing.

## CUSTOMER-L5-02 Status

PARTIAL per its own final report — the deepened CUSTOMER-L5-02 pass
(refresh coordinator, sessions/devices, logout-all, query-cache clearing on
logout) is implemented and tested, but no live backend was reachable in
this environment to perform the live-runtime certification CUSTOMER-L5-02
itself required for a hard PASS. This sprint (L5-03) inherits that same
constraint — see `CUSTOMER-L5-03-runtime-evidence.md`.

## Verification of the 20 Checklist Items

1. App startup works — 46 test suites pass, including the full
   `startup-route-resolver.test.ts` suite (unchanged).
2. Remote configuration resolves safely — `remote-config-*` tests
   unchanged, passing.
3. Customer authentication works — CUSTOMER-L5-02's OTP flow, unchanged.
4. Session restoration works — `session-bootstrap.test.ts`, unchanged.
5. Current customer loads — `GET /v1/auth/me`, unchanged.
6. Marketplace context available — **partially**: `request-context.ts` has
   tenant binding (`setRequestTenantId`/`getRequestTenantId`, the getter
   added this pass) but nothing in the app currently calls
   `setRequestTenantId` with a real value — this backend/environment has
   only one marketplace, so there's no real value to bind yet. Documented,
   not fabricated.
7. Tenant-branded context — same as above, UNVERIFIED (single-tenant test
   environment).
8. Typed navigation works — `route-guards.test.ts`, `route-registry.ts`,
   unchanged.
9. Theme works — CUSTOMER-L5-00, unchanged.
10. Localization works — **defect found and fixed this pass**: see below.
11. Connectivity state works — `useConnectivity`, unchanged.
12. API client works — `api-client.test.ts`, unchanged plus new
    `request-context.test.ts`.
13. Query client works — CUSTOMER-L5-00, unchanged.
14. Error normalization works — `api-errors.test.ts`, unchanged.
15. Secure storage isolated — CUSTOMER-L5-02, unchanged.
16. Customer cache clears on logout — CUSTOMER-L5-02's `queryClient.clear()`
    fix, unchanged (already covers Home's category query, since
    `queryClient.clear()` wipes every query, not a customer-specific
    subset).
17. Pending destinations handled — CUSTOMER-L5-01, unchanged.
18. Production debug tools excluded — `__DEV__` guards, unchanged.
19. Existing tests pass — 312/312 (up from 291 before this pass).
20. Working tree understood — `git status`/`git diff --stat` reviewed
    before starting; only files listed in this report's "Files
    Added/Modified" sections were touched.

## Defect Found and Fixed This Pass

**`setRequestLocale()` (CUSTOMER-L5-00's `request-context.ts`) was never
called anywhere in the codebase.** Every outgoing API request's
`Accept-Language` header was permanently `"en"` regardless of the
customer's actual selected or system-detected language — Hindi and
Punjabi customers were silently sending `Accept-Language: en` on every
request since CUSTOMER-L5-00. Fixed in `localization/i18n-setup.ts`:
`initI18n()` now calls `setRequestLocale()` with the resolved initial
locale and subscribes to i18next's `languageChanged` event to keep it in
sync. Covered by the new `request-context.test.ts` and exercised
end-to-end by `home-queries.ts` now reading `getRequestLocale()` instead
of a hardcoded `"en"` argument.

## Corrective Work Completed

- Locale header fix (above).
- `home-queries.ts` query key now scoped by locale + tenant (was: locale
  only, hardcoded to `"en"` at the call site).
- `HomeScreen.tsx` now routes its one real module through the new
  module-registry/visibility-evaluator layer instead of rendering the
  category grid unconditionally.

## Deferred Non-Blocking Issues

See `CUSTOMER-L5-03-known-gaps.md` (this pass) and the original
`known-gaps.md` (cross-sprint).
