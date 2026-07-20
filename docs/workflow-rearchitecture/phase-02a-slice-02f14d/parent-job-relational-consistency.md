# Parent Job Relational Consistency

## Disposition: PARENT_FIELDS_CROSS_CHECKED (customer) + REPAIR_SERVICE_MAY_DIFFER_BY_POLICY (service)

## Verified / fixed this slice

- **Parent is a field_ops.Job**: confirmed — `parent_job_id` is looked up against the `Job` model
  itself (Slice 2F-14C, unmodified).
- **Parent belongs to principal tenant**: enforced (Slice 2F-14C, unmodified).
- **Parent customer matches the child Job customer**: fixed this slice
  (`CUSTOMER_PARENT_JOB_MISMATCH` if an explicitly-supplied `customer_id` disagrees with
  `parent.customer_id`).
- **Parent service matches or legally maps to the child service**: service type is **NOT**
  cross-checked — `convert_to_repair`'s own established, pre-existing behavior
  (`repair_service_id or job.service_type_id`) already treats a differing repair service as
  legitimate product policy (a consultation's service type and its spawned repair's service type
  are frequently different, e.g. "AC Diagnosis" consultation → "AC Compressor Replacement"
  repair). Enforcing a match here would contradict already-approved behavior in a sibling route.
- **Parent status permits child/repair creation**: **not enforced** by `create_job` (same gap
  class as booking status, see known-limitations.md) — `convert_to_repair`'s own
  `JS.QUOTE_APPROVED` precondition is not re-checked here since `create_job` is a generic,
  non-conversion-specific endpoint. Recorded as `PRODUCT_DECISION_REQUIRED`.
- **Parent is not itself an invalid child source**: no additional constraint found or needed
  beyond tenant/customer ownership.
- **Parent chain cannot create a direct cycle**: `parent_job_id` cannot equal the new Job's own
  `id` (the new Job doesn't have an `id` yet at validation time — structurally impossible).
- **Parent chain cannot create an indirect cycle**: not applicable — `parent_job_id` is a single-
  level reference (no chain-walking logic exists anywhere in this codebase that could be
  corrupted by a cycle); a Job's `parent_job_id` is never itself required to have a null
  `parent_job_id`, so multi-level chains are structurally possible but harmless (nothing
  recursively walks the chain).
- **Duplicate child/repair creation prevented where policy requires**: fixed this slice — when
  `parent.job_type == CONSULTATION` and the new Job's `job_type == REPAIR`, mirrors
  `convert_to_repair`'s/`spawn_repair`'s own existing duplicate-repair guard
  (`CONSULTATION_ALREADY_CONVERTED`, 409). For any other parent/child `job_type` combination,
  **multiple children per parent are allowed** — no evidence of a uniqueness requirement exists
  for non-consultation parents (see duplicate-idempotency-policy.md).
- **parent_job_id and booking_id compatibility**: not mutually exclusive, see
  supported-creation-modes.md.
- **No bridge to ServiceJob**: confirmed — `parent_job_id` only ever references another
  `field_ops.Job` row.
