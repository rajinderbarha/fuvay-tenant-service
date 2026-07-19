# Changed File Report

`git diff --stat ddf7094..HEAD` (ddf7094 = UX-03 tip, the base of this
branch) shows **53 files changed, 1935 insertions(+), 0 deletions(-)**,
entirely under `frontend/tenant-portal/lib/ux04/`,
`frontend/tenant-portal/components/ux04/`,
`frontend/tenant-portal/app/dev/ux-04/`, and
`docs/design/ux-04-tenant-operations/`. No file outside those four
directories was modified. Verified via:

```
git diff --name-only ddf7094..HEAD -- frontend/super-admin frontend/customer-app mobile/   # 0 files
git diff --name-only ddf7094..HEAD -- app/                                                  # 0 files
```
