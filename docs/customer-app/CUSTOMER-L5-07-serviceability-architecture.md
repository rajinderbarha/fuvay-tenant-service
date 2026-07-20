# CUSTOMER-L5-07 — Serviceability Architecture

## The Real Flow

```
address selected on AddressListScreen
  → PUT /booking-drafts/{id} { address_id }
      → backend copies city/zipcode into the draft (address_snapshot)
  → navigate to ServiceabilityScreen
      → POST /booking-drafts/{id}/serviceability-check
          → HomeServiceServiceabilityService.check(category_id, offering_id, city, zipcode)
              → validates category active (ServiceCategory)
              → validates offering active (MasterService)
              → matches TenantServiceAreaService rows: exact (city, zipcode) first, city-only fallback
              → returns {serviceable, available_provider_count, matched_by, message, reason_code}
      → draft.serviceability_status updated server-side to "serviceable" | "not_serviceable"
```

This is the **only** serviceability path this sprint uses. It is real,
and — unlike CUSTOMER-L5-06's draft-creation finding — correctly scoped to
the same `MasterService`/`category_id`/`offering_id` ID space the draft
already uses throughout, so there is no cross-catalog mismatch risk here.

## Why the General `/v1/serviceability/*` Engine Is Not Used

A separate, richer serviceability engine exists
(`ServiceabilityService.check_serviceability`, `get_matching_tenants`,
`get_available_services_for_address`) with its own audit log, zone
awareness, and city-tier lookups. It is **never called by the
booking-draft flow anywhere in the backend** (confirmed by grep — no
import of `serviceability.service` from `home_service_booking/*.py`) — it
is keyed to a third, unrelated, tenant-scoped catalog
(`service_catalog.ServiceCatalogItem`) that has no relationship to the
`MasterService`/`MasterOffering` catalogs this app's real discovery and
draft flows are built on. Adopting it would mean either fabricating a
bridge between three disconnected catalogs (which does not exist) or
passing IDs the general engine cannot resolve. This sprint does neither —
it uses the real, already-correctly-wired check instead.

## Zone and City-Tier

Real master data exists elsewhere in the backend (`location_engine`'s
`LocationZone`/`city_tier` fields, the `geo` engine's `ServiceZone`) but
**neither is resolved or returned by the actual serviceability check this
draft flow uses**. This sprint does not display a zone or city tier
anywhere, because the real, in-flow check has none to show — not because
of a frontend oversight.

## Result Model

Two outcomes only — a simple boolean, not the spec's aspirational
multi-state enum (`SERVICEABLE_WITH_LIMITATIONS`, `POSTAL_CODE_UNSUPPORTED`,
`ZONE_UNMAPPED`, etc. do not exist in this backend):

| `serviceable` | `matched_by` | Meaning |
|---|---|---|
| `true` | `"zipcode"` | Exact zipcode-level coverage found |
| `true` | `"city"` | City-level coverage found (zipcode-specific coverage not confirmed) |
| `false` | `null` | No coverage found — `reason_code` explains why (invalid category/offering, or genuinely no provider in that city/zipcode) |

## `available_provider_count`

Real field, parsed, but **deliberately not rendered** in the UI — an
internal operational number (CUSTOMER-L5-07 §26's "do not display internal
provider counts unless product-approved"). No product approval exists for
surfacing it this sprint.

## Temporary vs. Permanent Unavailability

The real backend does not distinguish these — a `false` result's
`message` already contains forward-looking, honest copy when applicable
(e.g. `"This service is not available in {city} yet. We're expanding
soon!"`), which this screen displays verbatim rather than inventing its
own "temporarily unavailable" framing the backend does not actually claim.

## No-Service Flow

`ServiceabilityScreen`'s unavailable state offers exactly one real action:
"Change address" (returns to `AddressListScreen`). No waitlist/"notify me"
action is shown, since none exists (CUSTOMER-L5-07 §30's explicit
guidance: "must be hidden unless implemented").

## Caching

The serviceability result is not cached as a standalone query — it is a
`useMutation` (an explicit check action, not a passively-fetched resource),
matching its real nature as a stateful operation that also mutates the
draft. Re-selecting a different address always triggers a fresh check
(new navigation to `ServiceabilityScreen` with a new `addressId` param),
never reusing a stale prior result.
