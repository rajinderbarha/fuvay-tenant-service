# Runtime Verification Report

## Route-level (unchanged, re-run this slice)
All 10 selected routes still report a `VERIFIED`-set `guard_status`,
confirmed via live `inventory_mutation_routes.walk()` output identical to
every prior slice in this series.

## Object/attachment/office-first-use/replacement/lifecycle-level (this slice's new deterministic checks)
`tests/test_phase2f18e_platform_notifications_office_sharing_and_lifecycle.py`
— 18/18 passing:
- Office first-use ambiguity (4 tests): staff denied without uploader
  match into a customer-linked thread, staff allowed with uploader match,
  staff allowed into a provider-internal thread, tenant_owner subject to
  the identical rule as staff.
- `replace_asset` authorization (7 tests): uploader allowed, mutation-scoped
  staff allowed, read-only staff denied, non-uploader customer denied,
  non-uploader technician denied, foreign-tenant staff denied, super_admin
  allowed.
- Retrieval lifecycle (4 tests): deleted denied, quarantined denied,
  active passes, non-chat_attachment context unaffected.
- Transaction boundary (2 tests): no commit before claim+message ready,
  commit failure propagates.
- No partial state (1 test): ambiguous office share persists nothing.

## Exit-condition checks (per this slice's Workstream 12)
- Office first-use relying only on tenant/customer equality for an
  ambiguous external audience — **fixed**: uploader-match now required
  for any customer-linked destination.
- Recipient compatibility unverified — addressed via the retrieval-time
  design (2F-18C) plus this slice's sender-side destination-authority fix
  (`attachment-recipient-compatibility.md`).
- Thread read authority authorizing asset replacement — **fixed**:
  `_assert_chat_attachment_replace_authority` is structurally independent
  of thread membership.
- Claim and message not transactionally atomic — confirmed FALSE (already
  atomic since 2F-18D's `FOR UPDATE`; this slice adds the missing proof).
- Failed message persistence leaving an orphan claim — confirmed FALSE
  (two-pass claim-application design, 2F-18C, plus this slice's
  commit-failure-propagates proof).
- Delivery occurring before successful validation/transaction — confirmed
  FALSE (unchanged, re-traced this slice).
- Deleted or inactive chat assets remaining retrievable — **fixed**: new
  `_assert_chat_attachment_lifecycle` check.
- A blocked route marked fully protected — none;
  `final-selected-route-protection.csv` shows all 10 routes individually
  re-verified.
- Documentation disagreeing with runtime — cross-checked; the CSV/docs
  match the actual implementation.

## Test-suite exit code
`pytest tests/test_phase2f18e_platform_notifications_office_sharing_and_lifecycle.py`
exits 0 (18/18). Combined with 2F-18's 49, 2F-18A's 26, 2F-18B's 9,
2F-18C's 11, and 2F-18D's 12, this module now has 125 deterministic tests
across the six slices.
