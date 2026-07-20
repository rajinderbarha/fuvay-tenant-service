# Product Decisions Required — Slice 2F-20

These are policy/product questions this slice deliberately did NOT decide
unilaterally, per the mission's scope discipline (no migration, no new
permission/role, no feature-completeness redesign). Each is a candidate
for a future slice or a direct product decision.

## 1. Export-generation worker
`generate_export` creates a `ComplianceExport` row in `"processing"`
status; no code anywhere in the codebase ever transitions it to
`"ready"` (see `compliance-export-worker-discovery.md`). Every export a
tenant generates is permanently stuck. Decision needed: build the worker
(file generation + storage + signed URL), or explicitly retire the
export feature until it can be built. This is the reason final status is
`DOMAIN_INTEGRITY_BLOCKED` rather than fully closed.

## 2. Export deduplication / idempotency
`generate_export` has no check for an existing in-flight or completed
export for the same request; repeated calls (or a race between the
tenant route and the admin `process_request` path) create multiple,
independently-stuck `ComplianceExport` rows for one request (see
`compliance-export-retry-concurrency.md`). Decision needed: add a
uniqueness/dedup constraint or check once a worker exists — building
dedup logic ahead of the worker was judged not meaningfully useful this
slice (there's nothing yet for the dedup to protect).

## 3. Staff role admission
None of the 6 protected routes admit `staff`, only `tenant_owner` /
`super_admin` (via `require_tenant_owner_mutation`), consistent with the
pre-existing `require_tenant_owner` behavior these routes already had.
Decision needed (out of this slice's scope to decide): should compliance
staff-requests handling ever be delegable to `staff`? No canonical
permission currently supports this distinction at the route level.

## 4. Constant-set consolidation
Three independently-maintained subject-type / request-type validation
constant sets exist across `enterprise_service.py` (`VALID_SUBJECT_TYPES`,
`VALID_REQUEST_TYPES`) and the router-level allow-lists
(`TENANT_ALLOWED_REQUEST_TYPES` in `provider_router.py`). This slice
only widened the service-layer allow-lists to include what the router
already sends (fixing a real, always-broken `create_my_request`).
Decision needed: consolidate to a single source of truth to prevent this
class of drift recurring.

## 5. Duplicate audit-log call in `download_export`
Found during route audit (see `compliance-export-storage-download.md`):
`download_export` appears to call `_audit(...)` twice on the success
path. Not fixed this slice — cosmetic/log-volume issue, not a security or
correctness defect, and fixing it was judged out of proportion to touch
during an authorization-focused slice. Flagged for cleanup.
