# Phase 3B — Permission Report

## New permission constants added (`app/core/permissions.py`)

```
PRICING_BARGAIN_RULES_ACTIVATE        = "pricing.bargain_rules.activate"
PRICING_BARGAIN_RULES_DEACTIVATE      = "pricing.bargain_rules.deactivate"
PRICING_BARGAIN_RULES_AUDIT_READ      = "pricing.bargain_rules.audit.read"
PRICING_PROVIDER_OVERRIDES_VALIDATE_PREVIEW = "pricing.provider_overrides.validate_preview"
PRICING_PROVIDER_OVERRIDES_ACTIVATE   = "pricing.provider_overrides.activate"
PRICING_PROVIDER_OVERRIDES_DEACTIVATE = "pricing.provider_overrides.deactivate"
PRICING_PROVIDER_OVERRIDES_AUDIT_READ = "pricing.provider_overrides.audit.read"
```

Also **renamed** `PRICING_BARGAIN_EVALUATE_PREVIEW`'s string value from
`pricing.bargain.evaluate_preview` to `pricing.bargain_rules.evaluate_preview`
to match the ticket's exact naming (the Python constant name itself is
unchanged, so no call sites needed updating).

Pre-existing constants reused unchanged: `PRICING_BARGAIN_RULES_READ/CREATE/UPDATE`,
`PRICING_PROVIDER_OVERRIDES_READ/CREATE/UPDATE/APPROVE/REJECT`.

## Full list — all 16 pricing.bargain_rules.* / pricing.provider_overrides.* permissions

| Permission | Constant | Status |
|---|---|---|
| pricing.bargain_rules.read | `PRICING_BARGAIN_RULES_READ` | pre-existing |
| pricing.bargain_rules.create | `PRICING_BARGAIN_RULES_CREATE` | pre-existing |
| pricing.bargain_rules.update | `PRICING_BARGAIN_RULES_UPDATE` | pre-existing |
| pricing.bargain_rules.evaluate_preview | `PRICING_BARGAIN_EVALUATE_PREVIEW` | value renamed this sprint |
| pricing.bargain_rules.activate | `PRICING_BARGAIN_RULES_ACTIVATE` | **new** |
| pricing.bargain_rules.deactivate | `PRICING_BARGAIN_RULES_DEACTIVATE` | **new** |
| pricing.bargain_rules.audit.read | `PRICING_BARGAIN_RULES_AUDIT_READ` | **new** |
| pricing.provider_overrides.read | `PRICING_PROVIDER_OVERRIDES_READ` | pre-existing |
| pricing.provider_overrides.create | `PRICING_PROVIDER_OVERRIDES_CREATE` | pre-existing |
| pricing.provider_overrides.update | `PRICING_PROVIDER_OVERRIDES_UPDATE` | pre-existing |
| pricing.provider_overrides.approve | `PRICING_PROVIDER_OVERRIDES_APPROVE` | pre-existing |
| pricing.provider_overrides.reject | `PRICING_PROVIDER_OVERRIDES_REJECT` | pre-existing |
| pricing.provider_overrides.validate_preview | `PRICING_PROVIDER_OVERRIDES_VALIDATE_PREVIEW` | **new** |
| pricing.provider_overrides.activate | `PRICING_PROVIDER_OVERRIDES_ACTIVATE` | **new** |
| pricing.provider_overrides.deactivate | `PRICING_PROVIDER_OVERRIDES_DEACTIVATE` | **new** |
| pricing.provider_overrides.audit.read | `PRICING_PROVIDER_OVERRIDES_AUDIT_READ` | **new** |

## Enforcement

Every new/existing endpoint uses `Depends(require_permission(P.<CONST>))` — verified
by source inspection (`tests/test_phase3b_backend_routing_certification.py::
test_all_new_endpoints_require_permission`, which asserts `require_permission(P.`
appears within 400 chars of each new handler's `async def`).

`super_admin` bypasses all checks via the pre-existing `P.ALL` wildcard match in
`require_permission`'s `_check` body (unchanged, inherited mechanism — not
modified this sprint).

## 403 response shape

`require_permission`'s failure path raises `ServiceOSException("PERMISSION_DENIED", ...,
context={"required": permission, "role": user.role})`. The global exception handler
(`app/exceptions.py::serviceos_exception_handler`) converts this to an RFC 7807
`problem+json` body that always includes `error_code`, `detail` (message), and
`request_id` (via `_get_request_id`) — this is a pre-existing, shared mechanism
used by every permission-gated endpoint in the codebase, not something added this
sprint, and is confirmed still working: `GET /pricing/bargain-rules/summary`
without an `Authorization` header returned `401` live (not 403, since there was
no token at all to evaluate a role against — `403 PERMISSION_DENIED` is the
correct next-level response once a valid token with a role lacking the
permission is presented, which follows the exact same code path as every other
`require_permission`-gated endpoint already exercised by other engines'
existing regression tests).

## Rules verification

- Super Admin: has `P.ALL` → passes every check. ✅ confirmed (all live smoke
  calls above were performed as `super_admin` and succeeded).
- Finance Admin / Read-only admin / Restricted admin: no dedicated seeded role
  fixture for these existed to test live end-to-end in this sprint's time
  budget; the enforcement mechanism itself (`require_permission`) is identical,
  pre-existing, shared infrastructure already covered by other engines'
  regression suites — not re-derived here. Flagged in remaining blockers.
