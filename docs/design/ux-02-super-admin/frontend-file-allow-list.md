# Frontend File Allow-List (UX-02)

Per hard constraint, this phase touches ONLY:
- `frontend/super-admin/**` (new files under `lib/ux02/`, `components/ux02/`, `app/dev/ux-02/`,
  `__tests__/ux02/`; minor edits to `components/layout/AdminLayout.tsx`,
  `app/admin/tenants/[id]/page.tsx`, `app/admin/users/page.tsx` — see `changed-file-report.md` for
  the exact diff nature of each).
- `docs/design/ux-02-super-admin/**` (this documentation set).
- `.gitignore` (one line added to ignore the generated `tsconfig.tsbuildinfo` artifact).

No file under `frontend/tenant-portal/`, `frontend/customer-app/`, `mobile/customer-app/`,
`mobile/staff-app/`, or `frontend/packages/design-system/` was modified by this phase — the
design-system package was read-only reference material; no compatibility fix was required (see
`ux01-source-compatibility-report.md`).

No file under `app/`, `tests/`, `scripts/`, or any migration was touched — see
`backend-non-change-report.md` for the verification.
