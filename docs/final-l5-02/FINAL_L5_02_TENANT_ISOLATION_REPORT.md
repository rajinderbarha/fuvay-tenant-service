# FINAL-L5-02 — Tenant Isolation Certification

Two tenants: `demo-ac-services` (Tenant A, full data) and `isolation-test-services` (Tenant B).

## Data-layer isolation (verified, from FINAL-L5-01 + re-confirmed)
- Tenant A's users, jobs, ledger, coverage, provider offerings all carry Tenant A's `tenant_id`; Tenant B has its own owner and **zero** jobs/ledger/coverage rows — no cross-tenant leakage.
- Cross-join check `service_jobs JOIN users ON assigned_staff_id WHERE user.tenant_id != job.tenant_id` returns 0 rows — no technician assigned across tenants.
- Global catalog (`master_services`, `service_types`, `brands`, `master_issue_types`, `master_offerings`) has no `tenant_id` column — correctly global.

## Live authorization isolation (verified this sprint)
- The admin-tenant endpoints that expose cross-tenant data (`GET /v1/admin/tenants`, `/{tenant_id}`, etc.) are now `require_super_admin`-gated — a tenant user cannot read the admin cross-tenant surface at all (403, verified live).
- Tenant-scoped provider/staff endpoints derive `tenant_id` from the authenticated user's JWT (`tenant_id` claim), not from request input, for the paths exercised.

## Not exhaustively tested this sprint
The full 14-vector isolation matrix (path-ID swap, body `tenant_id` override, query `tenant_id` override across profile/services/pricing/coverage/jobs/ledger/notifications/settings/file-upload) was **not run end-to-end** for every tenant endpoint. The critical vectors — cross-tenant admin read (blocked by RBAC fix) and cross-tenant job/staff assignment (blocked at data layer) — are verified. Body/query `tenant_id`-override attacks on each individual tenant mutation endpoint were not each independently fuzzed this sprint.

## Result
**Tenant isolation: PASS at the data layer and for the critical cross-tenant admin-read vector** (the one tied to the fixed RBAC vulnerability). Exhaustive per-endpoint `tenant_id`-override fuzzing across all tenant mutations is representative, not complete — documented honestly.
