# Known Limitations - Slice 2F-30

1. **Risk scores are hand-assigned 0-3**, not measured. They are now backed by
   a per-module `ownership_verified_in_service` evidence column, but they order
   the queue rather than express absolute severity.
2. **N01 is not the most dangerous module per route.** N09 (webhook,
   client-asserted tenant) and N10 (geo, no tenant predicate at all) are worse
   per route. N01 was selected for leverage and readiness; the trade-off is
   recorded in the selection decision, not hidden.
3. **Set B is non-empty (3 routes).** N01 cannot be claimed closed until they
   are adjudicated - unlike M01, which had an empty Set B.
4. The 59 held candidates remain unadjudicated overall.
5. Security observations remain static and unexecuted; none is a proven exploit.
6. This slice selects work only; no authorization correctness was proven beyond
   identifying the gap class and verifying which ownership checks already exist.
