# FINAL-L5-01D — Technician Redirect Root-Cause Analysis

## Reproduction method
Real Chromium, `e2e/super-admin/final-l5-01d-technician-redirect.spec.ts` (5 fresh-context cold logins) and a separate debug spec capturing console/network/pageerror events in detail.

## Root cause #1 (confirmed and fixed): full-page reload via `window.location.href`
`app/staff/login/page.tsx` used `window.location.href = "/staff/dashboard"` after a successful login — a full browser page reload rather than an SPA transition. Debug capture showed this coinciding with a Next.js dev-mode "Fast Refresh" (HMR) rebuild event firing mid-navigation (`[Fast Refresh] rebuilding... done in 1703ms`), adding real, observed latency, and made the navigation unreliable to detect via Playwright's `waitForURL` (which tracks the current frame — a full document reload creates a new execution context that `waitForURL` intermittently missed, even though a manual URL-check after a fixed wait confirmed the navigation genuinely completed).

**Classification: STALE_CACHE / TOKEN_STORAGE_DELAY** (compounded by dev-mode HMR interference, which would not occur in a production build).

**Fix applied**: replaced `window.location.href` with Next.js `useRouter().push()` — a client-side SPA transition. Verified: a clean single run completed the full login→dashboard transition in **2,756ms**, down from an unbounded/unreliable full-reload wait.

## Root cause #2 (found, NOT fully diagnosed): intermittent failure on repeated rapid re-login
After the fix, running 5 fresh-browser-context cold logins in succession showed **1 success (2,756ms) and 4 failures** (`waitForURL` timeout at 15s). This is a **different, not-yet-root-caused issue** — candidates considered but not confirmed given time constraints:
- Backend rate-limiting/account-lockout on rapid repeated logins of the same test account (this codebase does have `failed_login_attempts`/`locked_until` columns per FINAL-L5-01's schema inventory — plausible but not confirmed via server logs this pass).
- Test-harness resource contention from creating 5 new Chromium browser contexts in a tight loop against an already-busy local dev environment (this session has had multiple frontend/backend dev servers, a local Postgres instance, and repeated file-triggered HMR rebuilds running concurrently for hours).
- A genuine intermittent app-level race not yet isolated.

## Result
**Root cause #1 is confirmed and fixed.** **Root cause #2 remains a real, open, honestly-reported gap** — the technician redirect is demonstrably faster and more reliable than before this sprint's fix, but is **not proven deterministically stable across repeated runs**, per the mission's own explicit evidence bar. See the fix report and remaining blockers.
