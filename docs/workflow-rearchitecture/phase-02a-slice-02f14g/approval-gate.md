# Slice 2F-14G Approval Gate

> **SUPERSEDED (Slice 2F-15):** the `SECURITY_CLOSED_CUSTOMER_AUTHORITY_PROVENANCE_BLOCKED`
> status below was blocked specifically on `BookingService.create_booking`'s missing customer
> validation and the resulting self-confirmation bootstrap chain, both explicitly named as
> out-of-scope for this slice. Slice 2F-15 closes that exact gap by fixing `create_booking`
> directly (customer existence/state validation + an existing same-tenant relationship
> requirement for tenant-assisted bookings). See
> `docs/workflow-rearchitecture/phase-02a-slice-02f15/documentation-corrections.md` and
> `docs/workflow-rearchitecture/phase-02a-slice-02f15/approval-gate.md` for the current status.
> All other findings (route security, coverage, `_assert_tenant_customer_relationship`'s own
> predicate) remain accurate and unchanged.

## Final status

**SECURITY_CLOSED_CUSTOMER_AUTHORITY_PROVENANCE_BLOCKED**

## Rationale

- **SECURITY_CLOSED**: all existing route protections remain intact (`field_ops.router` 28/28,
  `field_ops.staff_router` 6/6, re-verified via fresh `--verify-module` runs and full re-run of
  the Slice 2F-14B/14C/14D/14E/14F authorization suites). No alternate route can fabricate
  qualifying relationship evidence for an *unrelated* customer within the boundary this slice can
  fix: the trivial one-call bootstrap (create a low-trust Booking) is closed; a legacy Job row
  can no longer silently establish authority.
- **CUSTOMER_AUTHORITY — provenance genuinely BLOCKED, not closed**: every qualifying relationship
  source now has trustworthy STRUCTURAL provenance (Booking status reachability, Job lineage
  fields) — but this slice's own Workstream 1 audit found a real, disclosed architectural gap
  that structural status/lineage checks alone cannot close: `BookingService.create_booking`'s
  missing customer validation combined with `confirm_booking`'s unilateral tenant confirmation
  means a determined `tenant_owner` can still reach a "qualifying" status without genuine
  customer participation, by fabricating AND self-confirming a Booking. This is reported honestly
  as a provenance block, not force-closed — per the mission's explicit instruction: "do not claim
  customer-authority closure while an unrelated tenant can create a qualifying draft/legacy
  record and then pass the manual Job relationship check." (Note: the record is no longer
  "draft" — it must reach `CONFIRMED` — but the underlying gap of provider-only creation +
  provider-only confirmation remains, just requiring 2 calls with `BOOKING_MANAGE` authority
  instead of 1.)
- **PRIVACY_CLOSED for the fixable boundary**: an unrelated tenant cannot create customer history
  through the trivial fabrication path any more (closed this slice). Relationship errors do not
  disclose another tenant or customer activity (unchanged, re-verified). Rejected bootstrap
  attempts produce no customer-visible side effects (verified via `db.add.assert_not_called()`
  across all 17 new tests).
- **DOMAIN_INTEGRITY_CLOSED**: relationship status and provenance rules are now explicit
  (booking-status-trust-matrix.csv, field-ops-job-creation-provenance.csv). Source eligibility and
  lineage rules from Slices 2F-14D/14E remain intact (re-verified via full regression). Invalid
  evidence is rejected before persistence (unchanged position in validation order). Valid
  Booking/parent/manual modes remain functional (re-verified: no fixture changes were needed for
  any pre-existing test).
- **GLOBAL_COVERAGE_CLOSED**: 169/210 remains canonical (confirmed via fresh `--verify-module`
  runs and the unmodified coverage-recount test suite). Both CSVs recount identically.
- **PRODUCT_POLICY BLOCKED** for: `BookingService.create_booking`'s missing customer validation;
  `confirm_booking`'s unilateral confirmation; `BookingStatusHistory`-based cancelled/voided
  disambiguation; `TENANT_LOCAL_CUSTOMER_DIRECTORY_WITH_VERIFIED_LINKING`; customer-contact
  merging; database-level provenance marker; database concurrency hardening; future migration of
  legacy customer relationships; address normalization.

## Scope discipline confirmed

No second router module was begun. `Booking.convert_to_job`, `ServiceJob`, `ServiceBooking`,
`quote_checklist`, `PartsRequest` were not modified — this slice's fixes are entirely contained
within `FieldOpsService._assert_tenant_customer_relationship`, reusing the existing `Booking`/
`Job`/`BS` constants read-only. No new table, migration, role, or permission was added. No
cross-pipeline adapter was introduced. `readonly@demo-ac-services.local` untouched. Migration 144
unapplied. No visual redesign occurred.

## Coverage

**169 protected of 210**, field_ops subtotal **40/40** — unchanged from the Slice 2F-14F
baseline, confirmed via fresh runtime verification.

## Regression

202 passed across direct slice/dependency suites (0 failures attributable to this slice); 1698
passed in the broad partition sweep, 0 failed. No pre-existing test file required a fixture
update.

## Stop condition

Per this slice's closing instruction, this response stops at the Slice 2F-14G approval gate. No
further router module is started. The trivial relationship-bootstrap vector and legacy-Job
grandfathering risk are closed. The residual self-confirmation gap is a genuine, disclosed
architectural limitation in the booking engine (`BookingService.create_booking`/
`confirm_booking`), explicitly out of this slice's scope, and is reported honestly as a
provenance block rather than falsely claimed as fully closed.
