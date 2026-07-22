# Duplicate / Concurrency Review — Slice 2F-13 (Workstream 14)

## Bulk / reorder / generation endpoints
**None exist** in this router. All mutations are single-record:
create/update/delete a template, add/update/delete one item. No bulk
answer, bulk completion, reorder, template bulk-update, or checklist
generation endpoint. So the mission's bulk-input-size / mixed-foreign-ID
/ per-item-result concerns are `UNSUPPORTED_CAPABILITY` here.

## Duplicate behavior
- **Duplicate template name**: `create_template` has an explicit
  application guard — an active template with the same
  `(tenant_id, service_id, name)` raises `409 CONFLICT`. Classification:
  **DUPLICATE_REJECTED**. Verified by existing
  `test_step8_quote_checklist.py::test_duplicate_active_template_name_blocked`.
- **Duplicate item**: no uniqueness constraint on item title — multiple
  items with the same title are allowed by design (a template may legitimately
  repeat a step). **DUPLICATE_ALLOWED** (explicit, benign).

## Concurrency
- **Duplicate template creation race**: the 409 guard is a
  SELECT-then-INSERT (no unique DB constraint / advisory lock), so two
  concurrent identical creates could both pass the check. Classification:
  **CONCURRENCY_RISK_DOCUMENTED** — a benign duplicate-template risk (no
  financial or completion-gate consequence; templates are catalog defs).
  Not fixed (no unique constraint added — out of scope: "do not redesign
  transaction infrastructure"; and the mission forbids adding migrations
  here).
- **No completion / snapshot concurrency**: this router creates no job
  checklist snapshots and no completion finalization, so the
  concurrent-finalization / duplicate-active-checklist risks do not arise
  here.

## Denied operations create no mutation
Read-only-scope and wrong-persona denials happen at the guard layer
before the service runs; foreign-tenant/foreign-item denials raise before
any `db.flush` — proven across the test suite.
