# FINAL-L5-04 — Browser Evidence Report

## Evidence source
All evidence below comes from real Chromium browser sessions (Playwright, no mocking) or manual verification against the live dev servers (`localhost:3000` super-admin, `localhost:3001` tenant-portal, `localhost:8000` backend) during this sprint. Machine-readable summary in `docs/final-l5-04/browser-e2e-results.json`.

## Evidence log
1. **Live vertical sidebar refresh** — logged in as `admin@serviceos.local`, navigated to `/admin/verticals`, clicked "Enable" on the Beauty & Wellness card, observed the sidebar's Catalog section grow a new "Beauty & Wellness" entry with zero page reload; clicked "Disable" and observed it disappear live; original disabled state restored at test end. Console evidence: `SIDEBAR_SHOWS_BEAUTY_AFTER_ENABLE_LIVE: true`, `SIDEBAR_HIDES_BEAUTY_AFTER_DISABLE_LIVE: true`.
2. **Direct route to disabled vertical** — direct-navigated to `/admin/catalog/beauty` while Beauty was disabled; page rendered the admin config page (not blank, not 500, not full unguarded content) — body snippet captured and reviewed, confirms genuine "Disabled" state.
3. **Breadcrumb — super-admin** — navigated to `/admin/categories`, breadcrumb rendered `"Catalog / Categories"`, 1 `<nav aria-label="Breadcrumb">` element present in DOM.
4. **Breadcrumb — tenant-portal, 2-crumb page** — logged in as `owner@demo-ac-services.local`, navigated to `/service-jobs`, breadcrumb rendered `"Jobs / Service Jobs"`.
5. **Breadcrumb — tenant-portal, 1-crumb page (intentional suppression)** — navigated to `/jobs`, 0 breadcrumb nav elements rendered, confirmed by source read to be correct/intentional (`resolved.length <= 1` guard), not a defect.
6. **Active-state highlighting** — `/admin/verticals` correctly highlighted the "Verticals" sidebar item.
7. **Production builds** — both `frontend/super-admin` and `frontend/tenant-portal` built successfully (`npm run build`) after all code changes, full route list compiled with no errors (see Static Build Report for the real command output).
8. **TypeScript** — `npx tsc --noEmit` returned 0 errors in both apps after all changes.
9. **Backend test suite** — `pytest -k "rbac or permission or vertical_catalog or category_runtime"` → 210 passed, 1 pre-existing unrelated failure (see Backend Visibility Test Report).

## Result
9 independent pieces of real evidence collected this sprint, each tied to a specific claim made elsewhere in this report set — no evidence item in this log is asserted without a corresponding real command/browser session behind it.
