# Build Report — MODE A, real evidence

Environment: WSL2 Debian, native Linux filesystem copy at
`/root/serviceos-ux04`, synced from the real git branch
`design/ux-04-tenant-operations` at commit `8cf630a` at verification time.

## npm install

```
added 196 packages in 5m
```
Zero errors, run twice (once before the host restart mid-session, once
fresh after WSL was restarted — both succeeded identically).

## npx tsc --noEmit (frontend/tenant-portal)

5 pre-existing errors remained BEFORE this phase's two fixes (Tooltip
`cloneElement` typing in design-system; a `.test.tsx` jest-dom matcher
typing gap in two UX-03 test files) — **zero of those 5 were in any UX-04
file**. After fixing the Tooltip typing (see
`frontend/packages/design-system/src/components/Tooltip.tsx`), that error
is gone; the remaining 4 are test-only jest-dom typing issues in
pre-existing UX-03 test files (`components/ux03/__tests__/
PermissionEditor.test.tsx`, `SetupWizard.test.tsx`), not fixed this pass
(different root cause — missing `@testing-library/jest-dom` type
augmentation in the tsconfig, out of scope for this bug-fix pass) and not
in any file this phase authored.

## npx next build (frontend/tenant-portal)

**Succeeded.** `✓ Compiled successfully in 72s`, `Finished TypeScript in
110s`, all ~130 routes statically prerendered including all 5 new
`/dev/ux-04/*` routes and the `/dev/ux-04` index. One pre-existing UX-03
build blocker was found and fixed along the way: `/dev/ux-03/
permission-editor/page.tsx` was a Server Component passing an
`onToggle` function prop into a Client Component — added the missing
`"use client"` directive (one line). Both fixes are narrow,
backward-compatible, and documented in `documentation-corrections.md`.

Full literal output tail is reproduced in this session's tool output for
the final `next build` run; route list confirms `/dev/ux-04/{,
assignment-workspace, booking-list, command-center, job-detail,
parts-approval}` all present and statically generated (`○` marker).
