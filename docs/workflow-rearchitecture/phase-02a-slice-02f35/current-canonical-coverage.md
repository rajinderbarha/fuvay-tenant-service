# Current Canonical Coverage

As of the end of Slice 2F-35:

- **Denominator:** 273 (264 + 9 Set B additions)
- **Protected:** 252 (241 + 2 Set A closures + 9 Set B closures)
- **Unprotected:** 21
- **Pending held:** 45 (54 − 9)
- **Canonical hash:** `58bbf1e1196688e7`
- **Matrix hash:** `4520e7f3ed2250ab`

This figure will move again as Slices 2F-36/37/38 close more routes; it
is not a claim that the whole application is secured — 21 canonical
routes remain unprotected, plus 45 pending held candidates not yet
adjudicated. Scoped to the 4 modules closed this slice
(`webhook_endpoint_management`, `rag_query`, `security`, `documents`):
all 11 in-scope routes are now closed on authorization/privacy grounds.
No new domain-integrity or product-policy blocker was found requiring a
different status for any of the 4 modules (see
[per-module-status-report.md](per-module-status-report.md)).
