# Selected Scope Hash Evidence - Slice 2F-28

| Set | File | Rows | Hash |
|---|---|---|---|
| A canonical implementation routes | selected-canonical-route-scope.csv | 12 | `012100a703047743` |
| B held adjudication routes (in-scope) | selected-held-adjudication-scope.csv | 0 in scope (2 recorded as NOT in scope) | `f1acd7b43c669b9e` |
| C out-of-scope adjacent routes | selected-out-of-scope-adjacent-routes.csv | 8 | `c77889cac83f07be` |

Set B contains **zero in-scope routes**: no held candidate sits on the
`app.engines.auth.router` boundary. The two nearest (`/v1/security/api-keys/*`)
are recorded in the file with `in_scope_for_M01 = NO` and the exact reason
(distinct model/table/router/service), so the emptiness is proven rather than
assumed.

The implementation slice may not add or omit a route without changing one of
these hashes.
