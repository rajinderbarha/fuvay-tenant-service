# Changed File Report (UX-04B, since baseline f66741f)

`git diff --name-status f66741f..HEAD -- frontend/`:

```
A  frontend/tenant-portal/app/dev/ux-04/field-ops-job-detail/page.tsx
M  frontend/tenant-portal/app/dev/ux-04/page.tsx
M  frontend/tenant-portal/app/dev/ux-04/parts-approval/page.tsx
A  frontend/tenant-portal/app/dev/ux-04/parts-list/page.tsx
A  frontend/tenant-portal/browser-tests/keyboard-a11y.spec.ts
A  frontend/tenant-portal/browser-tests/smoke.spec.ts
A  frontend/tenant-portal/components/ux04/FieldOpsJobDetail.tsx
A  frontend/tenant-portal/components/ux04/PartsRequestList.tsx
A  frontend/tenant-portal/components/ux04/__tests__/FieldOpsJobDetail.test.tsx
A  frontend/tenant-portal/components/ux04/__tests__/PartsRequestList.test.tsx
A  frontend/tenant-portal/lib/ux04/__tests__/provenance.test.ts
M  frontend/tenant-portal/lib/ux04/fixtures.ts
M  frontend/tenant-portal/lib/ux04/types.ts
M  frontend/tenant-portal/package.json
A  frontend/tenant-portal/playwright.config.ts
M  frontend/tenant-portal/vitest.config.ts
```

16 files, entirely under `frontend/tenant-portal/`. Plus
`docs/design/ux-04b-runtime-certification/**` (new files, not listed
individually — see `artifact-manifest.csv`).

Exact tree-hash comparison (stronger than diff):

```
git rev-parse f66741f:frontend/super-admin  HEAD:frontend/super-admin   # 4b799cb3... == 4b799cb3...
git rev-parse f66741f:app                   HEAD:app                   # b500e493... == b500e493...
git rev-parse f66741f:mobile                HEAD:mobile                # 231ecafc... == 231ecafc...
git rev-parse f66741f:frontend/customer-app HEAD:frontend/customer-app # 24b4c03c... == 24b4c03c...
```
All four identical — zero changes outside `frontend/tenant-portal/` and
`docs/`.
