# Slice 2F-14E Approval Gate

> **SUPERSEDED (Slice 2F-14F):** the `SECURITY_CLOSED_CUSTOMER_AUTHORITY_PRODUCT_POLICY_BLOCKED`
> status below was accurate at the time (no relationship policy had been ratified yet). A secure
> interim policy has since been ratified and implemented in Slice 2F-14F: standalone manual
> `create_job` now requires an existing same-tenant Booking or Job relationship for the requested
> customer. See `docs/workflow-rearchitecture/phase-02a-slice-02f14f/documentation-corrections.md`
> and `docs/workflow-rearchitecture/phase-02a-slice-02f14f/approval-gate.md` for the current
> status. All other findings below (source eligibility, lineage, route-security, coverage) remain
> accurate and unchanged.

## Final status

**SECURITY_CLOSED_CUSTOMER_AUTHORITY_PRODUCT_POLICY_BLOCKED**

## Rationale for this status (rather than full SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED)

- **SECURITY_CLOSED**: all route protections remain intact (`field_ops.router` 28/28,
  `field_ops.staff_router` 6/6, re-verified via fresh `--verify-module` runs and full re-run of
  the Slice 2F-14B/14C/14D authorization suites). No cross-tenant source or customer authority
  bypass exists — every tenant-owned reference (`service_type_id`/`parent_job_id`/`booking_id`)
  is tenant-validated, and no actor can associate a Job with a customer account they don't have
  independent, legitimate authority to reference (the tenant staff member's own
  `require_tenant_mutation_permission` authority is the operative control, unchanged and correct).
- **SOURCE_ELIGIBILITY_CLOSED**: Booking reference semantics classified
  (`AUTHORITATIVE_LINEAGE_REFERENCE`). Every real Booking status adjudicated (12 non-CONFIRMED
  statuses rejected, CONFIRMED allowed). Parent Job semantics classified (dual regime:
  `AUTHORITATIVE_REPAIR_SOURCE` for CONSULTATION→REPAIR, `INFORMATIONAL_PARENT_REFERENCE`
  otherwise). Every real parent status for the CONSULTATION→REPAIR combination adjudicated (12
  non-QUOTE_APPROVED statuses rejected, QUOTE_APPROVED allowed). Invalid sources create no
  records (verified via `db.add.assert_not_called()` across all rejection tests).
- **LINEAGE_INTEGRITY_CLOSED**: `booking_id`/`parent_job_id` coexistence is explicit
  (`MUTUALLY_EXCLUSIVE`, fixed this slice). Authoritative source fields are explicit
  (source-derived-field-matrix.csv). No ambiguous source combination persists.
- **CUSTOMER_AUTHORITY — genuinely BLOCKED, not closed**: this slice's Workstream 5/6
  investigation conclusively found NO tenant/customer relationship model anywhere in this
  codebase, and determined that inventing a "prior relationship required" rule would break the
  evidenced legitimate use case of creating the FIRST Job for a new customer. This is reported
  honestly as a **product-policy block**, not force-closed as `PRIVACY_CLOSED` — per the
  mission's own explicit instruction: "Do not claim complete privacy closure while a tenant can
  target an unrelated global customer without explicit authority." A tenant CAN currently target
  any real platform customer account; this is disclosed, not hidden, and is not classified as a
  security defect since it grants no elevated access to that customer's other data (see
  manual-customer-authority.md for the full reasoning).
- **GLOBAL_COVERAGE_CLOSED**: 169/210 remains canonical (no runtime evidence changed this slice —
  confirmed via fresh `--verify-module` runs and the unmodified coverage-recount test suite).
  Both CSVs recount identically.
- **PRODUCT_POLICY BLOCKED** for: existing tenant/customer relationship requirement;
  `booking_id`/`parent_job_id` documented coexistence semantics (if ever needed); address
  derivation from booking; concurrency hardening; customer-consent recording; address
  normalization; tenant/customer directory design.

## Scope discipline confirmed

No second router module was begun. `Booking.convert_to_job`, `ServiceJob`, `ServiceBooking`,
`quote_checklist`, `PartsRequest` were not modified — this slice's fixes reuse existing `BS`/`JS`
constants and existing `Booking`/`Job` models read-only. No role or alias was added. No new
permission was added. No cross-pipeline adapter was introduced.
`readonly@demo-ac-services.local` untouched. Migration 144 unapplied. No visual redesign occurred.

## Coverage

**169 protected of 210**, field_ops subtotal **40/40** — unchanged from the Slice 2F-14D
baseline, confirmed via fresh runtime verification.

## Regression

All direct slice/dependency suites passing (0 failures attributable to this slice); 1656 passed
in the broad partition sweep; the same pre-existing live-environment exclusion class honestly
disclosed.

## Stop condition

Per this slice's closing instruction, this response stops at the Slice 2F-14E approval gate. No
further router module is started. `create_job`'s individual-field ownership (2F-14C), cross-field
relational consistency (2F-14D), and source eligibility/lineage (2F-14E) are all now closed at
the security and domain-integrity level. The remaining customer-authority question is a genuine,
disclosed product-policy decision, not a defect requiring further code changes.
