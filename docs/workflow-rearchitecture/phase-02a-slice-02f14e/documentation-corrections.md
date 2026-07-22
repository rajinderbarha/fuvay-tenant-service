# Documentation Corrections to Slice 2F-14D

| File | Original claim | Correction |
|---|---|---|
| `phase-02a-slice-02f14d/approval-gate.md` | `CREATE_JOB_RELATIONAL_INTEGRITY_CLOSED` | This covered only cross-FIELD consistency (customer/service matching), not source-STATE eligibility. A cancelled/rejected/expired/draft Booking, or a CONSULTATION parent not yet at `QUOTE_APPROVED`, could still be referenced by `create_job` — both fixed in Slice 2F-14E. Also did not resolve simultaneous `booking_id`+`parent_job_id` use, now rejected. |
| same | (implicit) `PRIVACY_CLOSED` | Slice 2F-14D did not investigate manual customer-selection authority at all — this slice's Workstream 5/6 investigation found no established tenant/customer relationship model, and reports `SECURITY_CLOSED_CUSTOMER_AUTHORITY_PRODUCT_POLICY_BLOCKED` for this specific dimension rather than a blanket `PRIVACY_CLOSED`. |
| `phase-02a-slice-02f14d/known-limitations.md` item 1 | "Booking.status/parent Job.status are not preconditioned... no evidence exists that any caller relies on a status precondition here" | Corrected: `Booking.convert_to_job`/`convert_to_repair` themselves DO rely on exactly this precondition for their own dedicated routes, and per the mission's explicit instruction ("reuse existing eligibility rules where they represent the same capability"), `create_job`'s semantically-equivalent paths now enforce the identical prerequisite. Fixed in 2F-14E, not left open. |

No file was deleted. A qualifying notice is added to
`phase-02a-slice-02f14d/approval-gate.md` per the established pattern.
