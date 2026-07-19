# Execution Environment

WSL2 Debian, native Linux filesystem copy at `/root/serviceos-ux04a`
(rsynced from `G:\serviceos` at `design/ux-04-tenant-operations`, excluding
`node_modules`/`.next`), re-created fresh after the mid-session host/WSL
restart (the prior `/root/serviceos-ux04` copy from before the restart was
not reused — a brand new rsync + install was performed per the
coordinator's instruction). Node v20.20.2, npm 10.8.2. Same install
command as UX-04 baseline: `npm install --workspaces
--include-workspace-root --no-audit --no-fund`.

One environment change made this pass, from within `frontend/tenant-portal`
(in scope, backward-compatible, documented in
`prerequisite-bug-fix-report.md`): added vitest + testing-library
devDependencies, `vitest.config.ts`, `test-setup.ts`, and a `tsconfig.json`
`types` entry, none of which existed at UX-04 baseline.
