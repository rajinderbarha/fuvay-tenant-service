# Baseline Freeze (before any UX-04B edits)

- Starting commit: `f66741f` (UX-04A final).
- `git status` at session start: ~230 pre-existing uncommitted files
  under `app/`, `frontend/customer-app`, `mobile/customer-app`, plus a
  scattering under `frontend/tenant-portal` (e.g.
  `lib/api.persona.test.ts`, `app/staff/my-work/`) and new untracked docs
  folders (`docs/customer-app/`, `docs/workflow-rearchitecture/`) — all
  confirmed part of the parallel out-of-scope work noted in the original
  task brief, none touched by this phase.
- Dependency state: WSL scratch copy `/root/serviceos-ux04a` from UX-04A,
  `npm install --workspaces` previously verified working (196-200
  packages).
- `npx tsc --noEmit`: 0 errors (UX-04A had already fixed the earlier
  jest-dom typing gaps).
- 4 failing test node IDs, captured fresh this pass before any edit (see
  `initial-test-failure-inventory.csv` for the exact error message per
  test):
  - `components/ux03/__tests__/PermissionEditor.test.tsx > PermissionEditor > renders a distinct label for denied_override vs not_granted`
  - `components/ux03/__tests__/PermissionEditor.test.tsx > PermissionEditor > filters by search query across label/key/group`
  - `components/ux03/__tests__/SetupWizard.test.tsx > SetupWizard > shows progress and advances on goNext, calling onSaveDraft`
  - `components/ux03/__tests__/SetupWizard.test.tsx > SetupWizard > blocked steps are disabled in the step nav`
- Tenant build: succeeded (UX-04A's last verified state). Super-admin
  build: succeeded.
- Showcase route inventory at baseline: 15 UX-04/04A routes (see
  UX-04A's `final-showcase-inventory.csv`).
- Browser/a11y tooling at baseline: none — no Playwright, no axe-core, no
  browser test config existed anywhere in `frontend/tenant-portal` before
  this pass.
