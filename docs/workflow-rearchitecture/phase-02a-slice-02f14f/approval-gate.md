# Slice 2F-14F Approval Gate

> **SUPERSEDED (Slice 2F-14G):** the `CUSTOMER_AUTHORITY_CLOSED`/`PRIVACY_CLOSED` claims below
> relied on `ANY_HISTORICAL_SAME_TENANT_RELATIONSHIP` — a Booking or Job of ANY status counting as
> relationship evidence. Slice 2F-14G's provenance audit found this exploitable: a `tenant_owner`
> could fabricate a low-trust Booking (`BookingService.create_booking` never validates
> `customer_id` against the User table) for an arbitrary real customer and immediately satisfy the
> check. Fixed in Slice 2F-14G: only `CONFIRMED`-or-later Booking statuses and source-derived
> (booking/parent-linked) Job rows now qualify. A residual, disclosed architectural gap remains
> (self-confirmation of a fabricated booking) — see
> `docs/workflow-rearchitecture/phase-02a-slice-02f14g/documentation-corrections.md` and
> `docs/workflow-rearchitecture/phase-02a-slice-02f14g/approval-gate.md` for the current status.
> All other findings (relationship-helper architecture, disabled/deleted rejection, route
> security, coverage) remain accurate and unchanged.

## Final status

**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

- **SECURITY_CLOSED**: all route protections remain intact (`field_ops.router` 28/28,
  `field_ops.staff_router` 6/6, re-verified via fresh `--verify-module` runs and full re-run of
  the Slice 2F-14B/14C/14D/14E authorization suites). No tenant can reference another tenant's
  linked records (unchanged, re-verified — `FOREIGN_BOOKING`/`FOREIGN_PARENT_JOB` guards intact).
- **CUSTOMER_AUTHORITY_CLOSED**: Booking and parent sources establish authority directly (proven:
  no redundant relationship query for either mode). Standalone manual creation requires a prior
  same-tenant relationship (implemented and tested: `_assert_tenant_customer_relationship`).
  Customers known only to another tenant are rejected (`CUSTOMER_TENANT_RELATIONSHIP_REQUIRED`).
  Completely unrelated customers are rejected (identical error). Wrong-role and
  invalid/disabled/deleted customer accounts are rejected (`FOREIGN_CUSTOMER`). Request data
  cannot override relationship authority — `customer_id` is checked against real database state,
  never trusted at face value.
- **PRIVACY_CLOSED**: an unrelated tenant cannot create customer history (no Job created on
  rejection — verified via `db.add.assert_not_called()`). No customer notifications can be
  triggered (none exist; a fortiori none fire on rejection). Another tenant's relationship is
  never disclosed (the relationship query is tenant-scoped; "known to a different tenant" and
  "known to no tenant" produce the identical result and error). Customer existence and
  relationship errors use safe, uniform semantics (see error-privacy-semantics.md). Rejected
  attempts create no customer-visible records.
- **DOMAIN_INTEGRITY_CLOSED**: all Slice 2F-14D/14E source-eligibility and lineage rules remain
  intact and re-verified (booking/parent status eligibility, mutual exclusivity, duplicate
  guards). Relationship validation occurs before Job persistence (same validation block, before
  `db.add`). Valid Booking/parent/manual modes remain explicit
  (supported-creation-mode-policy.md). Invalid requests create no partial records.
- **GLOBAL_COVERAGE_CLOSED**: 169/210 remains canonical (confirmed via fresh `--verify-module`
  runs and the unmodified coverage-recount test suite). Both CSVs recount identically.
- **PRODUCT_POLICY BLOCKED** for: `TENANT_LOCAL_CUSTOMER_DIRECTORY_WITH_VERIFIED_LINKING` (the
  long-term target, explicitly out of scope); verified customer invitation/consent workflow;
  customer-contact merging; address normalization; database-level relationship/concurrency
  constraints; future first-time manual-customer onboarding. None of these are security gaps —
  the security question this slice was opened to answer (can a tenant target an unrelated global
  customer?) is now closed: **no**.

## Scope discipline confirmed

No second router module was begun. `Booking.convert_to_job`, `ServiceJob`, `ServiceBooking`,
`quote_checklist`, `PartsRequest` were not modified. No customer-contact table, invitation flow,
OTP/consent workflow, customer-directory UI, or migration was created. No role or alias was
added. No new permission was added. No cross-pipeline adapter was introduced — the new
relationship helper reads only the pre-existing `Booking`/`Job` tables.
`readonly@demo-ac-services.local` untouched. Migration 144 unapplied. No visual redesign occurred.

## Coverage

**169 protected of 210**, field_ops subtotal **40/40** — unchanged from the Slice 2F-14E
baseline, confirmed via fresh runtime verification.

## Regression

185 passed across direct slice/dependency suites (0 failures attributable to this slice); 1681
passed in the broad partition sweep, 0 failed this run.

## Stop condition

Per this slice's closing instruction, this response stops at the Slice 2F-14F approval gate. No
further router module is started. `create_job`'s individual-field ownership (2F-14C), cross-field
relational consistency (2F-14D), source eligibility/lineage (2F-14E), and manual customer
authority (2F-14F) are all now closed at the security, domain-integrity, and privacy level. The
remaining long-term customer-directory capability is a genuine, disclosed future product
initiative, not a defect requiring further code changes now.
