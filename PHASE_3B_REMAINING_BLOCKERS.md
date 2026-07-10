# Phase 3B — Remaining Blockers

None of these are hard-gate failures for Phase 3B specifically (router,
permissions, Swagger, and the new backend surface are all live-verified
working). Carried-forward / scope-boundary notes only:

1. **No dedicated Finance Admin / Read-only Admin / Restricted Admin role
   fixtures exist to live-test 403 responses end-to-end for this specific
   new permission set.** The `require_permission` enforcement mechanism
   itself is shared, pre-existing infrastructure already exercised by every
   other permission-gated engine in this codebase — not newly written this
   sprint — so the risk is low, but a true multi-role live smoke (create a
   `finance_admin`-only token, hit `/bargain-rules/{id}/activate`, confirm
   403 with `error_code`/`request_id`) was not performed this sprint due to
   no such seeded user existing in the current dataset.

2. **No public/tenant-facing `POST /v1/pricing/bargain/evaluate` endpoint
   exists** — only the admin-preview `/v1/admin/pricing/bargain/evaluate-preview`
   exists. This is pre-existing (not a Phase 3B regression); the ticket
   phrased this as "verify ... if it exists," so it is documented, not
   treated as a failure.

3. **Request/response bodies are untyped `dict` via `await r.json()`,
   not dedicated Pydantic request/response models** — matches the
   pre-existing convention for this entire router module (every other
   bargain/override endpoint already worked this way before Phase 3B), so
   not a regression, but worth flagging if a future sprint wants stricter
   OpenAPI schema generation (currently the schema shows `dict`/`any`
   rather than named fields).

4. **`below_floor_rejections` KPI relies on evaluation audit logs
   (`bargain_evaluation` entity type) that only start accumulating from this
   sprint onward** — historical evaluations performed before this sprint
   (via the old `evaluate_bargain` implementation, which did not audit-log)
   are not retroactively counted. Not fixable without a backfill, and the
   ticket doesn't ask for one.

5. **Duplicate-active-rule/override checks are scoped to (master_service_id,
   pricing_rule_id) / (tenant_id, master_service_id) only** — they do not
   yet consider `service_type_id`/`brand_id`/`issue_type_id`/`zipcode`
   sub-scoping, so two bargain rules or overrides that differ only by, e.g.,
   brand would currently be flagged as duplicates even if the ticket intends
   finer-grained scoping. This is a conservative (over-blocking rather than
   under-blocking) simplification, explicitly worth a product decision in a
   future sprint if finer scoping is required.

6. Same audit-system fragmentation noted in the prior Phase 3 sprint
   (`master_data_audit_log` not surfaced in the dedicated `/admin/audit-logs`
   UI's 3 tabs) still applies — unchanged this sprint, out of Phase 3B's
   backend-only scope.
