# create_job Invalid-Persistence Proof

## Ordering

All new validations (`service_type_id` → `parent_job_id` → `booking_id` → `customer_id`) execute
**before** the `Job(...)` constructor call and before `self.db.add(job)`. Confirmed via direct
source inspection: the validation block is inserted immediately after the `job_type` enum check
and immediately before `job = Job(...)`.

## Proven per rejected case

- **Foreign `tenant_id`**: rejected before reaching any of the new checks (pinned at the top of
  the method, Slice 2F-14B) — `test_tenant_owner_cannot_override_tenant_id`.
- **Foreign/missing `service_type_id`**: `FOREIGN_SERVICE_TYPE` / `INACTIVE_SERVICE_TYPE` raised
  before `Job(...)` — `test_foreign_service_type_rejected`, `test_inactive_service_type_rejected`.
- **Foreign/missing `parent_job_id`**: `FOREIGN_PARENT_JOB` raised before `Job(...)` —
  `test_foreign_parent_job_rejected`, `test_missing_parent_job_rejected`.
- **Foreign `booking_id`**: `FOREIGN_BOOKING` raised before `Job(...)` —
  `test_foreign_booking_rejected`.
- **Foreign/missing `customer_id`**: `FOREIGN_CUSTOMER` raised before `Job(...)` —
  `test_foreign_customer_rejected`, `test_missing_customer_rejected`.
- **No linked-record category exists for address/staff/technician/template/schedule-slot** — see
  create-job-request-field-inventory.csv (`UNSUPPORTED_FIELD`); no fabricated test was written
  for a field the route does not accept.

## No Job, assignment, checklist item, status history, audit, or notification side effect on
## rejection

Verified directly: `test_no_job_created_on_rejection` asserts `db.add.assert_not_called()` after
a rejected `create_job` call. Since `Job(...)` is never constructed, no cascading effect
(`self._write_history`, `adjust_usage`, Redis token caching, `self._publish("job.created", ...)`)
is reachable either — all of these occur strictly after `self.db.add(job); await self.db.flush()`
in the source, which the rejection path never reaches.

## Read-only tenant owner / read-only staff / technician / customer / unknown role / unknown scope

These are enforced at the **router** level (`require_tenant_mutation_permission`, Slice 2F-14B,
unchanged this slice) — a rejected persona/scope never reaches the service method at all, so no
linked-record validation or persistence is attempted. Re-verified via full regression
(`test_phase2f14b_field_ops_creation_conversion_quote_authorization.py` still passing).
