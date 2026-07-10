# FRONTEND-CONNECT-01 — Direct Fetch Scan

`grep -rl "fetch(\|axios\.\|XMLHttpRequest"` across `app/`, `components/`, `hooks/` in both frontends returned ~140 file hits. Manual sampling showed the overwhelming majority are **false positives**: `useApi()`'s own `refetch()` method call (e.g. `summary.refetch()`, `health.refetch()`) matches the substring `fetch(`. `hooks/useApi.ts` itself also matches (it's the one legitimate place `fetch`-adjacent logic is defined, wrapping `apiFetch`).

## Genuine direct `fetch()` calls found (sampled/spot-checked)
1. `frontend/tenant-portal/app/login/page.tsx:49` — `fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/v1/tenant/dashboard/runtime`, ...)`. **Classify: allowed existing.** Runs before login/auth context exists (pre-auth runtime probe), can't go through `apiFetch()` which assumes a token may exist; uses the same base-URL fallback convention as `lib/api.ts`.
2. CSV/export streaming and SSE endpoints in the 13 files listed in the API Config report (`audit-logs`, `bookings`, `commission-records`, `customers`, `payments`, `refund-requests`, etc.) — these call `fetch()` directly because they stream a file download or an event stream, which `apiFetch<T>()` (designed for JSON envelope responses) doesn't support. **Classify: allowed existing / migrate later** — a typed `apiFetchBlob()`/`apiFetchStream()` wrapper would be the correct long-term fix but is out of scope for this sprint (no genuine bug, just duplication).
3. `frontend/super-admin/app/admin/intelligence/page.tsx.tmp.13128.892018edb538` — a stray editor temp file, not part of the build (Next.js ignores non-`.tsx` files under `app/`). **Classify: test-only/dead file, safe to ignore**, not a runtime risk. Recommend deleting in a future cleanup sprint (not touched here to avoid unrelated changes).

## No fetch calls found that:
- hit a hardcoded non-localhost/production URL
- attach or log a raw token
- bypass the `apiFetch()` error/401/403 handling for a page that has a straightforward JSON-envelope equivalent already available

## Verdict
No blocking direct-fetch violations. The duplicated `localhost:8000` fallback string (13 files) is the only concrete DRY cleanup item, tracked in Remaining Blockers as "migrate later."
