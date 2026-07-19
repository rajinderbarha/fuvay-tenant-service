# Prerequisite Bug Fix Report

Both fixes are from UX-04 baseline (commit `8cf630a`) and were **kept
as-is, not reverted or broadened**, per this phase's explicit instruction:

1. `frontend/packages/design-system/src/components/Tooltip.tsx` —
   `TooltipProps.children` narrowed from `React.ReactElement` to
   `React.ReactElement<{ "aria-describedby"?: string }>` so
   `React.cloneElement` type-checks. Verified still present, unchanged,
   this pass (`npx tsc --noEmit` clean).
2. `frontend/tenant-portal/app/dev/ux-03/permission-editor/page.tsx` —
   added the missing `"use client"` directive (was a Server Component
   passing a function prop into a Client Component). Verified still
   present, unchanged, this pass.

No new prerequisite bug fix was required this pass — `npx tsc --noEmit`
and `npx next build` both ran clean for `frontend/tenant-portal` without
needing any further source change beyond the new UX-04A feature code.
