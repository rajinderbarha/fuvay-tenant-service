# Slice 2F-14D Approval Gate

> **QUALIFIED (Slice 2F-14E):** `CREATE_JOB_RELATIONAL_INTEGRITY_CLOSED` below covered only
> cross-FIELD consistency (customer/service matching) — it did not resolve Booking/parent
> source-STATE eligibility (a cancelled/draft Booking or a not-yet-approved consultation could
> still be referenced) or manual customer-selection authority, both explicitly flagged as open
> at the top of Slice 2F-14E's own mission. Booking/parent status eligibility and
> booking+parent-coexistence are now fixed in Slice 2F-14E; manual customer authority was
> investigated and found to be a genuine product-policy question, not a defect. Cross-field
> mismatch/duplicate fixes and route-security closure below remain accurate and unchanged. See
> `docs/workflow-rearchitecture/phase-02a-slice-02f14e/documentation-corrections.md` and
> `docs/workflow-rearchitecture/phase-02a-slice-02f14e/approval-gate.md` for the current status.

## Final status

**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

- **SECURITY_CLOSED**: all Slice 2F-14C route protections remain intact — `field_ops.router`
  28/28, `field_ops.staff_router` 6/6, re-verified via fresh `--verify-module` runs (exit 0) and
  full re-run of the Slice 2F-14B/14C authorization test suites (unchanged, all passing).
- **CREATE_JOB_RELATIONAL_INTEGRITY_CLOSED**:
  - Every supported creation mode is explicit (`MANUAL_PROVIDER_JOB`,
    `PARENT_JOB_DERIVED_REPAIR`, `STANDALONE_JOB_WITH_BOOKING_REFERENCE`; `BOOKING_DERIVED_JOB`
    identified as belonging to the separate, unmodified `Booking.convert_to_job` pipeline).
  - Authoritative customer source is explicit: `PROVIDER_SELECTED_EXISTING_CUSTOMER` for the
    manual mode; cross-checked against booking/parent when either is also supplied.
  - Authoritative service source is explicit: independently supplied/catalog-validated;
    cross-checked against `booking_id` (must match); intentionally NOT cross-checked against
    `parent_job_id` (documented policy, matches `convert_to_repair`).
  - Booking/customer/service consistency is enforced (`CUSTOMER_BOOKING_MISMATCH`/
    `SERVICE_BOOKING_MISMATCH`, fixed this slice).
  - Parent/customer consistency is enforced (`CUSTOMER_PARENT_JOB_MISMATCH`, fixed this slice).
  - Booking/parent combination behavior is explicit (not mutually exclusive; each independently
    cross-checked against its own customer/service — documented as `PRODUCT_DECISION_REQUIRED`
    whether to formalize mutual exclusivity, not silently assumed safe).
  - Duplicate source behavior is explicit: booking-to-Job and consultation-to-repair are both
    now `DUPLICATE_REJECTED` (fixed this slice, mirroring pre-existing sibling-route guards);
    other parent/child combinations are `MULTIPLE_CHILDREN_ALLOWED` by evidenced policy.
  - Invalid combinations create no partial records: verified (all new checks precede `db.add`;
    no assignment/checklist-item/history is ever created on a rejected request).
- **PRIVACY_CLOSED**: a Job cannot be associated with an unrelated customer through mismatched
  linked records (fixed — both booking and parent cross-checks close this). Foreign customer or
  booking relationships do not leak data (404/422 on mismatch, no content disclosed). Notifications
  and histories target the correct customer (server-derived actor fields, unchanged; the domain
  event published always carries the already-validated, consistent `job.customer_id`).
- **GLOBAL_COVERAGE_CLOSED**: 169/210 remains canonical (no runtime evidence changed this slice —
  confirmed via fresh `--verify-module` runs and the unmodified coverage-recount test suite).
  Both CSVs recount identically. Runtime verification agrees.
- **PRODUCT_POLICY BLOCKED** for: existing-customer-relationship requirement; booking/parent
  mutual exclusivity; booking/parent status preconditions on manual reference fields;
  concurrency hardening; customer-consent recording; address normalization. None of these are
  security gaps.

## Scope discipline confirmed

No second router module was begun. `ServiceJob`, `ServiceBooking`, `Booking` (including
`Booking.convert_to_job`), `quote_checklist`, `PartsRequest` were not modified — this slice's
fixes are entirely contained within `FieldOpsService.create_job`, reusing the existing `Booking`/
`Job`/`ServiceCatalogItem`/`User` models read-only. No role or alias was added. No new permission
was added. No cross-pipeline adapter was introduced (`Booking` is read, never written, by
`create_job`'s new checks). `readonly@demo-ac-services.local` untouched. Migration 144 unapplied.
No visual redesign occurred.

## Coverage

**169 protected of 210**, field_ops subtotal **40/40** — unchanged from the Slice 2F-14C
baseline, confirmed via fresh runtime verification.

## Regression

253 passed across direct slice/dependency suites; 1625 passed in the broad partition sweep; 21
pre-existing live-environment exclusions honestly separated out.

## Stop condition

Per this slice's closing instruction, this response stops at the Slice 2F-14D approval gate. No
further router module is started. `create_job`'s individual-field ownership (2F-14C) and
cross-field relational consistency (2F-14D) are both now closed.
