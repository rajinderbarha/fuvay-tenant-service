# Behavioral Invariant Report

- **Admitted-role sets on `delete_zone`/`create_zone` unchanged.**
  `require_permission(P.TENANT_UPDATE)` → `require_tenant_mutation_permission
  (P.TENANT_UPDATE)` wraps the identical role/permission check; only the
  access-scope layer is new.
- **Admitted-role set on `update_location` unchanged.** `get_current_user`
  → `require_mutation_access_scope` wraps the identical dependency; only
  the access-scope layer is new. The router's staff-self check is
  byte-identical to before.
- **`StaffPermission` explicit-deny semantics untouched** — no change to
  `permission_checker` or `app/core/permissions.py`'s `has()` logic.
- **`MediaAccessService`/`MediaService`/N01 closure untouched** — no
  media file was modified this slice.
- **`ServiceZone`/`StaffLocation` field allow-lists unchanged** — only the
  WHERE-clause predicate and constructor context changed; no new column,
  no schema change, no migration.
- **`update_zone`/`get_zone` (Set C) byte-identical** — confirmed by
  `tests/test_phase2f33_geo_zone_closure.py::TestSetBAdjudication::
  test_no_set_c_route_was_touched`.
- **Only 4 application files touched**: `app/engines/geo/service.py`,
  `app/engines/geo/router.py`, `docs/workflow-rearchitecture/phase-02a-
  slice-02f/tenant-mutation-endpoint-inventory.csv`, `.../mutation-
  enforcement-matrix.csv` (the latter two are canonical tracking artifacts,
  not application code).
