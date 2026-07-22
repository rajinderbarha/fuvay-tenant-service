# Behavioral Invariant Report

- **Admitted-role sets unchanged on every guard swap.**
  `require_staff_or_above_mutation` admits the identical 4 roles as the
  `require_technician` dependency it replaces; `require_mutation_access_scope`
  adds no role restriction (used only where none existed);
  `require_tenant_mutation_permission(P.TENANT_UPDATE)` reuses the exact
  permission previously checked by the bare `require_permission` it
  replaces.
- **`StaffPermission` explicit-deny semantics untouched** — no change to
  `permission_checker` or `app/core/permissions.py`'s `has()` logic; no
  new permission or guard function was added this slice (all 3 guards
  reused pre-existing helpers from Slices 2F-31A and earlier).
- **M01/N01/geo/2F-35 closures untouched** — no file under
  `app/engines/auth/`, `app/engines/media/`, `app/engines/geo/`,
  `app/engines/webhook/`, `app/engines/rag/`, `app/engines/security/`, or
  `app/engines/document/` was modified this slice.
- **Set C routes (5) byte-identical** — confirmed by verifier condition
  R19 (no Set C route was newly protected).
- **`update_my_profile` (universal self-service) retains its fully open
  admitted-role set** — no role/permission restriction was added, per the
  open product decision on whether self-service should ever be role-
  gated; only the read-only-access-scope floor was added.
- **9 application files touched**: `app/engines/enterprise_grid/
  {router,services}.py`, `app/engines/admin_catalog/
  {service_option_provider_router,brand_provider_router,
  recommendation_router}.py`, `app/engines/profile/router.py`,
  `app/engines/marketing_automation/provider_router.py`,
  `app/engines/analytics/provider_router.py`, plus 8 held-registry
  service/router pairs: `app/engines/chat/{router,service}.py`,
  `app/engines/inventory/{router,service}.py`,
  `app/engines/appointment/{router,service}.py`,
  `app/engines/service_catalog/{router,service}.py`,
  `app/engines/dispatch/{router,service}.py`,
  `app/engines/data_science/{router,service}.py`,
  `app/engines/settings_engine/{router,service}.py`,
  `app/engines/notification/{router,service}.py`.
