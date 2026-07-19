# Known Limitations

1. **`npm install` could not be completed in this sandbox after ~35+ retry
   attempts spanning roughly an hour of wall-clock time.** Two distinct,
   compounding failures were observed on essentially every attempt:
   - `ERR_SSL_CIPHER_OPERATION_FAILED` /
     `Provider routines:ossl_gcm_stream_update:cipher operation failed`
     (`ciphercommon_gcm.c:325`) while streaming large package tarballs
     (`next`, `vitest`, `jsdom`, `@testing-library/*`) from
     `registry.npmjs.org` — an OpenSSL 3.x/Node GCM-cipher streaming bug,
     unrelated to this codebase, that corrupts big HTTPS response bodies
     partway through.
   - `EPERM`/`ENOTEMPTY` file-lock errors (`operation not permitted,
     unlink/rmdir ...`) while npm tried to clean up the partial extraction
     from the previous failed attempt — consistent with an active
     file-system scanner (antivirus/Defender) holding a lock on
     newly-written large `.js` files in `node_modules/next/dist/**` at the
     exact moment npm tries to delete/replace them. One file
     (`app-page-turbo-experimental.runtime.dev.js`) was observed locked
     even against a direct `rm`, confirming this isn't npm-internal.
   - Net effect: progress was real but non-monotonic — `next` fully
     installed for `tenant-portal` at one point, then got corrupted again
     on a later attempt when the SSL/lock failure hit mid-extraction on a
     shared/hoisted dependency. As of the last attempt, `node_modules/react`,
     `node_modules/vitest`, `node_modules/typescript`, and the
     `@serviceos/design-system` workspace symlinks were still missing at
     the point this was written up — `tsc`, `vitest run`, and `next build`
     could not be run for real. See `frontend-test-report.md` and
     `build-report.md` for the concrete "not run" status.
   - What was tried: plain retry (~15x), `--no-audit --no-fund`,
     `--prefer-offline`, `--network-concurrency=1`, `--fetch-retries`/
     `--fetch-retry-mintimeout` tuning, `npm cache clean --force` (itself
     failed with the same EPERM pattern), manually deleting the locked
     file/directory and retrying. None produced a clean, complete install.
   - If this recurs: this looks like an environment/sandbox issue (AV +
     Node OpenSSL interaction on Windows), not something fixable from the
     repo. Retrying outside this sandbox, or with real-time AV scanning
     exclusions for the repo's `node_modules`, would be the next thing to
     try.
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
