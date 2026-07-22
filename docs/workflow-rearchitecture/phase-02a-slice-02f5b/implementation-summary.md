# Slice 2F-5B Implementation Summary

## Scope
Full verification and security/financial-integrity closure of
`app.engines.finance_hub.admin_router` (17 mounted mutation routes),
under the approved interim least-privilege persona policy, following on
from Slice 2F-5A's adjudication that this module (and
`package_commerce.admin_router`, untouched here) has no tenant persona.

## What changed
1. **`app/engines/finance_hub/service.py`** — `approve_deposit` gained a
   final-state guard (`status != "refunded"`), mirroring the pattern
   `refund_deposit` already used for itself. This closes the one
   conclusively-proven financial-integrity defect found this slice: an
   admin could previously "re-approve" an already-refunded security
   deposit, silently reversing money already returned to the tenant.
2. **`scripts/workflow_rearchitecture/inventory_mutation_routes.py`** —
   `CONFIRMED_PLATFORM_ADMIN_PERMISSION_ROUTES` extended with all 17
   finance_hub mutation endpoints (evidence-backed, not guessed),
   bringing `--verify-module` to 0 unverified for this module.
3. **`tests/test_phase2f5b_finance_hub_platform_authorization.py`** — new,
   182 tests: persona denial matrix, permission-bundle-gap regression
   guard, the new guard's behavior, and source-inspection confirmation
   that every pre-existing state-machine guard in the file remains intact.
4. **19 documentation files** in this directory (see
   `approval-gate.md` for the closure statement).

## What did not change
`package_commerce.admin_router`, tenant access-scope logic, any
permission grant, any role definition, any finance UI, `readonly@`,
migration 144, and all six previously-closed modules
(`tenant_engine.router`, `provider_portal.router`,
`execution.home_service_router`, `home_service_assignment.staff_router`,
`home_service_assignment.provider_router`, `tenant_engine.portal_router`).

## Outcome
Security posture: closed. Product-policy posture: intentionally open
(2 permission bundles remain super-admin-only pending a future product
decision — see `product-decisions-required.md`). See `approval-gate.md`
for the full status statement.
