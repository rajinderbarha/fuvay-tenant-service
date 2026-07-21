# Known Limitations — Slice 2F-39A2

1. **149 mounted routes remain genuinely unclassified** (229 - 80), across
   roughly 28 remaining modules, smaller than the 4 covered this tranche.
2. **6 real, unresolved authorization findings** discovered this slice were
   not fixed, given genuine uncertainty about intended caller model:
   `record_activity`, `write_audit`, `create_session`, `revoke_session`
   (all in `security.router`, all bare-`get_current_user`, all with fully
   client-controlled tenant/entity/user identifiers and zero internal
   callers found anywhere in the codebase), and `activate_rule`/
   `deactivate_rule` (in `pricing.router`, same class of gap as the fixed
   `create_api_key` — `require_permission` instead of
   `require_tenant_mutation_permission`). See
   `authorization-remediation-report.md`.
3. **Two read-path privacy observations** (`run_preflight`,
   `replay_snapshot`) — read-only, no mutation, but accept/leak
   cross-tenant data with no ownership check. Consistent with this
   program's already-documented pricing/read-path limitation; not fixed
   (out of mutation-authorization scope).
4. **3 of the 3 api-key routes in `security.router` other than
   `create_api_key`** (`list_api_keys`, `get_api_key`) were not
   individually re-verified this slice beyond the guard grep — only
   `create_api_key` (the mutation) was fixed and tested.
5. **`verify_2f37.py`'s hardcoded 313/313** still does not reflect the
   true canonical count, now 313 (2F-37) + 8 (2F-39A) = 321 confirmed +
   this slice's field_ops/platform_commerce/pricing/security additions
   (not all of which were formally added to a "canonical inventory" file —
   this slice's classification work lives in `final-route-classification.csv`
   rather than being merged into a single master canonical CSV). See
   `deferred-items.md`.
6. Full backend regression run once, not twice, given its ~15-20 minute
   cost.
7. No dedicated `verify_2f39a2.py` was built.
