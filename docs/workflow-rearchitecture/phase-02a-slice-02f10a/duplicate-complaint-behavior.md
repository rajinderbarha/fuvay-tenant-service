# Duplicate and Existing-Complaint Behavior — Slice 2F-10A (Workstream 4)

## Mechanism
`check_eligible`'s `check_duplicate_open_complaint` is an **application-level
guard**, not a database unique constraint — confirmed by direct read of
`CustomerComplaint`'s model (no unique index across
`customer_id`/`record_type`/`record_id`/`complaint_type`). No migration
was added or is being added this slice (explicitly out of scope).

## Classification
- **First valid complaint**: `CREATION_ALLOWED`.
- **Exact repeated create request (same record, same complaint_type,
  first still open)**: `DUPLICATE_REJECTED` — now enforced at creation
  (previously bypassed; see `complaint-creation-policy-matrix.csv`).
- **Second complaint, different `complaint_type`, same record**:
  `MULTIPLE_ALLOWED_BY_EXPLICIT_POLICY` — the duplicate check is scoped
  to `(customer_id, record_type, record_id, complaint_type)`, so a
  different `complaint_type` (e.g. "billing_dispute" after
  "service_quality") is a distinct, allowed complaint by design.
- **Existing complaint in `resolved`/`closed`/`cancelled`/`rejected`**:
  `MULTIPLE_ALLOWED_BY_EXPLICIT_POLICY` — `OPEN_STATUSES` (the duplicate
  check's scope) excludes all 4 of these; a new complaint of the same
  type against the same record is allowed once the prior one is no
  longer open. This directly answers the mission's question "does a
  resolved complaint allow a new complaint?": **yes, by explicit,
  existing policy** (the duplicate guard's own `OPEN_STATUSES` set proves
  this was a deliberate scoping choice, not an oversight).
- **Existing complaint in `resolution_proposed`**: `DUPLICATE_REJECTED`
  — `resolution_proposed` is in `OPEN_STATUSES`.
- **Same customer, another job**: `CREATION_ALLOWED` — the duplicate
  check is scoped to the specific `record_id`, not the customer globally.
- **Another customer, same tenant/provider**: `CREATION_ALLOWED` —
  ownership is per-customer/per-record, not shared across customers of
  the same tenant.
- **Retry after transaction failure**: not idempotent by an idempotency
  key (none exists in `CreateComplaintIn`), but the duplicate-open-complaint
  guard now provides an equivalent practical protection — a retried
  request after a successful first creation is rejected as a duplicate,
  not silently creating a second row. A retry after a genuinely failed
  (rolled-back) first attempt succeeds normally (no complaint was ever
  persisted).

## Concurrency
No row/advisory locking exists around the duplicate check — a race
between two concurrent identical requests could both pass the
`SELECT`-based duplicate check before either commits, producing 2 open
complaints. This is a **known, documented concurrency limitation**
(`CONCURRENCY_RISK_DOCUMENTED`), consistent with the mission's explicit
instruction not to add a unique constraint or migration in this slice.

## Not changed this slice
No unique database constraint or migration was added. The duplicate
guard's scope and `OPEN_STATUSES` set are unmodified — this slice only
made the pre-existing guard *reachable from creation* (it previously ran
only in the separate, un-consulted advisory endpoint).
