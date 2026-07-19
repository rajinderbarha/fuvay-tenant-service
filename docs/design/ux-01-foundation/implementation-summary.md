# UX-01 Foundation — Implementation Summary

Built a shared design-system foundation for the two web apps in scope:
`frontend/super-admin` and `frontend/tenant-portal`.

## What was built
- Root npm workspaces (`package.json`) wiring `frontend/packages/*`,
  `frontend/super-admin`, `frontend/tenant-portal`.
- `@serviceos/design-system` package: color/typography/spacing/motion tokens
  (TS + `theme.css` CSS vars, additive to each app's existing `globals.css`
  `[data-theme]` convention), a `ThemeProvider`/`useTheme` hook (light/dark/
  system, localStorage-persisted, pre-paint script to avoid flash-of-wrong-
  theme), and 12 core components (Button, StatusBadge, Input/Textarea/Select,
  Card, Modal, Drawer, Tooltip, Alert/Toast, Skeleton/Spinner, EmptyState/
  ErrorState/PermissionDeniedState, PageShell/PageHeader/Section, DataTable).
- Both apps' root layouts wired to `ThemeProvider` + `theme.css`, with
  `tsconfig.json` path aliases and `package.json` deps pointing at the
  workspace package.
- Dev-only showcase route (`super-admin` `/dev/design-system`) exercising all
  components in both themes with realistic ServiceOS fixture data.
- One sample shell screen per app (`/dev/sample-shell`) demonstrating
  shell+nav+header+status+table.
- Vitest + Testing Library suite (6 files) covering tokens, theme
  persistence, Button variants, Modal focus trap, StatusBadge fallback,
  EmptyState.
- 22 documentation files under `docs/design/ux-01-foundation/`.

## What was intentionally deferred
customer-app (web + mobile), staff-app (mobile), i18n, full nav population,
and the 12 "may-skip" detail-spec docs (content folded into the specs kept).
See `deferred-items.md`.

## Final status
**DESIGN_FOUNDATION_PARTIAL** — see `approval-gate.md` for the honest
breakdown of what is proven vs. best-effort.
