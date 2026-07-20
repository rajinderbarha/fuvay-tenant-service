# Documentation Corrections

## Corrections to Slice 2F-18D's documentation
Per this slice's mission, the following 2F-18D claims are
corrected/qualified (files remain, annotated with a pointer to this slice
— not deleted or rewritten):

- **`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED`**
  (2F-18D's final status): 2F-18D closed the TECHNICIAN first-use gap but
  left the OFFICE (tenant_owner/staff) first-use gap open — office could
  still first-claim any tenant/customer-matched asset into any of a
  customer's threads. This slice's mission explicitly says not to claim
  security closure while "office/staff may redistribute ambiguous media
  to an unrelated Job audience." 2F-18D's status is preserved as an
  honest record of what was true then (it correctly scoped its own fix to
  technician, per its own mission); this slice closes the office gap.
- **2F-18D's `unclaimed-asset-authority.md`** stated "Office access
  intentionally left tenant-wide" for VIEWING — this remains TRUE and
  unchanged (2F-18E did not touch viewing authority); it did NOT
  previously distinguish FIRST-USE CLAIMING from viewing, which this
  slice now does — office viewing remains tenant-wide, office first-use
  CLAIMING is now uploader-gated for customer-linked threads.
- **2F-18D's `known-limitations.md`** did not flag `replace_asset`'s
  read-authority-equals-replace-authority conflation at all — this slice
  discovers and fixes it for the first time.
- **2F-18D's `atomic-claiming.md`** asserted atomicity properties
  (no-intermediate-commit, orphan-claim prevention) based on code
  structure alone, without a dedicated test — CORRECTED/STRENGTHENED:
  this slice adds `test_no_commit_before_claim_and_message_are_both_ready`
  and `test_commit_failure_propagates_not_swallowed` as direct proof.
- **2F-18D's retrieval-path lifecycle handling** was never audited for
  deleted/inactive `chat_attachment` assets at all (2F-18D's scope was
  first-use authority and atomicity, not lifecycle) — this slice performs
  that audit for the first time and closes the gap found.

## No prior slice's coverage arithmetic was found incorrect
200/226 (2F-18 through 2F-18D's figure) is CONFIRMED, not corrected, by
this slice's independent, route-by-route reconciliation
(`canonical-coverage-reconciliation.md`) — now with the cumulative
evidence of all six slices in this series.

## This slice's own approval-gate annotation convention
Per this initiative's established pattern, 2F-18D's `approval-gate.md` is
annotated below with a note pointing to this slice.
