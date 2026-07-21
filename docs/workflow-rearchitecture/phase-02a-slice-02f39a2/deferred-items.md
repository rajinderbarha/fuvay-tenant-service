# Deferred Items

- Classification of the remaining 149 routes across ~28 smaller modules —
  next tranche should continue by descending unresolved count.
- **Product/security decision required** for `record_activity`,
  `write_audit`, `create_session`, `revoke_session` (security.router):
  are these meant to be internal-service-only endpoints (need an
  internal-authority guard) or genuinely end-user-facing (need
  tenant/actor ownership checks)? No internal caller was found anywhere
  in this codebase, which argues against "internal-only by design," but
  this was not conclusively resolved.
- **Fix verification needed** for pricing's `activate_rule`/
  `deactivate_rule` before applying the same `require_tenant_mutation_permission`
  fix used for `create_api_key` — confirm this isn't a deliberate,
  documented exception before changing it.
- Merging this slice's + 2F-39A's classification work into one master
  canonical-mutation ledger, and updating `verify_2f37.py`'s hardcoded
  denominator accordingly.
- A dedicated `verify_2f39a2.py`.
- A second full-backend-regression run.
- All items already deferred by 2F-39/2F-39A (13 domain failures, 2
  frontend version-pin items, 2 TS-compile items) remain deferred,
  unchanged.
