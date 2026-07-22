# Product Decisions Required

1. **Should `PUT /v1/me/profile` require any role/permission check?**
   Currently `AUTHENTICATED_ONLY_NO_PERMISSION_CHECK` by apparent design
   (universal self-service). Flagged in
   [implementation-module-boundaries.csv](implementation-module-boundaries.csv)
   (`profile_universal_self_service`) — not adjudicated this slice.
2. **Should `enterprise_grid_preferences_exports` (column preferences +
   bulk export) be prioritized ahead of its current position** given
   `create_export`'s unaudited bulk-data-export privacy/compliance
   exposure? This slice could not score it definitively because
   `ColumnPreferenceService`/`ExportService` were not read (WS5's
   no-inference rule).
3. **Should `create_zone`/`update_location` (the 2 geo-module held
   candidates) be adjudicated in the same future slice that closes
   `delete_zone`**, given they share the exact same `GeoService`
   boundary? This slice explicitly declines to make that call — see
   [held-route-adjudication-contract.md](held-route-adjudication-contract.md).
4. **Should the N01 domain-integrity backlog
   ([n01-domain-integrity-backlog.csv](n01-domain-integrity-backlog.csv))
   be scheduled as its own slice**, independent of the next
   authorization-hardening module? It was explicitly kept separate this
   slice per WS7's instruction.
