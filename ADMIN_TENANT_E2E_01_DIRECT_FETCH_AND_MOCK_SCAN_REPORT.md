# ADMIN_TENANT_E2E_01 — Direct Fetch / Mock Data Scan Report

## Direct fetch()/axios usage
- ~140 files across both apps call `fetch(` directly rather than exclusively through a single wrapper.
  Sampled a representative set: the large majority go through `lib/api.ts` helper functions that
  internally use `fetch` with `process.env.NEXT_PUBLIC_API_URL`. Classification: **safe placeholder /
  existing pattern**, not a runtime blocker, since `NEXT_PUBLIC_API_URL` is correctly set in both
  `.env.local` files and `NEXT_PUBLIC_USE_MOCK=false`.
- 14 files use a `process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"` fallback-default
  pattern (both apps): `admin/audit-logs`, `admin/bookings`, `admin/commission-records`,
  `admin/customers`, `admin/home-services/service-jobs`, `admin/payments`, `admin/refund-requests`
  (super-admin); `(tenant)/appointments`, `(tenant)/provider/complaints`,
  `(tenant)/provider/refund-requests`, `(tenant)/provider/reviews`,
  `(tenant)/provider/service-invoices`, `(tenant)/service-jobs`, and `login/page.tsx` (tenant-portal).
  Classification: **safe placeholder** — this is a fallback for local dev only, and the fallback value
  matches the actual configured backend in this environment (localhost:8000), so it is not presently a
  runtime blocker, but should be migrated to a single shared constant in a later cleanup sprint
  (classification: **needs migration later**).

## Mock data
- `frontend/super-admin/lib/mock.ts` (120 lines) — contains `MOCK_TENANTS`, `MOCK_KPIS`,
  `MOCK_REVENUE`, `MOCK_JOBS_CHART`, etc. **Checked for actual imports**: `grep` for
  `from ".../mock"` / `from './mock'` across `super-admin` (excluding `node_modules`) returned **zero
  matches** — this file is currently dead code, not imported or rendered anywhere in the live app.
  Classification: **safe placeholder (unreferenced)** — confirmed not a runtime blocker, but flagged
  for deletion or storybook-style relocation in a later cleanup sprint since it duplicates fake data
  that could accidentally get wired in later.
- No `mockJobs`, `mockLedger`, `mockNotifications`, `fakeAudit`, `fakePricing`, `dummyServices`, or
  `sampleBookings` identifiers were found anywhere in either app's `app/` tree (0 matches).
- `MOCK_MODE` constant exists in both `lib/api.ts` files, gated by `NEXT_PUBLIC_USE_MOCK`, currently
  `false` in both apps — confirmed the apps are running against the real backend for all testing in
  this sprint (verified via real request logs in `evidence/*-requests.json` showing real
  `/v1/auth/login` calls, and via the real 200/404 API responses captured in Part 8).
- The tenant login page previously had a hardcoded `"Demo AC Services"`-adjacent placeholder
  ("Rahul AC Services") only inside the `MOCK_MODE` branch of `login/page.tsx` (line 24) — this branch
  is dead in this environment since `MOCK_MODE=false`; classification: **test fixture, gated off**.

## Result
No runtime-blocking mock data found. One dead mock file flagged for cleanup, one fallback-URL pattern
flagged for later migration. Nothing required immediate deletion.
