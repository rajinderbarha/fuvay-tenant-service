# Deferred Items — Slice 2B

## Workstream 1 — no code deferred (fully investigated, all 5 resolved to KEEP/flag-only)
One item requires a future product decision: intelligence KB's `allowed_roles_json` enforcement (build it for real, or remove the non-functional control).

## Workstream 2 — remediation execution
The 2 confirmed invalid persisted accounts require separate approval to remediate (see `invalid-role-remediation-recommendation.md`). Automating the detection query into CI/deploy checks is also deferred.

## Workstreams 3/4 — shell remaps
Tenant-owner's full 9-item grouping remap and a distinct staff/manager shell separate from technician's remain deferred (unchanged from Slice 2 — still page-consolidation-scale work requiring new pages).

## Workstream 6 — duplicate consolidation
`/staff/jobs` vs `/staff/home-services/jobs` — identified since Slice 1, still not consolidated (would require choosing and migrating one, out of this slice's narrow closure scope).

## Workstream 7 — breadcrumb extension
`useBreadcrumbOverride()` built but only adopted by 1 page. Extending it to other tenant-portal contextual detail pages (customers, quotes, business profile) is a natural next increment, not done this slice.

## Workstream 8 — shared route-access-state component
Still not built (unchanged from Slice 2's reasoning — avoids new shared-component/visual work).

## Not in scope for any future slice unless separately approved
Admin My Work, Tenant My Work, Next-Action aggregation, guided onboarding, provider setup redesign, Booking Exception Resolution, visual redesign — all explicitly excluded from this slice and untouched.

## Recommended next slice
Given this slice's single highest-value action was querying the live database rather than only reading source code, a natural next step (if the team wants to keep finding real bugs cheaply) would be a similar live-data spot-check for the finance/credit domain's canonical-vs-legacy tables noted in Phase 1A (e.g., confirming `TenantPackagePurchase` vs `TenantPackageAssignment` really has zero remaining active writers, rather than just inferring it from code). That said, the more directly relevant next step per this series' own trajectory is executing the tenant-role remediation (pending approval) and then resuming the deferred tenant-owner/staff shell remaps.
