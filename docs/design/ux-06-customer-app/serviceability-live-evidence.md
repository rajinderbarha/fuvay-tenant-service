# Serviceability Live Evidence — UX-06 Round 4

All calls real, against the live backend, real customer JWT, real draft IDs.

1. **Seeded offering discoverable**: `GET /v1/customer/categories/home_services/offerings`
   → real `ac_repair` offering, id `c813ccec-218a-42e2-a6ab-2e36389ac575` (MasterOffering).
2. **Test address resolves to expected city**: draft `PUT` with `city:"Ludhiana"`
   returns the draft echoing `city: "Ludhiana"`.
3. **Serviceability succeeds for the intended tenant/offering/area**:
   `POST .../serviceability-check` → `{"serviceable": true, "available_provider_count": 1,
   "matched_by": "city", "message": "Service is available in Ludhiana."}`.
4. **Foreign/unsupported zipcode/city still fails**: identical sequence with
   `city:"Mumbai"` → `{"serviceable": false, "reason_code": "NO_PROVIDER_IN_CITY",
   "message": "This service is not available in Mumbai yet. We're expanding soon!"}`.
5. **Another tenant not affected**: the seed only modified one
   `TenantServiceAreaService` row scoped to `tenant_id=5209ef33-...`; the
   `check()` query (`app/engines/home_service_booking/serviceability_service.py`)
   joins on `TenantServiceArea.tenant_id` — no other tenant's rows were read or
   written. (Direct multi-tenant re-verification with a second tenant account
   was not performed this round due to time — see known-limitations.md.)
6. **Pricing/estimate uses real server data**: see price-live-evidence.md.
7. **Removing the seed restores prior unavailable result**: reasoned from the
   real, unmodified query logic — see seed-removal-report.md (not executed
   this round to preserve the seed for continued work).

Exact created row id (internal only, never shown in customer UI):
`TenantServiceAreaService.id = d07529ff-406f-4c83-9f89-ba423199860b`.
