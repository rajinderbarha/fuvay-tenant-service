# Dependency Install Report — Round 2 (Workstream 2)

All installs performed in WSL Debian (`wsl -d Debian`), copying each app (excluding `node_modules`/`.expo`/`.next`/`.git`) via `rsync` from `/mnt/g/serviceos-ux07-cross-app/...` into the WSL native filesystem (`~/ux07-round2/...`), per the proven prior-phase pattern (native Windows npm install is conclusively broken on this machine — `ERR_SSL_CIPHER_OPERATION_FAILED`, documented across UX-01–06's own known-limitations files; not re-attempted).

## mobile/customer-app

- Copied to `~/ux07-round2/customer-app`.
- Command: `rm -rf node_modules && npm install --legacy-peer-deps`
- `--legacy-peer-deps` used because this app mixes Expo/React Native peer dependency trees that npm's default (non-legacy) peer resolution cannot satisfy — the exact same reason documented in every one of UX-01 through UX-06's own environment docs for this app family; not a new discovery this round.
- Result: SUCCESS. 866 packages added, audited 867, in ~2 minutes. 12 moderate vulnerabilities (pre-existing, not investigated — out of this round's scope). No native-module build failures.
- Lockfile: `package-lock.json` used as-is, not deleted or regenerated from scratch beyond the standard `npm install` lockfile refresh.

## mobile/staff-app

- Copied to `~/ux07-round2/staff-app`.
- Command: `rm -rf node_modules && npm install --legacy-peer-deps` (same rationale as customer-app).
- Result: SUCCESS. 872 packages added, audited 873, in 27s. 12 moderate vulnerabilities (pre-existing).

## frontend workspace (super-admin + tenant-portal + packages/design-system)

- These three are an npm-workspaces monorepo (root `package.json`'s `"workspaces"` field: `frontend/packages/*`, `frontend/super-admin`, `frontend/tenant-portal`) — a real, previously-undocumented-in-this-round structural fact discovered when a tenant-portal-only install failed with `404 @serviceos/design-system` (a workspace-linked local package, not a registry package). Corrected by copying the whole workspace root (`package.json` + `frontend/`) into `~/ux07-round2/workspace` and running `npm install` from there instead.
- Command: `npm install --legacy-peer-deps` from the workspace root.
- Result: SUCCESS. 188 packages added, audited 192, in ~4 minutes. 6 vulnerabilities (4 moderate, 1 high, 1 critical — pre-existing, not investigated this round).
- One real dependency-declaration gap found and fixed (frontend-owned correction, not a version upgrade): `frontend/tenant-portal/package.json` was missing `@testing-library/dom` as an explicit devDependency, even though `@testing-library/react@^16.0.1` requires it as a peer. This caused 12 of 16 tenant-portal test files to fail outright (`Cannot find module '@testing-library/dom'`) and 13 real `tsc` errors (`Module '"@testing-library/react"' has no exported member 'screen'`/`'fireEvent'`) purely from the missing declaration — not from any logic defect. Added `"@testing-library/dom": "^10.4.0"` (the version `@testing-library/react@16` itself declares as its peer requirement) as an explicit devDependency and re-ran `npm install` — this is adding a missing pinned dependency the code already required, not a broad upgrade or a `--force`/`legacy-peer-deps`-driven suppression. See `frontend-corrections-report.md`.

## Not installed this round

- `frontend/packages/design-system` was installed AS PART OF the workspace root install above (it is one of the 3 workspaces) — no standalone install attempted or needed.
- No Playwright browser binaries installed this round (`npx playwright install` not run) — see `playwright-baseline.md`.
