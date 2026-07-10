# HS5 — Tenant Service Areas Report

## Real route
`/provider/service-areas` (not `/tenant/setup/service-areas` as the
ticket assumed — same naming-convention pattern already established for
`/provider/availability` and `/tenant/setup/services`; confirmed real,
linked from the live tenant nav's Setup group under the label "Service
Areas").

## Pre-existing, already certified (earlier "Tenant Service Coverage
Areas Enterprise UI" sprint — confirmed unchanged this sprint)
- 1490-line real enterprise page: KPI cards, area table (Area Name,
  State, District, City, Pincode, Zone/Tier, Primary, Status, Updated,
  Actions), primary-area logic, duplicate/limit validation pipeline
  shown before save ("Package Limit Check").
- Backend: `create_service_area` real, server-side enforces package
  area limit (`"Your plan allows a maximum of {max} service areas."`,
  422) and duplicate-zipcode/area rejection (`ERR_DUPLICATE_AREA`).
- Migration 117 (earlier sprint) added `is_primary` persistence and
  `max_service_areas`, plus `/set-primary`/`/limits`/`/validate`
  endpoints.

## Not re-verified in depth this sprint
Service/type/brand coverage-by-area (Part of the ticket's Coverage
section) was not independently re-tested this sprint — time budget went
to the availability time-validation gap (a genuine, previously-untested
bug) instead. The area page's fields list (Supported Services/Types/
Brands) was confirmed present via the earlier sprint's certification,
not re-verified live this sprint.

## Verdict
Service Areas: **real, substantial, already certified**. No new bugs
found or fixed here this sprint (the earlier sprint's fixes remain
intact, confirmed via regression: 44/44 passing).
