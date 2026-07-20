# Deferred Items — Slice 2E

## The one real remaining architectural gap
Extend mutation-guard coverage from 1 to 16 (+ the additional routers found outside the original 16, e.g. `auth/router.py`, `execution/home_service_router.py`) tenant-facing router files, with careful per-endpoint review. This is the single item that unblocks both the read-only persona and `readonly@`'s remediation.

## Smaller, scoped follow-ups
1. Extend `_build_token_pair`'s `StaffPermission` loading to `technician` and `tenant_owner` roles, if a future need arises to restrict either via overrides.
2. Add session-revocation to `update_permissions` for deny-direction changes (security-sensitive reductions), per this slice's honest disclosure in `session-and-token-revocation.md`.
3. Define the missing manager-persona permission constants (team-wide job/quote/customer visibility, finance, business-settings) if a real manager persona is ever needed.
4. Complete the service-layer bypass audit across the remaining ~137 engine service classes not spot-checked this slice.
5. Complete the per-endpoint mutation route inventory for the domains marked UNVERIFIED in `mutation-enforcement-matrix.csv`.
6. Consider whether "role and access_scope combinations that cannot be enforced" (the one integrity check not implemented) becomes meaningful once the guard-coverage gap closes.

## Not in scope for any future slice unless separately approved
Admin My Work, Tenant My Work, guided workflows, page consolidation, visual redesign, booking-pipeline work — none touched, consistent with every prior slice.

## Recommended next slice
Given this slice found the read-only persona's blocker is now precisely, countably scoped (15 named files), the highest-value next slice is a dedicated, systematic pass extending `require_tenant_mutation_permission` (or an equivalent guard) across those 15 files, one engine at a time, with its own test suite proving each engine's genuine mutations are now blocked for a read-only scope while legitimate tenant_owner/staff mutations remain unaffected. Only after that closes should `readonly@demo-ac-services.local`'s remediation and migration 144's application be reattempted.
