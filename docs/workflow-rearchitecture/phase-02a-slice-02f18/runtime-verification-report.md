# Runtime Verification Report

## Method
Ran the existing `scripts/workflow_rearchitecture/inventory_mutation_routes.py`
tool's `walk()` function in-process against the fully mounted FastAPI app
and filtered to `module == "app.engines.platform_notifications.provider_router"`.

## Result (live output, captured this slice)
All 10 selected mutation routes now report a `VERIFIED`-set `guard_status`:

```
POST /v1/provider/notifications/{notification_id}/read  -> TENANT_MUTATION_ROLE_SCOPE_AWARE
POST /v1/provider/notifications/mark-all-read            -> TENANT_MUTATION_ROLE_SCOPE_AWARE
PUT  /v1/provider/notifications/preferences               -> TENANT_MUTATION_ROLE_SCOPE_AWARE
POST /v1/provider/chat/threads                            -> TENANT_MUTATION_ROLE_SCOPE_AWARE
POST /v1/provider/chat/threads/{thread_id}/messages       -> TENANT_MUTATION_ROLE_SCOPE_AWARE
POST /v1/provider/chat/threads/{thread_id}/read           -> TENANT_MUTATION_ROLE_SCOPE_AWARE
POST /v1/staff/notifications/{notification_id}/read       -> STAFF_EXECUTION_ROLE_SCOPE_AWARE
POST /v1/staff/notifications/mark-all-read                -> STAFF_EXECUTION_ROLE_SCOPE_AWARE
POST /v1/staff/chat/threads/{thread_id}/messages          -> STAFF_EXECUTION_ROLE_SCOPE_AWARE
POST /v1/staff/chat/threads/{thread_id}/read              -> STAFF_EXECUTION_ROLE_SCOPE_AWARE
```

Both guard_status values are members of the established `VERIFIED` set
(`tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py`'s
`TestCanonicalCoverageRecount.VERIFIED`) — no new guard_status category was
invented.

## Exit-condition checks
- No selected route remains unclassified — all 10 resolved to a real,
  named dependency (`require_owner_or_office_staff_mutation` /
  `require_staff_or_technician_only`), confirmed by inspecting
  `dependency_names` directly from the live app, not from source-reading
  alone.
- No tenant mutation lacks mutation-scope enforcement — all 6
  `provider_*` mutations use `require_owner_or_office_staff_mutation`,
  which includes the readonly-access-scope check.
- No sender identity is client-controlled — confirmed in
  `sender-identity-authority.md`.
- No recipient can be selected without authority — confirmed in
  `recipient-authority.md`.
- No cross-tenant recipient is allowed — the only recipient-adjacent input
  (`record_id`) is now ownership-validated.
- Technician-route assignment enforcement — deliberately NOT tightened this
  slice (documented, `PRODUCT_DECISION_REQUIRED`, see
  `product-decisions-required.md`); this is the one exit condition this
  slice does not fully satisfy, which is why the final status is
  `SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED` rather than a fully closed
  status — see `approval-gate.md`.
- No conversation/message IDOR remains for the resolvable record types —
  proven by `TestChatThreadRecordOwnership`.
- No weaker same-record route remains — `customer_router.py` fixed
  alongside.
- Documentation/runtime consistency — `provider-router-final-route-inventory.csv`
  matches the live `walk()` output exactly (dependency names, paths,
  methods all cross-checked).

## Test-suite exit code
`pytest tests/test_phase2f18_platform_notifications_authorization.py` exits
0 (49/49 passing) — this suite functions as the deterministic verification
equivalent for this slice, following the same pattern used by
`test_phase2f17a_global_mutation_inventory.py` in the prior slice.
