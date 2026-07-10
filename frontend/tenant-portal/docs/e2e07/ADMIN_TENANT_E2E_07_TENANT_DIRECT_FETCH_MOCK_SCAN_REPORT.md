# E2E-07 Tenant Direct Fetch / Mock Data Scan Report
**Date:** 2026-07-10  
**Analysis:** grep scan + fixes applied

---

## Direct `fetch()` Call Scan

### Files Fixed This Sprint

All 6 files were using raw `fetch()` with manually extracted tokens instead of `apiFetch` from `lib/api.ts`.

| File | Endpoint | Fix Applied |
|---|---|---|
| `app/(tenant)/appointments/page.tsx` | `/v1/appointments/staff` | Replaced with `apiFetch` |
| `app/(tenant)/provider/complaints/page.tsx` | `/v1/provider/complaints` | Replaced with `apiFetch` |
| `app/(tenant)/provider/refund-requests/page.tsx` | `/v1/provider/refund-requests` | Replaced with `apiFetch` |
| `app/(tenant)/provider/reviews/page.tsx` | `/v1/provider/reviews` | Replaced with `apiFetch` |
| `app/(tenant)/provider/service-invoices/page.tsx` | `/v1/provider/service-invoices` | Replaced with `apiFetch` |
| `app/(tenant)/service-jobs/page.tsx` | `/v1/provider/service-jobs` | Replaced with `apiFetch` |

### Why These Were Direct `fetch()` Calls

These 6 pages use `EnterpriseDataGrid` with a `fetchFn` callback that needs to return paginated data. The original implementation bypassed `lib/api.ts` to handle the raw response structure. All were converted to use `apiFetch<Record<string, unknown>>(path)` which:

1. Injects the auth token centrally
2. Handles 401 with automatic token refresh
3. Handles errors with `ServiceOSError` typed exceptions
4. Follows the Level 5 API client standard

### Pattern After Fix

```tsx
import { apiFetch } from "../../../lib/api";

const fetchFn = useCallback(async (params: Record<string, unknown>) => {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v != null && v !== "") qs.set(k, String(v)); });
  const d = await apiFetch<Record<string, unknown>>(`/v1/provider/service-jobs?${qs}`);
  if ((d as Record<string, unknown>)?.pagination) return d;
  return wrapLegacy(d, params);
}, []);
```

### `apiFetch` Export

`lib/api.ts` was updated to export `apiFetch` (previously private):
```ts
// Before: async function apiFetch<T>(...)
// After:
export async function apiFetch<T>(path: string, options: RequestInit = {}, skipAuth = false): Promise<T>
```

## Mock Data Scan

Searched for hardcoded mock data in `app/(tenant)/`:

| Pattern | Files Found | Notes |
|---|---|---|
| `"Your Business"` (hardcoded) | 5 files | Loading-state fallbacks — acceptable |
| `"Demo AC Services"` | 0 | CLEAN |
| Hardcoded arrays of objects as placeholder data | None detected | CLEAN |
| `const MOCK_` or `const FAKE_` | None detected | CLEAN |

### "Your Business" Assessment

The string `"Your Business"` appears as a loading-state fallback (shown for < 500ms while `useTenant` resolves live data). This is an acceptable UX pattern — not hardcoded business data. It is not seeded data and does not appear in user-facing reports or persistent state.

## Remaining `fetch()` Calls (Accepted)

`lib/api.ts` internally calls `fetch()` — this is the API client itself and is correct. No other direct `fetch()` calls remain in `app/(tenant)/`.

**Status: PASS** — All 6 direct `fetch()` bypasses fixed. No mock data found.
