# Slice 2F-12A Implementation Summary

## Scope
Narrow follow-up to Slice 2F-12: fully adjudicate and verify
`cancel_appointment`'s object-authorization (assignment) behavior, which
2F-12 left as the one unresolved question.

## The question
`cancel_appointment` does not call `_assert_staff_owns_appt` (the
per-appointment assignment check) that the other 7 coaching mutations
use. 2F-12 documented this as "plausibly intentional business-wide
cancellation" but explicitly marked it UNVERIFIED and flagged that the
evidence did not yet prove whether canonical staff should have
business-wide or assigned-only cancellation authority.

## Resolution: VERIFIED via approved cross-module evidence (no code change)
The sibling `home_service_service.cancel_job` — the canonical
field-service execution module CLOSED and APPROVED in **Slice 2F-3B** —
uses the byte-for-byte identical pattern: whole-record cancellation
deliberately omits `_assert_staff_owns_job` while every other job
mutation enforces it. Slice 2F-3B explicitly documented and approved
`POST /v1/provider/service-jobs/{job_id}/cancel` as a **"tenant-wide
(business-wide) provider action"**, `n/a` for assignment ownership
(`phase-02a-slice-02f3b/execution-assignment-enforcement-matrix.csv` and
`execution-assignment-policy-matrix.csv`).

Same Sprint 21 author, same signature shape
(`cancel_X(db, id, tenant_id, user_id, reason, actor_role="provider")` —
**no `staff_member_id` parameter at all**, unlike the assignment-checked
methods), same `actor_role="provider"` default, same deliberate omission
of the assignment helper.

**Evidence class**: `EXPLICIT_PRODUCT_POLICY` (2F-3B approved) +
`TESTED_EXISTING_CONTRACT` + `ESTABLISHED_CROSS_MODULE_PATTERN`.

**Conclusion**: business-wide cancellation for tenant_owner AND canonical
staff is the intentional, approved, cross-module-consistent design — not
an assignment gap. Coaching's `cancel_appointment` is in fact **stricter**
than the approved sibling: 2F-12 gates it with
`require_owner_or_office_staff_mutation` (technician excluded), vs.
`cancel_job`'s `require_staff_or_above_mutation` (which admits
technician). So no fix is warranted, and the 2F-12 "business-wide"
characterization was substantively correct — it simply hadn't been
cross-referenced against the approved 2F-3B sibling until now.

## Final cancellation persona matrix (verified)
| Persona | Authority | Classification |
|---|---|---|
| tenant_owner | business-wide (any same-tenant appointment) | TENANT_OWNER_BUSINESS_WIDE_CANCEL |
| canonical staff | business-wide (any same-tenant appointment) | STAFF_BUSINESS_WIDE_CANCEL |
| super_admin | business-wide (existing behavior preserved) | EXISTING_BEHAVIOR_PRESERVED |
| technician | denied | TECHNICIAN_CANCEL_DENIED |
| customer | denied (from this provider route) | CUSTOMER_CANCEL_DENIED |
| cross-tenant (any role) | denied (tenant filter) | — |
| read-only tenant scope | denied (mutation guard) | — |

## What changed
1. **New test file**: `tests/test_phase2f12a_coaching_cancellation.py`
   (27 tests) — HTTP-level cancellation persona matrix, service-level
   business-wide proof (cancel succeeds for a non-assigned actor; accept
   by contrast is blocked), cross-tenant denial, full cancellation-state
   matrix (legal from confirmed/accepted/scheduled; rejected from
   started/completed/no_show/rejected/cancelled with no mutation), reason
   integrity, and direct source proof that cancel omits the assignment
   check while accept enforces it and the sibling `cancel_job` matches.
2. **Slice 2F-12 documentation corrected** — the "business-wide,
   documented but unverified / product-decision-required" wording is
   upgraded to "verified via approved 2F-3B cross-module pattern" (see
   `documentation-corrections.md`).

## What did NOT change
No source file. `cancel_appointment`, `APPT_TRANSITIONS`, the 7
assignment-checked mutations, all 8 route guards, provider reads,
customer tracking, and `app.engines.coaching_appointment` are all
unmodified. No permission or role was created. `field_ops.*` was not
begun. Global tenant mutation coverage remains **125/182**.

## Outcome
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED` —
with cancellation object-authorization now CLOSED (verified), not
blocked. See `approval-gate.md`.
