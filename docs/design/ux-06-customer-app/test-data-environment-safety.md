# Test Data Environment Safety — UX-06 Round 4

## Environment identified

- Backend: `http://localhost:8000` (Windows host), reachable from WSL at
  `http://172.28.240.1:8000`. Postgres at `127.0.0.1:5432`.
- Tenant used: `5209ef33-a53e-4fc0-b3f6-006335b8d712` — this is the **DEMO
  tenant** created/upserted by `scripts/seed_demo_users.py` (`get_or_create_demo_tenant`),
  the same tenant already used for the `provider@serviceos.local` /
  `staff@serviceos.local` demo accounts referenced throughout prior UX rounds'
  memory notes. It is explicitly a development/demo tenant, not a real
  production business.
- Customer used: `customer@serviceos.local` (role=`customer`), also a real
  seeded demo account from the same script.
- Offering: `home_services` / `ac_repair` — the only category+offering with
  any real data in `MasterOffering`/`MasterService` in this dev DB (confirmed
  in Round 3).
- Before touching anything, listed the DEMO tenant's existing service areas via
  the real `GET /v1/tenant/service-areas` endpoint (not a direct query) — found
  2 pre-existing rows (a Ludhiana city-coverage area with 0 service mappings,
  and a Ludhiana/147001 zipcode area with 1 pre-existing, unrelated mapping for
  `ac_installation`). Both were clearly already test/demo data (created
  2026-07-14, well before this round), not anything resembling a real customer
  business.

## What was NOT touched (confirmed safe)

- No production data, no real customer bookings, no shared canonical seed
  script, no authorization/permission configuration, no migration file.
- No raw SQL was used at any point — every seed action this round went
  through the real, existing tenant-portal API
  (`POST /v1/tenant/service-areas/{area_id}/services`,
  `PUT /v1/tenant/service-areas/{area_id}/services/{mapping_id}`), authenticated
  as the DEMO tenant's own real `tenant_owner` account. This is safer than a
  direct DB write: it goes through the same validation, ownership, and
  duplicate-detection logic real tenant onboarding would use.
- The `BargainRule` table (a platform-wide, `master_service_id`-scoped pricing/
  negotiation policy, not tenant-scoped) was found to be a hard dependency of
  the next step in the real flow (`match-and-price`) but was **deliberately
  NOT created or modified** this round — it is exactly the kind of "shared
  canonical seed record" the brief instructed not to touch, since a
  `BargainRule` for `ac_repair` would apply platform-wide, not just to the
  isolated DEMO tenant. This is documented as a precise, honest blocker for the
  next round rather than worked around by touching shared config.

## Verdict

**SAFE_TEST_DATA_ENVIRONMENT: available and used correctly** — scoped strictly
to the pre-existing DEMO tenant, via real APIs, fully reversible (see
seed-removal-report.md).
