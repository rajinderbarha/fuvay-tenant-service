# Baseline Verification

Baseline: commit `6dbd8ce` on `design/ux-04-tenant-operations`
(`TENANT_OPERATIONS_DESIGN_PARTIAL`). Verified this pass, fresh, in a new
WSL copy (`/root/serviceos-ux04a`, previous `/root/serviceos-ux04` copy
was lost when the host/WSL restarted mid-session, as expected):

- `npm install --workspaces` — succeeded, "added 196 packages" (consistent
  with the baseline's own reported result).
- The 5 baseline showcase routes (`command-center`, `booking-list`,
  `job-detail`, `assignment-workspace`, `parts-approval`) all still exist
  unmodified in structure (job-detail gained new sections this pass, see
  `implementation-summary.md`) and all still build.
- Baseline's 2 documented fixes (Tooltip typing, `permission-editor`
  `"use client"`) are present in the tree and were NOT reverted or
  broadened — confirmed by inspecting both files before making any new
  change.
