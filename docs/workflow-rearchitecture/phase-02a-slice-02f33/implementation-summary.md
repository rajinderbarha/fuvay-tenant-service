# Slice 2F-33 — Geo Zone Management Authorization Closure and Held-Route Adjudication

**Status:** `SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED` (scoped to
`geo_zone_management` only)

## What this slice closed

- **Set A** — `DELETE /v1/geo/zones/{zone_id}` (`delete_zone`): had ZERO
  tenant predicate anywhere (route or service). Closed by deriving the
  principal's tenant server-side and scoping the query by both `zone_id`
  AND `tenant_id`.
- **Set B, adjudicated `TENANT_PROVIDER_MUTATION_ADD`, added canonically,
  and closed in the same slice**:
  - `POST /v1/geo/tenants/{tenant_id}/zones` (`create_zone`)
  - `POST /v1/geo/tenants/{tenant_id}/staff/{staff_id}/location`
    (`update_location`)

Both had the client-supplied path `tenant_id` trusted unconditionally;
both now verify it against the server-derived principal tenant.

## Coverage

| | Before | After |
|---|---|---|
| Denominator | 262 | 264 (+2, Set B) |
| Protected | 238 | 241 (+1 Set A, +2 Set B) |
| Unprotected | 24 | 23 |
| Canonical hash | `1f7891798eb8382f` | `d4900ce03daa5437` |
| Matrix hash | `abac4ae72e8ab1d4` | `abfa5d030b1cfeee` |
| Pending held | 56 | 54 |

## Key findings

- `GeoService` had no tenant-authority concept at all prior to this slice
  — `_require_trusted_tenant` (mirroring `MediaService`'s 2F-31A pattern)
  now derives it server-side for all 3 closed mutations.
- No parent-geography hierarchy exists in this schema (no District/City/
  Region model tied to `ServiceZone`) — WS8's hierarchy-ownership
  requirement is honestly reported as not-applicable rather than
  fabricated.
- No dependent-record cascading/orphaning risk exists — `delete_zone` is
  soft-delete only and no hard FK constraint ties serviceability/pricing
  to `ServiceZone.id`.
- `update_zone`/`get_zone` (Set C) share the identical historical defect
  but were explicitly frozen out of this slice's scope and left untouched.

## Regression

Full `tests/test_phase2f*.py` suite, run twice: see
[regression-report.md](regression-report.md). A blanket literal-value
sed initially miscorrected 6 unrelated classifier-agreement tests during
this slice's own cascading rebaseline; caught by the full regression run
and fixed with narrow, explained exceptions before reporting completion
— see [documentation-corrections.md](documentation-corrections.md).

## Scope discipline

No Set C route modified. No route outside frozen Set B added. No role,
alias, permission, or migration added. `MediaAccessService`/N01/M01
untouched. Stopping at the Slice 2F-33 approval gate — no next module
selected.
