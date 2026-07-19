# Deferred Items

Explicitly out of scope for this pass, per the agreed UX-01 scope decision:

- **`frontend/customer-app` (web)** — no design-system wiring, no shell.
- **`mobile/customer-app` (Expo)** — mobile shells not built.
- **`mobile/staff-app` (Expo)** — mobile shells not built.
- **i18n / localization** — no library integrated; see
  `localization-readiness.md`.
- **Full nav population** — `lib/nav-config.ts` in either app was not
  edited; the two `/dev/sample-shell` pages are standalone illustrations,
  not linked into real navigation.
- **Workstream items 8–21 (remaining detail-spec docs)** — see
  `known-limitations.md` item 4 for the full list and where their content
  now lives instead.
- **Big-bang migration of existing pages** onto the new components — this
  phase ships the foundation only; adoption happens incrementally as other
  work touches those pages (see `existing-ui-audit.md` recommendation).
- **Automated axe/contrast tooling** and **screen-reader manual pass** —
  see `accessibility-report.md`.
