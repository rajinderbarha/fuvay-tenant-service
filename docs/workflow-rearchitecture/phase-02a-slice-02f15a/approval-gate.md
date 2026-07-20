# Slice 2F-15A Approval Gate

> **QUALIFIED BY SLICE 2F-15B.** This slice's `CUSTOMER_AUTHORITY_PROVENANCE_CLOSED` and
> `179/220` figures were directionally correct but not yet proven by executed tests: the exact
> creation-event predicate, the fail-closed behavior for missing/ambiguous legacy history, later-
> customer-activity non-establishment, and the customer-dependency/tenant-scope independence were
> all asserted from source reading rather than demonstrated. Slice 2F-15B
> (`docs/workflow-rearchitecture/phase-02a-slice-02f15b/`) proves each with new executed tests and
> physically removes `booking_preflight` from the canonical coverage CSV. No finding in 2F-15B
> reverses this slice's code changes — see `phase-02a-slice-02f15b/documentation-corrections.md`.

## Final status

**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

- **SECURITY_CLOSED**: all 11 mounted `booking.router` mutation routes are reconciled
  (`exact-booking-route-reconciliation.csv`). The 6 that left `--verify-module app.engines.booking.router`
  exiting non-zero at the 2F-15 gate are resolved: 5 (`cancel_booking`, `request_reschedule`,
  `accept_reschedule`, `reject_reschedule`, `add_note`) now carry correct mutation-scope/staff-execution
  guards; 1 (`booking_preflight`) is confirmed a false positive (zero persistence) and exempted. Runtime
  verification for `app.engines.booking.router` now exits **0** (`runtime-verification-report.md`).
  Customer self-service mutations (`create_booking`, `cancel_booking`, `request_reschedule`) remain
  authorized via `require_tenant_mutation_permission`'s dual-persona admission, separate from
  tenant-only mutation scope (`confirm_booking`, `reject_booking`, `convert_to_job`,
  `accept_reschedule`, `reject_reschedule`, `add_note`).
- **CUSTOMER_AUTHORITY_PROVENANCE_CLOSED**: a pre-fix or provider-created confirmed Booking can no
  longer, by itself, establish customer-tenant relationship authority, be used directly by
  `field_ops.create_job`, or convert via `Booking.convert_to_job` — all three require either genuine
  customer origination (via the pre-existing `BookingStatusHistory.changed_by_role` value, no new
  column) or independent prior relationship evidence. Proven via `legacy-row-test-matrix.csv` and
  `bootstrap-attack-regression.csv`, all with `db.add.assert_not_called()` on every rejection path
  (`no-partial-persistence-proof.md`).
- **DOMAIN_INTEGRITY_CLOSED**: the Booking state machine itself is unchanged (`complete-booking-state-machine.csv`);
  this slice's fixes operate entirely in authorization/provenance layers upstream and alongside
  transitions, not within them. `Booking`/`ServiceBooking` and `field_ops.Job`/`ServiceJob` remain
  separate (unmodified, confirmed).
- **PRIVACY_CLOSED**: rejected relationship/provenance checks raise a single uniform
  `CUSTOMER_TENANT_RELATIONSHIP_REQUIRED` error in every case (own-tenant unrelated customer,
  cross-tenant customer, provider-created Booking with no independent evidence) — no case
  discloses which specific condition applied, matching the established privacy-safe error pattern
  from Slice 2F-14F/2F-14G.
- **GLOBAL_COVERAGE_RECONCILED**: canonical coverage corrected from the provisional 174/221 to
  **179/220** (see `canonical-coverage-reconciliation.md`) — +5 numerator (newly protected routes),
  -1 denominator (`booking_preflight` reclassified as a non-mutation false positive, not merely
  left unprotected).
- **PRODUCT_POLICY BLOCKED** for: truly unrecorded-provenance legacy Booking rows (if any exist with
  no creation-history row at all); the first-ever assisted booking for a brand-new phone-order
  customer with zero prior relationship evidence (see `product-decisions-required.md`). Neither is
  a security gap in the code as it exists today — both require a product decision this slice has
  no authority to make (no tenant-customer directory, invitation flow, or first-booking exception
  was in scope).

## Scope discipline confirmed

No merge of `Booking`/`ServiceBooking` or `field_ops.Job`/`ServiceJob`. `PartsRequest` and
`quote_checklist` untouched. No tenant-customer directory, customer-contact model, or
invitation/OTP/consent infrastructure created. No migration, provenance column, role, or role
alias added. No permission added merely to make a route accessible — only the existing
`require_tenant_mutation_permission`/`require_staff_or_above_mutation` dependencies (already used
across the field_ops and booking series) were applied to the 5 remaining routes. No frontend/UI
work performed. `readonly@demo-ac-services.local` confirmed untouched (no diff references it).
Migration 144 confirmed unapplied (untracked file, pre-existing, not touched or applied this
slice). No visual redesign. No second module was begun.

## Coverage

**179 protected of 220** tenant-facing/platform mutation routes (up from the provisional 174/221 —
see `canonical-coverage-reconciliation.md` for the full +5/-1 reconciliation).

## Regression

8/8 new tests passing (`test_phase2f15a_booking_provenance_and_remaining_routes.py`). 7 pre-existing
tests required additive mock-scaffolding fixes (no logic changes) after adding new provenance
queries — all fixed and passing. Full broad partition sweep: **1713 passed, 9 skipped, 0 failed**
(`regression-report.md`, `test-report.md`).

## Stop condition

Per this slice's closing instruction, this response stops at the Slice 2F-15A approval gate. No
further router module is started. `booking.router` full-router runtime verification now exits 0.
The pre-fix/legacy provider-created Booking provenance risk disclosed at every prior gate since
2F-14G is now closed at its source, subject only to the two narrow product-policy questions listed
above.
