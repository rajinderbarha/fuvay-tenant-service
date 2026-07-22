# Known Limitations

- **No dependency check on zone deletion** — `delete_zone` deactivates a
  zone regardless of whether active bookings/pricing reference it
  (pre-existing behavior, unchanged; see
  [product-decisions-required.md](product-decisions-required.md)).
- **No audit-log row emitted** for any of the 3 closed mutations
  (pre-existing gap).
- **No live two-tenant PostgreSQL integration test was executed** — WS13
  used deterministic static-inspection doubles instead; see
  [live-database-evidence.md](live-database-evidence.md).
- **`update_zone`/`get_zone` (Set C) share the same historical
  zero-tenant-predicate defect as `delete_zone` did** but remain
  untouched — explicitly frozen out of this slice's scope by the mission.
- **This closure is scoped to `geo_zone_management` only** — 23 canonical
  routes remain unprotected application-wide; this slice makes no claim
  about any of them.
