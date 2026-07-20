# Approval Gate — Slice 2F-7

## Status
**SECURITY_AND_DOMAIN_INTEGRITY_CLOSED_PRODUCT_POLICY_BLOCKED**

## Reasoning

### SECURITY_CLOSED: YES
All 8 tenant-facing serviceability mutations now enforce
access-scope-aware authorization via `require_tenant_mutation_permission`
(previously plain `require_permission`, with no access-scope check at
all). Platform-only routes (`admin_*`, `admin_serviceability_test`)
remain correctly separated on `PLATFORM_ADMIN`/`SERVICEABILITY_ADMIN_TEST`,
neither granted to any role but `super_admin`. Tenant, coverage, and
service ownership are all verified (pre-existing `_assert_owns_tenant`,
`_assert_service_active`, mapping cross-checks — re-confirmed via direct
tests, not source-string assertions). Cross-tenant mutations are denied
(direct `NotFoundException` proof against a genuinely mismatched
tenant_id). Technicians cannot mutate tenant-wide coverage — confirmed
via the actual permission grants (`TENANT_SERVICE_AREA_*` mutation
permissions belong only to `tenant_owner`). No weaker alternate route
exists (sole writer confirmed via repository-wide search). Zero
unverified routes remain (19/19, exit 0).

### DOMAIN_INTEGRITY_CLOSED: YES
Duplicate service-area and service-mapping creation are rejected
(pre-existing guards, re-verified). The one previously-known concurrent-
duplicate-creation race is already closed via an advisory lock
(FINAL-L5-05Q, pre-existing, re-verified unmodified). Bulk operations do
not exist in this module (vacuously safe). Service ownership against the
canonical catalog is verified. Matching correctly respects disabled/
removed coverage at the SQL-query level — no bypass found. No confirmed
integrity defect remains open; the only geography-reference gaps found
(no canonical table, no postal-code format validation) are explicit,
pre-existing platform characteristics, not proven defects, and were not
invented or fixed per instruction.

### PRODUCT_POLICY_CLOSED: BLOCKED
Tenant-owner-only delegation for service-area/coverage mutations is
evidence-based (permission grants), not assumed — but whether staff
should ever receive delegated capability remains an open product
question. Supported geography levels are now explicitly documented
(city, zipcode, zone, radius are implemented; district and city-tier are
not). Platform geography ownership is explicit (owned by `geo`/`pricing`,
not touched by this module). Frontend exposure was corrected to match
backend policy for the one page found to be misaligned
(`provider/service-areas/page.tsx`'s hardcoded booleans) — this is a
genuine fix, not merely documented. Unsupported capabilities (district
coverage) are not advertised as functional in the form the reviewed code
handles. The block is due to the still-open questions in
`product-decisions-required.md` (staff delegation, tenant-catalog-
enablement, canonical geography), none of which are security or
integrity gaps.

## Quality gates (39) — summary
All satisfied. Full itemized evidence is distributed across the other 21
files in this directory.

## Global coverage after this slice
97/183 tenant-facing mutations now protected (up from 89 pre-slice) —
see `global-coverage-update.md`.

## Stop condition honored
Only one module (`app.engines.serviceability.router`) was investigated
and closed. No previously-closed module was modified. Invoice/payment
closure (Slice 2F-6/2F-6A/2F-6B) was not reopened. `admin_catalog.tenant_router`
and `complaints.provider_router` were not begun. No permission was
granted. `readonly@demo-ac-services.local` was not touched. Migration
144 was not applied. No visual redesign occurred (one minimal, targeted
boolean-computation fix in an existing page, preserving all layout/forms/
confirmation behavior).
