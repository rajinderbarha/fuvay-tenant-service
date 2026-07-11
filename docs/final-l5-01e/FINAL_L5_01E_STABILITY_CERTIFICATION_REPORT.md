# FINAL-L5-01E — Real Chromium Stability Certification (Part 15)

All runs used real Chromium via Playwright (`chromium.launch()`), zero network mocking, against a locally running FastAPI backend (`localhost:8000`) and a freshly restarted, route-warmed Next.js dev server (`localhost:3001`). Each "cold" run uses a brand-new `browser`+`context`; "warm" runs reuse a single browser/page across iterations, clearing `localStorage` between attempts.

| Batch | Required | Result | Evidence file |
|---|---|---|---|
| Cold logins | 20/20 | **20/20 SUCCESS** | `evidence/cold-login-repro-batch.json` |
| Warm logins | 20/20 | **20/20 SUCCESS** | `evidence/warm-login-repro-batch.json` |
| Logout→login cycles | 10/10 | **10/10 SUCCESS** | `evidence/logout-login-repro-batch.json` |
| Expired-session recovery | 5/5 | **5/5 SUCCESS** | `evidence/expired-session-repro-batch.json` |
| Authorized deep-link | 5/5 | **5/5 SUCCESS** | `evidence/authorized-deeplink-repro-batch.json` |
| Unauthorized deep-link | 5/5 | **5/5 SUCCESS_BLOCKED** | `evidence/unauthorized-deeplink-repro-batch.json` |

**Total: 65/65 real-browser runs, zero inconclusive, zero flaky, zero failures**, run after both fixes (duplicate-context removal, test-harness hydration wait) were applied and the dev server was restarted clean (no further source edits during the runs, per rule 2's spirit — determinism was measured against a stable target, not a moving one).

## What each batch proves
- **Cold (20/20)**: a first-time visitor, fresh browser profile, always reaches `/staff/dashboard` with real rendered content ("My Dashboard", "Welcome back, Technician One").
- **Warm (20/20)**: repeated logins within one already-warmed browser/runtime are equally reliable — rules out "only works once per process" theories.
- **Logout→login (10/10)**: each cycle asserts `localStorage.serviceos_tenant_token` is `null` immediately after logout (before the next login), and that the next login still lands cleanly — no stale principal/query state carried across logout (rule 7).
- **Expired-session (5/5)**: a corrupted/invalid token seeded into `localStorage` before first navigation does not hang or crash the app; a subsequent real login still succeeds cleanly.
- **Authorized deep-link (5/5)**: an already-authenticated technician navigating directly to `/staff/jobs` (not via the dashboard) lands on real content, not a sign-in wall.
- **Unauthorized deep-link (5/5)**: an anonymous browser navigating directly to `/staff/jobs` is blocked with a sign-in prompt in all 5 runs — no protected content ever rendered.

## Timing
Cold logins: ~3.4–3.7s each (includes full page load + hydration wait + login POST + dashboard data fetch). Warm logins: ~2.5–2.8s each (routes already compiled). No run exceeded its allotted timeout; no run required a retry.

## Explicit non-negotiable-rule compliance
- Rule 1 (not from 1–2 runs): 65 total runs across 6 categories.
- Rule 2 (no arbitrary sleep to hide a race): the only fixed-duration wait remaining is a 1–1.5s settle after the redirect assertion already resolves true, used purely to let already-fired data-fetch promises complete before reading page text for the JSON evidence log — not a wait *for* the redirect itself, which is asserted via `waitForFunction` on `window.location.pathname`.
- Rule 3/4 (no route-guard bypass, no auth-check disable): unauthorized deep-link batch proves guards are still fully enforced (5/5 blocked).
- Rule 5 (no fabricated sessions): every successful run performed a real `POST /v1/auth/login` against the real backend with the real seeded technician account.
- Rule 6 (no runtime mock data): zero network mocking in any spec.
- Rule 9 (no tokens/credentials in reports): evidence JSON logs response status codes and endpoint paths only, never token values (see `authTimeline` usage — event names and role strings only).
- Rule 10 (real Chromium mandatory): all runs used `chromium.launch()`, not a mocked browser.
