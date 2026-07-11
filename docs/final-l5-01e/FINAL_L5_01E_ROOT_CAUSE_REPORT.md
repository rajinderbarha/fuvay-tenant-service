# FINAL-L5-01E — Root Cause Report

## The instability was NOT the application's redirect logic

FINAL-L5-01D fixed one real bug (`window.location.href` → `router.push()`) and left the redirect unstable at 1/5 repeated runs. This sprint set out to find "a second contributing root cause" per the mission brief and did — but it was not in the application's auth/redirect code at all.

## Root cause #1 (dominant): Turbopack dev-mode on-demand route compilation racing with browser automation

Next.js dev mode (Turbopack) compiles each route **lazily, on first visit**, not ahead of time. The first `GET /staff/login` after a dev-server (re)start took **21.9s** to compile (captured live in the dev server log this sprint: `GET /staff/login 200 in 21.9s (next.js: 21.6s, application-code: 291ms)`). If a test (or a real user) begins interacting with the page before that compile finishes, one of two things happens:
1. In-flight static chunk requests get aborted mid-navigation as Turbopack swaps in the freshly compiled bundle (`net::ERR_ABORTED` on `_next/static/chunks/*`), silently discarding the click.
2. The page hot-reloads/re-hydrates *after* Playwright has already written values into the (not-yet-hydrated) controlled `<input>` DOM nodes; when React attaches, it reconciles those inputs back to their initial empty `useState("")` values, silently wiping the typed email/password before submit — reproduced live this sprint (form showed "Both fields are required." despite `page.fill()` having "succeeded").

**This is a dev-server-only artifact.** Production builds (`next build && next start`) pre-compile every route; there is no on-demand compilation and no Fast Refresh, so this exact class of race cannot occur in production. It is also very plausibly the reason the FINAL-L5-01D session (which was itself actively editing files while testing, in a single very long-running dev server) observed instability: the same dev server was serving increasingly stale/recompiling bundles throughout that testing.

**Fix**: reproduction scripts now (a) warm each route once with a plain `curl`/`fetch` before the test batch begins, and (b) wait for a real hydration signal (`__reactFiber`/`__reactProps` present on the email input) before filling the form, instead of proceeding immediately after `domcontentloaded`. This is test-harness correctness, not a production code change, and does not violate rule 2 ("no arbitrary sleep/setTimeout to hide a race") — it waits for a specific, verifiable condition (hydration attached), not a fixed delay.

## Root cause #2 (real, fixed): duplicate `useStaffContext()` instances

Independent of the above, `frontend/tenant-portal/app/staff/dashboard/page.tsx` called `useStaffContext()` a second time in addition to `StaffLayout`'s own call — two uncoordinated hook instances, each firing its own `/v1/auth/me` request and resolving through its own separate state machine on every dashboard load. This is a real, source-level violation of mission rule 8 ("do not issue duplicate login/profile requests"), independent of whether it was the dominant cause of the observed flakiness. Fixed via `StaffContextProvider`/`useStaffContextValue()` — see `FINAL_L5_01E_TECHNICIAN_AUTH_FLOW_INVENTORY.md` and the Bug Fix Register.

## What was ruled out (with evidence, not assumption)
- **Middleware/client-guard conflict** — no `middleware.ts` exists for tenant-portal at all (confirmed by directory listing); only client-side guarding via `StaffLayout` exists. Not applicable.
- **Access-token near-expiry / refresh race** — access tokens are minted with an 8-hour expiry; a token used seconds after login is nowhere near expiry, so `apiFetch`'s 401→refresh path cannot be involved in a fresh-login failure.
- **JTI collision / blacklist false-positive** — JTIs are `uuid.uuid4()`-generated; Redis blacklist check fails open on Redis unavailability. No plausible source of a spurious 401 on a fresh token.
- **Account lockout** — ruled out in FINAL-L5-01D via direct DB check (`failed_login_attempts=0`); reconfirmed not relevant here since batches this sprint used a clean canonical seed.

## Evidence
Live dev-server log showing the 21.9s first-compile: captured in this sprint's terminal session (not re-pasted here to avoid duplicating raw logs — reproducible by restarting the dev server and requesting `/staff/login` cold).
Chromium reproduction: `docs/final-l5-01e/evidence/cold-login-repro-batch.json` (20/20 SUCCESS after applying both fixes) and `warm-login-repro-batch.json` (20/20 SUCCESS).
