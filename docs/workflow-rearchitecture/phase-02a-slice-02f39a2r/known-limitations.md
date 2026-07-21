# Known Limitations — Slice 2F-39A2R

1. **149 mounted routes remain genuinely unclassified** — unchanged by
   this slice (remediation-only scope, per the review's explicit
   instruction to resolve defects before continuing the census).
2. **New finding this slice: `list_api_keys`/`get_api_key` read-path
   cross-tenant gap** in `security.router` — client-supplied `tenant_id`
   with no cross-check against the caller's own tenant, letting an
   authenticated caller list or view another tenant's API key metadata
   (names, prefixes, scopes — not the raw key, which is never
   retrievable after creation regardless). Read-only, not a mutation
   defect; consistent with this program's standing pricing/read-path
   limitation. Not fixed this slice.
3. `create_session`'s fix (actor-identity match) was not independently
   documented in the Slice 2F-26 observation corpus the way the other 3
   security.router findings were — treated the same way on the strength
   of its structural identity (bare auth, client-controlled identifiers,
   zero internal callers), not an explicit prior finding.
4. No dedicated `verify_2f39a2r.py` was built.
5. Full backend regression run once, not twice, given its ~15-20 minute cost.
