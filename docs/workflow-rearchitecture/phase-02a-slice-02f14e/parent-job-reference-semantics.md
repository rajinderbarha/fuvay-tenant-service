# Parent Job Reference Semantics

## Classification: AUTHORITATIVE_REPAIR_SOURCE (for CONSULTATION→REPAIR only) / INFORMATIONAL_PARENT_REFERENCE (otherwise)

`parent_job_id` has **two distinct semantic regimes**, both confirmed via direct source
inspection:

1. **CONSULTATION → REPAIR**: `parent_job_id` is `AUTHORITATIVE_REPAIR_SOURCE` — it authorizes
   customer identity (cross-checked, 2F-14D), gates on source status (`QUOTE_APPROVED`, fixed
   this slice), and enforces uniqueness (one repair per consultation, fixed in 2F-14D). This
   exactly mirrors `convert_to_repair`'s own dedicated capability — `create_job` with this
   specific combination is a semantically equivalent, alternate entry point to the same business
   capability.
2. **Any other parent/child `job_type` combination**: `parent_job_id` is
   `INFORMATIONAL_PARENT_REFERENCE` — it still authorizes customer identity (the
   `CUSTOMER_PARENT_JOB_MISMATCH` check applies regardless of job_type combination, since a
   Job's customer should never disagree with its stated parent's customer no matter what kind of
   relationship it represents), but no status gate, no service cross-check, and no uniqueness
   constraint apply.

## Evidence

- Whether it represents repair lineage: yes, specifically for CONSULTATION→REPAIR.
- Whether it represents generic parent/child lineage: yes, for all other combinations (e.g. a
  SERVICE job spawning a follow-up SERVICE job).
- Which Job types may be parents: any (`Job.job_type` is not itself restricted by
  `parent_job_id`'s existence).
- Which Job types may be children: any.
- Whether a child inherits customer: cross-checked (must match, not silently inherited when
  independently supplied) for ALL combinations.
- Whether a child may use a different service: yes, for ALL combinations (no service
  cross-check exists for `parent_job_id` at all, unlike `booking_id`).
- Whether one parent may have multiple children: yes, except the CONSULTATION→REPAIR case
  (exactly one, enforced).
- Whether parent state affects eligibility: only for the CONSULTATION→REPAIR case (fixed this
  slice).
- Audit/history: `parent_job_id` is stored on the Job row; not separately called out in
  `JobStatusHistory`.
- Completion/invoice/commission: not affected by `parent_job_id` directly.
- Frontend/internal callers: `FieldOpsService._spawn_repair_from_consultation` (internal),
  always uses the CONSULTATION→REPAIR combination.
