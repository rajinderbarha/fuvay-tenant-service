# Known Limitations

1. **`npm install` was severely network-flaky in this sandbox** — repeated
   `ERR_SSL_CIPHER_OPERATION_FAILED` errors against registry.npmjs.org
   (an OpenSSL/Node TLS issue unrelated to this codebase). Installs
   eventually succeeded via repeated retries; see `build-report.md` and
   `frontend-test-report.md` for what ran to completion. If this recurs for
   the next engineer, retrying `npm install --workspaces
   --include-workspace-root` a handful of times has reliably worked.
2. **Only a partial component test suite** — 6 test files covering tokens,
   theme persistence, Button, Modal focus-trap, StatusBadge fallback, and
   EmptyState. Input/Select/Textarea/Card/Drawer/Tooltip/Alert/Toast/
   Skeleton/DataTable/PageShell have no dedicated tests yet (see
   `component-showcase-inventory.csv` for the exact gap list).
3. **No automated contrast-ratio audit** — token pairs were reviewed by eye
   against WCAG AA, not run through an automated tool.
4. **The 12 "may-skip" detail-spec docs were not separately authored** —
   design-principles.md, design-debt-inventory.csv (folded into
   existing-ui-audit.md), navigation-presentation-contract.md,
   page-layout-components.md, interaction-component-inventory.csv,
   form-component-specification.md, enterprise-table-specification.md,
   dashboard-component-specification.md, identity-entity-components.md,
   system-state-library.md, sample-shell-screen-inventory.csv,
   artifact-manifest.csv. Their content lives inline across
   `design-token-specification.md`, `status-system.md`,
   `spacing-layout-system.md`, and `component-showcase-inventory.csv`.
5. **No RTL/i18n support** — see `localization-readiness.md`.
6. **Package is not built/published** — `@serviceos/design-system` is
   consumed as raw TS source via a tsconfig path alias + workspace symlink,
   not compiled to a `dist/`. Fine for two Next.js apps that already compile
   TS themselves; would need a build step if consumed outside a bundler
   context.
