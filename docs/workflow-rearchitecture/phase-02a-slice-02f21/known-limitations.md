# Known Limitations — Slice 2F-21

1. **Frontend/mobile caller audit deferred.** Per this initiative's
   established `FRONTEND_CALLER_AUDIT_DEFERRED` convention (see 2F-20's
   `frontend-mobile-caller-audit.md`), this slice did not investigate
   frontend or mobile callers of any of the 20 remaining routes or the
   selected module. Deferred to Slice 2F-22 for the selected module;
   deferred to each respective future slice for the other 8 modules.

2. **`mutation-enforcement-matrix.csv` not updated.** This legacy
   per-domain summary matrix is stale (last substantively updated at
   2F-9-era scope, its own TOTAL row still reads a pre-17A 182-route
   figure) and, per the same convention already established in 2F-19's
   and 2F-20's own reconciliation docs, was not force-updated to the
   226/206 figure this slice either — `tenant-mutation-endpoint-inventory.csv`
   remains the single authoritative denominator.

3. **Application-wide full mutation sweep not re-run.** This slice's
   runtime verification scope was the 20 remaining rows from the 2F-19/2F-20
   queue (the mission's own explicit starting point), not a fresh
   full-application sweep for entirely new tenant-prefixed mutation routes
   application-wide (that sweep was last performed exhaustively in 2F-17A
   and is not repeated every slice per this initiative's established
   cadence).

4. **`package_commerce.tenant_router`'s 4 GET read routes** were confirmed
   non-mutating by reading their handler bodies, but were not subjected to
   the full same rigor as the 1 selected mutation route (out of this
   slice's scope; flagged for the implementation slice's own audit per
   `selected-next-module.md`).

5. **Service-layer second-entry-point audit deferred.** Whether
   `PackageCommerceService.create_package_assignment` (or any of the other
   8 modules' underlying service methods) has a second, unguarded call
   site outside its router was not exhaustively verified this slice —
   deferred to each module's implementation slice.
