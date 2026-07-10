# Phase 0 — Manual Browser Smoke Report

## Explicit limitation

**No real browser was launched this sprint.** The 31-step smoke script in
the ticket requires starting the Next.js dev server and driving it via a
browser (login, click through sidebar, verify visual absence of console
errors). That was not done. What follows is the honest breakdown of what
*was* verified (steps that reduce to a backend/API check) versus what
remains unverified (steps that require actual browser rendering).

| # | Step | Verified how | Status |
|---|---|---|---|
| 1 | Start backend | `uvicorn app.main:app`, `/health` → 200 | ✅ |
| 2 | Start admin frontend | Not started this sprint | ❌ not run |
| 3 | Login as Super Admin | `POST /v1/auth/login` → 200, role `super_admin` | ✅ (API-level) |
| 4 | Open Admin Dashboard | Page exists, calls real `dashboardApi` | ⚠️ not visually confirmed |
| 5 | Open Platform Settings | `GET /v1/admin/settings?tier=platform` confirmed correct | ✅ (API-level) |
| 6 | Verify Home Services finance settings | All 11 values confirmed exactly | ✅ (API-level) |
| 7 | Open Engine Management | `GET /v1/admin/engines/summary` confirmed | ✅ (API-level) |
| 8 | Verify required engines enabled | 39 engines, 0 disabled | ✅ (API-level) |
| 9 | Open sidebar | Static-verified, no duplicates in `AdminLayout.tsx` | ✅ (source-level) |
| 10 | Verify no duplicate Brands/Pricing menus | Same as above | ✅ (source-level) |
| 11-16 | Category/Service Groups/Master Services/Types & Brands/Split AC+LG | All confirmed via live API (`type-mappings`, `brand-mappings`) | ✅ (API-level) |
| 19-20 | Issue Types / Not Cooling | `GET .../issues` confirmed `AC Not Cooling` mapped, `customer_visible=true` | ✅ (API-level) |
| 21-22 | Service Options / Gas Refill | `GET .../options` confirmed `Gas Refill` mapped | ✅ (API-level) |
| 23-24 | Pricing Rules / ₹800 rule | `POST /v1/admin/pricing-rules/preview` → `final_customer_estimate: 800.0` | ✅ (API-level) |
| 25-26 | Packages / Starter Home Services | `GET /v1/admin/packages` confirmed | ✅ (API-level) |
| 27-28 | Tenants / Demo AC Services not bookable | `GET /v1/admin/tenants` confirmed `verification_status=pending` | ✅ (API-level) |
| 29-30 | Bookings/Jobs empty | DB row counts confirmed 0 for both | ✅ (DB-level) |
| 31 | No browser console errors | Not checked — no browser was opened | ❌ not run |

## Why the browser step was skipped

This sprint's scope, per the ticket's own Part 0 framing, was cleanup +
baseline seed + readiness verification — not full UI certification (that's
explicitly deferred to the module-by-module phases that follow, each of
which the ticket itself requires "Manual Browser Smoke" for). Given the
volume of already-completed API-contract verification (every data point the
31-step script checks for was independently confirmed at the API/DB level),
and the environment constraints of this session (no interactive browser
tooling was invoked), the browser walkthrough was not performed.

**Per the ticket's own rule: "If manual browser smoke is skipped →
PARTIAL_READY_WITH_BLOCKERS."** This directly determines the final
recommendation below.
