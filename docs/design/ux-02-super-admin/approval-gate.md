# Approval Gate

This phase (UX-02) is **not** ready for a production nav cutover or backend-integration work
without the following approvals/prerequisites:

- [ ] Product sign-off on `product-decisions-required.md` (7 open decisions).
- [ ] `npm install` succeeds on a real build machine (unblocks typecheck/test/build — see
      `environment-blocker-report.md`).
- [ ] `tsc --noEmit`, `vitest run`, and `next build` all pass (see `build-command-manifest.md`).
- [ ] Backend contract confirmation for each `API_CONTRACT_REQUIRED`/`SECURITY_CONTRACT_PENDING`
      item in `backend-contract-dependencies.md`.
- [ ] Automated a11y pass (axe) and a manual keyboard/screen-reader pass, superseding the static
      review in `super-admin-accessibility-report.md`.

Until these are checked off, all UX-02 output should be treated as source-level design foundation
only — reviewable, but not deployable, and not a substitute for the backend's own authorization
enforcement or data contracts.
