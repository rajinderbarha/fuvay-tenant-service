# Test Report — Slice 2F-13

## New deterministic authorization + IDOR tests
`tests/test_phase2f13_checklist_template_authorization.py` — **19 passed**.
- Permission + access-scope gate (unauthenticated; every no-permission
  role; read-only tenant_owner denied on all 6 mutations but retains
  reads; full-scope owner clears).
- Service-layer tenant-ownership IDOR (staff foreign rejected, owner
  foreign rejected, super_admin exempt, matching allowed).
- Item→template parent integrity (foreign item rejected, correct item
  allowed).
- `list_items` read-IDOR (foreign-tenant items GET rejected, own allowed).
- Source guards (6× scope-aware guard; role-agnostic ownership check).

## Existing targeted regression (checklist / step8 / quote_checklist)
```
python -m pytest tests/test_phase2f13_checklist_template_authorization.py \
  tests/test_step8_smoke.py tests/test_checklist_system.py \
  tests/test_step8_quote_checklist.py tests/test_sprint22_quote_checklist.py -q
```
**165 passed** — includes the pre-existing `test_super_admin_can_access_any_template`,
`test_duplicate_active_template_name_blocked`, and the job-checklist
completion-gate tests, all green after the fixes.

## Sibling closure regression subset
```
python -m pytest tests/test_phase2f13_...py tests/test_phase2f12a_coaching_cancellation.py \
  tests/test_phase2f11_real_estate_authorization.py \
  tests/test_phase2f9_complaints_provider_authorization.py -q
```
**152 passed.**

## Broader field_ops / checklist / job partition
```
python -m pytest tests/ -k "checklist or field_ops or step8 or job_type or quote_checklist" -q
```
**345 passed, 1 failed** — the 1 failure is
`test_module_l5_35_staff_app_jobs_api.py::TestLive::test_field_ops_jobs_list_...`,
a **live-server-dependent** test (`httpx.ConnectError` — connects to a
running server not available in this sandbox). Pre-existing, unrelated to
this slice's changes.

## Runtime verification
`inventory_mutation_routes.py --verify-module app.engines.field_ops.checklist_router`
→ `{"total_routes": 6, "unverified_count": 0, "unverified_routes": []}`.

## Live-database / network exclusions
`test_module_l5_35_...::TestLive` — excluded (live-server dependency),
honestly reported as not-run rather than passed.

## Frontend
No frontend file changed (no caller of `/v1/tenant/checklist-templates`
exists) — TypeScript/lint not run, per the instruction.

## Reporting note
The 165/152/345 figures are **test executions across overlapping
partitions**, not unique-test totals.
