# MODULE-L5-03 — Catalog & Pricing: High-Value Deep-Dive (Pricing-Floor Integrity)

## 1. Scope & Status

**Deep-dive slice** (not a full-module PROVEN_LEVEL_5 claim) on the highest-financial-risk area
of Catalog, Services & Pricing: **platform price-floor enforcement** and its bypass surfaces.
Real defect found and fixed; fail-closed guard + tests added; no sprint-attributable regression.
The rest of the MODULE-L5-03 surface (full 40-layer matrix, complete frontend/mobile catalog
completion, full pricing-precedence certification) is **not** certified here and would need a
dedicated multi-pass effort — reported honestly rather than rubber-stamped.

## 2. Central Finding — platform-floor bypass (HIGH, financial integrity)

The invariant "a tenant's price may not fall below the admin/master-service minimum" was
**bypassable via two paths** in `app/engines/admin_catalog/tenant_service.py`:

1. **Create path (`enable_service`)** — used Python truthiness:
   `if any([tenant_base, tenant_min, ...])` and `if tenant_min and svc.min_price and tenant_min < svc.min_price`.
   `Decimal('0')` is **falsy**, so a tenant setting `tenant_min_price = 0` skipped the floor
   check entirely and the value was still persisted → a tenant could price a service at **0**,
   below the platform floor.
2. **Update path (`update_enabled_service`)** — performed **no price validation at all**: it
   checked only `override_allowed`, then blindly `setattr(ts, field, Decimal(...))` for any
   provided price. A tenant could **update** their price to below the admin floor, to zero, or
   **negative**, with zero enforcement. This is the more severe bypass (the create-path floor
   check, however flawed, at least existed; the update path had none).

There was also **no non-negative validation** anywhere on tenant prices.

### Exploit conditions
Any `tenant_owner` (or role with tenant catalog-write permission) on a service whose
`tenant_override_allowed` is true, via the tenant catalog update endpoint — no cross-tenant
access needed; it undercuts the platform's own floor for that tenant's customers.

## 3. Fix

Introduced a shared `TenantCatalogService._validate_price_overrides(svc, base, min, max, visit)`
that enforces, using `is not None` (not truthiness):
- `TENANT_PRICE_NEGATIVE` — no negative base/min/max/visit;
- `TENANT_PRICE_BELOW_ADMIN_MIN` — `tenant_min ≥ svc.min_price`;
- `TENANT_PRICE_ABOVE_ADMIN_MAX` — `tenant_max ≤ svc.max_price`.

Wired into **both** mutation paths:
- create: `any(v is not None for v in ...)` gate + validator call;
- update: loads the `MasterService`, computes the **effective post-update** values (provided
  override merged with existing stored values), and validates before persisting.

## 4. Verification

- **Unit tests** (`tests/test_module_l5_03_pricing_floor.py`, 6 passed) directly exercise the
  validator, including `test_zero_below_floor_is_rejected` (the exact original bypass),
  below-floor, above-ceiling, negative, and valid-at-floor.
- **Fail-closed guard** (`e2e/pricing_floor_guard.py`, PASSED) statically asserts both mutation
  paths call the validator, the validator retains all three invariants, and the old truthiness
  check is gone. Fails closed if any mutation path stops enforcing the floor.
- **Regression:** 1081 catalog/pricing-scoped tests pass; full backend regression run (totals in
  the commit message / below) shows no sprint-attributable failure.
- Note: the running `:8000` backend predates the fix; live end-to-end proof would require the
  backend loaded with the new code (as done for IDG-1) plus a seeded tenant-service-with-floor
  fixture. The unit tests exercise the exact validation the endpoint invokes.

## 5. Other pricing observations (verified sound / minor, not fixed here)

- **Tenant floor create-path** and **bargain floor** are otherwise well-designed:
  `admin_catalog/bargain_engine.py` enforces `customer_min ≥ admin_min` (CUSTOMER_MIN_BELOW_ADMIN_MIN)
  and computes `bargain_floor = customer_min × (1 + platform_fee%)`, explicitly **never** using
  base_price for the floor "by construction." Sound.
- **Pricing models are server-validated** against a canonical set
  (`admin_catalog/service.py::VALID_PRICING_MODELS = {fixed, range, post_assessment, hourly}`,
  `INVALID_PRICING_MODEL` raised). Minor: there is no `GET /pricing-models` registry endpoint, so
  the ~7 Super-Admin frontend pages likely hardcode the model list — a low-severity
  data-drivenness gap (the set is small and server-enforced). Not fixed this slice.
- **Pricing rule resolution** (`admin_catalog/pricing_engine.py`) enforces effective_from/
  effective_to date windows and reads min_price/bargain_floor from the matched rule. Sound at a
  glance; full precedence certification not performed here.

## 6. Files Changed

- `app/engines/admin_catalog/tenant_service.py` — shared floor/ceiling/negative validator;
  fixed create-path truthiness gate; added validation to the previously-unvalidated update path.
- `e2e/pricing_floor_guard.py` — new fail-closed guard.
- `tests/test_module_l5_03_pricing_floor.py` — new tests (6).
- `docs/module-l5/MODULE_L5_03_PRICING_DEEPDIVE_REPORT.md` — this report.

## 7. Honest Status

Pricing-floor integrity: **defect fixed, guarded, and tested.** This is a genuine financial-
integrity improvement. Full MODULE-L5-03 `PROVEN_LEVEL_5` is **not** claimed — the broader
catalog/pricing certification (hierarchy reconciliation, dynamic pricing forms, full precedence
table, customer/staff catalog flows, frontend/mobile completion, import/export scale) remains a
scoped multi-pass effort.
