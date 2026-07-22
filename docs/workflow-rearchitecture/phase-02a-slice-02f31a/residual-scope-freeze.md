# Residual Scope Freeze (WS0)

Authoritative starting position, confirmed directly against the live
canonical CSV before any edit in this slice:

- Protected: 233
- Denominator: 262
- Unprotected: 29
- Canonical hash: `af8388463ac3dbfa`
- Matrix hash: `3066e137e9a23c19`

Exactly 5 canonical unprotected routes in N01 scope:

| # | Method | Path | Source |
|---|---|---|---|
| 1 | POST | `/v1/media/upload` | Known from 2F-31's `NOT_CLOSED_A` set |
| 2 | POST | `/v1/media/{media_id}/replace` | Known from 2F-31's `NOT_CLOSED_A` set |
| 3 | POST | `/v1/media/upload/initiate` | Loaded from 2F-31's `ADDED_B` (Set B) |
| 4 | POST | `/v1/media/upload/{session_id}/confirm` | Loaded from 2F-31's `ADDED_B` (Set B) |
| 5 | DELETE | `/v1/media/tenants/{tenant_id}/files/{file_id}` | Loaded from 2F-31's `ADDED_B` (Set B) |

Routes 3–5 were not invented; they are the exact 3-route `ADDED_B` set
already present in `scripts/workflow_rearchitecture/verify_n01_2f31.py`
(and canonical, with `guard_status` not yet `VERIFIED` prior to this slice).

No other N01 route was in scope. No route outside this set of 5 was
modified in this slice.
