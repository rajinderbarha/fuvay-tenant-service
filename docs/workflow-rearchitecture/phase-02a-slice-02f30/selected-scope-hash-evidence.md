# Selected Scope Hash Evidence - Slice 2F-30

| Set | File | Rows | Hash |
|---|---|---|---|
| A canonical implementation routes | selected-canonical-route-scope.csv | 9 | `3a5124b153345df5` |
| B held adjudication routes | selected-held-adjudication-scope.csv | 3 | `62de4c311dde3043` |
| C out-of-scope adjacent routes | selected-out-of-scope-adjacent-routes.csv | 7 | `6d53d0647cdee7ec` |

Set B is **non-empty** for this module: three held candidates sit on the same
MediaService boundary and are mandatory before closure. They are **not**
canonical and must not be counted until adjudicated with full evidence.

No implementation slice may add or omit a route without changing a hash.
