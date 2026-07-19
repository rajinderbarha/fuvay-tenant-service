# Known Limitations

- Only 5 of the ~27 requested dev showcase routes were built (see
  `development-showcase-inventory.csv` for the full list of what's
  deferred and why).
- No automated test suite for UX-04 (`frontend-test-report.md`).
- No filter/preset controls on list views (data model supports them; UI
  controls not built).
- No operational search UI (`operational-search-specification.md`).
- Responsive table overflow not handled with a scroll wrapper
  (`responsive-operational-behavior.md`).
- No i18n/locale system — matches UX-03 baseline, not a new regression.
- Per-adapter-method contract documentation (route/shape/permission/error
  mapping/etc.) not written out — only TypeScript signatures exist
  (`frontend-adapter-contract.md`).
- `ServiceJob` status literal set not re-verified against the real backend
  model this pass (`job-list-specification.md`).
