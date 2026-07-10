# Tenant My Offerings — Integration Report

## Live-verified endpoint matrix (provider@serviceos.in, tenant_owner, tenant 34b427a7-b2be-496c-b826-6d51bb181248)

| Endpoint | Method | Before fix | After fix |
|---|---|---|---|
| `/v1/provider/offerings/available` | GET | 0 offerings (wrong table) | **200, 15 offerings incl. AC Repair** |
| `/v1/provider/offerings/enabled` | GET | 0 (consistent but wrong table) | 200, real data |
| `/v1/provider/offerings/enabled` | POST (enable) | **500** (ON CONFLICT / partial index mismatch) | 200, offering created |
| `/v1/provider/offerings/enabled/{id}` | GET | `provider_enabled_offering_id` missing | 200, field present |
| `/v1/provider/offerings/enabled/{id}/refresh-readiness` | POST | 200 (stub — see Remaining Blockers) | 200 (still a stub) |
| `/v1/admin/master-services/{id}/types` | GET | 0 mappings | **200, 2 mappings (Split AC, Window AC)** |
| `/v1/admin/master-services/{id}/brands` | GET | 0 mappings | **200, 3 mappings (LG, Samsung, Voltas)** |
| `/v1/admin/master-services/{id}/issues` | GET | endpoint didn't exist | **200, 8 real mappings (incl. AC Not Cooling)** |
| `/v1/catalog/master/service-options?master_service_id=` | GET | — | 200, 2 real options (Gas Refill, Emergency Visit) |
| `/v1/provider/brands/services/{id}/available` | GET | — | 200, 3 brands (dedicated provider endpoint) |
| `/v1/pricing/tenants/{id}/price-preview` | POST | — | 200, real pipeline (city floor ₹50 for Split AC in Ludhiana tier_3) |
| `/v1/tenant/service-areas` | GET | — | 200 (reused from My Status sprint) |
| `/v1/provider/team-members` | GET | — | 200 (reused) |
| `/v1/tenants/{id}/audit-log` | GET | — | 200 (reused) |

## End-to-end flow verified live

1. Logged in as `provider@serviceos.in`.
2. Confirmed `GET /v1/provider/offerings/available` returned 0 offerings before the fix, live
   500'd on the underlying legacy-table query error confirmed in backend logs
   (`asyncpg.exceptions.UndefinedTableError` on `provider_offering_bookable_statuses`, and
   before that a silent-zero-rows condition on `master_offerings`).
3. Applied the query rewrite; restarted backend; re-confirmed 15 real offerings including AC
   Repair.
4. Mapped Split AC/Window AC (types) and LG/Samsung/Voltas (brands) to AC Repair via the real
   admin API (`admin@serviceos.in`, super_admin) — these were the two coverage dimensions with
   zero real mappings.
5. Enabled AC Repair for the tenant via `POST /v1/provider/offerings/enabled` — hit the
   `ON CONFLICT` bug, fixed, retried successfully.
6. Confirmed `GET /v1/provider/offerings/enabled` now returns the real enabled row with a
   correct `provider_enabled_offering_id`.
7. Confirmed `GET /v1/provider/offerings/available` now shows `is_already_enabled: true` for
   AC Repair, consistent with step 6.
8. Called `POST .../refresh-readiness` — succeeded but confirmed it is a stub (resets
   `readiness_status` to `"pending"` without evaluating real blockers) — documented honestly in
   Remaining Blockers rather than presented as a working readiness engine.
9. Called the real pricing preview endpoint for Split AC + Ludhiana + 141001 — got a real,
   backend-computed price (₹50, tier_3 city floor, no tenant override set yet) — confirms "do
   not calculate authoritative price in frontend" is satisfied structurally (the frontend never
   computes a price; it only displays what this endpoint returns).

## request_id propagation

`useApi`/`useAction` (already fixed in Phase 7B) expose `requestId` from every error; the new
`SectionError` component in this page renders it, plus the failing section name, on every
section-level failure (Available, Enabled, Readiness, Activity).
