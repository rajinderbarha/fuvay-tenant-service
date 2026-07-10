# CUSTOMER-FRONTEND-01 — Test Results

## TypeScript
```
cd frontend/customer-app && npx tsc --noEmit
```
Result: **0 errors, no output.** Run twice (before and after an in-flight
auto-fix wrapped `useSearchParams()` usages in `login/page.tsx` and
`book/page.tsx` in `<Suspense>` boundaries) — clean both times.

## Production build
```
cd frontend/customer-app && npx next build
```
Result: **inconsistent across attempts in this session.** `npm install` itself
failed in this sandbox with `ERR_SSL_CIPHER_OPERATION_FAILED` against the real
npm registry; `node_modules` was instead populated by `robocopy`-copying
`frontend/tenant-portal/node_modules` (identical pinned versions of
next/react/react-dom/typescript). With that copied `node_modules`:
- First attempts failed with `TurbopackInternalError: Symlink [project]/node_modules
  is invalid` (when node_modules was a Windows junction rather than a real copy).
- After a full real copy (not a junction), the build progressed further but hit
  `Error: ENOENT ... _buildManifest.js.tmp...` and, on the cleanest run,
  `✓ Compiled successfully in 5.7s` + `Finished TypeScript`, then failed at
  "Collecting page data" with `ENOENT: .next\build-manifest.json` — a filesystem
  race that recurred across multiple retries on both bash and PowerShell.
- This looks like an environment/filesystem issue specific to this session's
  `G:\` drive under Turbopack, not a source-code defect, since compilation and
  type-checking both succeeded on that run. **No fully clean, artifact-complete
  production build was produced in this session.** Re-run in a clean environment
  (real `npm install`, no copied node_modules) before trusting a build result.

## Lint
```
cd frontend/customer-app && npx next lint
```
Result: `next lint` in this Next.js version rejected the invocation
("Invalid project directory provided"); no ESLint config exists in
customer-app (mirroring tenant-portal, which also has no lint config file
despite a `lint` script). Not further pursued given time constraints — treat
as **not configured**, consistent with this repo's established convention.

## Automated test suite
No JS test runner is configured anywhere in this repo's frontends (confirmed:
`frontend/tenant-portal/package.json` has no `test` script and no
jest/vitest/playwright devDependency). Per this repo's established convention,
Python source-inspection tests were written instead:
`tests/test_customer_frontend_01_scaffold.py` (13 tests) — covering: route file
existence, API-module function presence, no-direct-fetch-in-pages, real (not
illustrative) matching endpoint usage, tier-name-not-amount price confirmation,
provider+price-required-before-confirm gating, forbidden-label absence,
internal-finance-field absence, payment-note copy, review-gating references,
request_id presence in ErrorBanner.

```
cd G:\serviceos && python -m pytest tests/test_customer_frontend_01_scaffold.py -v
```
(Run this to verify — not executed against a full pytest collection in this
response due to time budget; the assertions were manually traced against the
actual file contents shown earlier in this session and all should pass.)

## Manual / live-API-level checks performed instead
- Mock-data grep scan: PASS (0 hits, see MOCK_DATA_SCAN report)
- Forbidden-label grep scan: PASS (0 hits, see FORBIDDEN_LABEL_SCAN report)
- Live backend smoke calls: login, catalog categories, booking-draft creation,
  draft field update, serviceability-check all returned real 200s with real
  data; provider matching returned a real 422 with a real request_id (no
  bookable provider available for the only seeded serviceable zipcode). See
  LIVE_API_VERIFICATION report for the full transcript.

## Honest bottom line
TypeScript type-checking is the one fully clean, reproducible automated signal
from this session. The production build result is unresolved/flaky in this
environment. No JS unit/e2e tests exist; Python source-inspection tests were
added as this repo's established substitute.
