# Known Limitations

- No install/build/test has ever been executed for UX-02 source (MODE B throughout). All
  correctness claims are from manual source review only.
- Fixture data stands in for every list/detail view; no real API integration exists yet anywhere
  in `app/dev/ux-02/**`.
- Bulk actions, saved views, and the command palette are UI-only affordances with no backend
  mutation or persistence.
- Verification/compliance document previews are placeholder labels, not a real secure-preview
  mechanism (by design, per the hard constraint against raw storage keys/URLs — but also not a
  working preview of any kind yet).
- Platform Configuration has no real write path, no real change-history data source.
- Accessibility and localization reviews are static/source-level only — no automated tooling or
  manual assistive-technology pass was performed.
- `UX02_NAV_GROUPS` is not wired into production navigation; only the pre-existing
  `ADMIN_NAV_GROUPS` renders in the live app today.
- Test files exist but have never been run; `frontend/super-admin/package.json` lacks a test
  script/vitest dependency to run them at all right now.
