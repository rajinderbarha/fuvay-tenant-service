# Deferred Items

- Dedicated multi-service setup wizard showcase (distinct from the generic
  first-time SetupWizard demo).
- Dedicated Quote + Checklist showcase route (currently embedded as a Job
  Detail section only).
- Dark-mode / tablet / mobile dedicated showcase route variants (the
  design-system's ThemeProvider and responsive CSS are inherited, but no
  separate showcase route forces each state).
- Remaining test cases listed in frontend-test-plan.md's "still to write"
  section (dashboard state-switching, pricing validation, media-secret
  redaction, light/dark + keyboard + long-text tests for shared patterns).
- Wiring `UX03_NAV_GROUPS` into the production sidebar/layout.
- Consolidating the duplicate routes identified in
  tenant-route-duplication-map.csv into single canonical pages.
- A deeper, per-file manual audit of all 84 existing tenant-portal routes
  (this phase's audit is a naming/config cross-reference — see
  known-limitations.md item 4).
