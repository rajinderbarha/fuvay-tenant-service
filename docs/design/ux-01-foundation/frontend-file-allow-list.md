# Frontend File Allow-List (files touched or created this pass)

All paths below are under `frontend/`, `docs/`, or the repo root — nothing
under `app/` (backend), no migrations, no permission/auth files were opened
or modified.

## Created
- `package.json` (repo root)
- `frontend/packages/design-system/**` (entire new package: `package.json`,
  `tsconfig.json`, `vitest.config.ts`, `src/tokens/*.ts`, `src/theme/
  ThemeProvider.tsx`, `src/theme.css`, `src/components/*.tsx`, `src/
  __tests__/*`, `src/index.ts`)
- `frontend/super-admin/app/dev/design-system/page.tsx`
- `frontend/super-admin/app/dev/sample-shell/page.tsx`
- `frontend/tenant-portal/app/dev/sample-shell/page.tsx`
- `docs/design/ux-01-foundation/**` (this directory)

## Modified
- `frontend/super-admin/tsconfig.json` (added path alias)
- `frontend/super-admin/package.json` (added dependency)
- `frontend/super-admin/app/layout.tsx` (added ThemeProvider wiring)
- `frontend/tenant-portal/tsconfig.json` (added baseUrl/paths)
- `frontend/tenant-portal/package.json` (added dependency)
- `frontend/tenant-portal/app/layout.tsx` (added ThemeProvider wiring)

## Explicitly not touched
- Anything under `app/` (Python/FastAPI backend), migrations, permission
  registries, auth files.
- Any existing business page/component in `super-admin` or `tenant-portal`
  beyond the two root `layout.tsx` files.
- `frontend/customer-app`, `mobile/customer-app`, `mobile/staff-app`.
