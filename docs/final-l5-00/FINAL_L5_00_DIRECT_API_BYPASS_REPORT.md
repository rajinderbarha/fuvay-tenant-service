# FINAL-L5-00 — Direct API Bypass Report (Parts 14-15)

Scope: `frontend/super-admin`, `frontend/tenant-portal`, `frontend/customer-app` — `app/`,
`components/`, `hooks/`, excluding `__tests__`, `*.test.*`, `*.spec.*`, `e2e/`.

## Method

Grepped `[^a-zA-Z_]fetch\(` (to exclude `refetch(`, `apiFetch(`, `prefetch(`), `axios\(`, and
`XMLHttpRequest` in all three apps outside their central clients
(`super-admin/lib/api.ts`, `tenant-portal/lib/api.ts`, `customer-app/lib/api/*`). No `axios(` or
`XMLHttpRequest` usage exists anywhere in the codebase (0 hits, all 3 apps) — all HTTP is via
`fetch`. `customer-app` has zero raw `fetch(` calls outside `lib/api/client.ts` — fully clean.

## Findings

### super-admin — 5 pages hand-roll `fetch()` with manual auth header instead of `apiFetch`

All five follow an identical pattern: read `serviceos_admin_token` from `localStorage`, build a
`Authorization: Bearer` header, call `fetch(`${API}${endpoint}?${qs}`)` directly, then hand-parse
`json.data`/pagination — duplicating logic `apiFetch` in `lib/api.ts` already centralizes
(base URL, auth header injection, envelope unwrap, error handling).

1. **`frontend/super-admin/app/admin/audit-logs/page.tsx:129`**
   ```ts
   const res = await fetch(`${API}${TAB_CONFIG[tab].endpoint}?${qs}`, { headers: { Authorization: `Bearer ${token}` } });
   ```
   Central client has no dedicated `auditLogsApi` list method for these tab endpoints (spot check:
   `grep -n "auditLogsApi" lib/api.ts` → 0 hits). **Classification: REVIEW_REQUIRED** — no
   equivalent client method exists yet; this needs a new `apiFetch`-based method added to
   `lib/api.ts`, not just a call-site swap.

2. **`frontend/super-admin/app/admin/commission-records/page.tsx:62`**
   ```ts
   const res = await fetch(`${API}/v1/admin/commission-records?${qs}`, { headers: { Authorization: `Bearer ${token}` } });
   ```
   Central client already has `apiFetch<CommissionRecord[]>('/v1/admin/commission-records...')`
   at `lib/api.ts:6233`. **Classification: DIRECT_BYPASS** — a working central-client method for
   this exact resource exists but isn't used (page needs the enterprise pagination envelope,
   which the existing method doesn't return, but the fix is to extend the central method, not
   bypass it).

3. **`frontend/super-admin/app/admin/payments/page.tsx:71`**
   ```ts
   const res = await fetch(`${API}/v1/admin/payments?${qs}`, { headers: { Authorization: `Bearer ${token}` } });
   ```
   Central client already has `apiFetch<PaymentRecord[]>('/v1/admin/payments...')` at
   `lib/api.ts:6221`. **Classification: DIRECT_BYPASS** — same pattern as #2.

4. **`frontend/super-admin/app/admin/refund-requests/page.tsx:70`**
   ```ts
   const res = await fetch(`${API}/v1/admin/refund-requests?${qs}`, { headers: { Authorization: `Bearer ${token}` } });
   ```
   Central client already has `apiFetch<RefundRecord[]>('/v1/admin/refund-requests...')` at
   `lib/api.ts:6483`. **Classification: DIRECT_BYPASS** — same pattern as #2.

5. **`frontend/super-admin/app/admin/home-services/service-jobs/page.tsx:50`**
   ```ts
   const res = await fetch(`${API}/v1/admin/final-records/jobs?${qs}`, { headers: { Authorization: `Bearer ${token}` } });
   ```
   Central client only has a single-record getter, `getJob(jobId)` at `lib/api.ts:8200` — no list
   method for `/v1/admin/final-records/jobs`. **Classification: REVIEW_REQUIRED** — no existing
   list method to swap to; needs a new one added.

   *Common root cause across all 5:* these pages feed a shared `EnterpriseDataGrid`/
   `EnterpriseFilterBar` component whose `fetchFn` prop expects a specific
   `{ items, pagination, sort, filters_applied, available_columns }` envelope shape that the
   existing plain-array `apiFetch<T[]>` client methods don't return, so each page grew its own
   raw-fetch + `wrapLegacy()` adapter instead of extending the central client to return that
   shape. Recommend adding a shared `apiFetchPaginated()` helper in `lib/api.ts` used by all
   enterprise-grid pages, rather than 5 separate hand-rolled `fetch()` calls with duplicated token
   logic.

### super-admin — CSV export downloads (special case, not bypass)

6. **`frontend/super-admin/app/admin/bookings/page.tsx:364`** and
   **`frontend/super-admin/app/admin/customers/page.tsx:304`**
   ```ts
   fetch(`${API_BASE}${path}`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.blob())...
   ```
   Both call `adminBookingsApi.export(params)` / `adminCustomersApi.export(params)` from the
   central client to build the URL/query string, then use raw `fetch` only because the response
   must be consumed as a `Blob` (CSV file download via `URL.createObjectURL`), which `apiFetch`
   (JSON-envelope-only) doesn't support. **Classification: VALID_SPECIAL_CASE.**

### tenant-portal — 2 raw `fetch()` calls

7. **`frontend/tenant-portal/app/(tenant)/media/page.tsx:43`**
   ```ts
   await fetch(session.upload_url, { method: "PUT", body: file, headers: { "Content-Type": file.type } });
   ```
   PUT to a presigned S3/GCS-style upload URL returned by `mediaApi.initiateUpload()` (external
   storage URL, not an internal ServiceOS API route). **Classification: VALID_SPECIAL_CASE**
   (direct-to-storage upload — the standard presigned-URL pattern; `mediaApi.confirmUpload()` is
   correctly called afterward through the central client).

8. **`frontend/tenant-portal/app/login/page.tsx:49`**
   ```ts
   const rt = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/v1/tenant/dashboard/runtime`,
     { headers: { Authorization: `Bearer ${res.access_token}` } }).then(r2 => r2.json());
   ```
   Central client already has `runtimeApi.getRuntime()` → `apiFetch<ProviderDashboardRuntime>('/v1/tenant/dashboard/runtime')`
   at `lib/api.ts:2227`. **Classification: DIRECT_BYPASS**, though with a plausible reason: this
   call happens immediately after login, using `res.access_token` straight from the login response
   rather than the token `apiFetch` would read back out of `localStorage` (avoiding a
   write-then-immediately-read race). Recommend `apiFetch` accept an optional explicit-token
   override so this call-site can use the central client without the race, instead of
   re-implementing the fetch by hand.

### customer-app

No raw `fetch(`/`axios(`/`XMLHttpRequest` calls found anywhere in `app/`, `components/`, or
`hooks/`. All network calls go through `lib/api/client.ts`. **Clean.**

## Central-client spot checks performed

- `commissionApi`/`adminCommissionRecords` list — exists (`lib/api.ts:6233`), bypassed by finding #2.
- `adminPaymentsApi` list — exists (`lib/api.ts:6221`), bypassed by finding #3.
- `refundRequestsApi` list — exists (`lib/api.ts:6483`), bypassed by finding #4.
- `finalRecordsApi.getJob` — exists but single-record only (`lib/api.ts:8200`), no list method (finding #5).
- `auditLogsApi` — no client method exists at all (finding #1).
- `runtimeApi.getRuntime` — exists (`lib/api.ts:2227`), bypassed by finding #8.

## Summary

- **DIRECT_BYPASS:** 4 (commission-records, payments, refund-requests in super-admin; runtime
  fetch in tenant-portal login) — central client methods already exist for these resources but
  the pages call raw `fetch()` instead.
- **REVIEW_REQUIRED:** 2 (audit-logs, service-jobs in super-admin) — no equivalent central-client
  method exists yet, so these aren't simple bypasses; they need new client methods added.
- **VALID_SPECIAL_CASE:** 3 (2 CSV blob-download exports in super-admin, 1 presigned upload PUT
  in tenant-portal).
- **customer-app:** 0 findings, fully clean.
- No `axios()`/`XMLHttpRequest` usage anywhere in the codebase.
