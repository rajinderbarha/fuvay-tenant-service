# FINAL-L5-03 — Test Infrastructure Standardization

## Current state (audited, not restructured this sprint)
Every FINAL-L5-* sprint's Playwright specs (including this sprint's `final-l5-03-cross-app-regression.spec.ts`) re-implement the same small set of helpers inline per spec file:
- `waitHydrated(page, selector)` — waits for a React fiber/props marker on a form input before interacting (established FINAL-L5-01E, to avoid the hydration-race false-flakiness root-caused in that sprint).
- Per-role login sequences (admin/tenant-owner/customer/technician), each a `goto → waitHydrated → fill → fill → click → waitForFunction(url change)` block.
- Canonical seed test credentials (`CanonicalL5!2026` for most seeded users, `admin@serviceos.local`/`Password123!` for the legacy-fixture admin account — both established across this whole engagement, re-used correctly this sprint after one initial diagnostic mistake with a wrong email domain).

## Real, acknowledged duplication
This exact `waitHydrated`/login-block pattern has now been copied into at least 6 different spec files across FINAL-L5-01E, FINAL-L5-02B, and this sprint. A shared `e2e/helpers/` module (one `login(page, role)` function, one `waitHydrated(page)` function) would eliminate this real duplication.

## Why not extracted this sprint
These specs are **ad-hoc evidence-generation scripts** for each sprint's certification, not a permanent, CI-run regression suite (confirmed: no `e2e/tenant-portal/*.spec.ts` file from a prior sprint is referenced by any CI config or `package.json` script found in this sprint's scan). Extracting a shared helper module now would require deciding on a permanent home/ownership for it and retrofitting every existing spec file to use it — a real, valuable investment, but one that only pays off once these scripts graduate into an actual maintained CI suite (out of this mission's Part 30 scope, which asks for representative real-browser verification, not permanent test-infrastructure engineering).

## Recommendation (not implemented)
Create `e2e/helpers/auth.ts` exporting `waitHydrated(page, selector?)` and `loginAs(page, role: "admin"|"tenant_owner"|"tenant_readonly"|"customer1"|"customer2"|"technician")`, and migrate future sprints' specs to import it — flagged in the Developer Architecture Guide.

## Other required helpers (mission's list) — status
- System Chrome launch: already the default for all specs run in this engagement (`chromium.launch()`).
- Canonical seed verification: performed via direct DB queries in FINAL-L5-02B, not a shared test helper function.
- API request helpers: `python -c "..."` inline scripts used ad-hoc per sprint, not a shared module.
- Screenshot/trace paths: Playwright's default `test-results/` — not customized per sprint into a documented convention.
- request_id assertions: performed ad-hoc (reading `meta.request_id` from live responses), not a shared assertion helper.
- Forbidden-label scan: implemented this sprint as an inline regex (`FORBIDDEN` const in the new spec file) — a real, reusable pattern worth extracting alongside the login helper.
- Mock-data scan: not a dedicated automated scan; this sprint's mock-data check was the manual `mock.ts`/`MOCK_MODE` investigation, not a repeatable script.

## Result
Real, honest gap identified and explained; not fixed this sprint given the scripts' current ad-hoc nature, but a concrete recommendation is recorded for when a permanent E2E suite is built.
