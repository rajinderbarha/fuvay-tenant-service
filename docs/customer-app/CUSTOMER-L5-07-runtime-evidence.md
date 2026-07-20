# CUSTOMER-L5-07 — Runtime Evidence

## Live Backend Certification: NOT PERFORMED

Identical constraint to every previous sprint: this environment has no
running backend server, no reachable database, and no device/simulator
with real location services. None of CUSTOMER-L5-07 §66's 18 required
proof points were executed against a real system.

**Stated plainly, none of the following were done:**

- No real customer loaded, created, edited, or deleted a real address
  against a live backend.
- No real current-location permission flow or OS-level reverse geocode was
  exercised on a real device/simulator.
- No real `POST /{draftId}/serviceability-check` request ever left this
  machine — meaning the real, ID-space-correct serviceability logic
  (`TenantServiceAreaService` matching) was verified by reading source
  only, never observed producing an actual serviceable/not-serviceable
  result against seeded coverage data.
- No real app-restart or logout/account-switch isolation was exercised
  against live multi-customer address data.
- No request IDs, status codes, or screenshots from a live run exist.

## What Was Verified Instead

- The exact real backend contract for every endpoint used, via direct
  source-code reading of `serviceability/router.py`, `service.py`,
  `models.py`, `schemas.py`, and `home_service_booking/service.py`,
  `serviceability_service.py`, `constants.py` — cross-checked by an
  independent research pass reaching identical conclusions on every point,
  including the central "no real SLA capability exists" finding.
- Every client-side code path (address schema validation, form validation
  matching real backend requirements, serviceability result parsing,
  route-registry promotion) is exercised by 30 new unit tests using
  fixtures shaped exactly like the real backend's actual response bodies.
- `npx tsc --noEmit`: 0 new errors (31 pre-existing, unchanged).
- `npx jest`: 516/516 passing (489 carried forward + 30 new — wait, note:
  see test-evidence.md for the exact breakdown including the
  route-registry test rewrite).
- `npx eslint`: 0 errors, 36 pre-existing warnings (baseline unchanged).
- `npx prettier --check`: clean.

## Honest Gate Impact

Per CUSTOMER-L5-07 §66's acceptance criteria, this sprint cannot claim a
hard PASS — both because live runtime proof was not possible in this
environment (consistent with every prior sprint) and because several of
§66's specific proof points (SLA selection, city-tier resolution, zone
resolution) describe backend capabilities that do not exist in the real
flow this app uses, so there is nothing for a live run to prove for them
even in principle. The gate decision reflects PARTIAL.

## What Would Close the Environment Gap

Run the actual backend (`uvicorn app.main:app`) against a seeded database
with at least one real `TenantServiceAreaService` row covering a real
city/zipcode for a real `MasterService` offering, authenticate a real test
customer, walk Home → Category → Service → Assistant → Draft → Media →
Address (create, select) → Serviceability (both a serviceable and a
not-serviceable case, by testing a covered vs. uncovered zipcode) end to
end on a real device to also exercise the location-permission and
reverse-geocode paths genuinely.
