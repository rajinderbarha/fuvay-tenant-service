# Final Status Rationale — Slice 2F-39A2R

## Selected token: `AUTHORIZATION_REMEDIATION_BLOCKED`

## This is a materially better state than 2F-39A2's, even though the token is unchanged

The token is the same because the mission's token set does not include a
"defects resolved, classification still incomplete" distinction — but the
underlying state changed substantially:

| | Slice 2F-39A2 (end state) | Slice 2F-39A2R (end state) |
|---|---|---|
| Confirmed unresolved authorization defects | 6 | **0** |
| Cumulative unresolved routes | 149 | 149 (unchanged — out of this slice's scope) |
| New findings surfaced | — | 1 (list_api_keys/get_api_key read-path gap, non-mutation) |

The trigger for `AUTHORIZATION_REMEDIATION_BLOCKED` this slice is now
**purely the classification-volume backlog (149 routes)** — the
"any confirmed mutation lacks a complete authorization boundary" and
"any newly discovered authorization issue remains unresolved" conditions
that made 2F-39A2's blocker qualitatively worse than 2F-39A's are both
now false.

## What this slice did, precisely

1. **Determined the intended caller model** for the 4 `security.router`
   findings by searching runtime callers (zero found for any of the 4),
   tests, documentation, and prior slice history — found 3 of the 4
   already documented as unremediated observations since Slice
   2F-26D/F/G/H, which explicitly named this as work for "a future slice
   to select, prove and close properly." This is that slice.
2. **Fixed all 4** with server-derived identity/tenant checks (not an
   internal-authority guard, since no internal caller model was
   supported by the evidence).
3. **Fixed `activate_rule`/`deactivate_rule`**, discovering the actual
   gap was worse than 2F-39A2's initial classification (zero tenant
   scoping at all, not merely a guard mismatch) — matched to the
   already-established `update_rule`/`delete_rule` pattern in the same
   file.
4. **Revalidated the full API-key sibling group** across both
   subsystems (`auth.router` and `security.router`), clarifying the
   review's supersession concern precisely: 2F-39A's "safe" conclusion
   and 2F-39A2's "broken" finding described two different, unrelated
   routes in two different files, not the same route reassessed
   differently. Both subsystems' siblings are now individually
   reconfirmed.
5. **Found and recorded (not fixed) one new read-path gap**
   (`list_api_keys`/`get_api_key`), consistent with this program's
   standing practice of surfacing what's found even when it's out of
   the current slice's remediation scope.
6. **Fixed the one test whose assertion enshrined the pre-fix, insecure
   design** (`test_revoke_session_deletes_redis_first`), preserving its
   real intent (immediacy for the destructive write) while updating what
   the security fix necessarily changed (a read-only ownership check now
   precedes the Redis delete).

## Evidence

- Phase-2F regression: 2494/2494 passed, twice, identical (2481 baseline
  + 13 new tests).
- 13 new tests, each proving a specific rejection/acceptance case, not a
  single generic assertion.
- Full backend regression: see `full-backend-regression-diff.md`.

## Path forward

Slice 2F-39A3 may now resume the remaining 149-route census, per the
review's own stated order ("only after these six defects are closed
should Slice 2F-39A3 resume").

This slice stops at its own approval gate. Demo-role migration, Migration
144 execution, and further route classification are not started.
