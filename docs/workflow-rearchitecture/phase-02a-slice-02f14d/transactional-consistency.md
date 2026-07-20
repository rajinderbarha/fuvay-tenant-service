# Transactional Consistency

## Verified ordering in create_job

1. **tenant_id pinning** (Slice 2F-14B).
2. **job_type enum validation**.
3. **Linked-record validation** (this slice + Slice 2F-14C, in this exact order):
   `service_type_id` (catalog tenant+active) → `parent_job_id` (tenant + customer cross-check +
   duplicate-repair guard) → `booking_id` (tenant + customer/service cross-check + duplicate
   guard) → `customer_id` (existence + role).
4. **Job construction** (`Job(...)`).
5. **Job persistence** (`self.db.add(job); await self.db.flush()`).
6. **Status history** (`self._write_history(job, None, JS.DRAFT, ...)`).
7. **Usage-quota increment** (best-effort, wrapped in `try/except`).
8. **Redis customer-token caching** (best-effort, wrapped in `try/except`).
9. **Domain event publish** (`self._publish("job.created", ...)`).

Steps 3 (all validations) occur strictly **before** step 4/5 — confirmed by direct source
inspection: every `raise ServiceOSException` in the validation block occurs before the `job =
Job(...)` line.

`create_job` never creates an assignment or a normalized `JobChecklistItem` row (see
create-job-contract.md), so requirements 5/6 in the mission's Workstream 9 ("no assignment", "no
checklist item on failure") are vacuously satisfied — there is no code path that could create
either.

## Requirements verified

- All linked and cross-field validations occur before `db.add`: confirmed.
- Invalid combinations create no Job: confirmed (`test_no_job_created_on_rejection`, Slice
  2F-14C, re-verified; this slice's own rejection tests never reach `db.add` either, per the
  ordering above).
- Invalid combinations create no assignment/JobChecklistItem: vacuously true (see above).
- Invalid combinations create no history: confirmed — `_write_history` is called only after
  `db.add`/`db.flush`, which never execute on a rejected validation.
- A failed child-record creation rolls back the Job: not applicable — no child record (besides
  the same-transaction `JobStatusHistory` row) is created by this method.
- A failed checklist materialization does not leave a partially initialized Job: not applicable —
  checklist population is an in-memory attribute assignment on the same `Job` object before
  `db.add`, wrapped in its own `try/except` that only logs a warning on catalog-lookup failure
  (does not abort Job creation) — this is pre-existing, unmodified behavior, and does not
  constitute a "partial" Job (the Job is still fully valid without an auto-populated checklist).
- Success audit/notification does not occur before durable success: `_write_history` and
  `_publish` both occur after `await self.db.flush()`, which assigns `job.id` and durably
  persists the row within the current transaction — confirmed correct ordering, unchanged.
