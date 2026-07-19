# Regression Report

- **Backend**: tree hash identical to baseline (`backend-non-change-report.md`).
- **Super Admin**: tree hash identical to baseline AND independently
  rebuilt successfully (`super-admin-non-regression-report.md`,
  `super-admin-build-report.md`).
- **Mobile/customer-app**: tree hash identical to baseline
  (`mobile-customer-non-change-report.md`).
- **UX-04 baseline's own 5 routes + 10 components**: none removed,
  renamed, or behaviorally altered — only Job Detail Workspace gained new
  sections (invoice/payment) additively; verified by diff (`git diff
  6dbd8ce..HEAD -- frontend/tenant-portal/app/dev/ux-04/job-detail
  frontend/tenant-portal/components/ux04`) showing only additive hunks to
  `job-detail/page.tsx` and zero changes to the 10 baseline component
  files.
- **UX-04 baseline's 2 documented fixes**: unchanged (confirmed by
  inspection, not reverted or broadened).
- **Test suite**: 35/35 new UX-04A tests pass; the only failures are 2
  pre-existing UX-03 test files that could not run at all before this
  pass (no regression — a newly-surfaced pre-existing issue, not a
  newly-caused one).
