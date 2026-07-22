# Behavioral Invariant Report - Slice 2F-29

- Closed-module canaries pass (field_ops review-request, Package Commerce,
  customer_reviews IDOR, legacy review parent + 410, compliance).
- StaffPermission grant / explicit-deny / cross-tenant isolation /
  unknown-role fail-closed all re-asserted.
- Canonical roles only; no alias introduced.
- One pre-existing behavioural test was updated deliberately:
  `test_cross_tenant_target_still_rejected` asserted the OLD oracle
  (`PERMISSION_DENIED`). The cross-tenant rejection itself is unchanged; only
  the error code moved to `NOT_FOUND`. The test was strengthened to also assert
  the message no longer reveals tenant membership.
