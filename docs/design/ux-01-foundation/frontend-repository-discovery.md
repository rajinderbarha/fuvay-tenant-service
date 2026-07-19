# Frontend Repository Discovery

- `frontend/super-admin/` — Next.js 16.2.9 + React 19.2.0, App Router, plain
  CSS with custom properties (`styles/globals.css`, `data-theme="light"/
  "dark"` already present), lucide-react icons, recharts, components in
  `components/{analytics,enterprise,layout,pricing,shared,tour}`, permission
  helpers at `hooks/usePermissions.ts` + `components/shared/
  PermissionGate.tsx` + `lib/permission-catalog.ts`, nav config at
  `lib/nav-config.ts`.
- `frontend/tenant-portal/` — same stack; `styles/globals.css`, `lib/
  nav-config.ts`, `components/{analytics,dashboard,enterprise,layout,media,
  shared,status,tour}`.
- Neither app had Tailwind, Storybook, or tests before this pass.
- No shared package existed — both apps fully duplicated their CSS token
  sets and had no cross-app component reuse.
- No root `package.json` / npm workspaces existed before this pass.
- Out of scope for this phase (noted, not built): `frontend/customer-app`
  (web), `mobile/customer-app` and `mobile/staff-app` (Expo).
