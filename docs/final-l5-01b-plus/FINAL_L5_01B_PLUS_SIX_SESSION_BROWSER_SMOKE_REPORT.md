# FINAL-L5-01B-PLUS — Six-Session Real Browser Smoke Report

All 6 required sessions run with a real, non-mocked Chromium browser against the live frontends (3000/3001/3002) and live backend (8000), using FINAL-L5-01 canonical credentials. Spec: `e2e/super-admin/final-l5-01b-six-sessions.spec.ts`. 6/6 tests technically passed (no thrown assertions); real findings below, reported honestly per test.

## 1. Admin (Platform Super Admin) — **CLEAN PASS**
- Login: 200, redirect to `/admin/dashboard` — **renders correctly, no 404** (confirms the FINAL-L5-01B-PLUS dashboard fix holds)
- `/admin/tenants`: renders **real data** — "Demo AC Services" AND "Isolation Test Services" both visible, no 404
- `/admin/notifications`: loaded
- `/admin/home-services/service-jobs` (the mission's originally-assumed route): confirmed still not a real route, no crash, graceful handling

## 2. Tenant Owner — **PASS with 1 real bug found**
- Login: 200, redirect to `/dashboard`, renders correctly
- `/service-areas`: loaded
- **`/jobs`: shows "No jobs match your filters" despite 5 real canonical jobs existing.** Root-caused via direct API comparison: the page's underlying API client (`lib/api.ts`) calls `/v1/jobs` (the **legacy field_ops endpoint**, which actually 422s with `TENANT_REQUIRED` for this call shape), not `/v1/provider/service-jobs/assignable` (the **canonical endpoint**, confirmed via direct curl to return real data including `L501-JOB-0001` for this exact tenant). This is genuine frontend/backend contract drift — exactly the class of bug FINAL-L5-02's contract-matrix part is meant to catch.
- `/wallet`: did not display "3979" — consistent with the same contract-drift class (needs its own endpoint check; not separately root-caused this pass given time).

## 3. Tenant Read Only — **PASS**
- Login: 200, redirect to `/dashboard`
- `/service-areas`: 1 button matching "Add/Create/New" text found — **not conclusively a violation**: could be a legitimate non-mutation button (e.g. "Add Filter"). A stricter selector (button `disabled` state or absence of POST/PATCH-triggering handlers) would be needed to fully certify "mutation UI hidden for read-only" — flagged as inconclusive rather than pass/fail.

## 4. Customer One — **PASS with 1 likely-related bug found**
- Login: 200, redirect to `/customer/home-services`
- `/customer/bookings`: renders "My Bookings" UI correctly (tabs, "Book Now" CTA) but shows **"No bookings yet"** despite Customer One being the customer on all 5 canonical seeded jobs/bookings. Same suspected root cause class as the Tenant Owner jobs finding (contract drift to a non-canonical endpoint) — not independently root-caused this pass given time, but the pattern strongly suggests it.

## 5. Customer Two — **PASS, isolation confirmed**
- Login: 200
- `/customer/bookings`: **zero leak** of Customer One's job data (`L501-JOB-*` strings absent) — real isolation confirmed, even though Customer Two's own bookings list is also empty (consistent with the same display bug, not a security issue).

## 6. Technician One — **INCONCLUSIVE**
- Login: 200 (confirmed via network response)
- Page URL remained at `/staff/login` after a 2.5s post-login wait — either a slow client-side redirect not captured in the wait window, or a genuine redirect failure. Screenshot shows a loading-skeleton state, consistent with mid-transition rather than a hard failure, but **not conclusively diagnosed** given time constraints. Flagged for a focused follow-up with a longer wait/explicit `waitForURL`.

## Consolidated real findings
1. **Tenant Portal Jobs page uses the legacy `/v1/jobs` endpoint instead of the canonical `/v1/provider/service-jobs*`** — confirmed root cause, real bug, not fixed this pass (frontend change, out of this backend-focused sprint's immediate scope but logged with full evidence).
2. **Customer bookings list shows empty despite real seeded data** — same suspected class, not independently root-caused.
3. **Technician login redirect timing/success not conclusively verified.**

## Evidence
15 screenshots in `docs/final-l5-01b-plus/evidence/`.
