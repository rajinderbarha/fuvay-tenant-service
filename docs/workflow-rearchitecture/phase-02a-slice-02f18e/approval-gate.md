# Slice 2F-18E Approval Gate

> **SUCCEEDED BY SLICE 2F-19.** This slice closed the final chat-media
> control identified across the six-slice `platform_notifications` series
> (2F-18 through 2F-18E). Slice 2F-19
> (`docs/workflow-rearchitecture/phase-02a-slice-02f19/`) reconciled the
> remaining 26 unprotected canonical routes, confirmed the 200/226
> baseline unchanged, and selected `app.engines.compliance.provider_router`
> as the next implementation module. This notice records the series'
> conclusion and handoff, not a correction — nothing in this slice's
> findings was factually wrong.

## Final status

**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

## Why SECURITY_CLOSED (deepened — office first-use ambiguity closed)
- Per the mission's own instruction ("Do not claim security closure while
  office/staff may redistribute ambiguous media to an unrelated Job
  audience"): a `tenant_owner`/`staff` actor can no longer first-claim an
  unowned, unclaimed asset into a customer-linked thread merely by
  passing tenant/customer matching —uploader-match is now required
  (`test_staff_cannot_first_claim_unowned_asset_into_customer_thread`,
  `test_tenant_owner_same_ambiguity_rule_as_staff`).
- Provider-internal sharing (no customer party) remains correctly
  unaffected (`test_staff_can_first_claim_into_provider_internal_thread`),
  matching the ratified policy's explicit allowance.
- `replace_asset` no longer conflates view authority with replace
  authority — a customer or technician who can merely VIEW a same-tenant
  asset can no longer overwrite someone else's upload
  (`test_customer_cannot_replace_provider_asset`,
  `test_technician_cannot_replace_unowned_asset`).
- All 2F-18/2F-18A/2F-18B/2F-18C/2F-18D security controls remain intact
  and unmodified — re-confirmed by the full targeted regression (374
  tests).

## Why DOMAIN_INTEGRITY_CLOSED (deepened — atomicity now proven, not merely asserted)
- Per the mission's own instruction ("Do not claim domain-integrity
  closure while a failed message can leave an orphan claim or a reader
  can replace another user's attachment"): both are now directly proven,
  not merely structurally argued —
  `test_no_commit_before_claim_and_message_are_both_ready` and
  `test_commit_failure_propagates_not_swallowed` give deterministic proof
  of the transaction-boundary properties 2F-18D introduced but never
  independently tested; `replace_asset`'s new authorization closes the
  reader-can-replace gap.
- Retrieval lifecycle enforcement closes the remaining "stale
  authorization bypasses lifecycle state" risk — a `chat_attachment`
  asset that becomes deleted/inactive after being attached is now denied
  on its next retrieval, not silently still servable.

## Why PRIVACY_CLOSED (deepened — deleted/inactive assets no longer retrievable)
- Per the mission's own instruction ("Do not claim privacy closure while
  deleted/inactive chat media remains retrievable"): fixed — every
  retrieval and replacement entry point for `chat_attachment` assets now
  rejects `deleted_at`-set or non-`"active"`-status assets, converging on
  the SAME privacy-equivalent `NotFoundException` established since
  2F-18C.
- Every prior privacy-equivalence guarantee (thread errors, attachment
  errors, claimed-retrieval errors) remains intact and unmodified.

## Why PRODUCT_POLICY_BLOCKED (not fully closed)
Four genuine product questions remain open (see
`product-decisions-required.md`), none representing a live authorization
bypass in the paths this six-slice series' combined mission actually
covers:
1. Whether a thread's customer linkage could theoretically change after
   creation (currently structurally impossible, flagged for awareness).
2. Whether a dedicated, granular "media:replace" permission should be
   added in a future permission-adding slice.
3. Whether same-tenant unrelated staff replacement authority should be
   narrowed beyond the existing tenant-wide office policy.
4. Whether a live two-session concurrency integration test should be
   written for a future CI/staging environment with real Postgres access.

## Preserved (re-confirmed unchanged)
- `field_ops.router` 28/28, `field_ops.staff_router` 6/6.
- Booking authorization/provenance closure.
- Quote-checklist authorization, privacy, and invoice-lineage closure.
- `PartsRequest` remains ServiceJob-only.
- `Booking`/`ServiceBooking` and `field_ops.Job`/`ServiceJob` separation —
  this slice touched no Job/Booking model at all.
- `readonly@demo-ac-services.local` untouched.
- Migration 144 unapplied — and no migration was added or applied this
  slice either.
- No new role, permission, or alias added.
- All 2F-18/2F-18A/2F-18B/2F-18C/2F-18D controls remain intact and
  unmodified.
- All previously-approved tests still pass, unmodified (see
  `test-report.md`).

## Coverage
**Unchanged at 200/226** — verified route-by-route, not assumed (see
`canonical-coverage-reconciliation.md` and `final-selected-route-protection.csv`).
All 10 selected routes are individually confirmed `FULLY_PROTECTED`.

## Scope discipline confirmed
No new role, permission, or migration was added. No pipeline was merged.
`PartsRequest` and `quote_checklist` were not touched. No frontend/mobile
file was modified. No media upload/storage/signed-URL infrastructure or
new message-attachment table was built. No second, unrelated module's
authorization was begun.

## Stop condition
Per this slice's closing instruction, this response stops at the Slice
2F-18E approval gate. The remaining 26-route, 10-module queue is left for
a future slice; no implementation of any other module has begun. This
six-slice series (2F-18, 2F-18A, 2F-18B, 2F-18C, 2F-18D, 2F-18E) has now
addressed every workstream explicitly assigned to
`app.engines.platform_notifications.provider_router` and its full
attachment/media chain — no further sub-slice of this specific module is
anticipated unless new evidence surfaces.
