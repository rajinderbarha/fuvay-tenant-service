# FRONTEND-CONNECT-01 — API Base URL Config Report

## Canonical config
- super-admin: `frontend/super-admin/lib/api.ts:11` — `const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";`
- tenant-portal: `frontend/tenant-portal/lib/api.ts` — same pattern, same env var name.
- Both are read once at module load and used by every call inside `apiFetch<T>()`. No page imports a different base URL constant.

## Fallback behavior
- Fallback is `http://localhost:8000`, applied only when `NEXT_PUBLIC_API_URL` is unset (local dev). No `console.warn` is emitted on fallback today — this is a minor gap, not a blocker (dev-only default, not reachable in a real deployed build since prod compose sets `NEXT_PUBLIC_API_URL`).

## Hardcoded URLs found outside lib/api.ts
`grep -rl "localhost:8000" frontend/*/app` found 13 page files duplicating the exact same fallback expression instead of importing a shared constant from `lib/api.ts`:
- super-admin: `app/admin/audit-logs/page.tsx`, `app/admin/bookings/page.tsx`, `app/admin/commission-records/page.tsx`, `app/admin/customers/page.tsx`, `app/admin/home-services/service-jobs/page.tsx`, `app/admin/payments/page.tsx`, `app/admin/refund-requests/page.tsx`
- tenant-portal: `app/(tenant)/appointments/page.tsx`, `app/(tenant)/provider/complaints/page.tsx`, `app/(tenant)/provider/refund-requests/page.tsx`, `app/(tenant)/provider/reviews/page.tsx`, `app/(tenant)/provider/service-invoices/page.tsx`, `app/(tenant)/service-jobs/page.tsx`, `app/login/page.tsx`

All 13 use the identical guarded pattern `process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"` for one-off direct `fetch()` calls (CSV export streaming, SSE, or a pre-login runtime check) — none hardcode a bare/unguarded URL, and none hardcode a production URL. Classified as **should migrate later**: functionally safe today (same fallback semantics as `lib/api.ts`), but they duplicate the constant instead of exporting/importing `API_BASE` from `lib/api.ts`. Not touched in this sprint to stay within the "extend, don't bulldoze" mandate — flagged in Direct Fetch Scan below and in Remaining Blockers.

## Verdict
Base URL config is centralized and correct in the canonical client. The 13 duplicated fallbacks are a lint/DRY issue, not a correctness or security issue.
