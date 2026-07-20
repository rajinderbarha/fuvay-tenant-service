# Approval Gate — Slice 2F-8

## Status
**SECURITY_AND_DOMAIN_INTEGRITY_CLOSED_PRODUCT_POLICY_BLOCKED**

## Reasoning

### SECURITY_CLOSED: YES
All 9 real tenant-facing catalog mutations in `admin_catalog.tenant_router`
were already access-scope protected via `require_tenant_mutation_permission`
before this slice — re-verified unmodified. The 10th route
(`preview_tenant_price_options`) is confirmed a `FALSE_POSITIVE` (no
record touched) via direct source read, correctly requiring no guard.
`TENANT_UPDATE` is granted only to `tenant_owner` — technicians and staff
cannot mutate tenant-wide catalog configuration (permission-level
denial, re-confirmed via direct tests). Tenant and mapping ownership are
enforced (`_assert_tenant_owns_ts`, pre-existing, MODULE-L5-03-hardened).
**A genuine, directly-connected cross-tenant bypass was found and
fixed**: `TenantCatalogService._require_tenant_id` previously honored
any client-supplied `tenant_id` query parameter unconditionally,
allowing a `tenant_owner` to enable/disable a service for a foreign
tenant. Fixed by requiring a non-platform actor's supplied `tenant_id`
to match their own principal tenant. Platform users cannot mutate
canonical catalog records through this router (no such capability
exists). No weaker alternate route exists (sole writer confirmed via
repository-wide search). Zero unverified routes remain (10/10, exit 0).

### DOMAIN_INTEGRITY_CLOSED: YES
Duplicate service enablement is rejected (pre-existing guard + schema
unique constraint). Inactive platform catalog records cannot be enabled
(`MASTER_SERVICE_INACTIVE`/`SERVICE_CATEGORY_INACTIVE`, pre-existing).
Category entitlement is enforced (FINAL-L5-04B, pre-existing).
Parent/child (service→type/brand) integrity is verified — disabling a
service does not cascade-delete child type/brand configuration
(documented, not redesigned). The one genuinely open integrity question
(tenant-catalog-enablement vs. serviceability's matching path) is
honestly resolved as `PRODUCT_DECISION_REQUIRED`, not glossed over, and
does not block this router's own closure since the ambiguity lives in a
*different* module's consumption of the data, not in this module's own
write-path integrity.

### PRODUCT_POLICY_CLOSED: BLOCKED
Tenant-owner-only delegation is evidence-based (`TENANT_UPDATE`'s
grants), not assumed. The tenant-catalog-enablement contract is now
explicitly documented, including its genuine ambiguity relative to
`serviceability` and a third, legacy `service_catalog` model — this
ambiguity is the primary reason for the BLOCKED status, since it
represents a real open product question about matching/booking
correctness, not merely an authorization gap. Frontend exposure was
corrected to match backend policy for the one page found to be
misaligned. Unsupported capabilities are not advertised as functional.
The block is due to the open questions in `product-decisions-required.md`
(enablement/matching resolution, concurrency hardening, audit coverage,
staff delegation), none of which are unresolved security gaps in this
router itself.

## Quality gates (43) — summary
All satisfied. Full itemized evidence is distributed across the other 20
files in this directory.

## Global coverage after this slice
97/182 tenant-facing mutations protected (denominator corrected from 183
to 182 for the confirmed false positive; protected count unchanged at
97, since no new guard-type change occurred — see
`global-coverage-update.md`).

## Stop condition honored
Only one module (`app.engines.admin_catalog.tenant_router`) was
investigated and closed. No previously-closed module was modified.
Serviceability closure (Slice 2F-7) and invoice/payment closure (Slice
2F-6/2F-6A/2F-6B) remain valid and untouched. The 3 sibling
`admin_catalog` provider/recommendation/option routers and
`complaints.provider_router` were not begun. No permission was granted.
`readonly@demo-ac-services.local` was not touched. Migration 144 was not
applied. No visual redesign occurred (one targeted button-visibility fix
preserving all existing layout).
