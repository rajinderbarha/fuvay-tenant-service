# Slice 2F-27A Approval Gate

## Final status: EXPLICIT_TWO_ROUTE_CANONICAL_EXPANSION_COMPLETE

The user explicitly authorized Path 2. Both routes were reconfirmed against
mounted runtime evidence and added exactly once to the canonical inventory and
the enforcement matrix, classified UNPROTECTED. No other candidate applied.

## Coverage

| Metric | Before | After |
|---|---|---|
| Protected | 214 | 214 |
| Denominator | 257 | 259 |
| Unprotected | 43 | 45 |
| Canonical hash | 45244cd9540456db | e7a89231207221aa |
| Matrix hash | 4c7c3bce02096a43 | ee6011f6ce6a97ab |

## Gate checklist

- Both routes reconfirmed (mounted, genuine mutation, tenant/provider,
  require_permission(TENANT_UPDATE), canonical+matrix absent, no duplicate/alias): MET
- Exactly two canonical rows added: MET
- Exactly two matrix module rows added: MET
- Coverage 214/259, unprotected 45: MET
- Neither FULLY_PROTECTED: MET (both PERMISSION_ONLY_NOT_SCOPE_AWARE)
- No unauthorized candidate applied: MET (59 held)
- Recount assertions updated (current) / historical docs preserved: MET
- Full suite green: MET (2136 passed)
- No app/role/permission/migration change; no merge; closures intact;
  PartsRequest ServiceJob-only; readonly@ untouched; 144 unapplied; 2D canaries
  untouched; no frontend: MET

## Honest notes

- Held count is 59, not the mission's "57" (the 2 authorized routes were never
  among the 59). See documentation-corrections.md.
- The two added routes are UNPROTECTED - this slice records them; it does not
  remediate their authorization.
- Rebaselining updated 23 current assertions across the live suite to
  259/45/new-hash; the historical slice docs (e.g. 2F-26H, 2F-27) retain their
  point-in-time values, asserted by TestHistoricalDocsPreserved.

Stopping at the Slice 2F-27A approval gate. No implementation module selected.
