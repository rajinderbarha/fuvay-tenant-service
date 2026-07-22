# Selected Next Module — Slice 2F-22

## Module
`app.engines.package_commerce.tenant_router`

## Mounted prefix
`/v1/tenant/packages/*` (mutation route) — related reads under
`/v1/tenant/packages/available`, `/v1/tenant/packages/purchases`,
`/v1/provider/onboarding/package-summary`, `/v1/tenant/security-deposit`
(all GET, all in the same router file).

## Exact mutation count
**1** — confirmed by direct grep of `app/engines/package_commerce/tenant_router.py`
for `@router.post|put|delete|patch`: the only non-GET route in the file is
`POST /v1/tenant/packages/{package_id}/purchase`. This matches the queue
CSV's prior count of 1 exactly, now re-derived from current code (not
merely repeated from the prior slice).

## Exact route list
1. `POST /v1/tenant/packages/{package_id}/purchase` (`tenant_purchase_package`)

## Related reads (same router, not selected-mutation routes but in-scope for the implementation slice's audit)
`GET /v1/tenant/packages/available`, `GET /v1/tenant/packages/purchases`,
`GET /v1/provider/onboarding/package-summary`, `GET /v1/tenant/security-deposit`
— all currently `get_current_user`-only (read access, lower risk than the
mutation route, but confirm no state-mutating GET pattern like 2F-20's
`download_export` exists here — none found: none of these 4 reads write to
the database, confirmed by reading their handler bodies).

## Models / tables
`TenantPackageAssignment` (created by `PackageCommerceService.create_package_assignment`)
— the real, tested, symmetric package-entitlement mechanism (per the
`MODULE-L5-30` comment already in the route handler; the old
`TenantPackagePurchase`/`tenant_package_purchases` path was dead — table
never migrated — and was already replaced in a prior module fix, not part
of this slice's scope).

## Parent workflow
Tenant package commerce: an already-onboarded tenant purchasing an
additional or renewal package entitlement (as distinct from the initial
onboarding-time package selection, which uses a different, already-tested
inline path).

## Canonical personas
`tenant_owner` (current, via `require_tenant_owner`); no `staff`/`technician`
admission — confirmed correct scope for a financial/entitlement action
(consistent with `require_tenant_owner`'s use across every other genuinely
financial route this initiative has closed, e.g. compliance's
`generate_export`).

## Existing permissions
None of the granular `P`-class permission strings apply — role-based
`require_tenant_owner` is the established pattern here, same as every
`provider_portal`/`tenant`-prefixed router this initiative has audited.

## Existing dependency available for reuse (no new dependency needed)
`require_tenant_owner_mutation` (`app/core/permissions.py`) — same admitted
role set as `require_tenant_owner` (`tenant_owner`, `super_admin`) plus the
missing read-only-`access_scope` denial. Direct drop-in, zero role-set
change, identical pattern to 2F-20's fix for compliance.

## Tenant and object ownership
`package_id` is catalog-level (shared across tenants, not tenant-owned) —
the mutation creates a NEW tenant-owned `TenantPackageAssignment` row keyed
to the caller's own `tenant_id` (server-derived from JWT via the `_tenant_id()`
helper, confirmed NOT client-controlled by direct source read of
`tenant_router.py` lines 106-131). No pre-existing object ownership to
verify (this is a create, not an update/delete of an existing tenant-owned
row) — this module's core gap is narrower and shallower than compliance's
(no missing schema-level tenant_id column; JWT tenant_id is trustworthy and
already used correctly).

## The module's core gap: CLIENT_AMOUNT_TRUSTED on `mark_paid`
`payload.get("mark_paid")` is read directly from the untrusted request body
and passed straight into `create_package_assignment(..., is_paid=bool(payload.get("mark_paid")))`.
A malicious or careless tenant client could set `mark_paid: true` and
receive an assignment marked paid without any actual payment verification.
This is the genuinely new, evidence-based finding of this slice (the
2F-19/2F-20 queue CSV only flagged the role-gate gap
`PERMISSION_ONLY_NOT_SCOPE_AWARE`; this slice additionally confirmed a
`CLIENT_AMOUNT_TRUSTED`-class gap by reading the actual handler body, which
prior slices had not yet done for this route since it was only ever listed,
not implemented).

## State machine
None (new) -> `pending`/`active` depending on `is_paid` — server-driven
post-creation, no further transitions in this route.

## Client-controlled identifiers
`package_id` (path param, catalog-level — read-only lookup, low risk);
`payload.payment_reference` (string, stored as-is — low risk, audit trail
field); `payload.mark_paid` (boolean — HIGH risk, see above).

## Financial / irreversible side effects
YES — creates a package entitlement. Whether `mark_paid=true` should ever
be trusted from a tenant-side caller (vs. requiring a separate,
payment-gateway-verified activation step) is a genuine, unresolved product
question flagged for Slice 2F-22, not resolved here.

## Read/privacy surface
None — no PII read or exposed by this route.

## Alternate routes
None found — confirmed sole mutation route in the entire router file by
direct grep; no other router creates or mutates `TenantPackageAssignment`
rows from the tenant side (the admin-side `activate_tenant_package_assignment`
path is a distinct, already-audited platform-admin capability, out of
scope here).

## Service-layer callers
`PackageCommerceService.create_package_assignment` (single call site from
this router; not independently audited for a second unguarded entry point
this slice — deferred to the implementation slice per FRONTEND_CALLER_AUDIT_DEFERRED-style
convention, see below).

## Frontend/mobile callers
Not investigated this slice (discovery/selection only) — deferred to the
implementation slice, per this initiative's established
`FRONTEND_CALLER_AUDIT_DEFERRED` convention (see 2F-20's
`frontend-mobile-caller-audit.md` for the pattern this defers to).

## Product decisions flagged (not resolved this slice)
- Whether tenant-side `mark_paid=true` self-attestation should ever be
  trusted at all, versus requiring server-side payment-gateway
  verification before an assignment can be marked paid. This is the single
  blocking-adjacent question for Slice 2F-22 — but per the mission's
  selection criteria it is a "possible" dependency, not a confirmed
  blocker, since a valid interim fix (deny `mark_paid` entirely for
  non-`super_admin` callers, or require idempotency-key + duplicate-purchase
  guard) exists without resolving the deeper payment-gateway-integration
  question.
- Purchase idempotency / duplicate-purchase semantics (flagged by the
  original queue CSV, re-confirmed here: no idempotency-key check found
  in `create_package_assignment`'s call from this route).

## Explicit boundaries for the implementation slice
- Do NOT modify the admin-side package-activation path
  (`app.engines.admin_catalog.tenant_service` / equivalent
  `activate_tenant_package_assignment`) — out of scope, already a distinct,
  correctly-scoped platform-admin capability.
- Do NOT add a payment-gateway integration — if `mark_paid` trust is
  addressed, the interim fix must be an authorization/scope change (e.g.
  deny the flag outright, or require an explicit `super_admin` override),
  not a new payment-processing dependency, per this initiative's standing
  no-new-infrastructure discipline.
- Do NOT change `TenantPackageAssignment`'s schema (no migration
  permitted per this initiative's standing constraint).
- Do NOT touch the 4 GET read routes' business logic beyond their
  dependency, unless proven directly connected to the mutation's fix.

## Why it outranks every other remaining module
Per `remaining-module-risk-scoring.csv`: `package_commerce` is the sole
`HIGH`-severity module among the 9 — the only one combining a confirmed
financial/entitlement side effect with a genuinely new, evidence-based
finding (`mark_paid` client-trust gap) that was NOT visible from the queue
CSV alone and required this slice's direct source read to surface. Every
other remaining module's gap is either a simple role-gate upgrade
(self-owned-by-construction resources: media_profile, profile,
admin_catalog_recommendation, analytics) or a parent-child-ownership gap
with no financial/PII dimension (customer_reviews, marketing_automation,
admin_catalog_brand, admin_catalog_service_option). This re-derives and
CONFIRMS the queue CSV's rank-1 a-priori candidate from actual current
code, per the mission's explicit instruction not to take the prior ranking
at face value.
