# Known Limitations

- **Ownership was not inspected in the service layer for 6 of 11
  modules** (`admin_catalog_provider_setup`, `profile_technician_self_
  service`, `profile_universal_self_service`, `marketing_automation_
  provider`, `analytics_provider_reports`, `rag_query`,
  `enterprise_grid_preferences_exports`). Their risk scores explicitly say
  `UNKNOWN -- not inspected this slice` rather than inferring low risk
  from the route guard alone, per WS5. A future slice selecting any of
  these modules must perform its own direct service inspection before
  scoring.
- **`update_zone` (PUT /v1/geo/zones/{zone_id}) shares `delete_zone`'s
  exact defect but is neither canonical nor held** — flagged as a
  security observation in Set C, not actioned, since adding it to
  canonical coverage is out of this slice's scope.
- **This reconciliation is scoped to the 24-route canonical unprotected
  queue and the 59-route held registry only.** It does not re-audit any
  already-`VERIFIED` route, and does not re-open M01 or N01.
