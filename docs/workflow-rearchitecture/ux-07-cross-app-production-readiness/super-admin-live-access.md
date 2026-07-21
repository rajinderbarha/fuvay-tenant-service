# Super Admin Live Access Verification — Round 4, Pass 1 (Workstream 4)

## Outcome: SUPER_ADMIN_LIVE_ACCESS_VERIFIED (real browser, Playwright)

This supersedes the Round 2 API-only verification
(`super-admin-access-investigation.md`) with a genuine browser-driven
check of the real UI, as this pass's brief required.

## Setup

- Backend: FastAPI already running and reachable from WSL at
  `http://172.28.240.1:8000` (`curl .../docs` → 200).
- Frontend: `frontend/super-admin` built for production
  (`npx next build`, `NEXT_PUBLIC_API_URL=http://172.28.240.1:8000`) and
  served via its Next.js standalone server
  (`node .next/standalone/frontend/super-admin/server.js`) on
  `localhost:3000`.
- Browser: Playwright (Chromium, headless, `--no-sandbox` — required
  inside this WSL container) via `npx playwright install chromium
  --with-deps`.
- Credentials: `admin@serviceos.local` / `Password123!`, the repo's own
  documented seed account (`scripts/seed_demo_users.py`), `super_admin`
  role. No password was guessed, no account reset, no role promoted.

## Two environment findings along the way (neither is a product defect)

1. **`next dev` (Turbopack HMR) did not work for this check.** Under
   `next dev`, the browser's WebSocket connection to Turbopack's HMR
   endpoint (`ws://.../_next/webpack-hmr`) failed repeatedly
   (`net::ERR_INVALID_HTTP_RESPONSE`) inside this WSL container, and as a
   side effect client-side hydration never appeared to complete: clicking
   the theme toggle did nothing, and the client-side auth-redirect
   `useEffect` in `AdminLayout.tsx` (which sends unauthenticated users to
   `/login`) never fired, leaving an un-hydrated, non-interactive
   dashboard shell rendered indefinitely on screen even with no token.
   Switching to a **production build + `next start`-equivalent
   standalone server** (no HMR socket at all) immediately fixed this: the
   same unauthenticated root request correctly redirected to `/login`,
   and every click worked. This is logged as a dev-server/WSL environment
   limitation for future test authors, not a source defect — the app's
   auth guard behaves correctly.
2. **CORS 404... actually CORS block, not 404** on a `next start` run
   bound to port 3100: the backend's `ALLOWED_ORIGINS`
   (`app/config.py`) is a fixed list that includes `http://localhost:3000`
   for the Super Admin Portal but not arbitrary ports. Serving on
   `localhost:3000` (matching the backend's actual configured origin)
   resolved this immediately. Not a defect — just needed the app on its
   documented port for this environment's backend CORS config.

## Verified live, via real UI interaction (not just API calls)

1. **Login**: navigated to `http://localhost:3000/` → real redirect to
   `/login` → filled the real login form → submitted → landed on
   `/admin/dashboard`. `localStorage` afterward held real
   `serviceos_admin_token` / `serviceos_admin_refresh` values (real JWTs
   from the running backend, not mocked).
2. **Dashboard loads with real data**: `main` content included live
   figures — "Platform Health 90 / 100 healthy", "Active Tenants 4",
   "Pending Admin Actions 12", "Critical Alerts 0 All clear" — sourced
   from the actual backend, not placeholder/mock text.
3. **Tenant list view**: navigating to `/admin/tenants` rendered the real
   tenant table ("Total Providers 4", per-status breakdown, verification
   filters) — genuine data, not an error or empty state.
4. **Catalog/pricing config access**: `/admin/pricing` rendered the real
   "Pricing Rules" page ("Platform-wide category and service minimum
   prices...").
5. **Package/credit area**: `/admin/packages` rendered the real "Package
   & Plan Management" page with a live count ("Total Packages 1").
6. **Logout**: the header's "Log out" button is initially covered by a
   full-screen onboarding "tour" overlay (`useTour()`,
   `z-index: 498`) on first dashboard visit — clicking "Skip tour"
   dismissed it (this overlay behavior is expected first-run onboarding
   UX, not a defect; documented in `frontend-corrections-report.md` so a
   future round doesn't mistake an occluded button for a broken one).
   After dismissing it, clicking "Log out" correctly: cleared
   `serviceos_admin_token` from `localStorage`, navigated back to
   `/login`, and a subsequent direct navigation to `/admin/dashboard`
   correctly bounced back to `/login` (session genuinely terminated, not
   just a UI-only redirect).

## Read-only admin role check — not available, not fabricated

`scripts/seed_demo_users.py` (the repo's own committed demo-account seed
script) defines exactly four roles: `super_admin`, `tenant_owner`,
`technician`, `customer`. No read-only/limited-admin seed account exists.
Per this pass's explicit instruction not to fabricate one, this check was
**skipped** rather than invented — no read-only account was created, no
existing account was altered to simulate one.

## What was explicitly NOT done

No password guessing, no credential reset, no new user creation, no role
promotion/aliasing. The `admin@serviceos.local` credential used is the
same pre-existing, version-controlled, dev-only seed credential Round 2
already used and documented.
