# Product Decisions Required

1. **Should `delete_zone` block deactivation of a zone with live/active
   dependent state** (e.g. active bookings, pricing overrides referencing
   it)? Currently no dependency check exists (soft delete only, no
   validation). See
   [geography-hierarchy-integrity-audit.csv](geography-hierarchy-integrity-audit.csv).
   Not changed this slice (existing behavior; WS8 required reporting this
   as a blocker rather than guessing a new policy).
2. **Should `ServiceZone` gain a uniqueness constraint** on
   `(tenant_id, zone_name)` or similar, to prevent duplicate active
   geography mappings? No such constraint exists today.
3. **Should mutation audit-log rows be emitted for `delete_zone`/
   `create_zone`/`update_staff_location`?** None of the 3 routes emits a
   dedicated audit-log entry today (pre-existing gap, not introduced or
   fixed this slice).
4. **Should `update_zone`/`get_zone` (Set C, explicitly frozen out of this
   slice) receive the same tenant-scoping fix in a future slice?** They
   share the identical pre-fix defect pattern as `delete_zone` but were
   out of this slice's authorized scope.
5. **Should the 2 held candidates that share the geo module boundary
   (`create_zone`'s sibling routes, if any remain, or any newly-discovered
   geo-adjacent held routes) be adjudicated together in a future slice?**
   Not applicable this slice — both Set B routes were fully adjudicated
   and closed.
