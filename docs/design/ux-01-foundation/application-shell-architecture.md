# Application Shell Architecture

## Provider wiring
Both apps' root `app/layout.tsx`:
1. Imports the app's own `globals.css` (unchanged — still owns the base
   `[data-theme]` palette).
2. Imports `@serviceos/design-system/src/theme.css` (additive tokens).
3. Injects `themeInitScript` via an inline `<script>` in `<head>`, which
   reads `localStorage` synchronously and sets `data-theme` on `<html>`
   before React hydrates — prevents flash-of-wrong-theme.
4. Wraps `children` in `<ThemeProvider>` and renders `<ToastViewport/>`
   alongside it.

## Existing shells untouched
Neither app's actual dashboard shell (sidebar/nav in `components/layout`)
was rewritten — this pass only adds the provider at the root. The two
`/dev/sample-shell` pages demonstrate what a shell built purely from
design-system primitives (`PageShell`/`PageHeader`/`Section`/`Card`/
`DataTable`) looks like, as a reference for future migration, without
touching the real nav/shell components or `lib/nav-config.ts`.

## Package resolution
`@serviceos/design-system` is resolved via npm workspaces + a `tsconfig.json`
path alias in each app (`"@serviceos/design-system": ["../packages/
design-system/src/index.ts"]`), so no build step is required for the
package itself — Next.js compiles its TSX directly, same as any other
first-party source file.
