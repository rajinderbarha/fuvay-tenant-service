# Documentation Corrections / Code Fixes Made This Phase

Two narrow, backward-compatible fixes were made outside the primary
`lib/ux04`/`components/ux04`/`app/dev/ux-04` scope, both found while
running the real WSL build verification (not applied speculatively):

1. `frontend/packages/design-system/src/components/Tooltip.tsx` —
   `TooltipProps.children` was typed as `React.ReactElement` (no generic),
   which `React.cloneElement(children, { "aria-describedby": id })`
   couldn't satisfy under the installed React/TS versions. Narrowed to
   `React.ReactElement<{ "aria-describedby"?: string }>`. Purely a type
   annotation change — no runtime behavior differs. This was blocking
   `next build`'s full-project type check for the entire tenant-portal
   app, not just UX-04.
2. `frontend/tenant-portal/app/dev/ux-03/permission-editor/page.tsx` — was
   a Server Component (no `"use client"`) passing a function prop
   (`onToggle`) into a Client Component, which Next.js 16 rejects at
   static-export time. Added the missing `"use client"` directive. This
   is a pre-existing UX-03 bug, unrelated to UX-04's own code, but it
   blocked `next build` from completing for the whole app.

Both are recorded here per the "backward-compatible evidence-based fixes
to frontend/packages/design-system" allowance, plus the tenant-portal fix
which is squarely in this phase's primary scope (`frontend/tenant-portal`)
and was required to get a real, non-fabricated build-success result.
