# CUSTOMER-FRONTEND-01 — Mock/Hardcoded Data Scan

## Scan performed
```
grep -rn "Math.random\|faker\|mockData\|MOCK_MODE\|hardcoded" frontend/customer-app/app frontend/customer-app/components frontend/customer-app/lib
```
Result: **zero matches**.

## Manual review confirms
- Every list/detail page (`home-services`, `book`, `bookings`,
  `bookings/[bookingId]`, `bookings/[bookingId]/rate`) fetches its data through
  `lib/api/customer-home-services.ts`, which calls `apiFetch()` against the real
  `NEXT_PUBLIC_API_URL` backend. No page contains inline static arrays of
  categories, providers, bookings, or prices.
- Loading states use CSS-only skeleton placeholders (`.co-skeleton` divs with no
  text content) — not fake data.
- Unlike tenant-portal (which has a `MOCK_MODE` flag and mock login branch in its
  login page for demo purposes), customer-app's `login/page.tsx` has **no**
  mock-mode branch at all — it always calls the real `customerLogin()` →
  `POST /v1/auth/login`.
- The only "fabricated" strings in the codebase are copy/labels required
  verbatim by the spec (e.g. "Finding the best available provider near you...",
  "No bookings yet...") — these are UI copy, not data.

## Exception noted
`tests/test_customer_frontend_01_scaffold.py` is explicitly out of scope for
this scan per the spec's own carve-out ("except in tests/storybook-demo/loading-skeletons").
