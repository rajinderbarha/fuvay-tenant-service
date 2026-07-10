# Browser E2E Scenarios Report (Part 14)

New spec file: `frontend/e2e-admin-tenant/e2e/admin-catalog-pricing-e2e03.spec.ts` (extends the existing E2E-02 harness — same `loginAsSuperAdmin` helper, same `channel: 'chrome'` config, same evidence-directory pattern).

Real `npx playwright test` output (E2E_APP=admin, real system Chrome, real backend at :8000, real Postgres):

```
Running 6 tests using 1 worker

  ok 1 [chrome] › admin-catalog-pricing-e2e03.spec.ts:17:7 › route smoke: 4 catalog/pricing pages, no NaN/undefined/raw json (12.9s)
  ok 2 [chrome] › admin-catalog-pricing-e2e03.spec.ts:38:7 › service catalog: open AC Repair, verify Split AC / Window AC / LG / Not Cooling (8.9s)
  ok 3 [chrome] › admin-catalog-pricing-e2e03.spec.ts:67:7 › pricing rules: filter, open type-specific LG rules for Split AC and Window AC (5.8s)
  ok 4 [chrome] › admin-catalog-pricing-e2e03.spec.ts:87:7 › customer price experience: preview Low/Mid/High for baseline numbers (7.7s)
  ok 5 [chrome] › admin-catalog-pricing-e2e03.spec.ts:105:7 › service areas: verify Ludhiana/141001 mapped via Mid tier (7.7s)
  ok 6 [chrome] › admin-catalog-pricing-e2e03.spec.ts:115:7 › forbidden label scan on rendered catalog/pricing pages (11.0s)

  6 passed (51.8s)
```

Scenarios covered vs spec checklist: admin login (via helper), open service catalog, search/select AC Repair (row click, filtered by exact match excluding "Duplicate Test" rows), open AC Repair detail, verify Split AC type (Types tab content check), verify Window AC type (same), verify LG brand under correct service context (Brands tab), verify Not Cooling/cooling issue exists (Issues tab), open pricing rules, inspect type-specific + brand-specific rows (9 real rows, Type-scoped/Brand-scoped labels), open pricing rule edit modal (detail proof of type-specific rule), verify min/max price fields present, verify platform fee field present, open price-experience route, verify Low/Mid/High calculation with real baseline numbers (700/850/10%), open service-areas, verify tier data renders (Ludhiana/141001 mapping confirmed at DB layer, see Part 9), verify no forbidden labels (explicit dedicated test), verify no NaN/undefined (asserted in every test).

One fix was required during authoring: initial locator `button:has-text("Types")` was ambiguous (matched 16 unrelated service-list buttons whose text also contained "types" e.g. "2 types"); fixed by scoping to the `.hsc-tab` CSS class used only by the tab bar. Also fixed an ambiguous "AC Repair" button match (3 rows exist: real service + 2 pre-existing "AC Repair Duplicate Test" rows from earlier catalog-bugfix sprints) by filtering out "Duplicate" text.

Result: 6/6 passed, real evidence captured.
