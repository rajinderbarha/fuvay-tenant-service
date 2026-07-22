# Post-N01 Queue Reconciliation (WS1)

## Proof of the 24-route reconciliation

- **Exactly 24 routes are unprotected**: `len(canon) - protected == 262 -
  238 == 24`, confirmed by direct count of the canonical CSV.
- **Every route has one canonical row**: the canonical CSV has 262 rows
  total, no duplicate `(method, path)` keys (checked programmatically).
- **Every route is mounted**: all 24 keys found in
  `authority_model_2f26e.py::route_index()` — zero missing.
- **Every route appears exactly once** in
  [authoritative-unprotected-route-inventory.csv](authoritative-unprotected-route-inventory.csv)
  — 24 rows, 24 unique keys.
- **No M01 route appears**: sample route `POST /v1/auth/api-keys`
  confirmed `VERIFIED` and absent from the 24-route set.
- **No N01 route appears**: sample route `POST /v1/media/upload`
  confirmed `VERIFIED` and absent from the 24-route set. All 5 N01
  residual routes and all 7 earlier-closed N01 routes checked absent.
- **No protected route appears**: the live queue inventory (`inv_keys`)
  was built directly from the canonical CSV's unprotected rows, so this is
  true by construction; re-verified by `verify_selection_2f32.py`
  condition W06 (`inv_keys & prot_keys == ∅`).
- **No held candidate is counted**: none of the 56 pending held route
  keys appear in either the protected or unprotected canonical sets
  (verified — see [held-candidate-arithmetic.md](held-candidate-arithmetic.md)).
- **238 + 24 = 262**: arithmetic identity, holds trivially and is
  re-checked by the verifier (W01/W02).

Full per-route detail (router, service, model, capability, permission,
tenant source, primary/secondary gaps, provenance): see
[authoritative-unprotected-route-inventory.csv](authoritative-unprotected-route-inventory.csv).
