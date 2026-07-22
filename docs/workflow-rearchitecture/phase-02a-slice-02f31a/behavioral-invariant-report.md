# Behavioral Invariant Report

Invariants proven to hold before AND after this slice's changes:

1. **Admitted-role set on `upload_media`/`replace_media` is unchanged.**
   `get_current_user` before, `require_mutation_access_scope` (which wraps
   `get_current_user`) after — same role set, verified live via
   `authority_model_2f26e.py::route_guards`.
2. **`StaffPermission` explicit-deny semantics are untouched.** No route in
   this slice used `require_tenant_mutation_permission`; `permission_checker`
   was not imported or modified by any change this slice made.
3. **`MediaAccessService`/`MediaAssetService` ownership semantics are
   byte-identical** — neither file was modified.
4. **Non-oracular responses hold on every closed route** — verified in
   [media-router-tenant-authority-audit.csv](media-router-tenant-authority-audit.csv)
   and by `TestNonOracularResponses`.
5. **No storage object is ever hard-deleted by any of the 5 residual
   routes** — `delete_file` is soft-delete only, confirmed by reading its
   full body (no call to `MediaStorageService` or a provider SDK).
6. **The M01/2F-31-protected route sets are unchanged** — spot-checked and
   full-suite re-run, 0 regressions.
