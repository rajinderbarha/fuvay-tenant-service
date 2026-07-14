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

## 5b. Second finding — cross-tenant catalog isolation (defense-in-depth hardening)

Audited the tenant catalog IDOR surface: all 12 `/{tenant_service_id}` endpoints in
`admin_catalog/tenant_router.py` correctly call `_load_tenant_service` + `_assert_tenant_owns_ts`
(no missing-check IDOR). **However**, `_assert_tenant_owns_ts` enforced ownership only for an
allowlist — `if self.actor_role in ("tenant_owner", "staff") and self.actor_tenant_id`. This
**fails open** for any other tenant-scoped role: a `technician` (or a future tenant role) would
skip the `ts.tenant_id == actor_tenant_id` check entirely.

**Current exploitability: none** — `technician`/`staff` hold only `tenant_service_area:read`,
not `tenant:read`/`tenant:update`, so they cannot presently reach these endpoints (the
permission layer is the effective boundary and holds). This is therefore a **defense-in-depth /
future-proofing** hardening, not an active vulnerability — reported honestly as such.

**Fix:** enforce ownership for **every** tenant-scoped actor —
`if self.actor_tenant_id and self.actor_role not in PLATFORM_ROLES`. Platform roles
(`super_admin`, `admin_*`) carry `tenant_id=None` (01D-R canonical model) and correctly remain
cross-tenant. `tenant_owner`/`staff` behavior is unchanged; `technician`/any future tenant role
is now confined. Verified: 3 new tests (`test_technician_confined_to_own_tenant`,
`test_tenant_owner_still_confined`, `test_platform_role_crosses_tenants`) + 1175 catalog/pricing
tests pass.

## 5c. Third slice — data-drive the pricing-model dropdown (single source of truth)

The mission requires pricing models to load "from the canonical API or registry" and that
"hardcoded client options must be removed." Previously `VALID_PRICING_MODELS` was a bare set in
`service.py` with no API exposure, so the ~7 Super-Admin frontend pages had to hardcode the list
(backend/frontend drift risk).

**Delivered:**
- `PRICING_MODEL_REGISTRY` in `admin_catalog/service.py` — the canonical source describing each
  model (`fixed`, `range`, `post_assessment`, `hourly`) with `label`, `description`,
  `required_fields`, `optional_fields`, derived to match `_validate_pricing_config`.
  `VALID_PRICING_MODELS = set(PRICING_MODEL_REGISTRY)` — the two **cannot drift**.
- `GET /v1/admin/pricing-models` (any authenticated user, incl. tenant portal) serving the
  registry so clients load models from the API instead of hardcoding.
- `e2e/pricing_model_registry_guard.py` (fail-closed): asserts `VALID_PRICING_MODELS` == registry,
  every model has label + required_fields, `_validate_pricing_config` branches on exactly the
  registry's models, and the endpoint exists.

**Verified (genuine in-process HTTP):** 6 new tests incl. `test_pricing_models_endpoint_serves_registry`
(200 + all 4 models with field metadata), tenant-owner access, and auth-required (401). The
existing 25 `test_dynamic_pricing_form` assertions still pass (no drift from deriving
`VALID_PRICING_MODELS`). Registry guard passes. (Frontend migration to *consume* the new endpoint
is a follow-up; the canonical API source now exists.)

## 6. Files Changed

- `app/engines/admin_catalog/tenant_service.py` — shared floor/ceiling/negative validator;
  fixed create-path truthiness gate; added validation to the previously-unvalidated update path;
  hardened `_assert_tenant_owns_ts` to confine all tenant-scoped roles (not a fragile allowlist).
- `app/engines/admin_catalog/service.py` — `PRICING_MODEL_REGISTRY` single source of truth;
  `VALID_PRICING_MODELS` derived from it.
- `app/engines/admin_catalog/admin_router.py` — `GET /v1/admin/pricing-models` registry endpoint.
- `e2e/pricing_floor_guard.py`, `e2e/pricing_model_registry_guard.py` — new fail-closed guards.
- `tests/test_module_l5_03_pricing_floor.py` (9), `tests/test_module_l5_03_pricing_models.py` (6)
  — new tests.
- `docs/module-l5/MODULE_L5_03_PRICING_DEEPDIVE_REPORT.md` — this report.

## 7. Honest Status

Pricing-floor integrity: **defect fixed, guarded, and tested.** This is a genuine financial-
integrity improvement. Full MODULE-L5-03 `PROVEN_LEVEL_5` is **not** claimed — the broader
catalog/pricing certification (hierarchy reconciliation, dynamic pricing forms, full precedence
table, customer/staff catalog flows, frontend/mobile completion, import/export scale) remains a
scoped multi-pass effort.
