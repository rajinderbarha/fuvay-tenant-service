# FINAL-L5-03 — Direct Fetch and Duplicate Client Removal

Real scans this sprint (not carried from memory):
- `grep` for a word-boundary-correct `fetch(` pattern (not matching `apiFetch(`/`.refetch(`, which an earlier naive substring grep incorrectly flagged ~140 files on) across `frontend/{super-admin,tenant-portal,customer-app}/app` and `/components`.
- `grep` for `axios(`, `axios.create(`, `XMLHttpRequest` — **zero matches anywhere** in all 3 apps' source.

## Classified occurrences

| File | Classification | Resolution |
|---|---|---|
| `super-admin/app/admin/audit-logs/page.tsx` | `MIGRATE_TO_SHARED_CLIENT` | Fixed — `apiFetchPaginatedRaw` |
| `super-admin/app/admin/refund-requests/page.tsx` | `MIGRATE_TO_SHARED_CLIENT` | Fixed |
| `super-admin/app/admin/payments/page.tsx` | `MIGRATE_TO_SHARED_CLIENT` | Fixed |
| `super-admin/app/admin/commission-records/page.tsx` | `MIGRATE_TO_SHARED_CLIENT` | Fixed |
| `super-admin/app/admin/home-services/service-jobs/page.tsx` | `MIGRATE_TO_SHARED_CLIENT` | Fixed |
| `tenant-portal/app/login/page.tsx` (runtime fetch) | `MIGRATE_TO_SHARED_CLIENT` | Fixed — `categoryDashboardApi.getRuntime()` |
| `tenant-portal/app/(tenant)/media/page.tsx` (`fetch(session.upload_url, ...)`) | `VALID_SPECIAL_CASE` | Not changed — this is a direct `PUT` to a backend-issued pre-signed storage URL; routing it through `apiFetch` would be actively wrong (it would attach our own API's Bearer token and JSON content-type to a storage-provider request) |
| `apiFetch`'s own internal `fetch()` calls (all 3 apps' `lib/api.ts`/`lib/api/client.ts`) | `CANONICAL_CLIENT` | This *is* the canonical client — not a bypass |
| `apiFetchMultipart`'s internal `fetch()` (tenant-portal) | `CANONICAL_CLIENT` | Dedicated multipart variant, correctly separate from the JSON `apiFetch` (different headers/timeout needs) |

## Acceptance check
**0 unexplained production direct API bypasses** — met. The one remaining raw `fetch()` in application code (`media/page.tsx`) is explained and justified (pre-signed upload URL), matching the mission's own "Valid special cases" list ("Server-only framework fetch with documented caching requirements" analog — here, a documented storage-upload requirement).

Machine-readable version: `direct-fetch-inventory.json`.
