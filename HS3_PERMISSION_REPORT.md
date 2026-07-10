# HS3 — Permission Report

## Real permission constants (not the ticket's assumed namespace)
Same finding as HS2/HS2B: no `admin.home_services.pricing.*` constants
exist in `app/core/permissions.py`. The closest real, existing constants
are `catalog:services:write` (generic) — no dedicated pricing-specific
permission namespace was found.

## Not implemented this sprint
The admin pricing-rules page (`/admin/home-services/pricing-rules`) does
**not** currently use `usePermissions()` at all — unlike the HS2B catalog
console, which was wired to permission-gate its actions. This sprint's
time budget went to the higher-priority backend validation gaps (brand-
requires-type, duplicate detection) rather than permission wiring.

## Verdict
Permission-aware UI for the pricing-rules page: **not implemented**.
Documented as a real, honest gap — the same class of work already done
for the catalog console (HS2B) was not repeated here this sprint.
