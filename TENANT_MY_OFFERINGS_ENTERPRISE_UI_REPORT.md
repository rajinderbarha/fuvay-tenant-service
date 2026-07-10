# Tenant My Offerings — Enterprise UI + Functionality Upgrade Report

## Route

`frontend/tenant-portal/app/(tenant)/provider/offerings/page.tsx` → `/provider/offerings`. The
real, existing route (confirmed via `lib/nav-config.ts`, `TenantLayout.tsx`'s Setup group, and
`tenant_engine/portal_router.py`'s per-vertical navigation config, all pointing to
`/provider/offerings`). None of the ticket's suggested alternate routes exist or were created.

## Hard gate: SATISFIED

AC Repair exists in the platform catalog (`master_services`) and now appears as a real,
available offering for the certified tenant — confirmed live. Root cause was that
`GET /v1/provider/offerings/available` queried an empty, orphaned legacy table
(`master_offerings`, 0 rows) instead of the real, populated catalog table (`master_services`,
6 rows). Full diagnostic trail in `TENANT_MY_OFFERINGS_CATALOG_DIAGNOSTIC_REPORT.md`.

## What changed

- **Backend**: rewrote 2 endpoints (`available`, `enabled`) to query the real catalog; fixed a
  live 500 on offering-enable (`ON CONFLICT` vs. partial unique index mismatch); fixed a
  frontend/backend field-name mismatch (`provider_enabled_offering_id`) across 6 call sites;
  added 1 new endpoint (`GET .../issues`) to fill a genuine gap (issue-type coverage was real
  data with no read access); seeded 5 real type/brand mappings for AC Repair via the real admin
  API (Split AC, Window AC, LG, Samsung, Voltas) since those two coverage dimensions had zero
  mappings even though the base catalog entities existed.
- **Frontend**: page rewritten from a basic 3-tab/empty-state layout into an 11-section
  enterprise console — breadcrumb, header, hero, 8 KPI cards, 4 tabs (added Catalog
  Diagnostics), enriched catalog cards, enriched enabled-offerings table, readiness issues
  panel, an enhanced Enable/Edit wizard with real type/brand/issue/option coverage plus service
  area and technician panels, and a real activity timeline.

## Business rules compliance

- No free-text service creation — the wizard only ever operates on a `master_services` catalog
  row selected from the Available Offerings tab; there is no text input that creates a new
  catalog entry.
- Coverage selection (types, brands) is built from real, admin-mapped catalog data; issue
  coverage and service options are shown read-only (platform-mapped, not tenant-editable).
- Pricing preview never computes a price client-side — it displays the response of
  `POST /v1/pricing/tenants/{id}/price-preview`, a real backend pricing pipeline.
- No forbidden wallet/payout/escrow language anywhere — confirmed via scan (0 matches) and a
  dedicated test.
- Explanatory copy states customer pays provider directly and the platform does not collect
  customer service payment.

## Recommendation

**READY_TENANT_MY_OFFERINGS_ENTERPRISE_UI_CERTIFIED**

See `TENANT_MY_OFFERINGS_TEST_RESULTS.md` for full verification evidence and
`TENANT_MY_OFFERINGS_REMAINING_BLOCKERS.md` for honestly-documented, non-blocking gaps (chiefly:
the offering-readiness rule engine itself is still a stub on the backend, tracked separately
from this UI/catalog-mapping upgrade).
