# Deferred Workstreams — Round 2

Explicitly not attempted this round, per the brief's own instruction to
stop before these:

- Full status-transition certification (quote/checklist/parts/completion/
  commission/review) beyond Round 1's single `assigned -> accepted`
  transition.
- Full responsive/dark-mode/accessibility certification.
- UX-08 or any work beyond UX-07's scope.
- Backend remediation for the offering_type_id defect (ticket written,
  not implemented — `backend-remediation-ticket-offering-type.md`).

## Also not reached this round (time-budget, honestly disclosed)

- Full Playwright browser-driven test suite (installation not even
  attempted — `playwright-baseline.md`).
- New automated tests for the specific behaviors listed in the brief's
  Workstream 13 (role landing routes, forbidden-route access, session
  refresh, etc.) — verified via curl instead; see `targeted-test-report.md`.
- Visual evidence (screenshots) for any app's production screens —
  `visual-evidence-index.csv` still empty for the same reason as Round 1
  (no browser session run).
- `next build` for tenant-portal/super-admin (only typecheck+test run).
- Full field-by-field tenant onboarding trace (only the route/endpoint
  map + a live status/package-summary snapshot were done — see
  `tenant-onboarding-source-map.md`).
- Fixing the real React-version-pin mismatch in tenant-portal (diagnosed,
  not changed — see `frontend-corrections-report.md`).
- Wiring a `test` script + jsdom vitest config for `frontend/super-admin`.
- Testing tenant separation (a second real tenant's accounts) for the
  role-boundary checks — only one demo tenant's accounts were available.
- Full registration of a brand-new tenant end-to-end to properly test the
  real approval pipeline (the existing demo tenant bypassed it via seeding,
  so its own state couldn't answer this question — see
  `tenant-onboarding-live-verification.md`).

## Recommended Round 3 priorities

1. Fix the offering_type_id catalog-data inconsistency (backend-owned;
   ticket is ready).
2. Investigate the `500` vs `403` authorization defect on
   `/v1/provider/service-jobs/assignable` for customer-role tokens
   (backend-owned).
3. Install Playwright and run real browser-driven smoke flows for the
   Round 1 E2E proof's exact steps.
4. Register a genuinely new tenant end-to-end to properly test the real
   onboarding/approval pipeline.
5. Add the missing `frontend/super-admin` test script + jsdom config.
