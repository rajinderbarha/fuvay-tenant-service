# Geography Reference Integrity — Workstream 6

## Supported geography levels (re-verified via direct source read)

### Postal code / ZIP
- **Format validation**: none. `zipcode` is a bare `String(20)` column
  and a Pydantic `Field(..., min_length=1, max_length=20)` — no regex,
  no numeric-only check, no country-specific format rule.
- **Country linkage**: none — `country` defaults to `"India"` and is
  never cross-validated against `zipcode`.
- **City/district linkage**: none — no check that a given `zipcode`
  belongs to the stated `city`/`district`; these are independent,
  unvalidated string fields entered together in the same payload.
- **Duplicate behavior**: `_check_duplicate_area` rejects a second
  active `zipcode`-coverage-type area for the same tenant with the same
  `city`+`zipcode` (pre-existing, confirmed unmodified).
- **Bulk behavior**: N/A — no bulk endpoint exists (see
  `bulk-operation-security.md`).

### City
- **State/district relationship**: `state` is required for
  `coverage_type == "city"`; `district` is optional and unvalidated.
- **Tier linkage**: none — `CityTierConfig` (in `pricing`) is never
  referenced by `serviceability`.
- **Expansion to postal codes**: none — selecting `coverage_type="city"`
  remains an abstract city-level coverage record; it does not expand
  into a set of postal codes. Confirmed via `create_service_area`:
  `if coverage_type == CoverageType.CITY: zipcode = None`.

### District
- **Implemented or documentation-only**: documentation-only in the
  practical sense — the `district` column exists on both
  `CustomerAddress` and `TenantServiceArea`, but no `coverage_type` value
  is `"district"` (confirmed via `CoverageType.ALL` — only `city`,
  `zipcode`, `zone`, `radius` are valid), and `district` is never used as
  a matching key in `service.py`. It is stored but functionally inert.
- **State relationship**: none enforced.
- **Tenant mapping behavior**: N/A — cannot be selected as a coverage
  type at all.

### Zone
- **Platform-defined or tenant-defined**: platform-defined —
  `zone_id` references `app.engines.geo.ServiceZone`, a table this
  module never writes to. A tenant can also supply a free-text
  `zone_name` without a `zone_id` (the `_check_duplicate_area` logic
  handles both cases), meaning a "zone" coverage entry can be entirely
  tenant-defined-by-name with no link to the canonical `ServiceZone`
  table at all.
- **Parent geography**: `city`/`state` are still required alongside the
  zone reference (`_validate_coverage`'s `ZONE` branch).
- **Postal-code membership**: not modeled in this module — no join table
  exists here linking `ServiceZone` to a set of postal codes (this may
  exist in `app.engines.geo`, not investigated as out of scope for this
  module's own boundary).
- **Tenant ownership**: the `TenantServiceArea` row itself is
  tenant-owned; the referenced `ServiceZone` (if `zone_id` is supplied)
  is platform-owned and read-only from here.
- **Pricing linkage**: not found in `serviceability` — `ZoneSurcharge`
  lives in `app.engines.pricing`, not referenced by this module.

### Tier
- **Platform ownership**: `CityTierConfig` is entirely owned by
  `app.engines.pricing`.
- **Tenant mutability**: N/A — not referenced by `serviceability` at all.
- **Pricing/matching effects**: not evaluated (out of scope — a
  different engine's model).

## Conclusion
Geography-reference validation in this module is genuinely minimal by
design (no canonical Country/State/District/City/PostalCode table
exists to validate against anywhere in the platform). This is not a
defect introduced or hidden by `serviceability` — it is an accurate
reflection of what the platform currently implements. Per "do not invent
geography concepts missing from the repository" and "mark unsupported
geography concepts explicitly... do not implement them during this
slice," no new validation was added.
